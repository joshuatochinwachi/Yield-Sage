"""
solana_pools_live.py

Pure in-memory run: fetch Solana pools from DefiLlama, enrich with
project Image/App Link (also from DefiLlama, live), print the result.
Nothing is written to disk... except see the TEMP / DEV-ONLY block below.

Note: "Pool Address" column is present (matches the target output
shape) but is NULL for any protocol without a verified resolver below.
Wire a new resolver into `fetch_pool_addresses()` for anything else -
that function (plus its per-protocol `_fetch_*_index()` / `_resolve_*()`
helpers) is the only place that needs to change.

Protocols with real Pool Address resolution right now:

  Index-built (bulk fetch from the protocol's own API, matched by mint
  or mint-pair, highest-TVL match wins on ambiguity):
    - raydium         (per-pool mint-pair lookup, Raydium's own API)
    - orca-dex        (bulk mint-pair index, Orca's own API)
    - jupiter-lend    (bulk mint index, Fluid's API - Jupiter Lend runs on Fluid)
    - kamino-lend     (bulk (mint, market) + mint-fallback index, Kamino's own API)
    - kamino-liquidity(bulk mint-pair index, Kamino's own API - different product from kamino-lend)
    - save            (bulk (mint, market) + mint-fallback index, Save/Solend's own API)
    - project-0       (bulk mint index, project-0's own API)
    - gmtrade         (bulk mint/mint-pair index, gmtrade's own DefiLlama-facing feed)
    - loopscale       (bulk mint index, loopscale's own API - first 100 vaults only, see caveat below)

  Direct Pool ID, suffix-stripped (Pool ID = "{address}-solana" ->
  strip the suffix to get the real on-chain address):
    - omnipair          pairAddress
    - onre              ONYC_MINT (mint - ONYC has no separate pool
                        contract, same situation as the LSTs below)
    - ondo-yield-assets USDY mint and OUSG mint (two pools, same
                        stripping logic handles both)

  Direct Pool ID, verbatim (Pool ID = the real on-chain address with no
  suffix at all - pass straight through):
    - allbridge-classic poolAddress
    - cube              pair address (confirmed live against cubee.ee's
                        own /pool/{address} URLs in its API response,
                        not just inferred from source)
    - kyros             LST mint - no separate pool contract exists,
                        the mint IS the yield-bearing asset
    - blackrock-buidl   BUIDL Solana mint (this adaptor is multi-chain
                        and its EVM rows DO append a "-{chain}" suffix,
                        but its Solana row specifically does not - a
                        genuine inconsistency in the adaptor itself, not
                        a mistake in this resolver)
    - Every plain liquid-staking-token adaptor below: the mint IS the
      asset, there is no separate AMM pool - binance-staked-sol,
      jito-liquid-staking, jupiter-staked-sol, drift-staked-sol,
      marinade-liquid-staking, sanctum-infinity, phantom-sol,
      doublezero-staked-sol, jpool, the-vault-liquid-staking,
      bybit-staked-sol, blazestake, helius-staked-sol, dfdv-staked-sol

  Direct Pool ID, verbatim, but with a real alternative to weigh
  (DefiLlama's own adaptor uses the LST mint as Pool ID even though a
  separate on-chain stake-pool program account also exists - this
  resolver follows DefiLlama's own choice for consistency, but the
  program address is noted in case deposit-contract granularity is
  ever wanted instead):
    - jagpool-staked-sol        mint used; stake pool program is
                                jagEdDepWUgexiu4jxojcRWcVKKwFqgZBBuAoGu2BxM
    - stkesol-by-sol-strategies mint used; stake pool program is
                                StKeDUdSu7jMSnPJ1MPqDnk3RdEwD2QbJaisHMebGhw

  Hardcoded mapping (no bulk endpoint exists because the pool set is a
  small fixed constant in the adaptor's own source, not something an
  API lists):
    - hastra            wYLDS has no pool contract -> Pool Address = its
                        own mint. PRIME has no pool contract either, but
                        PRIME_VAULT is the account depositors actually
                        interact with, so that's used instead of the
                        PRIME mint.

Ambiguity note (applies to every index-built resolver above): where a
mint or mint pair backs more than one on-chain pool, these resolvers
take the highest-TVL match rather than guaranteeing a unique correct
one. Where a protocol runs isolated markets (Kamino Lend, Save), a
(mint, market name) index is tried first and is a real match, not a
heuristic - the mint-only path is the fallback used only when that
doesn't hit. Direct Pool ID and hardcoded-mapping resolvers above have
no such ambiguity - the address either falls straight out of DefiLlama's
own Pool ID or is a hand-verified constant, nothing is inferred.

---
TEMP / DEV-ONLY: writes the result to solana_pools_output.csv so you
can inspect it locally. Everything under the "TEMP" markers below is
meant to be deleted when this gets wired into the DB - it's not part
of the real pipeline, it's just a window to look through for now.
---

Usage:
    python solana_pools_live.py
"""

import sys
from datetime import datetime, timezone

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

POOLS_URL = "https://yields.llama.fi/pools"
PROTOCOLS_URL = "https://api.llama.fi/protocols"
RAYDIUM_MINT_URL = "https://api-v3.raydium.io/pools/info/mint"
ORCA_POOLS_URL = "https://api.orca.so/v2/solana/pools"
JUPITER_LEND_TOKENS_URL = "https://api.solana.fluid.io/v1/lending/tokens"
JUPITER_LEND_VAULTS_URL = "https://api.solana.fluid.io/v1/borrowing/vaults"
KAMINO_MARKETS_URL = "https://api.kamino.finance/v2/kamino-market"
KAMINO_RESERVES_METRICS_URL_TMPL = "https://api.kamino.finance/kamino-market/{market}/reserves/metrics"
KAMINO_LIQUIDITY_STRATEGIES_URL = "https://api.kamino.finance/strategies/metrics"
SAVE_CONFIGS_URL = "https://api.solend.fi/v1/markets/configs"
PROJECT_ZERO_METRICS_URL = "https://api.0.xyz/v0/bankMetrics"
GMTRADE_POOLS_URL = "https://market-info-mainnet-prod.gmtrade.xyz/defillama/pools"
LOOPSCALE_VAULTS_URL = "https://tars.loopscale.com/v1/markets/lending_vaults/stats"

# Hastra has no bulk pool-listing endpoint - its own adaptor hardcodes
# exactly these three constants because the pool set is fixed at two
# entries (wYLDS, PRIME). Mirrored here verbatim rather than derived,
# same as the adaptor does it.
HASTRA_WYLDS_MINT = "8fr7WGTVFszfyNWRMXj6fRjZZAnDwmXwEpCrtzmUkdih"
HASTRA_PRIME_MINT = "3b8X44fLF9ooXaUm3hhSgjpmVs6rZZ3pPoGnGahc3Uu7"
HASTRA_PRIME_VAULT = "FvkbfMm98jefJWrqkvXvsSZ9RFaRBae8k6c1jaYA5vY3"

# --- TEMP / DEV-ONLY ---
OUTPUT_CSV = "solana_pools_output.csv"
# --- end TEMP ---

# Some CDN-fronted APIs (this one sits behind Cloudflare) drop or truncate
# responses to Python's default "python-requests/x.x" User-Agent even when
# the same URL loads fine in a browser. A browser-like UA plus a small
# retry policy fixes that without touching anything else in the pipeline.
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
})
_retry = Retry(
    total=3,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],  # POST calls (loopscale) get a single attempt, no retry
)
_SESSION.mount("https://", HTTPAdapter(max_retries=_retry))

# Separate, no-retry session for the Raydium per-pool loop. That loop can
# fire hundreds of sequential requests - if Raydium starts rate-limiting,
# retrying each one with backoff would multiply the wait time instead of
# just moving on. One attempt, fail fast, keep going.
_SESSION_FAST = requests.Session()
_SESSION_FAST.headers.update(_SESSION.headers)


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


NUMERIC_COLUMNS = [
    "APY", "APY Base", "APY Reward",
    "APY % 1D", "APY % 7D", "APY % 30D",
    "APY Base 7D", "TVL USD",
]


def fetch_solana_pools() -> pd.DataFrame:
    """Pull all Solana-chain pools from DefiLlama's yields endpoint."""
    log("Step 1/4: requesting DefiLlama yields.llama.fi/pools ...")
    resp = _SESSION.get(POOLS_URL, timeout=60)
    resp.raise_for_status()
    pools = resp.json().get("data", [])
    log(f"Step 1/4: got {len(pools)} total pools across all chains, filtering to Solana ...")

    rows = []
    for pool in pools:
        if pool.get("chain") != "Solana":
            continue
        rows.append({
            "Project": pool.get("project", ""),
            "Symbol": pool.get("symbol", ""),
            "APY": pool.get("apy") or 0,
            "APY Base": pool.get("apyBase") or 0,
            "APY Reward": pool.get("apyReward") or 0,
            "Reward Tokens": ", ".join(pool.get("rewardTokens") or []),
            "Pool ID": pool.get("pool", ""),
            "APY % 1D": pool.get("apyPct1D") or 0,
            "APY % 7D": pool.get("apyPct7D") or 0,
            "APY % 30D": pool.get("apyPct30D") or 0,
            "Stablecoin": pool.get("stablecoin", False),
            "APY Base 7D": pool.get("apyBase7d") or 0,
            "TVL USD": pool.get("tvlUsd") or 0,
            "Underlying Tokens": ", ".join(pool.get("underlyingTokens") or []),
            # Internal-use only, not part of the final display columns.
            # Needed to disambiguate protocols that run isolated markets
            # (Kamino Lend, Save), where the same mint can appear in more
            # than one pool and only poolMeta tells them apart.
            "Pool Meta": pool.get("poolMeta") or "",
        })

    df = pd.DataFrame(rows)
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    log(f"Step 1/4: done - {len(df)} Solana pools.")
    return df


def fetch_project_lookup() -> pd.DataFrame:
    """Pull Image + App Link per project slug from DefiLlama's protocols list."""
    log("Step 2/4: requesting DefiLlama api.llama.fi/protocols ...")
    resp = _SESSION.get(PROTOCOLS_URL, timeout=60)
    resp.raise_for_status()
    protocols = resp.json()

    rows = []
    for p in protocols:
        slug = p.get("slug") or p.get("module")
        if not slug:
            continue
        rows.append({
            "Project": slug,
            "Image": p.get("logo", ""),
            "App Link": p.get("url", ""),
        })

    log(f"Step 2/4: done - {len(rows)} projects indexed.")
    return pd.DataFrame(rows)


def _fetch_orca_pool_index() -> dict:
    """
    Pull Orca's full Solana pool list once and index it by mint pair
    (frozenset of the two mint addresses -> best pool address by TVL).

    Pagination fix: the real DefiLlama orca-dex adaptor confirms the
    actual cursor shape is meta.cursor.next (not meta.next, which an
    earlier version of this resolver incorrectly assumed) and the next
    page is requested via a `next` query param carrying that cursor
    value, not a `cursor` param. The old shape likely stopped after page
    one whenever meta.next was absent (it always is), which is the most
    probable reason some Orca pools were coming back with no Pool
    Address before.

    minTvl floor: Orca Whirlpools are permissionless - anyone can create
    a pool for any pair at any tick spacing - so the true pool count
    includes a very long tail of $0/dust pools that will never match
    anything in our own DefiLlama-sourced dataset anyway. An earlier
    version of this resolver dropped minTvl entirely to "maximize
    coverage," which in practice meant paginating through tens of
    thousands of empty pools for effectively zero extra matches. This
    now applies minTvl=1 - far below DefiLlama's own minTvl=10000 cutoff,
    so real small pools aren't lost, but true dust is excluded.
    """
    log("Step 3/4: building Orca pool index (bulk fetch, paginated) ...")
    index = {}
    next_cursor = None
    pages = 0
    cumulative_pools = 0
    while True:
        if next_cursor:
            params = {"next": next_cursor, "size": 1000, "minTvl": 1}
        else:
            params = {"sortBy": "tvl", "sortDirection": "desc", "size": 1000, "minTvl": 1}
        resp = _SESSION.get(ORCA_POOLS_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        pools = payload.get("data", [])
        pages += 1

        for p in pools:
            mint_a = (p.get("tokenA") or {}).get("address")
            mint_b = (p.get("tokenB") or {}).get("address")
            address = p.get("address")
            tvl = float(p.get("tvlUsdc") or 0)
            if not (mint_a and mint_b and address):
                continue
            key = frozenset((mint_a, mint_b))
            existing = index.get(key)
            if existing is None or tvl > existing[1]:
                index[key] = (address, tvl)

        cumulative_pools += len(pools)
        log(f"  Orca progress: page {pages} fetched, {cumulative_pools} pool(s) processed so far, {len(index)} mint pairs indexed so far")

        next_cursor = ((payload.get("meta") or {}).get("cursor") or {}).get("next")
        if not next_cursor:
            break

    log(f"Step 3/4: Orca index built - {len(index)} mint pairs across {pages} page(s).")
    return index


def _fetch_jupiter_lend_index() -> dict:
    """
    Pull Jupiter Lend's Earn tokens + borrow vaults from Fluid's API
    (Jupiter Lend runs on Fluid's infrastructure, not its own backend)
    and index by underlying/supply mint address -> best (highest TVL)
    pool address.
    """
    log("Step 4/4: building Jupiter Lend pool index ...")
    index = {}

    def _consider(mint, address, tvl):
        if not (mint and address):
            return
        existing = index.get(mint)
        if existing is None or tvl > existing[1]:
            index[mint] = (address, tvl)

    try:
        resp = _SESSION.get(JUPITER_LEND_TOKENS_URL, timeout=30)
        resp.raise_for_status()
        for t in resp.json():
            asset = t.get("asset", {})
            mint = t.get("assetAddress") or asset.get("address")
            decimals = asset.get("decimals", 0)
            price = float(asset.get("price") or 0)
            tvl = (float(t.get("totalAssets") or 0) / (10 ** decimals)) * price if decimals else 0.0
            _consider(mint, t.get("address"), tvl)
    except requests.RequestException as e:
        log(f"  Jupiter Lend tokens fetch failed: {e}")

    try:
        resp = _SESSION.get(JUPITER_LEND_VAULTS_URL, timeout=30)
        resp.raise_for_status()
        for v in resp.json():
            supply = v.get("supplyToken", {})
            decimals = supply.get("decimals", 0)
            price = float(supply.get("price") or 0)
            tvl = (float(v.get("totalSupply") or 0) / (10 ** decimals)) * price if decimals else 0.0
            _consider(supply.get("address"), v.get("address"), tvl)
    except requests.RequestException as e:
        log(f"  Jupiter Lend vaults fetch failed: {e}")

    log(f"Step 4/4: Jupiter Lend index built - {len(index)} mint(s) indexed.")
    return index


def _fetch_kamino_index() -> tuple[dict, dict]:
    """
    Pull Kamino Lend's markets + per-market reserve metrics from
    Kamino's own API and build two indexes:

      - by_market: (liquidityTokenMint, market name lowercased) -> reserve
        address. This is the precise match - Kamino runs isolated
        markets, so the same mint can have a separate reserve in several
        different markets (visible in DefiLlama's own data as different
        `poolMeta` values like "Ethena Market", "OnRe Market", etc.),
        and only the market name disambiguates them correctly.

      - by_mint: liquidityTokenMint -> (reserve address, tvl), keeping the
        highest-TVL reserve per mint. Used only as a fallback.
    """
    log("Step 4/4: building Kamino Lend pool index (markets + per-market reserves) ...")
    by_market = {}
    by_mint = {}

    try:
        resp = _SESSION.get(KAMINO_MARKETS_URL, timeout=30)
        resp.raise_for_status()
        markets = resp.json()
    except requests.RequestException as e:
        log(f"  Kamino Lend markets fetch failed: {e}")
        return by_market, by_mint

    log(f"Step 4/4: {len(markets)} Kamino Lend market(s) to check ...")

    for market in markets:
        lending_market = market.get("lendingMarket")
        market_name = (market.get("name") or "").strip().lower()
        if not lending_market:
            continue

        try:
            resp = _SESSION.get(
                KAMINO_RESERVES_METRICS_URL_TMPL.format(market=lending_market),
                params={"env": "mainnet-beta"},
                timeout=30,
            )
            resp.raise_for_status()
            reserves = resp.json()
        except requests.RequestException as e:
            log(f"  Kamino Lend reserves fetch failed for market {lending_market}: {type(e).__name__}")
            continue

        for r in reserves:
            mint = r.get("liquidityTokenMint")
            address = r.get("reserve")
            if not (mint and address):
                continue

            if market_name:
                by_market[(mint, market_name)] = address

            tvl = float(r.get("totalSupplyUsd") or 0) - float(r.get("totalBorrowUsd") or 0)
            existing = by_mint.get(mint)
            if existing is None or tvl > existing[1]:
                by_mint[mint] = (address, tvl)

    log(
        f"Step 4/4: Kamino Lend index built - {len(by_market)} (mint, market) pair(s), "
        f"{len(by_mint)} mint(s) fallback."
    )
    return by_market, by_mint


def _fetch_kamino_liquidity_index() -> dict:
    """
    Pull Kamino's liquidity (LP vault) strategies and index by mint pair
    (frozenset of tokenA/tokenB mint addresses) -> best pool address by
    TVL. This is a different Kamino product from Kamino Lend above -
    "kamino-liquidity" wraps concentrated-liquidity positions into
    managed vaults, each with its own on-chain strategy address, given
    directly by the API (no derivation needed).
    """
    log("Step 4/4: building Kamino Liquidity pool index ...")
    index = {}
    try:
        resp = _SESSION.get(
            KAMINO_LIQUIDITY_STRATEGIES_URL,
            params={"env": "mainnet-beta", "status": "LIVE"},
            timeout=30,
        )
        resp.raise_for_status()
        strategies = resp.json()
    except requests.RequestException as e:
        log(f"  Kamino Liquidity strategies fetch failed: {e}")
        return index

    for s in strategies:
        mint_a = s.get("tokenAMint")
        mint_b = s.get("tokenBMint")
        address = s.get("strategy")
        tvl = float(s.get("totalValueLocked") or 0)
        if not (mint_a and mint_b and address):
            continue
        key = frozenset((mint_a, mint_b))
        existing = index.get(key)
        if existing is None or tvl > existing[1]:
            index[key] = (address, tvl)

    log(f"Step 4/4: Kamino Liquidity index built - {len(index)} mint pair(s).")
    return index


def _fetch_save_index() -> tuple[dict, dict]:
    """
    Pull Save's (formerly Solend) market configs and index reserve
    addresses. Save runs multiple named markets ("Main Pool", "Turbo
    Pool", etc.) similar to Kamino Lend's isolated markets - same
    convention as Kamino Lend above: a precise (mint, market label)
    index first, mint-only fallback second.

    Only the configs endpoint is used (not the live /v1/reserves
    endpoint) since reserve addresses and mints are static config-level
    data, not something that changes with live rates - no need to pull
    live rate data just to resolve an address.

    The market label reproduces DefiLlama's own poolMeta string exactly
    (capitalize only the first character of the market name, append
    " Pool"), so it can be matched directly against the "Pool Meta"
    column already captured in fetch_solana_pools().

    Fallback caveat: the configs payload has no per-reserve TVL, so
    unlike every other resolver here, the mint-only fallback for Save
    just keeps the first reserve seen for a given mint rather than
    picking the highest-TVL one - there's no TVL to pick by.
    """
    log("Step 4/4: building Save pool index ...")
    by_market = {}
    by_mint = {}
    try:
        resp = _SESSION.get(SAVE_CONFIGS_URL, params={"deployment": "production"}, timeout=30)
        resp.raise_for_status()
        markets = resp.json()
    except requests.RequestException as e:
        log(f"  Save configs fetch failed: {e}")
        return by_market, by_mint

    for market in markets:
        market_name = (market.get("name") or "").strip()
        label = ""
        if market_name:
            label = (market_name[:1].upper() + market_name[1:] + " Pool").strip().lower()

        for reserve in market.get("reserves", []):
            liquidity_token = reserve.get("liquidityToken") or {}
            mint = liquidity_token.get("mint")
            address = reserve.get("address")
            if not (mint and address):
                continue
            if label:
                by_market[(mint, label)] = address
            by_mint.setdefault(mint, address)

    log(f"Step 4/4: Save index built - {len(by_market)} (mint, market) pair(s), {len(by_mint)} mint(s) fallback.")
    return by_market, by_mint


def _fetch_project_zero_index() -> dict:
    """
    Pull project-0's bank metrics and index by mint -> best (highest TVL)
    bank address. `bank.bank` is the actual on-chain Bank account pubkey;
    DefiLlama's own adaptor just prefixes it with "project-0-" to build
    its internal pool key, so `bank.bank` itself - not that prefixed
    string - is the real Pool Address.
    """
    log("Step 4/4: building project-0 pool index ...")
    index = {}
    try:
        resp = _SESSION.get(PROJECT_ZERO_METRICS_URL, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        banks = payload.get("banks") or []
    except requests.RequestException as e:
        log(f"  project-0 metrics fetch failed: {e}")
        return index

    for bank in banks:
        mint = bank.get("mint")
        address = bank.get("bank")
        tvl = float(bank.get("totalDepositsUsd") or 0)
        if not (mint and address):
            continue
        existing = index.get(mint)
        if existing is None or tvl > existing[1]:
            index[mint] = (address, tvl)

    log(f"Step 4/4: project-0 index built - {len(index)} mint(s) indexed.")
    return index


def _fetch_gmtrade_index() -> dict:
    """
    Pull gmtrade's own DefiLlama-facing pools feed directly - it already
    returns the real on-chain pool address per pool in one bulk call.
    Indexed by mint pair for two-sided markets, or the single mint for
    single-asset markets (long_token == short_token after dedup).
    """
    log("Step 4/4: building gmtrade pool index ...")
    index = {}
    try:
        resp = _SESSION.get(GMTRADE_POOLS_URL, timeout=30)
        resp.raise_for_status()
        pools = resp.json()
    except requests.RequestException as e:
        log(f"  gmtrade pools fetch failed: {e}")
        return index

    for p in pools:
        address = str(p.get("pool") or "").strip()
        long_token = str(p.get("long_token") or "").strip()
        short_token = str(p.get("short_token") or "").strip()
        mint_list = list(dict.fromkeys(t for t in (long_token, short_token) if t))
        if not (address and mint_list):
            continue
        key = frozenset(mint_list) if len(mint_list) == 2 else mint_list[0]
        tvl = float(p.get("tvl_usd") or 0)
        existing = index.get(key)
        if existing is None or tvl > existing[1]:
            index[key] = (address, tvl)

    log(f"Step 4/4: gmtrade index built - {len(index)} key(s) indexed.")
    return index


def _fetch_loopscale_index() -> dict:
    """
    Pull loopscale's lending vault stats and index by principal mint ->
    best (highest TVL) vault address.

    Coverage caveat: this mirrors the DefiLlama adaptor's own call
    exactly - page 0, pageSize 100, no pagination loop beyond that. If
    loopscale ever lists more than 100 vaults, both DefiLlama's own
    adaptor and this resolver silently miss the rest. That's a real,
    unfixed limitation, not something patched here - the source didn't
    show what page-2+ looks like, so I'm not guessing at an endpoint
    shape I haven't seen.
    """
    log("Step 4/4: building loopscale pool index ...")
    index = {}
    try:
        resp = _SESSION.post(
            LOOPSCALE_VAULTS_URL,
            json={"page": 0, "pageSize": 100},
            timeout=30,
        )
        resp.raise_for_status()
        vaults = resp.json()
    except requests.RequestException as e:
        log(f"  loopscale vaults fetch failed: {e}")
        return index

    for v in vaults:
        mint = v.get("principalMint")
        address = v.get("vaultAddress")
        deposits = float(v.get("principalDepositsUsd") or 0)
        deployed = float(v.get("principalDeployedUsd") or 0)
        tvl = deposits - deployed
        if not (mint and address):
            continue
        existing = index.get(mint)
        if existing is None or tvl > existing[1]:
            index[mint] = (address, tvl)

    if len(vaults) >= 100:
        log("  loopscale returned 100 vaults on page 0 - there may be more on later pages not fetched here.")

    log(f"Step 4/4: loopscale index built - {len(index)} mint(s) indexed.")
    return index


def _fetch_raydium_pool_address(mint_a: str, mint_b: str) -> str | None:
    """
    Query Raydium's mint-pair endpoint for a specific pool pair.
    If multiple pools exist for this pair (different fee tiers / pool
    types), take the highest-liquidity one.
    """
    m1, m2 = sorted((mint_a, mint_b))
    params = {
        "mint1": m1,
        "mint2": m2,
        "poolType": "all",
        "poolSortField": "liquidity",
        "sortType": "desc",
        "pageSize": 1,
        "page": 1,
    }
    resp = _SESSION_FAST.get(RAYDIUM_MINT_URL, params=params, timeout=10)
    if resp.status_code != 200:
        return None
    payload = resp.json()
    if not payload.get("success"):
        return None
    rows = (payload.get("data") or {}).get("data") or []
    if not rows:
        return None
    return rows[0].get("id")


# Direct Pool ID = "{address}-solana" -> strip the suffix to recover the
# real on-chain address. See module docstring for per-protocol notes.
_SUFFIX_STRIP_PROJECTS = frozenset({
    "omnipair",
    "onre",
    "ondo-yield-assets",
})

# Direct Pool ID, no suffix at all - the Pool ID already IS the real
# on-chain address (mint, for LSTs and single-asset RWA tokens with no
# separate pool contract; pair/vault address, for the AMM-style ones).
# See module docstring for per-protocol notes and the two cases
# (jagpool-staked-sol, stkesol-by-sol-strategies) where a real
# alternative program address exists but DefiLlama's own adaptor - and
# therefore this resolver, for consistency - uses the mint instead.
_VERBATIM_PROJECTS = frozenset({
    "allbridge-classic",
    "cube",
    "kyros",
    "blackrock-buidl",
    "binance-staked-sol",
    "jito-liquid-staking",
    "jupiter-staked-sol",
    "drift-staked-sol",
    "marinade-liquid-staking",
    "sanctum-infinity",
    "phantom-sol",
    "doublezero-staked-sol",
    "jpool",
    "the-vault-liquid-staking",
    "bybit-staked-sol",
    "blazestake",
    "helius-staked-sol",
    "dfdv-staked-sol",
    "jagpool-staked-sol",
    "stkesol-by-sol-strategies",
})

DIRECT_POOL_ID_PROJECTS = _SUFFIX_STRIP_PROJECTS | _VERBATIM_PROJECTS


def _resolve_direct_pool_id(project: str, pool_id: str) -> str | None:
    """
    Direct Pool ID protocols - no index build, no per-pool API call
    needed at all. DefiLlama's own Pool ID already IS (or trivially
    contains) the real on-chain pool/pair/mint address for these
    adaptors, confirmed by reading each adaptor's own source (cube also
    confirmed live - see module docstring).

    No ambiguity note applies here, unlike the index-built resolvers
    above - there's no TVL tiebreak because there's nothing to choose
    between, the address falls straight out of the Pool ID.
    """
    if project in _SUFFIX_STRIP_PROJECTS:
        if pool_id.endswith("-solana"):
            return pool_id[: -len("-solana")]
        return None
    if project in _VERBATIM_PROJECTS:
        return pool_id or None
    return None


def _resolve_hastra_pool_address(pool_id: str) -> str | None:
    """
    Hastra has no AMM pool contract - "pool" in its own adaptor is just
    the yield-bearing mint itself, and its Pool ID format is
    "{mint}-solana", same suffix convention as omnipair.

      - wYLDS: no separate contract exists at all - Pool Address is the
        wYLDS mint itself.
      - PRIME: also has no separate pool contract, but PRIME_VAULT (the
        account actually holding the wYLDS backing every PRIME token) is
        the closer analogue to a "pool" a depositor interacts with, so
        that vault address is used instead of the PRIME mint.

    Hardcoded rather than fetched because hastra's own adaptor hardcodes
    these same three constants - there's no bulk endpoint to index
    against since the pool set is fixed at exactly two entries.
    """
    if not pool_id.endswith("-solana"):
        return None
    mint = pool_id[: -len("-solana")]
    if mint == HASTRA_WYLDS_MINT:
        return HASTRA_WYLDS_MINT
    if mint == HASTRA_PRIME_MINT:
        return HASTRA_PRIME_VAULT
    return None


def fetch_pool_addresses(pools_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve "Pool Address" across every protocol with a verified free
    source (see the module docstring for the current list). Everything
    else gets None - there is no verified free source for them yet.

    Ambiguity note: applies globally to the index-built resolvers only -
    see module docstring.
    """
    log("Step 4/4: resolving Pool Address across all supported protocols ...")
    results = []

    orca_index = None
    jupiter_index = None
    kamino_index = None
    kamino_liquidity_index = None
    save_index = None
    project_zero_index = None
    gmtrade_index = None
    loopscale_index = None

    raydium_calls = 0
    raydium_hits = 0
    raydium_failures = 0
    orca_hits = 0
    jupiter_hits = 0
    kamino_hits = 0
    kamino_market_hits = 0
    kamino_liquidity_hits = 0
    save_hits = 0
    save_market_hits = 0
    project_zero_hits = 0
    gmtrade_hits = 0
    loopscale_hits = 0
    hastra_hits = 0
    # One counter per "direct" protocol (suffix-strip + verbatim) rather
    # than a named variable each - there are 21 of them now and that many
    # flat counters stops being readable. Populated on demand as hits
    # come in, so protocols that never appear in a given run just don't
    # show up in the summary log instead of printing a wall of zeros.
    direct_hits: dict[str, int] = {}

    raydium_total = int(pools_df["Project"].str.lower().str.contains("raydium").sum())
    log(f"Step 4/4: {raydium_total} Raydium pool(s) to check individually (this is the slow part) ...")

    for _, row in pools_df.iterrows():
        pool_id = row["Pool ID"]
        project = str(row["Project"]).lower()
        underlying = row.get("Underlying Tokens") or ""
        mints = [t.strip() for t in underlying.split(",") if t.strip()]
        pool_meta = str(row.get("Pool Meta") or "").strip().lower()

        address = None

        # Direct Pool ID + hardcoded-mapping protocols first - these
        # don't depend on the mints list at all, so they're resolved
        # before (and independently of) the mint-count gate below.
        if project in DIRECT_POOL_ID_PROJECTS:
            address = _resolve_direct_pool_id(project, pool_id)
            if address:
                direct_hits[project] = direct_hits.get(project, 0) + 1

        elif project == "hastra":
            address = _resolve_hastra_pool_address(pool_id)
            if address:
                hastra_hits += 1

        elif len(mints) in (1, 2):
            if "raydium" in project and len(mints) == 2:
                raydium_calls += 1
                try:
                    address = _fetch_raydium_pool_address(mints[0], mints[1])
                    if address:
                        raydium_hits += 1
                except requests.RequestException as e:
                    raydium_failures += 1
                    log(f"  Raydium lookup failed for pool {pool_id}: {type(e).__name__}")
                    address = None
                if raydium_calls % 25 == 0 or raydium_calls == raydium_total:
                    log(f"  Raydium progress: {raydium_calls}/{raydium_total} checked, {raydium_hits} matched so far")

            elif "orca" in project and len(mints) == 2:
                if orca_index is None:
                    try:
                        orca_index = _fetch_orca_pool_index()
                    except requests.RequestException as e:
                        log(f"  Orca index build failed: {e}")
                        orca_index = {}
                match = orca_index.get(frozenset(mints))
                address = match[0] if match else None
                if address:
                    orca_hits += 1

            elif "jupiter-lend" in project and len(mints) == 1:
                if jupiter_index is None:
                    try:
                        jupiter_index = _fetch_jupiter_lend_index()
                    except requests.RequestException as e:
                        log(f"  Jupiter Lend index build failed: {e}")
                        jupiter_index = {}
                match = jupiter_index.get(mints[0])
                address = match[0] if match else None
                if address:
                    jupiter_hits += 1

            elif "kamino-liquidity" in project and len(mints) == 2:
                if kamino_liquidity_index is None:
                    try:
                        kamino_liquidity_index = _fetch_kamino_liquidity_index()
                    except requests.RequestException as e:
                        log(f"  Kamino Liquidity index build failed: {e}")
                        kamino_liquidity_index = {}
                match = kamino_liquidity_index.get(frozenset(mints))
                address = match[0] if match else None
                if address:
                    kamino_liquidity_hits += 1

            elif "kamino-lend" in project and len(mints) == 1:
                if kamino_index is None:
                    try:
                        kamino_index = _fetch_kamino_index()
                    except requests.RequestException as e:
                        log(f"  Kamino Lend index build failed: {e}")
                        kamino_index = ({}, {})
                by_market, by_mint = kamino_index
                if pool_meta:
                    address = by_market.get((mints[0], pool_meta))
                    if address:
                        kamino_market_hits += 1
                if not address:
                    match = by_mint.get(mints[0])
                    address = match[0] if match else None
                if address:
                    kamino_hits += 1

            elif project == "save" and len(mints) == 1:
                if save_index is None:
                    try:
                        save_index = _fetch_save_index()
                    except requests.RequestException as e:
                        log(f"  Save index build failed: {e}")
                        save_index = ({}, {})
                by_market, by_mint = save_index
                if pool_meta:
                    address = by_market.get((mints[0], pool_meta))
                    if address:
                        save_market_hits += 1
                if not address:
                    address = by_mint.get(mints[0])
                if address:
                    save_hits += 1

            elif "project-0" in project and len(mints) == 1:
                if project_zero_index is None:
                    try:
                        project_zero_index = _fetch_project_zero_index()
                    except requests.RequestException as e:
                        log(f"  project-0 index build failed: {e}")
                        project_zero_index = {}
                match = project_zero_index.get(mints[0])
                address = match[0] if match else None
                if address:
                    project_zero_hits += 1

            elif "gmtrade" in project:
                if gmtrade_index is None:
                    try:
                        gmtrade_index = _fetch_gmtrade_index()
                    except requests.RequestException as e:
                        log(f"  gmtrade index build failed: {e}")
                        gmtrade_index = {}
                key = frozenset(mints) if len(mints) == 2 else mints[0]
                match = gmtrade_index.get(key)
                address = match[0] if match else None
                if address:
                    gmtrade_hits += 1

            elif "loopscale" in project and len(mints) == 1:
                if loopscale_index is None:
                    try:
                        loopscale_index = _fetch_loopscale_index()
                    except requests.RequestException as e:
                        log(f"  loopscale index build failed: {e}")
                        loopscale_index = {}
                match = loopscale_index.get(mints[0])
                address = match[0] if match else None
                if address:
                    loopscale_hits += 1

        results.append({"Pool ID": pool_id, "Pool Address": address})

    direct_summary = " | ".join(
        f"{project} {count} matched" for project, count in sorted(direct_hits.items())
    )
    log(
        f"Step 4/4: done - Raydium {raydium_hits}/{raydium_calls} matched "
        f"({raydium_failures} request failures) | Orca {orca_hits} matched | "
        f"Jupiter Lend {jupiter_hits} matched | "
        f"Kamino Lend {kamino_hits} matched ({kamino_market_hits} via exact market match) | "
        f"Kamino Liquidity {kamino_liquidity_hits} matched | "
        f"Save {save_hits} matched ({save_market_hits} via exact market match) | "
        f"project-0 {project_zero_hits} matched | "
        f"gmtrade {gmtrade_hits} matched | "
        f"loopscale {loopscale_hits} matched | "
        f"hastra {hastra_hits} matched"
        + (f" | {direct_summary}" if direct_summary else "")
    )
    return pd.DataFrame(results)


def build_enriched_view() -> pd.DataFrame:
    """Fetch + merge, entirely in memory. Nothing written to disk."""
    pools = fetch_solana_pools()
    projects = fetch_project_lookup()
    addresses = fetch_pool_addresses(pools)

    log("Merging pools + project metadata + pool addresses ...")
    enriched = pools.merge(projects, on="Project", how="left")
    enriched = enriched.merge(addresses, on="Pool ID", how="left")

    # Column order matches the target output shape exactly.
    display_cols = {
        "Project": "Protocol",
        "Pool Address": "Pool Address",
        "Symbol": "Asset",
        "APY": "APY",
        "APY Base": "Base APY",
        "APY Reward": "Reward APY",
        "TVL USD": "TVL ($)",
        "Reward Tokens": "Reward Tokens",
        "Pool ID": "Pool ID",
        "APY % 1D": "APY (1D)",
        "APY % 7D": "APY (7D)",
        "APY % 30D": "APY (30D)",
        "Image": "Image",
        "App Link": "App Link",
    }
    enriched = enriched.rename(columns=display_cols)
    enriched = enriched[list(display_cols.values())]
    enriched = enriched.sort_values("TVL ($)", ascending=False).reset_index(drop=True)

    return enriched


def main():
    log("Starting Solana pool refresh ...")
    try:
        df = build_enriched_view()
    except requests.RequestException as e:
        log(f"FAILED during a network request: {type(e).__name__}: {e}")
        print(
            "\nIf this URL loads fine in a browser but fails here, it's usually "
            "either a Cloudflare/User-Agent block (should be fixed by the "
            "session headers in this script) or a local network/antivirus "
            "interception. Try disabling antivirus real-time protection or any "
            "VPN temporarily and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        log(f"FAILED with an unexpected error: {type(e).__name__}: {e}")
        raise

    log(f"All steps complete - {len(df)} Solana pools ready.")

    # --- TEMP / DEV-ONLY: remove this block when the DB write replaces it ---
    df.to_csv(OUTPUT_CSV, index=False)
    log(f"[TEMP] Wrote {len(df)} rows to {OUTPUT_CSV} for local inspection.")
    # --- end TEMP ---


if __name__ == "__main__":
    main()
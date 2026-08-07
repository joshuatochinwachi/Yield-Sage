"""
solana_pools_live.py

Pure in-memory run: fetch Solana pools from DefiLlama, enrich with
project Image/App Link (also from DefiLlama, live), print the result.
Nothing is written to disk... except see the TEMP / DEV-ONLY block below.

Note: "Pool Address" column is present (matches the target output
shape) but is NULL for any protocol without a verified resolver below.
Wire a new resolver into `fetch_pool_addresses()` for anything else -
that function (plus its per-protocol helpers) is the only place that
needs to change.

*** IMPORTANT - READ BEFORE ADDING A NEW RESOLVER ***
DefiLlama's live yields.llama.fi/pools endpoint does NOT expose the
literal `pool:` string an adaptor author wrote in their source code.
DefiLlama's backend assigns its own internal UUID (e.g.
"9e709e57-84eb-496b-82ce-2e8f6a17db1b") as the public "pool" id for
every single protocol, with no exceptions found so far - confirmed by
fetching the live endpoint directly, not just reading adaptor source.
The "Pool ID" column in this script's output is that UUID. It is
USELESS as a source of the real on-chain address, no matter how clean
or address-like the adaptor's own `pool:` field looks in its GitHub
source. An earlier version of this script assumed Pool ID could be
parsed directly for several protocols (stripping a "-solana" suffix,
or passing it through verbatim) - that assumption was wrong for all of
them and silently produced either the UUID itself as a fake "Pool
Address", or nothing at all, depending on the shape. Every resolver
below either (a) reads the real mint address from the separate
`underlyingTokens` field DefiLlama does preserve correctly, and looks
the pool/vault/reserve address up via the protocol's own API, or (b)
uses a hand-verified hardcoded constant for protocols whose pool set is
small and fixed. Nothing here trusts Pool ID for anything beyond
joining this table back to the row it came from.

Protocols with real Pool Address resolution right now:

  Index-built (bulk fetch from the protocol's own API, matched by mint
  or mint-pair pulled from `underlyingTokens` - never from Pool ID -
  highest-TVL match wins on ambiguity where the source data allows it):
    - raydium         (per-pool mint-pair lookup, Raydium's own API)
    - orca-dex        (bulk mint-pair index, Orca's own API)
    - jupiter-lend    (bulk mint index, Fluid's API - Jupiter Lend runs on Fluid)
    - kamino-lend     (bulk (mint, market) + mint-fallback index, Kamino's own API)
    - kamino-liquidity(bulk mint-pair index, Kamino's own API - different product from kamino-lend)
    - save            (bulk (mint, market) + mint-fallback index, Save/Solend's own API)
    - project-0       (bulk mint index, project-0's own API)
    - gmtrade         (bulk mint/mint-pair index, gmtrade's own DefiLlama-facing feed)
    - loopscale       (bulk mint index, loopscale's own API - first 100 vaults only, see caveat below)
    - omnipair        (bulk mint-pair index, omnipair's own indexer API -
                       no TVL tiebreak available, see caveat below)
    - allbridge-classic (bulk mint index, Allbridge's own token-info API,
                       filtered to the SOL chain entry)
    - cube            (bulk mint/mint-pair index, Cube's own DefiLlama-
                       facing feed - live-confirmed the `pool` field it
                       returns is a real on-chain address, via that
                       feed's own accompanying /pool/{address} url per
                       entry)
    - sentora         (bulk (mint, vault name) + mint-fallback index,
                       Sentora's own vaults API - Solana side of this
                       adaptor is Kamino-managed vaults only, see
                       caveat below)
    - yo-protocol     (bulk (mint, vault name) + mint-fallback index,
                       yo.xyz's own Solana vault-stats API, see caveat
                       below)

  Hardcoded (no bulk endpoint needed - the pool set is a small fixed
  constant taken from each adaptor's own source, matched by Project,
  or by (Project, Symbol) where a protocol has more than one Solana
  pool):
    - Single-pool LSTs / RWA tokens with no separate pool contract -
      the mint IS the yield-bearing asset - matched on Project alone:
      binance-staked-sol, jito-liquid-staking, jupiter-staked-sol,
      drift-staked-sol, marinade-liquid-staking, sanctum-infinity,
      phantom-sol, doublezero-staked-sol, jpool, the-vault-liquid-staking,
      bybit-staked-sol, blazestake, helius-staked-sol, dfdv-staked-sol,
      onre, blackrock-buidl, stronghold-staked-sol, save-sol,
      lantern-staked-sol, pico-staked-sol, laine-sol, starke-staked-sol,
      openeden-usdo, openeden-tbill, invesco-ustb.
    - jagpool-staked-sol / stkesol-by-sol-strategies / save-sol /
      laine-sol: same situation, matched on Project alone, but each has
      a real, separate on-chain stake-pool program account that
      DefiLlama's own adaptor chooses NOT to use as `pool` (it uses the
      mint instead). This resolver follows DefiLlama's own choice for
      consistency - the program addresses are noted next to the
      constants below in case deposit-contract granularity is ever
      wanted instead.
    - Single-pool RWA/stablecoin tokens, same "mint is the asset, no
      separate pool contract" situation as above - matched on Project
      alone: apollo-diversified-credit-securitize-fund, vaneck-treasury-
      fund, hylo-lsts, bonk-staked-sol, bitwise-uscc, marginfi-lst,
      unitas-usdu.
    - credix: matched on Project alone, but unlike every other entry in
      this list, the pool value isn't a mint at all - it's a hardcoded
      market/pool address literal (with the same "-solana" suffix
      convention as omnipair/onre) baked directly into the adaptor's own
      source, not derived from underlyingTokens (which is just the USDC
      mint here, shared across many unrelated pools, so unusable as a
      key on its own).
    - tramplin.io: matched on Project alone, same "not a mint" situation
      as credix - this protocol has no LST token at all. The pool value
      is the Solana validator vote-account address depositors delegate
      stake to (rewards are redistributed via an off-chain lottery, not
      an on-chain LST), baked directly into the adaptor's own source.
    - hastra: matched on (Project, Symbol) - two pools. wYLDS has no
      pool contract -> Pool Address = its own mint. PRIME has no pool
      contract either, but PRIME_VAULT is the account depositors
      actually interact with, so that's used instead of the PRIME mint.
    - ondo-yield-assets: matched on (Project, Symbol) - two pools
      (USDY, OUSG), each just its own mint, no separate pool contract.
    - kyros: matched on (Project, Symbol) - two pools (kySOL, kyJTO),
      each just its own mint, no separate pool contract.

Ambiguity note (applies to every index-built resolver above except
omnipair and allbridge-classic, which have no TVL signal available -
see their docstrings): where a mint or mint pair backs more than one
on-chain pool, these resolvers take the highest-TVL match rather than
guaranteeing a unique correct one. Where a protocol runs isolated
markets (Kamino Lend, Save), a (mint, market name) index is tried first
and is a real match, not a heuristic - the mint-only path is the
fallback used only when that doesn't hit.

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
OMNIPAIR_POOLS_URL = "https://api.indexer.omnipair.fi/api/v1/pools"
ALLBRIDGE_TOKEN_INFO_URL = "https://core.api.allbridgecoreapi.net/token-info"
CUBE_POOLS_URL = "https://api.cubee.ee/api/defillama/yields"
SENTORA_VAULTS_URL = "https://services.vaults.sentora.com/vaults"
YO_PROTOCOL_SOLANA_URL = "https://api.yo.xyz/api/v1/solana/vault/stats"

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


def _omnipair_get_address(value) -> str | None:
    """omnipair's token0/token1 fields are sometimes a bare address
    string, sometimes an object with an .address key - mirrors the
    getAddress() helper in the adaptor's own source exactly."""
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        addr = value.get("address")
        return addr if isinstance(addr, str) else None
    return None


def _fetch_omnipair_index() -> dict:
    """
    Pull omnipair's own indexer API and index by mint pair (frozenset of
    token0/token1 addresses) -> pool/pair address.

    No TVL tiebreak: unlike every other index-built resolver above,
    omnipair's pools endpoint doesn't return a ready-made USD TVL - the
    adaptor's own source computes it via a multi-pass price-propagation
    routine (using reserves + DefiLlama spot prices) that isn't worth
    replicating just to resolve an address. On the rare mint pair with
    more than one omnipair pool, this index keeps the last one seen in
    the response rather than a verified highest-TVL winner - a real,
    documented limitation, not a silent guess.

    Response shape caveat: I have not been able to independently verify
    the live shape of this endpoint - api.indexer.omnipair.fi isn't
    reachable from my own tooling, so this candidate-selection logic is
    ported from the adaptor's own defensive extractPools() helper, which
    itself tries several possible shapes because even its author wasn't
    certain which one is live. A first version of this resolver picked
    the first *truthy* candidate regardless of what was inside it, which
    crashed in production when that candidate turned out to be a list of
    plain strings, not pool objects. This version only accepts a
    candidate if it's a list AND its first element is a dict, and logs
    a diagnostic of what it actually found if nothing qualifies, so a
    real run surfaces the true shape instead of guessing wrong again.
    """
    log("Step 4/4: building omnipair pool index ...")
    index: dict = {}
    try:
        resp = _SESSION.get(
            OMNIPAIR_POOLS_URL,
            params={"limit": 1000, "sortBy": "tvl", "sortOrder": "desc"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        log(f"  omnipair pools fetch failed: {e}")
        return index

    def _looks_like_pool_list(candidate) -> bool:
        return (
            isinstance(candidate, list)
            and len(candidate) > 0
            and isinstance(candidate[0], dict)
        )

    pools = []
    if isinstance(payload, dict):
        candidates = [
            ("pools", payload.get("pools")),
            ("data", payload.get("data")),
            ("data.pools", (payload.get("data") or {}).get("pools")
                if isinstance(payload.get("data"), dict) else None),
            ("result", payload.get("result")),
            ("result.pools", (payload.get("result") or {}).get("pools")
                if isinstance(payload.get("result"), dict) else None),
        ]
        for name, candidate in candidates:
            if _looks_like_pool_list(candidate):
                pools = candidate
                log(f"  omnipair: using '{name}' as the pool list ({len(pools)} entries).")
                break
        else:
            shapes = {name: type(c).__name__ for name, c in candidates if c is not None}
            log(f"  omnipair: no candidate field held a list of pool objects. "
                f"Field types seen: {shapes or 'none present'}. Top-level keys: {list(payload.keys())}")
    elif _looks_like_pool_list(payload):
        pools = payload
        log(f"  omnipair: response was itself a pool list ({len(pools)} entries).")
    else:
        log(f"  omnipair: unrecognized top-level response type {type(payload).__name__}, skipping.")

    skipped_non_dict = 0
    for p in pools:
        if not isinstance(p, dict):
            skipped_non_dict += 1
            continue
        address = p.get("pair_address") or p.get("address") or p.get("poolAddress")
        mint_a = _omnipair_get_address(p.get("token0"))
        mint_b = _omnipair_get_address(p.get("token1"))
        if not (address and mint_a and mint_b):
            continue
        index[frozenset((mint_a, mint_b))] = address

    if skipped_non_dict:
        log(f"  omnipair: skipped {skipped_non_dict} non-dict entr(ies) in the pool list.")

    log(f"Step 4/4: omnipair index built - {len(index)} mint pair(s).")
    return index


def _fetch_allbridge_classic_index() -> dict:
    """
    Pull Allbridge Classic's token-info API and index by mint -> pool
    address, filtered to the SOL chain entry only (this API is
    multi-chain - BSC, ETH, POL, TRX, SOL, ARB - and poolAddress values
    from other chains are meaningless here).

    No TVL tiebreak: the configs payload has no per-token USD TVL
    exposed in a form worth trusting over `poolInfo.totalLpAmount`
    (a raw LP unit count, not USD) - same situation as Save's mint-only
    fallback above. In practice this API appears to list each Solana
    mint once, so it hasn't come up, but it's not verified to never
    happen.
    """
    log("Step 4/4: building allbridge-classic pool index ...")
    index: dict = {}
    try:
        resp = _SESSION.get(ALLBRIDGE_TOKEN_INFO_URL, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        log(f"  allbridge-classic token-info fetch failed: {e}")
        return index

    sol_chain = payload.get("SOL") or {}
    for t in sol_chain.get("tokens", []):
        mint = t.get("tokenAddress")
        address = t.get("poolAddress")
        if not (mint and address):
            continue
        index.setdefault(mint, address)

    log(f"Step 4/4: allbridge-classic index built - {len(index)} mint(s) indexed.")
    return index


def _fetch_cube_index() -> dict:
    """
    Pull Cube's own DefiLlama-facing pools feed and index by mint pair
    (frozenset of underlyingTokens) or single mint -> best (highest TVL)
    pool address. Same shape and same feed as the gmtrade resolver
    above. The `pool` field this feed returns is a confirmed real
    on-chain address - live-checked against the accompanying
    /pool/{address} `url` field in the same feed's response, not just
    inferred from the adaptor's source.
    """
    log("Step 4/4: building cube pool index ...")
    index: dict = {}
    try:
        resp = _SESSION.get(CUBE_POOLS_URL, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        pools = payload.get("pools") or []
    except requests.RequestException as e:
        log(f"  cube pools fetch failed: {e}")
        return index

    for p in pools:
        address = str(p.get("pool") or "").strip()
        mints = [m for m in (p.get("underlyingTokens") or []) if m]
        if not (address and mints):
            continue
        key = frozenset(mints) if len(mints) == 2 else mints[0]
        tvl = float(p.get("tvlUsd") or 0)
        existing = index.get(key)
        if existing is None or tvl > existing[1]:
            index[key] = (address, tvl)

    log(f"Step 4/4: cube index built - {len(index)} key(s) indexed.")
    return index


def _fetch_sentora_index() -> tuple[dict, dict]:
    """
    Pull Sentora's own vaults API and index Solana-side vaults by
    (deposit mint, vault name lowercased) -> vault address, plus a
    mint-only fallback keeping the highest-TVL vault per mint.

    Solana scope: read against the adaptor's own source, its Solana
    coverage is Kamino-managed vaults only (v.protocol === 'kamino') -
    every other protocol Sentora tracks on this feed is either
    Ethereum-side or explicitly skipped by the adaptor itself (Morpho
    and Euler v2 vaults are dropped since those are already tracked by
    their own DefiLlama adaptors). This resolver mirrors that same
    filter rather than trying to resolve pools the live DefiLlama data
    will never actually contain for this project.

    `vault.address` here is a real on-chain Kamino vault address, not a
    derived one - same status as the vault addresses gmtrade/cube hand
    back directly. The (mint, name) index exists because a single
    deposit mint can back more than one Sentora/Kamino vault (different
    strategies over the same asset), matching the same isolated-market
    ambiguity Kamino Lend and Save already handle above - DefiLlama's
    own `poolMeta` for this project is set to `vault.name`, so it lines
    up directly with the "Pool Meta" column already captured in
    fetch_solana_pools().
    """
    log("Step 4/4: building sentora pool index ...")
    by_name: dict = {}
    by_mint: dict = {}
    try:
        resp = _SESSION.get(SENTORA_VAULTS_URL, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        vaults = payload if isinstance(payload, list) else (payload.get("vaults") or [])
    except requests.RequestException as e:
        log(f"  sentora vaults fetch failed: {e}")
        return by_name, by_mint

    for v in vaults:
        if v.get("status") != "ACTIVE" or v.get("protocol") != "kamino":
            continue
        mint = (v.get("depositToken") or {}).get("address")
        address = v.get("address")
        name = (v.get("name") or "").strip().lower()
        tvl = float((v.get("analytics") or {}).get("tvlUsd") or 0)
        if not (mint and address):
            continue

        if name:
            by_name[(mint, name)] = address

        existing = by_mint.get(mint)
        if existing is None or tvl > existing[1]:
            by_mint[mint] = (address, tvl)

    log(
        f"Step 4/4: sentora index built - {len(by_name)} (mint, vault name) pair(s), "
        f"{len(by_mint)} mint(s) fallback."
    )
    return by_name, by_mint


def _fetch_yo_protocol_index() -> tuple[dict, dict]:
    """
    Pull yo.xyz's own Solana vault-stats API and index by (asset mint,
    vault name lowercased) -> vault address, plus a mint-only fallback.

    `vault.contracts.vaultAddress` is the real on-chain vault address -
    this is exactly the value the adaptor's own source uses as its
    `pool:` field for Solana rows, just re-derived here from
    underlyingTokens instead of trusted from Pool ID (see the module
    warning at the top of this file for why that distinction matters).

    Fallback caveat: this endpoint doesn't expose a USD TVL figure
    directly (only raw token units in `tvl.raw`, which isn't comparable
    across vaults without a price lookup this resolver doesn't do) - so
    unlike most other index-built resolvers here, the mint-only fallback
    just keeps the first vault seen for a given mint rather than picking
    a highest-TVL one. Same situation, and same tradeoff, as Save's
    mint-only fallback above.
    """
    log("Step 4/4: building yo-protocol pool index ...")
    by_name: dict = {}
    by_mint: dict = {}
    try:
        resp = _SESSION.get(YO_PROTOCOL_SOLANA_URL, timeout=30)
        resp.raise_for_status()
        vaults = (resp.json().get("data")) or []
    except requests.RequestException as e:
        log(f"  yo-protocol vaults fetch failed: {e}")
        return by_name, by_mint

    for v in vaults:
        mint = (v.get("asset") or {}).get("address")
        address = (v.get("contracts") or {}).get("vaultAddress")
        name = (v.get("name") or "").strip().lower()
        if not (mint and address):
            continue

        if name:
            by_name[(mint, name)] = address
        by_mint.setdefault(mint, address)

    log(
        f"Step 4/4: yo-protocol index built - {len(by_name)} (mint, vault name) pair(s), "
        f"{len(by_mint)} mint(s) fallback."
    )
    return by_name, by_mint


# --- Hardcoded pool addresses ---------------------------------------
#
# Only for protocols where the pool set is a small fixed constant taken
# straight from the adaptor's own source - see the big warning at the
# top of this file for why Pool ID itself can never be used for this.

# Single Solana pool, matched on Project alone. The mint IS the
# yield-bearing asset for every one of these - no separate pool
# contract exists to resolve to.
_HARDCODED_SINGLE_POOL: dict[str, str] = {
    "binance-staked-sol": "BNso1VUJnh4zcfpZa6986Ea66P6TCp59hvtNJ8b1X85",
    "jito-liquid-staking": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
    "jupiter-staked-sol": "jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v",
    "drift-staked-sol": "Dso1bDeDjCQxTrWHqUUi63oBvV7Mdm6WaobLbQ7gnPQ",
    "marinade-liquid-staking": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "sanctum-infinity": "5oVNBeEEQvYi1cX3ir8Dx5n1P7pdxydbGF2X4TxVusJm",
    "phantom-sol": "pSo1f9nQXWgXibFtKf7NWYxb5enAM4qfP6UJSiXRQfL",
    "doublezero-staked-sol": "Gekfj7SL2fVpTDxJZmeC46cTYxinjB6gkAnb6EGT6mnn",
    "jpool": "7Q2afV64in6N6SeZsAAB81TJzwDoD6zpqmHkzi9Dcavn",
    "the-vault-liquid-staking": "vSoLxydx6akxyMD9XEcPvGYNGq6Nn66oqVb3UkGkei7",
    "bybit-staked-sol": "Bybit2vBJGhPF52GBdNaQfUJ6ZpThSgHBobjWZpLPb4B",
    "blazestake": "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",
    "helius-staked-sol": "he1iusmfkpAdwvxLNGV8Y1iSbj4rUy6yMhEA3fotn9A",
    "dfdv-staked-sol": "sctmB7GPi5L2Q5G9tUSzXvhZ4YiDMEGcRov9KfArQpx",
    # These two have a real, separate stake-pool program account that
    # DefiLlama's own adaptor doesn't use as `pool` (it uses the mint) -
    # matching that choice here for consistency. Program accounts noted
    # in case deposit-contract granularity is wanted instead:
    #   jagpool-staked-sol:        jagEdDepWUgexiu4jxojcRWcVKKwFqgZBBuAoGu2BxM
    #   stkesol-by-sol-strategies: StKeDUdSu7jMSnPJ1MPqDnk3RdEwD2QbJaisHMebGhw
    "jagpool-staked-sol": "jag58eRBC1c88LaAsRPspTMvoKJPbnzw9p9fREzHqyV",
    "stkesol-by-sol-strategies": "stke7uu3fXHsGqKVVjKnkmj65LRPVrqr4bLG2SJg7rh",
    "onre": "5Y8NV33Vv7WbnLfq3zBcKSdYPrk7g2KoiQoe7M2tcxp5",
    "blackrock-buidl": "GyWgeqpy5GueU2YbkE8xqUeVEokCMMCEeUrfbtMw6phr",
    "apollo-diversified-credit-securitize-fund": "FubtUcvhSCr3VPXEcxouoQjKQ7NWTCzXyECe76B7L3f8",
    "vaneck-treasury-fund": "34mJztT9am2jybSukvjNqRjgJBZqHJsHnivArx1P4xy1",
    "hylo-lsts": "hy1oXYgrBW6PVcJ4s6s2FKavRdwgWTXdfE69AxT7kPT",
    "bonk-staked-sol": "BonK1YhkXEGLZzwtcvRTip3gAL9nCeQD7ppZBLXhtTs",
    "bitwise-uscc": "BTRR3sj1Bn2ZjuemgbeQ6SCtf84iXS81CS7UDTSxUCaK",
    "marginfi-lst": "LSTxxxnJzKDFSLr4dUkPcmCf5VyryEqzPLz5j4bpxFp",
    "unitas-usdu": "9iq5Q33RSiz1WcupHAQKbHBZkpn92UxBG2HfPWAZhMCa",
    # Not a mint - a hardcoded market/pool address literal baked into
    # the adaptor's own source (see module docstring). Stored here
    # without the adaptor's own "-solana" suffix.
    "credix": "66v9TQq1P7JKMiKjUZ4xxZRoZh7zyqVdEwuaEAHuE1Bx",
    # Also not a mint - no LST token exists for this protocol at all.
    # The pool value is the Solana vote-account address depositors
    # delegate stake to; rewards flow back via an off-chain lottery
    # rather than through any on-chain receipt token.
    "tramplin.io": "TRAMp1Z9EXyWQQNwNjjoNvVksMUHKioVU7ky61yNsEq",
    # LSTs added from the second adaptor batch. save-sol and laine-sol
    # each have a real, separate stake-pool program account that the
    # adaptor doesn't use as `pool` (it uses the mint) - same
    # DefiLlama-consistency choice as jagpool/stkesol above. Program
    # accounts noted here in case deposit-contract granularity is ever
    # wanted instead:
    #   save-sol:  SAVEY1fVMBeRVo9V9rgEz8ENTvHreftd3QgpAKBDFV4
    #   laine-sol: 2qyEeSAWKfU18AFthrF7JA8z8ZCi1yt76Tqs917vwQTV
    "stronghold-staked-sol": "strng7mqqc1MBJJV6vMzYbEqnwVGvKKGKedeCvtktWA",
    "save-sol": "SAVEDpx3nFNdzG3ymJfShYnrBuYy7LtQEABZQ3qtTFt",
    "lantern-staked-sol": "LnTRntk2kTfWEY6cVB8K9649pgJbt6dJLS1Ns1GZCWg",
    "pico-staked-sol": "picobAEvs6w7QEknPce34wAE4gknZA9v5tTonnmHYdX",
    "laine-sol": "LAinEtNLgpmCP9Rvsf5Hn8W6EhNiKLZQti1xfWMLy6X",
    "starke-staked-sol": "EPCz5LK372vmvCkZH3HgSuGNKACJJwwxsofW6fypCPZL",
    # RWA / stablecoin single-pool tokens, same "mint is the asset, no
    # separate pool contract" situation. Solana's invesco-ustb and
    # openeden-tbill pools are each a single mint per the adaptor's own
    # source. openeden-usdo's Solana leg is cUSDO only (USDO itself has
    # no Solana deployment) - also a single mint, no wrapper needed.
    "invesco-ustb": "CCz3SGVziFeLYk2xfEstkiqJfYkjaSWb2GCABYsVcjo2",
    "openeden-tbill": "4MmJVdwYN8LwvbGeCowYjSx7KoEi6BJWg8XXnW4fDDp6",
    "openeden-usdo": "BnANu5CtUogLqcvBNByJuwaRvRxNtVuDcAytwjsUUtqs",
}

# Multiple Solana pools per project, matched on (Project, Symbol).
# Symbol is compared case-insensitively since DefiLlama's live payload
# doesn't guarantee casing consistency with the adaptor's own literal.
HASTRA_WYLDS_MINT = "8fr7WGTVFszfyNWRMXj6fRjZZAnDwmXwEpCrtzmUkdih"
HASTRA_PRIME_MINT = "3b8X44fLF9ooXaUm3hhSgjpmVs6rZZ3pPoGnGahc3Uu7"
HASTRA_PRIME_VAULT = "FvkbfMm98jefJWrqkvXvsSZ9RFaRBae8k6c1jaYA5vY3"

_HARDCODED_MULTI_POOL: dict[tuple[str, str], str] = {
    # hastra: wYLDS has no pool contract -> its own mint. PRIME has no
    # pool contract either, but PRIME_VAULT is the account depositors
    # actually interact with, so that's used instead of the PRIME mint.
    ("hastra", "WYLDS"): HASTRA_WYLDS_MINT,
    ("hastra", "PRIME"): HASTRA_PRIME_VAULT,
    ("ondo-yield-assets", "USDY"): "A1KLoBrKBde8Ty9qtNQUtq3C2ortoC3u7twggz7sEto6",
    ("ondo-yield-assets", "OUSG"): "i7u4r16TcsJTgq1kAG8opmVZyVnAKBwLKu6ZPMwzxNc",
    ("kyros", "KYSOL"): "kySo1nETpsZE2NWe5vj2C64mPSciH1SppmHb4XieQ7B",
    ("kyros", "KYJTO"): "kyJtowDDACsJDm2jr3VZdpCA6pZcKAaNftQwrJ8KBQP",
}


def _resolve_hardcoded_pool_address(project: str, symbol: str) -> str | None:
    """Look up a hardcoded Pool Address by Project, then by
    (Project, Symbol) for protocols with more than one Solana pool."""
    if project in _HARDCODED_SINGLE_POOL:
        return _HARDCODED_SINGLE_POOL[project]
    key = (project, (symbol or "").strip().upper())
    return _HARDCODED_MULTI_POOL.get(key)


def fetch_pool_addresses(pools_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve "Pool Address" across every protocol with a verified free
    source (see the module docstring for the current list, and the
    warning at the top of the file about why Pool ID itself is never
    used as a source here). Everything else gets None - there is no
    verified free source for them yet.

    Ambiguity note: applies to the TVL-tiebreak index-built resolvers
    only - see module docstring.
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
    omnipair_index = None
    allbridge_index = None
    cube_index = None
    sentora_index = None
    yo_protocol_index = None

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
    omnipair_hits = 0
    allbridge_hits = 0
    cube_hits = 0
    sentora_hits = 0
    sentora_name_hits = 0
    yo_protocol_hits = 0
    yo_protocol_name_hits = 0
    hardcoded_hits: dict[str, int] = {}

    raydium_total = int(pools_df["Project"].str.lower().str.contains("raydium").sum())
    log(f"Step 4/4: {raydium_total} Raydium pool(s) to check individually (this is the slow part) ...")

    for _, row in pools_df.iterrows():
        pool_id = row["Pool ID"]
        project = str(row["Project"]).lower()
        symbol = str(row.get("Symbol") or "")
        underlying = row.get("Underlying Tokens") or ""
        mints = [t.strip() for t in underlying.split(",") if t.strip()]
        pool_meta = str(row.get("Pool Meta") or "").strip().lower()

        address = None

        # Hardcoded protocols first - cheapest check, no network call,
        # and doesn't depend on mints/underlyingTokens at all.
        hardcoded = _resolve_hardcoded_pool_address(project, symbol)
        if hardcoded:
            address = hardcoded
            hardcoded_hits[project] = hardcoded_hits.get(project, 0) + 1

        elif project == "omnipair" and len(mints) == 2:
            if omnipair_index is None:
                try:
                    omnipair_index = _fetch_omnipair_index()
                except requests.RequestException as e:
                    log(f"  omnipair index build failed: {e}")
                    omnipair_index = {}
            address = omnipair_index.get(frozenset(mints))
            if address:
                omnipair_hits += 1

        elif project == "allbridge-classic" and len(mints) == 1:
            if allbridge_index is None:
                try:
                    allbridge_index = _fetch_allbridge_classic_index()
                except requests.RequestException as e:
                    log(f"  allbridge-classic index build failed: {e}")
                    allbridge_index = {}
            address = allbridge_index.get(mints[0])
            if address:
                allbridge_hits += 1

        elif project == "cube" and len(mints) in (1, 2):
            if cube_index is None:
                try:
                    cube_index = _fetch_cube_index()
                except requests.RequestException as e:
                    log(f"  cube index build failed: {e}")
                    cube_index = {}
            key = frozenset(mints) if len(mints) == 2 else mints[0]
            match = cube_index.get(key)
            address = match[0] if match else None
            if address:
                cube_hits += 1

        elif project == "sentora" and len(mints) == 1:
            if sentora_index is None:
                try:
                    sentora_index = _fetch_sentora_index()
                except requests.RequestException as e:
                    log(f"  sentora index build failed: {e}")
                    sentora_index = ({}, {})
            by_name, by_mint = sentora_index
            if pool_meta:
                address = by_name.get((mints[0], pool_meta))
                if address:
                    sentora_name_hits += 1
            if not address:
                match = by_mint.get(mints[0])
                address = match[0] if match else None
            if address:
                sentora_hits += 1

        elif project == "yo-protocol" and len(mints) == 1:
            if yo_protocol_index is None:
                try:
                    yo_protocol_index = _fetch_yo_protocol_index()
                except requests.RequestException as e:
                    log(f"  yo-protocol index build failed: {e}")
                    yo_protocol_index = ({}, {})
            by_name, by_mint = yo_protocol_index
            if pool_meta:
                address = by_name.get((mints[0], pool_meta))
                if address:
                    yo_protocol_name_hits += 1
            if not address:
                address = by_mint.get(mints[0])
            if address:
                yo_protocol_hits += 1

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

    hardcoded_summary = " | ".join(
        f"{project} {count} matched" for project, count in sorted(hardcoded_hits.items())
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
        f"omnipair {omnipair_hits} matched | "
        f"allbridge-classic {allbridge_hits} matched | "
        f"cube {cube_hits} matched | "
        f"sentora {sentora_hits} matched ({sentora_name_hits} via exact vault-name match) | "
        f"yo-protocol {yo_protocol_hits} matched ({yo_protocol_name_hits} via exact vault-name match)"
        + (f" | {hardcoded_summary}" if hardcoded_summary else "")
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
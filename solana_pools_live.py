"""
solana_pools_live.py

Pure in-memory run: fetch Solana pools from DefiLlama, enrich with
project Image/App Link (also from DefiLlama, live), print the result.
Nothing is written to disk... except see the TEMP / DEV-ONLY block below.

Note: "Pool Address" column is present (matches the target output
shape) but always NULL/None here. No public API exposes on-chain pool
addresses, so there is no live source to fill it from yet. Wire the
real source into `fetch_pool_addresses()` below when it's ready —
that function is the only thing that needs to change.

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
    allowed_methods=["GET"],
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
    One-time bulk fetch beats one HTTP call per pool.
    """
    log("Step 3/4: building Orca pool index (bulk fetch, paginated) ...")
    index = {}
    cursor = None
    pages = 0
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        resp = _SESSION.get(ORCA_POOLS_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        pools = payload.get("data", [])
        pages += 1

        for p in pools:
            mint_a = p.get("tokenA", {}).get("address") or p.get("tokenMintA")
            mint_b = p.get("tokenB", {}).get("address") or p.get("tokenMintB")
            address = p.get("address")
            tvl = float(p.get("tvlUsdc") or p.get("tvl") or 0)
            if not (mint_a and mint_b and address):
                continue
            key = frozenset((mint_a, mint_b))
            existing = index.get(key)
            if existing is None or tvl > existing[1]:
                index[key] = (address, tvl)

        cursor = (payload.get("meta") or {}).get("next")
        if not cursor:
            break

    log(f"Step 3/4: Orca index built - {len(index)} mint pairs across {pages} page(s).")
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


def fetch_pool_addresses(pools_df: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve "Pool Address" for Raydium and Orca pools only, matched by
    underlying token mint pair. Every other project gets None - there is
    no verified free source for them yet.

    Ambiguity note: a mint pair can have more than one pool (different
    fee tiers, AMM vs CLMM/Whirlpool). This takes the highest-TVL/
    liquidity match rather than guaranteeing a unique correct one.
    """
    log("Step 4/4: resolving Pool Address for Raydium/Orca pools ...")
    results = []
    orca_index = None  # lazy-built only if an Orca pool is actually present
    raydium_calls = 0
    raydium_hits = 0
    raydium_failures = 0
    orca_hits = 0

    raydium_total = int(pools_df["Project"].str.lower().str.contains("raydium").sum())
    log(f"Step 4/4: {raydium_total} Raydium pool(s) to check individually (this is the slow part) ...")

    for _, row in pools_df.iterrows():
        pool_id = row["Pool ID"]
        project = str(row["Project"]).lower()
        underlying = row.get("Underlying Tokens") or ""
        mints = [t.strip() for t in underlying.split(",") if t.strip()]

        address = None
        if len(mints) == 2:
            if "raydium" in project:
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
            elif "orca" in project:
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

        results.append({"Pool ID": pool_id, "Pool Address": address})

    log(
        f"Step 4/4: done - Raydium {raydium_hits}/{raydium_calls} matched "
        f"({raydium_failures} request failures), Orca {orca_hits} matched."
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

    # Column order matches the target output shape exactly, including
    # "Pool Address" right after "Protocol" even though it's NULL for now.
    display_cols = {
        "Project": "Protocol",
        "Pool Address": "Pool Address",
        "Symbol": "Asset",
        "APY": "APY",
        "APY Base": "Base APY",
        "APY Reward": "Reward APY",
        "TVL USD": "TVL ($)",
        "Reward Tokens": "Reward Tokens",
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
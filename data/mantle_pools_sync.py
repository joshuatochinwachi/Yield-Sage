"""
Fetches Solana DeFi pools from DefiLlama, writes to CSV.
This is a legacy data utility script — the live fetcher (agent/fetcher.py) now
pulls Solana pool data directly from the DefiLlama API on an hourly schedule.
"""

import csv
import io
import json
import time
import logging
from typing import Optional

import requests

# ─── CONFIG ───────────────────────────────────────────────────────────────────

LLAMA_URL    = "https://yields.llama.fi/pools"
OUTPUT_CSV   = "solana_pools.csv"
CHAIN_FILTER = "Solana"

HEADERS = [
    "Project", "Symbol", "APY", "APY Base", "APY Reward",
    "Reward Tokens", "Pool ID", "APY % 1D", "APY % 7D", "APY % 30D",
    "Stablecoin", "APY Base 7D", "TVL USD",
    "Underlying Token 1", "Underlying Token 2",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ─── FETCH + PARSE ────────────────────────────────────────────────────────────

def fetch_solana_pools() -> Optional[list[list]]:
    """Fetch all pools from DefiLlama and return only Solana rows."""
    for attempt in range(2):
        try:
            resp = requests.get(LLAMA_URL, timeout=30)
        except requests.RequestException as e:
            log.error("Request failed: %s", e)
            return None

        if resp.status_code == 429:
            if attempt == 0:
                log.warning("Rate limited — waiting 10s and retrying...")
                time.sleep(10)
                continue
            log.error("Still rate limited after retry. Aborting.")
            return None

        if resp.status_code != 200:
            log.error("DefiLlama API error: %s", resp.status_code)
            return None

        return parse_pools(resp.text)

    return None


def parse_pools(response_text: str) -> Optional[list[list]]:
    """Parse raw JSON and extract Solana pools."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        log.error("JSON parse failed: %s", e)
        return None

    pools = data.get("data", [])
    solana = [p for p in pools if p.get("chain") == CHAIN_FILTER]

    if not solana:
        log.warning("No Solana pools found in response.")
        return None

    rows = []
    for p in solana:
        tokens = p.get("underlyingTokens") or []
        reward_tokens = p.get("rewardTokens") or []
        rows.append([
            p.get("project", ""),
            p.get("symbol", ""),
            p.get("apy", 0),
            p.get("apyBase", 0),
            p.get("apyReward", 0),
            ", ".join(reward_tokens),
            p.get("pool", ""),
            p.get("apyPct1D", 0),
            p.get("apyPct7D", 0),
            p.get("apyPct30D", 0),
            p.get("stablecoin", False),
            p.get("apyBase7d", 0),
            p.get("tvlUsd", 0),
            tokens[0] if len(tokens) > 0 else "",
            tokens[1] if len(tokens) > 1 else "",
        ])

    log.info("Parsed %d Solana pools.", len(rows))
    return rows

# ─── CSV WRITER ───────────────────────────────────────────────────────────────

def write_pools_to_csv(rows: list[list], path: str = OUTPUT_CSV) -> None:
    """Write rows (with headers) to a local CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    log.info("CSV written: %s (%d rows)", path, len(rows))

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def sync_solana_pools() -> None:
    log.info("Starting Solana pools sync...")

    rows = fetch_solana_pools()
    if not rows:
        log.error("Fetch failed — aborting sync.")
        return

    write_pools_to_csv(rows)
    log.info("Sync complete. %d pools written to CSV.", len(rows))


if __name__ == "__main__":
    sync_solana_pools()
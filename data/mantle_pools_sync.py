"""
Fetches Mantle DeFi pools from DeFiLlama, writes to CSV, and uploads to Dune.
Equivalent to the Google Apps Script version.

Note: The full data isn't sourced from here alone.. I applied on-chain analytic skills to query and 
collect data from multiple sources (dune tables included) and then aggregate it into tables on Dune.
"""

import csv
import io
import json
import time
import logging
from typing import Optional

import requests

# ─── CONFIG ───────────────────────────────────────────────────────────────────

DUNE_API_KEY = " Insert API KEY here "
DUNE_TABLE_NAME = "protocol_apy"
LLAMA_URL       = "https://yields.llama.fi/pools"
OUTPUT_CSV      = "mantle_pools.csv"

HEADERS = [
    "Project", "Symbol", "APY", "APY Base", "APY Reward",
    "Reward Tokens", "Pool ID", "APY % 1D", "APY % 7D", "APY % 30D",
    "Stablecoin", "APY Base 7D", "TVL USD",
    "Underlying Token 1", "Underlying Token 2",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

# ─── FETCH + PARSE ────────────────────────────────────────────────────────────

def fetch_mantle_pools() -> Optional[list[list]]:
    """Fetch all pools from DeFiLlama and return only Mantle rows."""
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
            log.error("DeFiLlama API error: %s", resp.status_code)
            return None

        return parse_pools(resp.text)

    return None


def parse_pools(response_text: str) -> Optional[list[list]]:
    """Parse raw JSON and extract Mantle pools."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        log.error("JSON parse failed: %s", e)
        return None

    pools = data.get("data", [])
    mantle = [p for p in pools if p.get("chain") == "Mantle"]

    if not mantle:
        log.warning("No Mantle pools found in response.")
        return None

    rows = []
    for p in mantle:
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

    log.info("Parsed %d Mantle pools.", len(rows))
    return rows

# ─── CSV WRITER ───────────────────────────────────────────────────────────────

def write_pools_to_csv(rows: list[list], path: str = OUTPUT_CSV) -> None:
    """Write rows (with headers) to a local CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    log.info("CSV written: %s (%d rows)", path, len(rows))


def rows_to_csv_string(rows: list[list]) -> str:
    """Serialise headers + rows to a CSV string for Dune upload."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    return buf.getvalue()

# ─── DUNE UPLOAD ──────────────────────────────────────────────────────────────

def push_to_dune(rows: list[list]) -> None:
    """Upload pool data to Dune via the CSV upload endpoint."""
    csv_string = rows_to_csv_string(rows)

    payload = {
        "table_name":  DUNE_TABLE_NAME,
        "description": "Current APY of DeFi protocols on Mantle blockchain via DeFiLlama",
        "data":        csv_string,
        "is_private":  False,
    }

    resp = requests.post(
        "https://api.dune.com/api/v1/table/upload/csv",
        headers={
            "X-Dune-Api-Key": DUNE_API_KEY,
            "Content-Type":   "application/json",
        },
        json=payload,
        timeout=30,
    )

    log.info("Dune upload: %s — %s", resp.status_code, resp.text)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def sync_mantle_pools() -> None:
    log.info("Starting Mantle pools sync...")

    rows = fetch_mantle_pools()
    if not rows:
        log.error("Fetch failed — aborting sync.")
        return

    write_pools_to_csv(rows)
    push_to_dune(rows)

    log.info("Sync complete. %d pools pushed to Dune.", len(rows))


if __name__ == "__main__":
    sync_mantle_pools()
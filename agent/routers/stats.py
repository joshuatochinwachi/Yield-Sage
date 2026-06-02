"""
routers/stats.py
─────────────────
Public dashboard overview stats endpoint.

GET /api/stats/overview — Summary numbers for the dashboard header cards
"""

import os
import logging
from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["Stats"])

_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_db: Client | None = create_client(_url, _key) if _url and _key else None


def _db_or_503():
    if not _db:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return _db


@router.get("/overview")
async def get_overview_stats():
    """
    Returns headline numbers for the dashboard stat cards:
    - Total protocols tracked
    - Total yield snapshots in DB
    - Best current APY across all protocols
    - Total active paper trades across all users
    - Total recommendations generated
    - Last data refresh time
    """
    db = _db_or_503()
    try:
        # 1. Protocol count
        proto_res = db.table("protocols").select("id", count="exact").eq("is_active", True).execute()
        protocol_count = proto_res.count or len(proto_res.data or [])

        # 2. Total snapshots
        snap_count_res = db.table("yield_snapshots").select("id", count="exact").execute()
        snapshot_count = snap_count_res.count or len(snap_count_res.data or [])

        # 3. Best current APY — latest snapshot per protocol, take the max
        all_protos = db.table("protocols").select("id").eq("is_active", True).execute().data
        best_apy = 0.0
        last_fetched = None

        if all_protos:
            pids = [p["id"] for p in all_protos]
            snap_res = (
                db.table("yield_snapshots")
                .select("protocol_id, apy, fetched_at")
                .in_("protocol_id", pids)
                .order("fetched_at", desc=True)
                .limit(len(pids) * 5)
                .execute()
            )

            seen = set()
            for row in snap_res.data:
                pid = row["protocol_id"]
                if pid not in seen:
                    seen.add(pid)
                    apy = row.get("apy") or 0
                    if apy > best_apy:
                        best_apy = float(apy)
                    if last_fetched is None:
                        last_fetched = row.get("fetched_at")

        # 4. Active paper trades count
        trades_res = db.table("paper_trades").select("id", count="exact").eq("status", "active").execute()
        active_trades = trades_res.count or len(trades_res.data or [])

        # 5. Total recommendations
        recs_res = db.table("recommendations").select("id", count="exact").execute()
        recommendation_count = recs_res.count or len(recs_res.data or [])

        # 6. Recommendations with on-chain proof
        try:
            onchain_res = (
                db.table("recommendations")
                .select("on_chain_tx_hash")
                .order("created_at", desc=True)
                .limit(500)
                .execute()
            )
            onchain_count = sum(
                1 for r in (onchain_res.data or [])
                if r.get("on_chain_tx_hash")
            )
        except Exception:
            onchain_count = 0

        return {
            "protocols_tracked": protocol_count,
            "total_snapshots": snapshot_count,
            "best_apy": round(best_apy, 2),
            "active_paper_trades": active_trades,
            "recommendations_generated": recommendation_count,
            "recommendations_on_chain": onchain_count,
            "last_data_refresh": last_fetched,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[stats/overview] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch overview stats.")

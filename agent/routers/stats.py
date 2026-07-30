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
        # 1. Fetch active protocols and construct a lookup mapping
        all_protos = db.table("protocols").select("id, name").eq("is_active", True).execute().data
        
        # 2. Total snapshots in database
        snap_count_res = db.table("yield_snapshots").select("id", count="exact").execute()
        snapshot_count = snap_count_res.count or len(snap_count_res.data or [])

        # 3. Comprehensive yields metrics (TVL, best/avg/median APY, pool count, unique protocols)
        best_apy = 0.0
        total_tvl = 0.0
        apy_list = []
        pool_count = 0
        protocol_count = 0
        last_fetched = None

        # Fetch latest snapshots for active protocols using joined query (no URL param bloat)
        snap_res = (
            db.table("yield_snapshots")
            .select("protocol_id, apy, tvl_usd, fetched_at, protocols!inner(id, name, is_active)")
            .eq("protocols.is_active", True)
            .order("fetched_at", desc=True)
            .limit(5000)
            .execute()
        )

        seen_pids = set()
        seen_proto_names = set()
        for row in (snap_res.data or []):
            proto = row.get("protocols") or {}
            pid = row.get("protocol_id") or proto.get("id")
            if pid and pid not in seen_pids:
                seen_pids.add(pid)
                apy = row.get("apy") or 0.0
                tvl = row.get("tvl_usd") or 0.0
                
                total_tvl += float(tvl)
                apy_list.append(float(apy))
                
                if apy > best_apy:
                    best_apy = float(apy)
                if last_fetched is None:
                    last_fetched = row.get("fetched_at")
                
                p_name = proto.get("name")
                if p_name:
                    seen_proto_names.add(p_name)

        pool_count = len(seen_pids)
        protocol_count = len(seen_proto_names)

        # 4. Calculate average and median APY
        average_apy = sum(apy_list) / len(apy_list) if apy_list else 0.0
        median_apy = 0.0
        if apy_list:
            sorted_apys = sorted(apy_list)
            n = len(sorted_apys)
            if n % 2 == 1:
                median_apy = sorted_apys[n // 2]
            else:
                median_apy = (sorted_apys[n // 2 - 1] + sorted_apys[n // 2]) / 2.0

        # 5. Active paper trades count
        trades_res = db.table("paper_trades").select("id", count="exact").eq("status", "active").execute()
        active_trades = trades_res.count or len(trades_res.data or [])

        # 6. Total recommendations
        recs_res = db.table("recommendations").select("id", count="exact").execute()
        recommendation_count = recs_res.count or len(recs_res.data or [])

        # 7. Recommendations with on-chain proof
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
            "pools_tracked": pool_count,
            "total_tvl": round(total_tvl, 2),
            "average_apy": round(average_apy, 2),
            "median_apy": round(median_apy, 2),
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

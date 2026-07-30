"""
routers/yields.py
─────────────────
Public endpoints for live yield snapshot data.

GET /api/yields/latest       — Latest snapshot per active protocol (filterable by risk_tag)
GET /api/yields/leaderboard  — Sorted leaderboard (APY desc), with risk filter + pagination
GET /api/yields/history/{slug} — Time-series snapshots for one protocol (default 30 days)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from supabase import create_client, Client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/yields", tags=["Yields"])

# ── Supabase admin client ─────────────────────────────────────────────────────
_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_db: Client | None = create_client(_url, _key) if _url and _key else None


def _db_or_503():
    if not _db:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return _db


# ── GET /api/yields/latest ────────────────────────────────────────────────────
@router.get("/latest")
async def get_latest_yields(
    risk_tag: Optional[str] = Query(None, description="Filter by risk_tag: stable | moderate | aggressive"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Returns the most recent yield snapshot for every active protocol.
    Optionally filter by risk_tag. Ordered by APY descending.
    """
    db = _db_or_503()
    try:
        # Query yield_snapshots directly with joined protocol info (avoids URL parameter overflow)
        snap_res = (
            db.table("yield_snapshots")
            .select("*, protocols!inner(id, slug, name, pool_name, pool_address, risk_tag, chain, image_url, app_link, is_active)")
            .eq("protocols.is_active", True)
            .order("fetched_at", desc=True)
            .limit(2000)
            .execute()
        )

        seen = set()
        latest = []
        for row in (snap_res.data or []):
            proto = row.get("protocols") or {}
            pid = row.get("protocol_id") or proto.get("id")
            
            # Apply risk_tag filter if requested
            if risk_tag and (proto.get("risk_tag") or "").lower() != risk_tag.lower():
                continue

            if pid and pid not in seen:
                seen.add(pid)
                latest.append({
                    **row,
                    "protocol": proto,
                })

        # Sort by APY descending
        latest.sort(key=lambda x: (x.get("apy") or 0), reverse=True)
        latest = latest[:limit]

        return {
            "data": latest,
            "count": len(latest),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[yields/latest] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest yields.")


# ── GET /api/yields/leaderboard ───────────────────────────────────────────────
@router.get("/leaderboard")
async def get_leaderboard(
    risk_tag: Optional[str] = Query(None, description="Filter: stable | moderate | aggressive"),
    search: Optional[str] = Query(None, description="Filter by protocol name or asset"),
    min_tvl: Optional[float] = Query(None, description="Filter by minimum TVL in USD"),
    min_apy: Optional[float] = Query(None, description="Filter by minimum APY in percent (e.g. 5.5 for 5.5%)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
):
    """
    Paginated leaderboard of all active protocols, ranked by TVL descending.
    Supports filtering by risk_tag, search string, min_tvl, and min_apy.
    """
    db = _db_or_503()
    try:
        # Single joined query on yield_snapshots + protocols (no URL query param bloat)
        snap_res = (
            db.table("yield_snapshots")
            .select("protocol_id, apy, base_apy, reward_apy, reward_tokens, apy_1d, apy_7d, apy_30d, tvl_usd, asset, fetched_at, protocols!inner(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link, is_active)")
            .eq("protocols.is_active", True)
            .order("fetched_at", desc=True)
            .limit(2000)
            .execute()
        )

        seen = set()
        rows = []
        for row in (snap_res.data or []):
            proto = row.get("protocols") or {}
            pid = row.get("protocol_id") or proto.get("id")

            if risk_tag and (proto.get("risk_tag") or "").lower() != risk_tag.lower():
                continue

            if pid and pid not in seen:
                seen.add(pid)

                # Filter by search term
                if search:
                    search_term = search.lower()
                    p_name = (proto.get("name") or "").lower()
                    p_pool = (proto.get("pool_name") or "").lower()
                    p_asset = (row.get("asset") or "").lower()
                    if (search_term not in p_name and 
                        search_term not in p_pool and 
                        search_term not in p_asset):
                        continue

                # Filter by min_tvl
                tvl_val = row.get("tvl_usd")
                if min_tvl is not None:
                    if tvl_val is None or tvl_val < min_tvl:
                        continue

                # Filter by min_apy
                apy_val = row.get("apy")
                if min_apy is not None:
                    if apy_val is None or apy_val < min_apy:
                        continue

                rows.append({
                    "rank": 0,
                    "protocol_id": pid,
                    "slug": proto.get("slug"),
                    "name": proto.get("name"),
                    "pool_name": proto.get("pool_name"),
                    "pool_address": proto.get("pool_address"),
                    "risk_tag": proto.get("risk_tag"),
                    "image_url": proto.get("image_url"),
                    "app_link": proto.get("app_link"),
                    "apy": row.get("apy"),
                    "base_apy": row.get("base_apy"),
                    "reward_apy": row.get("reward_apy"),
                    "reward_tokens": row.get("reward_tokens"),
                    "apy_1d": row.get("apy_1d"),
                    "apy_7d": row.get("apy_7d"),
                    "apy_30d": row.get("apy_30d"),
                    "tvl_usd": tvl_val,
                    "asset": row.get("asset"),
                    "fetched_at": row.get("fetched_at"),
                    "protocol": proto,
                })

        # Sort by TVL descending and assign ranks
        rows.sort(key=lambda x: (x.get("tvl_usd") or 0), reverse=True)
        for i, row in enumerate(rows):
            row["rank"] = i + 1

        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = rows[start:end]

        return {
            "data": page_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[yields/leaderboard] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch leaderboard.")


# ── GET /api/yields/history/{slug} ───────────────────────────────────────────
@router.get("/history/{slug}")
async def get_yield_history(
    slug: str,
    days: int = Query(30, ge=1, le=90, description="Number of days of history to return"),
):
    """
    Returns hourly APY snapshots for a specific protocol over the past N days.
    Used to power the APY history chart on the dashboard.
    """
    db = _db_or_503()
    try:
        proto_res = db.table("protocols").select("id, slug, name, pool_name, pool_address, risk_tag").eq("slug", slug).limit(1).execute()
        if not proto_res.data:
            raise HTTPException(status_code=404, detail=f"Protocol '{slug}' not found.")

        protocol = proto_res.data[0]
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        snap_res = (
            db.table("yield_snapshots")
            .select("apy, base_apy, reward_apy, tvl_usd, apy_7d, apy_30d, asset, fetched_at")
            .eq("protocol_id", protocol["id"])
            .gte("fetched_at", since)
            .order("fetched_at", desc=False)
            .execute()
        )

        return {
            "protocol": protocol,
            "days": days,
            "data": snap_res.data,
            "count": len(snap_res.data),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[yields/history/{slug}] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch yield history.")

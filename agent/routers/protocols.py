"""
routers/protocols.py
─────────────────────
Public endpoints for protocol metadata.

GET /api/protocols          — List all active protocols (filterable by risk_tag)
GET /api/protocols/{slug}   — Single protocol detail with latest snapshot
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from supabase import create_client, Client
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/protocols", tags=["Protocols"])

_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_db: Client | None = create_client(_url, _key) if _url and _key else None


def _db_or_503():
    if not _db:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return _db


# ── GET /api/protocols ────────────────────────────────────────────────────────
@router.get("")
async def list_protocols(
    risk_tag: Optional[str] = Query(None, description="Filter by risk_tag: stable | moderate | aggressive"),
    include_inactive: bool = Query(False),
):
    """
    Returns all protocols, optionally filtered by risk tier.
    Each protocol includes its most recent APY snapshot inline.
    """
    db = _db_or_503()
    try:
        q = db.table("protocols").select(
            "id, slug, name, pool_name, pool_address, risk_tag, chain, source_url, is_active, created_at"
        )
        if not include_inactive:
            q = q.eq("is_active", True)
        if risk_tag:
            q = q.eq("risk_tag", risk_tag.lower())

        protocols = q.order("name").execute().data

        if not protocols:
            return {"data": [], "count": 0}

        # Attach latest snapshot to each protocol
        protocol_ids = [p["id"] for p in protocols]
        snap_res = (
            db.table("yield_snapshots")
            .select("protocol_id, apy, tvl_usd, apy_7d, fetched_at")
            .in_("protocol_id", protocol_ids)
            .order("fetched_at", desc=True)
            .limit(len(protocol_ids) * 5)
            .execute()
        )

        snap_map = {}
        for row in snap_res.data:
            pid = row["protocol_id"]
            if pid not in snap_map:
                snap_map[pid] = row

        for p in protocols:
            p["latest_snapshot"] = snap_map.get(p["id"])

        return {"data": protocols, "count": len(protocols)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[protocols] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch protocols.")


# ── GET /api/protocols/{slug} ─────────────────────────────────────────────────
@router.get("/{slug}")
async def get_protocol(slug: str):
    """
    Returns full detail for a single protocol:
    - Metadata
    - Latest yield snapshot
    - Historical APY data (last 30 snapshots for sparkline)
    - Latest AI recommendation mentioning this protocol (if any)
    """
    db = _db_or_503()
    try:
        proto_res = db.table("protocols").select("*").eq("slug", slug).limit(1).execute()
        if not proto_res.data:
            raise HTTPException(status_code=404, detail=f"Protocol '{slug}' not found.")

        protocol = proto_res.data[0]
        pid = protocol["id"]

        # Latest snapshot
        snap_res = (
            db.table("yield_snapshots")
            .select("*")
            .eq("protocol_id", pid)
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_snapshot = snap_res.data[0] if snap_res.data else None

        # Last 30 snapshots for sparkline / chart
        history_res = (
            db.table("yield_snapshots")
            .select("apy, tvl_usd, apy_7d, apy_30d, fetched_at")
            .eq("protocol_id", pid)
            .order("fetched_at", desc=True)
            .limit(30)
            .execute()
        )
        history = list(reversed(history_res.data))  # chronological order

        # Latest recommendation for this protocol
        rec_res = (
            db.table("recommendations")
            .select("rank, risk_tag, apy_at_time, ai_reasoning, ai_model, on_chain_tx_hash, created_at")
            .eq("protocol_id", pid)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_recommendation = rec_res.data[0] if rec_res.data else None

        return {
            "protocol": protocol,
            "latest_snapshot": latest_snapshot,
            "history": history,
            "latest_recommendation": latest_recommendation,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[protocols/{slug}] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch protocol detail.")

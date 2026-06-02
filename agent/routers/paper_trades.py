"""
routers/paper_trades.py
────────────────────────
Auth-protected endpoints for paper (simulated) trading.

GET    /api/user/trades              — List all user's paper trades (active + closed)
POST   /api/user/trades              — Open a new paper trade
PUT    /api/user/trades/{trade_id}/close — Close an active trade
DELETE /api/user/trades/{trade_id}   — Hard delete a trade record
GET    /api/user/trades/{trade_id}   — Single trade detail with live P&L
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from supabase import create_client, Client
from datetime import datetime

from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/trades", tags=["Paper Trades"])

_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_db: Client | None = create_client(_url, _key) if _url and _key else None


def _db_or_503():
    if not _db:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return _db


# ── Pydantic models ───────────────────────────────────────────────────────────

class OpenTradeRequest(BaseModel):
    protocol_id: str = Field(..., description="UUID of the protocol to trade")
    simulated_investment_usd: float = Field(..., gt=0, le=10_000_000)
    entry_apy: float = Field(..., ge=0, description="APY at the time of entry (%)")


# ── Helper: compute live P&L ─────────────────────────────────────────────────

def _compute_pnl(trade: dict, current_apy: float | None) -> dict:
    """
    Computes simulated P&L metrics for a paper trade.
    Returns additional fields: current_apy, apy_delta, estimated_daily_yield_usd,
    estimated_annual_yield_usd, performance_status.
    """
    entry_apy = trade.get("entry_apy") or 0
    investment = trade.get("simulated_investment_usd") or 0
    cur_apy = current_apy or 0

    apy_delta = cur_apy - entry_apy
    daily_yield = investment * (cur_apy / 100) / 365
    annual_yield = investment * (cur_apy / 100)

    if apy_delta >= 2:
        status = "outperforming"
    elif apy_delta <= -2:
        status = "underperforming"
    else:
        status = "stable"

    return {
        "current_apy": round(cur_apy, 4),
        "apy_delta": round(apy_delta, 4),
        "estimated_daily_yield_usd": round(daily_yield, 4),
        "estimated_annual_yield_usd": round(annual_yield, 2),
        "performance_status": status,
    }


# ── GET /api/user/trades ──────────────────────────────────────────────────────
@router.get("")
async def list_trades(
    status: Optional[str] = Query(None, description="Filter: active | closed"),
    user_id: str = Depends(get_current_user),
):
    """
    Returns all paper trades for the authenticated user.
    Each trade is enriched with live current APY and P&L metrics.
    """
    db = _db_or_503()
    try:
        q = (
            db.table("paper_trades")
            .select("*, protocols(id, slug, name, pool_name, pool_address, risk_tag)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if status:
            q = q.eq("status", status.lower())

        trades = q.execute().data or []

        if not trades:
            return {"data": [], "count": 0}

        # Fetch latest APY for each unique protocol in one query
        proto_ids = list({t["protocol_id"] for t in trades})
        snap_res = (
            db.table("yield_snapshots")
            .select("protocol_id, apy, fetched_at")
            .in_("protocol_id", proto_ids)
            .order("fetched_at", desc=True)
            .limit(len(proto_ids) * 5)
            .execute()
        )

        latest_apy_map: dict = {}
        for row in snap_res.data:
            pid = row["protocol_id"]
            if pid not in latest_apy_map:
                latest_apy_map[pid] = row.get("apy")

        # Enrich each trade
        for trade in trades:
            pid = trade["protocol_id"]
            cur_apy = latest_apy_map.get(pid)
            trade["live"] = _compute_pnl(trade, cur_apy)

        return {"data": trades, "count": len(trades)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[trades GET] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch paper trades.")


# ── POST /api/user/trades ─────────────────────────────────────────────────────
@router.post("")
async def open_trade(
    body: OpenTradeRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Opens a new paper trade. Validates the protocol exists before creating.
    """
    db = _db_or_503()
    try:
        # Verify protocol exists and is active
        proto_res = db.table("protocols").select("id, name, pool_name, risk_tag").eq(
            "id", body.protocol_id
        ).eq("is_active", True).limit(1).execute()

        if not proto_res.data:
            raise HTTPException(
                status_code=404,
                detail=f"Active protocol '{body.protocol_id}' not found.",
            )

        protocol = proto_res.data[0]

        trade_payload = {
            "user_id": user_id,
            "protocol_id": body.protocol_id,
            "simulated_investment_usd": body.simulated_investment_usd,
            "entry_apy": body.entry_apy,
            "status": "active",
        }

        res = db.table("paper_trades").insert(trade_payload).execute()

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create trade record.")

        trade = res.data[0]
        trade["protocol"] = protocol

        return {
            "data": trade,
            "message": f"Paper trade opened: ${body.simulated_investment_usd:,.0f} in {protocol['name']} at {body.entry_apy}% APY.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[trades POST] {e}")
        raise HTTPException(status_code=500, detail="Failed to open paper trade.")


# ── GET /api/user/trades/{trade_id} ──────────────────────────────────────────
@router.get("/{trade_id}")
async def get_trade(
    trade_id: str,
    user_id: str = Depends(get_current_user),
):
    """
    Returns a single paper trade with full live P&L detail.
    """
    db = _db_or_503()
    try:
        res = (
            db.table("paper_trades")
            .select("*, protocols(id, slug, name, pool_name, pool_address, risk_tag)")
            .eq("id", trade_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Trade not found.")

        trade = res.data[0]

        # Fetch latest APY
        snap_res = (
            db.table("yield_snapshots")
            .select("apy, fetched_at")
            .eq("protocol_id", trade["protocol_id"])
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        cur_apy = snap_res.data[0].get("apy") if snap_res.data else None
        trade["live"] = _compute_pnl(trade, cur_apy)

        return {"data": trade}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[trades/{trade_id} GET] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trade.")


# ── PUT /api/user/trades/{trade_id}/close ────────────────────────────────────
@router.put("/{trade_id}/close")
async def close_trade(
    trade_id: str,
    user_id: str = Depends(get_current_user),
):
    """Marks an active paper trade as closed."""
    db = _db_or_503()
    try:
        existing = (
            db.table("paper_trades")
            .select("id, status")
            .eq("id", trade_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Trade not found.")

        if existing.data[0]["status"] == "closed":
            raise HTTPException(status_code=400, detail="Trade is already closed.")

        res = db.table("paper_trades").update({
            "status": "closed",
            "closed_at": datetime.utcnow().isoformat(),
        }).eq("id", trade_id).eq("user_id", user_id).execute()

        return {
            "data": res.data[0] if res.data else {"id": trade_id},
            "message": "Trade closed successfully.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[trades/{trade_id}/close] {e}")
        raise HTTPException(status_code=500, detail="Failed to close trade.")


# ── DELETE /api/user/trades/{trade_id} ───────────────────────────────────────
@router.delete("/{trade_id}")
async def delete_trade(
    trade_id: str,
    user_id: str = Depends(get_current_user),
):
    """Permanently deletes a paper trade record."""
    db = _db_or_503()
    try:
        existing = (
            db.table("paper_trades")
            .select("id")
            .eq("id", trade_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not existing.data:
            raise HTTPException(status_code=404, detail="Trade not found.")

        db.table("paper_trades").delete().eq("id", trade_id).eq("user_id", user_id).execute()

        return {"message": "Trade deleted successfully.", "trade_id": trade_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[trades/{trade_id} DELETE] {e}")
        raise HTTPException(status_code=500, detail="Failed to delete trade.")

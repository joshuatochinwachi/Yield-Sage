"""
routers/recommendations.py
───────────────────────────
Public endpoints for AI-generated yield recommendations.

GET /api/recommendations/latest   — Latest recommendation per risk tier
GET /api/recommendations/history  — Full paginated history with on-chain proof links
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from supabase import create_client, Client
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])

_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_db: Client | None = create_client(_url, _key) if _url and _key else None

# Mantle explorer base URL for on-chain proof links
_EXPLORER_BASE = "https://mantlescan.xyz/tx/"


def _db_or_503():
    if not _db:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return _db


def _build_explorer_link(tx_hash: str | None) -> str | None:
    if not tx_hash:
        return None
    return f"{_EXPLORER_BASE}{tx_hash}"


# ── GET /api/recommendations/latest ──────────────────────────────────────────
@router.get("/latest")
async def get_latest_recommendations(
    risk_tag: Optional[str] = Query(None, description="Filter by risk_tag: stable | moderate | aggressive"),
):
    """
    Returns the most recent AI recommendation for each risk tier (stable / moderate / aggressive).
    Each recommendation includes the protocol metadata and an on-chain proof link if available.
    """
    db = _db_or_503()
    try:
        tiers = (
            [risk_tag.lower()]
            if risk_tag
            else ["stable", "moderate", "aggressive"]
        )

        results = {}
        for tier in tiers:
            rec_res = (
                db.table("recommendations")
                .select(
                    "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
                    "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                    "protocols(id, slug, name, pool_name, pool_address, risk_tag)"
                )
                .eq("risk_tag", tier)
                .eq("rank", 1)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if rec_res.data:
                rec = rec_res.data[0]
                rec["explorer_url"] = _build_explorer_link(rec.get("on_chain_tx_hash"))
                results[tier] = rec
            else:
                results[tier] = None

        return {
            "data": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[recommendations/latest] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch latest recommendations.")


# ── GET /api/recommendations/history ─────────────────────────────────────────
@router.get("/history")
async def get_recommendation_history(
    risk_tag: Optional[str] = Query(None, description="Filter by risk_tag"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Full paginated history of all AI recommendations.
    Includes the on-chain verification URL and protocol metadata per row.
    This powers the /history page's public track record.
    """
    db = _db_or_503()
    try:
        q = db.table("recommendations").select(
            "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
            "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
            "protocols(id, slug, name, pool_name, pool_address, risk_tag)"
        ).order("created_at", desc=True)

        if risk_tag:
            q = q.eq("risk_tag", risk_tag.lower())

        # Supabase doesn't support server-side count easily, so we fetch with range
        offset = (page - 1) * page_size
        q = q.range(offset, offset + page_size - 1)

        res = q.execute()
        data = res.data or []

        # Attach explorer URL to each record
        for rec in data:
            rec["explorer_url"] = _build_explorer_link(rec.get("on_chain_tx_hash"))

        return {
            "data": data,
            "page": page,
            "page_size": page_size,
            "has_more": len(data) == page_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[recommendations/history] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recommendation history.")

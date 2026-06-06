"""
routers/recommendations.py
───────────────────────────
Public endpoints for AI-generated yield recommendations

GET /api/recommendations/latest   — Latest recommendation per risk tier
GET /api/recommendations/history  — Full paginated history with on-chain proof links
"""

from logger import build_recommendation_payload
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
                    "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
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
# NOTE: This MUST be registered before /{rec_id} to prevent 'history' being
# treated as a UUID path parameter by FastAPI's route matching.
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
            "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
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


# ── GET /api/recommendations/{rec_id} ─────────────────────────────────────────
# NOTE: Keep this AFTER all named routes (/history, /verify, etc.) so FastAPI
# does not swallow those paths as UUID params.
@router.get("/{rec_id}")
async def get_recommendation_by_id(rec_id: str):
    """
    Returns a single recommendation details by ID, including protocol metadata
    and on-chain proof information.
    """
    db = _db_or_503()
    try:
        rec_res = (
            db.table("recommendations")
            .select(
                "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
                "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
            )
            .eq("id", rec_id)
            .single()
            .execute()
        )

        if not rec_res.data:
            raise HTTPException(status_code=404, detail="Recommendation not found.")

        rec = rec_res.data
        rec["explorer_url"] = _build_explorer_link(rec.get("on_chain_tx_hash"))
        return {
            "data": rec
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[recommendations/get_by_id] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recommendation details.")

# ── GET /api/recommendations/verify/{tx_hash} ────────────────────────────────
@router.get("/verify/{tx_hash}")
async def verify_recommendation_by_tx(tx_hash: str):
    """
    Returns a recommendation and its canonical JSON payload to allow client-side
    verification of the on-chain SHA-256 hash.
    """
    db = _db_or_503()
    try:
        # 1. Fetch from DB using ilike for case-insensitive lookup
        tx_lower = tx_hash.lower()
        rec_res = (
            db.table("recommendations")
            .select(
                "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
                "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
            )
            .ilike("on_chain_tx_hash", tx_lower)
            .execute()
        )

        if not rec_res.data:
            # Try without 0x prefix just in case
            clean_hash = tx_lower.replace("0x", "")
            rec_res = (
                db.table("recommendations")
                .select(
                    "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
                    "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                    "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
                )
                .ilike("on_chain_tx_hash", f"%{clean_hash}%")
                .execute()
            )

        if not rec_res.data:
            raise HTTPException(status_code=404, detail="Recommendation not found for this transaction hash.")

        rec = rec_res.data[0]
        if not rec.get("protocols"):
            rec["protocols"] = {
                "id": "",
                "name": "Unknown Protocol",
                "pool_name": "Unknown Pool",
                "pool_address": ""
            }
        rec["explorer_url"] = _build_explorer_link(rec.get("on_chain_tx_hash"))

        # 2. Reconstruct the canonical JSON payload
        # Try permutations to find the exact configuration matching the stored recommendation_hash
        # (resolving issues from historic renames, TVL placeholders, or legacy formats)
        try:
            from agent.logger import build_recommendation_payload
        except ImportError:
            from logger import build_recommendation_payload

        import json
        import hashlib
        from datetime import datetime
        
        created_at_str = rec["created_at"].replace("Z", "+00:00")
        scored_at_dt = datetime.fromisoformat(created_at_str)

        # Get TVL candidates from snapshots immediately before or after created_at
        # (resolves race conditions where snapshot fetched_at is slightly after rec created_at)
        snap_res_lte = (
            db.table("yield_snapshots")
            .select("tvl_usd")
            .eq("protocol_id", rec["protocols"]["id"])
            .lte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        snap_res_gte = (
            db.table("yield_snapshots")
            .select("tvl_usd")
            .eq("protocol_id", rec["protocols"]["id"])
            .gte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=False)
            .limit(1)
            .execute()
        )
        
        tvls = [0.0]
        if snap_res_lte.data:
            tvls.append(snap_res_lte.data[0]["tvl_usd"])
        if snap_res_gte.data:
            tvls.append(snap_res_gte.data[0]["tvl_usd"])
        tvls = list(set(tvls))

        target_hash = rec["recommendation_hash"]
        matched_payload = None
        found_match = False

        # Generate candidates for renames or formatting differences
        proto_names = list(set([
            rec["protocols"]["name"],
            rec["protocols"]["name"].replace(" ", "-"),
            rec["protocols"]["name"].replace("-", " "),
            rec["protocols"]["name"].lower(),
        ]))
        
        pool_names = list(set([
            rec["protocols"]["pool_name"],
            rec["protocols"]["pool_name"].replace("/", "-"),
            rec["protocols"]["pool_name"].replace("-", "/"),
        ]))

        for proto_n in proto_names:
            for pool_n in pool_names:
                for tvl_v in tvls:
                    # Try current v1.0 schema with version/source/chain details
                    payload = build_recommendation_payload(
                        protocol_name=proto_n,
                        pool_name=pool_n,
                        pool_address=rec["protocols"]["pool_address"] or "",
                        risk_tag=rec["risk_tag"],
                        rank=rec["rank"],
                        apy_at_time=rec["apy_at_time"],
                        tvl_usd=tvl_v,
                        ai_reasoning=rec["ai_reasoning"],
                        ai_model=rec["ai_model"],
                        scored_at=scored_at_dt,
                    )
                    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                    computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                    
                    if computed_hash == target_hash:
                        matched_payload = canonical_json
                        found_match = True
                        break
                    
                    # Try legacy schema layout (pre-v1.0 schema structure)
                    legacy_payload = {
                        "scored_at": scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "risk_tag": rec["risk_tag"],
                        "rank": rec["rank"],
                        "protocol_name": proto_n,
                        "pool_name": pool_n,
                        "pool_address": (rec["protocols"]["pool_address"] or "").lower(),
                        "apy_at_time": f"{float(rec['apy_at_time']):.4f}",
                        "tvl_usd": f"{float(tvl_v):.2f}",
                        "ai_reasoning": rec["ai_reasoning"].strip(),
                        "ai_model": rec["ai_model"]
                    }
                    canonical_json = json.dumps(legacy_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                    computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                    if computed_hash == target_hash:
                        matched_payload = canonical_json
                        found_match = True
                        break
                if found_match: break
            if found_match: break

        # Fallback to standard payload if no permutation matches
        if not found_match:
            payload = build_recommendation_payload(
                protocol_name=rec["protocols"]["name"],
                pool_name=rec["protocols"]["pool_name"],
                pool_address=rec["protocols"]["pool_address"] or "",
                risk_tag=rec["risk_tag"],
                rank=rec["rank"],
                apy_at_time=rec["apy_at_time"],
                tvl_usd=real_tvl,
                ai_reasoning=rec["ai_reasoning"],
                ai_model=rec["ai_model"],
                scored_at=scored_at_dt,
            )
            matched_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

        return {
            "data": rec,
            "canonical_payload": matched_payload
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[recommendations/verify] {e}")
        raise HTTPException(status_code=500, detail="Failed to verify recommendation details.")

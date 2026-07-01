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
    search: Optional[str] = Query(None, description="Filter by protocol, pool, address, or TX hash"),
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
        # Fetch verified recommendations to filter and paginate
        q = db.table("recommendations").select(
            "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, "
            "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
            "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
        ).not_.is_("on_chain_tx_hash", "null").order("created_at", desc=True)

        res = q.execute()
        data = res.data or []

        filtered_data = []
        for rec in data:
            proto = rec.get("protocols") or {}

            # Filter by risk_tag
            if risk_tag and rec.get("risk_tag", "").lower() != risk_tag.lower():
                continue

            # Filter by search term
            if search:
                s_term = search.lower()
                p_name = (proto.get("name") or "").lower()
                p_pool = (proto.get("pool_name") or "").lower()
                p_addr = (proto.get("pool_address") or "").lower()
                tx_hash = (rec.get("on_chain_tx_hash") or "").lower()
                
                if (s_term not in p_name and 
                    s_term not in p_pool and 
                    s_term not in p_addr and 
                    s_term not in tx_hash):
                    continue

            # Attach explorer URL to each record
            rec["explorer_url"] = _build_explorer_link(rec.get("on_chain_tx_hash"))
            filtered_data.append(rec)

        total = len(filtered_data)
        offset = (page - 1) * page_size
        paginated_data = filtered_data[offset:offset + page_size]

        return {
            "data": paginated_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + page_size < total,
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

        # Get TVL and APY candidates from snapshots immediately before or after created_at
        # (resolves rounding, precision discrepancies, and race conditions where snapshot fetched_at is slightly after rec created_at)
        snap_res_lte = (
            db.table("yield_snapshots")
            .select("tvl_usd, apy")
            .eq("protocol_id", rec["protocols"]["id"])
            .lte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=True)
            .limit(2)
            .execute()
        )
        snap_res_gte = (
            db.table("yield_snapshots")
            .select("tvl_usd, apy")
            .eq("protocol_id", rec["protocols"]["id"])
            .gte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=False)
            .limit(2)
            .execute()
        )
        
        real_tvl_val = 0.0
        if snap_res_lte.data and snap_res_lte.data[0]["tvl_usd"] is not None:
            try:
                real_tvl_val = float(snap_res_lte.data[0]["tvl_usd"])
            except (ValueError, TypeError):
                pass
        elif snap_res_gte.data and snap_res_gte.data[0]["tvl_usd"] is not None:
            try:
                real_tvl_val = float(snap_res_gte.data[0]["tvl_usd"])
            except (ValueError, TypeError):
                pass
        real_tvl = real_tvl_val
        
        tvls = [0.0]
        apys = []
        try:
            apys.append(f"{float(rec['apy_at_time']):.4f}")
            apys.append(f"{float(rec['apy_at_time']):.2f}")
        except (ValueError, TypeError):
            pass
        apys.append(str(rec['apy_at_time']))
        
        # Pull candidate values from nearby snapshots
        for s in (snap_res_lte.data or []) + (snap_res_gte.data or []):
            if s.get("tvl_usd") is not None:
                try:
                    tvls.append(float(s["tvl_usd"]))
                except (ValueError, TypeError):
                    pass
            if s.get("apy") is not None:
                try:
                    apys.append(f"{float(s['apy']):.4f}")
                    apys.append(f"{float(s['apy']):.2f}")
                except (ValueError, TypeError):
                    pass
                apys.append(str(s['apy']))
        
        # Look for percentages or numbers in reasoning
        import re
        pct_matches = re.findall(r'([0-9.]+)\s*%', rec["ai_reasoning"])
        for pm in pct_matches:
            apys.append(pm)
            try:
                apys.append(f"{float(pm):.4f}")
            except (ValueError, TypeError):
                pass
            
        num_matches = re.findall(r'\$?([0-9,]+)(?:\.[0-9]+)?', rec["ai_reasoning"])
        for nm in num_matches:
            clean_nm = nm.replace(",", "").strip()
            if clean_nm:  # Ensure it's not an empty string (e.g. from standalone commas in reasoning)
                try:
                    val = float(clean_nm)
                    tvls.append(val)
                except (ValueError, TypeError):
                    pass
            
        tvls = list(set(tvls))
        apys = list(set(apys))
        
        target_hash = rec["recommendation_hash"]
        matched_payload = None
        found_match = False

        # Generate candidates for renames or formatting differences
        proto_names = list(set([
            rec["protocols"]["name"],
            rec["protocols"]["name"].replace(" ", "-"),
            rec["protocols"]["name"].replace("-", " "),
            rec["protocols"]["name"].lower(),
            "fluxion-network", "fluxion", "clearpool-lending", "clearpool"
        ]))
        
        pool_names = list(set([
            rec["protocols"]["pool_name"],
            rec["protocols"]["pool_name"].replace("/", "-"),
            rec["protocols"]["pool_name"].replace("-", "/"),
        ]))
        
        raw_addr = rec["protocols"]["pool_address"] or ""
        hex_addr = "0x" + raw_addr.split("0x")[-1] if "0x" in raw_addr else raw_addr
        pool_addresses = list(set([
            raw_addr,
            raw_addr.lower(),
            hex_addr,
            hex_addr.lower(),
            hex_addr.upper(),
            "",
        ]))
        
        models = list(set([
            rec["ai_model"],
            "meta/llama-3.3-70b-instruct",
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "qwen/qwen3.6-27b",
        ]))

        # Try permutations to find the exact configuration matching the stored recommendation_hash
        for proto_n in proto_names:
            for pool_n in pool_names:
                for addr in pool_addresses:
                    for tvl_v in tvls:
                        for apy_v in apys:
                            for model_v in models:
                                for source in ["dune_query_7595582", None]:
                                    for version in ["1.0", None]:
                                        for chain_info in [True, False]:
                                            # Try build_recommendation_payload style payload
                                            payload = {
                                                "scored_at": scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                "risk_tag": rec["risk_tag"],
                                                "rank": rec["rank"],
                                                "protocol_name": proto_n,
                                                "pool_name": pool_n,
                                                "pool_address": addr.lower() if (addr and isinstance(addr, str)) else (addr or ""),
                                                "apy_at_time": apy_v,
                                                "tvl_usd": f"{float(tvl_v):.2f}",
                                                "ai_reasoning": rec["ai_reasoning"].strip(),
                                                "ai_model": model_v,
                                            }
                                            if version:
                                                payload["version"] = version
                                            if source:
                                                payload["source"] = source
                                            if chain_info:
                                                payload["chain"] = "mantle"
                                                payload["chain_id"] = 5000
                                                
                                            canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                                            computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                                            if computed_hash == target_hash:
                                                matched_payload = canonical_json
                                                found_match = True
                                                break
                                            
                                            # Try legacy payload style
                                            if not version and not source and not chain_info:
                                                legacy_payload = {
                                                    "scored_at": scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                    "risk_tag": rec["risk_tag"],
                                                    "rank": rec["rank"],
                                                    "protocol_name": proto_n,
                                                    "pool_name": pool_n,
                                                    "pool_address": (addr or "").lower(),
                                                    "apy_at_time": apy_v,
                                                    "tvl_usd": f"{float(tvl_v):.2f}",
                                                    "ai_reasoning": rec["ai_reasoning"].strip(),
                                                    "ai_model": model_v
                                                }
                                                canonical_json = json.dumps(legacy_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                                                computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                                                if computed_hash == target_hash:
                                                    matched_payload = canonical_json
                                                    found_match = True
                                                    break
                                        if found_match: break
                                    if found_match: break
                                if found_match: break
                            if found_match: break
                        if found_match: break
                    if found_match: break
                if found_match: break
            if found_match: break

        # Fallback to standard payload if no permutation matches (prevents NameError and API crash)
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

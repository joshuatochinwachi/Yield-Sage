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

# Solana explorer base URL for on-chain proof links
_EXPLORER_BASE = "https://solscan.io/tx/"



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
                    "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, tvl_usd, "
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
            "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, tvl_usd, "
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
                "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, tvl_usd, "
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
        # Strip URL prefix if full Solscan link was passed
        clean_tx = tx_hash.split("/")[-1].split("?")[0].strip()

        # 1. Try exact match (Solana Base58 signatures are case-sensitive)
        rec_res = (
            db.table("recommendations")
            .select(
                "id, risk_tag, rank, apy_at_time, tvl_usd, ai_reasoning, ai_model, "
                "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
            )
            .eq("on_chain_tx_hash", clean_tx)
            .execute()
        )

        # 2. Fallback to case-insensitive substring match (for Solana Base58 copy-paste quirks)
        if not rec_res.data:
            rec_res = (
                db.table("recommendations")
                .select(
                    "id, risk_tag, rank, apy_at_time, tvl_usd, ai_reasoning, ai_model, "
                    "on_chain_tx_hash, on_chain_logged_at, recommendation_hash, created_at, "
                    "protocols(id, slug, name, pool_name, pool_address, risk_tag, image_url, app_link)"
                )
                .ilike("on_chain_tx_hash", f"%{clean_tx}%")
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


        # 2. Reconstruct the canonical JSON payload to verify the hash
        try:
            from agent.logger import build_recommendation_payload
        except ImportError:
            from logger import build_recommendation_payload

        import json
        import hashlib
        from datetime import datetime

        created_at_str = rec["created_at"].replace("Z", "+00:00")
        scored_at_dt = datetime.fromisoformat(created_at_str)

        # --- TVL resolution ---
        # For new records: tvl_usd is stored directly in recommendations table (exact value used at hash time).
        # For old records (before this migration): tvl_usd is NULL → fall back to snapshots & reasoning.
        stored_tvl = rec.get("tvl_usd")
        if stored_tvl is not None:
            try:
                tvl_candidates = [float(stored_tvl)]
            except (ValueError, TypeError):
                tvl_candidates = [0.0]
        else:
            tvls = [0.0]
            # 1. Query snapshots for this protocol (no timestamp restriction, in case snapshots were refreshed)
            try:
                snap_res = (
                    db.table("yield_snapshots")
                    .select("tvl_usd, apy")
                    .eq("protocol_id", rec["protocols"]["id"])
                    .order("fetched_at", desc=True)
                    .limit(10)
                    .execute()
                )
                for s in (snap_res.data or []):
                    if s.get("tvl_usd") is not None:
                        try: tvls.append(float(s["tvl_usd"]))
                        except (ValueError, TypeError): pass
            except Exception:
                pass

            # 2. Extract numbers/amounts from ai_reasoning text (e.g. $88M, 88.4M, $88,438,097)
            import re
            reasoning_text = rec.get("ai_reasoning") or ""
            for match in re.finditer(r'\$?([0-9,]+(?:\.[0-9]+)?)\s*([kKmMbB])?', reasoning_text):
                num_str = match.group(1).replace(",", "").strip()
                suffix = (match.group(2) or "").upper()
                if num_str:
                    try:
                        val = float(num_str)
                        if suffix == 'K': val *= 1_000
                        elif suffix == 'M': val *= 1_000_000
                        elif suffix == 'B': val *= 1_000_000_000
                        tvls.append(val)
                    except (ValueError, TypeError): pass

            tvl_candidates = list(set(tvls))

        target_hash = rec["recommendation_hash"]
        matched_payload = None
        found_match = False
        computed_hash = None

        raw_addr = rec["protocols"]["pool_address"] or ""
        addr_candidates = list(set([raw_addr, raw_addr.lower() if raw_addr else "", ""]))

        proto_raw = rec["protocols"].get("name") or "Unknown"
        slug_raw = rec["protocols"].get("slug") or ""
        proto_candidates = [p for p in set([
            proto_raw,
            slug_raw,
            proto_raw.replace(" ", "-"),
            proto_raw.replace("-", " "),
            proto_raw.lower(),
            slug_raw.lower(),
        ]) if p]

        pool_raw = rec["protocols"].get("pool_name") or "Unknown"
        pool_candidates = [p for p in set([
            pool_raw,
            pool_raw.replace(" ", "-"),
            pool_raw.replace("-", " "),
            pool_raw.replace("/", "-"),
            pool_raw.replace("-", "/"),
        ]) if p]

        # --- Primary attempt: exact same builder used at write time (v2.0 format) ---
        # Uses "program_address" key + "version":"2.0" + "source":"solana_live_pipeline".
        # apy_at_time is stored exactly in DB — no permutation needed.
        for proto_candidate in proto_candidates:
            for pool_candidate in pool_candidates:
                for addr_candidate in addr_candidates:
                    for tvl_candidate in tvl_candidates:
                        for source_candidate in ["solana_live_pipeline", "dune_query_7595582"]:
                            try:
                                payload = build_recommendation_payload(
                                    protocol_name=proto_candidate,
                                    pool_name=pool_candidate,
                                    pool_address=addr_candidate,
                                    risk_tag=rec["risk_tag"],
                                    rank=rec["rank"],
                                    apy_at_time=rec["apy_at_time"],
                                    tvl_usd=tvl_candidate,
                                    ai_reasoning=rec["ai_reasoning"],
                                    ai_model=rec["ai_model"],
                                    scored_at=scored_at_dt,
                                    data_source_id=source_candidate,
                                )
                                canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                                computed_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
                                if computed_hash == target_hash:
                                    matched_payload = canonical_json
                                    found_match = True
                                    break
                            except (ValueError, TypeError):
                                pass
                        if found_match: break
                    if found_match: break
                if found_match: break
            if found_match: break

        # --- Legacy fallback: older records used "pool_address" key instead of "program_address" ---
        if not found_match:
            models_to_try = list(set([
                rec["ai_model"],
                "meta/llama-3.3-70b-instruct",
                "llama-3.3-70b-versatile",
                "openai/gpt-oss-120b",
                "qwen/qwen3.6-27b",
            ]))
            apys_to_try = []
            try:
                apys_to_try.append(f"{float(rec['apy_at_time']):.4f}")
                apys_to_try.append(f"{float(rec['apy_at_time']):.2f}")
            except (ValueError, TypeError):
                pass
            apys_to_try.append(str(rec["apy_at_time"]))
            apys_to_try = list(set(apys_to_try))

            for model_v in models_to_try:
                for addr in addr_candidates:
                    for tvl_v in tvl_candidates:
                        for apy_v in apys_to_try:
                            legacy_payload = {
                                "scored_at": scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "risk_tag": rec["risk_tag"],
                                "rank": rec["rank"],
                                "protocol_name": rec["protocols"]["name"],
                                "pool_name": rec["protocols"]["pool_name"],
                                "pool_address": (addr or "").lower(),
                                "apy_at_time": apy_v,
                                "tvl_usd": f"{float(tvl_v):.2f}",
                                "ai_reasoning": rec["ai_reasoning"].strip(),
                                "ai_model": model_v,
                            }
                            for extra in [
                                {},
                                {"chain": "solana", "chain_id": 101},
                                {"version": "1.0"},
                                {"source": "dune_query_7595582"},
                                {"chain": "solana", "chain_id": 101, "version": "1.0"},
                            ]:
                                candidate = {**legacy_payload, **extra}
                                canonical_json = json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                                computed_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
                                if computed_hash == target_hash:
                                    matched_payload = canonical_json
                                    found_match = True
                                    break
                            if found_match: break
                        if found_match: break
                    if found_match: break
                if found_match: break

        # Final fallback: compute fresh payload for display even if hash doesn't match
        if not found_match:
            payload = build_recommendation_payload(
                protocol_name=rec["protocols"]["name"],
                pool_name=rec["protocols"]["pool_name"],
                pool_address=rec["protocols"]["pool_address"] or "",
                risk_tag=rec["risk_tag"],
                rank=rec["rank"],
                apy_at_time=rec["apy_at_time"],
                tvl_usd=tvl_candidates[0],
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


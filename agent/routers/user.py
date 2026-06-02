"""
routers/user.py
────────────────
Auth-protected endpoints for user profile and settings.

GET  /api/user/profile            — Fetch authenticated user's profile
PUT  /api/user/profile            — Update name / risk preference
POST /api/user/telegram/connect   — Link a Telegram chat_id to the user
GET  /api/user/alerts             — Fetch alert preference settings
PUT  /api/user/alerts             — Update alert thresholds / is_active toggle
GET  /api/user/activity           — Recent telegram messages sent to this user
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from supabase import create_client, Client
from datetime import datetime

from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["User"])

_url = os.getenv("SUPABASE_URL", "")
_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_db: Client | None = create_client(_url, _key) if _url and _key else None


def _db_or_503():
    if not _db:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return _db


# ── Pydantic models ───────────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=120)
    risk_preference: Optional[str] = Field(
        None,
        description="Comma-separated risk tiers: stable,moderate,aggressive",
    )


class TelegramConnectRequest(BaseModel):
    telegram_chat_id: int = Field(..., description="The Telegram chat_id to link to this account")


class UpdateAlertsRequest(BaseModel):
    is_active: Optional[bool] = None
    stable_apy_threshold: Optional[float] = Field(None, ge=0, le=10000)
    moderate_apy_threshold: Optional[float] = Field(None, ge=0, le=10000)
    aggressive_apy_threshold: Optional[float] = Field(None, ge=0, le=10000)


# ── GET /api/user/profile ─────────────────────────────────────────────────────
@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    """Returns the authenticated user's profile row from the users table."""
    db = _db_or_503()
    try:
        res = db.table("users").select(
            "id, email, full_name, telegram_chat_id, risk_preference, created_at, updated_at"
        ).eq("id", user_id).limit(1).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="User profile not found.")

        user = res.data[0]

        # Enrich with alert preferences
        alert_res = db.table("alert_preferences").select(
            "is_active, stable_apy_threshold, moderate_apy_threshold, aggressive_apy_threshold"
        ).eq("user_id", user_id).limit(1).execute()

        user["alert_preferences"] = alert_res.data[0] if alert_res.data else None

        return {"data": user}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user/profile GET] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user profile.")


# ── PUT /api/user/profile ─────────────────────────────────────────────────────
@router.put("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    user_id: str = Depends(get_current_user),
):
    """Updates the user's full_name and/or risk_preference."""
    db = _db_or_503()
    try:
        updates: dict = {"updated_at": datetime.utcnow().isoformat()}

        if body.full_name is not None:
            updates["full_name"] = body.full_name

        if body.risk_preference is not None:
            # Validate the tiers
            valid_tiers = {"stable", "moderate", "aggressive"}
            tiers = [t.strip().lower() for t in body.risk_preference.split(",")]
            invalid = [t for t in tiers if t not in valid_tiers]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid risk tiers: {invalid}. Use stable, moderate, aggressive.",
                )
            updates["risk_preference"] = ",".join(tiers)

        res = db.table("users").update(updates).eq("id", user_id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="User not found.")

        return {"data": res.data[0], "message": "Profile updated successfully."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user/profile PUT] {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile.")


# ── POST /api/user/telegram/connect ──────────────────────────────────────────
@router.post("/telegram/connect")
async def connect_telegram(
    body: TelegramConnectRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Links a Telegram chat_id to the authenticated user's account.
    After this, the user will receive hourly Telegram alerts.
    """
    db = _db_or_503()
    try:
        # Check this chat_id isn't already linked to another account
        existing = db.table("users").select("id").eq(
            "telegram_chat_id", body.telegram_chat_id
        ).limit(1).execute()

        if existing.data and existing.data[0]["id"] != user_id:
            raise HTTPException(
                status_code=409,
                detail="This Telegram account is already linked to another user.",
            )

        res = db.table("users").update({
            "telegram_chat_id": body.telegram_chat_id,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()

        # Provision alert_preferences row if not already present
        pref_check = db.table("alert_preferences").select("id").eq("user_id", user_id).limit(1).execute()
        if not pref_check.data:
            db.table("alert_preferences").insert({
                "user_id": user_id,
                "is_active": True,
            }).execute()

        return {
            "message": "Telegram account linked successfully.",
            "telegram_chat_id": body.telegram_chat_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user/telegram/connect] {e}")
        raise HTTPException(status_code=500, detail="Failed to link Telegram account.")


# ── GET /api/user/alerts ──────────────────────────────────────────────────────
@router.get("/alerts")
async def get_alerts(user_id: str = Depends(get_current_user)):
    """Returns the user's alert preference settings."""
    db = _db_or_503()
    try:
        res = db.table("alert_preferences").select("*").eq("user_id", user_id).limit(1).execute()

        if not res.data:
            # Return defaults if no row exists yet
            return {
                "data": {
                    "user_id": user_id,
                    "is_active": True,
                    "stable_apy_threshold": None,
                    "moderate_apy_threshold": None,
                    "aggressive_apy_threshold": None,
                }
            }

        return {"data": res.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user/alerts GET] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert preferences.")


# ── PUT /api/user/alerts ──────────────────────────────────────────────────────
@router.put("/alerts")
async def update_alerts(
    body: UpdateAlertsRequest,
    user_id: str = Depends(get_current_user),
):
    """Updates alert preferences (thresholds and active/inactive toggle)."""
    db = _db_or_503()
    try:
        updates: dict = {"updated_at": datetime.utcnow().isoformat()}

        if body.is_active is not None:
            updates["is_active"] = body.is_active
        if body.stable_apy_threshold is not None:
            updates["stable_apy_threshold"] = body.stable_apy_threshold
        if body.moderate_apy_threshold is not None:
            updates["moderate_apy_threshold"] = body.moderate_apy_threshold
        if body.aggressive_apy_threshold is not None:
            updates["aggressive_apy_threshold"] = body.aggressive_apy_threshold

        # Upsert — create the row if it doesn't exist
        existing = db.table("alert_preferences").select("id").eq("user_id", user_id).limit(1).execute()

        if existing.data:
            res = db.table("alert_preferences").update(updates).eq("user_id", user_id).execute()
        else:
            updates["user_id"] = user_id
            res = db.table("alert_preferences").insert(updates).execute()

        return {"data": res.data[0] if res.data else updates, "message": "Alert preferences updated."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user/alerts PUT] {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert preferences.")


# ── GET /api/user/activity ────────────────────────────────────────────────────
@router.get("/activity")
async def get_activity(
    user_id: str = Depends(get_current_user),
    limit: int = 20,
):
    """Returns recent Telegram messages sent to this user (hourly alerts + query responses)."""
    db = _db_or_503()
    try:
        res = (
            db.table("telegram_messages")
            .select("id, message_type, content, status, sent_at, error_message")
            .eq("user_id", user_id)
            .order("sent_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"data": res.data or [], "count": len(res.data or [])}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user/activity] {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user activity.")

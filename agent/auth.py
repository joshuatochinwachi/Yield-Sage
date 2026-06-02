"""
auth.py — FastAPI dependency for Supabase JWT validation.

Usage in a route:
    @router.get("/protected")
    async def protected(user_id: str = Depends(get_current_user)):
        ...
"""

import os
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ── Supabase client (service role — bypasses RLS for admin reads) ─────────────
_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
_SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

_supabase_admin: Client | None = (
    create_client(_SUPABASE_URL, _SUPABASE_SERVICE_KEY)
    if _SUPABASE_URL and _SUPABASE_SERVICE_KEY
    else None
)

# HTTPBearer scheme — reads the Authorization: Bearer <token> header
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency.
    Validates the Supabase JWT supplied in the Authorization header.
    Returns the authenticated user's UUID (str).
    Raises HTTP 401 if the token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Pass Authorization: Bearer <token>.",
        )

    token = credentials.credentials

    if not _supabase_admin:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not configured.",
        )

    try:
        # Supabase validates the JWT signature and expiry for us
        result = _supabase_admin.auth.get_user(token)
        if not result or not result.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            )
        return str(result.user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[Auth] Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    """
    Like get_current_user but returns None instead of raising 401.
    Use for endpoints that have richer responses for authenticated users.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

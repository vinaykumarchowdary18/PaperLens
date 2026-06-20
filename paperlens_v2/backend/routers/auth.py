"""
Auth Router — Google OAuth → JWT
----------------------------------
Flow:
  1. Frontend redirects user to Google OAuth consent screen
  2. Google redirects back with ?code= to /auth/callback
  3. We exchange code → Google token → user profile
  4. Create/find user in DB, issue our own JWT
  5. Return JWT to frontend (stored in localStorage / httpOnly cookie)
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import uuid
import json
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from database import get_db
from config import get_settings

router = APIRouter()
settings = get_settings()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(authorization: str = None):
    """Dependency to extract authenticated user from Bearer token."""
    from fastapi import Header
    return authorization  # placeholder — real version below


# ── Real dependency used by protected routes ──────────────────────────────────
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> dict:
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    async with db.execute(
        "SELECT id, email, name, credits, free_used FROM users WHERE id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query}")


@router.post("/google/callback")
async def google_callback(body: dict, db=Depends(get_db)):
    """
    Exchange Google authorization code for user info.
    Frontend POSTs: { "code": "...", "redirect_uri": "..." }
    Returns: { "token": "...", "user": {...} }
    """
    code = body.get("code")
    redirect_uri = body.get("redirect_uri", f"{settings.FRONTEND_URL}/auth/callback")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code with Google")

        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        # Get user info
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

        google_user = user_resp.json()

    email = google_user.get("email")
    name = google_user.get("name", "")
    google_sub = google_user.get("sub")

    if not email:
        raise HTTPException(status_code=400, detail="No email from Google")

    # Upsert user in DB
    async with db.execute("SELECT id, credits, free_used FROM users WHERE email = ?", (email,)) as cursor:
        existing = await cursor.fetchone()

    if existing:
        user_id = existing["id"]
        credits = existing["credits"]
        free_used = existing["free_used"]
    else:
        user_id = str(uuid.uuid4())
        credits = 1  # 1 free credit on signup
        free_used = 0
        await db.execute(
            "INSERT INTO users (id, email, name, credits, free_used) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, name, credits, free_used),
        )
        await db.commit()

    our_token = create_access_token(user_id, email)

    return {
        "token": our_token,
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "credits": credits,
            "free_used": free_used,
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(require_auth)):
    """Return current user profile."""
    return current_user

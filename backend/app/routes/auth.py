import secrets
import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings
from app.models import AuthStatus

logger = logging.getLogger(__name__)
router = APIRouter()

SCOPES = ["https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/userinfo.email",
          "openid"]

# In-memory session store (keyed by session token)
sessions: dict = {}


def get_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    return flow


@router.get("/google")
async def google_auth(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth credentials not configured.")
    flow = get_flow()
    state = secrets.token_urlsafe(32)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",
    )
    sessions[f"oauth_state_{state}"] = True
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, error: Optional[str] = None):
    if error:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error={error}")

    state_key = f"oauth_state_{state}"
    if state_key not in sessions:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error=invalid_state")
    del sessions[state_key]

    try:
        flow = get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        oauth2_service = build("oauth2", "v2", credentials=credentials)
        user_info = oauth2_service.userinfo().get().execute()
        email = user_info.get("email", "")
        name = user_info.get("name", "")

        session_token = secrets.token_urlsafe(32)
        sessions[session_token] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
            "email": email,
            "name": name,
        }

        # Pass token in URL so frontend can store it (works across different domains)
        redirect_url = f"{settings.FRONTEND_URL}?auth_success=true&session={session_token}"
        response = RedirectResponse(url=redirect_url)
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=False,   # allow JS to read on same-origin
            samesite="none",
            secure=True,
            max_age=3600 * 8,
        )
        return response
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error=callback_failed")


@router.get("/status", response_model=AuthStatus)
async def auth_status(request: Request):
    # Check cookie first, then X-Session-Token header (for cross-origin)
    session_token = request.cookies.get("session_token")
    if not session_token:
        session_token = request.headers.get("X-Session-Token")
    if not session_token or session_token not in sessions:
        return AuthStatus(connected=False)
    session = sessions[session_token]
    return AuthStatus(connected=True, email=session.get("email"), name=session.get("name"))


@router.post("/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if not session_token:
        session_token = request.headers.get("X-Session-Token")
    if session_token and session_token in sessions:
        del sessions[session_token]
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}


def get_session_credentials(request: Request) -> Optional[dict]:
    session_token = request.cookies.get("session_token")
    if not session_token:
        session_token = request.headers.get("X-Session-Token")
    if not session_token or session_token not in sessions:
        return None
    return sessions[session_token]

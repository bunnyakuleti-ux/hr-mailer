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
    """Initiate Google OAuth flow."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    flow = get_flow()
    state = secrets.token_urlsafe(32)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",
    )
    # Store state for CSRF validation
    sessions[f"oauth_state_{state}"] = True
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, error: Optional[str] = None):
    """Handle OAuth callback from Google."""
    if error:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error={error}")

    # Validate state
    state_key = f"oauth_state_{state}"
    if state_key not in sessions:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error=invalid_state")
    del sessions[state_key]

    try:
        flow = get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user email
        oauth2_service = build("oauth2", "v2", credentials=credentials)
        user_info = oauth2_service.userinfo().get().execute()
        email = user_info.get("email", "")
        name = user_info.get("name", "")

        # Store credentials in session
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

        response = RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_success=true")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=3600 * 8,  # 8 hours
        )
        return response
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error=callback_failed")


@router.get("/status", response_model=AuthStatus)
async def auth_status(request: Request):
    """Return current authentication status."""
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in sessions:
        return AuthStatus(connected=False)

    session = sessions[session_token]
    return AuthStatus(
        connected=True,
        email=session.get("email"),
        name=session.get("name"),
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Clear the session."""
    session_token = request.cookies.get("session_token")
    if session_token and session_token in sessions:
        del sessions[session_token]
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}


def get_session_credentials(request: Request) -> Optional[dict]:
    """Helper to get credentials from session."""
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in sessions:
        return None
    return sessions[session_token]

import secrets
import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings
from app.models import AuthStatus
from app.database import save_session, get_session, delete_session, session_exists

logger = logging.getLogger(__name__)
router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

# Short-lived OAuth state tokens — in-memory is fine (used once then discarded)
_oauth_states: dict = {}


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
    return Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )


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
    _oauth_states[state] = True
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, error: Optional[str] = None):
    if error:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error={error}")

    if state not in _oauth_states:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?auth_error=invalid_state")
    del _oauth_states[state]

    try:
        flow = get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        oauth2_service = build("oauth2", "v2", credentials=credentials)
        user_info = oauth2_service.userinfo().get().execute()
        email = user_info.get("email", "")
        name = user_info.get("name", "")

        session_token = secrets.token_urlsafe(32)
        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
        }

        # Persist to SQLite — survives restarts
        save_session(session_token, email, name, creds_data)

        redirect_url = f"{settings.FRONTEND_URL}?auth_success=true&session={session_token}"
        response = RedirectResponse(url=redirect_url)
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=False,
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
    token = _get_token(request)
    if not token or not session_exists(token):
        return AuthStatus(connected=False)
    session = get_session(token)
    if not session:
        return AuthStatus(connected=False)
    return AuthStatus(connected=True, email=session.get("email"), name=session.get("name"))


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = _get_token(request)
    if token:
        delete_session(token)
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}


def get_session_credentials(request: Request) -> Optional[dict]:
    """Return full credentials dict for the authenticated user, or None."""
    token = _get_token(request)
    if not token:
        return None
    return get_session(token)


def _get_token(request: Request) -> Optional[str]:
    """Extract session token from cookie or X-Session-Token header."""
    token = request.cookies.get("session_token")
    if not token:
        token = request.headers.get("X-Session-Token")
    return token

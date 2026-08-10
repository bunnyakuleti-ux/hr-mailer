import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

from app.models import RecipientModel, EmailStatus, CampaignStatus
from app.services.gmail_service import personalize_text, send_email, get_user_profile, build_gmail_service
from app.database import save_campaign, load_campaign, load_all_campaigns
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# In-memory running tasks (asyncio tasks can't be serialized)
campaign_tasks: Dict[str, asyncio.Task] = {}
# Store email body per campaign (short-lived)
_campaign_bodies: Dict[str, str] = {}


def _campaign_to_dict(c: CampaignStatus) -> dict:
    d = c.model_dump()
    # Convert enums to strings for JSON
    for r in d.get("recipients", []):
        if hasattr(r.get("status"), "value"):
            r["status"] = r["status"].value
    return d


def _dict_to_campaign(d: dict) -> CampaignStatus:
    recipients = [RecipientModel(**r) for r in d.get("recipients", [])]
    d["recipients"] = recipients
    return CampaignStatus(**d)


def create_campaign(
    recipients: List[RecipientModel],
    subject: str,
    attachment_name: Optional[str],
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    campaign_id = f"campaign_{ts}_{uuid.uuid4().hex[:6]}"
    valid_recipients = [r for r in recipients if r.is_valid and not r.is_duplicate]

    campaign = CampaignStatus(
        campaign_id=campaign_id,
        status="pending",
        total=len(valid_recipients),
        sent=0,
        failed=0,
        skipped=0,
        pending=len(valid_recipients),
        recipients=[r.model_copy() for r in valid_recipients],
        subject=subject,
        attachment_name=attachment_name,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    save_campaign(campaign_id, _campaign_to_dict(campaign))
    return campaign_id


def get_campaign(campaign_id: str) -> Optional[CampaignStatus]:
    data = load_campaign(campaign_id)
    if not data:
        return None
    try:
        return _dict_to_campaign(data)
    except Exception as e:
        logger.error(f"Failed to deserialize campaign {campaign_id}: {e}")
        return None


def store_body_for_campaign(campaign_id: str, body: str):
    _campaign_bodies[campaign_id] = body


def cancel_campaign(campaign_id: str) -> bool:
    data = load_campaign(campaign_id)
    if not data or data.get("status") != "running":
        return False
    data["status"] = "cancelled"
    save_campaign(campaign_id, data)
    return True


async def run_campaign(
    campaign_id: str,
    credentials_data: dict,
    attachment_path: Optional[str],
    delay_seconds: float = 2.0,
):
    """Send emails one by one, saving progress to SQLite after each send."""
    data = load_campaign(campaign_id)
    if not data:
        logger.error(f"Campaign {campaign_id} not found in DB")
        return

    logger.info(f"Starting campaign {campaign_id} with {len(data.get('recipients', []))} recipients")
    logger.info(f"Credentials present: token={bool(credentials_data.get('token'))}, refresh={bool(credentials_data.get('refresh_token'))}")

    data["status"] = "running"
    save_campaign(campaign_id, data)

    # Rebuild credentials with auto-refresh
    creds = Credentials(
        token=credentials_data.get("token"),
        refresh_token=credentials_data.get("refresh_token"),
        token_uri=credentials_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=credentials_data.get("client_id"),
        client_secret=credentials_data.get("client_secret"),
        scopes=credentials_data.get("scopes"),
    )

    # Force refresh if token is expired or missing
    try:
        if not creds.valid or not creds.token:
            from google.auth.transport.requests import Request as GRequest
            import requests as req_lib
            creds.refresh(GRequest(session=req_lib.Session()))
            logger.info("Token refreshed successfully")
    except Exception as e:
        logger.warning(f"Token refresh failed (will try anyway): {e}")

    try:
        service = build_gmail_service(creds)
        from_email, err = get_user_profile(service)
        if not from_email:
            data["status"] = "failed"
            save_campaign(campaign_id, data)
            logger.error(f"Could not get user profile: {err}")
            return
        logger.info(f"Sending as: {from_email}")
    except Exception as e:
        data["status"] = "failed"
        save_campaign(campaign_id, data)
        logger.error(f"Failed to build Gmail service: {e}", exc_info=True)
        return

    email_body = _campaign_bodies.get(campaign_id, "")
    subject = data.get("subject", "")
    attachment_name = data.get("attachment_name")

    for i, recipient_dict in enumerate(data["recipients"]):
        # Reload fresh from DB to catch cancellation
        fresh = load_campaign(campaign_id)
        if fresh and fresh.get("status") == "cancelled":
            # Mark remaining as skipped
            for r in data["recipients"][i:]:
                if r.get("status") == "pending":
                    r["status"] = "skipped"
                    data["skipped"] = data.get("skipped", 0) + 1
                    data["pending"] = max(0, data.get("pending", 0) - 1)
            save_campaign(campaign_id, data)
            break

        status = recipient_dict.get("status", "pending")
        if status in ("sent", "skipped"):
            continue

        email = recipient_dict.get("email", "")
        name = recipient_dict.get("name")
        company = recipient_dict.get("company")

        data["current_recipient"] = email
        data["recipients"][i]["status"] = "sending"
        save_campaign(campaign_id, data)

        personalized_subject = personalize_text(subject, name, company, email)
        personalized_body = personalize_text(email_body, name, company, email)

        success, error_msg = send_email(
            service=service,
            from_email=from_email,
            to_email=email,
            subject=personalized_subject,
            body=personalized_body,
            attachment_path=attachment_path,
            attachment_name=attachment_name,
        )

        if success:
            data["recipients"][i]["status"] = "sent"
            data["recipients"][i]["sent_at"] = datetime.now(timezone.utc).isoformat()
            data["sent"] = data.get("sent", 0) + 1
        else:
            data["recipients"][i]["status"] = "failed"
            data["recipients"][i]["error_message"] = error_msg
            data["failed"] = data.get("failed", 0) + 1

        data["pending"] = max(0, data.get("pending", 0) - 1)

        # Save progress after every email
        save_campaign(campaign_id, data)

        if i < len(data["recipients"]) - 1:
            await asyncio.sleep(delay_seconds)

    if data.get("status") != "cancelled":
        data["status"] = "completed"
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["current_recipient"] = None
    save_campaign(campaign_id, data)
    logger.info(
        f"Campaign {campaign_id} done: sent={data.get('sent')}, "
        f"failed={data.get('failed')}, skipped={data.get('skipped')}"
    )

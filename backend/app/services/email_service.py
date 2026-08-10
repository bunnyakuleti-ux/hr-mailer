import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

from app.models import RecipientModel, EmailStatus, CampaignStatus
from app.services.gmail_service import personalize_text, send_email, get_user_profile, build_gmail_service
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# In-memory campaign store
campaigns: Dict[str, CampaignStatus] = {}
# Track running tasks so they can be cancelled
campaign_tasks: Dict[str, asyncio.Task] = {}


def create_campaign(
    recipients: List[RecipientModel],
    subject: str,
    attachment_name: Optional[str],
) -> str:
    """Create a new campaign and return its ID."""
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
    campaigns[campaign_id] = campaign
    return campaign_id


def get_campaign(campaign_id: str) -> Optional[CampaignStatus]:
    return campaigns.get(campaign_id)


async def run_campaign(
    campaign_id: str,
    credentials_data: dict,
    attachment_path: Optional[str],
    delay_seconds: float = 2.0,
):
    """
    Async task that sends emails one by one with a delay.
    Stores progress in the in-memory campaigns dict.
    """
    campaign = campaigns.get(campaign_id)
    if not campaign:
        logger.error(f"Campaign {campaign_id} not found")
        return

    campaign.status = "running"

    # Rebuild credentials from stored dict
    creds = Credentials(
        token=credentials_data.get("token"),
        refresh_token=credentials_data.get("refresh_token"),
        token_uri=credentials_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=credentials_data.get("client_id"),
        client_secret=credentials_data.get("client_secret"),
        scopes=credentials_data.get("scopes"),
    )

    service = build_gmail_service(creds)
    from_email, err = get_user_profile(service)
    if not from_email:
        campaign.status = "failed"
        logger.error(f"Could not get user profile: {err}")
        return

    for i, recipient in enumerate(campaign.recipients):
        # Check for cancellation
        if campaign.status == "cancelled":
            # Mark remaining pending as skipped
            for r in campaign.recipients[i:]:
                if r.status == EmailStatus.PENDING:
                    r.status = EmailStatus.SKIPPED
                    campaign.skipped += 1
                    campaign.pending -= 1
            break

        if recipient.status in (EmailStatus.SENT, EmailStatus.SKIPPED):
            continue

        campaign.current_recipient = recipient.email
        recipient.status = EmailStatus.SENDING

        # Personalize subject and body
        personalized_subject = personalize_text(
            campaign.subject or "", recipient.name, recipient.company, recipient.email
        )
        body_template = campaign_tasks.get(f"{campaign_id}_body", "")
        personalized_body = personalize_text(
            body_template, recipient.name, recipient.company, recipient.email
        )

        success, error_msg = send_email(
            service=service,
            from_email=from_email,
            to_email=recipient.email,
            subject=personalized_subject,
            body=personalized_body,
            attachment_path=attachment_path,
            attachment_name=campaign.attachment_name,
        )

        if success:
            recipient.status = EmailStatus.SENT
            recipient.sent_at = datetime.now(timezone.utc).isoformat()
            campaign.sent += 1
        else:
            recipient.status = EmailStatus.FAILED
            recipient.error_message = error_msg
            campaign.failed += 1

        campaign.pending -= 1

        # Delay between emails
        if i < len(campaign.recipients) - 1 and campaign.status != "cancelled":
            await asyncio.sleep(delay_seconds)

    if campaign.status != "cancelled":
        campaign.status = "completed"
    campaign.completed_at = datetime.now(timezone.utc).isoformat()
    campaign.current_recipient = None
    logger.info(
        f"Campaign {campaign_id} finished: sent={campaign.sent}, failed={campaign.failed}, skipped={campaign.skipped}"
    )


def store_body_for_campaign(campaign_id: str, body: str):
    """Store the email body for use during async sending."""
    campaign_tasks[f"{campaign_id}_body"] = body


def cancel_campaign(campaign_id: str) -> bool:
    campaign = campaigns.get(campaign_id)
    if campaign and campaign.status == "running":
        campaign.status = "cancelled"
        return True
    return False

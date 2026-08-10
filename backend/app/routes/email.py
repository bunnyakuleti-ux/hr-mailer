import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models import (
    RecipientModel,
    EmailPreviewRequest,
    EmailPreviewResponse,
    SendCampaignRequest,
    CampaignStatus,
    RetryRequest,
    EmailStatus,
)
from app.routes.auth import get_session_credentials
from app.routes.upload import get_attachment_info
from app.services.email_service import (
    create_campaign,
    get_campaign,
    run_campaign,
    store_body_for_campaign,
    cancel_campaign,
    campaigns,
    campaign_tasks,
)
from app.services.gmail_service import personalize_text, build_gmail_service, get_user_profile

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/preview", response_model=EmailPreviewResponse)
async def preview_email(data: EmailPreviewRequest, request: Request):
    """Generate a preview of a personalized email for one recipient."""
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect your Gmail account.")

    recipient = data.recipient
    personalized_subject = personalize_text(data.subject, recipient.name, recipient.company, recipient.email)
    personalized_body = personalize_text(data.body, recipient.name, recipient.company, recipient.email)

    return EmailPreviewResponse(
        from_email=creds.get("email", "your-gmail@gmail.com"),
        to_email=recipient.email,
        subject=personalized_subject,
        body=personalized_body,
        attachment_name=None,
    )


@router.post("/send")
async def send_campaign(
    data: SendCampaignRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Create and start a sending campaign.
    Recipients must be provided; only valid non-duplicate ones are sent.
    """
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect your Gmail account.")

    if not data.subject.strip():
        raise HTTPException(status_code=400, detail="Email subject cannot be empty.")
    if not data.body.strip():
        raise HTTPException(status_code=400, detail="Email body cannot be empty.")

    # Load recipients from request
    if not data.recipient_indices and not hasattr(data, "recipients"):
        raise HTTPException(status_code=400, detail="No recipients provided.")

    return {"error": "Use /send_full endpoint"}, 400


@router.post("/send_full")
async def send_campaign_full(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Full send endpoint. Expects JSON body with recipients list, subject, body, attachment_id, delay.
    """
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect your Gmail account.")

    body = await request.json()
    subject: str = body.get("subject", "").strip()
    email_body: str = body.get("body", "").strip()
    recipients_data: list = body.get("recipients", [])
    attachment_id: Optional[str] = body.get("attachment_id")
    delay_seconds: float = float(body.get("delay_seconds", settings.DEFAULT_DELAY_SECONDS))
    retry_failed_ids: Optional[List[int]] = body.get("retry_failed_indices")

    if not subject:
        raise HTTPException(status_code=400, detail="Email subject cannot be empty.")
    if not email_body:
        raise HTTPException(status_code=400, detail="Email body cannot be empty.")
    if not recipients_data:
        raise HTTPException(status_code=400, detail="No recipients provided.")

    # Validate max recipients
    if len(recipients_data) > settings.MAX_RECIPIENTS_PER_CAMPAIGN:
        raise HTTPException(
            status_code=400,
            detail=f"Too many recipients ({len(recipients_data)}). Maximum: {settings.MAX_RECIPIENTS_PER_CAMPAIGN}",
        )

    # Build recipient models
    recipients = [RecipientModel(**r) for r in recipients_data]

    # Get attachment info
    attachment_path = None
    attachment_name = None
    if attachment_id:
        info = get_attachment_info(attachment_id)
        if info:
            attachment_path = info["path"]
            attachment_name = info["filename"]

    # Create campaign
    campaign_id = create_campaign(recipients, subject, attachment_name)
    store_body_for_campaign(campaign_id, email_body)

    # Start background task
    task = asyncio.create_task(
        run_campaign(
            campaign_id=campaign_id,
            credentials_data=creds,
            attachment_path=attachment_path,
            delay_seconds=delay_seconds,
        )
    )
    campaign_tasks[campaign_id] = task

    return {
        "campaign_id": campaign_id,
        "message": "Campaign started",
        "total": get_campaign(campaign_id).total,
    }


@router.get("/status/{campaign_id}", response_model=CampaignStatus)
async def campaign_status(campaign_id: str):
    """Get the current status of a campaign."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.post("/cancel/{campaign_id}")
async def cancel_campaign_route(campaign_id: str):
    """Request cancellation of a running campaign."""
    success = cancel_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail="Campaign is not running or not found.")
    return {"message": "Cancellation requested."}


@router.post("/retry")
async def retry_failed(request: Request, background_tasks: BackgroundTasks):
    """Retry all failed emails in a campaign."""
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    body = await request.json()
    campaign_id: str = body.get("campaign_id", "")
    delay_seconds: float = float(body.get("delay_seconds", settings.DEFAULT_DELAY_SECONDS))

    campaign = get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    if campaign.status == "running":
        raise HTTPException(status_code=400, detail="Campaign is still running.")

    # Reset failed recipients to pending
    retry_count = 0
    for r in campaign.recipients:
        if r.status == EmailStatus.FAILED:
            r.status = EmailStatus.PENDING
            r.error_message = None
            retry_count += 1

    if retry_count == 0:
        raise HTTPException(status_code=400, detail="No failed emails to retry.")

    # Reset campaign counters
    campaign.status = "running"
    campaign.failed = 0
    campaign.pending = retry_count
    campaign.completed_at = None

    # Get attachment
    attachment_path = None
    attachment_name = campaign.attachment_name
    if attachment_name:
        # Try to find the attachment in the store
        from app.routes.upload import attachment_store
        for info in attachment_store.values():
            if info["filename"] == attachment_name:
                attachment_path = info["path"]
                break

    task = asyncio.create_task(
        run_campaign(
            campaign_id=campaign_id,
            credentials_data=creds,
            attachment_path=attachment_path,
            delay_seconds=delay_seconds,
        )
    )
    campaign_tasks[campaign_id] = task

    return {"message": f"Retrying {retry_count} failed emails.", "campaign_id": campaign_id}


@router.get("/export/{campaign_id}")
async def export_results(campaign_id: str):
    """Export campaign results as a CSV file."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Company", "Status", "Error", "Timestamp"])

    for r in campaign.recipients:
        writer.writerow([
            r.name or "",
            r.email,
            r.company or "",
            r.status.value,
            r.error_message or "",
            r.sent_at or "",
        ])

    output.seek(0)
    filename = f"{campaign_id}_results.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

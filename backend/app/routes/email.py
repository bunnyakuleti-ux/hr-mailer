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
    CampaignStatus,
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
    campaign_tasks,
)
from app.services.gmail_service import personalize_text
from app.database import load_campaign, save_campaign

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/preview", response_model=EmailPreviewResponse)
async def preview_email(data: EmailPreviewRequest, request: Request):
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect your Gmail account.")

    recipient = data.recipient
    return EmailPreviewResponse(
        from_email=creds.get("email", "your-gmail@gmail.com"),
        to_email=recipient.email,
        subject=personalize_text(data.subject, recipient.name, recipient.company, recipient.email),
        body=personalize_text(data.body, recipient.name, recipient.company, recipient.email),
        attachment_name=None,
    )


@router.post("/send_full")
async def send_campaign_full(request: Request, background_tasks: BackgroundTasks):
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated. Please connect your Gmail account.")

    body = await request.json()
    subject: str = body.get("subject", "").strip()
    email_body: str = body.get("body", "").strip()
    recipients_data: list = body.get("recipients", [])
    attachment_id: Optional[str] = body.get("attachment_id")
    delay_seconds: float = float(body.get("delay_seconds", settings.DEFAULT_DELAY_SECONDS))

    if not subject:
        raise HTTPException(status_code=400, detail="Email subject cannot be empty.")
    if not email_body:
        raise HTTPException(status_code=400, detail="Email body cannot be empty.")
    if not recipients_data:
        raise HTTPException(status_code=400, detail="No recipients provided.")
    if len(recipients_data) > settings.MAX_RECIPIENTS_PER_CAMPAIGN:
        raise HTTPException(
            status_code=400,
            detail=f"Too many recipients ({len(recipients_data)}). Maximum: {settings.MAX_RECIPIENTS_PER_CAMPAIGN}",
        )

    recipients = [RecipientModel(**r) for r in recipients_data]

    attachment_path = None
    attachment_name = None
    if attachment_id:
        info = get_attachment_info(attachment_id)
        if info:
            attachment_path = info["path"]
            attachment_name = info["filename"]

    campaign_id = create_campaign(recipients, subject, attachment_name, credentials_data=creds)
    store_body_for_campaign(campaign_id, email_body)

    # Pass credentials directly — does NOT rely on session being in DB during async task
    task = asyncio.create_task(
        run_campaign(
            campaign_id=campaign_id,
            credentials_data=creds,  # full creds dict passed directly
            attachment_path=attachment_path,
            delay_seconds=delay_seconds,
        )
    )
    campaign_tasks[campaign_id] = task

    campaign = get_campaign(campaign_id)
    return {
        "campaign_id": campaign_id,
        "message": "Campaign started",
        "total": campaign.total if campaign else len(recipients),
    }


@router.get("/status/{campaign_id}", response_model=CampaignStatus)
async def campaign_status(campaign_id: str):
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.post("/cancel/{campaign_id}")
async def cancel_campaign_route(campaign_id: str):
    success = cancel_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail="Campaign is not running or not found.")
    return {"message": "Cancellation requested."}


@router.post("/retry")
async def retry_failed(request: Request, background_tasks: BackgroundTasks):
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    body = await request.json()
    campaign_id: str = body.get("campaign_id", "")
    delay_seconds: float = float(body.get("delay_seconds", settings.DEFAULT_DELAY_SECONDS))

    data = load_campaign(campaign_id)
    if not data:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if data.get("status") == "running":
        raise HTTPException(status_code=400, detail="Campaign is still running.")

    # Reset failed recipients
    retry_count = 0
    for r in data.get("recipients", []):
        if r.get("status") == "failed":
            r["status"] = "pending"
            r["error_message"] = None
            retry_count += 1

    if retry_count == 0:
        raise HTTPException(status_code=400, detail="No failed emails to retry.")

    data["status"] = "running"
    data["failed"] = 0
    data["pending"] = retry_count
    data["completed_at"] = None
    save_campaign(campaign_id, data)

    # Reconstruct body from campaign subject (body is not stored in DB, re-use subject as hint)
    # User must provide body again via retry — use stored body if available
    from app.services.email_service import _campaign_bodies
    email_body = _campaign_bodies.get(campaign_id, "")

    # Re-store body if provided in request
    if body.get("body"):
        email_body = body.get("body")
        store_body_for_campaign(campaign_id, email_body)

    # Find attachment
    attachment_path = None
    attachment_name = data.get("attachment_name")
    if attachment_name:
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
async def export_results(campaign_id: str, token: Optional[str] = None):
    data = load_campaign(campaign_id)
    if not data:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Company", "Status", "Error", "Timestamp"])

    for r in data.get("recipients", []):
        writer.writerow([
            r.get("name") or "",
            r.get("email") or "",
            r.get("company") or "",
            r.get("status") or "",
            r.get("error_message") or "",
            r.get("sent_at") or "",
        ])

    output.seek(0)
    filename = f"{campaign_id}_results.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

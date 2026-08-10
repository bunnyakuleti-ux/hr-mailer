import os
import uuid
import logging
import shutil
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import ParsedContactsResponse
from app.services.file_parser import parse_contacts

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_CONTACT_EXTENSIONS = {".csv", ".xlsx", ".xls"}
ALLOWED_ATTACHMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"}

# Track uploaded attachments
attachment_store: dict = {}


@router.post("/contacts", response_model=ParsedContactsResponse)
async def upload_contacts(
    file: UploadFile = File(...),
    email_column: Optional[str] = Form(None),
):
    """Upload and parse an Excel or CSV file containing HR contacts."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_CONTACT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Please upload .csv, .xlsx, or .xls",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        result = parse_contacts(file_bytes, file.filename, email_column=email_column)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error parsing contacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse the uploaded file.")

    return result


@router.post("/attachment")
async def upload_attachment(file: UploadFile = File(...)):
    """Upload an attachment to be used in emails."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported attachment type '{ext}'. Allowed: PDF, DOC, DOCX, TXT, PNG, JPG",
        )

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)

    if size_mb > settings.MAX_ATTACHMENT_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed: {settings.MAX_ATTACHMENT_SIZE_MB} MB",
        )

    # Save to disk with unique ID
    attachment_id = uuid.uuid4().hex
    safe_filename = os.path.basename(file.filename).replace("..", "").replace("/", "").replace("\\", "")
    save_path = os.path.join(UPLOAD_DIR, f"{attachment_id}_{safe_filename}")

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    attachment_store[attachment_id] = {
        "path": save_path,
        "filename": safe_filename,
        "size_mb": round(size_mb, 2),
    }

    logger.info(f"Attachment saved: {safe_filename} ({size_mb:.2f} MB) -> {save_path}")

    return {
        "attachment_id": attachment_id,
        "filename": safe_filename,
        "size_mb": round(size_mb, 2),
    }


@router.delete("/attachment/{attachment_id}")
async def delete_attachment(attachment_id: str):
    """Remove an uploaded attachment."""
    info = attachment_store.get(attachment_id)
    if not info:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    if os.path.exists(info["path"]):
        os.remove(info["path"])
    del attachment_store[attachment_id]
    return {"message": "Attachment removed."}


def get_attachment_info(attachment_id: str) -> Optional[dict]:
    return attachment_store.get(attachment_id)

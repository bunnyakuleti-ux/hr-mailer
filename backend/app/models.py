from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum
import datetime


class EmailStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class RecipientModel(BaseModel):
    row_index: int
    name: Optional[str] = None
    email: str
    company: Optional[str] = None
    is_valid: bool = True
    is_duplicate: bool = False
    status: EmailStatus = EmailStatus.PENDING
    error_message: Optional[str] = None
    sent_at: Optional[str] = None


class ParsedContactsResponse(BaseModel):
    total_rows: int
    valid_count: int
    invalid_count: int
    duplicate_count: int
    recipients: List[RecipientModel]
    columns: List[str]
    detected_email_column: Optional[str] = None
    detected_name_column: Optional[str] = None
    detected_company_column: Optional[str] = None


class EmailComposeRequest(BaseModel):
    campaign_id: str
    subject: str
    body: str
    recipient_indices: Optional[List[int]] = None  # None = all valid


class EmailPreviewRequest(BaseModel):
    subject: str
    body: str
    recipient: RecipientModel


class EmailPreviewResponse(BaseModel):
    from_email: str
    to_email: str
    subject: str
    body: str
    attachment_name: Optional[str] = None


class SendCampaignRequest(BaseModel):
    campaign_id: str
    subject: str
    body: str
    delay_seconds: float = 2.0
    recipient_indices: Optional[List[int]] = None


class CampaignStatus(BaseModel):
    campaign_id: str
    status: str  # running, completed, cancelled, failed
    total: int
    sent: int
    failed: int
    skipped: int
    pending: int
    current_recipient: Optional[str] = None
    recipients: List[RecipientModel] = []
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    subject: Optional[str] = None
    attachment_name: Optional[str] = None


class RetryRequest(BaseModel):
    campaign_id: str


class AuthStatus(BaseModel):
    connected: bool
    email: Optional[str] = None
    name: Optional[str] = None

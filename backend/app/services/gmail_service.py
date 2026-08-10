import base64
import os
import re
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def build_gmail_service(credentials: Credentials):
    """Build and return a Gmail API service instance."""
    return build("gmail", "v1", credentials=credentials)


def personalize_text(template: str, name: Optional[str], company: Optional[str], email: str) -> str:
    """Replace template variables with actual values."""
    result = template
    result = result.replace("{{name}}", name or "")
    result = result.replace("{{company}}", company or "")
    result = result.replace("{{email}}", email or "")
    # Clean up double spaces that might result from empty replacements
    result = re.sub(r"  +", " ", result)
    return result


def create_mime_message(
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    attachment_name: Optional[str] = None,
) -> MIMEMultipart:
    """Create a MIME email message with optional attachment."""
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject

    # Attach body as plain text
    message.attach(MIMEText(body, "plain", "utf-8"))

    # Attach file if provided
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            file_data = f.read()

        part = MIMEBase("application", "octet-stream")
        part.set_payload(file_data)
        encoders.encode_base64(part)

        safe_name = attachment_name or os.path.basename(attachment_path)
        part.add_header("Content-Disposition", f'attachment; filename="{safe_name}"')
        message.attach(part)

    return message


def encode_message(message: MIMEMultipart) -> dict:
    """Encode MIME message for Gmail API."""
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def send_email(
    service,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
    attachment_name: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Send an individual email via Gmail API.
    Returns (success: bool, error_message: Optional[str])
    """
    try:
        mime_message = create_mime_message(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
            attachment_name=attachment_name,
        )
        encoded = encode_message(mime_message)
        result = service.users().messages().send(userId="me", body=encoded).execute()
        logger.info(f"Email sent to {to_email}, message id: {result.get('id')}")
        return True, None
    except HttpError as e:
        error_msg = f"Gmail API error: {e.status_code} - {e.reason}"
        logger.error(f"Failed to send to {to_email}: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error sending to {to_email}: {error_msg}")
        return False, error_msg


def get_user_profile(service) -> Tuple[Optional[str], Optional[str]]:
    """Get authenticated user's email and name."""
    try:
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
        return email, None
    except Exception as e:
        return None, str(e)

import pandas as pd
import re
import io
from typing import Optional, Tuple, List
from app.models import RecipientModel, ParsedContactsResponse


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

# Common column name patterns
EMAIL_PATTERNS = ["email", "e-mail", "emailaddress", "email_address", "mail", "contact"]
NAME_PATTERNS = ["name", "fullname", "full_name", "firstname", "first_name", "candidate"]
COMPANY_PATTERNS = ["company", "organization", "org", "employer", "firm", "companyname", "company_name"]


def is_valid_email(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    value = value.strip()
    return bool(EMAIL_REGEX.match(value))


def detect_column(columns: List[str], patterns: List[str]) -> Optional[str]:
    """Detect a column by matching against known patterns (case-insensitive)."""
    normalized = {col: col.lower().replace(" ", "").replace("_", "") for col in columns}
    for col, norm in normalized.items():
        for pattern in patterns:
            if pattern in norm or norm in pattern:
                return col
    return None


def find_email_column_by_content(df: pd.DataFrame) -> Optional[str]:
    """Scan each column to find one that contains the most valid email addresses."""
    best_col = None
    best_count = 0
    for col in df.columns:
        count = df[col].astype(str).apply(lambda v: is_valid_email(v.strip())).sum()
        if count > best_count:
            best_count = count
            best_col = col
    return best_col if best_count > 0 else None


def parse_contacts(file_bytes: bytes, filename: str, email_column: Optional[str] = None) -> ParsedContactsResponse:
    """Parse an Excel or CSV file and extract contact information."""
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        else:
            raise ValueError("Unsupported file format. Please upload .csv, .xlsx, or .xls")
    except Exception as e:
        raise ValueError(f"Could not read file: {str(e)}")

    if df.empty:
        raise ValueError("The uploaded file is empty.")

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]
    columns = list(df.columns)

    # Detect columns
    if email_column and email_column not in columns:
        raise ValueError(f"Column '{email_column}' not found in file.")

    detected_email_col = email_column or detect_column(columns, EMAIL_PATTERNS) or find_email_column_by_content(df)
    detected_name_col = detect_column(columns, NAME_PATTERNS)
    detected_company_col = detect_column(columns, COMPANY_PATTERNS)

    if not detected_email_col:
        raise ValueError(
            "Could not detect an email column. Please ensure your file has a column named 'Email' or similar."
        )

    total_rows = len(df)
    recipients: List[RecipientModel] = []
    seen_emails = set()
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0

    for idx, row in df.iterrows():
        raw_email = str(row.get(detected_email_col, "")).strip()
        name = str(row.get(detected_name_col, "")).strip() if detected_name_col else None
        company = str(row.get(detected_company_col, "")).strip() if detected_company_col else None

        # Clean up "nan" values from pandas
        if name in ("nan", "None", ""):
            name = None
        if company in ("nan", "None", ""):
            company = None
        if raw_email in ("nan", "None", ""):
            raw_email = ""

        normalized_email = raw_email.lower()

        recipient = RecipientModel(
            row_index=int(str(idx)),
            name=name,
            email=raw_email,
            company=company,
        )

        if not raw_email or not is_valid_email(raw_email):
            recipient.is_valid = False
            recipient.error_message = "Invalid or missing email address"
            invalid_count += 1
        elif normalized_email in seen_emails:
            recipient.is_valid = False
            recipient.is_duplicate = True
            recipient.error_message = "Duplicate email address"
            duplicate_count += 1
        else:
            seen_emails.add(normalized_email)
            recipient.email = normalized_email  # store normalized
            valid_count += 1

        recipients.append(recipient)

    return ParsedContactsResponse(
        total_rows=total_rows,
        valid_count=valid_count,
        invalid_count=invalid_count,
        duplicate_count=duplicate_count,
        recipients=recipients,
        columns=columns,
        detected_email_column=detected_email_col,
        detected_name_column=detected_name_col,
        detected_company_column=detected_company_col,
    )

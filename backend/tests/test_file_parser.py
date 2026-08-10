"""Tests for file_parser service."""
import io
import pytest
import pandas as pd

from app.services.file_parser import (
    is_valid_email,
    detect_column,
    parse_contacts,
)


# ─── Email validation ────────────────────────────────────────────────────────

class TestIsValidEmail:
    def test_valid_emails(self):
        valid = [
            "user@example.com",
            "user.name+tag@domain.co.in",
            "hr@company.org",
            "test123@abc.io",
        ]
        for e in valid:
            assert is_valid_email(e), f"Expected valid: {e}"

    def test_invalid_emails(self):
        invalid = [
            "",
            "notanemail",
            "@nodomain.com",
            "no@",
            "spaces in@email.com",
            None,
            "double@@domain.com",
        ]
        for e in invalid:
            assert not is_valid_email(e), f"Expected invalid: {e}"


# ─── Column detection ────────────────────────────────────────────────────────

class TestDetectColumn:
    def test_detects_email_column(self):
        from app.services.file_parser import EMAIL_PATTERNS
        cols = ["Name", "Email", "Company"]
        assert detect_column(cols, EMAIL_PATTERNS) == "Email"

    def test_detects_name_column(self):
        from app.services.file_parser import NAME_PATTERNS
        cols = ["Full Name", "Contact Email", "Org"]
        result = detect_column(cols, NAME_PATTERNS)
        assert result is not None

    def test_returns_none_when_not_found(self):
        from app.services.file_parser import EMAIL_PATTERNS
        cols = ["Column1", "Column2"]
        assert detect_column(cols, EMAIL_PATTERNS) is None


# ─── CSV parsing ─────────────────────────────────────────────────────────────

class TestParseCsv:
    def _make_csv(self, rows: list[dict]) -> bytes:
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        return buf.getvalue()

    def test_basic_parsing(self):
        data = [
            {"Name": "Rahul", "Email": "rahul@abc.com", "Company": "ABC Tech"},
            {"Name": "Priya", "Email": "priya@xyz.com", "Company": "XYZ Ltd"},
        ]
        result = parse_contacts(self._make_csv(data), "test.csv")
        assert result.total_rows == 2
        assert result.valid_count == 2
        assert result.invalid_count == 0
        assert result.duplicate_count == 0

    def test_duplicate_removal(self):
        data = [
            {"Name": "A", "Email": "same@example.com", "Company": "Acme"},
            {"Name": "B", "Email": "SAME@example.com", "Company": "Acme"},  # dup
            {"Name": "C", "Email": "other@example.com", "Company": "Beta"},
        ]
        result = parse_contacts(self._make_csv(data), "test.csv")
        assert result.valid_count == 2
        assert result.duplicate_count == 1

    def test_invalid_emails_counted(self):
        data = [
            {"Name": "A", "Email": "valid@example.com", "Company": "X"},
            {"Name": "B", "Email": "not-an-email", "Company": "Y"},
            {"Name": "C", "Email": "", "Company": "Z"},
        ]
        result = parse_contacts(self._make_csv(data), "test.csv")
        assert result.valid_count == 1
        assert result.invalid_count == 2

    def test_empty_file_raises(self):
        df = pd.DataFrame()
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        with pytest.raises(ValueError):
            parse_contacts(buf.getvalue(), "empty.csv")

    def test_detects_email_column_automatically(self):
        data = [
            {"contact_email": "a@b.com", "FullName": "Alice"},
        ]
        result = parse_contacts(self._make_csv(data), "test.csv")
        assert result.valid_count == 1


# ─── Excel parsing ───────────────────────────────────────────────────────────

class TestParseExcel:
    def _make_xlsx(self, rows: list[dict]) -> bytes:
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        return buf.getvalue()

    def test_basic_xlsx_parsing(self):
        data = [
            {"Name": "Arun", "Email": "arun@pqr.com", "Company": "PQR"},
            {"Name": "Sneha", "Email": "sneha@lmn.com", "Company": "LMN"},
        ]
        result = parse_contacts(self._make_xlsx(data), "test.xlsx")
        assert result.total_rows == 2
        assert result.valid_count == 2

    def test_unsupported_extension(self):
        with pytest.raises(ValueError, match="Unsupported"):
            parse_contacts(b"data", "file.json")


# ─── Gmail service (mocked) ──────────────────────────────────────────────────

class TestGmailService:
    def test_personalize_text(self):
        from app.services.gmail_service import personalize_text
        tmpl = "Dear {{name}}, interested in {{company}}."
        result = personalize_text(tmpl, "Rahul", "ABC Tech", "rahul@abc.com")
        assert result == "Dear Rahul, interested in ABC Tech."

    def test_personalize_missing_values(self):
        from app.services.gmail_service import personalize_text
        result = personalize_text("Hi {{name}}", None, None, "x@y.com")
        assert "{{name}}" not in result

    def test_mime_message_created(self):
        from app.services.gmail_service import create_mime_message
        msg = create_mime_message("me@gmail.com", "hr@co.com", "Test", "Hello")
        assert msg["To"] == "hr@co.com"
        assert msg["Subject"] == "Test"

    def test_encode_message(self):
        from app.services.gmail_service import create_mime_message, encode_message
        import base64
        msg = create_mime_message("a@b.com", "c@d.com", "Subj", "Body")
        encoded = encode_message(msg)
        assert "raw" in encoded
        # Should be valid base64
        decoded = base64.urlsafe_b64decode(encoded["raw"] + "==")
        assert b"Subj" in decoded

    def test_send_email_returns_error_on_failure(self):
        """send_email should return (False, error_msg) on HttpError without raising."""
        from app.services.gmail_service import send_email
        from unittest.mock import MagicMock
        from googleapiclient.errors import HttpError

        mock_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 403
        mock_service.users().messages().send().execute.side_effect = HttpError(
            resp=mock_response, content=b"Quota exceeded"
        )
        success, error = send_email(mock_service, "me@gmail.com", "hr@co.com", "Subject", "Body")
        assert success is False
        assert error is not None

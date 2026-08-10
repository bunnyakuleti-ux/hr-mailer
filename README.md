# HR Mailer

> Send personalized job application emails with attachments — powered by Gmail API & Google OAuth 2.0.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Quick Start — Local Development](#quick-start)
5. [Gmail API Setup (Required)](#gmail-api-setup)
6. [Environment Variables](#environment-variables)
7. [Usage Workflow](#usage-workflow)
8. [Running Tests](#running-tests)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)
11. [Quotas & Limits](#quotas--limits)

---

## Overview

HR Mailer is a full-stack web application that lets you:

- Upload an Excel/CSV file of HR contacts
- Compose a personalized email with `{{name}}`, `{{company}}`, `{{email}}` variables
- Attach a resume or document
- Preview each personalized email before sending
- Send individual emails through your own Gmail account via Gmail API
- Track real-time progress and retry failed emails
- Export results as CSV

**Zero cost** — uses Gmail API directly, no paid email services needed.

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | React + Vite + TypeScript + Tailwind CSS |
| Backend    | Python + FastAPI                  |
| Auth       | Google OAuth 2.0                  |
| Email      | Gmail API (`gmail.send` scope)    |
| File Parse | pandas + openpyxl                 |

---

## Project Structure

```
hr-mailer/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── GmailConnect.tsx
│   │   │   ├── ContactsUpload.tsx
│   │   │   ├── EmailComposer.tsx
│   │   │   ├── AttachmentUpload.tsx
│   │   │   ├── EmailPreview.tsx
│   │   │   ├── SendConfirm.tsx
│   │   │   ├── SendingProgress.tsx
│   │   │   ├── Results.tsx
│   │   │   └── Stepper.tsx
│   │   ├── api.ts
│   │   ├── types.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── upload.py
│   │   │   └── email.py
│   │   └── services/
│   │       ├── gmail_service.py
│   │       ├── file_parser.py
│   │       └── email_service.py
│   ├── tests/
│   │   └── test_file_parser.py
│   ├── requirements.txt
│   └── .env.example
│
├── sample_hr_contacts.xlsx
├── sample_hr_contacts.csv
├── create_sample.py
├── .gitignore
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Google account
- Google Cloud project with Gmail API enabled (see below)

### 1. Clone / download the project

```bash
cd "email project"
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows CMD)
venv\Scripts\activate

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env
```

Edit `.env` and fill in your Google credentials (see Gmail API Setup below).

```bash
# Start backend
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000

### 3. Frontend setup

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

### 4. Generate sample data

```bash
# From project root
python create_sample.py
```

---

## Gmail API Setup

This is the **only manual step** required. Follow carefully.

### Step 1 — Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click **"Select a project"** → **"New Project"**
3. Name it `HR Mailer` → Click **Create**

### Step 2 — Enable Gmail API

1. In your project, go to **APIs & Services → Library**
2. Search for **"Gmail API"**
3. Click it → Click **Enable**

### Step 3 — Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** → Click **Create**
3. Fill in:
   - App name: `HR Mailer`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue**
5. On **Scopes** page, click **Add or Remove Scopes**
6. Add: `https://www.googleapis.com/auth/gmail.send`
7. Also add: `https://www.googleapis.com/auth/userinfo.email` and `openid`
8. Click **Save and Continue**
9. On **Test Users** page, click **Add Users** → add your Gmail address
10. Click **Save and Continue** → **Back to Dashboard**

> **Note:** While the app is in "Testing" mode, only added test users can sign in. This is fine for personal use.

### Step 4 — Create OAuth Client ID

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth Client ID**
3. Application type: **Web application**
4. Name: `HR Mailer Local`
5. Under **Authorized redirect URIs**, click **Add URI**:
   ```
   http://localhost:8000/api/auth/google/callback
   ```
6. Click **Create**
7. Copy your **Client ID** and **Client Secret**

### Step 5 — Add to .env

```env
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
FRONTEND_URL=http://localhost:5173
SECRET_KEY=generate_a_random_32_char_string_here
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_CLIENT_ID` | Yes | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Yes | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | Yes | Must match exactly what's in Google Console |
| `FRONTEND_URL` | Yes | Frontend origin for CORS |
| `SECRET_KEY` | Yes | Random secret for session security |
| `MAX_ATTACHMENT_SIZE_MB` | No | Default: 10 |
| `DEFAULT_DELAY_SECONDS` | No | Default: 2 |
| `MAX_RECIPIENTS_PER_CAMPAIGN` | No | Default: 500 |

---

## Usage Workflow

1. Open http://localhost:5173
2. Click **Sign in with Google** → complete OAuth
3. Upload `sample_hr_contacts.xlsx`
4. Review extracted contacts (valid/invalid/duplicate counts)
5. Write your email subject and body using `{{name}}`, `{{company}}`, `{{email}}`
6. Upload your resume PDF as attachment
7. Preview emails for individual recipients
8. Review the confirmation dialog
9. Click **Send Emails** — emails are sent one by one
10. Monitor real-time progress
11. Export results as CSV

---

## Running Tests

```bash
cd backend
venv\Scripts\activate   # or source venv/bin/activate on Mac/Linux
pytest tests/ -v
```

Tests cover:
- Email validation
- Duplicate removal
- CSV/Excel parsing
- Column auto-detection
- Variable replacement
- MIME message creation
- Error handling (mocked Gmail API)

---

## Deployment

### Free-tier options

#### Backend — Render.com (free tier)

1. Push code to GitHub (without `.env`)
2. Go to https://render.com → New → Web Service
3. Connect your repo → set root to `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables in Render dashboard

#### Frontend — Vercel (free tier)

1. Go to https://vercel.com → New Project
2. Connect your repo → set root to `frontend`
3. Add env var: `VITE_API_URL=https://your-render-backend.onrender.com`
4. Deploy

#### After deployment

Update `GOOGLE_REDIRECT_URI` in:
- Your `.env` / Render env vars: `https://your-backend.onrender.com/api/auth/google/callback`
- Google Cloud Console → Credentials → OAuth Client → Authorized redirect URIs

---

## Troubleshooting

### "Google OAuth credentials not configured"
→ Check that `.env` exists in the `backend/` folder with valid `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### "redirect_uri_mismatch" from Google
→ The `GOOGLE_REDIRECT_URI` in `.env` must exactly match what you added in Google Cloud Console. Check for trailing slashes or http vs https.

### "Access blocked: This app's request is invalid"
→ Your OAuth consent screen may not be configured. Follow Step 3 in Gmail API Setup above.

### "This app isn't verified"
→ While in Testing mode, only added Test Users can sign in. Add your Gmail to Test Users in the consent screen settings.

### Emails not sending / "Gmail API error: 403"
→ Make sure you enabled the Gmail API in Step 2. Also verify the `gmail.send` scope is added in Step 3.

### "Token has expired"
→ Sign out and reconnect Gmail. The app will get a fresh token.

### CSV file not detected
→ Make sure your CSV has a column named "Email", "email", "E-mail", or similar. You can manually select the column after upload.

### Backend CORS error
→ Make sure `FRONTEND_URL` in `.env` matches exactly where your frontend runs (default: `http://localhost:5173`).

---

## Quotas & Limits

- **Gmail free accounts**: ~500 emails/day
- **Google Workspace accounts**: ~2000 emails/day
- HR Mailer's default delay (2s between emails) respects these limits
- The app will display clear errors if Gmail API returns quota/rate-limit errors
- Do NOT attempt to bypass Gmail's sending limits — your account may be suspended

---

## Security Notes

- Your Gmail password is **never** stored or transmitted to this app
- OAuth tokens are stored in server-side sessions only (not in the browser)
- Client secret is never exposed to the frontend
- Uploaded files are stored temporarily and can be deleted after sending
- Add `.env` to `.gitignore` — **never commit your credentials**

---

*Built with ❤️ for job seekers. Gmail API usage is subject to Google's Terms of Service and quotas.*

# Udyam Verifier

FastAPI service to verify Udyam registration details (company name, email) using Playwright automation and CAPTCHA solving.

## API

**POST** `/verify`

```json
{
  "udyam_no": "UDYAM-XX-00-0000000",
  "company_name": "COMPANY NAME",
  "email": "email@example.com"
}
```

**Response:**
```json
{
  "company": "✅ Company Verified: 'COMPANY NAME' found",
  "email": "✅ Email Verified: 'email@example.com' found",
  "verdict": "FULLY VERIFIED"
}
```

## Run locally

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload
```

## Deploy on Render

Use the included `Dockerfile`. Set runtime to **Docker**.

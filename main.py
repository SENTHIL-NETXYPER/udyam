import io
import os
import re
from contextlib import redirect_stdout, redirect_stderr
from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import ddddocr

app = FastAPI()

class VerifyRequest(BaseModel):
    udyam_no: str

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    ocr = ddddocr.DdddOcr()

@app.get("/")
def root():
    return {"status": "ok", "message": "Udyam Verifier API"}

def get_captcha_text(page):
    if os.path.exists("captcha.png"):
        os.remove("captcha.png")
    captcha_elem = page.locator("img[src*='captcha'], img[src*='Captcha'], #ContentPlaceHolder1_imgCaptcha").first
    captcha_elem.screenshot(path="captcha.png")
    with open("captcha.png", "rb") as f:
        result = ocr.classification(f.read())
    text = result.strip().upper()
    return text

def navigate_to_verify(page):
    for nav_attempt in range(3):
        try:
            page.locator("text=Print/Verify").hover(timeout=15000)
            page.wait_for_timeout(1500)
            page.locator("text=Verify Udyam Registration").click(force=True, timeout=15000)
            page.wait_for_load_state("domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            return True
        except Exception:
            page.wait_for_timeout(2000)
    return False

@app.post("/verify")
def verify(req: VerifyRequest):
    if not req.udyam_no or not req.udyam_no.strip():
        return {"error": "udyam_no is required"}

    target = req.udyam_no.strip().upper()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=500)
        page = browser.new_page()
        page.set_default_timeout(60000)

        page.goto(
            "https://www.udyamregistration.gov.in/Default.aspx",
            wait_until="domcontentloaded",
            timeout=90000
        )
        page.wait_for_timeout(2000)

        success = navigate_to_verify(page)
        if not success:
            page.goto(
                "https://udyamregistration.gov.in/Udyam_Verify.aspx",
                wait_until="domcontentloaded",
                timeout=90000
            )
            page.wait_for_timeout(3000)

        page.locator('input[type="text"]').first.fill(req.udyam_no)

        for attempt in range(5):
            try:
                captcha_text = get_captcha_text(page)
            except Exception as e:
                browser.close()
                return {"error": f"CAPTCHA screenshot/OCR failed: {str(e)}"}

            captcha_input = page.locator(
                "#ContentPlaceHolder1_txtCaptcha, input[name*='Captcha'], input[name*='captcha'], input[placeholder*='erification']"
            ).first
            captcha_input.fill(captcha_text)
            page.wait_for_timeout(500)
            page.locator("#ctl00_ContentPlaceHolder1_btnVerify").click()
            page.wait_for_timeout(5000)

            body_text = page.locator("body").inner_text()
            body_lower = body_text.lower()
            if any(w in body_lower for w in ["invalid", "wrong", "incorrect", "cannot read", "does not support"]):
                continue

            browser.close()
            if target in body_text.upper():
                return {"status": "valid", "udyam_no": req.udyam_no}
            return {"status": "not verified", "udyam_no": req.udyam_no}

        browser.close()
        return {"error": "Failed to verify after 5 CAPTCHA attempts"}

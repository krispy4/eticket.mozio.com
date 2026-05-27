#!/usr/bin/env python3
"""
GO Transit E-Ticket Generator
==============================
Generates a ticket page, pushes it to GitHub Pages,
and sends a confirmation email to tade.adebajo@gmail.com.

Setup (one-time):
  pip install requests
"""

import smtplib
import base64
import json
import os
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

# ─────────────────────────────────────────────
#  CONFIG
#  When running via GitHub Actions: values come from repo secrets automatically.
#  When running locally: fill in the fallback values below.
# ─────────────────────────────────────────────

GITHUB_TOKEN   = os.environ.get("GH_PAT", "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN")
GITHUB_USER    = "krispy4"
GITHUB_REPO    = "eticket.mozio.com"

GMAIL_ADDRESS  = os.environ.get("GMAIL_ADDRESS", "tade.adebajo@gmail.com")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS", "YOUR_GMAIL_APP_PASSWORD")

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

TICKET_URL     = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}/"
RECIPIENT      = "tade.adebajo@gmail.com"

MONTH_NAMES_LONG = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"]

# ─────────────────────────────────────────────
#  DATE HELPERS
# ─────────────────────────────────────────────

def fmt_validity(d: datetime) -> str:
    return f"{MONTH_NAMES_LONG[d.month-1]} {d.day}, {d.year}"

def fmt_order_date(d: datetime) -> str:
    return d.strftime("%Y%m%d")

def random_suffix(length=8) -> str:
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ─────────────────────────────────────────────
#  GENERATE TICKET HTML
# ─────────────────────────────────────────────

def build_ticket_html(activation_time: datetime) -> str:
    template_path = Path(__file__).parent / "ticket.html"
    html = template_path.read_text(encoding="utf-8")
    iso = activation_time.strftime("%Y-%m-%dT%H:%M:%S")
    html = html.replace(
        "const ACTIVATION_TIME = new Date();",
        f'const ACTIVATION_TIME = new Date("{iso}");'
    )
    return html

# ─────────────────────────────────────────────
#  PUSH TO GITHUB PAGES
# ─────────────────────────────────────────────

def push_to_github(html_content: str) -> bool:
    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/index.html"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    encoded = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")

    sha = None
    resp = requests.get(api_url, headers=headers)
    if resp.status_code == 200:
        sha = resp.json().get("sha")

    payload = {
        "message": f"Update ticket - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, data=json.dumps(payload))

    if put_resp.status_code in (200, 201):
        print(f"✓ Ticket page pushed to {TICKET_URL}")
        return True
    else:
        print(f"✗ GitHub push failed: {put_resp.status_code} — {put_resp.text}")
        return False

# ─────────────────────────────────────────────
#  BUILD EMAIL HTML
# ─────────────────────────────────────────────

def build_email_html(valid_from: datetime, valid_to: datetime, order_number: str) -> str:
    template_path = Path(__file__).parent / "email_template.html"
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{ORDER_NUMBER}", order_number)
    html = html.replace("{VALID_FROM}", fmt_validity(valid_from))
    html = html.replace("{VALID_TO}",   fmt_validity(valid_to))
    html = html.replace("{TICKET_URL}", TICKET_URL)
    return html

# ─────────────────────────────────────────────
#  SEND EMAIL
# ─────────────────────────────────────────────

def send_email(html_body: str, order_number: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your GO Transit purchase, Confirmation {order_number}"
    msg["From"]    = f"GO Transit <{GMAIL_ADDRESS}>"
    msg["To"]      = RECIPIENT
    msg["Reply-To"] = "no-reply@email.gotransit.com"

    plain = (
        f"Hi Tade,\n\n"
        f"Your journey has now been confirmed.\n\n"
        f"Union Station GO to Bronte GO\n"
        f"Order #: {order_number}\n\n"
        f"View your ticket: {TICKET_URL}\n\n"
        f"Thank you for riding with GO Transit!"
    )

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            server.sendmail(GMAIL_ADDRESS, RECIPIENT, msg.as_string())
        print(f"✓ Email sent to {RECIPIENT}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    if "YOUR_GITHUB" in GITHUB_TOKEN or "YOUR_GMAIL" in GMAIL_APP_PASS:
        print("ERROR: Secrets not configured. Add GH_TOKEN, GMAIL_APP_PASS, and GMAIL_ADDRESS as repo secrets.")
        sys.exit(1)

    now      = datetime.now()
    valid_to = now + timedelta(days=7)
    order_no = f"{fmt_order_date(now)}-{random_suffix(8)}"

    print(f"\n🚆 GO Transit Ticket Generator")
    print(f"   Route:      Union Station GO → Bronte GO")
    print(f"   Valid:      {fmt_validity(now)} → {fmt_validity(valid_to)}")
    print(f"   Order #:    {order_no}")
    print(f"   Ticket URL: {TICKET_URL}\n")

    ticket_html = build_ticket_html(activation_time=now)

    pushed = push_to_github(ticket_html)
    if not pushed:
        print("Aborting — ticket page not published.")
        sys.exit(1)

    email_html = build_email_html(valid_from=now, valid_to=valid_to, order_number=order_no)
    sent = send_email(email_html, order_number=order_no)

    if pushed and sent:
        print("\n✅ Done! Check your inbox.")
    else:
        print("\n⚠️  Completed with errors — check output above.")

if __name__ == "__main__":
    main()

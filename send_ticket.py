#!/usr/bin/env python3
"""
GO Transit E-Ticket Generator
"""

import smtplib
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
# ─────────────────────────────────────────────

GITHUB_USER    = "krispy4"
GITHUB_REPO    = "eticket.mozio.com"
TICKET_URL     = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}/"
RECIPIENT      = "tade.adebajo@gmail.com"

GMAIL_ADDRESS  = os.environ.get("GMAIL_ADDRESS", "tade.adebajo@gmail.com")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS", "")
ROUTE          = os.environ.get("ROUTE", "Union Station GO to Bronte GO")
INCREMENT      = int(os.environ.get("INCREMENT", "300"))

MONTH_NAMES_LONG = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"]

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def fmt_validity(d: datetime) -> str:
    return f"{MONTH_NAMES_LONG[d.month-1]} {d.day}, {d.year}"

def fmt_order_date(d: datetime) -> str:
    return d.strftime("%Y%m%d")

def random_suffix(length=8) -> str:
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def gen_ticket_number(increment: int) -> str:
    state_path = Path(__file__).parent / "ticket_state.json"

    if state_path.exists():
        with open(state_path, "r") as f:
            state = json.load(f)
    else:
        state = {"last_ticket_number": 66801593}

    new_number = state["last_ticket_number"] + increment
    state["last_ticket_number"] = new_number

    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    return f"MZ{new_number}"

# ─────────────────────────────────────────────
#  BUILD TICKET HTML
# ─────────────────────────────────────────────

def build_ticket_html(activation_time: datetime, ticket_number: str) -> str:
    template_path = Path(__file__).parent / "ticket.html"
    html = template_path.read_text(encoding="utf-8")
    iso = activation_time.strftime("%Y-%m-%dT%H:%M:%S")
    html = html.replace(
        "const ACTIVATION_TIME = new Date();",
        f'const ACTIVATION_TIME = new Date("{iso}");'
    )
    html = html.replace("{TICKET_NUMBER}", ticket_number)
    html = html.replace("Union Station GO to Bronte GO", ROUTE)
    return html

# ─────────────────────────────────────────────
#  BUILD EMAIL HTML
# ─────────────────────────────────────────────

def build_email_html(valid_from: datetime, valid_to: datetime, order_number: str, ticket_number: str) -> str:
    template_path = Path(__file__).parent / "email_template.html"
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{ORDER_NUMBER}", order_number)
    html = html.replace("{VALID_FROM}", fmt_validity(valid_from))
    html = html.replace("{VALID_TO}", fmt_validity(valid_to))
    html = html.replace("{TICKET_URL}", TICKET_URL)
    html = html.replace("{TICKET_NUMBER}", ticket_number)
    html = html.replace("MZ66801593", ticket_number)
    html = html.replace("Union Station GO to Bronte GO", ROUTE)
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
        f"Hi Tade,\n\nYour journey has now been confirmed.\n\n"
        f"{ROUTE}\nOrder #: {order_number}\n\n"
        f"View your ticket: {TICKET_URL}\n\nThank you for riding with GO Transit!"
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
    now      = datetime.now()
    valid_to = now + timedelta(days=7)
    order_no = f"{fmt_order_date(now)}-{random_suffix(8)}"
    ticket_no = gen_ticket_number(INCREMENT)

    print(f"\n🚆 GO Transit Ticket Generator")
    print(f"   Route:      {ROUTE}")
    print(f"   Valid:      {fmt_validity(now)} → {fmt_validity(valid_to)}")
    print(f"   Order #:    {order_no}")
    print(f"   Ticket #:   {ticket_no}")
    print(f"   Ticket URL: {TICKET_URL}\n")

    ticket_html = build_ticket_html(activation_time=now, ticket_number=ticket_no)
    output_path = Path(__file__).parent / "index.html"
    output_path.write_text(ticket_html, encoding="utf-8")
    print(f"✓ index.html written")

    email_html = build_email_html(valid_from=now, valid_to=valid_to, order_number=order_no, ticket_number=ticket_no)
    send_email(email_html, order_number=order_no)

if __name__ == "__main__":
    main()

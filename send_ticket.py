#!/usr/bin/env python3
"""
GO Transit E-Ticket Generator
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

GITHUB_USER    = "krispy4"
GITHUB_REPO    = "eticket.mozio.com"
TICKET_URL     = "http://eticket.nnozio.com"
RECIPIENT      = "tade.adebajo@gmail.com"

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_5jUt3Ysp_JRrgndJbkfZqeM1qNXjDbQMc")
ROUTE          = os.environ.get("ROUTE", "Union Station GO to Bronte GO")
INCREMENT      = int(os.environ.get("INCREMENT", "300"))

FROM_EMAIL     = "GO Transit <info@nnozio.com>"

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
#  SEND EMAIL VIA RESEND
# ─────────────────────────────────────────────

def send_email(html_body: str, order_number: str) -> bool:
    print(f"DEBUG: API key length = {len(RESEND_API_KEY)}, first 6 = {RESEND_API_KEY[:6]}")
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": FROM_EMAIL,
                "to": [RECIPIENT],
                "subject": f"Your GO Transit purchase, Confirmation {order_number}",
                "reply_to": "no-reply@nnozio.com",
                "html": html_body
            }
        )
        if resp.status_code == 200 or resp.status_code == 201:
            print(f"✓ Email sent to {RECIPIENT}")
            return True
        else:
            print(f"✗ Email failed: {resp.status_code} — {resp.text}")
            return False
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

#!/usr/bin/env python3
"""
GO Transit E-Ticket Generator - WORK (Bronte GO to Union Station GO)
"""

import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

GITHUB_USER    = "krispy4"
GITHUB_REPO    = "eticket.mozio.com"
TICKET_URL     = "https://eticket.nnozio.com/oakville.html"
RECIPIENT      = "tade.adebajo@gmail.com"
RESEND_API_KEY = "re_5jUt3Ysp_JRrgndJbkfZqeM1qNXjDbQMc"
ROUTE          = "Oakville GO to Union Station GO"
INCREMENT      = 5000
OUTPUT_FILE    = "oakville.html"
FROM_EMAIL     = "GO Transit <info@nnozio.com>"

MONTH_NAMES_LONG = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"]

def fmt_validity(d):
    return f"{MONTH_NAMES_LONG[d.month-1]} {d.day}, {d.year}"

def fmt_order_date(d):
    return d.strftime("%Y%m%d")

def random_suffix(length=8):
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def gen_ticket_number(increment):
    state_path = Path(__file__).parent / "ticket_state.json"
    if state_path.exists():
        with open(state_path, "r") as f:
            state = json.load(f)
    else:
        state = {"last_ticket_number": 66898416}
    new_number = state["last_ticket_number"] + increment
    state["last_ticket_number"] = new_number
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
    return f"MZ{new_number}"

def build_ticket_html(activation_time, ticket_number):
    template_path = Path(__file__).parent / "ticket.html"
    html = template_path.read_text(encoding="utf-8")
    iso = activation_time.strftime("%Y-%m-%dT%H:%M:%S")
    html = html.replace("const ACTIVATION_TIME = new Date();", f'const ACTIVATION_TIME = new Date("{iso}");')
    html = html.replace("{TICKET_NUMBER}", ticket_number)
    html = html.replace("Union Station GO to Bronte GO", ROUTE)
    html = html.replace("Bronte GO to Union Station GO", ROUTE)
    html = html.replace("Oakville GO to Union Station GO", ROUTE)
    return html

def build_email_html(valid_from, valid_to, order_number, ticket_number):
    template_path = Path(__file__).parent / "email_template.html"
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{ORDER_NUMBER}", order_number)
    html = html.replace("{VALID_FROM}", fmt_validity(valid_from))
    html = html.replace("{VALID_TO}", fmt_validity(valid_to))
    html = html.replace("{TICKET_URL}", TICKET_URL)
    html = html.replace("{TICKET_NUMBER}", ticket_number)
    html = html.replace("MZ66801593", ticket_number)
    html = html.replace("Union Station GO to Bronte GO", ROUTE)
    html = html.replace("Bronte GO to Union Station GO", ROUTE)
    html = html.replace("Oakville GO to Union Station GO", ROUTE)
    return html

def send_email(html_body, order_number):
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": FROM_EMAIL, "to": [RECIPIENT], "subject": f"Your GO Transit purchase, Confirmation {order_number}", "html": html_body}
    )
    if resp.status_code in (200, 201):
        print(f"✓ Email sent to {RECIPIENT}")
    else:
        print(f"✗ Email failed: {resp.status_code} — {resp.text}")

def main():
    now      = datetime.now()
    valid_to = now + timedelta(days=7)
    order_no = f"{fmt_order_date(now)}-{random_suffix(8)}"
    ticket_no = gen_ticket_number(INCREMENT)

    print(f"\n🚆 GO Transit Ticket Generator (Oakville)")
    print(f"   Route:      {ROUTE}")
    print(f"   Ticket #:   {ticket_no}")
    print(f"   Ticket URL: {TICKET_URL}\n")

    ticket_html = build_ticket_html(activation_time=now, ticket_number=ticket_no)
    output_path = Path(__file__).parent / OUTPUT_FILE
    output_path.write_text(ticket_html, encoding="utf-8")
    print(f"✓ {OUTPUT_FILE} written")

    email_html = build_email_html(valid_from=now, valid_to=valid_to, order_number=order_no, ticket_number=ticket_no)
    send_email(email_html, order_number=order_no)

if __name__ == "__main__":
    main()

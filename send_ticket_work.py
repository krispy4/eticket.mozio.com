#!/usr/bin/env python3
"""
GO Transit E-Ticket Generator - WORK (combined: Bronte GO ↔ Union Station GO)
Generates two tickets per run: ticket_1 (Bronte→Union Station) and ticket_2 (ticket_1 + 1).
"""

import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

GITHUB_USER    = "krispy4"
GITHUB_REPO    = "eticket.mozio.com"

# Card 1: Bronte GO to Union Station GO  →  work.html
TICKET_URL_1   = "https://eticket.nnozio.com/work.html"
# Card 2: Union Station GO to Bronte GO  →  index.html
TICKET_URL_2   = "https://eticket.nnozio.com/index.html"

RECIPIENT      = "tade.adebajo@gmail.com"
RESEND_API_KEY = "re_5jUt3Ysp_JRrgndJbkfZqeM1qNXjDbQMc"
ROUTE_1        = "Bronte GO to Union Station GO"
ROUTE_2        = "Union Station GO to Bronte GO"
INCREMENT      = 7549
OUTPUT_FILE    = "work.html"
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

def gen_ticket_numbers(increment):
    """Returns (ticket_number_1, ticket_number_2) where ticket_2 = ticket_1 + 1."""
    state_path = Path(__file__).parent / "ticket_state.json"
    if state_path.exists():
        with open(state_path, "r") as f:
            state = json.load(f)
    else:
        state = {"last_ticket_number": 66801593}
    ticket_1 = state["last_ticket_number"] + increment
    ticket_2 = ticket_1 + 1
    state["last_ticket_number"] = ticket_2  # next run starts after ticket_2
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)
    return f"MZ{ticket_1}", f"MZ{ticket_2}"

def build_ticket_html(activation_time, ticket_number, route):
    template_path = Path(__file__).parent / "ticket.html"
    html = template_path.read_text(encoding="utf-8")
    iso = activation_time.strftime("%Y-%m-%dT%H:%M:%S")
    html = html.replace("const ACTIVATION_TIME = new Date();", f'const ACTIVATION_TIME = new Date("{iso}");')
    html = html.replace("{TICKET_NUMBER}", ticket_number)
    html = html.replace("Union Station GO to Bronte GO", route)
    html = html.replace("Bronte GO to Union Station GO", route)
    return html

def build_email_html(valid_from, valid_to, order_number, ticket_number_1, ticket_number_2):
    template_path = Path(__file__).parent / "email_template.html"
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{ORDER_NUMBER}", order_number)
    html = html.replace("{VALID_FROM}", fmt_validity(valid_from))
    html = html.replace("{VALID_TO}", fmt_validity(valid_to))
    html = html.replace("{TICKET_URL_1}", TICKET_URL_1)
    html = html.replace("{TICKET_URL_2}", TICKET_URL_2)
    html = html.replace("{TICKET_NUMBER_1}", ticket_number_1)
    html = html.replace("{TICKET_NUMBER_2}", ticket_number_2)
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
    ticket_no_1, ticket_no_2 = gen_ticket_numbers(INCREMENT)

    print(f"\n🚆 GO Transit Ticket Generator (Work — combined)")
    print(f"   Ticket 1:   {ticket_no_1}  ({ROUTE_1})")
    print(f"   Ticket 2:   {ticket_no_2}  ({ROUTE_2})")
    print(f"   Valid:      {fmt_validity(now)} → {fmt_validity(valid_to)}")
    print(f"   Order #:    {order_no}\n")

    # Build and write the work ticket page (Bronte → Union Station)
    ticket_html = build_ticket_html(activation_time=now, ticket_number=ticket_no_1, route=ROUTE_1)
    output_path = Path(__file__).parent / OUTPUT_FILE
    output_path.write_text(ticket_html, encoding="utf-8")
    print(f"✓ {OUTPUT_FILE} written ({ticket_no_1})")

    email_html = build_email_html(
        valid_from=now, valid_to=valid_to, order_number=order_no,
        ticket_number_1=ticket_no_1, ticket_number_2=ticket_no_2
    )
    send_email(email_html, order_number=order_no)

if __name__ == "__main__":
    main()

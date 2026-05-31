#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
# ]
# ///
"""
SF Events Emailer
Fetches upcoming events from plra.io for San Francisco and emails new ones.

Setup:
  pip3 install requests
"""

import json
import os
import re
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ─── CONFIGURATION ───────────────────────────────────────────────────────────

CITY_SLUG = "San Francisco_CA"
EVENTS_URL = f"https://plra.io/events/city/{CITY_SLUG}"
DAYS_AHEAD = 60

SENT_IDS_FILE = "/var/lib/sf_events_sent.txt"

SMTP_SERVER = "smtppro.zoho.com"
SMTP_PORT = 465
SENDER_EMAIL = "homeserver@itsshedtime.com"
RECIPIENT_EMAILS = ["agmetcalf@gmail.com"]
EMAIL_SUBJECT = "🎉 New SF Events on Plura"

# ─── FETCH EVENTS ────────────────────────────────────────────────────────────

def fetch_events_page(page: int) -> tuple:
    """Fetch one page of events; returns (events, next_page_or_None)."""
    params = {} if page == 1 else {"page": page}
    r = requests.get(EVENTS_URL, params=params, timeout=15)
    r.raise_for_status()
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        r.text,
        re.DOTALL,
    )
    if not m:
        raise ValueError("Could not find __NEXT_DATA__ in page HTML")
    data = json.loads(m.group(1))
    props = data["props"]["pageProps"]
    return props["events"], props.get("nextPage")


def fetch_all_events(days_ahead: int) -> list:
    """Fetch events starting within `days_ahead` days, paginating as needed."""
    cutoff = datetime.now(tz=timezone.utc) + timedelta(days=days_ahead)
    all_events = []
    page = 1
    while True:
        events, next_page = fetch_events_page(page)
        done = False
        for event in events:
            starts_at = datetime.fromisoformat(event["startsAt"].replace("Z", "+00:00"))
            if starts_at > cutoff:
                done = True
                break
            loc = event.get("location") or {}
            if loc.get("city") == "San Francisco":
                all_events.append(event)
        if done or next_page is None:
            break
        page = next_page
    return all_events

# ─── SENT IDS ────────────────────────────────────────────────────────────────

def load_sent_ids() -> set:
    path = Path(SENT_IDS_FILE)
    if not path.exists():
        return set()
    return set(path.read_text().splitlines())


def save_sent_ids(ids: set):
    Path(SENT_IDS_FILE).write_text("\n".join(sorted(ids)) + "\n")

# ─── EMAIL ───────────────────────────────────────────────────────────────────

def format_date(iso: str, tz_name: str) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo(tz_name))
    return dt.strftime("%a, %b %d · %-I:%M %p %Z")


def build_html(events: list) -> str:
    today_str = datetime.now().strftime("%B %d, %Y")
    count = len(events)
    cards = []
    for e in events:
        name = e["name"]
        url = e["url"]
        image = e.get("image", "")
        tz_name = e.get("timezone") or "America/Los_Angeles"
        date_str = format_date(e["startsAt"], tz_name)
        loc = e.get("location") or {}
        location_parts = [loc.get("name"), loc.get("city"), loc.get("region")]
        location_str = ", ".join(p for p in location_parts if p)

        img_tag = (
            f'<img src="{image}" alt="" style="width:100%;max-height:220px;'
            f'object-fit:cover;display:block;">'
            if image
            else ""
        )
        location_html = (
            f'<div style="color:#888;font-size:0.85em;margin-top:4px;">📍 {location_str}</div>'
            if location_str
            else ""
        )
        cards.append(f"""<div style="background:white;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-bottom:20px;overflow:hidden;">
  {img_tag}
  <div style="padding:16px 20px 18px;">
    <a href="{url}" style="font-size:1.05em;font-weight:700;color:#1a1a2e;text-decoration:none;line-height:1.4;">{name}</a>
    <div style="color:#555;font-size:0.9em;margin-top:8px;">📅 {date_str}</div>
    {location_html}
    <div style="margin-top:12px;">
      <a href="{url}" style="display:inline-block;background:#6a0dad;color:white;font-size:0.85em;font-weight:600;padding:6px 14px;border-radius:20px;text-decoration:none;">View Event →</a>
    </div>
  </div>
</div>""")

    cards_html = "\n".join(cards)
    plural = "s" if count != 1 else ""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0f5;margin:0;padding:20px;color:#333;">
<div style="max-width:620px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#6a0dad,#c44dff);padding:28px 32px;border-radius:12px 12px 0 0;color:white;">
    <h1 style="margin:0 0 4px;font-size:1.5em;">🎉 New SF Events on Plura</h1>
    <p style="margin:0;opacity:0.85;font-size:0.95em;">{count} new event{plural} · {today_str}</p>
  </div>
  <div style="padding:20px 0;">
{cards_html}
  </div>
  <div style="text-align:center;font-size:0.78em;color:#aaa;padding:0 0 16px;">
    <a href="https://plra.io/events/city/San%20Francisco_CA" style="color:#aaa;">View all SF events on Plura</a>
  </div>
</div>
</body>
</html>"""


def send_email(html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, os.environ["SENDER_PASS"])
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAILS, msg.as_string())

# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Email new SF events from plra.io")
    parser.add_argument("--email", action="store_true", help="Send email instead of printing HTML")
    parser.add_argument("--days", type=int, default=DAYS_AHEAD, help="Days ahead to include")
    args = parser.parse_args()

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Fetching SF events (next {args.days} days)...")
    try:
        events = fetch_all_events(args.days)
        print(f"  {len(events)} events found")

        sent_ids = load_sent_ids()
        new_events = [e for e in events if e["id"] not in sent_ids]
        print(f"  {len(new_events)} new (not previously sent)")

        if not new_events:
            print("Nothing to send.")
        else:
            html = build_html(new_events)
            if args.email:
                send_email(html)
                save_sent_ids(sent_ids | {e["id"] for e in new_events})
                print(f"[{datetime.now():%Y-%m-%d %H:%M}] Email sent to {', '.join(RECIPIENT_EMAILS)} ✓")
            else:
                print(html)
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} — {e.response.text}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise

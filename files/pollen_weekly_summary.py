#!/usr/bin/env python3
"""
Weekly Pollen Summary Emailer
Fetches pollen forecast from Ambee Pollen API and sends an HTML email.

Setup:
  pip3 install requests
"""

import os
import smtplib
import requests
from collections import defaultdict
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
# CONFIGURATION — edit these values
# ─────────────────────────────────────────────

# Ambee API key
# Sign up at: https://www.getambee.com/
AMBEE_API_KEY = os.environ["AMBEE_API_KEY"]

# Your location (Noe Valley, San Francisco)
LATITUDE  = 37.7477
LONGITUDE = -122.4208

# Email settings
SMTP_SERVER     = "smtppro.zoho.com"
SMTP_PORT       = 465
SENDER_EMAIL    = "homeserver@itsshedtime.com"

RECIPIENT_EMAILS = ["agmetcalf@gmail.com", "morgandavismetcalf@gmail.com"]
EMAIL_SUBJECT   = "🌿 Pollen Forecast"

# Species to always highlight prominently.
# Use the exact names Ambee returns under Species.Tree/Grass/Weed.
WATCHED_PLANTS = [
    "Cypress / Juniper / Cedar",
]

# ─────────────────────────────────────────────
# POLLEN LEVEL HELPERS
# ─────────────────────────────────────────────

RISK_LEVELS = ["Low", "Moderate", "High", "Very High"]

LEVEL_COLORS = {
    "Low":       "#8bc34a",
    "Moderate":  "#ffc107",
    "High":      "#ff5722",
    "Very High": "#b71c1c",
}

LEVEL_EMOJI = {
    "Low":       "🟡",
    "Moderate":  "🟠",
    "High":      "🔴",
    "Very High": "🚨",
}

def level_badge(risk: str) -> str:
    color = LEVEL_COLORS.get(risk, "#9e9e9e")
    emoji = LEVEL_EMOJI.get(risk, "⚪")
    return (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:12px;font-size:0.85em;font-weight:bold;">'
        f'{emoji} {risk}</span>'
    )

def max_risk(a: str, b: str) -> str:
    """Return the higher of two risk level strings."""
    rank = {r: i for i, r in enumerate(RISK_LEVELS)}
    return a if rank.get(a, -1) >= rank.get(b, -1) else b

# Thresholds: (min_count, risk_label)
_SPECIES_THRESHOLDS = {
    "Tree":  [(1500, "Very High"), (90, "High"), (15, "Moderate"), (0, "Low")],
    "Grass": [(200,  "Very High"), (20, "High"), ( 5, "Moderate"), (0, "Low")],
    "Weed":  [(500,  "Very High"), (50, "High"), (10, "Moderate"), (0, "Low")],
}

def count_to_risk(count: int, category: str) -> str:
    for threshold, label in _SPECIES_THRESHOLDS.get(category, []):
        if count >= threshold:
            return label
    return "Low"

# ─────────────────────────────────────────────
# API CALL
# ─────────────────────────────────────────────

def fetch_pollen_forecast() -> list:
    """
    Fetch forecast from Ambee and return a list of daily summaries:
    [
      {
        "date_str": "Mon, Mar 10",
        "tree_risk": "High", "grass_risk": "Low", "weed_risk": "Low",
        "tree_count": 150, "grass_count": 10, "weed_count": 5,
        "species": {"Oak": 80, "Birch": 50, ...}  # all species, all categories
      },
      ...
    ]
    """
    url = "https://api.ambeedata.com/forecast/pollen/by-lat-lng"
    headers = {"x-api-key": AMBEE_API_KEY, "Content-type": "application/json"}
    params  = {"lat": LATITUDE, "lng": LONGITUDE}
    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    data_points = r.json().get("data", [])

    # Group time-series points by local date (UTC date from ISO timestamp)
    by_date = defaultdict(list)
    for pt in data_points:
        dt = datetime.fromtimestamp(pt["time"], tz=timezone.utc)
        date_key = dt.astimezone().strftime("%Y-%m-%d")
        by_date[date_key].append(pt)

    daily = []
    for date_key in sorted(by_date.keys()):
        pts = by_date[date_key]
        dt  = datetime.strptime(date_key, "%Y-%m-%d")

        # Aggregate: max risk level and max count per category across the day
        tree_risk  = "Low"
        grass_risk = "Low"
        weed_risk  = "Low"
        tree_count  = 0
        grass_count = 0
        weed_count  = 0
        species_max = {}  # name -> {"count": int, "category": str}

        for pt in pts:
            risk    = pt.get("Risk", {})
            count   = pt.get("Count", {})
            species = pt.get("Species", {})

            tree_risk  = max_risk(tree_risk,  risk.get("tree_pollen",  "Low"))
            grass_risk = max_risk(grass_risk, risk.get("grass_pollen", "Low"))
            weed_risk  = max_risk(weed_risk,  risk.get("weed_pollen",  "Low"))

            tree_count  = max(tree_count,  count.get("tree_pollen",  0))
            grass_count = max(grass_count, count.get("grass_pollen", 0))
            weed_count  = max(weed_count,  count.get("weed_pollen",  0))

            for category_key, category_val in species.items():
                if not isinstance(category_val, dict):
                    continue
                for name, val in category_val.items():
                    if not isinstance(val, (int, float)):
                        continue
                    if name not in species_max or val > species_max[name]["count"]:
                        species_max[name] = {"count": val, "category": category_key}

        daily.append({
            "date_str":   dt.strftime("%a, %b %d"),
            "tree_risk":  tree_risk,
            "grass_risk": grass_risk,
            "weed_risk":  weed_risk,
            "tree_count":  tree_count,
            "grass_count": grass_count,
            "weed_count":  weed_count,
            "species":    dict(species_max),
        })

    return daily

# ─────────────────────────────────────────────
# EMAIL BUILDER
# ─────────────────────────────────────────────

def build_html(daily_info: list) -> str:
    today_str = datetime.now().strftime("%B %d, %Y")

    # ── Day rows ──────────────────────────────
    rows = []
    for day in daily_info:
        cells = [f'<td style="padding:8px 12px;font-weight:600;">{day["date_str"]}</td>']
        for key, count_key in [("tree_risk", "tree_count"), ("grass_risk", "grass_count"), ("weed_risk", "weed_count")]:
            risk  = day[key]
            count = day[count_key]
            cells.append(
                f'<td style="padding:8px 12px;text-align:center;">{level_badge(risk)}'
                f'<br><small style="color:#888;">{count} grains/m³</small></td>'
            )
        row_bg = "#ffffff" if len(rows) % 2 == 0 else "#f9f9f9"
        rows.append(f'<tr style="background:{row_bg};">{"".join(cells)}</tr>')

    table_rows = "\n".join(rows)

    # ── Watched plants section ────────────────
    # Peak count across all days
    watched_peak = {}
    for day in daily_info:
        for name, info in day["species"].items():
            if name not in WATCHED_PLANTS:
                continue
            if name not in watched_peak or info["count"] > watched_peak[name]["count"]:
                watched_peak[name] = {"count": info["count"], "category": info["category"]}

    watched_rows = []
    for name in WATCHED_PLANTS:
        info = watched_peak.get(name)
        if info:
            count    = info["count"]
            risk     = count_to_risk(count, info["category"])
            badge    = level_badge(risk)
            count_str = f'{count} grains/m³'
        else:
            badge     = '<span style="color:#aaa;">No data</span>'
            count_str = "—"

        row_bg = "#fff" if len(watched_rows) % 2 == 0 else "#f9f9f9"
        watched_rows.append(
            f'<tr style="background:{row_bg};">'
            f'<td style="padding:8px 12px;font-weight:600;">{name}</td>'
            f'<td style="padding:8px 12px;text-align:center;">{badge}'
            f'<br><small style="color:#888;">{count_str}</small></td>'
            f'</tr>'
        )

    watched_html = "\n".join(watched_rows)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#f4f4f4; margin:0; padding:20px; color:#333; }}
  .card {{ background:white; max-width:680px; margin:0 auto; border-radius:12px;
           box-shadow:0 2px 8px rgba(0,0,0,0.1); overflow:hidden; }}
  .header {{ background:linear-gradient(135deg,#2e7d32,#66bb6a);
             padding:28px 32px; color:white; }}
  .header h1 {{ margin:0 0 4px; font-size:1.5em; }}
  .header p  {{ margin:0; opacity:0.85; font-size:0.95em; }}
  .body  {{ padding:28px 32px; }}
  h2 {{ font-size:1em; color:#444; margin:24px 0 10px; text-transform:uppercase;
        letter-spacing:0.05em; }}
  table  {{ width:100%; border-collapse:collapse; font-size:0.93em; }}
  th     {{ background:#f0f4f0; padding:10px 12px; text-align:center;
             font-weight:600; color:#555; border-bottom:2px solid #e0e0e0; }}
  th:first-child {{ text-align:left; }}
  .footer   {{ text-align:center; font-size:0.78em; color:#aaa;
               padding:16px 32px 24px; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>🌿 Pollen Forecast</h1>
    <p>{today_str}</p>
  </div>
  <div class="body">
    <h2>📌 Watched Plants — Peak Count</h2>
    <table>
      <thead>
        <tr>
          <th style="text-align:left;">Plant</th>
          <th>Peak Level</th>
        </tr>
      </thead>
      <tbody>
        {watched_html}
      </tbody>
    </table>

    <h2>📅 Daily Overview</h2>
    <table>
      <thead>
        <tr>
          <th style="text-align:left;">Date</th>
          <th>🌳 Tree</th>
          <th>🌾 Grass</th>
          <th>🌿 Weed</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>
  <div class="footer">
    Data: Ambee Pollen API · Generated {today_str}<br>
  </div>
</div>
</body>
</html>
"""

# ─────────────────────────────────────────────
# SEND EMAIL
# ─────────────────────────────────────────────

def send_email(html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENT_EMAILS)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, os.environ["SENDER_PASS"])
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAILS, msg.as_string())

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pollen forecast — prints HTML to stdout by default.")
    parser.add_argument("--email", action="store_true", help="Send email instead of printing to stdout")
    args = parser.parse_args()

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Fetching pollen data...")
    try:
        daily_info = fetch_pollen_forecast()
        all_species = sorted({name for day in daily_info for name in day["species"]})
        print(f"Species returned: {', '.join(all_species)}")
        html = build_html(daily_info)
        if args.email:
            send_email(html)
            print(f"[{datetime.now():%Y-%m-%d %H:%M}] Email sent to {', '.join(RECIPIENT_EMAILS)} ✓")
        else:
            print(html)
    except requests.HTTPError as e:
        print(f"API error: {e.response.status_code} — {e.response.text}")
    except Exception as e:
        print(f"Error: {e}")
        raise

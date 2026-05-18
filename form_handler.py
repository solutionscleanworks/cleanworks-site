#!/usr/bin/env python3
"""Simple form handler — receives qualify form submissions and emails them via Himalaya."""
import json
import subprocess
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from datetime import datetime

PORT = 8900
NOTIFY_EMAIL = "CleanWorks.solutions1@gmail.com"
CALENDLY_URL = "https://calendly.com/solutionscleanworks/walk-through"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Submitting...</title>
<style>
  body { font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f9fafb; text-align: center; }
  .card { background: white; padding: 2.5rem; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 420px; }
  h2 { margin: 0 0 0.75rem; }
  p { color: #4b5563; margin: 0 0 1.5rem; line-height: 1.6; }
  .btn { display: inline-block; background: #1a56db; color: white; padding: 0.9rem 2rem; border-radius: 10px; font-weight: 700; text-decoration: none; font-size: 1.05rem; }
  .btn:hover { background: #1e40af; }
</style>
</head>
<body>
<div class="card">
  <h2>✅ Got it!</h2>
  <p>Now pick a time for your free 15-minute walkthrough — no obligation, no pressure.</p>
  <a href="REDIRECT_URL" class="btn">Schedule on Calendly →</a>
</div>
<script>window.location.href = "REDIRECT_URL";</script>
</body>
</html>"""


class FormHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = parse_qs(body)

        # Flatten
        fields = {k: v[0] if len(v) == 1 else v for k, v in data.items()}

        # Build email body
        name = fields.get("name", "Unknown")
        company = fields.get("company", "Unknown")
        email_addr = fields.get("email", "unknown")
        phone = fields.get("phone", "")

        lines = []
        labels = {
            "name": "Name", "phone": "Phone", "email": "Email",
            "company": "Company", "address": "Facility Address",
            "facility_type": "Facility Type", "sqft": "Square Footage",
            "employees": "Employees/Occupants",
            "has_cleaner": "Has Current Cleaner",
            "current_company": "Current Cleaning Company",
            "frequency": "Cleaning Frequency",
            "priority": "Top Priority",
            "pain_points": "Pain Points",
            "cleaning_time": "Preferred Cleaning Time",
            "special_requirements": "Special Requirements",
        }

        for key, label in labels.items():
            val = fields.get(key, "")
            if val:
                lines.append(f"<b>{label}:</b> {val}")

        html_body = f"""<html><body>
<h2>🔔 New Walkthrough Lead — {name} ({company})</h2>
<p>Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} AZ</p>
<hr>
<p>{'<br>'.join(lines)}</p>
<hr>
<p><small>Book them on Calendly: <a href="{CALENDLY_URL}">{CALENDLY_URL}</a></small></p>
</body></html>"""

        # Send email via Himalaya
        try:
            subprocess.run([
                "himalaya", "message", "send",
                "--to", NOTIFY_EMAIL,
                "--subject", f"New Lead: {name} — {company}",
                "--body-html", html_body,
            ], check=True, timeout=15, capture_output=True)
            print(f"[{datetime.now()}] Lead emailed: {name} ({company})", flush=True)
        except Exception as e:
            print(f"[{datetime.now()}] Email failed: {e}", flush=True)

        # Log to file
        log_path = os.path.expanduser("~/.hermes/output/qualify_leads.jsonl")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps({"timestamp": datetime.now().isoformat(), **fields}) + "\n")

        # Respond with success page
        html = TEMPLATE.replace("REDIRECT_URL", CALENDLY_URL)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # suppress default logs


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), FormHandler)
    print(f"Form handler running on :{PORT}", flush=True)
    server.serve_forever()

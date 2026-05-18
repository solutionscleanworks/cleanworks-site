#!/usr/bin/env python3
"""Single-server: serves static site + handles form submissions → emails via Himalaya."""
import json
import subprocess
import os
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime

PORT = 8900
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
NOTIFY_EMAIL = "CleanWorks.solutions1@gmail.com"
CALENDLY_URL = "https://calendly.com/solutionscleanworks/walk-through"

SUCCESS_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redirecting...</title>
<style>
  body {{ font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f9fafb; text-align: center; }}
  .card {{ background: white; padding: 2.5rem; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 420px; margin: 1rem; }}
  .check {{ font-size: 3rem; margin-bottom: 1rem; }}
  h2 {{ margin: 0 0 0.75rem; }}
  p {{ color: #4b5563; margin: 0 0 1.5rem; line-height: 1.6; }}
  .btn {{ display: inline-block; background: #1a56db; color: white; padding: 0.9rem 2rem; border-radius: 10px; font-weight: 700; text-decoration: none; font-size: 1.05rem; }}
  .btn:hover {{ background: #1e40af; }}
</style>
<script>setTimeout(function(){{ window.location.href = "{CALENDLY_URL}"; }}, 1500);</script>
</head>
<body>
<div class="card">
  <div class="check">✅</div>
  <h2>Got it!</h2>
  <p>Taking you to our calendar now — pick a time for your free 15-minute walkthrough.</p>
  <a href="{CALENDLY_URL}" class="btn">Schedule on Calendly →</a>
</div>
</body>
</html>"""

LABELS = {
    "name": "Name", "phone": "Phone", "email": "Email",
    "company": "Company", "address": "Facility Address",
    "facility_type": "Facility Type", "sqft": "Square Footage",
    "employees": "Employees / Occupants",
    "has_cleaner": "Has Current Cleaner",
    "current_company": "Current Cleaning Company",
    "frequency": "Cleaning Frequency",
    "priority": "Top Priority",
    "pain_points": "Pain Points",
    "cleaning_time": "Preferred Cleaning Time",
    "special_requirements": "Special Requirements",
}


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "":
            path = "/index.html"
        filepath = os.path.join(STATIC_DIR, path.lstrip("/"))

        if os.path.isfile(filepath) and STATIC_DIR in os.path.abspath(filepath):
            mime, _ = mimetypes.guess_type(filepath)
            self.send_response(200)
            self.send_header("Content-Type", mime or "text/html")
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_POST(self):
        if self.path != "/submit":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        data = parse_qs(body)
        fields = {k: v[0] if len(v) == 1 else v for k, v in data.items()}

        name = fields.get("name", "Unknown")
        company = fields.get("company", "Unknown")

        # Build email
        lines = []
        for key, label in LABELS.items():
            val = fields.get(key, "")
            if val:
                lines.append(f"<b>{label}:</b> {val}")

        html_body = f"""<html><body>
<h2>🔔 New Lead — {name} ({company})</h2>
<p><i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} AZ</i></p>
<hr>
<p>{'<br>'.join(lines)}</p>
<hr>
<p><small>📅 <a href="{CALENDLY_URL}">Calendly</a> | 📞 {fields.get('phone', 'N/A')}</small></p>
</body></html>"""

        # Send email
        try:
            subprocess.run([
                "himalaya", "message", "send",
                "--to", NOTIFY_EMAIL,
                "--subject", f"New Lead: {name} — {company}",
                "--body-html", html_body,
            ], check=True, timeout=15, capture_output=True)
            print(f"✅ Lead emailed: {name} ({company})", flush=True)
        except Exception as e:
            print(f"❌ Email failed: {e}", flush=True)

        # Log to file
        log_path = os.path.expanduser("~/.hermes/output/qualify_leads.jsonl")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(), **fields}) + "\n")

        # Respond
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(SUCCESS_PAGE.encode())

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"🚀 CleanWorks site + form handler on :{PORT}", flush=True)
    server.serve_forever()

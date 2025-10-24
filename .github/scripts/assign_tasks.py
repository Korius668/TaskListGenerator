import os
import json
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from datetime import date # ⬅️ ADD THIS LINE

# -------------------------------
# Load configuration
# -------------------------------
TASKS_JSON = os.environ["TASKS_JSON"]
PEOPLE_JSON = os.environ["PEOPLE_JSON"]

tasks = pd.DataFrame(json.loads(TASKS_JSON))
people = pd.DataFrame(json.loads(PEOPLE_JSON))

history_path = Path(".github/data/history.json")
if history_path.exists():
    with open(history_path, "r") as f:
        history = json.load(f)
else:
    history = {}

# -------------------------------
# Helper function: send email
# -------------------------------
def send_mail(to, subject, body):
    msg = MIMEText(body)
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to
    msg["Subject"] = subject

    server_host = os.environ["SMTP_SERVER"]
    server_port = int(os.environ["SMTP_PORT"])

    if server_port == 465:
        # SSL mode (e.g. Gmail)
        with smtplib.SMTP_SSL(server_host, server_port) as server:
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            server.send_message(msg)
    else:
        # STARTTLS mode (e.g. Mailtrap, Outlook, SendGrid)
        with smtplib.SMTP(server_host, server_port) as server:
            server.ehlo()
            server.starttls()
            server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            server.send_message(msg)
# -------------------------------
# Task assignment with rotation
# -------------------------------
tasks = tasks.sort_values("value", ascending=False)
assignments = {p["name"]: {"tasks": [], "value": 0} for _, p in people.iterrows()}
last_week = history.get("last_week", {})

for _, task in tasks.iterrows():
    eligible_people = [
        name for name in assignments.keys()
        if task["name"] not in last_week.get(name, [])
    ]
    if not eligible_people:
        eligible_people = list(assignments.keys())

    person = min(
        eligible_people,
        key=lambda n: assignments[n]["value"]
    )

    assignments[person]["tasks"].append(task["name"])
    assignments[person]["value"] += task["value"]

# -------------------------------
# Send emails
# -------------------------------
for _, p in people.iterrows():
    name, email = p["name"], p["email"]
    body = f"Hi {name},\n\nYour tasks for this week:\n"
    for t in assignments[name]["tasks"]:
        body += f" - {t}\n"
    body += f"\nTotal value: {assignments[name]['value']}\n\nBest,\nTaskBot"

    print(f"📧 Sending to {name} ({email})")
    send_mail(email, "Weekly Task Assignment", body)

print("✅ All tasks assigned and emails sent.")

# -------------------------------
# Save updated rotation history
# -------------------------------
new_history = {str(date.today()): {name: data["tasks"] for name, data in assignments.items()}}
history_path.parent.mkdir(parents=True, exist_ok=True)
with open(history_path, "w", encoding='utf-8') as f:
    json.dump(new_history, f, indent=2, ensure_ascii=False)

print("🗂️ Updated history saved to .github/data/history.json")

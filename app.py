import os
import json
import uuid
import logging
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
WORKSPACE_SCHEMA = os.environ.get("WORKSPACE_SCHEMA", "workspace_7paj63sou26l4ymm11nudt76g")

def get_db_connection():
    return psycopg2.connect(
        DATABASE_URL,
        options=f'-c search_path="{WORKSPACE_SCHEMA}",core,public'
    )

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not any([name, phone, email]):
        return jsonify({"error": "name, phone or email required"}), 400

    parts = name.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT MAX(position) FROM "person"')
    max_pos = (cur.fetchone()[0] or 0) + 1

    person_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    cur.execute("""
        INSERT INTO "person" (
            id, "createdAt", "updatedAt", "deletedAt",
            "nameFirstName", "nameLastName",
            "emailsPrimaryEmail", "emailsAdditionalEmails",
            "jobTitle", "phonesPrimaryPhoneNumber", "city",
            "avatarUrl", "avatarFile", position,
            "createdBySource", "createdByName", "createdByContext",
            "updatedBySource", "updatedByName", "updatedByContext"
        ) VALUES (
            %s, %s, %s, NULL,
            %s, %s,
            %s, NULL,
            %s, %s, NULL,
            NULL, NULL, %s,
            'WEBHOOK', 'Webhook', NULL,
            'WEBHOOK', 'Webhook', NULL
        )
    """, (
        person_id, now, now,
        first_name, last_name,
        email or None,
        message[:200] if message else None,
        phone or None,
        max_pos
    ))
    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Created lead: {person_id} ({email})")
    return jsonify({"success": True, "personId": person_id}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

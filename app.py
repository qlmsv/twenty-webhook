import os, json, uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

DATABASE_URL = os.environ.get("DATABASE_URL", "")
WORKSPACE_SCHEMA = os.environ.get("WORKSPACE_SCHEMA", "workspace_7paj63sou26l4ymm11nudt76g")
PORT = int(os.environ.get("PORT", "10000"))

class LeadHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        self.send_json(200, {"status": "ok"} if self.path == "/health" else {"error": "not found"})

    def do_POST(self):
        if self.path != "/webhook":
            self.send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode() or "{}")
        except:
            data = {}
        name = (data.get("name") or "").strip()
        phone = (data.get("phone") or "").strip()
        email = (data.get("email") or "").strip()
        message = (data.get("message") or "").strip()
        if not any([name, phone, email]):
            self.send_json(400, {"error": "name/phone/email required"})
            return
        parts = name.split(" ", 1)
        fn, ln = parts[0], parts[1] if len(parts) > 1 else ""
        if DATABASE_URL:
            try:
                import psycopg2
                conn = psycopg2.connect(DATABASE_URL, options=f'-c search_path="{WORKSPACE_SCHEMA}",core,public')
                cur = conn.cursor()
                cur.execute('SELECT MAX(position) FROM "person"')
                pos = (cur.fetchone()[0] or 0) + 1
                pid = str(uuid.uuid4())
                now = datetime.now(timezone.utc)
                cur.execute('INSERT INTO "person" (id, "createdAt", "updatedAt", "deletedAt", "nameFirstName", "nameLastName", "emailsPrimaryEmail", "emailsAdditionalEmails", "jobTitle", "phonesPrimaryPhoneNumber", "city", "avatarUrl", "avatarFile", position, "createdBySource", "createdByName", "createdByContext", "updatedBySource", "updatedByName", "updatedByContext") VALUES (%s,%s,%s,NULL,%s,%s,%s,NULL,%s,%s,NULL,NULL,NULL,%s,\'WEBHOOK\',\'Webhook\',NULL,\'WEBHOOK\',\'Webhook\',NULL)', (pid,now,now,fn,ln,email or None,message[:200] if message else None,phone or None,pos))
                conn.commit()
                cur.close(); conn.close()
                self.send_json(201, {"success": True, "personId": pid})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
        else:
            self.send_json(500, {"error": "DATABASE_URL not set"})

class ReuseServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"Listening on 0.0.0.0:{PORT}")
    ReuseServer(("0.0.0.0", PORT), LeadHandler).serve_forever()

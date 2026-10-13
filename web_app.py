"""Local web frontend for the Bill Splitter agent."""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent import BillSplitterAgent
from memory import BillMemory
from settlement import calculate_settlement
from tools import BillTools


HOST = "127.0.0.1"
PORT = 8000
FRONTEND_DIR = Path(__file__).parent / "frontend"
HISTORY_FILE = Path(__file__).parent / ".bill_history.json"


class BillSplitterWebApp:
    def __init__(self):
        self.memory = BillMemory()
        self.tools = BillTools(self.memory)
        self.agent = None
        self.messages = []
        self.history = self.load_history()
        self.lock = threading.Lock()

    def load_history(self):
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not load bill history: {exc}") from exc

    def save_history(self):
        try:
            HISTORY_FILE.write_text(
                json.dumps(self.history, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise RuntimeError(f"Could not save bill history: {exc}") from exc

    def get_agent(self):
        if self.agent is None:
            self.agent = BillSplitterAgent(self.tools)
        return self.agent

    def state(self):
        expenses = self.memory.get_expenses()
        settlement = calculate_settlement(expenses) if expenses else None
        return {
            "expenses": expenses,
            "summary": settlement,
            "messages": self.messages,
        }

    def chat(self, message):
        message = str(message).strip()
        if not message:
            raise ValueError("Message cannot be empty.")

        answer = self.get_agent().chat(message)
        self.messages.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ])
        return answer

    def reset(self):
        expenses = self.memory.get_expenses()
        if expenses:
            summary = calculate_settlement(expenses)
            self.history.insert(0, {
                "id": datetime.now(timezone.utc).isoformat(),
                "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                "total": summary["total"],
                "people": summary["people"],
                "settlements": summary["settlements"],
            })
            self.history = self.history[:50]
            self.save_history()
        self.memory.clear()
        self.agent = None
        self.messages = []


app = BillSplitterWebApp()


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5500")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5500")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with app.lock:
                self.send_json(200, app.state())
            return

        if path == "/api/history":
            with app.lock:
                self.send_json(200, {"history": app.history})
            return

        if path == "/" or path == "/index.html":
            self.serve_file("index.html", "text/html; charset=utf-8")
            return

        if path == "/styles.css":
            self.serve_file("styles.css", "text/css; charset=utf-8")
            return

        if path == "/app.js":
            self.serve_file("app.js", "text/javascript; charset=utf-8")
            return

        self.send_json(404, {"error": "Not found."})

    def serve_file(self, name, content_type):
        try:
            body = (FRONTEND_DIR / name).read_bytes()
        except OSError:
            self.send_json(404, {"error": "Frontend file not found."})
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            with app.lock:
                if path == "/api/chat":
                    payload = self.read_json()
                    answer = app.chat(payload.get("message", ""))
                    self.send_json(200, {"answer": answer, **app.state()})
                    return

                if path == "/api/reset":
                    app.reset()
                    self.send_json(200, app.state())
                    return

            self.send_json(404, {"error": "Not found."})
        except (ValueError, RuntimeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:  # Keep the API response explicit for frontend users.
            self.send_json(500, {"error": f"Agent request failed: {exc}"})


def main():
    server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    print(f"Bill Splitter frontend running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

"""Small local HTTP API for the React generator workspace."""

from __future__ import annotations

import argparse
import json
import threading
import traceback
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from pbc_chaos.web.events import now_iso
from pbc_chaos.web.runner import metadata_payload, run_web_command


class RunStore:
    """Thread-safe in-memory run store for local UI sessions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, dict[str, Any]] = {}

    def create(self, mode: str, options: dict[str, Any], command: str) -> dict[str, Any]:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        run = {
            "run_id": run_id,
            "mode": mode,
            "command": command,
            "status": "queued",
            "events": [],
            "artifacts": [],
            "result": None,
            "error": None,
        }
        with self._lock:
            self._runs[run_id] = run
        thread = threading.Thread(
            target=self._execute,
            args=(run_id, mode, options, command),
            daemon=True,
        )
        thread.start()
        return self.get(run_id)

    def get(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            return json.loads(json.dumps(run))

    def _append_event(self, run_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            run = self._runs[run_id]
            event = {"run_id": run_id, **event}
            run["events"].append(event)
            run["status"] = "failed" if event["status"] == "failed" else "running"
            if event.get("artifact"):
                run["artifacts"].append(event["artifact"])

    def _execute(self, run_id: str, mode: str, options: dict[str, Any], command: str) -> None:
        with self._lock:
            self._runs[run_id]["status"] = "running"
        try:
            result = run_web_command(
                mode,
                options,
                command,
                emit=lambda event: self._append_event(run_id, event),
            )
            with self._lock:
                run = self._runs[run_id]
                run["result"] = result
                if result.get("artifacts"):
                    known = {artifact["path"] for artifact in run["artifacts"]}
                    run["artifacts"].extend(
                        artifact for artifact in result["artifacts"] if artifact["path"] not in known
                    )
                run["status"] = "succeeded" if not result.get("passed") is False else "failed"
        except Exception as exc:  # pragma: no cover - exercised through local UI.
            with self._lock:
                run = self._runs[run_id]
                run["status"] = "failed"
                run["error"] = {
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=6),
                }
                run["events"].append(
                    {
                        "run_id": run_id,
                        "command": command,
                        "status": "failed",
                        "stage_id": "complete",
                        "stage_label": "Complete",
                        "message": str(exc),
                        "overall_percent": 100,
                        "workbook": None,
                        "artifact": None,
                        "severity": "error",
                        "timestamp": now_iso(),
                    }
                )


STORE = RunStore()


class Handler(BaseHTTPRequestHandler):
    server_version = "PBCChaosWeb/0.1"

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_empty(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/metadata":
            self._send_json(metadata_payload())
            return
        if parsed.path.startswith("/api/runs/"):
            run_id = parsed.path.rsplit("/", 1)[-1]
            try:
                self._send_json(STORE.get(run_id))
            except KeyError:
                self._send_json({"error": "run not found"}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_json({"ok": True, "service": "pbc-chaos-web"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/runs":
            self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            mode = str(payload.get("mode") or "")
            options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
            command = str(payload.get("command") or "")
            run = STORE.create(mode, options, command)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(run, status=HTTPStatus.ACCEPTED)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object.")
        return payload

    def _send_empty(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self._cors_headers()
        self.end_headers()

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local PBC Chaos web API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"PBC Chaos web API listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

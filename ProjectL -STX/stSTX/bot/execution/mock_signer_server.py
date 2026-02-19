from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/sign-and-broadcast":
            self.send_json(404, {"ok": False, "status": "failed", "reason": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else ""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self.send_json(400, {"ok": False, "status": "failed", "reason": "invalid_json"})
            return

        order_usd = float(payload.get("order_usd") or 0.0)
        fee_stx = float(payload.get("fee_stx") or 0.0)
        if order_usd <= 0:
            self.send_json(400, {"ok": False, "status": "failed", "reason": "invalid_order_usd"})
            return

        txid = "mock-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        response = {
            "ok": True,
            "status": "filled",
            "reason": "mock_filled",
            "txid": txid,
            "fee_stx": fee_stx,
            "filled_ststx": order_usd,
            "avg_fill_price_stx_per_ststx": 0.97,
            "filled_stx": order_usd * 0.97,
            "trade_pnl_stx": max(0.0, order_usd * 0.002 - fee_stx),
        }
        self.send_json(200, response)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8787), Handler)
    print("mock signer listening on http://127.0.0.1:8787/sign-and-broadcast")
    server.serve_forever()


if __name__ == "__main__":
    main()

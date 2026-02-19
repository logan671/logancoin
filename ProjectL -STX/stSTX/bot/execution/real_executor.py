from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print_json({"ok": False, "status": "failed", "reason": "empty_payload"})
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print_json({"ok": False, "status": "failed", "reason": "invalid_payload_json"})
        return

    signer_url = os.getenv("SIGNER_API_URL", "").strip()
    signer_token = os.getenv("SIGNER_API_TOKEN", "").strip()
    timeout_sec = int(os.getenv("SIGNER_TIMEOUT_SEC", "20"))

    if not signer_url:
        print_json(
            {
                "ok": False,
                "status": "failed",
                "reason": "missing_signer_api_url",
            }
        )
        return

    body = {
        "action": payload.get("action"),
        "order_usd": payload.get("order_usd"),
        "pool_id": payload.get("pool_id"),
        "edge_pct": payload.get("edge_pct"),
        "slippage_pct": payload.get("slippage_pct"),
        "stx_usd": payload.get("stx_usd"),
        "ststx_usd": payload.get("ststx_usd"),
        "fee_stx": payload.get("fee_stx"),
    }

    headers = {"Content-Type": "application/json"}
    if signer_token:
        headers["Authorization"] = f"Bearer {signer_token}"

    req = Request(
        url=signer_url,
        method="POST",
        headers=headers,
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
    )

    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            resp_body = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = ""
        try:
            raw = exc.read().decode("utf-8")
            if raw:
                payload = json.loads(raw)
                detail = str(payload.get("reason") or payload.get("error") or raw)[:120]
        except Exception:
            detail = ""
        print_json(
            {
                "ok": False,
                "status": "failed",
                "reason": f"signer_http_error:{exc.code}:{detail}" if detail else f"signer_http_error:{exc.code}",
            }
        )
        return
    except URLError as exc:
        print_json(
            {
                "ok": False,
                "status": "failed",
                "reason": f"signer_network_error:{exc.reason}",
            }
        )
        return
    except Exception as exc:
        print_json(
            {
                "ok": False,
                "status": "failed",
                "reason": f"signer_exception:{exc.__class__.__name__}",
            }
        )
        return

    try:
        result = json.loads(resp_body)
    except json.JSONDecodeError:
        print_json({"ok": False, "status": "failed", "reason": "invalid_signer_response_json"})
        return

    print_json(
        {
            "ok": bool(result.get("ok", False)),
            "status": str(result.get("status") or ("submitted" if result.get("ok") else "failed")),
            "reason": str(result.get("reason") or ""),
            "txid": result.get("txid"),
            "fee_stx": result.get("fee_stx", payload.get("fee_stx")),
            "filled_stx": result.get("filled_stx"),
            "filled_ststx": result.get("filled_ststx"),
            "avg_fill_price_stx_per_ststx": result.get("avg_fill_price_stx_per_ststx"),
            "trade_pnl_stx": result.get("trade_pnl_stx"),
        }
    )


def print_json(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()

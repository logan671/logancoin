from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"ok": False, "status": "failed", "reason": "empty_payload"}))
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"ok": False, "status": "failed", "reason": "invalid_payload_json"}))
        return

    order_usd = float(payload.get("order_usd") or 0.0)
    fee_stx = float(payload.get("fee_stx") or 0.0)
    if order_usd <= 0:
        print(json.dumps({"ok": False, "status": "failed", "reason": "invalid_order_usd"}))
        return

    # This stub simulates a successful fill so app-level live path can be tested end-to-end.
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filled_ststx = order_usd / 1.0
    avg_price = 0.97
    filled_stx = filled_ststx * avg_price
    trade_pnl_stx = max(0.0, order_usd * 0.002 - fee_stx)

    out = {
        "ok": True,
        "status": "filled",
        "reason": "stub_fill",
        "txid": f"stub-{now}",
        "fee_stx": fee_stx,
        "filled_stx": filled_stx,
        "filled_ststx": filled_ststx,
        "avg_fill_price_stx_per_ststx": avg_price,
        "trade_pnl_stx": trade_pnl_stx,
    }
    print(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()

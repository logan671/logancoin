import json
import os
import time

import websocket
from websocket._exceptions import WebSocketTimeoutException


WS_URL = "wss://ws.domeapi.io/{api_key}"


def main() -> None:
    api_key = os.environ.get("DOME_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("DOME_API_KEY is not set")

    address = os.environ.get(
        "DOME_TEST_ADDRESS",
        "0x811192618fB0C7fCc678a81bB7c796a554bCB832",
    ).lower()
    market_slugs = [
        s.strip()
        for s in os.environ.get("DOME_MARKET_SLUGS", "").split(",")
        if s.strip()
    ]

    filters = {}
    if address:
        filters["users"] = [address]
    if market_slugs:
        filters["market_slugs"] = market_slugs
    if not filters:
        raise SystemExit("Set DOME_TEST_ADDRESS or DOME_MARKET_SLUGS")

    ws = websocket.create_connection(
        WS_URL.format(api_key=api_key),
        timeout=60,
    )
    ws.settimeout(60)

    sub = {
        "action": "subscribe",
        "platform": "polymarket",
        "version": 1,
        "type": "orders",
        "filters": filters,
    }
    ws.send(json.dumps(sub))
    print("subscribed:", sub, flush=True)

    while True:
        try:
            msg = ws.recv()
            print(time.strftime("%F %T"), msg, flush=True)
        except WebSocketTimeoutException:
            try:
                ws.ping()
            except Exception:
                pass
            continue


if __name__ == "__main__":
    main()

import json
import logging
import time
from urllib import request
from urllib.error import URLError

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_MAX_RETRIES


def send_telegram_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for _ in range(max(1, TELEGRAM_MAX_RETRIES)):
        try:
            with request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    return True
        except URLError:
            time.sleep(1)
        except Exception:
            logging.exception("telegram_send_error")
            time.sleep(1)
    return False

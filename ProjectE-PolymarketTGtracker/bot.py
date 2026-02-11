import json
import re
import time
from typing import Optional

import requests

from config import BOT_TOKEN, CHANNEL_ID, OWNER_CHAT_ID, MAX_RETRIES
from db import (
    init_db,
    list_wallets,
    remove_wallet,
    set_state,
    get_state,
    upsert_wallet,
    update_alias,
    update_note,
    get_wallet,
    add_tracked_market,
    list_tracked_markets,
    add_tracked_position,
    list_tracked_positions,
    get_track_button,
    delete_track_button,
)

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def api_request(method: str, payload: dict) -> dict:
    url = f"{API_BASE}/{method}"
    for _ in range(MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            time.sleep(1)
    return {"ok": False}


def send_message(chat_id: str, text: str, parse_mode: Optional[str] = None) -> None:
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    api_request("sendMessage", payload)


def answer_callback(callback_id: str, text: str, alert: bool = False) -> None:
    api_request(
        "answerCallbackQuery",
        {"callback_query_id": callback_id, "text": text, "show_alert": alert},
    )


def get_owner_chat_id() -> Optional[str]:
    val = get_state("owner_chat_id")
    return val


def set_owner_chat_id(chat_id: str) -> None:
    set_state("owner_chat_id", chat_id)


def load_pending(chat_id: str) -> Optional[dict]:
    val = get_state(f"pending:{chat_id}")
    return json.loads(val) if val else None


def save_pending(chat_id: str, data: Optional[dict]) -> None:
    if data is None:
        set_state(f"pending:{chat_id}", "")
        return
    set_state(f"pending:{chat_id}", json.dumps(data))


def is_owner(chat_id: str) -> bool:
    owner = OWNER_CHAT_ID or get_owner_chat_id()
    if owner:
        return str(chat_id) == str(owner)
    return False


def handle_command(chat_id: str, text: str) -> None:
    parts = text.strip().split()
    cmd = parts[0].lower()

    if cmd == "/start":
        if not (OWNER_CHAT_ID or get_owner_chat_id()):
            set_owner_chat_id(str(chat_id))
            send_message(chat_id, "오너로 등록했습니다. /add 로 지갑을 추가하세요.")
        else:
            send_message(chat_id, "이미 오너가 설정되어 있습니다.")
        return

    if not is_owner(chat_id):
        send_message(chat_id, "읽기 전용 채널입니다. 관리자만 명령어를 사용할 수 있습니다.")
        return

    if cmd == "/help":
        send_message(
            chat_id,
            "/add <address> - 지갑 등록\n"
            "/remove <address> - 지갑 삭제\n"
            "/list - 지갑 목록\n"
            "/tracking - 추적 중인 폴 목록\n"
            "/alias <address> <별명> - 별명 설정\n"
            "/note <address> <메모> - 메모 설정\n"
            "/help - 도움말",
        )
        return

    if cmd == "/add":
        if len(parts) < 2:
            send_message(chat_id, "사용법: /add 0x...")
            return
        address = parts[1].lower()
        upsert_wallet(address, None, None)
        save_pending(chat_id, {"stage": "alias", "address": address})
        send_message(chat_id, "별명을 입력하세요. 없으면 'no' 입력")
        return

    if cmd == "/remove":
        if len(parts) < 2:
            send_message(chat_id, "사용법: /remove 0x...")
            return
        remove_wallet(parts[1].lower())
        send_message(chat_id, "삭제 완료")
        return

    if cmd == "/list":
        rows = list_wallets()
        if not rows:
            send_message(chat_id, "등록된 지갑이 없습니다.")
            return
        lines = []
        for addr, alias, note in rows:
            alias_label = alias if alias else "-"
            note_label = note if note else "-"
            lines.append(f"{addr} | {alias_label} | {note_label}")
        send_message(chat_id, "\n".join(lines))
        return

    if cmd == "/tracking":
        rows = list_tracked_positions(str(chat_id))
        if not rows:
            send_message(chat_id, "추적 중인 폴이 없습니다.")
            return
        lines = []
        for title, slug, outcome, side in rows:
            link = f"https://polymarket.com/market/{slug}"
            lines.append(f"• <a href=\"{link}\">{title}</a> ({outcome} {side})")
        send_message(chat_id, "\n".join(lines), parse_mode="HTML")
        return

    if cmd == "/alias":
        if len(parts) < 3:
            send_message(chat_id, "사용법: /alias 0x... 별명")
            return
        address = parts[1].lower()
        alias = " ".join(parts[2:])
        if get_wallet(address) is None:
            send_message(chat_id, "등록되지 않은 지갑입니다.")
            return
        update_alias(address, alias)
        send_message(chat_id, "별명 저장 완료")
        return

    if cmd == "/note":
        if len(parts) < 3:
            send_message(chat_id, "사용법: /note 0x... 메모")
            return
        address = parts[1].lower()
        note = " ".join(parts[2:])
        if get_wallet(address) is None:
            send_message(chat_id, "등록되지 않은 지갑입니다.")
            return
        update_note(address, note)
        send_message(chat_id, "메모 저장 완료")
        return

    send_message(chat_id, "알 수 없는 명령어입니다. /help")


def handle_pending(chat_id: str, text: str) -> bool:
    pending = load_pending(chat_id)
    if not pending:
        return False

    stage = pending.get("stage")
    address = pending.get("address")
    if not address:
        save_pending(chat_id, None)
        return False

    if stage == "alias":
        if text.strip().lower() != "no":
            update_alias(address, text.strip())
            send_message(chat_id, "별명 저장 완료")
        else:
            send_message(chat_id, "별명 없음으로 저장")
        save_pending(chat_id, {"stage": "note", "address": address})
        send_message(chat_id, "메모를 입력하세요. 없으면 'no' 입력")
        return True

    if stage == "note":
        if text.strip().lower() != "no":
            update_note(address, text.strip())
            send_message(chat_id, "메모 저장 완료")
        else:
            send_message(chat_id, "메모 없음으로 저장")
        save_pending(chat_id, None)
        return True

    save_pending(chat_id, None)
    return False


def poll() -> None:
    init_db()
    offset = int(get_state("bot_offset") or "0")

    while True:
        data = requests.get(
            f"{API_BASE}/getUpdates",
            params={"timeout": 30, "offset": offset + 1},
            timeout=35,
        ).json()

        if not data.get("ok"):
            time.sleep(2)
            continue

        for update in data.get("result", []):
            offset = update.get("update_id", offset)
            callback = update.get("callback_query")
            if callback:
                callback_id = callback.get("id")
                from_user = callback.get("from", {}).get("id")
                data_payload = callback.get("data") or ""
                if not is_owner(str(from_user)):
                    answer_callback(callback_id, "권한이 없습니다.", alert=True)
                else:
                    if data_payload.startswith("track:"):
                        token = data_payload.replace("track:", "", 1).strip()
                        data = get_track_button(token)
                        if not data:
                            answer_callback(callback_id, "추적 정보를 찾지 못했습니다.", alert=True)
                        else:
                            address, slug, title, outcome, side, _ = data
                            add_tracked_position(str(from_user), address, slug, title, outcome, side)
                            delete_track_button(token)
                            answer_callback(callback_id, "추적 목록에 추가했습니다.")
                continue
            message = update.get("message") or update.get("channel_post")
            if not message:
                continue
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text") or ""
            if not text:
                continue

            if handle_pending(str(chat_id), text):
                continue

            if text.startswith("/"):
                handle_command(str(chat_id), text)
            else:
                if is_owner(str(chat_id)):
                    send_message(
                        str(chat_id),
                        "명령어가 아닙니다. /help 를 입력해 사용법을 확인하세요.",
                    )
                else:
                    send_message(
                        str(chat_id),
                        "읽기 전용 채널입니다. 관리자만 명령어를 사용할 수 있습니다.",
                    )

        set_state("bot_offset", str(offset))
        time.sleep(1)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("PROJECTE_BOT_TOKEN is not set")
    poll()

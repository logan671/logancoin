import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import URLError

from backend.config import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_CHAT_ID
from backend.repositories.pairs import create_pair, delete_pair, list_pairs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STEP_SOURCE = "source"
STEP_FOLLOWER = "follower"
STEP_BUDGET = "budget"
STEP_KEY_REF = "key_ref"
STEP_SOURCE_ALIAS = "source_alias"
STEP_FOLLOWER_LABEL = "follower_label"


@dataclass
class AddPairDraft:
    source: str = ""
    follower: str = ""
    budget_usdc: float = 0.0
    key_ref: str = ""
    source_alias: str | None = None
    follower_label: str | None = None
    step: str = STEP_SOURCE


PENDING_ADDPAIR: dict[str, AddPairDraft] = {}


def _is_hex_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value))


def _short_address(value: str) -> str:
    if len(value) < 12:
        return value
    return f"{value[:6]}...{value[-4:]}"


def _main_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "/help"}, {"text": "/listpairs"}],
            [{"text": "/addpair"}, {"text": "/rmpair"}],
        ],
        "resize_keyboard": True,
    }


def _api_base() -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _is_owner(chat_id: str) -> bool:
    if not TELEGRAM_OWNER_CHAT_ID:
        return False
    return str(chat_id) == str(TELEGRAM_OWNER_CHAT_ID)


def _send_message(chat_id: str, text: str, use_keyboard: bool = False) -> None:
    body: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if use_keyboard:
        body["reply_markup"] = _main_keyboard()
    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        f"{_api_base()}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10):
            return
    except Exception:
        logging.exception("telegram_send_failed")


def _get_updates(offset: int) -> dict[str, Any]:
    params = parse.urlencode({"timeout": 25, "offset": offset + 1})
    url = f"{_api_base()}/getUpdates?{params}"
    with request.urlopen(url, timeout=35) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _cmd_help() -> str:
    return (
        "ProjectK 등록 봇 사용법\n\n"
        "1) 페어 목록 보기\n"
        "/listpairs\n\n"
        "2) 페어 추가하기(대화형)\n"
        "/addpair\n\n"
        "3) 페어 삭제하기\n"
        "/rmpair <pair_id>\n\n"
        "4) 진행중 입력 취소\n"
        "/cancel"
    )


def _addpair_start_message() -> str:
    return (
        "페어 추가를 시작합니다.\n"
        "1/6 카피할 주소(source)를 입력해주세요.\n"
        "예: 0x1111111111111111111111111111111111111111"
    )


def _handle_listpairs(chat_id: str) -> None:
    rows = list_pairs()
    if not rows:
        _send_message(chat_id, "등록된 페어가 없습니다.")
        return
    lines = []
    for r in rows:
        source_text = _short_address(r["source_address"])
        follower_text = _short_address(r["follower_address"])
        lines.append(
            f"#{r['id']} | {r.get('source_alias') or '-'}({source_text}) -> "
            f"{r.get('follower_label') or '-'}({follower_text}) | budget={r['budget_usdc']}"
        )
    _send_message(chat_id, "\n".join(lines), use_keyboard=True)


def _handle_addpair(chat_id: str, parts: list[str]) -> None:
    if len(parts) == 1:
        PENDING_ADDPAIR[chat_id] = AddPairDraft()
        _send_message(chat_id, _addpair_start_message(), use_keyboard=True)
        return

    if len(parts) < 5:
        _send_message(chat_id, "대화형으로 진행하려면 /addpair 만 입력하세요.", use_keyboard=True)
        return

    source = parts[1].lower()
    follower = parts[2].lower()
    if not _is_hex_address(source):
        _send_message(chat_id, "source 주소 형식이 올바르지 않습니다. 0x로 시작하는 42자리 주소를 넣어주세요.")
        return
    if not _is_hex_address(follower):
        _send_message(chat_id, "follower 주소 형식이 올바르지 않습니다. 0x로 시작하는 42자리 주소를 넣어주세요.")
        return
    try:
        budget = float(parts[3])
    except ValueError:
        _send_message(chat_id, "budget_usdc는 숫자여야 합니다.")
        return
    if budget <= 0:
        _send_message(chat_id, "budget_usdc는 0보다 커야 합니다.")
        return
    key_ref = parts[4]
    source_alias = parts[5] if len(parts) >= 6 else None
    follower_label = parts[6] if len(parts) >= 7 else None
    try:
        pair_id = create_pair(
            source_address=source,
            follower_address=follower,
            source_alias=source_alias,
            follower_label=follower_label,
            budget_usdc=budget,
            key_ref=key_ref,
            mode="live",
            active=1,
            min_order_usdc=1.0,
            max_order_usdc=None,
            max_slippage_bps=300,
            max_consecutive_failures=3,
            rpc_error_threshold=5,
            initial_matic=3.0,
            min_matic_alert=0.5,
        )
        _send_message(
            chat_id,
            (
                f"추가 완료: pair_id={pair_id}\n"
                f"- source: {_short_address(source)}\n"
                f"- follower: {_short_address(follower)}\n"
                f"- budget_usdc: {budget}\n\n"
                "확인하려면 /listpairs 를 보내세요."
            ),
            use_keyboard=True,
        )
    except ValueError as exc:
        _send_message(chat_id, f"추가 실패: {exc}", use_keyboard=True)
    except sqlite3.IntegrityError as exc:
        _send_message(chat_id, f"추가 실패: {exc}")


def _create_pair_from_draft(chat_id: str, draft: AddPairDraft) -> None:
    try:
        pair_id = create_pair(
            source_address=draft.source,
            follower_address=draft.follower,
            source_alias=draft.source_alias,
            follower_label=draft.follower_label,
            budget_usdc=draft.budget_usdc,
            key_ref=draft.key_ref,
            mode="live",
            active=1,
            min_order_usdc=1.0,
            max_order_usdc=None,
            max_slippage_bps=300,
            max_consecutive_failures=3,
            rpc_error_threshold=5,
            initial_matic=3.0,
            min_matic_alert=0.5,
        )
        _send_message(
            chat_id,
            (
                f"추가 완료: pair_id={pair_id}\n"
                f"- source: {_short_address(draft.source)}\n"
                f"- follower: {_short_address(draft.follower)}\n"
                f"- budget_usdc: {draft.budget_usdc}\n"
                f"- key_ref: {draft.key_ref}\n\n"
                "확인하려면 /listpairs 를 보내세요."
            ),
            use_keyboard=True,
        )
    except ValueError as exc:
        _send_message(chat_id, f"추가 실패: {exc}", use_keyboard=True)
    except sqlite3.IntegrityError as exc:
        _send_message(chat_id, f"추가 실패: {exc}", use_keyboard=True)


def _handle_addpair_wizard(chat_id: str, text: str) -> bool:
    draft = PENDING_ADDPAIR.get(chat_id)
    if not draft:
        return False

    value = text.strip()
    if not value:
        _send_message(chat_id, "값이 비어 있습니다. 다시 입력해주세요.", use_keyboard=True)
        return True

    if draft.step == STEP_SOURCE:
        source = value.lower()
        if not _is_hex_address(source):
            _send_message(chat_id, "source 주소 형식이 올바르지 않습니다. 0x로 시작하는 42자리 주소를 입력해주세요.")
            return True
        draft.source = source
        draft.step = STEP_FOLLOWER
        _send_message(chat_id, "2/6 따라할 지갑(follower) 주소를 입력해주세요.\n예: 0xa111111111111111111111111111111111111111")
        return True

    if draft.step == STEP_FOLLOWER:
        follower = value.lower()
        if not _is_hex_address(follower):
            _send_message(chat_id, "follower 주소 형식이 올바르지 않습니다. 0x로 시작하는 42자리 주소를 입력해주세요.")
            return True
        draft.follower = follower
        draft.step = STEP_BUDGET
        _send_message(chat_id, "3/6 시작 예산(USDC)을 입력해주세요.\n예: 200")
        return True

    if draft.step == STEP_BUDGET:
        try:
            budget = float(value)
        except ValueError:
            _send_message(chat_id, "예산은 숫자로 입력해주세요. 예: 200")
            return True
        if budget <= 0:
            _send_message(chat_id, "예산은 0보다 커야 합니다.")
            return True
        draft.budget_usdc = budget
        draft.step = STEP_KEY_REF
        _send_message(
            chat_id,
            (
                "4/6 key_ref를 입력해주세요.\n"
                "예: vault://wallet_1\n\n"
                "보안상 시드구문/프라이빗키는 텔레그램에 입력하지 마세요."
            ),
        )
        return True

    if draft.step == STEP_KEY_REF:
        if value.startswith("0x"):
            _send_message(chat_id, "key_ref 형식이 아닙니다. 예: vault://wallet_1")
            return True
        draft.key_ref = value
        draft.step = STEP_SOURCE_ALIAS
        _send_message(chat_id, "5/6 source 별칭을 입력해주세요. 없으면 '-' 입력")
        return True

    if draft.step == STEP_SOURCE_ALIAS:
        draft.source_alias = None if value == "-" else value
        draft.step = STEP_FOLLOWER_LABEL
        _send_message(chat_id, "6/6 follower 별칭을 입력해주세요. 없으면 '-' 입력")
        return True

    if draft.step == STEP_FOLLOWER_LABEL:
        draft.follower_label = None if value == "-" else value
        _create_pair_from_draft(chat_id, draft)
        PENDING_ADDPAIR.pop(chat_id, None)
        return True

    PENDING_ADDPAIR.pop(chat_id, None)
    _send_message(chat_id, "입력 상태가 초기화되었습니다. /addpair 로 다시 시작해주세요.", use_keyboard=True)
    return True


def _handle_rmpair(chat_id: str, parts: list[str]) -> None:
    if len(parts) < 2:
        _send_message(chat_id, "사용법: /rmpair <pair_id>")
        return
    try:
        pair_id = int(parts[1])
    except ValueError:
        _send_message(chat_id, "pair_id는 숫자여야 합니다.")
        return
    ok = delete_pair(pair_id)
    if ok:
        _send_message(chat_id, f"삭제 완료: pair_id={pair_id}", use_keyboard=True)
    else:
        _send_message(chat_id, f"삭제 실패: pair_id={pair_id} not found")


def _handle_text(chat_id: str, text: str) -> None:
    if _handle_addpair_wizard(chat_id, text):
        return

    parts = text.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    if cmd in ("/start", "/help"):
        _send_message(chat_id, _cmd_help(), use_keyboard=True)
    elif cmd == "/cancel":
        if chat_id in PENDING_ADDPAIR:
            PENDING_ADDPAIR.pop(chat_id, None)
            _send_message(chat_id, "진행 중인 /addpair 입력을 취소했습니다.", use_keyboard=True)
        else:
            _send_message(chat_id, "취소할 진행 작업이 없습니다.", use_keyboard=True)
    elif cmd == "/listpairs":
        _handle_listpairs(chat_id)
    elif cmd == "/addpair":
        _handle_addpair(chat_id, parts)
    elif cmd == "/rmpair":
        _handle_rmpair(chat_id, parts)
    else:
        _send_message(chat_id, "알 수 없는 명령어입니다. 아래 버튼이나 /help를 사용하세요.", use_keyboard=True)


def run() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("PROJECTK_TELEGRAM_BOT_TOKEN is not set")
    if not TELEGRAM_OWNER_CHAT_ID:
        raise SystemExit("PROJECTK_TELEGRAM_OWNER_CHAT_ID is not set")

    offset = 0
    while True:
        try:
            data = _get_updates(offset)
            if not data.get("ok"):
                time.sleep(2)
                continue
            for update in data.get("result", []):
                offset = update.get("update_id", offset)
                message = update.get("message")
                if not message:
                    continue
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text") or ""
                if not chat_id or not text:
                    continue
                if not _is_owner(chat_id):
                    _send_message(chat_id, "권한이 없습니다.")
                    continue
                _handle_text(chat_id, text)
        except URLError:
            time.sleep(2)
        except Exception:
            logging.exception("register_bot_error")
            time.sleep(2)


if __name__ == "__main__":
    run()

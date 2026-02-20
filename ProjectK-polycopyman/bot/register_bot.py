import json
import logging
import os
import re
import sqlite3
import socket
import time
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import URLError
import fcntl

from backend.config import DASHBOARD_URL, DB_PATH, RPC_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_CHAT_ID, USDC_TOKEN_ADDRESS
from backend.repositories.pairs import create_pair, delete_pair, list_pairs
from backend.repositories.runtime import heartbeat

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
    created_at: float = 0.0


PENDING_ADDPAIR: dict[str, AddPairDraft] = {}
_LOCK_FILE = "/tmp/projectk-register-bot.lock"
PENDING_TTL_SECONDS = 180
BOT_INSTANCE = f"{socket.gethostname()}:{os.getpid()}"


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
            [{"text": "/rmpairall"}, {"text": "/whereami"}],
            [{"text": "/site"}, {"text": "/status"}],
            [{"text": "/analyze"}],
            [{"text": "/howto"}],
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


def _get_updates(offset: int | None = None, timeout: int = 25) -> dict[str, Any]:
    params_dict: dict[str, Any] = {"timeout": timeout}
    if offset is not None:
        params_dict["offset"] = offset
    params = parse.urlencode(params_dict)
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
        "/rmpair <pair_id>\n"
        "/rmpairall\n\n"
        "4) 진행중 입력 취소\n"
        "/cancel\n\n"
        "5) 현재 봇 DB 확인\n"
        "/whereami\n\n"
        "6) 대시보드 주소 보기\n"
        "/site\n\n"
        "7) 팔로워 실잔고 보기(USDC/MATIC)\n"
        "/status\n\n"
        "8) 페어별 미체결/실패 원인 진단\n"
        "/analyze\n"
        "/analyze <pair_id>\n\n"
        "9) 등록 가이드 보기\n"
        "/howto"
    )


def _cmd_howto() -> str:
    return (
        "ProjectK 완전 상세 등록 가이드\n\n"
        "0) 서버 터미널 먼저 열기(맥 로컬 터미널에서)\n"
        "ssh -i /Users/hwlee/.ssh/keys/lightsail-default.pem ubuntu@43.203.122.192\n\n"
        "1) 서버에서 볼트 등록(니모닉 저장)\n"
        "cd ~/claudecode/ProjectK-polycopyman\n"
        "python3 -m backend.wallet_cli add <볼트이름>\n"
        "예: python3 -m backend.wallet_cli add bera11\n\n"
        "2) 명령 후 나오는 입력창 처리\n"
        "- '니모닉 입력(화면 비표시):' 가 뜨면 12/24단어 니모닉 붙여넣고 Enter\n"
        "- 화면에 글자가 안 보여도 정상(보안 처리)\n"
        "- 저장되면 key_ref가 출력됨 (예: vault://bera11)\n\n"
        "3) 텔레그램에서 /addpair 입력 후 6개 순서대로 입력\n"
        "- source 주소(카피할 지갑)\n"
        "- follower 주소(내 지갑)\n"
        "- 예산(USDC, 숫자만)\n"
        "- key_ref (예: vault://bera11)\n"
        "- source 별칭('-' 가능)\n"
        "- follower 별칭('-' 가능)\n\n"
        "4) 여러 개 등록할 때\n"
        "- 한 개 끝나면 다시 /addpair\n"
        "- 중간 취소: /cancel\n"
        "- 목록 확인: /listpairs\n"
        "- 전체 삭제: /rmpairall\n\n"
        "주의: 니모닉/프라이빗키는 텔레그램에 절대 입력하지 말 것"
    )


def _addpair_start_message() -> str:
    return (
        "페어 추가를 시작합니다.\n"
        "1/6 카피할 주소(source)를 입력해주세요.\n"
        "예: 0x1111111111111111111111111111111111111111"
    )


def _addpair_step_message(step: str) -> str:
    if step == STEP_SOURCE:
        return "1/6 카피할 주소(source)를 입력해주세요.\n예: 0x1111111111111111111111111111111111111111"
    if step == STEP_FOLLOWER:
        return "2/6 따라할 지갑(follower) 주소를 입력해주세요.\n예: 0xa111111111111111111111111111111111111111"
    if step == STEP_BUDGET:
        return "3/6 시작 예산(USDC)을 입력해주세요.\n예: 200"
    if step == STEP_KEY_REF:
        return "4/6 key_ref를 입력해주세요.\n예: vault://wallet_1"
    if step == STEP_SOURCE_ALIAS:
        return "5/6 source 별칭을 입력해주세요. 없으면 '-' 입력"
    if step == STEP_FOLLOWER_LABEL:
        return "6/6 follower 별칭을 입력해주세요. 없으면 '-' 입력"
    return "입력 상태를 알 수 없습니다. /cancel 후 /addpair 로 다시 시작해주세요."


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
        existing = PENDING_ADDPAIR.get(chat_id)
        if existing:
            _send_message(chat_id, f"이미 페어 추가 진행 중입니다.\n{_addpair_step_message(existing.step)}", use_keyboard=True)
            return
        PENDING_ADDPAIR[chat_id] = AddPairDraft(created_at=time.time())
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
            source_portfolio_usdc=None,
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
            source_portfolio_usdc=None,
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

    if draft.created_at <= 0:
        draft.created_at = time.time()
    if (time.time() - draft.created_at) > PENDING_TTL_SECONDS:
        PENDING_ADDPAIR.pop(chat_id, None)
        _send_message(chat_id, "이전 /addpair 입력이 시간 초과로 종료되었습니다. 다시 /addpair 를 입력해주세요.", use_keyboard=True)
        return True

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


def _handle_rmpairall(chat_id: str) -> None:
    rows = list_pairs()
    if not rows:
        _send_message(chat_id, "삭제할 페어가 없습니다.", use_keyboard=True)
        return
    deleted = 0
    deleted_ids: list[str] = []
    for row in rows:
        pair_id = int(row["id"])
        if delete_pair(pair_id):
            deleted += 1
            deleted_ids.append(str(pair_id))
    if deleted_ids:
        detail = ",".join(deleted_ids)
        _send_message(chat_id, f"전체 삭제 완료: {deleted}개\n삭제된 pair_id: {detail}", use_keyboard=True)
        return
    _send_message(chat_id, "전체 삭제를 시도했지만 삭제된 페어가 없습니다.", use_keyboard=True)


def _handle_whereami(chat_id: str) -> None:
    rows = list_pairs()
    _send_message(chat_id, f"bot db_path: {DB_PATH}\nactive_pairs: {len(rows)}\ninstance: {BOT_INSTANCE}", use_keyboard=True)


def _handle_site(chat_id: str) -> None:
    _send_message(chat_id, f"ProjectK 대시보드 주소:\n{DASHBOARD_URL}\ninstance: {BOT_INSTANCE}", use_keyboard=True)


def _rpc_call(method: str, params: list[Any]) -> Any:
    if not RPC_URL:
        raise ValueError("PROJECTK_RPC_URL is not set")
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")
    req = request.Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("error"):
        raise ValueError(str(body["error"]))
    return body.get("result")


def _erc20_balance_call_data(address: str) -> str:
    clean = address.lower().replace("0x", "")
    return "0x70a08231" + clean.rjust(64, "0")


def _get_matic_balance(address: str) -> float:
    raw = _rpc_call("eth_getBalance", [address, "latest"])
    return int(str(raw), 16) / 1_000_000_000_000_000_000


def _get_usdc_balance(address: str) -> float:
    if not USDC_TOKEN_ADDRESS:
        raise ValueError("PROJECTK_USDC_TOKEN_ADDRESS is not set")
    call_obj = {
        "to": USDC_TOKEN_ADDRESS,
        "data": _erc20_balance_call_data(address),
    }
    raw = _rpc_call("eth_call", [call_obj, "latest"])
    return int(str(raw), 16) / 1_000_000


def _handle_status(chat_id: str) -> None:
    rows = list_pairs()
    if not rows:
        _send_message(chat_id, "등록된 페어가 없습니다.", use_keyboard=True)
        return

    by_follower: dict[str, dict[str, Any]] = {}
    for row in rows:
        follower_address = str(row["follower_address"]).lower()
        existing = by_follower.get(follower_address)
        if not existing:
            by_follower[follower_address] = {
                "follower_address": follower_address,
                "follower_label": row.get("follower_label") or "-",
                "budget_usdc": float(row.get("budget_usdc") or 0.0),
                "pair_ids": [int(row["id"])],
            }
            continue
        existing["pair_ids"].append(int(row["id"]))
        existing["budget_usdc"] = max(float(existing["budget_usdc"]), float(row.get("budget_usdc") or 0.0))

    lines = [
        "ProjectK /status",
        f"instance: {BOT_INSTANCE}",
        f"rpc: {RPC_URL or 'not_set'}",
        "",
    ]

    for item in by_follower.values():
        follower_address = str(item["follower_address"])
        pair_ids = ",".join(str(v) for v in item["pair_ids"])
        label = str(item["follower_label"])
        budget_usdc = float(item["budget_usdc"])
        try:
            usdc = _get_usdc_balance(follower_address)
            matic = _get_matic_balance(follower_address)
            lines.append(
                (
                    f"pairs={pair_ids} | {label}({_short_address(follower_address)})\n"
                    f"- onchain_usdc: {usdc:.4f}\n"
                    f"- onchain_matic: {matic:.6f}\n"
                    f"- configured_budget_usdc: {budget_usdc:.4f}"
                )
            )
        except Exception as exc:
            lines.append(
                (
                    f"pairs={pair_ids} | {label}({_short_address(follower_address)})\n"
                    f"- status: balance_check_failed ({exc})\n"
                    f"- configured_budget_usdc: {budget_usdc:.4f}"
                )
            )
        lines.append("")

    lines.append("note: onchain_usdc/matic 기준이며, 포지션 토큰 잔고는 포함되지 않습니다.")
    _send_message(chat_id, "\n".join(lines).strip(), use_keyboard=True)


def _format_local_ts(ts: int | None) -> str:
    if not ts:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts)))


def _fetch_pair_diag_rows(pair_id: int | None = None) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if pair_id is None:
            rows = conn.execute(
                """
                SELECT
                  p.id AS pair_id,
                  p.created_at AS pair_created_at,
                  s.address AS source_address,
                  COALESCE(s.alias, '-') AS source_alias,
                  f.address AS follower_address,
                  COALESCE(f.label, '-') AS follower_label,
                  COALESCE(f.budget_usdc, 0) AS budget_usdc
                FROM wallet_pairs p
                JOIN source_wallets s ON s.id = p.source_wallet_id
                JOIN follower_wallets f ON f.id = p.follower_wallet_id
                WHERE p.active = 1
                ORDER BY p.id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
        row = conn.execute(
            """
            SELECT
              p.id AS pair_id,
              p.created_at AS pair_created_at,
              s.address AS source_address,
              COALESCE(s.alias, '-') AS source_alias,
              f.address AS follower_address,
              COALESCE(f.label, '-') AS follower_label,
              COALESCE(f.budget_usdc, 0) AS budget_usdc
            FROM wallet_pairs p
            JOIN source_wallets s ON s.id = p.source_wallet_id
            JOIN follower_wallets f ON f.id = p.follower_wallet_id
            WHERE p.id = ?
            """,
            (pair_id,),
        ).fetchone()
        return [dict(row)] if row else []
    finally:
        conn.close()


def _analyze_one_pair(pair_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        pair = conn.execute(
            """
            SELECT
              p.id AS pair_id,
              p.created_at AS pair_created_at,
              p.source_wallet_id,
              s.address AS source_address,
              COALESCE(s.alias, '-') AS source_alias,
              f.address AS follower_address,
              COALESCE(f.label, '-') AS follower_label,
              COALESCE(f.budget_usdc, 0) AS budget_usdc
            FROM wallet_pairs p
            JOIN source_wallets s ON s.id = p.source_wallet_id
            JOIN follower_wallets f ON f.id = p.follower_wallet_id
            WHERE p.id = ?
            """,
            (pair_id,),
        ).fetchone()
        if not pair:
            return f"pair_id={pair_id} 를 찾지 못했습니다."

        last_signal = conn.execute(
            """
            SELECT id, side, source_notional_usdc, source_price, tx_hash, market_slug, created_at
            FROM trade_signals
            WHERE source_wallet_id = ?
              AND created_at >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(pair["source_wallet_id"]), int(pair["pair_created_at"])),
        ).fetchone()
        unmirrored_cnt = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM trade_signals t
            LEFT JOIN mirror_orders m
              ON m.trade_signal_id = t.id
             AND m.pair_id = ?
            WHERE t.source_wallet_id = ?
              AND t.created_at >= ?
              AND m.id IS NULL
            """,
            (pair_id, int(pair["source_wallet_id"]), int(pair["pair_created_at"])),
        ).fetchone()
        last_order = conn.execute(
            """
            SELECT
              m.id AS order_id,
              m.trade_signal_id,
              m.status,
              m.blocked_reason,
              m.requested_notional_usdc,
              m.adjusted_notional_usdc,
              m.created_at
            FROM mirror_orders m
            WHERE m.pair_id = ?
            ORDER BY m.id DESC
            LIMIT 1
            """,
            (pair_id,),
        ).fetchone()
        status_counts = conn.execute(
            """
            SELECT m.status AS status, COUNT(*) AS cnt
            FROM mirror_orders m
            WHERE m.pair_id = ?
              AND m.created_at >= ?
            GROUP BY m.status
            ORDER BY cnt DESC
            """,
            (pair_id, int(time.time()) - 7200),
        ).fetchall()

        lines = [
            f"[진단] pair_id={pair_id}",
            f"- source: {_short_address(str(pair['source_address']))} ({pair['source_alias']})",
            f"- follower: {_short_address(str(pair['follower_address']))} ({pair['follower_label']})",
            f"- 현재 budget_usdc: {float(pair['budget_usdc']):.6f}",
            f"- pair 생성시각: {_format_local_ts(int(pair['pair_created_at']))}",
        ]

        if last_signal:
            lines.append(
                (
                    f"- 마지막 소스 신호: id={int(last_signal['id'])}, side={last_signal['side']}, "
                    f"notional={float(last_signal['source_notional_usdc']):.4f}, "
                    f"가격={float(last_signal['source_price'] or 0):.6f}, "
                    f"시각={_format_local_ts(int(last_signal['created_at']))}"
                )
            )
        else:
            lines.append("- 마지막 소스 신호: 없음(pair 생성 이후)")

        lines.append(f"- 미처리 신호 수: {int(unmirrored_cnt['cnt'] if unmirrored_cnt else 0)}")

        if last_order:
            lines.append(
                (
                    f"- 마지막 미러오더: order_id={int(last_order['order_id'])}, "
                    f"signal_id={int(last_order['trade_signal_id'])}, status={last_order['status']}, "
                    f"blocked_reason={last_order['blocked_reason'] or '-'}, "
                    f"requested={float(last_order['requested_notional_usdc']):.4f}, "
                    f"adjusted={float(last_order['adjusted_notional_usdc']):.4f}, "
                    f"시각={_format_local_ts(int(last_order['created_at']))}"
                )
            )
        else:
            lines.append("- 마지막 미러오더: 없음")

        if status_counts:
            compact = ", ".join(f"{str(r['status'])}:{int(r['cnt'])}" for r in status_counts)
            lines.append(f"- 최근 2시간 상태요약: {compact}")
        else:
            lines.append("- 최근 2시간 상태요약: 데이터 없음")
        return "\n".join(lines)
    finally:
        conn.close()


def _handle_analyze(chat_id: str, parts: list[str]) -> None:
    if len(parts) >= 2:
        try:
            pair_id = int(parts[1])
        except ValueError:
            _send_message(chat_id, "사용법: /analyze 또는 /analyze <pair_id>", use_keyboard=True)
            return
        _send_message(chat_id, _analyze_one_pair(pair_id), use_keyboard=True)
        return

    rows = _fetch_pair_diag_rows(None)
    if not rows:
        _send_message(chat_id, "활성 페어가 없습니다.", use_keyboard=True)
        return
    chunks = [_analyze_one_pair(int(r["pair_id"])) for r in rows]
    _send_message(chat_id, "\n\n".join(chunks), use_keyboard=True)


def _handle_text(chat_id: str, text: str) -> None:
    parts = text.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()

    # Commands must always work even during addpair wizard.
    if cmd.startswith("/"):
        # If user runs a normal command, end wizard state implicitly.
        if cmd not in ("/addpair", "/cancel") and chat_id in PENDING_ADDPAIR:
            PENDING_ADDPAIR.pop(chat_id, None)
        if cmd in ("/start", "/help"):
            _send_message(chat_id, _cmd_help(), use_keyboard=True)
            return
        if cmd == "/howto":
            _send_message(chat_id, _cmd_howto(), use_keyboard=True)
            return
        if cmd == "/cancel":
            if chat_id in PENDING_ADDPAIR:
                PENDING_ADDPAIR.pop(chat_id, None)
                _send_message(chat_id, "진행 중인 /addpair 입력을 취소했습니다.", use_keyboard=True)
            else:
                _send_message(chat_id, "취소할 진행 작업이 없습니다.", use_keyboard=True)
            return
        if cmd == "/listpairs":
            _handle_listpairs(chat_id)
            return
        if cmd == "/addpair":
            _handle_addpair(chat_id, parts)
            return
        if cmd == "/rmpair":
            _handle_rmpair(chat_id, parts)
            return
        if cmd == "/rmpairall":
            _handle_rmpairall(chat_id)
            return
        if cmd == "/whereami":
            _handle_whereami(chat_id)
            return
        if cmd == "/site":
            _handle_site(chat_id)
            return
        if cmd == "/status":
            _handle_status(chat_id)
            return
        if cmd == "/analyze":
            _handle_analyze(chat_id, parts)
            return
        _send_message(chat_id, "알 수 없는 명령어입니다. 아래 버튼이나 /help를 사용하세요.", use_keyboard=True)
        return

    if _handle_addpair_wizard(chat_id, text):
        return

    if cmd in ("/start", "/help"):
        _send_message(chat_id, _cmd_help(), use_keyboard=True)
    elif cmd == "/listpairs":
        _handle_listpairs(chat_id)
    elif cmd == "/addpair":
        _handle_addpair(chat_id, parts)
    elif cmd == "/rmpair":
        _handle_rmpair(chat_id, parts)
    elif cmd == "/rmpairall":
        _handle_rmpairall(chat_id)
    else:
        _send_message(chat_id, "알 수 없는 명령어입니다. 아래 버튼이나 /help를 사용하세요.", use_keyboard=True)


def run() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("PROJECTK_TELEGRAM_BOT_TOKEN is not set")
    if not TELEGRAM_OWNER_CHAT_ID:
        raise SystemExit("PROJECTK_TELEGRAM_OWNER_CHAT_ID is not set")

    lock_fd = open(_LOCK_FILE, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        raise SystemExit(f"another register_bot instance is already running: {_LOCK_FILE}") from exc

    offset: int | None = None
    # Drain stale backlog once at startup to avoid replaying old wizard messages.
    try:
        initial = _get_updates(offset=None, timeout=0)
        if initial.get("ok") and initial.get("result"):
            max_id = max(int(u.get("update_id", 0)) for u in initial["result"])
            offset = max_id + 1
    except Exception:
        logging.exception("register_bot_bootstrap_updates_error")

    while True:
        try:
            heartbeat("bot")
            data = _get_updates(offset=offset, timeout=25)
            if not data.get("ok"):
                time.sleep(2)
                continue
            for update in data.get("result", []):
                update_id = int(update.get("update_id", 0))
                if update_id:
                    offset = update_id + 1
                message = update.get("message")
                if not message:
                    continue
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text") or ""
                if not chat_id or not text:
                    continue
                logging.info("telegram_update chat_id=%s text=%s instance=%s", chat_id, text.strip(), BOT_INSTANCE)
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

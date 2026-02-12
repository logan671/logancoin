import logging
import os
import time
from typing import Optional
import html
import secrets

import requests
from eth_abi import decode
from web3 import Web3

from config import (
    BOT_TOKEN,
    CHANNEL_ID,
    RPC_URL,
    POLL_SECONDS,
    CONFIRMATIONS,
    MAX_BLOCK_RANGE,
    MAX_LAG_BLOCKS,
    CTF_EXCHANGE,
    MAX_RETRIES,
    MIN_USDC_ALERT,
    MIN_USDC_EXEMPT,
    SENT_EVENTS_TTL_DAYS,
    SENT_EVENTS_CLEANUP_INTERVAL_SECONDS,
    LOG_DIR,
    TRACKER_LOG_PATH,
)
from db import (
    init_db,
    list_wallets,
    get_state,
    set_state,
    is_sent_any,
    mark_sent_any,
    prune_old_sent_events,
    update_directional_streak,
    get_active_tracked_position,
    mark_tracked_position_exited,
    add_track_button,
)
from market_cache import get_market_for_token_fast

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

EVENT_TYPES = [
    "uint256",
    "uint256",
    "uint256",
    "uint256",
    "uint256",
]
EVENT_SIG = "OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"


def setup_logging() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=TRACKER_LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def api_request(method: str, payload: dict) -> None:
    url = f"{API_BASE}/{method}"
    for _ in range(MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                return
        except Exception:
            time.sleep(1)


def send_message(text: str, reply_markup: Optional[dict] = None) -> None:
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    api_request("sendMessage", payload)


def fmt_amount(value: int) -> str:
    return f"{value}"


def format_usdc(amount: Optional[int]) -> str:
    if amount is None:
        return "-"
    return f"${amount / 1_000_000:.2f}"

def format_shares_value(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def format_price(value: Optional[float] | str) -> str:
    try:
        num = float(value)  # type: ignore[arg-type]
        return f"{num:.4f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def build_message(
    address: str,
    alias: Optional[str],
    note: Optional[str],
    market: Optional[dict],
    side: str,
    outcome: str,
    price: str,
    usdc_amount: Optional[int],
    shares_amount: Optional[int],
    price_value: Optional[float],
    tx_hash: str,
    warn_multi: bool,
) -> str:
    safe_alias = html.escape(alias) if alias else address
    safe_note = html.escape(note) if note else ""
    safe_address = html.escape(address)

    if safe_note:
        label = f"{safe_alias} - {safe_note} ({safe_address})"
    else:
        label = f"{safe_alias} ({safe_address})" if alias else safe_address

    if market:
        title = html.escape(market.get("question") or "")
        slug = market.get("slug") or ""
    else:
        title = ""
        slug = ""

    link = f"https://polymarket.com/market/{slug}" if slug else ""
    outcome_label = html.escape(outcome) if outcome else "?"
    action = "구입했습니다" if side == "매수" else "판매했습니다" if side == "매도" else "거래했습니다"
    shares_est = None
    if price_value and usdc_amount is not None:
        shares_est = (usdc_amount / 1_000_000) / price_value if price_value != 0 else None
    elif shares_amount is not None:
        shares_est = shares_amount / 1_000_000

    direction = f"{outcome_label}를 {format_price(price)}에 총 {format_shares_value(shares_est)} shares {action}. 총 규모는 {format_usdc(usdc_amount)} 입니다."
    if outcome_label == "?":
        follow_line = "포지션 따라하려면?: -"
    elif side == "매도":
        follow_line = f"포지션 따라하려면?: {outcome_label} 매도 / 무포지션 관망"
    else:
        follow_line = f"포지션 따라하려면?: {outcome_label} {format_price(price)} 구매"

    subject_line = f"종목: {title}" if title else "종목: -"

    profile_link = f"https://polymarket.com/profile/{address}"

    lines = [
        f"지갑: {label}",
        "",
        "===================",
        "",
        f"💡 {subject_line}",
        "",
        f"방향: {direction}",
        "",
        follow_line,
        "",
        "===================",
        "",
        (
            f"👉 <a href=\"{html.escape(link)}\">해당 종목 폴리마켓 바로가기</a>"
            if link
            else "👉 해당 종목 폴리마켓 바로가기 (-)"
        ),
        f"🧑‍🎓 <a href=\"{html.escape(profile_link)}\">스마트 월렛 프로필 바로가기</a>",
        f"📲 <a href=\"https://polygonscan.com/tx/{html.escape(tx_hash)}\">트랜잭션 링크(폴리곤스캔)</a>",
    ]
    if side == "매도":
        lines.insert(8, "⚠️ << 그의 판단에 변경이 생긴것으로 보입니다! >>")
        lines.insert(9, "")
    if warn_multi:
        lines.insert(2, "⚠️ 이 트레이더는 이번 블록에 많은 거래를 진행했습니다. 실제 activity를 확인해주세요.")
    return "\n".join(lines)


def build_add_message(
    address: str,
    alias: Optional[str],
    note: Optional[str],
    market: Optional[dict],
    outcome: str,
    streak_count: int,
    usdc_amount: Optional[int],
    price: str,
    tx_hash: str,
) -> str:
    safe_alias = html.escape(alias) if alias else address
    safe_note = html.escape(note) if note else ""
    safe_address = html.escape(address)

    if safe_note:
        label = f"{safe_alias} - {safe_note} ({safe_address})"
    else:
        label = f"{safe_alias} ({safe_address})" if alias else safe_address

    title = html.escape((market or {}).get("question") or "-")
    slug = (market or {}).get("slug") or ""
    outcome_label = html.escape(outcome) if outcome else "?"
    market_link = f"https://polymarket.com/market/{slug}" if slug else ""
    profile_link = f"https://polymarket.com/profile/{address}"

    lines = [
        f"지갑: {label}",
        "",
        "===================",
        "",
        "🔁 반복 매수 감지",
        "",
        f"💡 종목: {title}",
        "",
        (
            f"방향: {outcome_label}를 같은 방향으로 연속 {streak_count}회 매수 중입니다. "
            f"최근 매수 규모는 {format_usdc(usdc_amount)} / 가격 {format_price(price)} 입니다."
        ),
        "",
        "포지션 따라하려면?: 기존 포지션 유지 + 리스크 재점검",
        "",
        "===================",
        "",
        (
            f"👉 <a href=\"{html.escape(market_link)}\">해당 종목 폴리마켓 바로가기</a>"
            if market_link
            else "👉 해당 종목 폴리마켓 바로가기 (-)"
        ),
        f"🧑‍🎓 <a href=\"{html.escape(profile_link)}\">스마트 월렛 프로필 바로가기</a>",
        f"📲 <a href=\"https://polygonscan.com/tx/{html.escape(tx_hash)}\">트랜잭션 링크(폴리곤스캔)</a>",
    ]
    return "\n".join(lines)


def detect_side(
    maker_in_watch: bool,
    taker_in_watch: bool,
    maker_asset_id: int,
    taker_asset_id: int,
    maker_amt: int,
    taker_amt: int,
) -> tuple[str, str, str, Optional[float], Optional[int], Optional[int]]:
    maker_market = None
    taker_market = None
    if maker_asset_id != 0:
        maker_market = get_market_for_token_fast(str(maker_asset_id))
    if taker_asset_id != 0:
        taker_market = get_market_for_token_fast(str(taker_asset_id))

    outcome = ""
    side = ""
    price = "N/A"
    price_value = None
    usdc_amount = None
    shares_amount = None

    if maker_asset_id == 0:
        # maker pays USDC -> BUY outcome tokens
        outcome = taker_market.get("outcome", "") if taker_market else ""
        if maker_in_watch:
            side = "매수"
        elif taker_in_watch:
            side = "매도"
        usdc_amount = maker_amt
        shares_amount = taker_amt
        if taker_amt > 0:
            price_value = maker_amt / taker_amt
            price = f"{price_value:.4f}"
    elif taker_asset_id == 0:
        # taker pays USDC -> maker is SELLER
        outcome = maker_market.get("outcome", "") if maker_market else ""
        if maker_in_watch:
            side = "매도"
        elif taker_in_watch:
            side = "매수"
        usdc_amount = taker_amt
        shares_amount = maker_amt
        if maker_amt > 0:
            price_value = taker_amt / maker_amt
            price = f"{price_value:.4f}"
    elif maker_market:
        outcome = maker_market.get("outcome", "")
        side = "매수/매도"
    elif taker_market:
        outcome = taker_market.get("outcome", "")
        side = "매수/매도"
    else:
        outcome = ""
        side = "매수/매도"

    return side, outcome or "?", price, price_value, usdc_amount, shares_amount


def poll() -> None:
    setup_logging()
    logging.info("tracker_start")
    init_db()
    if not RPC_URL:
        raise SystemExit("PROJECTE_RPC_URL is not set")
    if not BOT_TOKEN or not CHANNEL_ID:
        raise SystemExit("PROJECTE_BOT_TOKEN or PROJECTE_CHANNEL_ID is not set")

    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
    topic0 = w3.keccak(text=EVENT_SIG).hex()

    last_block = int(get_state("last_block") or "0")
    last_cleanup_at = 0

    while True:
        target = None
        try:
            now = int(time.time())
            if now - last_cleanup_at >= SENT_EVENTS_CLEANUP_INTERVAL_SECONDS:
                deleted = prune_old_sent_events(SENT_EVENTS_TTL_DAYS)
                last_cleanup_at = now
                if deleted > 0:
                    logging.info(
                        "sent_events_pruned deleted=%s ttl_days=%s",
                        deleted,
                        SENT_EVENTS_TTL_DAYS,
                    )

            latest = w3.eth.block_number
            target = max(latest - CONFIRMATIONS, 0)
            if last_block == 0:
                last_block = max(target - MAX_BLOCK_RANGE, 0)

            if target <= last_block:
                time.sleep(POLL_SECONDS)
                continue

            lag_blocks = target - last_block
            if lag_blocks > MAX_LAG_BLOCKS:
                last_block = target
                set_state("last_block", str(last_block))
                logging.warning(
                    "lag too large; jump to latest target=%s lag_blocks=%s",
                    target,
                    lag_blocks,
                )
                time.sleep(POLL_SECONDS)
                continue

            wallets = {row[0].lower(): row for row in list_wallets()}
            if not wallets:
                last_block = target
                set_state("last_block", str(last_block))
                time.sleep(POLL_SECONDS)
                continue

            exchanges = [
                Web3.to_checksum_address(addr.strip())
                for addr in CTF_EXCHANGE.split(",")
                if addr.strip()
            ]

            from_block = last_block + 1
            to_block = min(target, last_block + MAX_BLOCK_RANGE)

            logging.info("poll blocks=%s->%s target=%s", from_block, to_block, target)
            logs = w3.eth.get_logs(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": exchanges,
                    "topics": [topic0],
                }
            )
            if logs:
                logging.info("logs count=%s blocks=%s->%s", len(logs), from_block, to_block)

            match_count = 0
            alert_count = 0
            candidates: dict[tuple[str, str], dict] = {}
            for log in logs:
                try:
                    if len(log.get("topics", [])) < 4:
                        continue

                    data = decode(EVENT_TYPES, bytes(log["data"]))
                    (
                        maker_asset_id,
                        taker_asset_id,
                        maker_amt,
                        taker_amt,
                        fee,
                    ) = data

                    maker = Web3.to_checksum_address(
                        "0x" + log["topics"][2].hex()[-40:]
                    ).lower()
                    taker = Web3.to_checksum_address(
                        "0x" + log["topics"][3].hex()[-40:]
                    ).lower()
                    tx_hash = log["transactionHash"].hex()
                    log_index = log["logIndex"]
                    block_number = log["blockNumber"]

                    for addr in (maker, taker):
                        if addr not in wallets:
                            continue
                        match_count += 1

                        alias = wallets[addr][1]
                        note = wallets[addr][2]
                        maker_in_watch = addr == maker
                        taker_in_watch = addr == taker
                        side, outcome, price, price_value, usdc_amount, shares_amount = detect_side(
                            maker_in_watch,
                            taker_in_watch,
                            maker_asset_id,
                            taker_asset_id,
                            maker_amt,
                            taker_amt,
                        )

                        market = None
                        if maker_asset_id != 0:
                            market = get_market_for_token_fast(str(maker_asset_id))
                        if not market and taker_asset_id != 0:
                            market = get_market_for_token_fast(str(taker_asset_id))

                        key = (tx_hash, addr)
                        weight = usdc_amount or 0
                        if key not in candidates or weight > candidates[key]["weight"]:
                            candidates[key] = {
                                "addr": addr,
                                "alias": alias,
                                "note": note,
                                "market": market,
                                "side": side,
                                "outcome": outcome,
                                "price": price,
                                "price_value": price_value,
                                "usdc_amount": usdc_amount,
                                "shares_amount": shares_amount,
                                "tx_hash": tx_hash,
                                "weight": weight,
                                "log_index": log_index,
                                "block_number": block_number,
                                "maker_asset_id": maker_asset_id,
                                "taker_asset_id": taker_asset_id,
                            }
                except Exception as exc:
                    logging.exception("log_parse_error: %s", exc)

            block_counts: dict[tuple[str, int], int] = {}
            for item in candidates.values():
                key = (item["addr"], item["block_number"])
                block_counts[key] = block_counts.get(key, 0) + 1

            for item in candidates.values():
                if is_sent_any(item["tx_hash"], item["addr"]):
                    continue
                usdc_amount = item["usdc_amount"]
                if (
                    usdc_amount is not None
                    and (usdc_amount / 1_000_000) < MIN_USDC_ALERT
                    and item["addr"] != MIN_USDC_EXEMPT
                ):
                    continue
                market_key = None
                if item["market"] and item["market"].get("slug"):
                    market_key = item["market"]["slug"]
                else:
                    if item["market"] and item["market"].get("question"):
                        market_key = item["market"]["question"]
                if not market_key:
                    if item.get("maker_asset_id"):
                        market_key = f"token:{item['maker_asset_id']}"
                    elif item.get("taker_asset_id"):
                        market_key = f"token:{item['taker_asset_id']}"

                if not market_key:
                    continue

                streak_count, is_milestone = update_directional_streak(
                    item["addr"],
                    market_key,
                    item["outcome"],
                    item["side"],
                )

                if item["side"] == "매수":
                    if streak_count == 1:
                        pass
                    elif is_milestone and usdc_amount is not None and (usdc_amount / 1_000_000) >= MIN_USDC_ALERT:
                        msg = build_add_message(
                            item["addr"],
                            item["alias"],
                            item["note"],
                            item["market"],
                            item["outcome"],
                            streak_count,
                            item["usdc_amount"],
                            item["price"],
                            item["tx_hash"],
                        )
                        send_message(msg)
                        mark_sent_any(item["tx_hash"], item["addr"])
                        alert_count += 1
                        logging.info(
                            "alerted_add_only address=%s tx=%s streak=%s",
                            item["addr"],
                            item["tx_hash"],
                            streak_count,
                        )
                        continue
                    else:
                        mark_sent_any(item["tx_hash"], item["addr"])
                        continue

                warn_multi = block_counts.get((item["addr"], item["block_number"]), 0) > 1
                msg = build_message(
                    item["addr"],
                    item["alias"],
                    item["note"],
                    item["market"],
                    item["side"],
                    item["outcome"],
                    item["price"],
                    item["usdc_amount"],
                    item["shares_amount"],
                    item["price_value"],
                    item["tx_hash"],
                    warn_multi,
                )
                reply_markup = None
                slug = ""
                if item["market"] and item["market"].get("slug"):
                    slug = item["market"]["slug"]
                if slug:
                    token = secrets.token_urlsafe(6)
                    add_track_button(
                        token,
                        item["addr"],
                        slug,
                        item["market"].get("question") if item["market"] else slug,
                        item["outcome"],
                        item["side"],
                    )
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "추적하기", "callback_data": f"track:{token}"}]
                        ]
                    }
                send_message(msg, reply_markup=reply_markup)
                mark_sent_any(item["tx_hash"], item["addr"])
                alert_count += 1
                logging.info("alerted address=%s tx=%s", item["addr"], item["tx_hash"])

                slug = ""
                if item["market"] and item["market"].get("slug"):
                    slug = item["market"]["slug"]
                if slug:
                    tracked = get_active_tracked_position(item["addr"], slug)
                    if tracked:
                        chat_id, t_outcome, t_side, t_title, t_started = tracked
                        if t_outcome == item["outcome"] and t_side != item["side"]:
                            exit_msg = (
                                "⚠️ 결과 전에 포지션 변경/청산 가능성\n"
                                f"지갑: {item['addr']}\n"
                                f"종목: {t_title}\n"
                                f"이전: {t_outcome} {t_side}\n"
                                f"현재: {item['outcome']} {item['side']}\n"
                                f"tx: https://polygonscan.com/tx/{item['tx_hash']}"
                            )
                            send_message(exit_msg)
                            mark_tracked_position_exited(chat_id, item["addr"], slug, t_started, item["tx_hash"])

            if logs:
                logging.info("matches=%s alerts=%s", match_count, alert_count)

            last_block = to_block
            set_state("last_block", str(last_block))
        except Exception as exc:
            if "Block range is too large" in str(exc) and target is not None:
                last_block = max(target - MAX_BLOCK_RANGE, 0)
                set_state("last_block", str(last_block))
                logging.warning(
                    "block range too large; reset last_block=%s target=%s",
                    last_block,
                    target,
                )
                time.sleep(1)
                continue
            logging.exception("tracker_error")
            time.sleep(2)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    poll()

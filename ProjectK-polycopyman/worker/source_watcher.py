import logging
import time

from eth_abi import decode
from web3 import Web3

from backend.config import (
    RPC_URL,
    WATCHER_BACKOFF_ERROR_STREAK,
    WATCHER_BACKOFF_SLOW_TICK_MS,
    WATCHER_CONFIRMATIONS,
    WATCHER_EXCHANGES,
    WATCHER_MAX_BLOCK_RANGE,
    WATCHER_MAX_LAG_BLOCKS,
    WATCHER_POLL_MAX_SECONDS,
    WATCHER_POLL_MIN_SECONDS,
    WATCHER_POLL_SECONDS,
    WATCHER_RECOVERY_HEALTHY_TICKS,
)
from backend.db import get_conn
from backend.repositories.runtime import heartbeat
from backend.repositories.signals import create_chain_signal, list_active_source_wallet_addresses

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

EVENT_SIG = "OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
EVENT_TYPES = ["uint256", "uint256", "uint256", "uint256", "uint256"]


def _ensure_state_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watcher_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )


def _get_state(key: str) -> str | None:
    _ensure_state_table()
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM watcher_state WHERE key=?", (key,)).fetchone()
    return str(row["value"]) if row else None


def _set_state(key: str, value: str) -> None:
    _ensure_state_table()
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO watcher_state(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, value, now),
        )


def _detect_trade_for_address(
    address: str,
    maker: str,
    taker: str,
    maker_asset_id: int,
    taker_asset_id: int,
    maker_amt: int,
    taker_amt: int,
) -> tuple[str, str | None, float, float | None] | None:
    addr = address.lower()
    maker_in_watch = addr == maker
    taker_in_watch = addr == taker
    if not maker_in_watch and not taker_in_watch:
        return None

    usdc = 0.0
    shares = 0.0
    token_id: str | None = None
    side = ""

    if maker_asset_id == 0:
        token_id = str(taker_asset_id)
        usdc = maker_amt / 1_000_000
        shares = taker_amt / 1_000_000
        side = "buy" if maker_in_watch else "sell"
    elif taker_asset_id == 0:
        token_id = str(maker_asset_id)
        usdc = taker_amt / 1_000_000
        shares = maker_amt / 1_000_000
        side = "sell" if maker_in_watch else "buy"
    else:
        return None

    if usdc <= 0:
        return None
    price = (usdc / shares) if shares > 0 else None
    return side, token_id, usdc, price


def run() -> None:
    if not RPC_URL:
        raise SystemExit("PROJECTK_RPC_URL is not set")

    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
    topic0 = w3.keccak(text=EVENT_SIG).hex()
    if not topic0.startswith("0x"):
        topic0 = f"0x{topic0}"
    exchanges = [Web3.to_checksum_address(x.strip()) for x in WATCHER_EXCHANGES.split(",") if x.strip()]
    if not exchanges:
        raise SystemExit("PROJECTK_WATCHER_EXCHANGES is empty")

    last_block = int(_get_state("watcher_last_block") or "0")
    min_poll = max(1, WATCHER_POLL_MIN_SECONDS)
    max_poll = max(min_poll, WATCHER_POLL_MAX_SECONDS)
    poll_seconds = WATCHER_POLL_SECONDS
    if poll_seconds < min_poll or poll_seconds > max_poll:
        poll_seconds = min_poll
    error_streak = 0
    healthy_streak = 0

    while True:
        tick_started = time.monotonic()
        had_error = False
        try:
            heartbeat("watcher", extra={"poll_seconds": poll_seconds})
            latest = int(w3.eth.block_number)
            target = max(latest - WATCHER_CONFIRMATIONS, 0)

            if last_block == 0:
                last_block = max(target - WATCHER_MAX_BLOCK_RANGE, 0)
                _set_state("watcher_last_block", str(last_block))

            if target <= last_block:
                time.sleep(poll_seconds)
                continue

            lag = target - last_block
            if lag > WATCHER_MAX_LAG_BLOCKS:
                last_block = target
                _set_state("watcher_last_block", str(last_block))
                logging.warning("watcher_lag_jump target=%s lag_blocks=%s", target, lag)
                time.sleep(poll_seconds)
                continue

            watch = set(list_active_source_wallet_addresses())
            if not watch:
                last_block = target
                _set_state("watcher_last_block", str(last_block))
                time.sleep(poll_seconds)
                continue

            from_block = last_block + 1
            to_block = min(target, last_block + WATCHER_MAX_BLOCK_RANGE)
            logs = w3.eth.get_logs(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": exchanges,
                    "topics": [topic0],
                }
            )

            inserted = 0
            for log in logs:
                try:
                    topics = log.get("topics", [])
                    if len(topics) < 4:
                        continue
                    maker_asset_id, taker_asset_id, maker_amt, taker_amt, _fee = decode(
                        EVENT_TYPES, bytes(log["data"])
                    )
                    maker = Web3.to_checksum_address("0x" + topics[2].hex()[-40:]).lower()
                    taker = Web3.to_checksum_address("0x" + topics[3].hex()[-40:]).lower()
                    tx_hash = log["transactionHash"].hex()
                    log_index = int(log["logIndex"])
                    block_number = int(log["blockNumber"])

                    for addr in (maker, taker):
                        if addr not in watch:
                            continue
                        detected = _detect_trade_for_address(
                            address=addr,
                            maker=maker,
                            taker=taker,
                            maker_asset_id=int(maker_asset_id),
                            taker_asset_id=int(taker_asset_id),
                            maker_amt=int(maker_amt),
                            taker_amt=int(taker_amt),
                        )
                        if not detected:
                            continue
                        side, token_id, usdc_notional, price = detected
                        signal_id = create_chain_signal(
                            source_address=addr,
                            tx_hash=tx_hash,
                            log_index=log_index,
                            block_number=block_number,
                            side=side,
                            source_notional_usdc=usdc_notional,
                            source_price=price,
                            token_id=token_id,
                            outcome=None,
                            market_slug=None,
                            chain_id=137,
                        )
                        if signal_id:
                            inserted += 1
                except Exception:
                    logging.exception("watcher_parse_error")

            last_block = to_block
            _set_state("watcher_last_block", str(last_block))
            logging.info(
                "watcher_tick blocks=%s->%s logs=%s inserted_signals=%s watched_wallets=%s poll=%s",
                from_block,
                to_block,
                len(logs),
                inserted,
                len(watch),
                poll_seconds,
            )
        except Exception:
            had_error = True
            logging.exception("watcher_error")

        tick_ms = int((time.monotonic() - tick_started) * 1000)
        is_slow = tick_ms >= WATCHER_BACKOFF_SLOW_TICK_MS
        if had_error:
            error_streak += 1
            healthy_streak = 0
        else:
            error_streak = 0
            healthy_streak = healthy_streak + 1 if not is_slow else 0

        if had_error or is_slow:
            if error_streak >= WATCHER_BACKOFF_ERROR_STREAK or is_slow:
                poll_seconds = max_poll
        elif poll_seconds == max_poll and healthy_streak >= WATCHER_RECOVERY_HEALTHY_TICKS:
            poll_seconds = min_poll

        logging.info(
            "watcher_perf tick_ms=%s poll=%s error_streak=%s healthy_streak=%s",
            tick_ms,
            poll_seconds,
            error_streak,
            healthy_streak,
        )
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run()

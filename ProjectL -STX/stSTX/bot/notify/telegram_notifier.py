from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class BotEventPayload:
    event_type: str
    strategy: str
    event_time_utc: str
    pool_id: Optional[str] = None
    txid: Optional[str] = None
    side: Optional[str] = None
    order_size_usd: Optional[float] = None
    filled_stx: Optional[float] = None
    filled_ststx: Optional[float] = None
    avg_fill_price_stx_per_ststx: Optional[float] = None
    fee_stx: Optional[float] = None
    slippage_pct: Optional[float] = None
    edge_pct_at_decision: Optional[float] = None
    trade_pnl_stx: Optional[float] = None
    running_pnl_stx: Optional[float] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    trade_count: Optional[int] = None
    win_rate: Optional[float] = None
    max_drawdown_stx: Optional[float] = None
    actual_event_time_utc: Optional[str] = None
    actual_status: Optional[str] = None
    actual_reason: Optional[str] = None
    actual_filled_stx: Optional[float] = None
    actual_filled_ststx: Optional[float] = None
    actual_avg_fill_price_stx_per_ststx: Optional[float] = None
    actual_fee_stx: Optional[float] = None
    actual_trade_pnl_stx: Optional[float] = None


@dataclass(frozen=True)
class TelegramCommand:
    update_id: int
    text: str


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True, parse_mode: str = "Markdown"):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()
        self.enabled = enabled
        self.parse_mode = parse_mode.strip()
        self._last_update_id = 0

        if self.enabled:
            if not self.bot_token:
                raise ValueError("TG_BOT_TOKEN is required when notifier is enabled")
            if not self.chat_id:
                raise ValueError("TG_CHAT_ID is required when notifier is enabled")

    def send(self, payload: BotEventPayload) -> bool:
        if not self.enabled:
            return False

        text = self._render(payload)
        return self.send_text(text)

    def send_text(self, text: str) -> bool:
        if not self.enabled:
            return False
        self._post_message(text)
        return True

    def fetch_commands(self) -> list[TelegramCommand]:
        if not self.enabled:
            return []

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        body: dict[str, object] = {
            "timeout": 0,
            "limit": 20,
            "allowed_updates": ["message"],
        }
        if self._last_update_id > 0:
            body["offset"] = self._last_update_id + 1

        req = Request(
            url=url,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Telegram API returned status {resp.status}")
                payload = json.loads(resp.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Failed to fetch telegram updates: {exc}") from exc

        if not payload.get("ok"):
            description = str(payload.get("description", "unknown telegram getUpdates error"))
            raise RuntimeError(f"Telegram getUpdates failed: {description}")
        results = payload.get("result", [])
        if not isinstance(results, list):
            return []

        commands: list[TelegramCommand] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            update_id = int(item.get("update_id", 0))
            if update_id > self._last_update_id:
                self._last_update_id = update_id
            message = item.get("message")
            if not isinstance(message, dict):
                continue
            chat = message.get("chat")
            if not isinstance(chat, dict):
                continue
            chat_id = str(chat.get("id", "")).strip()
            if chat_id != self.chat_id:
                continue
            text = str(message.get("text", "")).strip()
            if not text.startswith("/"):
                continue
            commands.append(TelegramCommand(update_id=update_id, text=text))
        return commands

    def _post_message(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        body = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if self.parse_mode:
            body["parse_mode"] = self.parse_mode
        req = Request(
            url=url,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Telegram API returned status {resp.status}")
                payload = json.loads(resp.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Failed to send telegram notification: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to decode telegram response: {exc}") from exc

        if not payload.get("ok"):
            description = str(payload.get("description", "unknown telegram sendMessage error"))
            raise RuntimeError(f"Telegram sendMessage failed: {description}")

    def _render(self, p: BotEventPayload) -> str:
        title = f"{self._event_kr(p.event_type)} | {p.strategy}"
        lines = [title, f"시간: {self._format_time(p.event_time_utc)}"]

        if p.side:
            lines.append(f"방향: {self._side_kr(p.side)}")
        if p.pool_id:
            lines.append(f"풀: `{p.pool_id}`")
        if p.order_size_usd is not None:
            lines.append(f"주문금액: ${p.order_size_usd:.2f}")
        if p.filled_ststx is not None or p.filled_stx is not None:
            fill_ststx = f"{p.filled_ststx:.6f}" if p.filled_ststx is not None else "-"
            fill_stx = f"{p.filled_stx:.6f}" if p.filled_stx is not None else "-"
            lines.append(f"체결수량: {fill_ststx} stSTX / {fill_stx} STX")
        if p.avg_fill_price_stx_per_ststx is not None:
            lines.append(f"체결가: {p.avg_fill_price_stx_per_ststx:.6f} STX/stSTX")
        if p.edge_pct_at_decision is not None:
            lines.append(f"진입엣지: {p.edge_pct_at_decision:.4f}%")
        if p.slippage_pct is not None:
            lines.append(f"슬리피지: {p.slippage_pct:.4f}%")
        if p.fee_stx is not None:
            lines.append(f"수수료: {p.fee_stx:.6f} STX")
        if p.trade_pnl_stx is not None:
            pnl_label = "예상손익(수수료포함)" if p.event_type == "order_submitted" else "실현손익(수수료포함)"
            lines.append(f"{pnl_label}: {self._signed(p.trade_pnl_stx)} STX")
        if p.running_pnl_stx is not None:
            lines.append(f"누적손익: {self._signed(p.running_pnl_stx)} STX")
        if p.trade_count is not None:
            lines.append(f"거래횟수: {p.trade_count}")
        if p.win_rate is not None:
            lines.append(f"승률: {p.win_rate:.2f}%")
        if p.max_drawdown_stx is not None:
            lines.append(f"최대낙폭: {p.max_drawdown_stx:.6f} STX")
        if p.status:
            lines.append(f"상태: {self._status_kr(p.status)}")
        if p.reason:
            lines.append(f"사유: {p.reason}")
        if p.txid:
            lines.append(f"트랜잭션: {self._tx_url(p.txid)}")
        if p.actual_status or p.actual_reason or p.actual_trade_pnl_stx is not None:
            lines.append("=======")
            lines.append("실제 결과")
            if p.actual_event_time_utc:
                lines.append(f"시간: {self._format_time(p.actual_event_time_utc)}")
            if p.actual_filled_ststx is not None or p.actual_filled_stx is not None:
                fill_ststx = f"{p.actual_filled_ststx:.6f}" if p.actual_filled_ststx is not None else "-"
                fill_stx = f"{p.actual_filled_stx:.6f}" if p.actual_filled_stx is not None else "-"
                lines.append(f"체결수량: {fill_ststx} stSTX / {fill_stx} STX")
            if p.actual_avg_fill_price_stx_per_ststx is not None:
                lines.append(f"체결가: {p.actual_avg_fill_price_stx_per_ststx:.6f} STX/stSTX")
            if p.actual_fee_stx is not None:
                lines.append(f"수수료: {p.actual_fee_stx:.6f} STX")
            if p.actual_trade_pnl_stx is not None:
                lines.append(f"실현손익(수수료포함): {self._signed(p.actual_trade_pnl_stx)} STX")
            if p.actual_status:
                lines.append(f"상태: {self._status_kr(p.actual_status)}")
            if p.actual_reason:
                lines.append(f"사유: {p.actual_reason}")

        return "\n".join(lines)

    @staticmethod
    def _event_kr(event_type: str) -> str:
        mapping = {
            "order_submitted": "주문접수",
            "order_filled": "주문체결",
            "order_failed": "주문실패",
        }
        return mapping.get(event_type, event_type.upper())

    @staticmethod
    def _side_kr(side: str) -> str:
        mapping = {
            "BUY": "매수",
            "SELL": "매도",
            "BUY_STSTX": "매수(STX->stSTX)",
            "SELL_STSTX": "매도(stSTX->STX)",
        }
        return mapping.get(side, side)

    @staticmethod
    def _status_kr(status: str) -> str:
        mapping = {
            "submitted": "제출됨",
            "filled": "체결됨",
            "failed": "실패",
            "blocked": "차단됨",
            "skipped": "건너뜀",
        }
        return mapping.get(status, status)

    @staticmethod
    def _tx_url(txid: str) -> str:
        tid = txid.strip()
        return f"https://explorer.hiro.so/txid/{quote_plus(tid)}?chain=mainnet"

    @staticmethod
    def _signed(v: float) -> str:
        return f"+{v:.6f}" if v >= 0 else f"{v:.6f}"

    @staticmethod
    def _format_time(raw: str) -> str:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

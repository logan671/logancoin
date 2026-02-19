from __future__ import annotations

from dataclasses import dataclass
import json
import shlex
import subprocess

from bot.execution.fee_policy import compute_final_fee_stx


@dataclass(frozen=True)
class ExecutionRequest:
    action: str
    order_usd: float
    pool_id: str
    edge_pct: float
    slippage_pct: float
    stx_usd: float
    ststx_usd: float


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    status: str
    reason: str
    txid: str | None
    fee_stx: float
    filled_stx: float | None = None
    filled_ststx: float | None = None
    avg_fill_price_stx_per_ststx: float | None = None
    trade_pnl_stx: float | None = None


class Executor:
    def __init__(
        self,
        *,
        trading_private_key: str,
        min_fee_floor_stx: float,
        fee_multiplier: float,
        network_fee_cap_stx: float,
        executor_command: str,
        timeout_sec: int,
    ) -> None:
        self._trading_private_key = trading_private_key.strip()
        self._min_fee_floor_stx = min_fee_floor_stx
        self._fee_multiplier = fee_multiplier
        self._network_fee_cap_stx = network_fee_cap_stx
        self._executor_command = executor_command.strip()
        self._timeout_sec = timeout_sec

    def execute(self, req: ExecutionRequest, hiro_estimate_stx: float) -> ExecutionResult:
        if not self._trading_private_key:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason="missing_trading_private_key",
                txid=None,
                fee_stx=0.0,
            )

        if not self._executor_command:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason="missing_executor_command",
                txid=None,
                fee_stx=0.0,
            )

        if req.order_usd <= 0:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason="invalid_order_size",
                txid=None,
                fee_stx=0.0,
            )

        fee_stx = compute_final_fee_stx(
            hiro_estimate_stx=hiro_estimate_stx,
            min_fee_floor_stx=self._min_fee_floor_stx,
            fee_multiplier=self._fee_multiplier,
            network_fee_cap_stx=self._network_fee_cap_stx,
        )

        payload = {
            "action": req.action,
            "order_usd": req.order_usd,
            "pool_id": req.pool_id,
            "edge_pct": req.edge_pct,
            "slippage_pct": req.slippage_pct,
            "stx_usd": req.stx_usd,
            "ststx_usd": req.ststx_usd,
            "fee_stx": fee_stx,
        }
        cmd = shlex.split(self._executor_command)

        try:
            completed = subprocess.run(
                cmd,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=self._timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason="executor_timeout",
                txid=None,
                fee_stx=fee_stx,
            )
        except Exception as exc:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason=f"executor_exception:{exc.__class__.__name__}",
                txid=None,
                fee_stx=fee_stx,
            )

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            return ExecutionResult(
                ok=False,
                status="failed",
                reason=f"executor_nonzero:{completed.returncode}:{stderr[:120]}",
                txid=None,
                fee_stx=fee_stx,
            )

        out_line = _last_non_empty_line(completed.stdout)
        if not out_line:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason="executor_empty_output",
                txid=None,
                fee_stx=fee_stx,
            )

        try:
            raw = json.loads(out_line)
        except json.JSONDecodeError:
            return ExecutionResult(
                ok=False,
                status="failed",
                reason="executor_invalid_json",
                txid=None,
                fee_stx=fee_stx,
            )

        return ExecutionResult(
            ok=bool(raw.get("ok", False)),
            status=str(raw.get("status") or ("filled" if raw.get("ok") else "failed")),
            reason=str(raw.get("reason") or ""),
            txid=_to_opt_str(raw.get("txid")),
            fee_stx=float(raw.get("fee_stx", fee_stx)),
            filled_stx=_to_opt_float(raw.get("filled_stx")),
            filled_ststx=_to_opt_float(raw.get("filled_ststx")),
            avg_fill_price_stx_per_ststx=_to_opt_float(raw.get("avg_fill_price_stx_per_ststx")),
            trade_pnl_stx=_to_opt_float(raw.get("trade_pnl_stx")),
        )


def _last_non_empty_line(s: str) -> str:
    lines = [x.strip() for x in (s or "").splitlines() if x.strip()]
    return lines[-1] if lines else ""


def _to_opt_float(v: object) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_opt_str(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None

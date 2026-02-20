from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext
import json
from typing import Any
from urllib import parse, request

from backend.config import (
    EXECUTOR_MODE,
    POLYMARKET_CHAIN_ID,
    POLYMARKET_HOST,
    POLYMARKET_SIGNATURE_TYPE,
    VAULT_PASSPHRASE,
)
from backend.repositories.vault import get_secret_by_key_ref

getcontext().prec = 28


@dataclass
class ExecutionResult:
    status: str
    fail_reason: str | None = None
    chain_tx_hash: str | None = None
    executed_price: float | None = None
    executor_ref: str | None = None


def _clamp_price(price: float | None) -> float:
    base = 0.5 if price is None else float(price)
    if base < 0.01:
        return 0.01
    if base > 0.99:
        return 0.99
    return round(base, 4)


def _book_snapshot(token_id: str) -> tuple[float | None, float | None, float]:
    # Public CLOB orderbook endpoint.
    q = parse.urlencode({"token_id": token_id})
    url = f"{POLYMARKET_HOST}/book?{q}"
    req = request.Request(
        url,
        headers={
            "User-Agent": "ProjectK-Worker/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    with request.urlopen(req, timeout=8) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    bids = body.get("bids") or []
    asks = body.get("asks") or []
    tick_size = float(body.get("tick_size") or 0.001)

    best_bid = None
    best_ask = None
    if bids:
        best_bid = max(float(x.get("price", 0)) for x in bids if x.get("price") is not None)
    if asks:
        best_ask = min(float(x.get("price", 1)) for x in asks if x.get("price") is not None)
    return best_bid, best_ask, tick_size


def _align_to_tick(price: float, tick_size: float) -> float:
    if tick_size <= 0:
        return round(price, 4)
    p = Decimal(str(price))
    tick = Decimal(str(tick_size))
    aligned = (p / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
    return float(aligned)


def _quantize_order_amounts(side: str, notional_usdc: float, price: float) -> tuple[float, float]:
    px = Decimal(str(price))
    if px <= 0:
        raise ValueError("invalid_price")

    notional = Decimal(str(notional_usdc))
    if side == "buy":
        # CLOB buy restriction: quote precision <= 2 decimals.
        quote = notional.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if quote < Decimal("1.00"):
            quote = Decimal("1.00")
        size = (quote / px).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        if size <= 0:
            raise ValueError("invalid_size_after_quantize")
        return float(quote), float(size)

    # For sell, keep notional as-is but enforce taker size max 5 decimals.
    size = (notional / px).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
    if size <= 0:
        raise ValueError("invalid_size_after_quantize")
    return float(notional), float(size)


def _quantize_size_for_decimals(side: str, notional_usdc: float, price: float, size_decimals: int) -> float:
    px = Decimal(str(price))
    if px <= 0:
        raise ValueError("invalid_price")
    if size_decimals < 0:
        raise ValueError("invalid_size_decimals")

    unit = Decimal("1").scaleb(-size_decimals) if size_decimals > 0 else Decimal("1")
    notional = Decimal(str(notional_usdc))
    if side == "buy":
        quote = notional.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if quote < Decimal("1.00"):
            quote = Decimal("1.00")
        size = (quote / px).quantize(unit, rounding=ROUND_DOWN)
    else:
        size = (notional / px).quantize(unit, rounding=ROUND_DOWN)

    if size <= 0:
        raise ValueError("invalid_size_after_quantize")
    return float(size)


class StubExecutor:
    def execute(self, order: dict[str, Any]) -> ExecutionResult:
        order_id = int(order["id"])
        notional = float(order["adjusted_notional_usdc"])
        budget_usdc = float(order["budget_usdc"])
        max_slippage_bps = int(order["max_slippage_bps"])
        simulated_slippage_bps = 100 + ((order_id * 37) % 401)

        if simulated_slippage_bps > max_slippage_bps:
            return ExecutionResult(status="failed", fail_reason="slippage_exceeded")
        if notional > budget_usdc:
            return ExecutionResult(status="failed", fail_reason="insufficient_balance")
        if order_id % 11 == 0:
            return ExecutionResult(status="failed", fail_reason="rpc_error")
        return ExecutionResult(status="filled", chain_tx_hash=f"stub-order-{order_id}")

    def cancel(self, order: dict[str, Any]) -> ExecutionResult:
        executor_ref = str(order.get("executor_ref") or "")
        if not executor_ref:
            return ExecutionResult(status="failed", fail_reason="missing_executor_ref")
        return ExecutionResult(status="canceled", executor_ref=executor_ref)


class PolymarketLiveExecutor:
    def __init__(self) -> None:
        try:
            from eth_account import Account  # type: ignore
            from py_clob_client.client import ClobClient  # type: ignore
            from py_clob_client.clob_types import OrderArgs, OrderType  # type: ignore
            from py_clob_client.order_builder.constants import BUY, SELL  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "live executor dependencies are missing; install eth-account and py-clob-client"
            ) from exc

        self.Account = Account
        self.ClobClient = ClobClient
        self.OrderArgs = OrderArgs
        self.BUY = BUY
        self.SELL = SELL
        self.OrderType = OrderType

    def _private_key_from_secret(self, secret: str) -> str:
        candidate = secret.strip()
        if candidate.startswith("0x") and len(candidate) == 66:
            return candidate

        # If mnemonic was stored, derive EOA private key using default path.
        self.Account.enable_unaudited_hdwallet_features()
        account = self.Account.from_mnemonic(candidate)
        key_hex = str(account.key.hex())
        if not key_hex.startswith("0x"):
            key_hex = f"0x{key_hex}"
        return key_hex

    def execute(self, order: dict[str, Any]) -> ExecutionResult:
        key_ref = str(order["key_ref"])
        token_id = order.get("token_id")
        side = str(order["side"]).lower()
        source_price = order.get("source_price")
        follower_address = str(order["follower_address"])
        notional = float(order["adjusted_notional_usdc"])

        if not token_id:
            return ExecutionResult(status="failed", fail_reason="missing_token_id")
        if side not in ("buy", "sell"):
            return ExecutionResult(status="failed", fail_reason="invalid_side")
        if not VAULT_PASSPHRASE:
            return ExecutionResult(status="failed", fail_reason="vault_passphrase_missing")

        try:
            secret = get_secret_by_key_ref(key_ref=key_ref, passphrase=VAULT_PASSPHRASE)
            private_key = self._private_key_from_secret(secret)
        except Exception as exc:
            return ExecutionResult(status="failed", fail_reason=f"key_resolve_failed:{exc}")

        try:
            client = self.ClobClient(
                host=POLYMARKET_HOST,
                key=private_key,
                chain_id=POLYMARKET_CHAIN_ID,
                signature_type=POLYMARKET_SIGNATURE_TYPE,
                funder=follower_address,
            )
            client.set_api_creds(client.create_or_derive_api_creds())
            best_bid = None
            best_ask = None
            tick_size = 0.001
            try:
                best_bid, best_ask, tick_size = _book_snapshot(str(token_id))
            except Exception:
                # Fallback to source price when public orderbook query is blocked/rate-limited.
                best_bid, best_ask, tick_size = None, None, 0.001

            # Place one-tick improved limit order around the source price.
            is_reprice_after_timeout = "reprice_after_timeout" in str(order.get("blocked_reason") or "")
            if side == "buy":
                if source_price is not None:
                    raw_price = float(source_price) + (0.1 if is_reprice_after_timeout else tick_size)
                elif best_bid is not None:
                    raw_price = best_bid + (0.1 if is_reprice_after_timeout else tick_size)
                elif best_ask is not None:
                    raw_price = best_ask
                else:
                    return ExecutionResult(status="failed", fail_reason="price_reference_unavailable")
                price = _clamp_price(_align_to_tick(raw_price, tick_size))
            else:
                if source_price is not None:
                    raw_price = float(source_price) - tick_size
                elif best_ask is not None:
                    raw_price = best_ask - tick_size
                elif best_bid is not None:
                    raw_price = best_bid
                else:
                    return ExecutionResult(status="failed", fail_reason="price_reference_unavailable")
                price = _clamp_price(_align_to_tick(raw_price, tick_size))
            # Retry once or twice with stricter size precision when CLOB rejects amount precision.
            last_invalid_amount_msg = ""
            for size_decimals in (5, 4, 3):
                size = _quantize_size_for_decimals(
                    side=side,
                    notional_usdc=notional,
                    price=price,
                    size_decimals=size_decimals,
                )
                try:
                    order_args = self.OrderArgs(
                        price=price,
                        size=size,
                        side=self.BUY if side == "buy" else self.SELL,
                        token_id=str(token_id),
                    )
                    signed = client.create_order(order_args)
                    # Keep order on book using one-tick-improved limit order.
                    result = client.post_order(signed, self.OrderType.GTC)
                except Exception as exc:
                    msg = str(exc)
                    if "invalid amounts" in msg.lower():
                        last_invalid_amount_msg = msg
                        continue
                    raise

                ok = bool((result or {}).get("success"))
                if ok:
                    tx_hash = str((result or {}).get("transactionHash", "")) or None
                    # GTC order may be only accepted(open) without immediate fill.
                    status = "filled" if tx_hash else "sent"
                    return ExecutionResult(
                        status=status,
                        fail_reason=None,
                        executed_price=price,
                        executor_ref=str((result or {}).get("orderID", "")) or None,
                        chain_tx_hash=tx_hash,
                    )

                err_msg = str((result or {}).get("errorMsg", "unknown"))
                if "invalid amounts" in err_msg.lower():
                    last_invalid_amount_msg = err_msg
                    continue
                return ExecutionResult(
                    status="failed",
                    fail_reason=f"exchange_rejected:{err_msg}",
                    executor_ref=str((result or {}).get("orderID", "")) or None,
                )

            if last_invalid_amount_msg:
                return ExecutionResult(
                    status="failed",
                    fail_reason=f"invalid_amounts_after_retry:{last_invalid_amount_msg}",
                )
            return ExecutionResult(status="failed", fail_reason="executor_failed_after_retry")
        except Exception as exc:
            return ExecutionResult(status="failed", fail_reason=f"live_rpc_error:{exc}")

    def cancel(self, order: dict[str, Any]) -> ExecutionResult:
        key_ref = str(order["key_ref"])
        follower_address = str(order["follower_address"])
        executor_ref = str(order.get("executor_ref") or "")
        if not executor_ref:
            return ExecutionResult(status="failed", fail_reason="missing_executor_ref")
        if not VAULT_PASSPHRASE:
            return ExecutionResult(status="failed", fail_reason="vault_passphrase_missing")

        try:
            secret = get_secret_by_key_ref(key_ref=key_ref, passphrase=VAULT_PASSPHRASE)
            private_key = self._private_key_from_secret(secret)
        except Exception as exc:
            return ExecutionResult(status="failed", fail_reason=f"key_resolve_failed:{exc}")

        try:
            client = self.ClobClient(
                host=POLYMARKET_HOST,
                key=private_key,
                chain_id=POLYMARKET_CHAIN_ID,
                signature_type=POLYMARKET_SIGNATURE_TYPE,
                funder=follower_address,
            )
            client.set_api_creds(client.create_or_derive_api_creds())

            canceled = False
            if hasattr(client, "cancel"):
                resp = client.cancel(executor_ref)  # type: ignore[attr-defined]
                canceled = bool((resp or {}).get("success", False))
            elif hasattr(client, "cancel_orders"):
                resp = client.cancel_orders([executor_ref])  # type: ignore[attr-defined]
                if isinstance(resp, dict):
                    canceled_ids = resp.get("canceled") or resp.get("orderIDs") or []
                    canceled = executor_ref in [str(x) for x in canceled_ids]
                elif isinstance(resp, list):
                    canceled = executor_ref in [str(x) for x in resp]

            if not canceled:
                return ExecutionResult(
                    status="failed",
                    fail_reason="cancel_failed_or_not_supported",
                    executor_ref=executor_ref,
                )
            return ExecutionResult(status="canceled", executor_ref=executor_ref)
        except Exception as exc:
            return ExecutionResult(status="failed", fail_reason=f"cancel_rpc_error:{exc}", executor_ref=executor_ref)


def build_executor() -> Any:
    if EXECUTOR_MODE == "live":
        return PolymarketLiveExecutor()
    return StubExecutor()

from dataclasses import dataclass
from typing import Any

from backend.config import (
    EXECUTOR_MODE,
    POLYMARKET_CHAIN_ID,
    POLYMARKET_HOST,
    POLYMARKET_SIGNATURE_TYPE,
    VAULT_PASSPHRASE,
)
from backend.repositories.vault import get_secret_by_key_ref


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
            price = _clamp_price(source_price)
            size = round(notional / price, 6)
            order_args = self.OrderArgs(
                price=price,
                size=size,
                side=self.BUY if side == "buy" else self.SELL,
                token_id=str(token_id),
            )
            signed = client.create_order(order_args)
            result = client.post_order(signed, self.OrderType.GTC)
            ok = bool((result or {}).get("success"))
            if not ok:
                return ExecutionResult(
                    status="failed",
                    fail_reason=f"exchange_rejected:{(result or {}).get('errorMsg', 'unknown')}",
                    executor_ref=str((result or {}).get("orderID", "")) or None,
                )
            return ExecutionResult(
                status="filled",
                fail_reason=None,
                executed_price=price,
                executor_ref=str((result or {}).get("orderID", "")) or None,
                chain_tx_hash=str((result or {}).get("transactionHash", "")) or None,
            )
        except Exception as exc:
            return ExecutionResult(status="failed", fail_reason=f"live_rpc_error:{exc}")


def build_executor() -> Any:
    if EXECUTOR_MODE == "live":
        return PolymarketLiveExecutor()
    return StubExecutor()

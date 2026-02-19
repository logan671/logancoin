from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

from bot.strategy.intrinsic import compute_intrinsic_stx_per_ststx


DAO_ADDR = "SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG"
SENDER = "SP000000000000000000002Q6VF78"


@dataclass(frozen=True)
class IntrinsicInputs:
    reserve_total_stx: int
    ststx_supply: int
    ststxbtc_supply: int
    ststxbtc_v2_supply: int


@dataclass(frozen=True)
class WalletBalances:
    stx_balance: float
    ststx_balance: float


@dataclass(frozen=True)
class TxOutcome:
    txid: str
    tx_status: str
    block_time_iso: str | None
    fee_stx: float
    filled_stx: float | None
    filled_ststx: float | None
    avg_fill_price_stx_per_ststx: float | None


class HiroClient:
    def __init__(self, api_base: str):
        self.api_base = api_base.rstrip("/")

    def fetch_intrinsic_inputs(self) -> IntrinsicInputs:
        reserve_total_stx = self._call_read("reserve-v1", "get-total-stx")
        ststx_supply = self._call_read("ststx-token", "get-total-supply")
        ststxbtc_supply = self._call_read("ststxbtc-token", "get-total-supply")
        ststxbtc_v2_supply = self._call_read("ststxbtc-token-v2", "get-total-supply")
        return IntrinsicInputs(
            reserve_total_stx=reserve_total_stx,
            ststx_supply=ststx_supply,
            ststxbtc_supply=ststxbtc_supply,
            ststxbtc_v2_supply=ststxbtc_v2_supply,
        )

    def fetch_intrinsic_stx_per_ststx(self) -> float:
        x = self.fetch_intrinsic_inputs()
        return compute_intrinsic_stx_per_ststx(
            reserve_total_stx=float(x.reserve_total_stx),
            ststx_supply=float(x.ststx_supply),
            ststxbtc_supply=float(x.ststxbtc_supply),
            ststxbtc_v2_supply=float(x.ststxbtc_v2_supply),
        )

    def fetch_transfer_fee_rate_microstx_per_byte(self) -> float:
        url = f"{self.api_base}/v2/fees/transfer"
        with urlopen(url, timeout=10) as resp:
            raw = resp.read().decode("utf-8").strip()
        return float(raw)

    def fetch_wallet_balances(self, address: str, ststx_contract: str) -> WalletBalances:
        address = address.strip()
        if not address:
            raise ValueError("address is required")
        contract_prefix = f"{ststx_contract.strip()}::"
        url = f"{self.api_base}/extended/v1/address/{quote(address)}/balances"
        with urlopen(url, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        stx_micro = int(payload.get("stx", {}).get("balance", "0"))
        ft = payload.get("fungible_tokens", {})
        ststx_micro = 0
        exact_key = f"{contract_prefix}ststx"
        if exact_key in ft:
            ststx_micro = int(ft.get(exact_key, {}).get("balance", "0"))
        else:
            for k, v in ft.items():
                if not isinstance(k, str) or not k.startswith(contract_prefix):
                    continue
                if "ststx" not in k.lower():
                    continue
                ststx_micro = int((v or {}).get("balance", "0"))
                break
        return WalletBalances(
            stx_balance=stx_micro / 1_000_000.0,
            ststx_balance=ststx_micro / 1_000_000.0,
        )

    def wait_for_tx_outcome(
        self,
        txid: str,
        *,
        trading_address: str,
        action: str,
        ststx_contract: str,
        timeout_sec: int = 45,
        poll_interval_sec: int = 3,
    ) -> TxOutcome:
        txid = txid.strip().removeprefix("0x")
        if not txid:
            raise ValueError("txid is required")
        address = trading_address.strip()
        if not address:
            raise ValueError("trading_address is required")

        started = time.time()
        last_payload: dict | None = None
        while True:
            payload = self._fetch_tx(txid)
            last_payload = payload
            tx_status = str(payload.get("tx_status", "")).strip().lower()
            if tx_status == "success" or tx_status.startswith("abort") or tx_status.startswith("drop") or tx_status.startswith("bad_"):
                return self._build_tx_outcome(
                    payload=payload,
                    trading_address=address,
                    action=action,
                    ststx_contract=ststx_contract,
                )
            if time.time() - started >= timeout_sec:
                break
            time.sleep(max(1, poll_interval_sec))

        if last_payload is None:
            raise RuntimeError("tx lookup failed")
        return self._build_tx_outcome(
            payload=last_payload,
            trading_address=address,
            action=action,
            ststx_contract=ststx_contract,
        )

    def _fetch_tx(self, txid: str) -> dict:
        url = f"{self.api_base}/extended/v1/tx/0x{quote(txid)}"
        with urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _build_tx_outcome(
        self,
        *,
        payload: dict,
        trading_address: str,
        action: str,
        ststx_contract: str,
    ) -> TxOutcome:
        events = payload.get("events", []) or []
        stx_sent_micro = 0
        stx_recv_micro = 0
        ststx_sent_micro = 0
        ststx_recv_micro = 0
        ststx_prefix = f"{ststx_contract.strip()}::"

        for ev in events:
            et = ev.get("event_type")
            asset = ev.get("asset", {}) or {}
            if et == "stx_asset":
                amount = int(asset.get("amount", "0"))
                if asset.get("sender") == trading_address:
                    stx_sent_micro += amount
                if asset.get("recipient") == trading_address:
                    stx_recv_micro += amount
                continue
            if et == "fungible_token_asset":
                asset_id = str(asset.get("asset_id", ""))
                if not asset_id.startswith(ststx_prefix):
                    continue
                amount = int(asset.get("amount", "0"))
                if asset.get("sender") == trading_address:
                    ststx_sent_micro += amount
                if asset.get("recipient") == trading_address:
                    ststx_recv_micro += amount

        filled_stx: float | None = None
        filled_ststx: float | None = None
        if action == "BUY_STSTX":
            if stx_sent_micro > 0:
                filled_stx = stx_sent_micro / 1_000_000.0
            if ststx_recv_micro > 0:
                filled_ststx = ststx_recv_micro / 1_000_000.0
        elif action == "SELL_STSTX":
            if stx_recv_micro > 0:
                filled_stx = stx_recv_micro / 1_000_000.0
            if ststx_sent_micro > 0:
                filled_ststx = ststx_sent_micro / 1_000_000.0

        avg_price = None
        if filled_stx and filled_ststx and filled_stx > 0 and filled_ststx > 0:
            avg_price = filled_stx / filled_ststx

        fee_micro = int(payload.get("fee_rate", "0"))
        return TxOutcome(
            txid=str(payload.get("tx_id", "")),
            tx_status=str(payload.get("tx_status", "")),
            block_time_iso=payload.get("block_time_iso"),
            fee_stx=fee_micro / 1_000_000.0,
            filled_stx=filled_stx,
            filled_ststx=filled_ststx,
            avg_fill_price_stx_per_ststx=avg_price,
        )

    def _call_read(self, contract: str, function: str) -> int:
        url = f"{self.api_base}/v2/contracts/call-read/{DAO_ADDR}/{contract}/{function}"
        body = {"sender": SENDER, "arguments": []}
        req = Request(
            url=url,
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body).encode("utf-8"),
        )
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("okay"):
            raise ValueError(f"Hiro call-read failed: {contract}/{function}")
        return _cv_hex_to_int(payload["result"])


def _cv_hex_to_int(cv_hex: str) -> int:
    h = cv_hex[2:] if cv_hex.startswith("0x") else cv_hex
    # 07 = response-ok, 01 = uint
    if h.startswith("07"):
        h = h[2:]
    if h.startswith("01"):
        h = h[2:]
    return int(h, 16)

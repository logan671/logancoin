from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class PairItem(BaseModel):
    id: int
    mode: str
    active: int
    max_slippage_bps: int
    max_consecutive_failures: int
    source_address: str
    source_alias: str | None = None
    follower_address: str
    follower_label: str | None = None
    budget_usdc: float
    initial_matic: float
    min_matic_alert: float


class PairCreateRequest(BaseModel):
    source_address: str
    follower_address: str
    source_alias: str | None = None
    follower_label: str | None = None
    budget_usdc: float = 100.0
    key_ref: str
    mode: str = "live"
    active: int = 1
    min_order_usdc: float = 1.0
    max_order_usdc: float | None = None
    max_slippage_bps: int = 300
    max_consecutive_failures: int = 3
    rpc_error_threshold: int = 5
    initial_matic: float = 3.0
    min_matic_alert: float = 0.5


class PairDeleteResponse(BaseModel):
    ok: bool
    pair_id: int


class SignalMockRequest(BaseModel):
    source_address: str
    side: str = "buy"
    source_notional_usdc: float = 25.0
    source_price: float = 0.52
    market_slug: str | None = "demo-market"
    token_id: str | None = "demo-token"
    outcome: str | None = "YES"


class TradeSignalItem(BaseModel):
    id: int
    source_address: str
    side: str
    source_notional_usdc: float
    source_price: float | None = None
    market_slug: str | None = None
    created_at: int


class MirrorOrderItem(BaseModel):
    id: int
    pair_id: int
    trade_signal_id: int
    requested_notional_usdc: float
    adjusted_notional_usdc: float
    status: str
    blocked_reason: str | None = None
    created_at: int


class ExecutionItem(BaseModel):
    id: int
    mirror_order_id: int
    pair_id: int
    follower_wallet_id: int
    chain_tx_hash: str | None = None
    executed_side: str | None = None
    executed_outcome: str | None = None
    executed_price: float | None = None
    executed_notional_usdc: float | None = None
    status: str
    fail_reason: str | None = None
    executed_at: int | None = None


class RuntimeServiceItem(BaseModel):
    component: str
    pid: int
    db_path: str
    updated_at: int
    extra_json: str | None = None

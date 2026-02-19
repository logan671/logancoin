import sqlite3
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .repositories.orders import list_recent_executions, list_recent_mirror_orders
from .repositories.pairs import create_pair, delete_pair, get_pair, list_pairs
from .repositories.runtime import heartbeat, list_runtime_services
from .repositories.signals import create_mock_signal, list_recent_signals
from .schemas import (
    HealthResponse,
    ExecutionItem,
    MirrorOrderItem,
    PairCreateRequest,
    PairDeleteResponse,
    PairItem,
    RuntimeServiceItem,
    SignalMockRequest,
    TradeSignalItem,
)

app = FastAPI(title="ProjectK API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_stop_event = threading.Event()


def _runtime_heartbeat_loop() -> None:
    while not _stop_event.is_set():
        try:
            heartbeat("api")
        except Exception:
            pass
        _stop_event.wait(10)


@app.on_event("startup")
def startup_event() -> None:
    heartbeat("api")
    threading.Thread(target=_runtime_heartbeat_loop, daemon=True).start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    _stop_event.set()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    heartbeat("api")
    return HealthResponse(status="ok")


@app.get("/pairs", response_model=list[PairItem])
def pairs() -> list[PairItem]:
    data = list_pairs()
    return [PairItem(**row) for row in data]


@app.post("/pairs", response_model=PairItem, status_code=201)
def create_pair_endpoint(payload: PairCreateRequest) -> PairItem:
    try:
        pair_id = create_pair(
            source_address=payload.source_address.lower(),
            follower_address=payload.follower_address.lower(),
            source_alias=payload.source_alias,
            follower_label=payload.follower_label,
            budget_usdc=payload.budget_usdc,
            key_ref=payload.key_ref,
            mode=payload.mode,
            active=payload.active,
            min_order_usdc=payload.min_order_usdc,
            max_order_usdc=payload.max_order_usdc,
            max_slippage_bps=payload.max_slippage_bps,
            max_consecutive_failures=payload.max_consecutive_failures,
            rpc_error_threshold=payload.rpc_error_threshold,
            initial_matic=payload.initial_matic,
            min_matic_alert=payload.min_matic_alert,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"pair_create_conflict: {exc}") from exc

    item = get_pair(pair_id)
    if not item:
        raise HTTPException(status_code=500, detail="pair_created_but_not_found")
    return PairItem(**item)


@app.delete("/pairs/{pair_id}", response_model=PairDeleteResponse)
def delete_pair_endpoint(pair_id: int) -> PairDeleteResponse:
    deleted = delete_pair(pair_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="pair_not_found")
    return PairDeleteResponse(ok=True, pair_id=pair_id)


@app.post("/signals/mock", response_model=TradeSignalItem, status_code=201)
def create_mock_signal_endpoint(payload: SignalMockRequest) -> TradeSignalItem:
    try:
        signal_id = create_mock_signal(
            source_address=payload.source_address.lower(),
            side=payload.side.lower(),
            source_notional_usdc=payload.source_notional_usdc,
            source_price=payload.source_price,
            market_slug=payload.market_slug,
            token_id=payload.token_id,
            outcome=payload.outcome,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"signal_create_conflict: {exc}") from exc

    rows = list_recent_signals(limit=1)
    if not rows:
        raise HTTPException(status_code=500, detail="signal_created_but_not_found")
    return TradeSignalItem(**rows[0])


@app.get("/signals", response_model=list[TradeSignalItem])
def list_signals_endpoint(limit: int = 20) -> list[TradeSignalItem]:
    rows = list_recent_signals(limit=limit)
    return [TradeSignalItem(**row) for row in rows]


@app.get("/mirror-orders", response_model=list[MirrorOrderItem])
def list_mirror_orders_endpoint(limit: int = 20) -> list[MirrorOrderItem]:
    rows = list_recent_mirror_orders(limit=limit)
    return [MirrorOrderItem(**row) for row in rows]


@app.get("/executions", response_model=list[ExecutionItem])
def list_executions_endpoint(limit: int = 20) -> list[ExecutionItem]:
    rows = list_recent_executions(limit=limit)
    return [ExecutionItem(**row) for row in rows]


@app.get("/runtime/services", response_model=list[RuntimeServiceItem])
def runtime_services_endpoint() -> list[RuntimeServiceItem]:
    rows = list_runtime_services()
    return [RuntimeServiceItem(**row) for row in rows]

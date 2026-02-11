from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os

from src.database import (
    init_db,
    get_recent_markets,
    get_high_alpha_markets,
    get_screened_markets,
    get_favorite_markets,
    get_favorite_ids,
    add_favorite,
    remove_favorite,
    save_feedback,
    get_all_feedbacks,
    add_learning_rule,
    get_active_learning_rules,
    toggle_learning_rule,
    get_market,
)

app = FastAPI(title="Polymarket Alpha Scanner")

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================
# Pydantic Models
# ============================================
class MarketResponse(BaseModel):
    id: str
    title: str
    title_ko: Optional[str]
    category: Optional[str]
    yes_price: float
    no_price: float
    volume: float
    end_date: Optional[str]
    polymarket_url: Optional[str]
    screening_passed: Optional[bool]
    screening_reason: Optional[str]
    alpha_type: Optional[str]
    alpha_score: Optional[int]
    ai_prediction: Optional[float]
    recommendation: Optional[str]
    analysis_summary: Optional[str]
    key_evidence: Optional[list]
    is_favorite: bool = False

    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    market_id: Optional[str] = None
    feedback_type: str  # GOOD_CALL, BAD_CALL, SKIP_SIMILAR, NOTE
    content: str


class LearningRuleRequest(BaseModel):
    rule_type: str  # AVOID_TOPIC, PREFER_TOPIC, THRESHOLD_ADJUST
    rule_content: str


# ============================================
# API Endpoints
# ============================================
@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    """메인 페이지"""
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"message": "Polymarket Alpha Scanner API"}


@app.get("/api/markets")
async def list_markets(
    filter: str = "recent",  # recent, high_alpha, passed, failed, favorites
    limit: int = 50,
):
    """마켓 목록 조회"""
    favorite_ids = await get_favorite_ids()

    if filter == "recent":
        markets = await get_recent_markets(limit)
    elif filter == "high_alpha":
        markets = await get_high_alpha_markets(50)
    elif filter == "passed":
        markets = await get_screened_markets(True)
    elif filter == "failed":
        markets = await get_screened_markets(False)
    elif filter == "favorites":
        markets = await get_favorite_markets()
    else:
        markets = await get_recent_markets(limit)

    result = []
    for m in markets:
        result.append(MarketResponse(
            id=m.id,
            title=m.title,
            title_ko=m.title_ko,
            category=m.category,
            yes_price=m.yes_price,
            no_price=m.no_price,
            volume=m.volume,
            end_date=m.end_date.isoformat() if m.end_date else None,
            polymarket_url=m.polymarket_url,
            screening_passed=m.screening_passed,
            screening_reason=m.screening_reason,
            alpha_type=m.alpha_type,
            alpha_score=m.alpha_score,
            ai_prediction=m.ai_prediction,
            recommendation=m.recommendation,
            analysis_summary=m.analysis_summary,
            key_evidence=m.key_evidence,
            is_favorite=m.id in favorite_ids,
        ))

    return result


@app.get("/api/markets/{market_id}")
async def get_market_detail(market_id: str):
    """마켓 상세 조회"""
    market = await get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    favorite_ids = await get_favorite_ids()

    return MarketResponse(
        id=market.id,
        title=market.title,
        title_ko=market.title_ko,
        category=market.category,
        yes_price=market.yes_price,
        no_price=market.no_price,
        volume=market.volume,
        end_date=market.end_date.isoformat() if market.end_date else None,
        polymarket_url=market.polymarket_url,
        screening_passed=market.screening_passed,
        screening_reason=market.screening_reason,
        alpha_type=market.alpha_type,
        alpha_score=market.alpha_score,
        ai_prediction=market.ai_prediction,
        recommendation=market.recommendation,
        analysis_summary=market.analysis_summary,
        key_evidence=market.key_evidence,
        is_favorite=market.id in favorite_ids,
    )


# ============================================
# 즐겨찾기
# ============================================
@app.post("/api/favorites/{market_id}")
async def add_to_favorites(market_id: str):
    """즐겨찾기 추가"""
    success = await add_favorite(market_id)
    return {"success": success, "market_id": market_id}


@app.delete("/api/favorites/{market_id}")
async def remove_from_favorites(market_id: str):
    """즐겨찾기 제거"""
    success = await remove_favorite(market_id)
    return {"success": success, "market_id": market_id}


# ============================================
# 피드백 & 학습
# ============================================
@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """피드백 제출"""
    await save_feedback(req.market_id, req.feedback_type, req.content)

    # 특정 피드백 타입은 자동으로 학습 규칙 생성
    if req.feedback_type == "SKIP_SIMILAR":
        await add_learning_rule("AVOID_TOPIC", f"Skip markets similar to: {req.content}")

    return {"success": True}


@app.get("/api/feedback")
async def list_feedbacks():
    """피드백 목록"""
    feedbacks = await get_all_feedbacks()
    return [
        {
            "id": f.id,
            "market_id": f.market_id,
            "feedback_type": f.feedback_type,
            "content": f.content,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]


@app.post("/api/learning-rules")
async def create_learning_rule(req: LearningRuleRequest):
    """학습 규칙 생성"""
    await add_learning_rule(req.rule_type, req.rule_content)
    return {"success": True}


@app.get("/api/learning-rules")
async def list_learning_rules():
    """학습 규칙 목록"""
    rules = await get_active_learning_rules()
    return [
        {
            "id": r.id,
            "rule_type": r.rule_type,
            "rule_content": r.rule_content,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
        }
        for r in rules
    ]


@app.patch("/api/learning-rules/{rule_id}")
async def update_learning_rule(rule_id: int, is_active: bool):
    """학습 규칙 활성화/비활성화"""
    await toggle_learning_rule(rule_id, is_active)
    return {"success": True}

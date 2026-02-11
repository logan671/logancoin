from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, desc
from typing import Optional
import os

from src.models import Base, Market, Alert, UserFeedback, Favorite, LearningContext

# 데이터 디렉토리 확인
os.makedirs("data", exist_ok=True)

engine = create_async_engine(
    "sqlite+aiosqlite:///data/markets.db",
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """데이터베이스 초기화"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_market(market_id: str) -> Optional[Market]:
    """마켓 조회"""
    async with async_session() as session:
        result = await session.execute(select(Market).where(Market.id == market_id))
        return result.scalar_one_or_none()


async def save_market(market: Market):
    """마켓 저장"""
    async with async_session() as session:
        await session.merge(market)
        await session.commit()


async def get_unanalyzed_markets() -> list[Market]:
    """분석되지 않은 마켓 조회"""
    async with async_session() as session:
        result = await session.execute(
            select(Market).where(Market.is_analyzed == False)
        )
        return list(result.scalars().all())


async def get_markets_to_alert(threshold: int) -> list[Market]:
    """알림 보낼 마켓 조회 (알파 점수 이상, 미발송)"""
    async with async_session() as session:
        result = await session.execute(
            select(Market).where(
                Market.is_analyzed == True,
                Market.is_alerted == False,
                Market.alpha_score >= threshold,
            )
        )
        return list(result.scalars().all())


async def mark_as_alerted(market_id: str):
    """알림 발송 완료 표시"""
    async with async_session() as session:
        result = await session.execute(select(Market).where(Market.id == market_id))
        market = result.scalar_one_or_none()
        if market:
            from datetime import datetime

            market.is_alerted = True
            market.alert_sent_at = datetime.utcnow()
            await session.commit()


async def save_alert(alert: Alert):
    """알림 기록 저장"""
    async with async_session() as session:
        session.add(alert)
        await session.commit()


async def get_all_known_market_ids() -> set[str]:
    """이미 알고 있는 마켓 ID 목록"""
    async with async_session() as session:
        result = await session.execute(select(Market.id))
        return set(row[0] for row in result.all())


# ============================================
# 마켓 조회 (웹사이트용)
# ============================================
async def get_recent_markets(limit: int = 50, offset: int = 0) -> list[Market]:
    """최근 마켓 목록"""
    async with async_session() as session:
        result = await session.execute(
            select(Market)
            .order_by(desc(Market.first_seen_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


async def get_high_alpha_markets(threshold: int = 50) -> list[Market]:
    """알파 점수 높은 마켓"""
    async with async_session() as session:
        result = await session.execute(
            select(Market)
            .where(Market.alpha_score >= threshold)
            .order_by(desc(Market.alpha_score))
        )
        return list(result.scalars().all())


async def get_screened_markets(passed: bool = True) -> list[Market]:
    """스크리닝 통과/실패 마켓"""
    async with async_session() as session:
        result = await session.execute(
            select(Market)
            .where(Market.screening_passed == passed)
            .order_by(desc(Market.first_seen_at))
        )
        return list(result.scalars().all())


# ============================================
# 즐겨찾기
# ============================================
async def add_favorite(market_id: str) -> bool:
    """즐겨찾기 추가"""
    async with async_session() as session:
        existing = await session.execute(
            select(Favorite).where(Favorite.market_id == market_id)
        )
        if existing.scalar_one_or_none():
            return False
        session.add(Favorite(market_id=market_id))
        await session.commit()
        return True


async def remove_favorite(market_id: str) -> bool:
    """즐겨찾기 제거"""
    async with async_session() as session:
        result = await session.execute(
            select(Favorite).where(Favorite.market_id == market_id)
        )
        fav = result.scalar_one_or_none()
        if fav:
            await session.delete(fav)
            await session.commit()
            return True
        return False


async def get_favorite_markets() -> list[Market]:
    """즐겨찾기 마켓 목록"""
    async with async_session() as session:
        result = await session.execute(
            select(Market)
            .join(Favorite, Market.id == Favorite.market_id)
            .order_by(desc(Favorite.created_at))
        )
        return list(result.scalars().all())


async def get_favorite_ids() -> set[str]:
    """즐겨찾기 ID 목록"""
    async with async_session() as session:
        result = await session.execute(select(Favorite.market_id))
        return set(row[0] for row in result.all())


# ============================================
# 피드백 & 학습
# ============================================
async def save_feedback(market_id: str, feedback_type: str, content: str):
    """사용자 피드백 저장"""
    async with async_session() as session:
        feedback = UserFeedback(
            market_id=market_id,
            feedback_type=feedback_type,
            content=content,
        )
        session.add(feedback)
        await session.commit()


async def get_all_feedbacks() -> list[UserFeedback]:
    """모든 피드백 조회"""
    async with async_session() as session:
        result = await session.execute(
            select(UserFeedback).order_by(desc(UserFeedback.created_at))
        )
        return list(result.scalars().all())


async def add_learning_rule(rule_type: str, rule_content: str):
    """학습 규칙 추가"""
    async with async_session() as session:
        rule = LearningContext(
            rule_type=rule_type,
            rule_content=rule_content,
        )
        session.add(rule)
        await session.commit()


async def get_active_learning_rules() -> list[LearningContext]:
    """활성 학습 규칙 조회"""
    async with async_session() as session:
        result = await session.execute(
            select(LearningContext).where(LearningContext.is_active == True)
        )
        return list(result.scalars().all())


async def toggle_learning_rule(rule_id: int, is_active: bool):
    """학습 규칙 활성화/비활성화"""
    async with async_session() as session:
        result = await session.execute(
            select(LearningContext).where(LearningContext.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule:
            rule.is_active = is_active
            await session.commit()

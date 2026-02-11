from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserFeedback(Base):
    """사용자 피드백 - AI 학습용"""
    __tablename__ = "user_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50))  # GOOD_CALL, BAD_CALL, SKIP_SIMILAR, NOTE
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Favorite(Base):
    """즐겨찾기"""
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LearningContext(Base):
    """AI 학습 컨텍스트 - 피드백 기반 규칙"""
    __tablename__ = "learning_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_type: Mapped[str] = mapped_column(String(50))  # AVOID_TOPIC, PREFER_TOPIC, THRESHOLD_ADJUST
    rule_content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    title_ko: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 한글 번역
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    polymarket_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 1차 스크리닝 결과
    screening_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    screening_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # EASY_WIN, UNCERTAIN, SKIP

    # Market Data
    yes_price: Mapped[float] = mapped_column(Float, default=0.5)
    no_price: Mapped[float] = mapped_column(Float, default=0.5)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity: Mapped[float] = mapped_column(Float, default=0.0)

    # AI Analysis
    alpha_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_already_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_prediction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alpha_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_gap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_evidence: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_alerted: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_id: Mapped[str] = mapped_column(String(100))
    alpha_score: Mapped[int] = mapped_column(Integer)
    alpha_type: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    telegram_message_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

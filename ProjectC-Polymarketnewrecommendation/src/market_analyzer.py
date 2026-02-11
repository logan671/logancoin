import json
import httpx
from datetime import datetime
from typing import Optional, Tuple
from openai import AsyncOpenAI

from config.settings import settings
from src.models import Market, LearningContext
from src.polymarket_client import PolymarketMarket


# ============================================
# 1차 스크리닝 프롬프트 (GPT-4o-mini, 저비용)
# ============================================
SCREENING_PROMPT = """You are a prediction market screener. Quickly assess if this market has alpha potential.

**Market:** {title}
**YES Price:** {yes_price:.0%} / **NO Price:** {no_price:.0%}
**End Date:** {end_date}

{learning_context}

## Quick Assessment
Determine if this market likely has:
1. **EASY_WIN**: Result is almost certain (already happened, overwhelming odds, common sense)
2. **UNCERTAIN**: Genuinely unpredictable, no clear edge
3. **SKIP**: Low volume topic, too niche, or matches user's skip preferences

Output JSON only:
{{"verdict": "EASY_WIN|UNCERTAIN|SKIP", "confidence": 0-100, "reason_ko": "한글로 짧은 이유", "title_ko": "한글 제목 번역"}}"""


# ============================================
# 2차 딥리서치 프롬프트 (Perplexity Sonar Pro)
# ============================================
DEEP_RESEARCH_PROMPT = """You are an expert prediction market analyst with web search capabilities.

**Market:** {title}
**Description:** {description}
**Current YES:** {yes_price:.1%} / NO: {no_price:.1%}
**End Date:** {end_date}
**Volume:** ${volume:,.0f}

## Your Task
1. **SEARCH** for recent news, official announcements, or data about this topic
2. **VERIFY** if the outcome is already determined or highly predictable
3. **CALCULATE** the true probability based on evidence

## Alpha Types
- **TYPE_A_FACT**: Event already occurred, result is known (check news!)
- **TYPE_B_PROBABILITY**: Outcome is highly predictable (>85% certain)

## Output JSON:
{{
  "alpha_type": "TYPE_A_FACT|TYPE_B_PROBABILITY|UNCERTAIN",
  "is_resolved": true/false,
  "ai_prediction": 0.0-1.0,
  "confidence": 0-100,
  "alpha_score": 0-100,
  "reasoning_ko": "한글로 상세 분석",
  "key_evidence": ["근거1", "근거2"],
  "sources": ["url1", "url2"],
  "recommendation": "STRONG_BUY_YES|BUY_YES|HOLD|BUY_NO|STRONG_BUY_NO|SKIP",
  "risk_factors": ["리스크1", "리스크2"]
}}"""


class MarketAnalyzer:
    """2단계 AI 분석기"""

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.perplexity_client = httpx.AsyncClient(
            base_url="https://api.perplexity.ai",
            headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
            timeout=60.0,
        )

    async def close(self):
        await self.perplexity_client.aclose()

    # ============================================
    # 1차 스크리닝 (GPT-4o-mini)
    # ============================================
    async def screen(
        self, poly_market: PolymarketMarket, learning_rules: list[LearningContext] = None
    ) -> Tuple[bool, Market]:
        """1차 스크리닝: 알파 가능성 빠른 판단"""

        market = self._create_base_market(poly_market)

        if not settings.openai_api_key:
            market.screening_passed = True
            market.screening_reason = "NO_API_KEY"
            return True, market

        try:
            # 학습 컨텍스트 포맷팅
            learning_context = ""
            if learning_rules:
                rules_text = "\n".join(f"- {r.rule_content}" for r in learning_rules if r.is_active)
                if rules_text:
                    learning_context = f"\n## User Preferences (IMPORTANT):\n{rules_text}\n"

            prompt = SCREENING_PROMPT.format(
                title=poly_market.title,
                yes_price=poly_market.yes_price,
                no_price=poly_market.no_price,
                end_date=poly_market.end_date.strftime("%Y-%m-%d") if poly_market.end_date else "Unknown",
                learning_context=learning_context,
            )

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Output valid JSON only. Be concise."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            content = self._parse_json_response(response.choices[0].message.content)

            verdict = content.get("verdict", "UNCERTAIN")
            market.title_ko = content.get("title_ko", poly_market.title)
            market.screening_reason = content.get("reason_ko", "")
            market.screening_passed = verdict == "EASY_WIN"

            return market.screening_passed, market

        except Exception as e:
            print(f"[ERROR] Screening failed: {e}")
            market.screening_passed = False
            market.screening_reason = f"Error: {str(e)[:50]}"
            return False, market

    # ============================================
    # 2차 딥리서치 (Perplexity Sonar Pro)
    # ============================================
    async def deep_research(self, market: Market, poly_market: PolymarketMarket) -> Market:
        """2차 딥리서치: 웹 검색 + 정밀 분석"""

        if not settings.perplexity_api_key:
            # Perplexity 없으면 GPT-4o로 대체
            return await self._deep_research_openai(market, poly_market)

        try:
            prompt = DEEP_RESEARCH_PROMPT.format(
                title=poly_market.title,
                description=poly_market.description or "No description",
                yes_price=poly_market.yes_price,
                no_price=poly_market.no_price,
                end_date=poly_market.end_date.strftime("%Y-%m-%d") if poly_market.end_date else "Unknown",
                volume=poly_market.volume,
            )

            response = await self.perplexity_client.post(
                "/chat/completions",
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {"role": "system", "content": "You are a prediction market analyst. Search the web and output JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = self._parse_json_response(data["choices"][0]["message"]["content"])
            market = self._apply_analysis(market, content, poly_market)

        except Exception as e:
            print(f"[ERROR] Deep research failed: {e}")
            # 폴백: OpenAI로 시도
            market = await self._deep_research_openai(market, poly_market)

        return market

    async def _deep_research_openai(self, market: Market, poly_market: PolymarketMarket) -> Market:
        """OpenAI GPT-4o로 딥리서치 (폴백)"""

        if not settings.openai_api_key:
            market.is_analyzed = False
            return market

        try:
            prompt = DEEP_RESEARCH_PROMPT.format(
                title=poly_market.title,
                description=poly_market.description or "No description",
                yes_price=poly_market.yes_price,
                no_price=poly_market.no_price,
                end_date=poly_market.end_date.strftime("%Y-%m-%d") if poly_market.end_date else "Unknown",
                volume=poly_market.volume,
            )

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a prediction market analyst. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            content = self._parse_json_response(response.choices[0].message.content)
            market = self._apply_analysis(market, content, poly_market)

        except Exception as e:
            print(f"[ERROR] OpenAI deep research failed: {e}")
            market.is_analyzed = False

        return market

    def _apply_analysis(self, market: Market, analysis: dict, poly_market: PolymarketMarket) -> Market:
        """분석 결과를 Market 객체에 적용"""

        ai_prediction = float(analysis.get("ai_prediction", 0.5))
        price_gap = abs(ai_prediction - poly_market.yes_price)
        confidence = int(analysis.get("confidence", 50))

        # 알파 점수 계산
        calculated_alpha = min(100, int(price_gap * confidence * 1.5))
        final_alpha = max(calculated_alpha, int(analysis.get("alpha_score", 0)))

        market.alpha_type = analysis.get("alpha_type", "UNCERTAIN")
        market.is_already_resolved = analysis.get("is_resolved", False)
        market.ai_prediction = ai_prediction
        market.ai_confidence = confidence
        market.alpha_score = final_alpha
        market.price_gap = price_gap
        market.recommendation = analysis.get("recommendation", "SKIP")
        market.analysis_summary = analysis.get("reasoning_ko", "")
        market.key_evidence = analysis.get("key_evidence", [])
        market.sources = analysis.get("sources", [])
        market.risk_factors = analysis.get("risk_factors", [])
        market.is_analyzed = True

        return market

    def _create_base_market(self, poly_market: PolymarketMarket) -> Market:
        """기본 Market 객체 생성"""
        return Market(
            id=poly_market.id,
            title=poly_market.title,
            description=poly_market.description,
            end_date=poly_market.end_date,
            polymarket_url=poly_market.url,
            yes_price=poly_market.yes_price,
            no_price=poly_market.no_price,
            volume=poly_market.volume,
            liquidity=poly_market.liquidity,
        )

    def _parse_json_response(self, content: str) -> dict:
        """JSON 응답 파싱"""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        return json.loads(content)


# 싱글톤
_analyzer: Optional[MarketAnalyzer] = None


def get_analyzer() -> MarketAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MarketAnalyzer()
    return _analyzer

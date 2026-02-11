import httpx
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from config.settings import settings


@dataclass
class PolymarketMarket:
    """Polymarket에서 가져온 마켓 데이터"""

    id: str
    title: str
    description: Optional[str]
    end_date: Optional[datetime]
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    url: str
    created_at: Optional[datetime] = None


class PolymarketClient:
    """Polymarket API 클라이언트"""

    def __init__(self):
        self.base_url = settings.polymarket_base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_active_markets(self, limit: int = 100) -> list[PolymarketMarket]:
        """활성 마켓 목록 조회"""
        markets = []

        try:
            # Gamma API로 이벤트 조회
            response = await self.client.get(
                f"{self.base_url}/events",
                params={
                    "closed": "false",
                    "limit": limit,
                    "active": "true",
                },
            )
            response.raise_for_status()
            data = response.json()

            for event in data:
                # 각 이벤트 내의 마켓들 추출
                event_markets = event.get("markets", [])

                for m in event_markets:
                    if m.get("closed", True):
                        continue

                    market = self._parse_market(m, event)
                    if market:
                        markets.append(market)

        except Exception as e:
            print(f"[ERROR] Failed to fetch markets: {e}")

        return markets

    async def get_new_markets(
        self, known_ids: set[str], limit: int = 100
    ) -> list[PolymarketMarket]:
        """신규 마켓만 필터링해서 반환"""
        all_markets = await self.get_active_markets(limit)
        new_markets = [m for m in all_markets if m.id not in known_ids]
        return new_markets

    def _parse_market(self, market_data: dict, event_data: dict) -> Optional[PolymarketMarket]:
        """API 응답을 PolymarketMarket 객체로 변환"""
        try:
            market_id = market_data.get("id") or market_data.get("condition_id")
            if not market_id:
                return None

            # 가격 파싱
            yes_price = 0.5
            no_price = 0.5

            outcomes = market_data.get("outcomes", [])
            outcome_prices = market_data.get("outcomePrices", [])

            if outcome_prices and len(outcome_prices) >= 2:
                try:
                    yes_price = float(outcome_prices[0])
                    no_price = float(outcome_prices[1])
                except (ValueError, TypeError):
                    pass

            # 마감일 파싱
            end_date = None
            end_date_str = market_data.get("endDate") or event_data.get("endDate")
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                except:
                    pass

            # 생성일 파싱
            created_at = None
            created_str = market_data.get("createdAt") or event_data.get("createdAt")
            if created_str:
                try:
                    created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except:
                    pass

            # URL 생성
            slug = event_data.get("slug", "")
            url = f"https://polymarket.com/event/{slug}" if slug else ""

            return PolymarketMarket(
                id=str(market_id),
                title=market_data.get("question") or event_data.get("title", "Unknown"),
                description=market_data.get("description") or event_data.get("description"),
                end_date=end_date,
                yes_price=yes_price,
                no_price=no_price,
                volume=float(market_data.get("volume", 0) or 0),
                liquidity=float(market_data.get("liquidity", 0) or 0),
                url=url,
                created_at=created_at,
            )

        except Exception as e:
            print(f"[ERROR] Failed to parse market: {e}")
            return None


# 싱글톤 클라이언트
_client: Optional[PolymarketClient] = None


async def get_client() -> PolymarketClient:
    global _client
    if _client is None:
        _client = PolymarketClient()
    return _client

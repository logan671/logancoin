#!/usr/bin/env python3
"""Polymarket API 테스트"""
import asyncio
import sys
sys.path.insert(0, '.')

from src.polymarket_client import PolymarketClient


async def test():
    print("Polymarket API 테스트 중...")
    print("=" * 50)

    client = PolymarketClient()

    try:
        markets = await client.get_active_markets(limit=10)
        print(f"\n활성 마켓 {len(markets)}개 발견!\n")

        for i, m in enumerate(markets[:5], 1):
            print(f"{i}. {m.title[:60]}...")
            print(f"   YES: {m.yes_price:.1%} | NO: {m.no_price:.1%}")
            print(f"   Volume: ${m.volume:,.0f}")
            print(f"   URL: {m.url}")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test())

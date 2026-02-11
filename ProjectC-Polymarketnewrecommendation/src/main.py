import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings
from src.database import (
    init_db,
    get_all_known_market_ids,
    save_market,
    get_markets_to_alert,
    mark_as_alerted,
    save_alert,
    get_active_learning_rules,
)
from src.polymarket_client import get_client, PolymarketMarket
from src.market_analyzer import get_analyzer
from src.telegram_notifier import get_notifier
from src.models import Alert

console = Console()


async def scan_new_markets():
    """신규 마켓 스캔 및 2단계 분석"""
    console.print(f"\n[bold blue][{datetime.now().strftime('%H:%M:%S')}] Scanning for new markets...[/bold blue]")

    try:
        # 이미 알고 있는 마켓 ID 조회
        known_ids = await get_all_known_market_ids()
        console.print(f"  Known markets: {len(known_ids)}")

        # 학습 규칙 로드
        learning_rules = await get_active_learning_rules()
        if learning_rules:
            console.print(f"  [dim]Active learning rules: {len(learning_rules)}[/dim]")

        # 신규 마켓 조회
        client = await get_client()
        new_markets = await client.get_new_markets(known_ids, limit=100)

        if not new_markets:
            console.print("  [dim]No new markets found[/dim]")
            return

        console.print(f"  [green]Found {len(new_markets)} new markets![/green]")

        # 분석기 준비
        analyzer = get_analyzer()
        passed_markets: list[tuple[PolymarketMarket, any]] = []

        # ============================================
        # 1차 스크리닝 (GPT-4o-mini, 저비용)
        # ============================================
        console.print(f"\n  [bold cyan]1차 스크리닝 (GPT-4o-mini)...[/bold cyan]")

        for poly_market in new_markets:
            passed, market = await analyzer.screen(poly_market, learning_rules)
            await save_market(market)

            status = "[green]PASS[/green]" if passed else "[dim]SKIP[/dim]"
            title_display = market.title_ko or poly_market.title
            console.print(f"    {status} {title_display[:50]}...")

            if passed:
                passed_markets.append((poly_market, market))

        console.print(f"\n  [yellow]1차 통과: {len(passed_markets)}/{len(new_markets)}[/yellow]")

        # ============================================
        # 2차 딥리서치 (Perplexity Sonar Pro, 고비용)
        # ============================================
        if passed_markets:
            console.print(f"\n  [bold magenta]2차 딥리서치 (Perplexity Sonar)...[/bold magenta]")

            for poly_market, market in passed_markets:
                console.print(f"    Researching: [cyan]{market.title_ko or poly_market.title[:50]}...[/cyan]")

                market = await analyzer.deep_research(market, poly_market)
                await save_market(market)

                # 결과 출력
                if market.alpha_score and market.alpha_score >= settings.alpha_threshold:
                    console.print(
                        f"      [bold yellow]Alpha: {market.alpha_score} | "
                        f"Type: {market.alpha_type} | "
                        f"Rec: {market.recommendation}[/bold yellow]"
                    )
                else:
                    console.print(f"      [dim]Alpha: {market.alpha_score or 0}[/dim]")

        # 알림 발송
        await send_alerts()

    except Exception as e:
        console.print(f"  [red]Error during scan: {e}[/red]")
        import traceback
        traceback.print_exc()


async def send_alerts():
    """알림 조건 충족 마켓에 알림 발송"""
    markets_to_alert = await get_markets_to_alert(settings.alpha_threshold)

    if not markets_to_alert:
        return

    notifier = get_notifier()
    console.print(f"\n[bold magenta]Sending {len(markets_to_alert)} alerts...[/bold magenta]")

    for market in markets_to_alert:
        message_id = await notifier.send_alert(market)

        # 알림 기록 저장
        alert = Alert(
            market_id=market.id,
            alpha_score=market.alpha_score or 0,
            alpha_type=market.alpha_type or "UNCERTAIN",
            message=market.title,
            telegram_message_id=message_id,
        )
        await save_alert(alert)
        await mark_as_alerted(market.id)

        console.print(f"  [green]Sent: {market.title_ko or market.title[:50]}...[/green]")


async def display_status():
    """현재 상태 출력"""
    known_ids = await get_all_known_market_ids()
    high_alpha = await get_markets_to_alert(settings.high_alpha_threshold)
    learning_rules = await get_active_learning_rules()

    table = Table(title="Polymarket Alpha Scanner Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Known Markets", str(len(known_ids)))
    table.add_row("High Alpha Pending", str(len(high_alpha)))
    table.add_row("Learning Rules", str(len(learning_rules)))
    table.add_row("Scan Interval", f"{settings.scan_interval_minutes} min")
    table.add_row("Alpha Threshold", str(settings.alpha_threshold))
    table.add_row("OpenAI (1차)", "O" if settings.openai_api_key else "X")
    table.add_row("Perplexity (2차)", "O" if settings.perplexity_api_key else "X")
    table.add_row("Telegram", "O" if settings.telegram_bot_token else "X")

    console.print(table)


async def run_once():
    """한 번만 실행 (테스트용)"""
    await init_db()
    await display_status()
    await scan_new_markets()
    await display_status()


async def run_scheduler():
    """스케줄러 실행"""
    await init_db()
    await display_status()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scan_new_markets,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="scan_markets",
    )
    scheduler.start()

    console.print(
        f"\n[bold green]Scanner started! "
        f"Scanning every {settings.scan_interval_minutes} minutes.[/bold green]"
    )
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    # 시작하자마자 한 번 실행
    await scan_new_markets()

    # 무한 대기
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        scheduler.shutdown()


def main():
    """CLI 엔트리포인트"""
    import sys

    console.print("[bold]Polymarket Alpha Scanner[/bold]")
    console.print("=" * 40)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            asyncio.run(run_once())
        elif sys.argv[1] == "--web":
            # 웹서버 실행
            import uvicorn
            from src.web.api import app

            console.print("[bold green]Starting web server...[/bold green]")
            uvicorn.run(app, host="0.0.0.0", port=8000)
        else:
            print("Usage: python run.py [--once|--web]")
    else:
        # 스케줄러 실행
        asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()

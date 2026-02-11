from telegram import Bot
from telegram.constants import ParseMode
from typing import Optional

from config.settings import settings
from src.models import Market


class TelegramNotifier:
    """텔레그램 알림 발송기"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        if settings.telegram_bot_token:
            self.bot = Bot(token=settings.telegram_bot_token)
        self.chat_id = settings.telegram_chat_id

    async def send_alert(self, market: Market) -> Optional[str]:
        """마켓 알림 발송"""

        if not self.bot or not self.chat_id:
            print("[WARN] Telegram not configured, printing to console")
            print(self._format_message(market))
            return None

        try:
            message = self._format_message(market)
            result = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            return str(result.message_id)

        except Exception as e:
            print(f"[ERROR] Failed to send telegram: {e}")
            return None

    def _format_message(self, market: Market) -> str:
        """알림 메시지 포맷팅"""

        # 알파 타입에 따른 헤더
        if market.alpha_type == "TYPE_A_FACT":
            header = "FACT-CHECK ALPHA"
            type_label = "TYPE A (이미 결과 확정)"
        elif market.alpha_type == "TYPE_B_PROBABILITY":
            header = "PROBABILITY ALPHA"
            type_label = "TYPE B (높은 확률 예측)"
        else:
            header = "POTENTIAL ALPHA"
            type_label = "분석 필요"

        # 알파 점수에 따른 이모지
        if market.alpha_score and market.alpha_score >= 80:
            score_emoji = "🔴"
        elif market.alpha_score and market.alpha_score >= 50:
            score_emoji = "🟡"
        else:
            score_emoji = "🟢"

        # 추천에 따른 액션
        rec = market.recommendation or "SKIP"
        if "STRONG_BUY_YES" in rec:
            action = "💰 강력 매수: YES"
        elif "BUY_YES" in rec:
            action = "📈 매수 고려: YES"
        elif "STRONG_BUY_NO" in rec:
            action = "💰 강력 매수: NO"
        elif "BUY_NO" in rec:
            action = "📉 매수 고려: NO"
        else:
            action = "👀 관망"

        # 근거 포맷팅
        evidence_text = ""
        if market.key_evidence:
            evidence_list = "\n".join(f"• {e}" for e in market.key_evidence[:3])
            evidence_text = f"\n\n<b>📋 근거:</b>\n{evidence_list}"

        # 리스크 포맷팅
        risk_text = ""
        if market.risk_factors:
            risk_list = "\n".join(f"• {r}" for r in market.risk_factors[:2])
            risk_text = f"\n\n<b>⚠️ 리스크:</b>\n{risk_list}"

        # 마감일
        end_date_str = market.end_date.strftime("%Y-%m-%d") if market.end_date else "Unknown"

        message = f"""
{'🚨' if market.alpha_score and market.alpha_score >= 80 else '🔔'} <b>{header}</b> {'🚨' if market.alpha_score and market.alpha_score >= 80 else '🔔'}

<b>📊 마켓:</b> {market.title}
<b>🏷️ 타입:</b> {type_label}
<b>📁 카테고리:</b> {market.category or 'other'}

<b>💰 현재 가격:</b>
  YES: {market.yes_price:.1%} / NO: {market.no_price:.1%}

<b>🎯 AI 예측:</b> YES {market.ai_prediction:.1%if market.ai_prediction else 'N/A'}
<b>📊 신뢰도:</b> {market.ai_confidence or 0}/100
{score_emoji} <b>알파 점수:</b> {market.alpha_score or 0}/100

<b>{action}</b>
{evidence_text}
{risk_text}

<b>📝 분석:</b>
{market.analysis_summary or 'No analysis available'}

<b>🔗 링크:</b> {market.polymarket_url or 'N/A'}
<b>⏰ 마감:</b> {end_date_str}
<b>📉 거래량:</b> ${market.volume:,.0f}
""".strip()

        return message


# 싱글톤
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier

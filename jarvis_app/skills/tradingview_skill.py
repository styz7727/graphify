from __future__ import annotations
from jarvis_app.skills.base_skill import BaseSkill, SkillResult
from jarvis_app.safety.permissions import SafetyLevel
from jarvis_app.tools.tradingview import open_chart


class TradingViewSkill(BaseSkill):
    name = "tradingview"
    description = "TradingView-Chart im Browser öffnen"
    keywords = ["tradingview", "chart", "kurs von", "bitcoin chart", "btc chart", "eth chart"]
    safety_level = SafetyLevel.CONFIRM
    examples = ["Öffne TradingView BTC", "Zeig mir den ETH Chart", "TradingView AAPL"]

    def handle(self, intent: str, entities: dict) -> SkillResult:
        symbol = entities.get("symbol", "BTC")
        msg = open_chart(symbol)
        return SkillResult(success=True, message=msg)

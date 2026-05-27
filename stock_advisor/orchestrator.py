from pathlib import Path
from typing import List

from .agents import (
    MarketDataAgent,
    NewsAgent,
    PortfolioAgent,
    ReportWriterAgent,
    RiskAgent,
    SignalAgent,
    UniverseAgent,
)
from .models import Position, RiskProfile


class DailyResearchOrchestrator:
    """Coordinates the specialist agents for one daily research run."""

    def __init__(self, config: dict):
        self.config = config
        self.universe_agent = UniverseAgent(config)
        self.market_data_agent = MarketDataAgent(config.get("market_data", {}))
        self.news_agent = NewsAgent(config.get("news", {}))
        self.portfolio_agent = PortfolioAgent()
        self.signal_agent = SignalAgent()
        self.risk_agent = RiskAgent()
        self.report_writer_agent = ReportWriterAgent()

    def run(self, positions: List[Position], output_dir: Path) -> Path:
        symbols = self.universe_agent.run(positions)
        symbol_names = self.universe_agent.symbol_names()
        risk_profile = self._load_risk_profile()

        market_data = self.market_data_agent.run(symbols)
        news = self.news_agent.run(symbols)
        portfolio = self.portfolio_agent.run(
            cash=float(self.config["portfolio"].get("cash", 0)),
            positions=positions,
            market_data=market_data,
        )
        signals = self.signal_agent.run(symbols, market_data, news, positions)
        recommendations = self.risk_agent.run(signals, portfolio, risk_profile)

        return self.report_writer_agent.run(
            recommendations=recommendations,
            portfolio=portfolio,
            market_data=market_data,
            symbol_names=symbol_names,
            output_dir=output_dir,
        )

    def _load_risk_profile(self) -> RiskProfile:
        risk_config = self.config["risk_profile"]
        return RiskProfile(
            style=risk_config.get("style", "balanced"),
            max_single_position_pct=float(risk_config["max_single_position_pct"]),
            max_new_position_pct=float(risk_config["max_new_position_pct"]),
            min_cash_pct=float(risk_config["min_cash_pct"]),
            target_invested_pct=float(risk_config.get("target_invested_pct", 80)),
        )

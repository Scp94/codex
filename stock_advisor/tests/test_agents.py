import unittest

from stock_advisor.agents import MarketDataAgent, PortfolioAgent, RiskAgent, SignalAgent
from stock_advisor.agents.universe import UniverseAgent
from stock_advisor.models import Position, RiskProfile


class AgentTests(unittest.TestCase):
    def test_signal_agent_marks_positive_momentum_as_watch_buy(self):
        market_data = MarketDataAgent(
            {
                "provider": "sample",
                "sample_prices": {
                    "NVDA": {
                        "price": 125,
                        "previous_close": 120,
                        "volume_vs_20d": 1.8,
                        "rsi": 65,
                        "pe": 45,
                    }
                },
            }
        ).run(["NVDA"])

        signals = SignalAgent().run(["NVDA"], market_data, {"NVDA": []})

        self.assertEqual(signals[0].action, "观察买入")
        self.assertGreater(signals[0].confidence, 0.5)

    def test_risk_agent_blocks_new_buy_when_cash_is_too_low(self):
        market_data = MarketDataAgent(
            {
                "provider": "sample",
                "sample_prices": {
                    "AAPL": {"price": 950, "previous_close": 900},
                    "NVDA": {"price": 125, "previous_close": 120, "volume_vs_20d": 2},
                },
            }
        ).run(["AAPL", "NVDA"])
        portfolio = PortfolioAgent().run(50, [Position("AAPL", 10, 100)], market_data)
        signals = SignalAgent().run(["NVDA"], market_data, {"NVDA": []})

        recs = RiskAgent().run(
            signals,
            portfolio,
            RiskProfile(
                style="balanced",
                max_single_position_pct=25,
                max_new_position_pct=10,
                min_cash_pct=10,
                target_invested_pct=80,
            ),
        )

        self.assertEqual(recs[0].action, "观察，不新增")

    def test_universe_agent_supports_domestic_symbol_names(self):
        agent = UniverseAgent(
            {
                "watchlist": [],
                "universe": [{"symbol": "600519.SH", "name": "贵州茅台"}],
            }
        )

        self.assertEqual(agent.run([]), ["600519.SH"])
        self.assertEqual(agent.symbol_names()["600519.SH"], "贵州茅台")


if __name__ == "__main__":
    unittest.main()

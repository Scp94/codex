from typing import Dict, List

from stock_advisor.models import MarketSnapshot, PortfolioContext, Position


class PortfolioAgent:
    """Turns holdings and cash into portfolio context for downstream agents."""

    def run(
        self,
        cash: float,
        positions: List[Position],
        market_data: Dict[str, MarketSnapshot],
    ) -> PortfolioContext:
        values = {}
        for position in positions:
            snapshot = market_data.get(position.symbol)
            if snapshot:
                if position.shares > 0:
                    values[position.symbol] = position.shares * snapshot.price
                elif position.principal > 0 and position.cost_basis > 0:
                    values[position.symbol] = (
                        position.principal / position.cost_basis * snapshot.price
                    )

        total_value = cash + sum(values.values())
        cash_pct = cash / total_value * 100 if total_value else 100
        return PortfolioContext(
            cash=cash,
            positions=positions,
            market_value_by_symbol=values,
            total_value=total_value,
            cash_pct=cash_pct,
        )

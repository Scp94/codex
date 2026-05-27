from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Position:
    symbol: str
    shares: float
    cost_basis: float
    principal: float = 0
    weekly_dca_day: Optional[str] = None
    dca_min: float = 0
    dca_max: float = 0


@dataclass(frozen=True)
class RiskProfile:
    style: str
    max_single_position_pct: float
    max_new_position_pct: float
    min_cash_pct: float
    target_invested_pct: float


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    previous_close: float
    volume_vs_20d: float
    rsi: Optional[float] = None
    pe: Optional[float] = None
    as_of_date: Optional[str] = None
    return_1d_pct: Optional[float] = None
    return_5d_pct: Optional[float] = None
    return_20d_pct: Optional[float] = None
    return_60d_pct: Optional[float] = None
    volatility_20d_pct: Optional[float] = None
    max_drawdown_60d_pct: Optional[float] = None
    ma20_deviation_pct: Optional[float] = None
    ma60_deviation_pct: Optional[float] = None

    @property
    def change_pct(self) -> float:
        if self.previous_close == 0:
            return 0.0
        return (self.price - self.previous_close) / self.previous_close * 100


@dataclass(frozen=True)
class NewsEvent:
    symbol: str
    title: str
    sentiment: str
    impact: int
    source_url: Optional[str] = None


@dataclass(frozen=True)
class PortfolioContext:
    cash: float
    positions: List[Position]
    market_value_by_symbol: Dict[str, float]
    total_value: float
    cash_pct: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    action: str
    score: float
    confidence: float
    reasons: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Recommendation:
    symbol: str
    action: str
    confidence: float
    score: float
    reasons: List[str]
    risks: List[str]
    position_note: str
    trade_plan: str

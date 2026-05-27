from datetime import datetime
from typing import Dict, Iterable, List

from stock_advisor.models import MarketSnapshot, NewsEvent, Position, Signal


class SignalAgent:
    """Combines market data and events into candidate investment signals."""

    def run(
        self,
        symbols: Iterable[str],
        market_data: Dict[str, MarketSnapshot],
        news: Dict[str, List[NewsEvent]],
        positions: List[Position] = None,
    ) -> List[Signal]:
        positions = positions or []
        positions_by_symbol = {position.symbol: position for position in positions}
        signals = []
        for symbol in symbols:
            snapshot = market_data.get(symbol)
            if not snapshot:
                signals.append(
                    Signal(
                        symbol=symbol,
                        action="缺少数据",
                        score=0,
                        confidence=0,
                        reasons=["没有找到行情快照"],
                        risks=["需要补充可靠数据源后再判断"],
                    )
                )
                continue

            score = 0.0
            reasons = []
            risks = []
            position = positions_by_symbol.get(symbol)
            is_fund = self._looks_like_fund(symbol)

            if is_fund:
                self._score_fund(symbol, snapshot, position, reasons, risks)
                score = self._fund_score(snapshot, position)
            elif snapshot.change_pct > 2:
                score += 1
                reasons.append(f"价格较前收盘上涨 {snapshot.change_pct:.2f}%，短线动量偏强")
            elif snapshot.change_pct < -2:
                score -= 1
                risks.append(f"价格较前收盘下跌 {abs(snapshot.change_pct):.2f}%，短线承压")

            if not is_fund and snapshot.rsi is not None:
                if snapshot.rsi > 70:
                    score -= 0.75
                    risks.append(f"RSI {snapshot.rsi:.0f}，存在过热风险")
                elif snapshot.rsi < 40:
                    score += 0.5
                    reasons.append(f"RSI {snapshot.rsi:.0f}，短线超卖后可能修复")

            if not is_fund and snapshot.pe is not None:
                if snapshot.pe > 50:
                    score -= 0.5
                    risks.append(f"PE {snapshot.pe:.1f}，估值容错率较低")
                elif snapshot.pe < 25:
                    score += 0.5
                    reasons.append(f"PE {snapshot.pe:.1f}，估值相对温和")

            if not is_fund and snapshot.volume_vs_20d > 1.5:
                score += 0.5
                reasons.append(f"成交量为 20 日均量的 {snapshot.volume_vs_20d:.1f} 倍，关注度上升")

            for event in news.get(symbol, []):
                score += event.impact
                if event.impact > 0:
                    reasons.append(f"正面事件：{event.title}")
                elif event.impact < 0:
                    risks.append(f"负面事件：{event.title}")
                else:
                    reasons.append(f"中性事件：{event.title}")

            if score >= 1.5:
                action = "观察买入"
            elif score <= -1:
                action = "谨慎/减仓"
            else:
                action = "持有/观察"

            confidence = min(0.9, max(0.35, 0.45 + abs(score) * 0.12))
            signals.append(
                Signal(
                    symbol=symbol,
                    action=action,
                    score=score,
                    confidence=confidence,
                    reasons=reasons or ["没有明显优势信号"],
                    risks=risks or ["仍需关注大盘和个股突发事件"],
                )
            )
        return signals

    def _looks_like_fund(self, symbol: str) -> bool:
        return symbol.isdigit() and len(symbol) == 6

    def _score_fund(
        self,
        symbol: str,
        snapshot: MarketSnapshot,
        position: Position,
        reasons: List[str],
        risks: List[str],
    ) -> None:
        if snapshot.as_of_date:
            reasons.append(f"最新净值日期：{snapshot.as_of_date}")
        reasons.append(f"最新单位净值 {snapshot.price:.4f}，单日变化 {snapshot.change_pct:.2f}%")

        if snapshot.return_20d_pct is not None:
            if snapshot.return_20d_pct > 3:
                reasons.append(f"近 20 个交易日上涨 {snapshot.return_20d_pct:.2f}%，趋势偏强")
            elif snapshot.return_20d_pct < -3:
                risks.append(f"近 20 个交易日下跌 {abs(snapshot.return_20d_pct):.2f}%，趋势偏弱")

        if snapshot.rsi is not None:
            if snapshot.rsi < 35:
                reasons.append(f"RSI {snapshot.rsi:.0f}，可能处于阶段低位")
            elif snapshot.rsi > 70:
                risks.append(f"RSI {snapshot.rsi:.0f}，短期可能偏热")

        if position:
            gain_pct = (snapshot.price - position.cost_basis) / position.cost_basis * 100
            if gain_pct >= 8:
                risks.append(f"相对持仓成本浮盈 {gain_pct:.2f}%，可考虑分批止盈")
            elif gain_pct <= -8:
                reasons.append(f"相对持仓成本浮亏 {abs(gain_pct):.2f}%，若基本面未变可考虑分批补仓")
            else:
                reasons.append(f"相对持仓成本收益 {gain_pct:.2f}%，未触发大幅止盈/补仓阈值")

            if position.weekly_dca_day and self._is_dca_day(position.weekly_dca_day):
                reasons.append(
                    f"今天是定投日，可在 {position.dca_min:.0f}-{position.dca_max:.0f} 元区间内动态定投"
                )

    def _fund_score(self, snapshot: MarketSnapshot, position: Position) -> float:
        score = 0.0
        if snapshot.return_20d_pct is not None:
            if snapshot.return_20d_pct > 3:
                score += 1.0
            elif snapshot.return_20d_pct < -3:
                score -= 0.75
        if snapshot.change_pct <= -1:
            score += 0.4
        elif snapshot.change_pct >= 2:
            score -= 0.2
        if snapshot.rsi is not None:
            if snapshot.rsi < 35:
                score += 0.8
            elif snapshot.rsi > 70:
                score -= 0.8
        if position:
            gain_pct = (snapshot.price - position.cost_basis) / position.cost_basis * 100
            if gain_pct <= -8:
                score += 0.8
            elif gain_pct >= 8:
                score -= 1.4
            if position.weekly_dca_day and self._is_dca_day(position.weekly_dca_day):
                score += 0.4
        return score

    def _is_dca_day(self, day: str) -> bool:
        aliases = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "周一": 0,
            "周二": 1,
            "周三": 2,
            "周四": 3,
            "周五": 4,
        }
        return datetime.now().weekday() == aliases.get(day.lower(), aliases.get(day))

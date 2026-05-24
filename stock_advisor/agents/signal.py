from typing import Dict, Iterable, List

from stock_advisor.models import MarketSnapshot, NewsEvent, Signal


class SignalAgent:
    """Combines market data and events into candidate investment signals."""

    def run(
        self,
        symbols: Iterable[str],
        market_data: Dict[str, MarketSnapshot],
        news: Dict[str, List[NewsEvent]],
    ) -> List[Signal]:
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

            if snapshot.change_pct > 2:
                score += 1
                reasons.append(f"价格较前收盘上涨 {snapshot.change_pct:.2f}%，短线动量偏强")
            elif snapshot.change_pct < -2:
                score -= 1
                risks.append(f"价格较前收盘下跌 {abs(snapshot.change_pct):.2f}%，短线承压")

            if snapshot.rsi is not None:
                if snapshot.rsi > 70:
                    score -= 0.75
                    risks.append(f"RSI {snapshot.rsi:.0f}，存在过热风险")
                elif snapshot.rsi < 40:
                    score += 0.5
                    reasons.append(f"RSI {snapshot.rsi:.0f}，短线超卖后可能修复")

            if snapshot.pe is not None:
                if snapshot.pe > 50:
                    score -= 0.5
                    risks.append(f"PE {snapshot.pe:.1f}，估值容错率较低")
                elif snapshot.pe < 25:
                    score += 0.5
                    reasons.append(f"PE {snapshot.pe:.1f}，估值相对温和")

            if snapshot.volume_vs_20d > 1.5:
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

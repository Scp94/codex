from typing import List

from stock_advisor.models import PortfolioContext, Recommendation, RiskProfile, Signal


class RiskAgent:
    """Applies portfolio limits and converts signals into usable recommendations."""

    def run(
        self,
        signals: List[Signal],
        portfolio: PortfolioContext,
        risk_profile: RiskProfile,
    ) -> List[Recommendation]:
        held_symbols = {position.symbol for position in portfolio.positions}
        buy_candidates = [signal for signal in signals if signal.action == "观察买入"]
        buy_candidates.sort(key=lambda signal: signal.score, reverse=True)
        top_buy_symbols = {signal.symbol for signal in buy_candidates[:3]}
        recommendations: List[Recommendation] = []

        for signal in signals:
            current_value = portfolio.market_value_by_symbol.get(signal.symbol, 0)
            current_pct = (
                current_value / portfolio.total_value * 100
                if portfolio.total_value
                else 0
            )
            action = signal.action
            risks = list(signal.risks)
            trade_plan = "今日不建议操作，继续观察。"

            if action == "观察买入" and signal.symbol not in top_buy_symbols:
                action = "候选观察"
                risks.append("买入候选排序未进入前三，优先级低于其他标的")
                trade_plan = "暂不买入，放入观察名单。"

            if action == "观察买入" and portfolio.cash_pct <= risk_profile.min_cash_pct:
                action = "观察，不新增"
                risks.append(
                    f"现金比例 {portfolio.cash_pct:.1f}% 已接近最低要求 {risk_profile.min_cash_pct:.1f}%"
                )
                trade_plan = "现金缓冲不足，今日不新增仓位。"

            if current_pct > risk_profile.max_single_position_pct:
                action = "谨慎/减仓"
                risks.append(
                    f"当前仓位 {current_pct:.1f}% 超过单票上限 {risk_profile.max_single_position_pct:.1f}%"
                )
                trade_plan = (
                    f"可考虑减至不超过组合 {risk_profile.max_single_position_pct:.1f}%。"
                )

            if signal.symbol in held_symbols:
                position_note = f"当前约占组合 {current_pct:.1f}%"
                if action == "观察买入":
                    room_pct = max(0, risk_profile.max_single_position_pct - current_pct)
                    add_pct = min(risk_profile.max_new_position_pct, room_pct)
                    trade_plan = f"如确认数据无误，可考虑加仓不超过组合 {add_pct:.1f}%。"
                elif action == "持有/观察":
                    trade_plan = "已有持仓可继续持有，暂不加仓。"
            else:
                position_note = (
                    f"如新开仓，建议不超过组合 {risk_profile.max_new_position_pct:.1f}%"
                )
                if action == "观察买入":
                    available_cash_pct = max(0, portfolio.cash_pct - risk_profile.min_cash_pct)
                    buy_pct = min(risk_profile.max_new_position_pct, available_cash_pct)
                    trade_plan = f"如确认适合你的风险偏好，可考虑试探建仓不超过组合 {buy_pct:.1f}%。"
                elif action == "谨慎/减仓":
                    trade_plan = "未持有则不建议新开仓。"

            recommendations.append(
                Recommendation(
                    symbol=signal.symbol,
                    action=action,
                    confidence=signal.confidence,
                    score=signal.score,
                    reasons=signal.reasons,
                    risks=risks,
                    position_note=position_note,
                    trade_plan=trade_plan,
                )
            )
        return sorted(recommendations, key=lambda rec: rec.score, reverse=True)

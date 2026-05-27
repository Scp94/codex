from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from stock_advisor.models import MarketSnapshot, PortfolioContext, Position, Recommendation


class ReportWriterAgent:
    """Writes the final user-facing daily research report."""

    def run(
        self,
        recommendations: List[Recommendation],
        portfolio: PortfolioContext,
        market_data: Dict[str, MarketSnapshot],
        symbol_names: Dict[str, str],
        output_dir: Path,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        report_path = output_dir / f"daily_report_{now:%Y-%m-%d}.md"

        lines = [
            f"# 每日基金理财简报 {now:%Y-%m-%d}",
            "",
            "## 今日执行摘要",
            "",
        ]

        buy_recs = [rec for rec in recommendations if rec.action == "观察买入"]
        sell_recs = [rec for rec in recommendations if rec.action == "谨慎/减仓"]
        if buy_recs:
            lines.append(
                f"- 优先候选：{', '.join(self._label(rec.symbol, symbol_names) for rec in buy_recs[:3])}"
            )
        else:
            lines.append("- 今日没有达到买入阈值的优先候选。")
        if sell_recs:
            lines.append(
                f"- 风险处理：{', '.join(self._label(rec.symbol, symbol_names) for rec in sell_recs)} 需要重点复核。"
            )
        else:
            lines.append("- 当前没有触发减仓规则的标的。")

        lines.extend(
            [
                "- 所有动作都需要人工复核基金净值、费率、赎回规则和个人风险承受能力。",
                "",
            ]
        )

        lines.extend(
            [
            "## 组合概览",
            "",
            f"- 总资产估算：{portfolio.total_value:,.2f}",
            "",
            "## 今日基金建议与理由",
            "",
            "以下为持有基金优先、同类按评分排序后的操作建议：",
            "",
            ]
        )

        for rec in recommendations:
            label = self._label(rec.symbol, symbol_names)
            snapshot = market_data.get(rec.symbol)
            if snapshot:
                price_line = (
                    f"现价 {snapshot.price:.2f}，日涨跌 {snapshot.change_pct:.2f}%"
                )
            else:
                price_line = "缺少行情数据"

            lines.extend(
                [
                    f"### {label}：{rec.action}",
                    "",
                    f"- 评分：{rec.score:.2f}",
                    f"- 置信度：{rec.confidence:.0%}",
                    f"- 建议：{rec.action}",
                    f"- 净值：{price_line}",
                    f"- 持仓：{rec.position_note}",
                    f"- 操作建议：{rec.trade_plan}",
                ]
            )
            holding_lines = self._holding_lines(rec.symbol, portfolio, market_data)
            if holding_lines:
                lines.extend(holding_lines)
            lines.append("- 理由：")
            lines.extend([f"  - {reason}" for reason in rec.reasons])
            lines.append("- 风险：")
            lines.extend([f"  - {risk}" for risk in rec.risks])
            lines.append("")

        lines.extend(
            [
                "## 风险提示",
                "",
                "本报告由本地多 agent MVP 自动生成，仅供研究参考，不构成个性化投资建议或买卖指令。请结合自身风险承受能力，并在真实申购或赎回前人工复核净值、费率、持有期、赎回到账时间和基金风险等级。",
                "",
            ]
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def _label(self, symbol: str, symbol_names: Dict[str, str]) -> str:
        name = symbol_names.get(symbol)
        return f"{name}（{symbol}）" if name else symbol

    def _holding_lines(
        self,
        symbol: str,
        portfolio: PortfolioContext,
        market_data: Dict[str, MarketSnapshot],
    ) -> List[str]:
        position = self._position_for_symbol(symbol, portfolio.positions)
        snapshot = market_data.get(symbol)
        if not position or not snapshot:
            return []

        shares = self._shares(position)
        if shares <= 0:
            return []

        market_value = portfolio.market_value_by_symbol.get(
            symbol,
            shares * snapshot.price,
        )
        cost_amount = position.principal or shares * position.cost_basis
        today_gain = shares * (snapshot.price - snapshot.previous_close)
        holding_gain = market_value - cost_amount
        holding_return_pct = holding_gain / cost_amount * 100 if cost_amount else 0
        return [
            f"- 持有总金额：{market_value:,.2f}",
            f"- 今日收益：{today_gain:,.2f} 元",
            f"- 持有收益：{holding_gain:,.2f} 元",
            f"- 持有收益率：{holding_return_pct:.2f}%",
        ]

    def _position_for_symbol(
        self,
        symbol: str,
        positions: List[Position],
    ) -> Optional[Position]:
        for position in positions:
            if position.symbol == symbol:
                return position
        return None

    def _shares(self, position: Position) -> float:
        if position.shares > 0:
            return position.shares
        if position.principal > 0 and position.cost_basis > 0:
            return position.principal / position.cost_basis
        return 0

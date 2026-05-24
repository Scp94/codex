from datetime import datetime
from pathlib import Path
from typing import Dict, List

from stock_advisor.models import MarketSnapshot, PortfolioContext, Recommendation


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
            f"# 每日股票投研简报 {now:%Y-%m-%d}",
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
                "- 所有动作都需要人工复核真实行情、新闻来源和个人风险承受能力。",
                "",
            ]
        )

        lines.extend(
            [
            "## 组合概览",
            "",
            f"- 总资产估算：{portfolio.total_value:,.2f}",
            f"- 现金：{portfolio.cash:,.2f}（{portfolio.cash_pct:.1f}%）",
            "",
            "## 今日建议",
            "",
            "以下为按评分排序后的操作建议：",
            "",
            ]
        )

        for rec in recommendations:
            label = self._label(rec.symbol, symbol_names)
            lines.extend(
                [
                    f"### {label}：{rec.action}",
                    "",
                    f"- 评分：{rec.score:.2f}",
                    f"- 置信度：{rec.confidence:.0%}",
                    f"- 操作计划：{rec.trade_plan}",
                    "",
                ]
            )

        lines.extend(["", "## 详细理由", ""])
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
                    f"### {label}",
                    "",
                    f"- 建议：{rec.action}",
                    f"- 行情：{price_line}",
                    f"- 仓位：{rec.position_note}",
                    f"- 操作计划：{rec.trade_plan}",
                    "- 理由：",
                ]
            )
            lines.extend([f"  - {reason}" for reason in rec.reasons])
            lines.append("- 风险：")
            lines.extend([f"  - {risk}" for risk in rec.risks])
            lines.append("")

        lines.extend(
            [
                "## 风险提示",
                "",
                "本报告由本地多 agent MVP 自动生成，仅供研究参考，不构成个性化投资建议或买卖指令。请结合自身风险承受能力，并在真实交易前人工复核数据来源、仓位和流动性。",
                "",
            ]
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def _label(self, symbol: str, symbol_names: Dict[str, str]) -> str:
        name = symbol_names.get(symbol)
        return f"{name}（{symbol}）" if name else symbol

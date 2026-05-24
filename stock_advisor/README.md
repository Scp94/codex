# Stock Advisor MVP

一个本地运行的多 agent 股票投研日报 MVP。第一版只生成研究参考报告，不自动交易。

## 快速开始

```bash
pip install -r requirements.txt
python3 -m stock_advisor.cli --config stock_advisor/config.example.json
```

报告会输出到 `stock_advisor/reports/`。

## 配置

复制示例配置后编辑：

```bash
cp stock_advisor/config.example.json stock_advisor/config.json
python3 -m stock_advisor.cli --config stock_advisor/config.json
```

主要字段：

- `portfolio.cash`: 现金
- `portfolio.positions`: 当前持仓
- `universe`: 系统主动扫描的股票池
- `watchlist`: 你特别关注的股票，可为空
- `risk_profile`: 风险偏好和仓位约束
- `notifications.dingtalk`: 钉钉机器人推送配置

## Agent 流程

1. `agents/universe.py` - `UniverseAgent`: 合并持仓、观察列表和国内股票池
2. `agents/market_data.py` - `MarketDataAgent`: 获取行情数据
3. `agents/news.py` - `NewsAgent`: 汇总新闻事件
4. `agents/portfolio.py` - `PortfolioAgent`: 分析持仓
5. `agents/signal.py` - `SignalAgent`: 生成候选信号
6. `agents/risk.py` - `RiskAgent`: 做仓位和风险过滤，输出操作计划
7. `agents/report_writer.py` - `ReportWriterAgent`: 输出 Markdown 日报

`orchestrator.py` 负责把这些 agent 串成一次每日投研流程。每个 agent 都可以独立替换成 LLM agent、外部 API agent 或后台服务。

## 钉钉推送

推荐用环境变量保存机器人 webhook 和加签 secret：

```bash
export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=你的token"
export DINGTALK_SECRET="SEC开头的加签密钥"
python3 -m stock_advisor.cli --config stock_advisor/config.json --send-dingtalk
```

默认 `require_signing` 为 `true`。也可以在 `config.json` 中把 `notifications.dingtalk.enabled` 设为 `true`，之后每次执行都会推送。

## 下一步可接入

- 新闻、公告和财报事件源，例如交易所公告、巨潮资讯、东方财富新闻或券商 API

## A 股真实行情

`stock_advisor/config.json` 已配置为：

```json
{
  "market_data": {
    "provider": "akshare",
    "use_realtime_spot": false
  }
}
```

默认使用 AKShare 的 A 股日线历史行情。`use_realtime_spot` 设为 `true` 后会尝试拉取东方财富实时行情，但该接口在部分代理网络下可能不稳定。
- SEC EDGAR 财报与公告
- OpenAI API 生成更自然的新闻解读
- 定时任务：cron、GitHub Actions 或本地 launchd
- 回测数据库：SQLite / PostgreSQL

## 免责声明

本项目生成内容仅供研究参考，不构成个性化投资建议，也不保证收益。

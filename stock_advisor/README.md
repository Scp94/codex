# Fund Advisor MVP

一个本地运行的多 agent 基金理财日报 MVP。第一版只生成研究参考报告，不自动交易。

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
- `universe`: 系统主动扫描的候选基金池
- `watchlist`: 你特别关注的基金，可为空
- `risk_profile`: 风险偏好和仓位约束
- `notifications.dingtalk`: 钉钉机器人推送配置

## Agent 流程

1. `agents/universe.py` - `UniverseAgent`: 合并持仓、观察列表和候选基金池
2. `agents/market_data.py` - `MarketDataAgent`: 获取基金净值数据
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

## API 服务

```bash
export STOCK_ADVISOR_CONFIG=stock_advisor/config.json
export STOCK_ADVISOR_OUTPUT_DIR=stock_advisor/reports
export STOCK_ADVISOR_API_TOKEN="change-me"
uvicorn stock_advisor.api:app --host 0.0.0.0 --port 8000
```

常用接口：

- `GET /portfolio`: 查看现金、持仓和候选基金池
- `POST /portfolio/funds`: 新增或更新持仓基金
- `DELETE /portfolio/funds/{symbol}`: 删除持仓基金
- `POST /portfolio/trades`: 记录买入或卖出金额
- `GET /portfolio/trades`: 查看交易流水
- `POST /analysis/run`: 立即生成报告，可推送钉钉

如果设置了 `STOCK_ADVISOR_API_TOKEN`，请求需要带：

```text
Authorization: Bearer change-me
```

示例：

```bash
curl -H "Authorization: Bearer change-me" \
  http://127.0.0.1:8000/portfolio

curl -X POST \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8000/portfolio/trades \
  -d '{"symbol":"007509","action":"buy","amount":1000,"nav":4.7960}'

curl -X POST \
  -H "Authorization: Bearer change-me" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8000/analysis/run \
  -d '{"send_dingtalk":true}'
```

## 阿里云部署

```bash
cd stock_advisor
export STOCK_ADVISOR_API_TOKEN="change-me"
docker compose up -d --build
```

部署前建议修改 `docker-compose.yml` 里的 `STOCK_ADVISOR_API_TOKEN`，并把服务器安全组只开放给可信来源。容器会：

- 启动 HTTP API：`0.0.0.0:8000`
- 按 `STOCK_ADVISOR_DAILY_RUN_TIME` 每天自动生成并推送报告
- 允许通过 `POST /analysis/run` 手动触发一次分析推送

完整部署步骤和每个接口的 `curl` 示例见 [DEPLOY_ALIYUN.md](./DEPLOY_ALIYUN.md)。

## 基金真实净值

`stock_advisor/config.json` 已配置为：

```json
{
  "market_data": {
    "provider": "akshare_fund"
  }
}
```

默认使用 AKShare 的开放式基金单位净值走势接口。

## 下一步可接入

- 基金经理、规模、持仓行业、最大回撤和夏普比率
- 支付宝/天天基金页面数据或自定义候选基金池
- SQLite / PostgreSQL 保存交易流水和历史报告

## 免责声明

本项目生成内容仅供研究参考，不构成个性化投资建议，也不保证收益。

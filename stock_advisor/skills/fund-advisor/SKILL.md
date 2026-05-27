---
name: fund-advisor
description: Use when building or updating a personal China mutual fund advisor that analyzes held funds, daily NAV changes, DCA plans, redemption risk, candidate funds, DingTalk reports, and API endpoints for fund position/trade management.
---

# Fund Advisor

Use this skill for the personal fund-advisor service in `stock_advisor`.

## Core Workflow

1. Read `stock_advisor/config.json` or `config.example.json`.
2. Treat `portfolio.positions` as the user's held funds.
3. Treat `universe` as the held plus candidate fund pool.
4. Fetch NAV data with `MarketDataAgent` provider `akshare_fund`.
5. Generate signals with cost basis, recent NAV trend, RSI, and DCA day context.
6. Apply risk controls before recommending add, hold, pause, or redeem.
7. Render DingTalk-friendly Markdown. Avoid Markdown tables.
8. For API changes, keep config writes atomic and preserve local secrets.

## Position Schema

```json
{
  "symbol": "007509",
  "principal": 2000,
  "shares": 0,
  "cost_basis": 4.4888,
  "weekly_dca_day": "周二",
  "dca_min": 1000,
  "dca_max": 4000
}
```

If `shares` is `0`, estimate shares as `principal / cost_basis`.

## Signal Rules

- Strong recent trend: add score when 20-day NAV return is above 3%.
- Weak recent trend: reduce score when 20-day NAV return is below -3%.
- Pullback: small positive score when daily NAV change is below -1%.
- Overheat: reduce score when RSI is above 70.
- Low zone: add score when RSI is below 35.
- Held loss: add score when current NAV is more than 8% below cost basis.
- Held gain: reduce score and consider profit-taking when current NAV is more than 8% above cost basis.
- DCA day: add a small score and mention the configured DCA range.

## API Expectations

The FastAPI service should support:

- `GET /portfolio`
- `PUT /portfolio/cash`
- `POST /portfolio/funds`
- `DELETE /portfolio/funds/{symbol}`
- `POST /portfolio/trades`
- `POST /analysis/run`

Protect mutating endpoints with `STOCK_ADVISOR_API_TOKEN` in deployed environments.

## Safety

Always include that the report is research-only and not a guaranteed buy/sell instruction. For real trades, remind the user to verify NAV date, subscription/redemption fees, holding period, risk rating, and redemption settlement time.

import json
import errno
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

from .agents import MarketDataAgent
from .cli import parse_positions
from .notifiers import DingTalkNotifier
from .orchestrator import DailyResearchOrchestrator


CONFIG_PATH = Path(os.environ.get("STOCK_ADVISOR_CONFIG", "stock_advisor/config.json"))
OUTPUT_DIR = Path(os.environ.get("STOCK_ADVISOR_OUTPUT_DIR", "stock_advisor/reports"))
DAILY_RUN_TIME = os.environ.get("STOCK_ADVISOR_DAILY_RUN_TIME", "09:30")
API_TOKEN = os.environ.get("STOCK_ADVISOR_API_TOKEN", "")

_config_lock = threading.Lock()


class Utf8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Fund Advisor API",
    version="0.1.0",
    default_response_class=Utf8JSONResponse,
)


class FundPositionRequest(BaseModel):
    symbol: str = Field(..., examples=["007509"])
    name: Optional[str] = Field(default=None, examples=["华商润丰灵活配置混合C"])
    principal: float = Field(default=0, ge=0)
    shares: float = Field(default=0, ge=0)
    cost_basis: float = Field(..., gt=0)
    weekly_dca_day: Optional[str] = Field(default=None, examples=["周二"])
    dca_min: float = Field(default=0, ge=0)
    dca_max: float = Field(default=0, ge=0)


class TradeRequest(BaseModel):
    symbol: str = Field(..., examples=["007509"])
    action: str = Field(..., pattern="^(buy|sell)$")
    amount: float = Field(..., gt=0, description="买入或卖出金额，单位：元")
    nav: Optional[float] = Field(default=None, gt=0, description="成交净值；不传则尝试使用最新净值")
    name: Optional[str] = None


class CashRequest(BaseModel):
    cash: float = Field(..., ge=0)


class AnalyzeRequest(BaseModel):
    send_dingtalk: bool = True


def require_token(
    token: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    if not API_TOKEN:
        return
    bearer = f"Bearer {API_TOKEN}"
    if authorization == bearer or x_api_key == API_TOKEN or token == API_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Invalid API token")


def load_config() -> Dict[str, Any]:
    with _config_lock:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: Dict[str, Any]) -> None:
    with _config_lock:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        temp_path = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
        temp_path.write_text(payload, encoding="utf-8")
        try:
            temp_path.replace(CONFIG_PATH)
        except OSError as exc:
            if exc.errno not in {errno.EBUSY, errno.EXDEV}:
                raise
            # Docker single-file bind mounts can reject os.replace with EBUSY.
            CONFIG_PATH.write_text(payload, encoding="utf-8")
            temp_path.unlink(missing_ok=True)


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def position_to_dict(request: FundPositionRequest) -> Dict[str, Any]:
    data = request.model_dump(exclude_none=True)
    data["symbol"] = normalize_symbol(data["symbol"])
    return data


def ensure_universe_item(config: Dict[str, Any], symbol: str, name: Optional[str]) -> None:
    universe = config.setdefault("universe", [])
    for item in universe:
        item_symbol = item.get("symbol") if isinstance(item, dict) else item
        if normalize_symbol(item_symbol) == symbol:
            if isinstance(item, dict) and name:
                item["name"] = name
            return
    universe.append({"symbol": symbol, "name": name or symbol})


def latest_nav(config: Dict[str, Any], symbol: str, fallback: float) -> float:
    try:
        snapshot = MarketDataAgent(config.get("market_data", {})).run([symbol]).get(symbol)
        if snapshot:
            return snapshot.price
    except Exception:
        pass
    return fallback


def run_analysis(send_dingtalk: bool) -> Dict[str, Any]:
    config = load_config()
    positions = parse_positions(config["portfolio"].get("positions", []))
    report_path = DailyResearchOrchestrator(config).run(positions, OUTPUT_DIR)
    if send_dingtalk:
        DingTalkNotifier(config.get("notifications", {}).get("dingtalk", {})).send_report(report_path)
    return {
        "report_path": str(report_path),
        "report": report_path.read_text(encoding="utf-8"),
        "sent_dingtalk": send_dingtalk,
    }


@app.on_event("startup")
def start_daily_scheduler() -> None:
    if os.environ.get("STOCK_ADVISOR_DISABLE_SCHEDULER") == "1":
        return
    thread = threading.Thread(target=_daily_scheduler_loop, daemon=True)
    thread.start()


def _daily_scheduler_loop() -> None:
    timezone = ZoneInfo("Asia/Shanghai")
    while True:
        now = datetime.now(timezone)
        hour, minute = [int(part) for part in DAILY_RUN_TIME.split(":", 1)]
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        time.sleep(max(1, int((next_run - now).total_seconds())))
        try:
            run_analysis(send_dingtalk=True)
        except Exception as exc:
            print(f"Scheduled fund advisor run failed: {exc}", flush=True)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/portfolio", dependencies=[Depends(require_token)])
def get_portfolio() -> Dict[str, Any]:
    config = load_config()
    return {
        "cash": config.get("portfolio", {}).get("cash", 0),
        "positions": config.get("portfolio", {}).get("positions", []),
        "universe": config.get("universe", []),
        "transactions": config.get("transactions", []),
    }


def update_cash_value(cash: float) -> Dict[str, Any]:
    config = load_config()
    if cash < 0:
        raise HTTPException(status_code=400, detail="cash must be greater than or equal to 0")
    config.setdefault("portfolio", {})["cash"] = cash
    save_config(config)
    return {"cash": cash}


@app.get("/portfolio/cash", dependencies=[Depends(require_token)])
def update_cash(
    cash: float = Query(..., ge=0, description="现金金额，单位：元"),
) -> Dict[str, Any]:
    return update_cash_value(cash)


@app.put("/portfolio/cash", dependencies=[Depends(require_token)])
def update_cash_legacy(request: CashRequest) -> Dict[str, Any]:
    return update_cash_value(request.cash)


def upsert_fund_position(request: FundPositionRequest) -> Dict[str, Any]:
    config = load_config()
    position = position_to_dict(request)
    positions = config.setdefault("portfolio", {}).setdefault("positions", [])
    positions[:] = [item for item in positions if normalize_symbol(item["symbol"]) != position["symbol"]]
    positions.append(position)
    ensure_universe_item(config, position["symbol"], request.name)
    save_config(config)
    return {"position": position}


@app.get("/portfolio/funds/upsert", dependencies=[Depends(require_token)])
def upsert_fund(
    symbol: str = Query(..., description="基金代码，如 007509"),
    cost_basis: float = Query(..., gt=0, description="持仓成本净值"),
    name: Optional[str] = Query(default=None, description="基金名称"),
    principal: float = Query(default=0, ge=0, description="本金/持仓成本金额，单位：元"),
    shares: float = Query(default=0, ge=0, description="持有份额；不清楚可传 0"),
    weekly_dca_day: Optional[str] = Query(default=None, description="定投日，如 周二"),
    dca_min: float = Query(default=0, ge=0, description="单次定投最低金额"),
    dca_max: float = Query(default=0, ge=0, description="单次定投最高金额"),
) -> Dict[str, Any]:
    request = FundPositionRequest(
        symbol=symbol,
        name=name,
        principal=principal,
        shares=shares,
        cost_basis=cost_basis,
        weekly_dca_day=weekly_dca_day,
        dca_min=dca_min,
        dca_max=dca_max,
    )
    return upsert_fund_position(request)


@app.post("/portfolio/funds", dependencies=[Depends(require_token)])
def upsert_fund_legacy(request: FundPositionRequest) -> Dict[str, Any]:
    return upsert_fund_position(request)


def delete_fund_position(symbol: str) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    config = load_config()
    positions = config.setdefault("portfolio", {}).setdefault("positions", [])
    before = len(positions)
    positions[:] = [item for item in positions if normalize_symbol(item["symbol"]) != normalized]
    if len(positions) == before:
        raise HTTPException(status_code=404, detail="Fund position not found")
    save_config(config)
    return {"deleted": normalized}


@app.get("/portfolio/funds/delete", dependencies=[Depends(require_token)])
def delete_fund(
    symbol: str = Query(..., description="要删除的基金代码"),
) -> Dict[str, Any]:
    return delete_fund_position(symbol)


@app.delete("/portfolio/funds/{symbol}", dependencies=[Depends(require_token)])
def delete_fund_legacy(symbol: str) -> Dict[str, Any]:
    return delete_fund_position(symbol)


def record_trade_request(request: TradeRequest) -> Dict[str, Any]:
    symbol = normalize_symbol(request.symbol)
    config = load_config()
    positions = config.setdefault("portfolio", {}).setdefault("positions", [])
    position = next((item for item in positions if normalize_symbol(item["symbol"]) == symbol), None)
    if not position:
        if request.action == "sell":
            raise HTTPException(status_code=404, detail="Cannot sell a fund that is not held")
        position = {"symbol": symbol, "principal": 0, "shares": 0, "cost_basis": request.nav or 1}
        positions.append(position)

    nav = request.nav or latest_nav(config, symbol, float(position["cost_basis"]))
    current_shares = float(position.get("shares") or 0)
    principal = float(position.get("principal") or 0)
    cost_basis = float(position.get("cost_basis") or nav)
    if current_shares <= 0 and principal > 0 and cost_basis > 0:
        current_shares = principal / cost_basis

    trade_shares = request.amount / nav
    if request.action == "buy":
        new_shares = current_shares + trade_shares
        new_principal = principal + request.amount
        new_cost_basis = new_principal / new_shares
        position.update(
            {
                "shares": round(new_shares, 4),
                "principal": round(new_principal, 2),
                "cost_basis": round(new_cost_basis, 4),
            }
        )
        ensure_universe_item(config, symbol, request.name)
    else:
        if trade_shares > current_shares:
            raise HTTPException(status_code=400, detail="Sell amount exceeds current estimated holding")
        new_shares = current_shares - trade_shares
        new_principal = max(0, new_shares * cost_basis)
        position.update(
            {
                "shares": round(new_shares, 4),
                "principal": round(new_principal, 2),
                "cost_basis": round(cost_basis, 4),
            }
        )

    transaction = {
        "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "symbol": symbol,
        "action": request.action,
        "amount": round(request.amount, 2),
        "nav": round(nav, 4),
        "shares": round(trade_shares, 4),
    }
    config.setdefault("transactions", []).append(transaction)
    save_config(config)
    return {
        "position": position,
        "transaction": transaction,
        "nav": nav,
        "trade_shares": round(trade_shares, 4),
    }


@app.get("/portfolio/trades/add", dependencies=[Depends(require_token)])
def record_trade(
    symbol: str = Query(..., description="基金代码"),
    action: str = Query(..., pattern="^(buy|sell)$", description="buy=买入，sell=卖出"),
    amount: float = Query(..., gt=0, description="买入或卖出金额，单位：元"),
    nav: Optional[float] = Query(default=None, gt=0, description="成交净值；不传则尝试使用最新净值"),
    name: Optional[str] = Query(default=None, description="基金名称，买入新基金时建议传"),
) -> Dict[str, Any]:
    request = TradeRequest(symbol=symbol, action=action, amount=amount, nav=nav, name=name)
    return record_trade_request(request)


@app.post("/portfolio/trades", dependencies=[Depends(require_token)])
def record_trade_legacy(request: TradeRequest) -> Dict[str, Any]:
    return record_trade_request(request)


@app.get("/portfolio/trades", dependencies=[Depends(require_token)])
def list_trades() -> Dict[str, Any]:
    config = load_config()
    return {"transactions": config.get("transactions", [])}


@app.get("/analysis/run", dependencies=[Depends(require_token)])
def analyze_now(
    send_dingtalk: bool = Query(default=True, description="是否发送钉钉，true/false"),
) -> Dict[str, Any]:
    return run_analysis(send_dingtalk=send_dingtalk)


@app.post("/analysis/run", dependencies=[Depends(require_token)])
def analyze_now_legacy(request: AnalyzeRequest) -> Dict[str, Any]:
    return run_analysis(send_dingtalk=request.send_dingtalk)

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from stock_advisor.models import MarketSnapshot


class MarketDataAgent:
    """Collects normalized market snapshots for each symbol."""

    def __init__(self, config: dict):
        self.config = config

    def run(self, symbols: Iterable[str]) -> Dict[str, MarketSnapshot]:
        provider = self.config.get("provider", "sample")
        if provider == "sample":
            return self._run_sample(symbols)
        if provider == "akshare":
            return self._run_akshare(symbols)
        raise ValueError(f"Unsupported market data provider for MVP: {provider}")

    def _run_sample(self, symbols: Iterable[str]) -> Dict[str, MarketSnapshot]:
        sample_prices = self.config.get("sample_prices", {})
        snapshots: Dict[str, MarketSnapshot] = {}
        for symbol in symbols:
            raw = sample_prices.get(symbol)
            if not raw:
                continue
            snapshots[symbol] = MarketSnapshot(
                symbol=symbol,
                price=float(raw["price"]),
                previous_close=float(raw.get("previous_close", raw["price"])),
                volume_vs_20d=float(raw.get("volume_vs_20d", 1)),
                rsi=raw.get("rsi"),
                pe=raw.get("pe"),
            )
        return snapshots

    def _run_akshare(self, symbols: Iterable[str]) -> Dict[str, MarketSnapshot]:
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError(
                "AKShare is required for market_data.provider='akshare'. "
                "Install dependencies with: pip install -r requirements.txt"
            ) from exc

        spot_rows = {}
        if self.config.get("use_realtime_spot", False):
            spot_rows = self._load_akshare_spot_rows(ak)

        snapshots: Dict[str, MarketSnapshot] = {}
        for symbol in symbols:
            code = self._to_akshare_code(symbol)
            spot = spot_rows.get(code, {})
            try:
                hist = self._load_akshare_history(ak, code)
            except Exception:
                continue

            price = self._read_float(spot, ["最新价", "最新", "现价"])
            previous_close = self._previous_close(price, spot, hist)
            volume_vs_20d = self._volume_vs_20d(spot, hist)
            rsi = self._rsi_from_history(hist)
            pe = self._read_float(
                spot,
                ["市盈率-动态", "市盈率", "市盈率TTM", "动态市盈率"],
            )

            if price is None:
                price = self._last_float(hist, ["收盘", "close"])
            if previous_close is None:
                previous_close = self._previous_close_from_history(hist)
            if price is None or previous_close is None:
                continue

            snapshots[symbol] = MarketSnapshot(
                symbol=symbol,
                price=price,
                previous_close=previous_close,
                volume_vs_20d=volume_vs_20d or 1,
                rsi=rsi,
                pe=pe,
            )
        return snapshots

    def _load_akshare_spot_rows(self, ak) -> Dict[str, dict]:
        try:
            frame = ak.stock_zh_a_spot_em()
        except Exception:
            return {}
        rows = {}
        for _, row in frame.iterrows():
            data = row.to_dict()
            code = str(data.get("代码", "")).zfill(6)
            if code:
                rows[code] = data
        return rows

    def _load_akshare_history(self, ak, code: str) -> List[dict]:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        frame = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
        return [row.to_dict() for _, row in frame.iterrows()]

    def _previous_close(
        self,
        price: Optional[float],
        spot: dict,
        hist: List[dict],
    ) -> Optional[float]:
        pct = self._read_float(spot, ["涨跌幅"])
        if price is not None and pct is not None and pct != -100:
            return price / (1 + pct / 100)

        closes = self._series(hist, ["收盘", "close"])
        if len(closes) >= 2:
            return closes[-2]
        return self._read_float(spot, ["昨收", "昨收价"])

    def _previous_close_from_history(self, hist: List[dict]) -> Optional[float]:
        closes = self._series(hist, ["收盘", "close"])
        if len(closes) >= 2:
            return closes[-2]
        return None

    def _volume_vs_20d(self, spot: dict, hist: List[dict]) -> Optional[float]:
        current_volume = self._read_float(spot, ["成交量"])
        volumes = self._series(hist, ["成交量", "volume"])
        if current_volume is None and volumes:
            current_volume = volumes[-1]
        lookback = volumes[-21:-1] if len(volumes) > 20 else volumes[:-1]
        if current_volume is None or not lookback:
            return None
        average = sum(lookback) / len(lookback)
        return current_volume / average if average else None

    def _rsi_from_history(self, hist: List[dict], period: int = 14) -> Optional[float]:
        closes = self._series(hist, ["收盘", "close"])
        if len(closes) <= period:
            return None

        gains = []
        losses = []
        for previous, current in zip(closes[-period - 1 : -1], closes[-period:]):
            change = current - previous
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))

        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_loss == 0:
            return 100.0
        rs = average_gain / average_loss
        return 100 - (100 / (1 + rs))

    def _to_akshare_code(self, symbol: str) -> str:
        return symbol.split(".")[0].zfill(6)

    def _read_float(self, row: dict, keys: List[str]) -> Optional[float]:
        for key in keys:
            if key in row:
                value = self._to_float(row[key])
                if value is not None:
                    return value
        return None

    def _last_float(self, rows: List[dict], keys: List[str]) -> Optional[float]:
        if not rows:
            return None
        return self._read_float(rows[-1], keys)

    def _series(self, rows: List[dict], keys: List[str]) -> List[float]:
        values = []
        for row in rows:
            value = self._read_float(row, keys)
            if value is not None:
                values.append(value)
        return values

    def _to_float(self, value) -> Optional[float]:
        try:
            if value is None or value == "-":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

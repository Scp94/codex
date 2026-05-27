from typing import Dict, Iterable, List, Tuple

from stock_advisor.models import Position


class UniverseAgent:
    """Builds the symbol universe the other agents should evaluate."""

    def __init__(self, config: dict):
        self.config = config

    def run(self, positions: Iterable[Position]) -> List[str]:
        held_symbols = {position.symbol.upper() for position in positions}
        watchlist = {self._parse_item(item)[0] for item in self.config.get("watchlist", [])}
        universe = {self._parse_item(item)[0] for item in self.config.get("universe", [])}
        return sorted(held_symbols | watchlist | universe)

    def symbol_names(self) -> Dict[str, str]:
        names: Dict[str, str] = {}
        for item in self.config.get("watchlist", []) + self.config.get("universe", []):
            symbol, name = self._parse_item(item)
            if name:
                names[symbol] = name
        return names

    def _parse_item(self, item) -> Tuple[str, str]:
        if isinstance(item, str):
            return item.upper(), ""
        symbol = item.get("symbol") or item.get("code")
        if not symbol:
            raise ValueError(f"Universe item is missing symbol/code: {item}")
        return symbol.upper(), item.get("name", "")

from typing import Dict, Iterable, List

from stock_advisor.models import NewsEvent


class NewsAgent:
    """Collects and normalizes news, filing, and event signals."""

    def __init__(self, config: dict):
        self.config = config

    def run(self, symbols: Iterable[str]) -> Dict[str, List[NewsEvent]]:
        provider = self.config.get("provider", "sample")
        if provider != "sample":
            raise ValueError(f"Unsupported news provider for MVP: {provider}")

        sample_events = self.config.get("sample_events", {})
        events: Dict[str, List[NewsEvent]] = {}
        for symbol in symbols:
            events[symbol] = [
                NewsEvent(
                    symbol=symbol,
                    title=event["title"],
                    sentiment=event.get("sentiment", "neutral"),
                    impact=int(event.get("impact", 0)),
                    source_url=event.get("source_url"),
                )
                for event in sample_events.get(symbol, [])
            ]
        return events

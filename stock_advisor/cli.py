import argparse
import json
from pathlib import Path
from typing import List

from .models import Position
from .notifiers import DingTalkNotifier
from .orchestrator import DailyResearchOrchestrator


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_positions(raw_positions: List[dict]) -> List[Position]:
    return [
        Position(
            symbol=item["symbol"].upper(),
            shares=float(item["shares"]),
            cost_basis=float(item["cost_basis"]),
        )
        for item in raw_positions
    ]


def run(config_path: Path, output_dir: Path, send_dingtalk: bool = False) -> Path:
    config = load_config(config_path)
    positions = parse_positions(config["portfolio"].get("positions", []))
    report_path = DailyResearchOrchestrator(config).run(positions, output_dir)
    dingtalk_config = config.get("notifications", {}).get("dingtalk", {})
    if send_dingtalk:
        dingtalk_config = {**dingtalk_config, "enabled": True}
    DingTalkNotifier(dingtalk_config).send_report(report_path)
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local stock research report.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("stock_advisor/config.example.json"),
        help="Path to config JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("stock_advisor/reports"),
        help="Directory for generated reports.",
    )
    parser.add_argument(
        "--send-dingtalk",
        action="store_true",
        help="Send the generated report to the DingTalk robot configured in JSON/env.",
    )
    args = parser.parse_args()

    report_path = run(args.config, args.output_dir, args.send_dingtalk)
    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    main()

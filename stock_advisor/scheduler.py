import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def next_run_at(now: datetime, run_time: str) -> datetime:
    hour, minute = [int(part) for part in run_time.split(":", 1)]
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def run_once(config_path: Path, output_dir: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "stock_advisor.cli",
        "--config",
        str(config_path),
        "--output-dir",
        str(output_dir),
        "--send-dingtalk",
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the stock advisor on a daily schedule.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--time", default="09:30", help="Daily run time in HH:MM, Asia/Shanghai.")
    args = parser.parse_args()

    timezone = ZoneInfo("Asia/Shanghai")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    while True:
        now = datetime.now(timezone)
        scheduled_at = next_run_at(now, args.time)
        sleep_seconds = max(1, int((scheduled_at - now).total_seconds()))
        print(f"Next stock advisor run: {scheduled_at.isoformat()}", flush=True)
        time.sleep(sleep_seconds)

        try:
            print(f"Starting stock advisor run: {datetime.now(timezone).isoformat()}", flush=True)
            run_once(args.config, args.output_dir)
            print(f"Finished stock advisor run: {datetime.now(timezone).isoformat()}", flush=True)
        except Exception as exc:
            print(f"Stock advisor run failed: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

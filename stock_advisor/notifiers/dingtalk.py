import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


class DingTalkNotifier:
    """Sends the generated Markdown report to a DingTalk custom robot."""

    def __init__(self, config: dict):
        self.config = config

    def is_enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    def send_report(self, report_path: Path) -> None:
        if not self.is_enabled():
            return

        webhook = self._get_secret_value("webhook", "webhook_env")
        secret = self._get_secret_value("secret", "secret_env", required=False)
        if not webhook:
            raise ValueError("DingTalk notification is enabled but webhook is missing.")
        if self.config.get("require_signing", True) and not secret:
            raise ValueError("DingTalk notification requires signing but secret is missing.")

        markdown = self._format_for_dingtalk(report_path.read_text(encoding="utf-8"))
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "每日股票投研简报",
                "text": markdown,
            },
        }

        url = self._sign_webhook(webhook, secret) if secret else webhook
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
        result = json.loads(body)
        if result.get("errcode") != 0:
            raise RuntimeError(f"DingTalk robot returned an error: {body}")

    def _format_for_dingtalk(self, markdown: str) -> str:
        lines = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("|"):
                continue
            lines.append(line.rstrip())
        text = "\n".join(lines).strip()

        # DingTalk documents recommend adding spaces around newlines for stable line breaks.
        text = text.replace("\n", "  \n")
        max_length = int(self.config.get("max_markdown_chars", 4800))
        if len(text) > max_length:
            text = text[: max_length - 24].rstrip() + "  \n\n> 内容过长，已截断。"
        return text

    def _get_secret_value(
        self,
        plain_key: str,
        env_key: str,
        required: bool = True,
    ) -> Optional[str]:
        env_name = self.config.get(env_key)
        if env_name and os.environ.get(env_name):
            return os.environ[env_name]
        value = self.config.get(plain_key)
        if required and not value:
            return None
        return value

    def _sign_webhook(self, webhook: str, secret: str) -> str:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(digest))
        separator = "&" if "?" in webhook else "?"
        return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"

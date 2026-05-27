from pathlib import Path
import unittest

from stock_advisor.notifiers.dingtalk import DingTalkNotifier


class DingTalkNotifierTests(unittest.TestCase):
    def test_sign_webhook_adds_timestamp_and_signature(self):
        notifier = DingTalkNotifier({"enabled": True, "require_signing": True})

        signed = notifier._sign_webhook(
            "https://oapi.dingtalk.com/robot/send?access_token=token",
            "SECexample",
        )

        self.assertIn("timestamp=", signed)
        self.assertIn("sign=", signed)
        self.assertIn("access_token=token", signed)

    def test_missing_secret_fails_when_signing_is_required(self):
        notifier = DingTalkNotifier(
            {
                "enabled": True,
                "require_signing": True,
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=token",
            }
        )

        with self.assertRaises(ValueError):
            notifier.send_report(Path(__file__))

    def test_format_for_dingtalk_removes_tables_and_keeps_headings(self):
        notifier = DingTalkNotifier({"enabled": True})

        formatted = notifier._format_for_dingtalk(
            "# 标题\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- item"
        )

        self.assertIn("# 标题", formatted)
        self.assertIn("- item", formatted)
        self.assertNotIn("| A | B |", formatted)


if __name__ == "__main__":
    unittest.main()

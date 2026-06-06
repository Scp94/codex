import html
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"


def _render_template(name: str, values: dict[str, str]) -> str:
    page = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        page = page.replace("{{ " + key + " }}", value)
    return page


def render_login_page(error: bool = False) -> str:
    error_html = "<p class='error'>登录失败，请检查访问令牌。</p>" if error else ""
    return _render_template("login.html", {"error": error_html})


def render_admin_page(token: str) -> str:
    return _render_template(
        "admin.html",
        {
            "token_json": html.escape(json.dumps(token), quote=False),
        },
    )

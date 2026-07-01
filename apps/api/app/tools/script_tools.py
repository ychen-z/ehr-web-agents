"""Script/Python 工具注册表。

与 llm_tools 不同：脚本工具可以执行任意 Python 逻辑，比如调用 LLM 生成内容、
执行 subprocess 等。最终返回的字典会作为结构化输出展示。
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess
from typing import Any, Callable

from app.models.adapters import ChatModelAdapter
from app.tools.llm_tools import invoke_llm_tool

logger = logging.getLogger(__name__)

MAX_SECTIONS = 20
MAX_ITEMS_PER_SECTION = 30
MAX_TEXT_LEN = 2000
MAX_HTML_BYTES = 256 * 1024  # 256 KiB
DEFAULT_SUBPROCESS_TIMEOUT = 30
_RUN_ID_RE = re.compile(r"^[a-f0-9\-]{8,64}$")

ScriptToolFn = Callable[..., dict[str, Any]]
SCRIPT_TOOLS: dict[str, ScriptToolFn] = {}


def register(name: str) -> Callable[[ScriptToolFn], ScriptToolFn]:
    def decorator(fn: ScriptToolFn) -> ScriptToolFn:
        SCRIPT_TOOLS[name] = fn
        return fn

    return decorator


def is_script_tool(tool_name: str) -> bool:
    return tool_name in SCRIPT_TOOLS


def invoke_script_tool(
    tool_name: str,
    user_message: str,
    adapter: ChatModelAdapter,
    run_id: str,
) -> dict[str, Any]:
    fn = SCRIPT_TOOLS[tool_name]
    return fn(user_message=user_message, adapter=adapter, run_id=run_id)


def get_available_script_tools() -> list[str]:
    return list(SCRIPT_TOOLS.keys())


def run_subprocess(
    cmd: list[str],
    *,
    cwd: str | None = None,
    timeout: int = DEFAULT_SUBPROCESS_TIMEOUT,
    input_text: str | None = None,
) -> dict[str, Any]:
    """通用 subprocess 包装，供 script tool 复用。

    强制传 list（禁用 shell=True）；带默认超时；捕获 stdout/stderr。
    仅供受信 tool 代码调用——**绝不能**把用户输入拼进 cmd。
    """
    if not isinstance(cmd, list) or not cmd:
        raise ValueError("cmd must be a non-empty list; shell strings are not allowed")

    logger.info("run_subprocess: %s", shlex.join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "returncode": -1,
            "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
            "stderr": f"timeout after {timeout}s",
            "timed_out": True,
        }

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "timed_out": False,
    }


@register("generate_html")
def generate_html(
    user_message: str,
    adapter: ChatModelAdapter,
    run_id: str,
) -> dict[str, Any]:
    """LLM 提取页面规格 → Python 模板渲染 HTML → 返回 HTML 内容（前端 srcDoc 内嵌预览）。"""
    if not _RUN_ID_RE.match(run_id):
        raise ValueError(f"invalid run_id format: {run_id!r}")

    spec = invoke_llm_tool("generate_html", user_message, adapter)
    spec = _sanitize_spec(spec)

    html_code = _render_html_from_spec(spec)
    size_bytes = len(html_code.encode("utf-8"))
    if size_bytes > MAX_HTML_BYTES:
        raise RuntimeError(f"generated HTML exceeds {MAX_HTML_BYTES} bytes")

    logger.info("Rendered HTML artifact run_id=%s size=%d", run_id, size_bytes)

    return {
        "title": spec.get("title"),
        "description": spec.get("description"),
        "theme": spec.get("theme"),
        "primary_color": spec.get("primary_color"),
        "sections": spec.get("sections", []),
        "html": html_code,
        "size_bytes": size_bytes,
    }


def _sanitize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """对 LLM 输出做容量裁剪，防止资源耗尽。"""
    sections = spec.get("sections") or []
    if not isinstance(sections, list):
        sections = []
    sections = sections[:MAX_SECTIONS]

    cleaned_sections = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        items = s.get("items") or []
        if not isinstance(items, list):
            items = []
        items = [str(i)[:MAX_TEXT_LEN] for i in items[:MAX_ITEMS_PER_SECTION]]
        cleaned_sections.append({
            "type": str(s.get("type", "hero"))[:32],
            "heading": str(s.get("heading", ""))[:MAX_TEXT_LEN],
            "body": str(s.get("body", ""))[:MAX_TEXT_LEN],
            "items": items,
        })

    primary = str(spec.get("primary_color") or "#2563eb")
    if not re.match(r"^#[0-9a-fA-F]{3,8}$", primary):
        primary = "#2563eb"

    theme = spec.get("theme")
    if theme not in ("light", "dark"):
        theme = "light"

    return {
        "title": str(spec.get("title") or "Generated Page")[:200],
        "description": str(spec.get("description") or "")[:MAX_TEXT_LEN],
        "theme": theme,
        "primary_color": primary,
        "sections": cleaned_sections,
    }


def _escape(text: Any) -> str:
    """HTML 转义，防止规格里的特殊字符破坏页面。"""
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_section(section: dict[str, Any], primary: str) -> str:
    stype = section.get("type", "hero")
    heading = _escape(section.get("heading", ""))
    body = _escape(section.get("body", ""))
    items = section.get("items") or []

    if stype == "hero":
        return (
            f'<section class="hero" style="background:linear-gradient(135deg,{primary},#0f172a);">'
            f"<h1>{heading}</h1><p>{body}</p></section>"
        )
    if stype == "features":
        cards = "".join(f'<div class="card"><p>{_escape(it)}</p></div>' for it in items)
        return (
            f'<section class="features"><h2>{heading}</h2>'
            f'<p class="lede">{body}</p>'
            f'<div class="grid">{cards}</div></section>'
        )
    if stype == "cta":
        return (
            f'<section class="cta" style="border-color:{primary};">'
            f"<h2>{heading}</h2><p>{body}</p>"
            f'<a class="btn" style="background:{primary};" href="#">Get Started</a></section>'
        )
    if stype == "footer":
        return f'<footer><h3>{heading}</h3><p>{body}</p></footer>'
    return f"<section><h2>{heading}</h2><p>{body}</p></section>"


def _render_html_from_spec(spec: dict[str, Any]) -> str:
    title = _escape(spec.get("title") or "Generated Page")
    description = _escape(spec.get("description") or "")
    theme = spec.get("theme") or "light"
    primary = spec.get("primary_color") or "#2563eb"
    sections = spec.get("sections") or []

    bg = "#0b1220" if theme == "dark" else "#ffffff"
    fg = "#e2e8f0" if theme == "dark" else "#0f172a"
    muted = "#94a3b8" if theme == "dark" else "#475569"
    surface = "#111827" if theme == "dark" else "#f8fafc"

    body_html = "\n".join(_render_section(s, primary) for s in sections)

    return f"""<!doctype html>
<html lang="en" data-theme="{theme}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<meta name="description" content="{description}" />
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:{bg}; color:{fg}; line-height:1.6; }}
  section, footer {{ padding:64px 32px; max-width:1100px; margin:0 auto; }}
  .hero {{ color:#fff; max-width:none; text-align:center; padding:96px 32px; }}
  .hero h1 {{ font-size:2.75rem; margin:0 0 16px; }}
  .hero p {{ font-size:1.15rem; opacity:0.9; max-width:680px; margin:0 auto; }}
  .features .lede {{ color:{muted}; max-width:720px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; margin-top:24px; }}
  .card {{ background:{surface}; padding:20px; border-radius:12px; }}
  .cta {{ border:2px solid; border-radius:16px; padding:48px; text-align:center; }}
  .btn {{ display:inline-block; color:#fff; padding:12px 28px; border-radius:8px; text-decoration:none; margin-top:16px; font-weight:600; }}
  footer {{ border-top:1px solid {surface}; color:{muted}; text-align:center; }}
  h2 {{ font-size:1.75rem; margin:0 0 12px; }}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""

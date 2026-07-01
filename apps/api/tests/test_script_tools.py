"""Tests for script_tools module: sanitization, rendering, escape, path defense."""

import json
import uuid

import pytest

from app.tools.script_tools import (
    MAX_HTML_BYTES,
    MAX_ITEMS_PER_SECTION,
    MAX_SECTIONS,
    MAX_TEXT_LEN,
    SCRIPT_TOOLS,
    _escape,
    _render_html_from_spec,
    _sanitize_spec,
    generate_html,
    get_available_script_tools,
    is_script_tool,
    run_subprocess,
)


class FakeAdapter:
    def __init__(self, payload: dict):
        self._payload = payload

        class _Usage:
            prompt_tokens = 10
            completion_tokens = 5
            total_tokens = 15
            model_name = "fake"

        self.last_usage = _Usage()

    def invoke(self, messages, **kwargs):
        return json.dumps(self._payload)


def test_registry_has_generate_html():
    assert is_script_tool("generate_html")
    assert "generate_html" in get_available_script_tools()
    assert SCRIPT_TOOLS["generate_html"] is generate_html


def test_is_script_tool_false_for_unknown():
    assert not is_script_tool("nonexistent_tool")
    assert not is_script_tool("generate_jd")  # generate_jd 是 LLM 工具


def test_escape_html_special_chars():
    assert _escape("<script>") == "&lt;script&gt;"
    assert _escape('a & b "c"') == "a &amp; b &quot;c&quot;"
    assert _escape(None) == ""
    assert _escape(123) == "123"


def test_sanitize_spec_caps_sections():
    spec = {
        "title": "T",
        "sections": [{"type": "hero", "heading": f"h{i}", "body": "b", "items": []} for i in range(MAX_SECTIONS + 5)],
    }
    cleaned = _sanitize_spec(spec)
    assert len(cleaned["sections"]) == MAX_SECTIONS


def test_sanitize_spec_caps_text_length():
    long_text = "x" * (MAX_TEXT_LEN + 500)
    spec = {
        "title": long_text,
        "description": long_text,
        "sections": [
            {"type": "hero", "heading": long_text, "body": long_text, "items": [long_text]},
        ],
    }
    cleaned = _sanitize_spec(spec)
    assert len(cleaned["title"]) == 200  # title cap is 200
    assert len(cleaned["description"]) == MAX_TEXT_LEN
    assert len(cleaned["sections"][0]["heading"]) == MAX_TEXT_LEN
    assert len(cleaned["sections"][0]["items"][0]) == MAX_TEXT_LEN


def test_sanitize_spec_caps_items_per_section():
    spec = {
        "title": "T",
        "sections": [
            {"type": "features", "heading": "h", "body": "b", "items": [f"i{i}" for i in range(MAX_ITEMS_PER_SECTION + 10)]},
        ],
    }
    cleaned = _sanitize_spec(spec)
    assert len(cleaned["sections"][0]["items"]) == MAX_ITEMS_PER_SECTION


def test_sanitize_spec_rejects_invalid_theme():
    cleaned = _sanitize_spec({"title": "T", "theme": "neon", "sections": []})
    assert cleaned["theme"] == "light"


def test_sanitize_spec_accepts_valid_themes():
    assert _sanitize_spec({"title": "T", "theme": "dark", "sections": []})["theme"] == "dark"
    assert _sanitize_spec({"title": "T", "theme": "light", "sections": []})["theme"] == "light"


def test_sanitize_spec_rejects_non_hex_primary_color():
    cleaned = _sanitize_spec({"title": "T", "primary_color": "javascript:alert(1)", "sections": []})
    assert cleaned["primary_color"] == "#2563eb"


def test_sanitize_spec_accepts_valid_hex_color():
    cleaned = _sanitize_spec({"title": "T", "primary_color": "#a3b2c1", "sections": []})
    assert cleaned["primary_color"] == "#a3b2c1"


def test_sanitize_spec_handles_non_list_sections():
    cleaned = _sanitize_spec({"title": "T", "sections": "not a list"})
    assert cleaned["sections"] == []


def test_sanitize_spec_skips_non_dict_section_entries():
    cleaned = _sanitize_spec({"title": "T", "sections": ["str", 123, None, {"type": "hero", "heading": "h"}]})
    assert len(cleaned["sections"]) == 1
    assert cleaned["sections"][0]["heading"] == "h"


def test_render_includes_title_and_primary():
    spec = {
        "title": "My Page",
        "description": "desc",
        "theme": "dark",
        "primary_color": "#7c3aed",
        "sections": [{"type": "hero", "heading": "Hi", "body": "Body", "items": []}],
    }
    html = _render_html_from_spec(spec)
    assert "<title>My Page</title>" in html
    assert "#7c3aed" in html
    assert "Hi" in html
    assert "Body" in html


def test_render_dark_theme_has_dark_bg():
    spec = {"title": "T", "theme": "dark", "primary_color": "#000", "sections": []}
    html = _render_html_from_spec(spec)
    assert "#0b1220" in html  # dark bg


def test_render_escapes_xss_in_content():
    spec = {
        "title": "<script>alert('xss')</script>",
        "description": '" onerror="alert(1)',
        "theme": "light",
        "primary_color": "#000",
        "sections": [
            {"type": "hero", "heading": "<img src=x>", "body": "&copy;", "items": []},
            {"type": "features", "heading": "f", "body": "b", "items": ["<a href=javascript:alert(1)>x</a>"]},
        ],
    }
    html = _render_html_from_spec(spec)
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert "<img src=x>" not in html
    assert "&lt;img src=x&gt;" in html
    assert "javascript:alert" not in html or "&lt;a href=javascript:alert" in html
    # 描述被 meta content 包，需 quote 转义
    assert '" onerror="alert' not in html


def test_render_all_section_types():
    spec = {
        "title": "T",
        "theme": "light",
        "primary_color": "#000",
        "sections": [
            {"type": "hero", "heading": "H", "body": "B", "items": []},
            {"type": "features", "heading": "F", "body": "B", "items": ["a", "b", "c"]},
            {"type": "cta", "heading": "C", "body": "B", "items": []},
            {"type": "footer", "heading": "Foot", "body": "B", "items": []},
        ],
    }
    html = _render_html_from_spec(spec)
    assert 'class="hero"' in html
    assert 'class="features"' in html
    assert 'class="cta"' in html
    assert html.count('<div class="card">') == 3
    assert "<footer>" in html


def test_render_unknown_section_type_falls_back():
    spec = {
        "title": "T",
        "theme": "light",
        "primary_color": "#000",
        "sections": [{"type": "alien", "heading": "X", "body": "Y", "items": []}],
    }
    html = _render_html_from_spec(spec)
    assert "<h2>X</h2>" in html
    assert "<p>Y</p>" in html


# ---------- generate_html (full flow) ----------

VALID_SPEC = {
    "title": "Launch",
    "description": "A landing page",
    "theme": "dark",
    "primary_color": "#7c3aed",
    "sections": [
        {"type": "hero", "heading": "Hello", "body": "World"},
    ],
}


def test_generate_html_full_flow_returns_html_and_metadata():
    run_id = str(uuid.uuid4())
    result = generate_html(
        user_message="Build a landing page",
        adapter=FakeAdapter(VALID_SPEC),
        run_id=run_id,
    )
    assert result["title"] == "Launch"
    assert result["theme"] == "dark"
    assert result["primary_color"] == "#7c3aed"
    assert "<title>Launch</title>" in result["html"]
    assert result["size_bytes"] == len(result["html"].encode("utf-8"))
    # 旧字段已移除
    assert "preview_url" not in result
    assert "artifact_path" not in result


def test_generate_html_rejects_invalid_run_id():
    with pytest.raises(ValueError, match="invalid run_id"):
        generate_html(
            user_message="x",
            adapter=FakeAdapter(VALID_SPEC),
            run_id="../etc/passwd",
        )


def test_generate_html_rejects_path_traversal_run_id():
    with pytest.raises(ValueError):
        generate_html(
            user_message="x",
            adapter=FakeAdapter(VALID_SPEC),
            run_id="../../../tmp/evil",
        )


def test_generate_html_rejects_too_short_run_id():
    with pytest.raises(ValueError):
        generate_html(user_message="x", adapter=FakeAdapter(VALID_SPEC), run_id="abc")


def test_generate_html_raises_when_html_too_large(monkeypatch):
    """HTML 体积超限时报错。"""
    huge_spec = {
        "title": "T",
        "theme": "light",
        "primary_color": "#000",
        "sections": [
            {"type": "features", "heading": "x" * 1000, "body": "y" * 1000, "items": ["z" * 1000] * 30}
        ] * 1,
    }
    # 直接调用 render 通常不会超 256 KiB，所以 monkeypatch 一个超大模板
    from app.tools import script_tools

    def fake_render(spec):
        return "x" * (MAX_HTML_BYTES + 1)

    monkeypatch.setattr(script_tools, "_render_html_from_spec", fake_render)

    with pytest.raises(RuntimeError, match="exceeds"):
        generate_html(
            user_message="x",
            adapter=FakeAdapter(huge_spec),
            run_id=str(uuid.uuid4()),
        )


# ---------- run_subprocess ----------

def test_run_subprocess_returns_stdout():
    result = run_subprocess(["echo", "hello"])
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]
    assert result["timed_out"] is False


def test_run_subprocess_captures_stderr_and_returncode():
    result = run_subprocess(["python", "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])
    assert result["returncode"] == 3
    assert "boom" in result["stderr"]


def test_run_subprocess_rejects_string_cmd():
    with pytest.raises(ValueError, match="non-empty list"):
        run_subprocess("echo hello")  # type: ignore[arg-type]


def test_run_subprocess_rejects_empty_list():
    with pytest.raises(ValueError):
        run_subprocess([])


def test_run_subprocess_times_out():
    result = run_subprocess(["python", "-c", "import time; time.sleep(5)"], timeout=1)
    assert result["timed_out"] is True
    assert result["returncode"] == -1
    assert "timeout" in result["stderr"]

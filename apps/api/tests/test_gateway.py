"""Tests for MCP tool gateway: registry + whitelist."""

import pytest

from app.gateway import ToolRegistry, ToolSpec, get_registry


def test_register_and_exists():
    r = ToolRegistry()
    r.register(ToolSpec(name="my_tool", description="Does stuff"))
    assert r.exists("my_tool")
    assert not r.exists("other_tool")


def test_register_rejects_empty_name():
    r = ToolRegistry()
    with pytest.raises(ValueError, match="名称不能为空"):
        r.register(ToolSpec(name="", description="x"))


def test_register_rejects_empty_description():
    r = ToolRegistry()
    with pytest.raises(ValueError, match="description 不能为空"):
        r.register(ToolSpec(name="t", description=""))


def test_disabled_tool_not_allowed():
    r = ToolRegistry()
    r.register(ToolSpec(name="disabled_tool", description="x", enabled=False))
    assert not r.is_allowed("disabled_tool")
    assert r.get("disabled_tool") is not None  # exists but disabled


def test_unregister():
    r = ToolRegistry()
    r.register(ToolSpec(name="tmp", description="x"))
    assert r.exists("tmp")
    r.unregister("tmp")
    assert not r.exists("tmp")


def test_list_enabled_filters():
    r = ToolRegistry()
    r.register(ToolSpec(name="a", description="x", enabled=True))
    r.register(ToolSpec(name="b", description="x", enabled=False))
    r.register(ToolSpec(name="c", description="x", enabled=True))
    enabled = r.list_enabled()
    names = {t.name for t in enabled}
    assert names == {"a", "c"}


def test_validate_skill_binding_passes():
    r = ToolRegistry()
    r.register(ToolSpec(name="good_tool", description="x"))
    r.validate_skill_binding("good_tool")  # 不抛异常


def test_validate_skill_binding_fails_missing():
    r = ToolRegistry()
    r.register(ToolSpec(name="other", description="x"))
    with pytest.raises(ValueError, match="未在注册表中"):
        r.validate_skill_binding("missing_tool")


def test_validate_skill_binding_fails_empty():
    r = ToolRegistry()
    with pytest.raises(ValueError, match="必须绑定"):
        r.validate_skill_binding("")


def test_global_registry_has_builtin_tools():
    """全局注册表在模块加载时自动注册内置工具。"""
    registry = get_registry()
    assert registry.is_allowed("generate_jd")
    assert registry.is_allowed("screen_resume")
    assert registry.is_allowed("generate_html")
    assert registry.is_allowed("generate_interview_questions")
    assert registry.is_allowed("summarize_interview_feedback")


def test_global_registry_tool_has_description():
    registry = get_registry()
    spec = registry.get("generate_jd")
    assert spec is not None
    assert len(spec.description) > 10


def test_global_registry_rejects_unknown():
    registry = get_registry()
    assert not registry.is_allowed("totally_fake_tool")

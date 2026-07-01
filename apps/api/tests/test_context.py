"""Tests for context service: history injection, prompt_template, token budget."""

from app.context import (
    build_context_messages,
    estimate_tokens,
    resolve_system_prompt,
)


def test_estimate_tokens_basic():
    assert estimate_tokens("hello") >= 1
    assert estimate_tokens("a" * 300) == 100  # 300 / 3


def test_build_context_no_history():
    msgs = build_context_messages(
        system_prompt="You are a bot.",
        user_message="Hi",
        history_messages=None,
    )
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"


def test_build_context_with_history():
    history = [
        {"role": "user", "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
    ]
    msgs = build_context_messages(
        system_prompt="sys",
        user_message="new question",
        history_messages=history,
        token_budget=4000,
    )
    assert len(msgs) == 4  # system + 2 history + user
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    assert msgs[3]["content"] == "new question"


def test_build_context_truncates_history_by_budget():
    # 每条消息 100 字符 ≈ 33 token。预算只够 1 条历史。
    history = [
        {"role": "user", "content": "x" * 100},
        {"role": "assistant", "content": "y" * 100},
        {"role": "user", "content": "z" * 100},
    ]
    msgs = build_context_messages(
        system_prompt="s" * 30,
        user_message="u" * 30,
        history_messages=history,
        token_budget=120,  # 很紧的预算
    )
    # system + user 至少消耗 (30/3 + 30/3 + 50) = 70 token
    # 剩余 50 token 只够 1 条历史 (100/3 ≈ 33)
    assert len(msgs) <= 4
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"


def test_build_context_keeps_latest_messages():
    history = [
        {"role": "user", "content": f"msg-{i}"} for i in range(30)
    ]
    msgs = build_context_messages(
        system_prompt="sys",
        user_message="latest",
        history_messages=history,
        token_budget=4000,
    )
    # 最多取 MAX_HISTORY_MESSAGES=20 条
    history_in_msgs = [m for m in msgs if m["role"] != "system" and m["content"] != "latest"]
    assert len(history_in_msgs) <= 20
    # 保留最新的
    if history_in_msgs:
        assert "msg-29" in history_in_msgs[-1]["content"]


def test_resolve_system_prompt_uses_template():
    result = resolve_system_prompt(
        skill_name="JD生成",
        tool_name="generate_jd",
        tool_output={"title": "Dev"},
        prompt_template="你是{skill_name}助手。工具{tool_name}输出：{tool_output}",
    )
    assert "JD生成" in result
    assert "generate_jd" in result
    assert '"title": "Dev"' in result


def test_resolve_system_prompt_fallback_when_no_template():
    result = resolve_system_prompt(
        skill_name="简历筛选",
        tool_name="screen_resume",
        tool_output={"score": "A"},
        prompt_template=None,
    )
    assert "简历筛选" in result
    assert "screen_resume" in result
    assert "工具输出" in result


def test_resolve_system_prompt_fallback_on_bad_template():
    result = resolve_system_prompt(
        skill_name="Test",
        tool_name="t",
        tool_output={},
        prompt_template="Bad template {nonexistent_var}",
    )
    # fallback 到默认
    assert "Test" in result
    assert "工具输出" in result

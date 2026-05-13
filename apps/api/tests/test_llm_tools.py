import json

import pytest

from app.tools.llm_tools import (
    TOOL_SCHEMAS,
    ToolExecutionError,
    _build_tool_prompt,
    get_available_tools,
    get_tool_schema,
    invoke_llm_tool,
)


def test_get_available_tools_returns_four():
    tools = get_available_tools()
    assert set(tools) == {"generate_jd", "screen_resume", "generate_interview_questions", "summarize_interview_feedback"}


def test_get_tool_schema_returns_schema():
    schema = get_tool_schema("generate_jd")
    assert schema is not None
    assert "output_fields" in schema
    assert "job_title" in schema["output_fields"]


def test_get_tool_schema_returns_none_for_unknown():
    assert get_tool_schema("nonexistent") is None


def test_build_tool_prompt_includes_fields():
    prompt = _build_tool_prompt("generate_jd", "Senior Python developer")
    assert "job_title" in prompt
    assert "responsibilities" in prompt
    assert "Senior Python developer" in prompt


def test_build_tool_prompt_raises_for_unknown_tool():
    with pytest.raises(ToolExecutionError) as exc_info:
        _build_tool_prompt("nonexistent", "test")
    assert "Unknown tool" in str(exc_info.value)


def test_invoke_llm_tool_parses_valid_json():
    jd_output = {
        "job_title": "Senior Python Developer",
        "responsibilities": ["Design APIs", "Code review"],
        "requirements": ["5+ years Python", "FastAPI experience"],
        "interview_focus": ["System design", "Python expertise"],
        "selling_points": ["Remote work", "Competitive salary"],
    }

    class FakeAdapter:
        def invoke(self, messages, **kwargs):
            return json.dumps(jd_output)

    result = invoke_llm_tool("generate_jd", "Senior Python developer", FakeAdapter())
    assert result["job_title"] == "Senior Python Developer"
    assert len(result["responsibilities"]) == 2


def test_invoke_llm_tool_strips_markdown_fences():
    output = {"question_groups": [{"competency": "Technical", "questions": ["Q1", "Q2"]}]}

    class FakeAdapter:
        def invoke(self, messages, **kwargs):
            return f"```json\n{json.dumps(output)}\n```"

    result = invoke_llm_tool("generate_interview_questions", "test", FakeAdapter())
    assert "question_groups" in result


def test_invoke_llm_tool_raises_on_invalid_json():
    class FakeAdapter:
        def invoke(self, messages, **kwargs):
            return "This is not JSON at all"

    with pytest.raises(ToolExecutionError) as exc_info:
        invoke_llm_tool("generate_jd", "test", FakeAdapter())
    assert "无效 JSON" in str(exc_info.value)


def test_invoke_llm_tool_raises_on_non_object():
    class FakeAdapter:
        def invoke(self, messages, **kwargs):
            return '["not", "an", "object"]'

    with pytest.raises(ToolExecutionError) as exc_info:
        invoke_llm_tool("generate_jd", "test", FakeAdapter())
    assert "non-object" in str(exc_info.value)


def test_invoke_llm_tool_warns_on_missing_fields():
    class FakeAdapter:
        def invoke(self, messages, **kwargs):
            return json.dumps({"job_title": "Developer"})

    result = invoke_llm_tool("generate_jd", "test", FakeAdapter())
    assert result["job_title"] == "Developer"


def test_invoke_llm_tool_raises_for_unknown_tool():
    class FakeAdapter:
        def invoke(self, messages, **kwargs):
            return "{}"

    with pytest.raises(ToolExecutionError) as exc_info:
        invoke_llm_tool("nonexistent_tool", "test", FakeAdapter())
    assert "Unknown tool" in str(exc_info.value)

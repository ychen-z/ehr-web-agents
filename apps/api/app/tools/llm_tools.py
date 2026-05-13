"""基于 LLM 的工具执行：用真实的 LLM 结构化输出替代 mock 工具。"""

import json
import logging
import re
from typing import Any

from app.models.adapters import ChatModelAdapter

logger = logging.getLogger(__name__)

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "generate_jd": {
        "description": "Generate a professional job description",
        "output_fields": {
            "job_title": "string - the job title",
            "responsibilities": "list of strings - key job responsibilities",
            "requirements": "list of strings - required qualifications and skills",
            "interview_focus": "list of strings - areas to focus on during interviews",
            "selling_points": "list of strings - reasons candidates should apply",
        },
    },
    "screen_resume": {
        "description": "Screen and evaluate a candidate resume against job requirements",
        "output_fields": {
            "screening_dimensions": 'list of objects with keys: dimension (string), score ("Strong"|"Adequate"|"Moderate"|"Limited"), notes (string)',
            "strengths": "list of strings - candidate strengths",
            "risks": "list of strings - potential risks or concerns",
            "recommended_next_step": "string - recommended next action",
        },
    },
    "generate_interview_questions": {
        "description": "Generate tailored interview questions grouped by competency",
        "output_fields": {
            "question_groups": "list of objects with keys: competency (string), questions (list of strings)",
        },
    },
    "summarize_interview_feedback": {
        "description": "Summarize interview feedback from multiple interviewers",
        "output_fields": {
            "feedback_summary": "string - overall summary of the interview feedback",
            "evidence": "list of strings - key evidence supporting the assessment",
            "concerns": "list of strings - concerns raised during interviews",
            "decision_recommendation": "string - hire/reject/additional evaluation recommendation",
        },
    },
}


class ToolExecutionError(Exception):
    """LLM 工具执行失败时抛出。"""

    def __init__(self, tool_name: str, message: str):
        super().__init__(message)
        self.tool_name = tool_name


def _build_tool_prompt(tool_name: str, user_message: str) -> str:
    schema = TOOL_SCHEMAS.get(tool_name)
    if schema is None:
        raise ToolExecutionError(tool_name, f"Unknown tool: {tool_name}")

    fields_desc = "\n".join(f'  - "{k}": {v}' for k, v in schema["output_fields"].items())

    return (
        f"You are an HR recruitment tool. Your task: {schema['description']}.\n\n"
        f"Based on the user's request below, produce a JSON object with EXACTLY these fields:\n"
        f"{fields_desc}\n\n"
        f"IMPORTANT RULES:\n"
        f"- Output ONLY valid JSON. No markdown, no explanation, no extra text.\n"
        f"- Do NOT wrap the JSON in ```json``` code blocks.\n"
        f"- All string values should be professional and detailed.\n"
        f"- List fields must contain at least 2 items.\n\n"
        f"User request:\n{user_message}"
    )


def invoke_llm_tool(
    tool_name: str,
    user_message: str,
    adapter: ChatModelAdapter,
) -> dict[str, Any]:
    """调用 LLM 为工具生成结构化输出。"""
    prompt = _build_tool_prompt(tool_name, user_message)

    messages = [
        {"role": "system", "content": "You are a structured data generator. Output only valid JSON."},
        {"role": "user", "content": prompt},
    ]

    raw = adapter.invoke(messages)

    # 从 LLM 响应中提取 JSON，支持多种格式：
    # 1. 纯 JSON
    # 2. markdown 代码块包裹的 JSON
    # 3. JSON 前后混有说明文字
    # 4. 推理模型带 <think>...</think> 标签
    cleaned = raw.strip()

    # 去除推理模型的思考标签（如 MiniMax-M1）
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()

    # 去除 markdown 代码块标记
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n") if "\n" in cleaned else 3
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[: -3]
    cleaned = cleaned.strip()

    # 如果清理后仍然不是以 { 开头，尝试从文本中提取 JSON 对象
    if cleaned and not cleaned.startswith("{"):
        # 寻找第一个 { 到最后一个 } 之间的内容
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)

    if not cleaned:
        logger.error("LLM tool %s 返回空内容，原始响应: %s", tool_name, raw[:500])
        raise ToolExecutionError(tool_name, f"LLM 返回了空内容，无法解析为 JSON")

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("LLM tool %s 返回无效 JSON: %s\n原始响应: %s", tool_name, cleaned[:200], raw[:500])
        raise ToolExecutionError(tool_name, f"LLM 返回无效 JSON: {e}") from e

    if not isinstance(result, dict):
        raise ToolExecutionError(tool_name, "LLM returned non-object JSON")

    schema = TOOL_SCHEMAS[tool_name]
    missing = [k for k in schema["output_fields"] if k not in result]
    if missing:
        logger.warning("LLM tool %s missing fields: %s", tool_name, missing)

    return result


def get_available_tools() -> list[str]:
    """返回可用工具名称列表。"""
    return list(TOOL_SCHEMAS.keys())


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """返回指定工具的 schema。"""
    return TOOL_SCHEMAS.get(tool_name)

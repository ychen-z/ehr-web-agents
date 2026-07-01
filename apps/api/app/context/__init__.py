"""Context 服务：会话历史注入 + Token 预算裁剪。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Token 预算：system prompt + history + user message 总共不超过此数
DEFAULT_CONTEXT_TOKEN_BUDGET = 4000
# 会话历史最多取最近 N 条消息
MAX_HISTORY_MESSAGES = 20
# 每条消息估算 token 的简易规则
CHARS_PER_TOKEN = 3  # 中英混合场景保守估算


def estimate_tokens(text: str) -> int:
    """简易 token 估算。生产环境建议换 tiktoken。"""
    return max(1, len(text) // CHARS_PER_TOKEN)


def build_context_messages(
    *,
    system_prompt: str,
    user_message: str,
    history_messages: list[dict] | None = None,
    token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET,
) -> list[dict]:
    """构造送入 LLM 的 messages 列表，按 token 预算裁剪历史。

    返回: [system, ...history(裁剪后), user]
    """
    system_tokens = estimate_tokens(system_prompt)
    user_tokens = estimate_tokens(user_message)
    reserved = system_tokens + user_tokens + 50  # 留 50 token 余量

    remaining_budget = max(0, token_budget - reserved)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    if history_messages:
        # 从最近开始往回取，直到预算用完
        selected: list[dict] = []
        for msg in reversed(history_messages[-MAX_HISTORY_MESSAGES:]):
            msg_tokens = estimate_tokens(msg.get("content", ""))
            if msg_tokens > remaining_budget:
                break
            selected.append(msg)
            remaining_budget -= msg_tokens
        # 恢复正序
        selected.reverse()
        messages.extend(selected)

    messages.append({"role": "user", "content": user_message})
    return messages


def load_conversation_history(db: "Session", conversation_id: str | None) -> list[dict]:
    """从数据库加载会话历史消息。"""
    if not conversation_id:
        return []

    from app.conversations.models import Message

    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in rows]


def resolve_system_prompt(
    *,
    skill_name: str,
    tool_name: str,
    tool_output: dict | None,
    prompt_template: str | None,
) -> str:
    """解析 system prompt：优先用 skill 的 prompt_template，否则走默认。

    prompt_template 支持占位符：
      {skill_name} - 技能名称
      {tool_name} - 工具名称
      {tool_output} - 工具输出 JSON
    """
    import json as _json

    output_str = _json.dumps(tool_output, ensure_ascii=False, indent=2) if tool_output else "{}"

    if prompt_template:
        try:
            return prompt_template.format(
                skill_name=skill_name,
                tool_name=tool_name,
                tool_output=output_str,
            )
        except (KeyError, IndexError):
            # 模板格式错误时 fallback 到默认
            pass

    # 默认 system prompt
    return (
        f"你是一个 HR 招聘助手。"
        f"用户激活了「{skill_name}」技能，调用了「{tool_name}」工具。\n\n"
        f"工具已产出结构化输出（如下）。"
        f"请基于工具输出为 HRBP 用户做总结、解读或扩展。"
        f"不要忽略工具输出或生成无关内容。\n\n"
        f"--- 工具输出 ---\n{output_str}\n--- 结束 ---"
    )

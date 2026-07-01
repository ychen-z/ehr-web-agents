from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.models import AgentRun, ToolInvocation
from app.agents.stream import RunEvent, emit
from app.context import build_context_messages, load_conversation_history, resolve_system_prompt
from app.conversations.models import Conversation, Message
from app.gateway import get_registry
from app.models.adapters import ChatModelAdapter
from app.quota import check_daily_quota, record_usage
from app.shared.config import get_settings
from app.shared.errors import AppError
from app.skills.models import Skill
from app.tools.llm_tools import ToolExecutionError, invoke_llm_tool
from app.tools.script_tools import invoke_script_tool, is_script_tool


@dataclass
class AgentContext:
    run_id: str
    user_id: str
    conversation_id: str | None
    skill_id: str
    model_provider_id: str | None
    user_message: str
    model_adapter: ChatModelAdapter
    structured_output: dict[str, Any] | None = None
    model_response: str | None = None
    skill: Skill | None = None
    events: list[RunEvent] = field(default_factory=list)

    def emit(self, event_type: str, data: dict[str, Any]):
        event = RunEvent(event_type=event_type, data=data)
        self.events.append(event)
        emit(self.run_id, event)


def load_context(ctx: AgentContext, db: Session) -> AgentContext:
    ctx.emit("run_started", {"run_id": ctx.run_id})
    settings = get_settings()
    check_daily_quota(db, ctx.user_id, daily_limit=settings.daily_token_limit)
    return ctx


def select_skill(ctx: AgentContext, db: Session) -> AgentContext:
    skill = db.query(Skill).filter(Skill.skill_id == ctx.skill_id).first()
    if skill is None:
        raise ToolExecutionError(ctx.skill_id, f"Skill not found: {ctx.skill_id}")
    ctx.skill = skill
    ctx.emit("skill_selected", {"skill_id": skill.skill_id, "name": skill.name})
    return ctx


def invoke_tool(ctx: AgentContext, db: Session) -> AgentContext:
    tool_name = ctx.skill.mock_tool_name or ctx.skill.skill_id
    ctx.emit("tool_started", {"tool_name": tool_name})

    # 工具白名单校验
    registry = get_registry()
    if not registry.is_allowed(tool_name):
        raise ToolExecutionError(tool_name, f"工具 '{tool_name}' 未在注册表中或已禁用")

    try:
        if is_script_tool(tool_name):
            result = invoke_script_tool(tool_name, ctx.user_message, ctx.model_adapter, ctx.run_id)
        else:
            result = invoke_llm_tool(tool_name, ctx.user_message, ctx.model_adapter)
    except ToolExecutionError:
        raise
    except Exception as e:
        raise ToolExecutionError(tool_name, f"Script tool failed: {e}") from e

    _record_adapter_usage(ctx, db, step="tool")

    ctx.emit("tool_completed", {"tool_name": tool_name, "output": result})
    ctx.emit("structured_result", {"tool_name": tool_name, "skill_id": ctx.skill.skill_id, "output": result})

    tool_inv = ToolInvocation(
        agent_run_id=ctx.run_id,
        tool_name=tool_name,
        input_params={"input_text": ctx.user_message},
        output=result,
        status="completed",
    )
    db.add(tool_inv)

    ctx.structured_output = result
    return ctx


def call_model(ctx: AgentContext, db: Session) -> AgentContext:
    skill_name = ctx.skill.name if ctx.skill else ctx.skill_id
    tool_name = (ctx.skill.mock_tool_name or ctx.skill_id) if ctx.skill else ctx.skill_id
    prompt_template = ctx.skill.prompt_template if ctx.skill else None

    # 1. 解析 system prompt（优先用 skill 的 prompt_template）
    system_prompt = resolve_system_prompt(
        skill_name=skill_name,
        tool_name=tool_name,
        tool_output=ctx.structured_output,
        prompt_template=prompt_template,
    )

    # 2. 加载会话历史
    history = load_conversation_history(db, ctx.conversation_id)

    # 3. 按 token 预算构造 messages（自动裁剪历史）
    settings = get_settings()
    messages = build_context_messages(
        system_prompt=system_prompt,
        user_message=ctx.user_message,
        history_messages=history,
        token_budget=settings.daily_token_limit // 20,  # 单次 context 约为日限额 5%
    )

    response = ctx.model_adapter.invoke(messages)

    _record_adapter_usage(ctx, db, step="summarize")

    ctx.model_response = response
    ctx.emit("model_delta", {"content": response})
    return ctx


def persist_result(ctx: AgentContext, db: Session) -> AgentContext:
    run = db.query(AgentRun).filter(AgentRun.id == ctx.run_id).first()
    if not run:
        raise AppError(code="RUN_NOT_FOUND", message="Run not found during persist.", status_code=500)

    run.status = "completed"
    run.structured_output = ctx.structured_output

    if ctx.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == ctx.conversation_id).first()
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
        msg = Message(
            conversation_id=ctx.conversation_id,
            role="assistant",
            content=ctx.model_response or "",
        )
        db.add(msg)

    db.commit()
    ctx.emit("run_completed", {"run_id": ctx.run_id})
    return ctx


def _record_adapter_usage(ctx: AgentContext, db: Session, step: str) -> None:
    """从 adapter.last_usage 记录 token 消耗。"""
    usage = getattr(ctx.model_adapter, "last_usage", None)
    if not usage or usage.total_tokens == 0:
        return
    record_usage(
        db,
        user_id=ctx.user_id,
        run_id=ctx.run_id,
        provider_id=ctx.model_provider_id or "unknown",
        model_name=usage.model_name or "unknown",
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )


def execute_graph(ctx: AgentContext, db: Session) -> AgentContext:
    nodes = [load_context, select_skill, invoke_tool, call_model, persist_result]
    try:
        for node_fn in nodes:
            ctx = node_fn(ctx, db)
    except Exception as e:
        db.rollback()
        ctx.emit("run_failed", {"error": str(e), "run_id": ctx.run_id})
        run = db.query(AgentRun).filter(AgentRun.id == ctx.run_id).first()
        if run:
            run.status = "failed"
            run.error_message = str(e)
            db.commit()
        raise
    return ctx

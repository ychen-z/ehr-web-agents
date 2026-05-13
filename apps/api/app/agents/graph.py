from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.models import AgentRun, ToolInvocation
from app.agents.stream import RunEvent, emit
from app.conversations.models import Conversation, Message
from app.models.adapters import ChatModelAdapter
from app.shared.errors import AppError
from app.skills.models import Skill
from app.tools.llm_tools import ToolExecutionError, invoke_llm_tool


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

    result = invoke_llm_tool(tool_name, ctx.user_message, ctx.model_adapter)

    ctx.emit("tool_completed", {"tool_name": tool_name, "output": result})
    ctx.emit("structured_result", result)

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
    import json as _json

    skill_name = ctx.skill.name if ctx.skill else ctx.skill_id
    tool_name = (ctx.skill.mock_tool_name or ctx.skill_id) if ctx.skill else ctx.skill_id

    system_prompt = (
        f"You are an HR recruitment assistant. "
        f"The user activated the \"{skill_name}\" skill which invoked the \"{tool_name}\" tool.\n\n"
        f"The tool has already produced structured output (shown below). "
        f"Use the tool output as your primary source of truth. "
        f"Summarize, explain, or expand on the tool results in a helpful way for the HRBP user. "
        f"Do NOT ignore the tool output or generate unrelated content.\n\n"
        f"--- TOOL OUTPUT ---\n{_json.dumps(ctx.structured_output, ensure_ascii=False, indent=2)}\n--- END TOOL OUTPUT ---"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": ctx.user_message},
    ]
    response = ctx.model_adapter.invoke(messages)

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

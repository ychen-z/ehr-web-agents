"""Agent 执行引擎：ReAct 循环 + HITL 检查点 + 死循环兜底。

流程：
  load_context → select_skill → agent_loop(推理→工具→检查点→回写循环) → persist_result

agent_loop 内部：
  1. LLM 规划下一步（call_tool 或 respond）
  2. 若 call_tool：执行工具，检查 checkpoint → 暂停或继续循环
  3. 若 respond：生成最终回答，跳出循环
  4. 超过 MAX_ITERATIONS 轮 → 强制总结已有结果并停止
"""

from __future__ import annotations

import json as _json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.models import AgentRun, ToolInvocation
from app.agents.stream import RunEvent, emit
from app.context import build_context_messages, load_conversation_history
from app.conversations.models import Conversation, Message
from app.gateway import get_registry
from app.models.adapters import ChatModelAdapter
from app.quota import check_daily_quota, record_usage
from app.shared.config import get_settings
from app.shared.errors import AppError
from app.skills.models import Skill
from app.tools.llm_tools import ToolExecutionError, invoke_llm_tool
from app.tools.script_tools import invoke_script_tool, is_script_tool

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


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
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    paused: bool = False
    human_input: str | None = None
    human_comment: str | None = None

    def emit(self, event_type: str, data: dict[str, Any]):
        event = RunEvent(event_type=event_type, data=data)
        self.events.append(event)
        emit(self.run_id, event)


# ---------- Graph Nodes ----------


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


def agent_loop(ctx: AgentContext, db: Session) -> AgentContext:
    """ReAct 循环：推理 → 工具调用 → 检查点 → 结果回写，直到 LLM 决定回复或超轮次。"""
    registry = get_registry()
    available_tools = _get_available_tools_description(ctx)

    while ctx.iteration < MAX_ITERATIONS:
        ctx.iteration += 1
        ctx.emit("loop_iteration", {"iteration": ctx.iteration, "max": MAX_ITERATIONS})

        # 1. LLM 规划下一步
        decision = _plan_next_step(ctx, db, available_tools)

        action = decision.get("action", "respond")

        if action == "respond":
            ctx.model_response = decision.get("content", "")
            ctx.emit("model_delta", {"content": ctx.model_response})
            break

        elif action == "call_tool":
            tool_name = decision.get("tool_name", "")
            tool_input = decision.get("tool_input", ctx.user_message)

            # 白名单校验
            if not registry.is_allowed(tool_name):
                ctx.tool_results.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "output": {"error": f"工具 '{tool_name}' 未注册或已禁用"},
                    "status": "rejected",
                })
                continue

            # 执行工具
            result = _execute_tool(ctx, db, tool_name, tool_input)
            ctx.tool_results.append({
                "tool": tool_name,
                "input": tool_input,
                "output": result,
                "status": "completed",
            })

            # 记录为最新 structured_output
            ctx.structured_output = result
            ctx.emit("structured_result", {
                "tool_name": tool_name,
                "skill_id": ctx.skill.skill_id,
                "output": result,
            })

            # --- HITL 检查点 ---
            checkpoint = _check_checkpoint(ctx.skill, tool_name)
            if checkpoint:
                _pause_at_checkpoint(ctx, db, checkpoint, result)
                return ctx  # 暂停退出，等待 resume
        else:
            ctx.model_response = decision.get("content", str(decision))
            ctx.emit("model_delta", {"content": ctx.model_response})
            break
    else:
        # 死循环兜底
        logger.warning("Agent loop hit max iterations (%d) for run %s", MAX_ITERATIONS, ctx.run_id)
        ctx.emit("loop_max_reached", {"iterations": ctx.iteration})
        ctx.model_response = _force_summarize(ctx, db)
        ctx.emit("model_delta", {"content": ctx.model_response})

    return ctx


def persist_result(ctx: AgentContext, db: Session) -> AgentContext:
    if ctx.paused:
        return ctx

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
    ctx.emit("run_completed", {"run_id": ctx.run_id, "iterations": ctx.iteration})
    return ctx


# ---------- HITL Checkpoint ----------


def _get_skill_checkpoints(skill: Skill) -> list[dict]:
    """解析 skill 的 checkpoints 配置。"""
    if not skill.checkpoints:
        return []
    try:
        data = _json.loads(skill.checkpoints)
        return data if isinstance(data, list) else []
    except (TypeError, _json.JSONDecodeError):
        return []


def _check_checkpoint(skill: Skill, tool_name: str) -> dict | None:
    """检查执行完 tool_name 后是否需要暂停。"""
    checkpoints = _get_skill_checkpoints(skill)
    for cp in checkpoints:
        if cp.get("after_tool") == tool_name:
            return cp
    return None


def _pause_at_checkpoint(ctx: AgentContext, db: Session, checkpoint: dict, tool_result: dict) -> None:
    """暂停 Agent Loop，持久化状态到 DB，推送 checkpoint_reached 事件。"""
    checkpoint_state = {
        "iteration": ctx.iteration,
        "tool_results": ctx.tool_results,
        "structured_output": ctx.structured_output,
        "checkpoint_config": checkpoint,
        "user_message": ctx.user_message,
        "skill_id": ctx.skill_id,
        "conversation_id": ctx.conversation_id,
        "model_provider_id": ctx.model_provider_id,
    }

    run = db.query(AgentRun).filter(AgentRun.id == ctx.run_id).first()
    if run:
        run.status = "awaiting_input"
        run.checkpoint_state = checkpoint_state
        run.structured_output = ctx.structured_output
        db.commit()

    ctx.paused = True
    ctx.emit("checkpoint_reached", {
        "run_id": ctx.run_id,
        "prompt": checkpoint["prompt"],
        "options": checkpoint["options"],
        "tool_output": tool_result,
        "tool_name": checkpoint["after_tool"],
    })


def resume_from_checkpoint(ctx: AgentContext, db: Session) -> AgentContext:
    """从检查点恢复执行。human_input 已注入 ctx。"""
    ctx.emit("checkpoint_resumed", {
        "run_id": ctx.run_id,
        "choice": ctx.human_input,
        "comment": ctx.human_comment,
    })

    # 将人类决策注入 tool_results 作为上下文
    ctx.tool_results.append({
        "tool": "__human_decision__",
        "input": "",
        "output": {
            "decision": ctx.human_input,
            "comment": ctx.human_comment or "",
        },
        "status": "completed",
    })

    # 继续 Agent Loop
    ctx = agent_loop(ctx, db)
    ctx = persist_result(ctx, db)
    return ctx


# ---------- Internal Helpers ----------


def _get_available_tools_description(ctx: AgentContext) -> str:
    """构造可用工具列表描述，给 planning LLM 用。"""
    registry = get_registry()
    tools = registry.list_enabled()
    if not tools:
        return "无可用工具。"

    lines = []
    for t in tools:
        lines.append(f"- {t.name}: {t.description}")
    return "\n".join(lines)


PLANNING_SYSTEM_PROMPT = """你是一个 HR 招聘 Agent。用户给了你一个任务，你需要决定下一步做什么。

当前激活的技能：{skill_name}（主工具：{primary_tool}）

可用工具：
{available_tools}

你必须输出 JSON（不要输出其他内容），格式二选一：

1. 调用工具：
{{"action": "call_tool", "tool_name": "工具名", "tool_input": "传给工具的输入文本"}}

2. 直接回复用户（所有工具调用已完成，或者任务不需要工具）：
{{"action": "respond", "content": "你的最终回复内容"}}

规则：
- 每次只能选一个 action
- tool_input 是自然语言描述，会传给对应工具
- 优先使用当前技能的主工具 {primary_tool}
- 如果之前已经调用过工具且结果足够回答用户，选择 respond
- 不要重复调用同一工具处理相同输入
- 最多可以调用 {max_iterations} 次工具
- 如果用户在检查点做了决策，根据决策生成合适的回复
"""


def _plan_next_step(ctx: AgentContext, db: Session, available_tools: str) -> dict[str, Any]:
    """让 LLM 决定下一步：调用工具或直接回复。"""
    primary_tool = (ctx.skill.mock_tool_name or ctx.skill.skill_id) if ctx.skill else ""
    skill_name = ctx.skill.name if ctx.skill else ctx.skill_id

    system_prompt = PLANNING_SYSTEM_PROMPT.format(
        available_tools=available_tools,
        max_iterations=MAX_ITERATIONS,
        skill_name=skill_name,
        primary_tool=primary_tool,
    )

    # 构造消息上下文
    messages_content: list[dict] = []

    # 加载会话历史（简短版）
    history = load_conversation_history(db, ctx.conversation_id)
    if history:
        messages_content.extend(history[-6:])  # 最近 6 条保持上下文

    # 用户消息
    messages_content.append({"role": "user", "content": ctx.user_message})

    # 已有的工具调用历史
    if ctx.tool_results:
        tool_history = "\n".join(
            f"[已调用] {r['tool']}(input=\"{r['input'][:100]}...\") → 状态: {r['status']}"
            + (f", 输出摘要: {_json.dumps(r['output'], ensure_ascii=False)[:200]}..." if r['status'] == 'completed' else "")
            for r in ctx.tool_results
        )
        messages_content.append({
            "role": "assistant",
            "content": f"我已经执行了以下工具调用：\n{tool_history}\n\n现在我需要决定下一步。",
        })

    # 人类决策上下文
    if ctx.human_input:
        messages_content.append({
            "role": "user",
            "content": f"用户在检查点选择了：{ctx.human_input}"
            + (f"\n用户备注：{ctx.human_comment}" if ctx.human_comment else ""),
        })

    settings = get_settings()
    messages = build_context_messages(
        system_prompt=system_prompt,
        user_message="基于以上信息，决定你的下一步 action（输出 JSON）。",
        history_messages=messages_content,
        token_budget=settings.daily_token_limit // 40,
    )

    raw_response = ctx.model_adapter.invoke(messages)
    _record_adapter_usage(ctx, db, step=f"plan_iter_{ctx.iteration}")

    return _parse_decision(raw_response)


def _parse_decision(raw: str) -> dict[str, Any]:
    """解析 LLM 的 planning 输出为结构化 decision。"""
    text = raw.strip()

    # 去掉 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()

    try:
        decision = _json.loads(text)
        if isinstance(decision, dict) and "action" in decision:
            return decision
    except _json.JSONDecodeError:
        pass

    # 解析失败 → 当作直接回复
    return {"action": "respond", "content": raw}


def _execute_tool(ctx: AgentContext, db: Session, tool_name: str, tool_input: str) -> dict[str, Any]:
    """执行单个工具调用。"""
    ctx.emit("tool_started", {"tool_name": tool_name, "iteration": ctx.iteration})

    try:
        if is_script_tool(tool_name):
            result = invoke_script_tool(tool_name, tool_input, ctx.model_adapter, ctx.run_id)
        else:
            result = invoke_llm_tool(tool_name, tool_input, ctx.model_adapter)
    except ToolExecutionError:
        raise
    except Exception as e:
        raise ToolExecutionError(tool_name, f"工具执行失败: {e}") from e

    _record_adapter_usage(ctx, db, step=f"tool_{tool_name}_iter_{ctx.iteration}")

    ctx.emit("tool_completed", {"tool_name": tool_name, "output": result, "iteration": ctx.iteration})

    # 持久化 tool invocation
    tool_inv = ToolInvocation(
        agent_run_id=ctx.run_id,
        tool_name=tool_name,
        input_params={"input_text": tool_input},
        output=result,
        status="completed",
    )
    db.add(tool_inv)

    return result


def _force_summarize(ctx: AgentContext, db: Session) -> str:
    """死循环兜底：强制总结已有工具输出。"""
    if not ctx.tool_results:
        return "抱歉，未能完成任务。请尝试简化您的请求。"

    results_summary = _json.dumps(
        [{"tool": r["tool"], "output": r["output"]} for r in ctx.tool_results if r["status"] == "completed"],
        ensure_ascii=False,
        indent=2,
    )[:3000]

    messages = [
        {"role": "system", "content": "你是 HR 招聘助手。请基于以下工具执行结果，为用户做简明总结。"},
        {"role": "user", "content": f"用户原始请求：{ctx.user_message}\n\n工具执行结果：\n{results_summary}\n\n请总结。"},
    ]
    response = ctx.model_adapter.invoke(messages)
    _record_adapter_usage(ctx, db, step="force_summarize")
    return response


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


# ---------- Graph Execution ----------


def execute_graph(ctx: AgentContext, db: Session) -> AgentContext:
    nodes = [load_context, select_skill, agent_loop, persist_result]
    try:
        for node_fn in nodes:
            ctx = node_fn(ctx, db)
            if ctx.paused:
                break
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

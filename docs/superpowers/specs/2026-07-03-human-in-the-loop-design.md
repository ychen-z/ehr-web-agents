# Human-in-the-Loop 检查点设计

## 1. 概述

在 Agent ReAct 循环中引入 Human-in-the-Loop (HITL) 检查点机制。当 Skill 配置了检查点，Agent 在指定工具执行完毕后暂停，将结果和选项推送给用户，等待人类决策后再继续执行。

### 目标

- Skill 可声明式配置检查点（哪个工具输出后暂停、提示语、选项）
- Agent Loop 命中检查点时优雅暂停，状态持久化到 DB
- 前端通过 SSE 收到 `checkpoint_reached` 事件，展示卡片选择器
- 用户选择后 POST resume API，Agent 从暂停点恢复继续
- 不影响无检查点 skill 的正常执行流程

### 不包含

- LLM 自主决定何时询问人类（本期仅支持配置声明）
- 检查点超时自动取消（后续可加）
- 多步审批链 / 多人审批

---

## 2. Skill 检查点配置

### 2.1 配置格式

在 Skill catalog/manifest 中新增 `checkpoints` 字段：

```python
{
    "skill_id": "screen_resume",
    "name": "Resume Screening",
    "mock_tool_name": "screen_resume",
    "checkpoints": [
        {
            "after_tool": "screen_resume",       # 触发时机：该工具执行完毕后
            "prompt": "简历筛选完成，请确认下一步操作：",
            "options": [
                {"label": "推进到面试", "value": "proceed_interview"},
                {"label": "拒绝候选人", "value": "reject"},
                {"label": "需要更多信息", "value": "need_more_info"},
            ]
        }
    ]
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `after_tool` | string | Y | 工具名，执行完毕后触发检查点 |
| `prompt` | string | Y | 展示给用户的提示文案 |
| `options` | array | Y | 可选操作列表（2-5 个） |
| `options[].label` | string | Y | 按钮/卡片文案 |
| `options[].value` | string | Y | 选择值，传回 resume API |
| `options[].description` | string | N | 选项补充描述 |

### 2.3 数据库存储

Skill 模型新增字段：

```python
class Skill(Base):
    # ... 现有字段 ...
    checkpoints: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON 序列化的 checkpoints 列表
```

---

## 3. Agent Loop 暂停机制

### 3.1 执行流程变更

```
agent_loop:
  while iteration < MAX_ITERATIONS:
    plan → decision
    if call_tool:
      result = execute_tool(...)
      
      # --- 新增：检查点判断 ---
      checkpoint = _check_checkpoint(ctx.skill, tool_name)
      if checkpoint:
        _pause_at_checkpoint(ctx, db, checkpoint, result)
        return ctx   # 退出循环，run 状态为 awaiting_input
      # --- 新增结束 ---
      
      continue loop
    if respond:
      break
```

### 3.2 暂停操作 `_pause_at_checkpoint`

```python
def _pause_at_checkpoint(ctx, db, checkpoint, tool_result):
    # 1. 序列化当前状态
    checkpoint_state = {
        "iteration": ctx.iteration,
        "tool_results": ctx.tool_results,
        "structured_output": ctx.structured_output,
        "checkpoint_config": checkpoint,
    }
    
    # 2. 更新 Run 状态
    run = db.query(AgentRun).filter(AgentRun.id == ctx.run_id).first()
    run.status = "awaiting_input"
    run.checkpoint_state = checkpoint_state
    db.commit()
    
    # 3. 推送 SSE 事件
    ctx.emit("checkpoint_reached", {
        "run_id": ctx.run_id,
        "prompt": checkpoint["prompt"],
        "options": checkpoint["options"],
        "tool_output": tool_result,
        "tool_name": checkpoint["after_tool"],
    })
    
    # 4. 标记 ctx 为暂停
    ctx.paused = True
```

### 3.3 AgentRun 模型扩展

```python
class AgentRun(Base):
    # ... 现有字段 ...
    checkpoint_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # status 新增可选值: "awaiting_input"
```

### 3.4 AgentContext 扩展

```python
@dataclass
class AgentContext:
    # ... 现有字段 ...
    paused: bool = False
    human_input: str | None = None  # resume 时注入的用户选择
```

---

## 4. Resume API

### 4.1 接口定义

```
POST /api/agent/runs/{run_id}/resume
Authorization: Bearer <token>
Content-Type: application/json

{
    "choice": "proceed_interview",       # 用户选择的 option.value
    "comment": "候选人技术面表现不错"     # 可选：用户附加说明
}
```

**响应：**
```json
{
    "id": "run-xxx",
    "status": "running",
    "message": "检查点已确认，继续执行"
}
```

### 4.2 Resume 逻辑

```python
@router.post("/{run_id}/resume")
def resume_run(run_id, body, background_tasks, current_user, db, settings):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    
    # 校验
    assert run.status == "awaiting_input"
    assert run.user_id == current_user.id
    
    # 恢复状态
    state = run.checkpoint_state
    run.status = "running"
    run.checkpoint_state = None
    db.commit()
    
    # 重建 AgentContext
    ctx = AgentContext(
        run_id=run.id,
        user_id=run.user_id,
        ...
        iteration=state["iteration"],
        tool_results=state["tool_results"],
        structured_output=state["structured_output"],
        human_input=body.choice,
    )
    
    # 继续后台执行
    background_tasks.add_task(_resume_run_background, ctx)
```

### 4.3 恢复后的 Agent Loop 行为

恢复后，`human_input` 作为额外上下文注入下一轮 planning prompt：

```
用户在检查点选择了：{human_input}
用户备注：{comment}

请基于用户的决策，决定下一步 action。
```

这样 LLM 可以根据人类决策决定后续行为（调用新工具 or 生成总结回复）。

---

## 5. SSE 事件协议

### 5.1 新增事件类型

```
event: checkpoint_reached
data: {
    "run_id": "xxx",
    "prompt": "简历筛选完成，请确认下一步操作：",
    "options": [
        {"label": "推进到面试", "value": "proceed_interview"},
        {"label": "拒绝候选人", "value": "reject"},
        {"label": "需要更多信息", "value": "need_more_info"}
    ],
    "tool_output": { ... },   // 工具输出摘要
    "tool_name": "screen_resume"
}
```

### 5.2 前端处理

收到 `checkpoint_reached` 后：
1. 暂停 loading 动画
2. 渲染 `CheckpointCard` 组件（卡片选择器）
3. 用户选择后调用 `POST /resume`
4. 重新连接 SSE stream 继续监听

---

## 6. 前端 CheckpointCard 组件

```tsx
interface CheckpointCardProps {
    runId: string;
    prompt: string;
    options: { label: string; value: string; description?: string }[];
    toolOutput: Record<string, any>;
    toolName: string;
    onResume: (choice: string, comment?: string) => void;
}
```

UI 结构：
```
┌─────────────────────────────────────────┐
│ 🔔 需要您的确认                          │
├─────────────────────────────────────────┤
│ 简历筛选完成，请确认下一步操作：           │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 推进到   │ │ 拒绝     │ │ 需要更   │ │
│  │ 面试 ✓  │ │ 候选人   │ │ 多信息   │ │
│  └──────────┘ └──────────┘ └──────────┘ │
│                                          │
│ 备注（可选）：[________________]          │
│                                          │
│                        [ 确认并继续 ]     │
└─────────────────────────────────────────┘
```

---

## 7. persist_result 适配

`persist_result` 节点需要区分暂停 vs 完成：

```python
def persist_result(ctx: AgentContext, db: Session) -> AgentContext:
    if ctx.paused:
        # 检查点暂停，不标记 completed，不写 assistant message
        return ctx
    
    # 原有逻辑：标记 completed + 写 message
    run.status = "completed"
    ...
```

---

## 8. 完整执行时序

### 正常（无检查点）
```
POST /runs → background: execute_graph → agent_loop → persist_result(completed)
  SSE: run_started → skill_selected → loop_iteration → structured_result → run_completed
```

### 有检查点
```
POST /runs → background: execute_graph → agent_loop → checkpoint hit → pause
  SSE: run_started → ... → checkpoint_reached → stream_closed

--- 用户思考 ---

POST /runs/{id}/resume → background: resume_graph → agent_loop(继续) → persist_result
  SSE: checkpoint_resumed → loop_iteration → ... → run_completed
```

---

## 9. 内置 Skill 检查点示例

| Skill | after_tool | 提示 | 选项 |
|-------|-----------|------|------|
| screen_resume | screen_resume | 简历筛选完成，请确认下一步 | 推进面试 / 拒绝 / 需要更多信息 |
| summarize_interview_feedback | summarize_interview_feedback | 面试反馈已汇总，请确认决策 | 发Offer / 下一轮面试 / 拒绝 / 搁置 |

`generate_jd`、`generate_interview_questions`、`generate_html` 不需要检查点（纯生成类，不涉及决策）。

---

## 10. 文件结构变更

```
apps/api/app/
├── agents/
│   ├── graph.py          # +_check_checkpoint, +_pause_at_checkpoint, resume逻辑
│   ├── router.py         # +POST /resume 接口
│   ├── schemas.py        # +ResumeInput schema
│   └── models.py         # +checkpoint_state 字段
├── skills/
│   ├── catalog.py        # +checkpoints 配置
│   └── models.py         # +checkpoints 字段
apps/web/src/
├── features/agent/
│   └── CheckpointCard.tsx  # 新增：卡片选择器组件
├── services/
│   └── agentApi.ts         # +resumeRun() 方法
```

---

## 11. 数据库迁移

新增迁移 `0004_checkpoint_state.py`：

```python
def upgrade():
    op.add_column("agent_runs", sa.Column("checkpoint_state", sa.JSON, nullable=True))
    op.add_column("skills", sa.Column("checkpoints", sa.Text, nullable=True))
```

---

## 12. 测试策略

- **单测 `_check_checkpoint`**：配置匹配 / 不匹配 / 无配置
- **单测 pause + resume**：验证状态序列化/反序列化正确
- **集成测试**：POST /runs → 收到 checkpoint_reached → POST /resume → run_completed
- **FakeChatAdapter 扩展**：resume 后 planning 应能读到 human_input 并 respond

---

## 13. 安全考量

- resume 接口验证 run.user_id == current_user.id（防越权）
- resume 仅在 status == "awaiting_input" 时允许
- checkpoint_state 不含敏感信息（不存 API key 等）
- 前端防重复提交（resume 按钮 loading 状态）

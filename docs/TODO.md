# HR Agent 项目 TODO

本清单记录 MVP 之后的下一步工作。除非有线上问题阻塞使用，否则按自上而下顺序推进。

## P0 - 稳定当前 MVP

- [x] 为技能所有权字段添加正确的 Alembic 迁移，不再依赖手工 SQL。
  - 背景：`skills` 表需要 `owner_user_id`、`visibility`、`source` 字段。
  - 验收：已有 MySQL 数据库可执行 `alembic upgrade head`，无需手工改表。
- [x] 重启并验证正确的 API 服务绑定到 `8010` 端口。
  - 背景：迁移到 `8010` 以避免冲突；文档化端口冲突恢复流程。
- [x] 提交并推送私有 / 共享技能管理改动。
  - 提交：`6edf6f3`、`1d7296a`。远端已更新。
- [x] 让本地开发端口可配置，并文档化冲突恢复。
  - 背景：考虑将 API 迁到 `8010` 或文档化如何杀掉冲突进程。
  - 验收：README 提供可靠启动路径与前端 API URL 覆盖方式。

## P1 - 移除 Mock 工具执行

- [ ] 用真实 MCP 客户端集成替换 `mock_mcp`。
  - 背景：时间线事件是真实的，但工具执行目前是本地 mock 逻辑。
  - 验收：技能通过 MCP 客户端调用工具，而非 `app/mock_mcp/tools.py`。
- [x] 定义技能 manifest 格式。
  - 包含：`skill_id`、名称、描述、可见性、版本、prompts、MCP server/tool 绑定、输入 schema。
  - 验收：技能创建时存储 manifest 字段并校验必填工具绑定。
  - 完成：`ToolSpec` dataclass + `ToolRegistry.validate_skill_binding()` 实现工具绑定校验。
- [x] 添加 MCP server 注册 / 配置。
  - 背景：内置 MCP 工具应为所有用户预配置；私有 / admin 技能可绑定到允许的工具。
  - 验收：后端能列出可用 MCP 工具，并校验技能所选工具存在。
  - 完成：`app/gateway/` 全局 `ToolRegistry`，启动时自动注册所有内置工具，`invoke_tool` 前白名单校验。
- [ ] 持久化工具调用 payload 与输出以备审计。
  - 背景：UI 已展示 Tool Invocation Evidence；后端应提供持久化证据。
  - 验收：run 详情 API 能返回工具名、输入、输出、起止时间、状态。

## P1 - 技能管理

- [ ] 完善私有 / 共享技能 UX。
  - 背景：Marketplace 已有基础 create/edit/delete 表单。
  - 验收：用户能创建私有技能，admin 能创建共享技能，标签与权限清晰。
- [x] 在技能创建中加入工具选择器和 prompt 编辑器。
  - 提交：`1d7296a`。创建者可选择工具绑定；LLM 现在使用工具输出作为上下文。
- [ ] 为用户 / admin 技能添加版本管理。
  - 验收：更新技能会创建新版本或记录更新元数据，不影响历史 run。
- [ ] 添加删除 / 归档规则。
  - 背景：系统技能不可删除；用户技能若已被 run 使用应归档。
  - 验收：无历史 agent run 指向缺失的技能元数据。

## P1 - 真实 HR 数据

- [ ] 添加候选人和职位需求数据模型。
  - 验收：JD 生成和筛选可引用持久化的职位 / 候选人记录。
- [ ] 添加简历上传与解析流程。
  - 验收：用户能上传简历、解析文本、对职位跑筛选。
- [ ] 添加面试反馈记录。
  - 验收：反馈总结技能可使用存储的面试官笔记。
- [ ] 添加 HR 政策或招聘知识源。
  - 验收：agent 能基于受控知识源回答问题，而非仅依赖 prompt 上下文。

## P2 - 智能体运行时加固

- [x] 实现 Context 服务（会话历史注入 + prompt_template 生效 + Token 预算裁剪）。
  - 验收：Agent 能感知同一会话历史；prompt_template 占位符生效；超预算消息自动丢弃。
  - 完成：`app/context/` 模块，`build_context_messages` + `resolve_system_prompt` + `load_conversation_history`。
- [ ] 将 agent 编排转为显式 LangGraph `StateGraph`。
  - 验收：图节点以图状态转换的形式声明并可测试。
- [ ] 将 SSE / 事件历史持久化到 MySQL。
  - 背景：当前事件历史存启后可重建时间线。
- [ ] 为 agent run 加后台任务队列。
  - 验收：长模型 / 工具调用不依赖 FastAPI 进程内后台任务。
- [ ] 添加取消支持。
  - 验收：点击 Stop 将 run 标记为 cancelled，并尽可能停止后续工具 / 模型工作。
- [ ] 添加 run 超时与重试策略。
  - 验收：卡住的 run 被标记为 failed 并带清晰原因。

## P2 - 鉴权、RBAC 与审计

- [ ] 用企业级鉴权方案替换本地测试 auth。
  - 选项：SSO/OIDC、session + refresh token、或公司身份提供商。
- [ ] 添加细粒度 RBAC。
  - 角色：HRBP、Admin、Skill Publisher、Auditor。
- [ ] 添加审计日志。
  - 验收：技能 create/update/delete/install/run 事件记录 actor 与时间戳。
- [ ] 若多 HR 团队使用系统，添加租户或组织边界。

## P2 - 模型运营

- [ ] 为 DeepSeek、OpenAI、Minimax 添加 provider 配置 UI。
  - 验收：admin 无需编辑 `.env` 即可测试 provider 连通性。
- [ ] 为每个 provider 添加模型参数。
  - 包含：模型名、temperature、max tokens、base URL。
- [x] 添加模型用量追踪。
  - 验收：记录 provider、模型、token 用量。每用户每日上限，超限 429。
  - 提交：`token_usage_logs` 表，adapter 捕获 usage，GET /api/quota/usage/today。
- [ ] 添加 provider 健康检查。
  - 验收：模型选择器清晰展示可用 / 不可用 provider。

## P2 - 前端质量

- [ ] 添加浏览器 E2E 测试。
  - 验收：Playwright 覆盖登录、安装技能、运行 agent、查看时间线 / 证据。
- [ ] 改进 Marketplace 管理 UI。
  - 验收：create/edit/delete 比当前紧凑 MVP 表单更清晰。
- [ ] 为每个 API 失败路径添加 empty / error 状态。
- [ ] 对 320px、768px、1024px 与桌面布局做响应式 QA。

## P3 - 部署与运维

- [ ] 为 API 和 Web 添加 Dockerfile。
- [ ] 添加完整 Docker Compose（MySQL、API、Web）。
- [ ] 添加 CI pipeline。
  - 验收：PR 触发后端测试、前端 lint/typecheck/build、MySQL 迁移测试。
- [ ] 添加生产就绪检查。
  - 包含：`/ready` 数据库检查、CORS 配置、安全头、限流、结构化日志。
- [ ] 添加部署文档。
  - 包含：env 变量、迁移流程、回滚流程、密钥处理。

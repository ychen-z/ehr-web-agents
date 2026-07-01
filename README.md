# HR Agent MVP

招聘场景的 HR 智能体 MVP，基于 Vite React + FastAPI + LangGraph + MySQL 构建。

## MVP 范围

- **技能市场** — 浏览并调用招聘相关技能（简历筛选、JD 生成、面试问答、候选人匹配）。
- **招聘技能** — 简历筛选、JD 生成、面试问题生成、面试反馈总结。
- **HTML 页面生成技能** — 新增的脚本工具技能，LLM 提取页面规格，Python 模板渲染 HTML，前端沙箱内嵌预览。
- **Mock MCP 工具** — 模拟候选人数据库、邮件服务、评估工具，用于开发与测试。
- **真实 LLM 适配器** — DeepSeek、OpenAI、Minimax 后端驱动智能体推理，无 mock LLM 回退。

## 技能体系

| skill_id | 名称 | 工具类型 | 描述 |
|---|---|---|---|
| `generate_jd` | JD 生成 | LLM 工具 | 根据岗位需求生成职位描述 |
| `screen_resume` | 简历筛选 | LLM 工具 | 按岗位要求评估候选人简历 |
| `generate_interview_questions` | 面试问题 | LLM 工具 | 按能力维度生成面试问题 |
| `summarize_interview_feedback` | 面试反馈总结 | LLM 工具 | 汇总多位面试官的反馈 |
| `generate_html` | HTML 页面生成 | **脚本工具** | LLM 提取页面规格 → Python 渲染 HTML → 沙箱预览 |

### 脚本工具架构

工具分两类，按名字在 `app/agents/graph.py:invoke_tool` 分派：

- **LLM 工具** (`app/tools/llm_tools.py`) — 纯 LLM 结构化输出，schema 定义在 `TOOL_SCHEMAS`。
- **脚本工具** (`app/tools/script_tools.py`) — Python 函数，可调 LLM + 写文件 + 跑 subprocess。

注册新脚本工具：

```python
from app.tools.script_tools import register, run_subprocess

@register("my_tool")
def my_tool(user_message, adapter, run_id):
    spec = invoke_llm_tool("my_tool", user_message, adapter)
    proc = run_subprocess(["python", "scripts/render.py"], timeout=60)
    return {**spec, "script_output": proc}
```

`generate_html` 流程：

```
用户输入
   ↓
LLM 提取 PageSpec (title/theme/primary_color/sections[])
   ↓
Python 渲染器 _render_html_from_spec(spec)
   ↓
HTML 字符串通过 SSE 推送前端
   ↓
iframe srcDoc 内嵌渲染 (sandbox="allow-scripts")
```

### 安全护栏

- HTML 转义所有 spec 字段，防 XSS 注入
- `run_id` 正则校验，防路径穿越
- 容量上限：sections ≤ 20、items ≤ 30、文本 ≤ 2000 字、HTML ≤ 256 KiB
- `run_subprocess` 强制 list 参数（禁 `shell=True`），默认 30s 超时
- iframe `sandbox="allow-scripts"` + `referrerPolicy="no-referrer"`
- 不落盘、不暴露静态服务，避免 IDOR 跨用户访问

## 前置依赖

- Node.js 18+
- Python 3.11+
- Docker（用于 MySQL）

## 本地启动

### 1. 环境变量

复制 `.env.example` 到 `.env` 并按需配置：

```bash
cp .env.example .env
```

| 变量 | 描述 | 默认值 |
|---|---|---|
| `MYSQL_HOST` | MySQL 主机 | `127.0.0.1` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_DATABASE` | MySQL 库名 | `ehr_agents` |
| `MYSQL_USER` | MySQL 用户 | `ehr_agents` |
| `MYSQL_PASSWORD` | MySQL 密码 | `ehr_agents` |
| `JWT_SECRET` | 鉴权 Token 签名密钥 | （必填）|
| `CORS_ORIGINS` | 允许的前端来源 | `http://localhost:5173` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | （调用真实模型时必填）|
| `DEEPSEEK_MODEL` | DeepSeek 模型名 | `deepseek-chat` |
| `OPENAI_API_KEY` | OpenAI API Key | （调用真实模型时必填）|
| `OPENAI_MODEL` | OpenAI 模型名 | `gpt-4o-mini` |
| `MINIMAX_API_KEY` | Minimax API Key | （调用 Minimax 模型时必填）|
| `MINIMAX_BASE_URL` | Minimax OpenAI 兼容地址 | `https://api.minimax.chat/v1` |
| `MINIMAX_MODEL` | Minimax 模型名 | `MiniMax-M1` |

**重要：** DeepSeek、OpenAI、Minimax 调用真实生产 API。Agent 运行至少需要配置一个 provider 的 API Key，无 mock LLM 回退。

### 2. 启动 MySQL

```bash
docker compose up -d mysql
# 等待 MySQL 健康检查通过后再跑迁移：
docker compose ps mysql
```

### 3. 后端（API）

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8010
```

### 4. 前端（Web）

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

应用访问地址：`http://localhost:5173`。前端默认通过 `apps/web/.env.example` 指向 `http://127.0.0.1:8010`。

如果登录返回 `404` 或 `405`，说明 API 端口被其他服务占用。排查：

```bash
lsof -nP -iTCP:8010 -sTCP:LISTEN
```

## 测试账号

| 邮箱 | 密码 | 角色 |
|---|---|---|
| `hrbp@example.com` | `password123` | HRBP |
| `admin@example.com` | `password123` | Admin |

## 验证

```bash
# 后端测试
cd apps/api && pytest -v

# 前端 lint、typecheck、build
cd apps/web && npm run lint && npm run typecheck && npm run build
```

## 已知限制

- 当前验证环境无法使用 Docker，因此 MySQL 迁移（`alembic upgrade head`）未在此处验证。有 Docker 的用户应先执行 `docker compose up -d mysql` 和 `alembic upgrade head`，再启动 API 服务。

## 后续计划

详见 `docs/TODO.md`，主要方向：

- 用真实 MCP 客户端替换 mock 工具执行
- 完善私有 / 共享技能的 UX 与版本管理
- 接入真实 HR 数据（候选人、职位、简历解析）
- 智能体运行时加固（LangGraph StateGraph、事件持久化、取消与超时）
- 鉴权、RBAC、审计日志
- 模型运营（provider 配置 UI、用量追踪、健康检查）
- 部署与运维（Dockerfile、CI、生产就绪检查）

# HR Agent MVP Design

Date: 2026-05-08
Status: Draft approved for planning

## Goal

Build a web-based HR Agent MVP for HRBP users focused on recruitment workflows. The MVP lets users log in with local test accounts, install recruitment skills, select a DeepSeek or GPT model, run agent tasks, and view both streaming responses and structured recruiting outputs.

The implementation should use Vite React on the web side and FastAPI with LangChain/LangGraph on the server side. MySQL stores application state. Model calls use real provider APIs only.

## Scope

### In Scope

- Monorepo scaffold with `apps/web` and `apps/api`.
- Vite React TypeScript recruitment Agent workspace.
- FastAPI backend with feature-first modules.
- MySQL persistence for users, skills, installations, conversations, messages, agent runs, tool invocations, and model metadata.
- Local test login with built-in HRBP and Admin users.
- Recruitment skill marketplace and installation flow.
- Built-in recruitment skills:
  - JD generation.
  - Resume screening advice.
  - Interview question generation.
  - Interview feedback summary.
- LangGraph-based agent orchestration.
- Mock MCP tools that return structured recruitment results.
- DeepSeek and OpenAI/GPT model adapters using real API keys from environment variables.
- REST APIs for management flows and SSE for streaming agent events.

### Out of Scope for MVP

- Enterprise SSO.
- Full RBAC and tenant management.
- Real MCP server/client integration.
- File upload and resume parsing.
- Knowledge base or RAG.
- Multi-user collaboration.
- Audit reports and analytics dashboards.
- Mock LLM fallback when model keys are missing or calls fail.

## Product Experience

The primary screen is a recruitment Agent workspace with a three-column layout:

- Left column: conversation list, installed skills, and model selector.
- Center column: chat-style task input, streaming response, and execution progress.
- Right column: structured result cards such as JD drafts, candidate screening criteria, interview question lists, and feedback summaries.

Main user flow:

1. User opens the app and logs in as HRBP or Admin using a local test account.
2. User opens the skill marketplace.
3. User installs one or more recruitment skills.
4. User selects DeepSeek or GPT as the model.
5. User starts or opens a conversation.
6. User enters a recruiting task.
7. Agent streams progress and response text.
8. Right panel displays structured output produced by the selected skill/tool.
9. Conversation history persists after refresh.

The visual style should feel like an enterprise HR SaaS product: trustworthy, clear, and information-dense enough for HRBP workflows without feeling generic.

## Architecture

### Repository Layout

```text
apps/
  web/
    src/
  api/
    app/
docs/
  superpowers/
    specs/
docker-compose.yml
.env.example
README.md
```

### Frontend

- Vite + React + TypeScript.
- Feature-oriented source structure for auth, skills, conversations, agent runs, and shared UI.
- API client uses environment-based backend URL.
- REST requests manage login, skills, conversations, and model metadata.
- SSE client subscribes to agent run events.
- Client stores auth token/session in a simple MVP-safe mechanism and attaches it to API requests.

### Backend

- FastAPI with feature-first modules:
  - `auth` for local login and current user.
  - `skills` for marketplace and installation state.
  - `conversations` for conversation and message persistence.
  - `agents` for LangGraph runs and streaming events.
  - `models` for supported model metadata and adapters.
  - `mock_mcp` for built-in mock tool execution.
  - `shared` for config, database, errors, logging, and auth dependencies.
- SQLAlchemy or SQLModel can be used for MySQL access.
- Alembic should manage schema migrations.
- Pydantic settings validate required environment variables at startup.

### Integration Pattern

- REST for regular CRUD and management operations.
- SSE for one-way server-to-client agent progress and model output streaming.
- JSON error responses use a consistent shape:

```json
{
  "code": "SKILL_NOT_INSTALLED",
  "message": "Skill is not installed for this user.",
  "request_id": "...",
  "details": {}
}
```

## API Design

Core endpoints:

- `POST /api/auth/login` logs in as a local test user.
- `GET /api/me` returns the current user.
- `GET /api/skills` lists built-in skills and installation state.
- `POST /api/skills/{skill_id}/install` installs a skill for the current user.
- `DELETE /api/skills/{skill_id}/install` uninstalls a skill for the current user.
- `GET /api/models` lists available model providers and configured status.
- `GET /api/conversations` lists conversations for the current user.
- `POST /api/conversations` creates a conversation.
- `GET /api/conversations/{conversation_id}/messages` lists messages.
- `POST /api/agent/runs` creates an agent run for a conversation and user message.
- `GET /api/agent/runs/{run_id}/events` streams run events by SSE.

SSE event types:

- `run_started`.
- `skill_selected`.
- `tool_started`.
- `tool_completed`.
- `model_delta`.
- `structured_result`.
- `run_completed`.
- `run_failed`.

## Data Model

Initial MySQL tables:

- `users`: local MVP users with role metadata.
- `skills`: built-in skill catalog entries.
- `user_skills`: installed skill mapping per user.
- `model_configs`: supported model providers and display metadata. API keys remain in environment variables.
- `conversations`: conversation headers per user.
- `messages`: user and assistant messages.
- `agent_runs`: execution state for each agent task.
- `tool_invocations`: mock MCP tool calls and structured outputs.

The schema should keep provider secrets out of the database. Environment variables provide API keys and default model names.

## Agent Design

LangGraph should model the recruitment task as explicit nodes:

1. `load_context`: load user, installed skills, conversation history, and selected model.
2. `select_skill`: determine which installed recruitment skill applies to the task.
3. `invoke_mock_mcp_tool`: call the built-in mock MCP tool for structured recruitment output.
4. `call_model`: call the selected DeepSeek or GPT model through a common adapter.
5. `persist_result`: save assistant messages, structured output, run status, and tool invocation records.
6. `stream_events`: emit progress, token deltas, tool output, and completion state.

Model adapters expose a common interface so the rest of the agent graph does not depend on provider-specific APIs:

- `DeepSeekChatModel` uses `DEEPSEEK_API_KEY` and DeepSeek model settings.
- `OpenAIChatModel` uses `OPENAI_API_KEY` and GPT model settings.

If a model key is missing or a provider call fails, the API should surface a clear error. The MVP must not silently fall back to a mock LLM.

## Skill and Mock MCP Design

Skills are catalog entries with metadata, prompts, and a mock tool mapping. Installing a skill enables it for the current user and makes it available to the agent.

Mock MCP tools live in a clearly named backend module. They return deterministic structured recruitment outputs that the UI can render in the right panel. They should be isolated behind an interface so a future real MCP client can replace them without changing the UI contract.

Initial mock tools:

- `generate_jd` returns job title, responsibilities, requirements, interview focus, and selling points.
- `screen_resume` returns screening dimensions, strengths, risks, and recommended next step.
- `generate_interview_questions` returns question groups by competency.
- `summarize_interview_feedback` returns feedback summary, evidence, concerns, and decision recommendation.

## Security and Configuration

- `.env.example` includes placeholders for MySQL, JWT/session secret, CORS origin, DeepSeek API key, OpenAI API key, and default model names.
- Real secrets must not be committed.
- CORS should allow the local Vite origin explicitly.
- Backend config should validate required values at startup.
- Error responses must not expose stack traces or provider secrets.
- Logging should avoid PII, tokens, and API keys.

## Testing and Verification

Backend checks:

- Config validation starts with required environment variables.
- Login returns a usable token/session for HRBP and Admin test users.
- Skill list and install/uninstall work for the current user.
- Conversation creation and message listing persist in MySQL.
- Agent run creation validates installed skill and selected model.
- Mock MCP tool execution stores structured output.

Frontend checks:

- TypeScript build succeeds.
- Production build succeeds.
- Login page can enter the workspace.
- Skill marketplace displays skills and installation state.
- Agent workspace shows conversations, selected model, streaming events, and right-side structured output.

Manual acceptance:

1. Start MySQL, FastAPI, and Vite locally.
2. Log in as HRBP.
3. Install a recruitment skill.
4. Select DeepSeek or GPT.
5. Create a conversation and submit a recruitment task.
6. Observe streaming progress and final answer.
7. Verify the right panel shows structured recruitment output.
8. Refresh and verify conversation history remains.

## Future Extensions

- Replace mock MCP tools with real MCP client/server integration.
- Add enterprise SSO and full RBAC.
- Add tenant-aware data model.
- Add resume file upload and parsing.
- Add RAG over HR policies and recruiting knowledge.
- Add audit logs, admin analytics, and model usage metrics.
- Add deployment manifests and production observability.

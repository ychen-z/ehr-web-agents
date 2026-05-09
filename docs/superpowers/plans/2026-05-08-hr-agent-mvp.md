# HR Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working recruitment-focused HR Agent MVP with Vite React, FastAPI, LangGraph, MySQL, local login, skill installation, real DeepSeek/GPT model calls, mock MCP tools, streaming agent events, and persistent conversations.

**Architecture:** Use a monorepo with `apps/web` for the React client and `apps/api` for the FastAPI service. The backend is feature-first, with shared config/database/error handling and isolated modules for auth, skills, conversations, models, mock MCP tools, and agent runs. The frontend uses a three-column recruitment workspace and a typed API/SSE client.

**Tech Stack:** Vite, React, TypeScript, FastAPI, Pydantic Settings, SQLAlchemy, Alembic, PyMySQL, LangChain, LangGraph, OpenAI SDK-compatible clients, MySQL, pytest, Vitest/TypeScript build checks.

---

## File Structure

Create this repository structure:

```text
.
  README.md
  .env.example
  docker-compose.yml
  apps/
    api/
      pyproject.toml
      alembic.ini
      alembic/
        env.py
        versions/
          20260508_0001_initial.py
      app/
        __init__.py
        main.py
        auth/
          __init__.py
          router.py
          schemas.py
          service.py
        skills/
          __init__.py
          catalog.py
          models.py
          router.py
          schemas.py
          service.py
        conversations/
          __init__.py
          models.py
          router.py
          schemas.py
          service.py
        models/
          __init__.py
          adapters.py
          models.py
          router.py
          schemas.py
          service.py
        mock_mcp/
          __init__.py
          tools.py
          schemas.py
        agents/
          __init__.py
          graph.py
          models.py
          router.py
          schemas.py
          service.py
          stream.py
        shared/
          __init__.py
          auth.py
          config.py
          database.py
          errors.py
          logging.py
          seed.py
      tests/
        conftest.py
        test_auth.py
        test_skills.py
        test_conversations.py
        test_models.py
        test_mock_mcp.py
        test_agent_runs.py
    web/
      package.json
      index.html
      tsconfig.json
      tsconfig.node.json
      vite.config.ts
      src/
        main.tsx
        App.tsx
        styles.css
        env.d.ts
        lib/
          api.ts
          sse.ts
          errors.ts
        features/
          auth/
            LoginPage.tsx
            authStore.tsx
          skills/
            SkillsMarketplace.tsx
            skillsApi.ts
          models/
            modelApi.ts
          conversations/
            conversationApi.ts
          agent/
            agentApi.ts
            AgentWorkspace.tsx
            ResultPanel.tsx
            ChatPanel.tsx
            Sidebar.tsx
            types.ts
```

Responsibilities:

- `apps/api/app/shared/*`: cross-cutting configuration, database sessions, error shape, auth dependency, logging, and seed data.
- `apps/api/app/auth/*`: local HRBP/Admin login and token/current-user behavior.
- `apps/api/app/skills/*`: built-in recruitment skill catalog and user installation state.
- `apps/api/app/conversations/*`: conversation and message persistence.
- `apps/api/app/models/*`: supported model metadata plus DeepSeek/OpenAI adapters.
- `apps/api/app/mock_mcp/*`: deterministic mock recruitment tools behind a replaceable interface.
- `apps/api/app/agents/*`: LangGraph orchestration, run persistence, and SSE event streaming.
- `apps/web/src/lib/*`: typed HTTP and SSE clients.
- `apps/web/src/features/*`: UI features grouped by product capability.

---

## Chunk 1: Repository Bootstrap and Backend Foundation

### Task 1: Create root project files

**Files:**
- Create: `README.md`
- Create: `.env.example`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create root files**

`README.md` should include local setup commands for MySQL, API, and web. `.env.example` should include placeholders only:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=ehr_agents
MYSQL_USER=ehr_agents
MYSQL_PASSWORD=ehr_agents
JWT_SECRET=change-me-in-local-dev
CORS_ORIGINS=http://localhost:5173
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

`docker-compose.yml` should start MySQL 8 with database/user/password matching `.env.example`.

- [ ] **Step 2: Verify Docker config parses**

Run: `docker compose config`
Expected: exits 0 and shows a `mysql` service.

### Task 2: Create backend package and app shell

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/shared/config.py`
- Create: `apps/api/app/shared/database.py`
- Create: `apps/api/app/shared/errors.py`
- Create: `apps/api/app/shared/logging.py`
- Create: `apps/api/tests/conftest.py`

- [ ] **Step 1: Write failing config tests**

Create `apps/api/tests/test_config.py`:

```python
from app.shared.config import Settings


def test_database_url_is_built_from_mysql_settings():
    settings = Settings(
        mysql_host="db",
        mysql_port=3306,
        mysql_database="ehr_agents",
        mysql_user="user",
        mysql_password="pass",
        jwt_secret="secret",
        cors_origins="http://localhost:5173",
    )

    assert settings.database_url == "mysql+pymysql://user:pass@db:3306/ehr_agents"
    assert settings.cors_origin_list == ["http://localhost:5173"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_config.py -v`
Expected: FAIL because `app.shared.config` does not exist.

- [ ] **Step 3: Implement backend shell**

Implement `Settings` with Pydantic Settings, SQLAlchemy engine/session helpers, JSON error helpers, and a FastAPI app with `/health` and `/ready`.

`apps/api/app/main.py` must expose `app = create_app()` and register exception handlers.

`apps/api/tests/conftest.py` must define the shared test harness used by all backend tests:

- `test_settings`: creates Settings with SQLite test URL unless a test explicitly needs MySQL.
- `db_session`: creates all SQLAlchemy metadata in an isolated temporary SQLite database, yields a session, then drops metadata.
- `client`: builds the FastAPI app with dependency overrides for `get_db` and test settings.
- `hrbp_token` and `admin_token`: seed local users through `seed_local_users(db_session)`, log in with the test client, and return bearer tokens.
- `auth_headers`: returns HRBP `Authorization` headers.
- `fake_chat_adapter`: returns deterministic assistant text and avoids real provider calls in unit tests.

Avoid module-level database connections in tests; all DB access must go through these fixtures.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Run smoke test**

Run: `cd apps/api && uvicorn app.main:app --port 8000`
Expected: server starts; `curl http://localhost:8000/health` returns `{"status":"ok"}`.

### Task 3: Add database models and migrations

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/20260508_0001_initial.py`
- Create: `apps/api/app/auth/models.py`
- Create: `apps/api/app/skills/models.py`
- Create: `apps/api/app/conversations/models.py`
- Create: `apps/api/app/models/models.py`
- Create: `apps/api/app/agents/models.py`

- [ ] **Step 1: Write schema import test**

Create `apps/api/tests/test_schema_imports.py`:

```python
from app.auth.models import User
from app.skills.models import Skill, UserSkill
from app.conversations.models import Conversation, Message
from app.models.models import ModelConfig
from app.agents.models import AgentRun, ToolInvocation


def test_all_models_define_tables():
    assert User.__tablename__ == "users"
    assert Skill.__tablename__ == "skills"
    assert UserSkill.__tablename__ == "user_skills"
    assert Conversation.__tablename__ == "conversations"
    assert Message.__tablename__ == "messages"
    assert ModelConfig.__tablename__ == "model_configs"
    assert AgentRun.__tablename__ == "agent_runs"
    assert ToolInvocation.__tablename__ == "tool_invocations"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_schema_imports.py -v`
Expected: FAIL because models are missing.

- [ ] **Step 3: Implement SQLAlchemy models and migration**

Define MVP columns for all tables in the spec, including `model_configs`. Use string UUID primary keys generated by application code, `created_at`, and JSON columns where structured tool output is needed. `ModelConfig` should store provider id, display name, default model name, enabled flag, and non-secret metadata only; API keys must stay in environment variables.

- [ ] **Step 4: Run schema tests**

Run: `cd apps/api && pytest tests/test_schema_imports.py -v`
Expected: PASS.

- [ ] **Step 5: Run migrations against MySQL**

Run: `docker compose up -d mysql && cd apps/api && alembic upgrade head`
Expected: migration completes and creates MVP tables.

---

## Chunk 2: Backend Features

### Task 4: Implement local auth

**Files:**
- Create: `apps/api/app/auth/schemas.py`
- Create: `apps/api/app/auth/service.py`
- Create: `apps/api/app/auth/router.py`
- Create: `apps/api/app/shared/seed.py`
- Modify: `apps/api/app/shared/auth.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_auth.py`

- [ ] **Step 1: Write failing auth tests**

`test_auth.py` should assert that `POST /api/auth/login` accepts `hrbp@example.com` and `admin@example.com`, returns a bearer token, and `GET /api/me` returns the current user when the token is provided.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_auth.py -v`
Expected: FAIL with 404 or missing router.

- [ ] **Step 3: Implement auth**

Implement `seed_local_users(db)` in `shared/seed.py`. It must upsert exactly two local users if absent: `hrbp@example.com` with role `hrbp`, and `admin@example.com` with role `admin`. Run this seeding from FastAPI startup and from tests through the `hrbp_token`/`admin_token` fixtures. Do not run seeding as an import-time side effect.

Use JWT signed with `JWT_SECRET`, with claims `sub`, `email`, and `role`. Add `get_current_user` dependency in `shared/auth.py`.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_auth.py -v`
Expected: PASS.

### Task 5: Implement skill catalog and installation

**Files:**
- Create: `apps/api/app/skills/catalog.py`
- Create: `apps/api/app/skills/schemas.py`
- Create: `apps/api/app/skills/service.py`
- Create: `apps/api/app/skills/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_skills.py`

- [ ] **Step 1: Write failing skills tests**

Assert that authenticated users can list four recruitment skills, install `generate_jd`, see `installed: true`, and uninstall it.

- [ ] **Step 2: Run failing test**

Run: `cd apps/api && pytest tests/test_skills.py -v`
Expected: FAIL because endpoints are missing.

- [ ] **Step 3: Implement catalog and installation service**

Keep built-in skill definitions in `catalog.py`, upsert them into the `skills` table on app startup or first list call, and store per-user installation in `user_skills`.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_skills.py -v`
Expected: PASS.

### Task 6: Implement model metadata and adapters

**Files:**
- Create: `apps/api/app/models/schemas.py`
- Create: `apps/api/app/models/adapters.py`
- Create: `apps/api/app/models/models.py`
- Create: `apps/api/app/models/service.py`
- Create: `apps/api/app/models/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

Assert that `/api/models` returns DeepSeek and OpenAI entries, with `configured` based on whether API keys are present.

- [ ] **Step 2: Run failing test**

Run: `cd apps/api && pytest tests/test_models.py -v`
Expected: FAIL because endpoint is missing.

- [ ] **Step 3: Implement model service and adapters**

Implement a provider-neutral `ChatModelAdapter` protocol, adapters for DeepSeek and OpenAI, and a `ModelConfig` persistence service that upserts the supported provider metadata without storing secrets. Do not call provider APIs from unit tests; inject fake adapters in agent tests.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_models.py -v`
Expected: PASS.

### Task 7: Implement conversations and messages

**Files:**
- Create: `apps/api/app/conversations/schemas.py`
- Create: `apps/api/app/conversations/service.py`
- Create: `apps/api/app/conversations/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_conversations.py`

- [ ] **Step 1: Write failing conversation tests**

Assert authenticated users can create a conversation, list their conversations, and list messages for a conversation.

- [ ] **Step 2: Run failing test**

Run: `cd apps/api && pytest tests/test_conversations.py -v`
Expected: FAIL because endpoints are missing.

- [ ] **Step 3: Implement conversation service**

Ensure users only access their own conversations. Store user messages and assistant messages with roles `user` and `assistant`.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_conversations.py -v`
Expected: PASS.

### Task 8: Implement mock MCP tools

**Files:**
- Create: `apps/api/app/mock_mcp/schemas.py`
- Create: `apps/api/app/mock_mcp/tools.py`
- Test: `apps/api/tests/test_mock_mcp.py`

- [ ] **Step 1: Write failing mock tool tests**

Assert `generate_jd`, `screen_resume`, `generate_interview_questions`, and `summarize_interview_feedback` return typed structured data with expected top-level fields.

- [ ] **Step 2: Run failing test**

Run: `cd apps/api && pytest tests/test_mock_mcp.py -v`
Expected: FAIL because module is missing.

- [ ] **Step 3: Implement deterministic tools**

Return useful recruitment content derived from input text. Keep the tool interface independent from LangGraph so a real MCP client can replace it later.

- [ ] **Step 4: Run tests**

Run: `cd apps/api && pytest tests/test_mock_mcp.py -v`
Expected: PASS.

---

## Chunk 3: Agent Graph and Streaming

### Task 9: Implement LangGraph run orchestration

**Files:**
- Create: `apps/api/app/agents/schemas.py`
- Create: `apps/api/app/agents/stream.py`
- Create: `apps/api/app/agents/graph.py`
- Create: `apps/api/app/agents/service.py`
- Create: `apps/api/app/agents/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_agent_runs.py`

- [ ] **Step 1: Write failing agent tests**

Assert that `POST /api/agent/runs` rejects uninstalled skills, creates a run for an installed skill, stores the user message, invokes the mock tool, stores the structured output, and can stream at least `run_started` and `run_completed` events.

- [ ] **Step 2: Run failing test**

Run: `cd apps/api && pytest tests/test_agent_runs.py -v`
Expected: FAIL because agent endpoints are missing.

- [ ] **Step 3: Implement run service boundaries**

Create service functions for run lifecycle only: create the run record, save the user message, validate selected model and installed skill, expose an in-memory event queue for MVP SSE, and call the LangGraph graph. Do not duplicate tool/model orchestration in the service.

- [ ] **Step 4: Implement LangGraph wrapper**

Represent the full orchestration flow as named graph nodes: `load_context`, `select_skill`, `invoke_mock_mcp_tool`, `call_model`, `persist_result`. The graph is the only layer that calls mock MCP tools, calls model adapters, saves assistant messages, and stores tool invocation records. Keep graph state typed with Pydantic or TypedDict.

- [ ] **Step 5: Implement SSE route**

`GET /api/agent/runs/{run_id}/events` should return `text/event-stream` and emit named events in the spec. Authenticate this route with `token` query parameter for MVP browser compatibility because native `EventSource` cannot set headers. Reuse the same JWT verification as `get_current_user`, verify the run belongs to the authenticated user before streaming, and reject invalid tokens or cross-user runs with 401/403. Include a timeout/completion path so clients do not hang forever.

- [ ] **Step 6: Run tests**

Run: `cd apps/api && pytest tests/test_agent_runs.py -v`
Expected: PASS.

### Task 10: Backend integration verification

**Files:**
- Modify as needed based on failures only.

- [ ] **Step 1: Run full backend test suite**

Run: `cd apps/api && pytest -v`
Expected: all tests PASS.

- [ ] **Step 2: Run backend server**

Run: `cd apps/api && uvicorn app.main:app --reload --port 8000`
Expected: server starts without config or import errors.

- [ ] **Step 3: Smoke test critical endpoints**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`.

Run login, skill list, and model list with curl or HTTP client.
Expected: endpoints return JSON without 500 errors.

---

## Chunk 4: Frontend Foundation and UI

### Task 11: Scaffold Vite React app

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/index.html`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/tsconfig.node.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/src/env.d.ts`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/styles.css`

- [ ] **Step 1: Create frontend scaffold**

Use Vite React TypeScript dependencies. Include scripts: `dev`, `build`, `preview`, `typecheck`.

- [ ] **Step 2: Build check**

Run: `cd apps/web && npm install && npm run build`
Expected: production build succeeds.

### Task 12: Implement frontend API clients

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/sse.ts`
- Create: `apps/web/src/lib/errors.ts`
- Create: `apps/web/src/features/skills/skillsApi.ts`
- Create: `apps/web/src/features/models/modelApi.ts`
- Create: `apps/web/src/features/conversations/conversationApi.ts`
- Create: `apps/web/src/features/agent/agentApi.ts`

- [ ] **Step 1: Write API client code**

Implement a typed `api<T>()` wrapper using `import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"`, bearer token support, JSON parsing, and user-friendly error mapping.

- [ ] **Step 2: Add SSE helper**

Implement `subscribeToRunEvents(runId, token, handlers)` using `EventSource` or fetch streaming. If using native `EventSource`, pass token via a short-lived query token or choose fetch streaming because EventSource cannot set headers.

- [ ] **Step 3: Typecheck**

Run: `cd apps/web && npm run typecheck`
Expected: PASS.

### Task 13: Implement login and auth state

**Files:**
- Create: `apps/web/src/features/auth/authStore.tsx`
- Create: `apps/web/src/features/auth/LoginPage.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Implement auth store**

Store token and current user in React context. Persist token in `sessionStorage` for MVP only.

- [ ] **Step 2: Implement login page**

Show HRBP and Admin quick-login cards. Submit credentials to `/api/auth/login`, then load `/api/me`.

- [ ] **Step 3: Build check**

Run: `cd apps/web && npm run build`
Expected: PASS.

### Task 14: Implement recruitment Agent workspace

**Files:**
- Create: `apps/web/src/features/agent/types.ts`
- Create: `apps/web/src/features/agent/Sidebar.tsx`
- Create: `apps/web/src/features/agent/ChatPanel.tsx`
- Create: `apps/web/src/features/agent/ResultPanel.tsx`
- Create: `apps/web/src/features/agent/AgentWorkspace.tsx`
- Create: `apps/web/src/features/skills/SkillsMarketplace.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Implement workspace layout**

Create a responsive three-column layout. Collapse side panels gracefully on small screens.

- [ ] **Step 2: Implement marketplace and installation UI**

Fetch skills, show installed state, and call install/uninstall endpoints. Installed skills should appear in the sidebar.

- [ ] **Step 3: Implement model selector and conversation list**

Fetch `/api/models` and `/api/conversations`. Show configured status and warn when selected provider is not configured.

- [ ] **Step 4: Implement chat submission and streaming UI**

Create an agent run, append user message optimistically, subscribe to run events, append model deltas, and update execution status.

- [ ] **Step 5: Implement structured result panel**

Render `structured_result` events as copyable cards for JD, screening, interview questions, or feedback summary.

- [ ] **Step 6: Build check**

Run: `cd apps/web && npm run build`
Expected: PASS.

---

## Chunk 5: End-to-End Verification and Documentation

### Task 15: Full local verification

**Files:**
- Modify only if verification exposes defects.

- [ ] **Step 1: Start MySQL**

Run: `docker compose up -d mysql`
Expected: MySQL container is healthy.

- [ ] **Step 2: Run migrations**

Run: `cd apps/api && alembic upgrade head`
Expected: migration succeeds.

- [ ] **Step 3: Run backend tests**

Run: `cd apps/api && pytest -v`
Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run: `cd apps/web && npm run build`
Expected: PASS.

- [ ] **Step 5: Manual smoke test**

Run API: `cd apps/api && uvicorn app.main:app --port 8000`

Run web: `cd apps/web && npm run dev`

Expected manual flow:

1. Open `http://localhost:5173`.
2. Log in as HRBP.
3. Install a recruitment skill.
4. Select a configured DeepSeek or GPT model.
5. Create a conversation.
6. Submit a recruitment task.
7. Confirm streaming events appear.
8. Confirm right panel shows structured result.
9. Refresh and confirm history persists.

### Task 16: Update documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document setup**

Add commands for installing backend dependencies, installing frontend dependencies, starting MySQL, running migrations, starting API, starting web, and running tests.

- [ ] **Step 2: Document environment variables**

Explain that DeepSeek/OpenAI keys are required for real model calls and that no mock LLM fallback exists.

- [ ] **Step 3: Final verification**

Run: `cd apps/api && pytest -v && cd ../web && npm run build`
Expected: all checks PASS.

---

## Implementation Notes

- Use @test-driven-development while implementing features and bug fixes.
- Use @systematic-debugging if any test, migration, model call, SSE stream, or build behaves unexpectedly.
- Use @verification-before-completion before claiming the implementation is complete.
- Keep commits frequent if the repository is initialized during implementation. Do not create commits unless explicitly asked.
- Keep mock MCP tools isolated. Do not hide them inside the agent graph.
- Keep model API keys in environment variables only.
- Prefer small files with clear responsibilities over broad utility modules.

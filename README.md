# HR Agent MVP

Recruitment-focused HR Agent MVP with Vite React, FastAPI, LangGraph, and MySQL.

## MVP Scope

- **Skill marketplace** — browse and invoke recruitment skills (resume screening, JD generation, interview QA, candidate matching).
- **Recruitment skills** — resume screening, JD generation, interview QA, candidate matching.
- **Mock MCP tools** — simulated candidate database, email service, and assessment tools for development and testing.
- **Real LLM adapters** — DeepSeek and OpenAI backends for agent reasoning; no mock LLM fallback exists.

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker (for MySQL)

## Local Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `MYSQL_HOST` | MySQL host | `127.0.0.1` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_DATABASE` | MySQL database name | `ehr_agents` |
| `MYSQL_USER` | MySQL user | `ehr_agents` |
| `MYSQL_PASSWORD` | MySQL password | `ehr_agents` |
| `JWT_SECRET` | Secret for signing auth tokens | (required) |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173,http://127.0.0.1:5173` |
| `DEEPSEEK_API_KEY` | DeepSeek API key | (required for real model calls) |
| `DEEPSEEK_MODEL` | DeepSeek model name | `deepseek-chat` |
| `OPENAI_API_KEY` | OpenAI API key | (required for real model calls) |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o-mini` |
| `MINIMAX_API_KEY` | Minimax API key | (required for Minimax model calls) |
| `MINIMAX_BASE_URL` | Minimax OpenAI-compatible base URL | `https://api.minimax.chat/v1` |
| `MINIMAX_MODEL` | Minimax model name | `MiniMax-M1` |

**Important:** DeepSeek, OpenAI, and Minimax calls use real provider APIs. At least one provider API key is required for agent runs. No mock LLM fallback exists.

### 2. Start MySQL

```bash
docker compose up -d mysql
# Wait for MySQL to become healthy before running migrations:
docker compose ps mysql
```

### 3. Backend (API)

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8010
```

### 4. Frontend (Web)

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

The app will be available at `http://localhost:5173`. The web app points to `http://127.0.0.1:8010` by default through `apps/web/.env.example`.

If login returns `404` or `405`, another service is likely using the API port. Check with:

```bash
lsof -nP -iTCP:8010 -sTCP:LISTEN
```

## Test Accounts

| Email              | Password    | Role  |
|--------------------|-------------|-------|
| hrbp@example.com   | password123 | HRBP  |
| admin@example.com  | password123 | Admin |

## Verification

```bash
# Backend tests
cd apps/api && pytest -v

# Frontend lint, typecheck, and build
cd apps/web && npm run lint && npm run typecheck && npm run build
```

## Known Limitations

- **Docker unavailable** in the current verification environment, so MySQL migration (`alembic upgrade head`) was not verified here. Users with Docker should run `docker compose up -d mysql` and `alembic upgrade head` before starting the API server.

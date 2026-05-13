# HR Agent Project TODO

This list captures the next work items after the MVP. Work through items from top to bottom unless a production issue blocks usage.

## P0 - Stabilize Current MVP

- [x] Add a proper Alembic migration for skill ownership fields instead of relying on manual SQL.
  - Context: `skills` now needs `owner_user_id`, `visibility`, and `source`.
  - Acceptance: existing MySQL databases can run `alembic upgrade head` without manual table edits.
- [x] Restart and verify the correct API service is bound to port `8010`.
  - Context: moved to `8010` to avoid conflicts; documented port conflict recovery.
- [x] Commit and push the private/shared skill management changes.
  - Committed: `6edf6f3`, `1d7296a`. Remote is updated.
- [x] Make local dev ports configurable and document conflict recovery.
  - Context: consider moving API to `8010` or documenting how to kill conflicting processes.
  - Acceptance: README includes a reliable startup path and frontend API URL override.

## P1 - Remove Mock Tool Execution

- [ ] Replace `mock_mcp` with a real MCP client integration.
  - Context: Timeline events are real, but tool execution is currently local mock logic.
  - Acceptance: skills invoke tools through MCP client calls, not `app/mock_mcp/tools.py`.
- [ ] Define a skill manifest format.
  - Include: `skill_id`, name, description, visibility, version, prompts, MCP server/tool binding, input schema.
  - Acceptance: skill creation stores manifest fields and validates required tool bindings.
- [ ] Add MCP server registration/configuration.
  - Context: built-in MCP tools should be configured for all users; private/admin skills can bind to allowed tools.
  - Acceptance: backend can list available MCP tools and validate a skill's selected tool exists.
- [ ] Persist tool invocation payloads and outputs for audit.
  - Context: UI already shows Tool Invocation Evidence; backend should provide durable evidence.
  - Acceptance: run detail API can return tool name, input, output, start/end time, and status.

## P1 - Skill Management

- [ ] Finish private/shared skill UX.
  - Context: Marketplace now has a basic create/edit/delete form.
  - Acceptance: user can create private skills, admin can create shared skills, labels and permissions are clear.
- [x] Add tool selector and prompt editor to skill creation.
  - Committed: `1d7296a`. Creator can choose tool binding; LLM now uses tool output as context.
- [ ] Add versioning for user/admin skills.
  - Acceptance: updating a skill creates a new version or records updated metadata without breaking old runs.
- [ ] Add delete/archive rules.
  - Context: system skills cannot be deleted; user skills should be archived if already used by runs.
  - Acceptance: no historical agent run points to missing skill metadata.

## P1 - Real HR Data

- [ ] Add candidate and job requisition data models.
  - Acceptance: JD generation and screening can reference persisted job/candidate records.
- [ ] Add resume upload and parsing flow.
  - Acceptance: user can upload a resume, parse text, and run screening against a job.
- [ ] Add interview feedback records.
  - Acceptance: feedback summary skill can use stored interviewer notes.
- [ ] Add HR policy or recruiting knowledge source.
  - Acceptance: agent can answer questions using a controlled knowledge source rather than only prompt context.

## P2 - Agent Runtime Hardening

- [ ] Convert agent orchestration to explicit LangGraph `StateGraph`.
  - Acceptance: graph nodes are declared and testable as graph state transitions.
- [ ] Persist SSE/event history in MySQL.
  - Context: current event history is in memory.
  - Acceptance: timeline can be reconstructed after API restart.
- [ ] Add background job queue for agent runs.
  - Acceptance: long model/tool calls do not depend on FastAPI in-process background tasks.
- [ ] Add cancellation support.
  - Acceptance: clicking Stop marks the run cancelled and stops further tool/model work when possible.
- [ ] Add run timeout and retry policies.
  - Acceptance: stuck runs are marked failed with clear reason.

## P2 - Auth, RBAC, and Audit

- [ ] Replace local test auth with enterprise-ready auth option.
  - Options: SSO/OIDC, session + refresh token, or company identity provider.
- [ ] Add fine-grained RBAC.
  - Roles: HRBP, Admin, Skill Publisher, Auditor.
- [ ] Add audit logs.
  - Acceptance: skill create/update/delete/install/run events are recorded with actor and timestamp.
- [ ] Add tenant or organization boundary if multiple HR teams will use the system.

## P2 - Model Operations

- [ ] Add provider configuration UI for DeepSeek, OpenAI, and Minimax.
  - Acceptance: admin can test provider connectivity without editing `.env`.
- [ ] Add model parameters per provider.
  - Include: model name, temperature, max tokens, base URL.
- [ ] Add model usage tracking.
  - Acceptance: record provider, model, latency, token usage if available, and failure reason.
- [ ] Add provider health checks.
  - Acceptance: model selector clearly shows available/unavailable providers.

## P2 - Frontend Quality

- [ ] Add browser E2E tests.
  - Acceptance: Playwright covers login, install skill, run agent, view timeline/evidence.
- [ ] Improve Marketplace management UI.
  - Acceptance: create/edit/delete are clearer than the current compact MVP form.
- [ ] Add empty/error states for every API failure path.
- [ ] Add responsive QA for 320px, 768px, 1024px, and desktop layouts.

## P3 - Deployment and Operations

- [ ] Add Dockerfiles for API and Web.
- [ ] Add full Docker Compose for MySQL, API, and Web.
- [ ] Add CI pipeline.
  - Acceptance: backend tests, frontend lint/typecheck/build, and MySQL migration test run on PR.
- [ ] Add production readiness checks.
  - Include: `/ready` database check, CORS config, security headers, rate limits, structured logs.
- [ ] Add deployment documentation.
  - Include env vars, migration process, rollback process, and secret handling.

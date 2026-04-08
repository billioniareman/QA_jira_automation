## QA Knowledge Platform

Production-oriented backend for Jira ingestion, rule extraction, semantic retrieval, and AI chat orchestration.

### Current implementation status

- Core ingestion platform: **Implemented**
- Chat persistence schema (threads/messages/artifacts/checkpoints): **Implemented**
- LangGraph orchestration (Phase 2): **Implemented**
- Azure AI Search tool integration in orchestration: **Implemented**
- Jira action tools (create/update/comment/transition): **Planned (next phase)**
- Chat API endpoints: **Planned (next phase)**

---

## Tech stack

- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy + Alembic
- LangGraph + LangChain
- Azure OpenAI
- Azure AI Search (hybrid vector + keyword search)
- Langfuse (observability-ready)

---

## Core modules

### 1) Existing QA knowledge platform modules

- `Story`: Jira story persistence
- `Rule`: extracted business/validation rules
- `FrontendSignal`: frontend signal model
- `EntityLink`: story↔rule lineage

Services:
- `jira_service.py`: sample Jira ingestion flow
- `rule_engine.py`: acceptance criteria parsing and rule extraction
- `mapping.py`: Jira component → module/feature mapping
- `azure_search_service.py`: Azure AI Search indexing + retrieval

### 2) Chat agent extension modules

Persistence:
- `app/models/chat/thread.py`
	- `ChatThread`
	- `ChatMessage`
	- `ChatArtifact`
	- `ChatCheckpoint`
- Migration: `migrations/versions/f1a2b3c4d5e6_add_chat_schema.py`

Orchestration:
- `app/orchestration/state.py`: `AgentState`, `Intent`, `ToolCall`
- `app/orchestration/routing.py`: intent classification
- `app/orchestration/nodes.py`: routing/planning/tool execution/response nodes
- `app/orchestration/graph.py`: LangGraph assembly and execution

Tools:
- `app/tools/base.py`: base tool + registry
- `app/tools/azure_ai_search.py`: Azure AI Search chat tool
- `app/tools/registry.py`: default tool registration

Guardrails:
- input/output validation
- rate limiting
- tool-call limits per thread

---

## Azure AI Search integration (included)

The orchestration layer can call `azure_ai_search` to retrieve rules/knowledge using your existing Azure Search implementation.

Required environment variables:

- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

Optional runtime setup:

- call `create_index_if_not_exists()` once during bootstrap
- call `sync_dirty_rules_to_azure(db)` after ingestion jobs

---

## Existing API endpoints

Current endpoints under `/api/v1`:

- `POST /ingest/jira`
- `GET /stories/{jira_key}`
- `GET /rules/`

> Chat API endpoints are not yet wired; those are part of the next phase.

---

## Local setup

### 1) Create and activate environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment

Use `.env.example` (local) or `.env.azure.example` (Azure deployment) and set:

- `DATABASE_URL`
- Jira credentials
- Azure OpenAI settings
- Azure AI Search settings

### 4) Run migrations

```bash
alembic -c migrations/alembic.ini upgrade head
```

### 5) Start API

```bash
python main.py
```

Server starts on `http://127.0.0.1:5000`.

---

## Quick validation

Ingest sample data:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/ingest/jira
```

Fetch one story:

```bash
curl http://127.0.0.1:5000/api/v1/stories/BOOK-101
```

---

## Branch workflow (rebase on latest main)

Use this flow before opening or updating a PR so your branch sits on top of current `main`.

```bash
# 0) Ensure you are on your feature branch
git switch <feature-branch>

# 1) If you have uncommitted changes, stash them (including untracked files)
git stash push -u -m "pre-rebase"

# 2) Pull latest refs from remote
git fetch origin

# 3) Rebase your branch onto latest main
git rebase origin/main

# 4) Re-apply your local uncommitted work
git stash pop
```

If conflicts occur during rebase or stash pop, resolve conflicts, then continue with:

```bash
git add <resolved-files>
git rebase --continue
```

After a successful rebase, update your remote branch safely with:

```bash
git push --force-with-lease
```

---

## Additional docs

- `CHAT_ARCHITECTURE.md`
- `DEVELOPER_GUIDE.md`
- `QUICK_REFERENCE.md`
- `IMPLEMENTATION_SUMMARY.md`
- `DELIVERY_SUMMARY.md`
- `FILE_INDEX.md`

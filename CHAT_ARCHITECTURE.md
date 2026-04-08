# AI Chat Agent Architecture & Implementation Guide

## Executive Summary

This document outlines a production-ready, modular extension to your existing QA Knowledge Platform. We're adding an LLM-powered chat agent that orchestrates user requests, routes intent, executes Jira tools, persists conversation context, and returns clear final answers. The architecture preserves your existing foundation while layering new capabilities on top.

**Key Principle**: Build incrementally, keep boundaries clean, use PostgreSQL as the single source of truth for persistence.

---

## Proposed System Architecture

### High-Level Data Flow

```
User Request
    ↓
┌─────────────────────────────────────────┐
│  FastAPI Endpoint (chat/)               │
│  - Validates input                       │
│  - Looks up/creates session              │
│  - Enqueues chat job                     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  LangGraph Orchestrator                 │
│  - Routes intent (Jira vs General)      │
│  - Manages execution graph               │
│  - Stores checkpoints in PostgreSQL      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Planning Node                          │
│  - Breaks down user request             │
│  - Identifies required tools             │
│  - Creates execution plan                │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Tool Execution Node                    │
│  - Calls Jira tools                     │
│  - Handles errors gracefully             │
│  - Stores large outputs as artifacts     │
│  - Reports progress via Langfuse         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Final Response Node                    │
│  - Synthesizes answer via LLM           │
│  - References artifacts                  │
│  - Formats user-facing response          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Persistence Layer (PostgreSQL)         │
│  - Stores messages                       │
│  - Saves artifacts                       │
│  - Tracks checkpoint state               │
│  - Maintains thread history              │
└─────────────────────────────────────────┘
    ↓
User Response
```

### Layered Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI Routes                            │
│  (chat, status, async endpoints)                                 │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                  Chat & Session Management                       │
│  (session isolation, thread tracking, context lookup)            │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│              LangGraph Orchestration Layer                        │
│  (graph definition, routing, state management, checkpoints)      │
└──────────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────┬───────────────┬──────────────────┐
            ↓               ↓               ↓                  ↓
        ┌────────┐   ┌────────────┐   ┌──────────┐    ┌──────────────┐
        │Planning│   │ Jira Tools │   │ General  │    │Final Response│
        │ Node   │   │   Node     │   │ Chat     │    │   Node       │
        └────────┘   └────────────┘   └──────────┘    └──────────────┘
            ↓               ↓               ↓                  ↓
        ┌────────────────────────────────────────────────────────────┐
        │              Tool Registry & Execution                     │
        │  (dynamic tool loading, validation, guardrails)            │
        └────────────────────────────────────────────────────────────┘
            ↓
        ┌────────────────────────────────────────────────────────────┐
        │           Jira Integration Layer                           │
        │  (read issues, search JQL, create, update, comment)        │
        └────────────────────────────────────────────────────────────┘
            ↓
        ┌────────────────────────────────────────────────────────────┐
        │           Azure Integration Layer                          │
        │  (Azure OpenAI LLM, Key Vault secrets, managed identity)   │
        └────────────────────────────────────────────────────────────┘
            ↓
        ┌────────────────────────────────────────────────────────────┐
        │        Persistence & Observability Layer                   │
        │  (PostgreSQL, Langfuse tracing, checkpoints, artifacts)    │
        └────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
app/
├── __init__.py
├── db.py                              # (existing - extend for chat models)
├── extensions.py                      # (existing)
├── models/
│   ├── __init__.py                    # (existing)
│   ├── entity_link.py                 # (existing)
│   ├── frontend_signal.py             # (existing)
│   ├── rule.py                        # (existing)
│   ├── story.py                       # (existing)
│   └── chat/                          # NEW: Chat-specific models
│       ├── __init__.py
│       ├── thread.py                  # Chat thread (session)
│       ├── message.py                 # Message record
│       ├── artifact.py                # Large tool outputs
│       └── checkpoint.py              # LangGraph checkpoints
│
├── routes/
│   ├── __init__.py                    # (existing)
│   ├── endpoints.py                   # (existing)
│   └── chat.py                        # NEW: Chat API endpoints
│
├── services/
│   ├── __init__.py                    # (existing)
│   ├── azure_search_service.py        # (existing)
│   ├── jira_service.py                # (existing - extend if needed)
│   ├── mapping.py                     # (existing)
│   ├── rule_engine.py                 # (existing)
│   └── chat/                          # NEW: Chat service layer
│       ├── __init__.py
│       ├── session_manager.py         # Thread/session lifecycle
│       └── history_manager.py         # Conversation history retrieval
│
├── orchestration/                     # NEW: LangGraph orchestration
│   ├── __init__.py
│   ├── graph.py                       # Main LangGraph graph definition
│   ├── state.py                       # AgentState, schema
│   ├── nodes.py                       # Planning, tool exec, response nodes
│   └── routing.py                     # Intent routing logic
│
├── tools/                             # NEW: Tool registry & executors
│   ├── __init__.py
│   ├── registry.py                    # Tool registry
│   ├── base.py                        # BaseTool abstract class
│   ├── jira/                          # Jira tools
│   │   ├── __init__.py
│   │   ├── read_issue.py              # Get issue details
│   │   ├── search_issues.py           # JQL search
│   │   ├── create_issue.py            # Create new issue
│   │   ├── update_issue.py            # Update issue fields
│   │   ├── add_comment.py             # Add comment
│   │   ├── transition_issue.py        # Change status
│   │   └── normalizer.py              # Response normalization
│   └── guardrails.py                  # Tool validation, rate limiting
│
├── prompts/                           # NEW: Prompt templates & management
│   ├── __init__.py
│   ├── prompt_store.py                # Load/manage prompts
│   ├── routing.txt                    # Routing prompt
│   ├── planning.txt                   # Planning prompt
│   ├── jira_agent.txt                 # Jira-specific prompt
│   └── response_synthesis.txt         # Final response prompt
│
├── azure/                             # NEW: Azure integration
│   ├── __init__.py
│   ├── config.py                      # Azure service initialization
│   ├── llm.py                         # Azure OpenAI client
│   ├── secrets.py                     # Key Vault integration
│   └── monitoring.py                  # Application Insights / Azure Monitor
│
├── persistence/                       # NEW: State persistence
│   ├── __init__.py
│   ├── checkpoint_store.py            # LangGraph checkpoint persistence
│   ├── artifact_store.py              # Large output storage
│   └── memory.py                      # Optional RAG memory layer
│
└── guardrails/                        # NEW: Safety & validation
    ├── __init__.py
    ├── input_validation.py            # Sanitize user input
    ├── output_validation.py           # Check LLM output
    ├── rate_limiter.py                # Per-user/IP limits
    └── error_handlers.py              # Graceful error handling

migrations/                            # (existing - extend with chat schema)
├── alembic.ini
├── env.py
├── README
├── script.py.mako
└── versions/
    ├── (existing)
    └── *_add_chat_schema.py           # NEW: Chat table migrations

tests/                                 # NEW: Test suite
├── __init__.py
├── test_orchestration.py              # Graph and routing tests
├── test_tools.py                      # Tool execution tests
├── test_persistence.py                # Checkpoint and artifact tests
└── test_integration.py                # End-to-end tests

config.py                              # (existing - extend with new settings)
main.py                                # (existing - extend with chat routes)
requirements.txt                       # (existing - add chat dependencies)
.env.example                           # NEW: Example env file
.env.azure.example                     # NEW: Azure-specific env example
azure-setup.sh                         # NEW: Azure CLI setup script
azure-deploy.sh                        # NEW: Azure deployment script
CHAT_ARCHITECTURE.md                   # This file
```

---

## Implementation Phases

### Phase 1: Foundation (Days 1–2)
- ✅ Extend `config.py` with Azure OpenAI, Langfuse, PostgreSQL settings
- ✅ Update `requirements.txt` with LangGraph, LangChain, Langfuse, azure-openai
- ✅ Create database models for chat threads, messages, artifacts, checkpoints
- ✅ Create Alembic migration for chat schema
- ✅ Create session manager and history manager services
- ✅ Set up basic Azure integration (LLM client, Key Vault client)

### Phase 2: Orchestration & Routing (Days 2–3)
- ✅ Build LangGraph orchestration layer (graph definition, state, nodes)
- ✅ Implement intent routing (Jira vs general chat)
- ✅ Implement planning node (break down requests)
- ✅ Implement tool execution node (guardrails, error handling)
- ✅ Implement final response node (synthesize answers)

### Phase 3: Tool Integration (Days 3–4)
- ✅ Build tool registry and base tool class
- ✅ Implement Jira tools (read, search, create, update, comment, transition)
- ✅ Implement response normalization
- ✅ Add guardrails (validation, rate limiting, timeouts)
- ✅ Add artifact storage for large outputs

### Phase 4: Persistence & Observability (Days 4–5)
- ✅ Implement checkpoint store (LangGraph state persistence)
- ✅ Implement artifact store (large tool outputs)
- ✅ Integrate Langfuse for tracing and observability
- ✅ Set up Application Insights / Azure Monitor

### Phase 5: API & Integration (Days 5–6)
- ✅ Create FastAPI chat endpoints (chat, status, history)
- ✅ Implement async job handling (background tasks)
- ✅ Extend `main.py` to include chat routes
- ✅ Add basic input/output validation

### Phase 6: Tests & Documentation (Days 6–7)
- ✅ Write pytest tests (routing, tools, persistence, integration)
- ✅ Create developer documentation
- ✅ Create .env examples
- ✅ Create Azure setup and deployment scripts

---

## Key Design Decisions

### 1. **LangGraph Over Custom State Machine**
- **Why**: LangGraph provides production-grade orchestration, checkpoint management, and human-in-the-loop patterns out of the box.
- **Benefit**: Easier to extend with complex routing, retries, and parallel execution.

### 2. **PostgreSQL as Single Source of Truth**
- **Why**: Keeps your existing infrastructure; supports both conversation history and LangGraph checkpoints.
- **Benefit**: Deterministic, queryable state; easy debugging and recovery.

### 3. **Artifact Storage for Large Outputs**
- **Why**: Jira API responses can be large; storing in chat history bloats the database.
- **Benefit**: Messages reference artifacts; LLM can summarize large responses into concise summaries.

### 4. **Tool Registry Pattern**
- **Why**: Allows dynamic tool registration, easy testing, and future extensions (Slack, GitHub, etc.).
- **Benefit**: Loose coupling; new tools don't require touching the core graph.

### 5. **Langfuse for Observability**
- **Why**: Tracks LLM calls, tool execution, cost, latency, and enables prompt versioning.
- **Benefit**: Production debugging, cost analysis, and continuous improvement.

### 6. **Azure Managed Identity**
- **Why**: Secure secret handling without hardcoded credentials.
- **Benefit**: Works in local dev (via Azure CLI login), staging, and production.

### 7. **Prompt Templates as Versioned Artifacts**
- **Why**: Decouples LLM behavior from code; enables A/B testing and version control.
- **Benefit**: Langfuse can track prompt versions and their performance.

---

## Guardrails & Safety

### Input Guardrails
- Validate user message length (max 4096 chars)
- Check for injection patterns (SQL, command injection)
- Rate limit per user/IP (10 messages/min)
- Validate thread/session ownership

### Tool Guardrails
- Validate tool inputs against Pydantic schemas
- Timeout tool execution (30s default)
- Catch and log tool failures
- Prevent infinite loops (max 10 tool calls per message)
- Validate Jira responses for malformed data

### Output Guardrails
- Cap LLM response length (8192 chars)
- Sanitize Jira URLs and credentials from responses
- Check for oversized artifacts (max 10MB)
- Validate JSON responses before returning to user

### Error Handling Strategy
- **Tool failures**: Retry once, then gracefully degrade with user-friendly message
- **LLM timeouts**: Return partial response with "I ran out of time, here's what I found"
- **Database errors**: Log, alert, and return 500 with retry guidance
- **Missing secrets**: Fail early during app startup with clear error message

---

## Deployment Considerations

### Local Development
- Use `.env` with mock Azure credentials or local Azure SDK login
- PostgreSQL runs in Docker or local instance
- Langfuse runs locally or uses cloud endpoint
- Azure OpenAI accessed via Azure SDK (respects local auth)

### Azure Deployment
- Use Azure Container Apps or App Service
- PostgreSQL via Azure Database for PostgreSQL (managed)
- Secrets via Azure Key Vault
- LLM via Azure OpenAI (in same subscription)
- Monitoring via Application Insights
- Auth via Managed Identity

### Monitoring & Alerting
- Application Insights tracks HTTP requests, exceptions, dependencies
- Langfuse dashboard shows LLM performance, cost, latency
- Prometheus metrics exported for custom monitoring
- Alarms on error rates, latency spikes, tool timeouts

---

## Security Posture

| Concern | Mitigation |
|---------|-----------|
| Credential leakage | Use Azure Key Vault, managed identity, never log secrets |
| SQL injection | Use SQLAlchemy ORM, parameterized queries, input validation |
| Jira credential exposure | Separate Jira auth; never expose tokens in responses or logs |
| Unbound tool execution | Timeout, rate limit, artifact size limits |
| LLM prompt injection | Input sanitization, prompt templates, output validation |
| Unauthorized access | Thread/session ownership checks, user authentication |
| Data at rest | Encrypted PostgreSQL via TLS, backups encrypted |
| Data in transit | HTTPS only, TLS 1.2+ for all Azure APIs |

---

## Scalability & Performance

### Bottlenecks & Mitigations
| Bottleneck | Mitigation |
|-----------|-----------|
| LLM latency (30s+) | Async task queue, progress updates, client-side polling |
| Tool execution (Jira API) | Cache, batch JQL queries, async execution |
| Database connections | Connection pooling (SQLAlchemy), read replicas for history |
| Artifact storage | Compression, tiered storage (hot/cold), cleanup jobs |
| Message throughput | Redis for session cache, database indexing |

### Caching Strategy
- **Session cache**: Redis or in-memory (5min TTL)
- **Jira responses**: 1hr cache for non-mutable queries (search, read)
- **Artifacts**: PostgreSQL (no cache; large files are referenced, not re-fetched)
- **Prompts**: In-memory with file watch for reloads

### Horizontal Scaling
- Stateless FastAPI workers
- Shared PostgreSQL backend
- Distributed LangGraph checkpoints (PostgreSQL)
- Message broker for async jobs (Celery + Redis or Azure Service Bus)

---

## Next Steps

1. **Review & approve architecture** ← You are here
2. Execute Phase 1: Foundation (config, models, migrations)
3. Execute Phase 2: Orchestration (LangGraph, routing)
4. Execute Phase 3: Tool Integration (Jira tools, guardrails)
5. Execute Phase 4: Persistence (checkpoints, artifacts)
6. Execute Phase 5: API (endpoints, async jobs)
7. Execute Phase 6: Tests & documentation

Each phase includes checkpoints for validation before moving to the next.

---

## FAQs

**Q: Will this interfere with my existing endpoints?**
A: No. Chat routes are at `/api/v1/chat/*`. Existing routes remain unchanged.

**Q: Can I swap LangGraph for something else?**
A: Yes, but you'll lose checkpoint management, routing, and multi-step orchestration. LangGraph is highly recommended for this use case.

**Q: What if I don't have Azure OpenAI yet?**
A: Use `OpenAI` (non-Azure) in Phase 1 for testing. Switch to Azure OpenAI in Phase 4 without code changes (config-only).

**Q: How do I add a new Jira tool?**
A: Extend `app/tools/jira/` with a new tool class, register it in `app/tools/registry.py`, and add to routing prompt. No graph changes.

**Q: What's the learning curve?**
A: LangGraph is simple (5-10 calls to define a graph). LangChain is standard. Langfuse is optional but highly recommended. PostgreSQL is familiar.

**Q: Can I use this in production immediately?**
A: Yes, but follow the Azure deployment guide, set up monitoring, and load-test with realistic traffic patterns.


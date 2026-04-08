# Quick Reference Guide

## Project Structure at a Glance

```
QA_jira_automation/
├── app/
│   ├── models/
│   │   ├── existing/                  # Your existing models
│   │   └── chat/                      # NEW: ChatThread, ChatMessage, ChatArtifact, ChatCheckpoint
│   ├── services/
│   │   ├── existing/                  # Your existing services
│   │   └── chat/                      # NEW: SessionManager, HistoryManager
│   ├── routes/
│   │   ├── endpoints.py               # Your existing endpoints
│   │   └── chat.py                    # NEW: Chat API routes (Phase 5)
│   ├── orchestration/                 # NEW: LangGraph orchestration
│   │   ├── state.py                   # Agent state, Intent enum
│   │   ├── graph.py                   # Graph definition (Phase 2)
│   │   ├── nodes.py                   # Node implementations (Phase 2)
│   │   └── routing.py                 # Routing logic (Phase 2)
│   ├── tools/                         # NEW: Tool registry
│   │   ├── base.py                    # BaseTool, ToolRegistry
│   │   ├── registry.py                # Tool registry singleton
│   │   └── jira/                      # Jira tools (Phase 3)
│   ├── prompts/                       # NEW: Prompt templates
│   │   ├── prompt_store.py            # PromptStore loader
│   │   ├── routing.txt                # Routing prompt
│   │   ├── planning.txt               # Planning prompt
│   │   ├── jira_agent.txt             # Jira-specific prompt
│   │   └── response_synthesis.txt     # Response prompt
│   ├── azure/                         # NEW: Azure integration
│   │   ├── config.py                  # Azure service manager
│   │   ├── llm.py                     # LLM client
│   │   └── secrets.py                 # Key Vault integration
│   ├── persistence/                   # NEW: Persistence layer
│   │   ├── checkpoint_store.py        # Checkpoints (Phase 4)
│   │   └── artifact_store.py          # Artifacts (Phase 4)
│   └── guardrails/                    # NEW: Safety & validation
│       ├── guardrails.py              # Rate limiting, validators
│       └── __init__.py
├── migrations/
│   └── versions/
│       └── f1a2b3c4d5e6_add_chat_schema.py  # NEW: Chat schema
├── tests/                             # NEW: Test suite
│   ├── test_orchestration.py          # State, routing tests
│   ├── test_tools.py                  # Tool registry tests
│   ├── test_persistence.py            # Persistence tests
│   └── test_guardrails.py             # Safety tests
├── config.py                          # EXTENDED: New settings
├── main.py                            # WILL EXTEND: Add chat routes
├── requirements.txt                   # EXTENDED: New dependencies
├── Dockerfile                         # NEW: Production container
├── .env.example                       # NEW: Local dev env
├── .env.azure.example                 # NEW: Azure prod env
├── azure-setup.sh                     # NEW: Resource provisioning
├── azure-deploy.sh                    # NEW: Deployment automation
├── CHAT_ARCHITECTURE.md               # NEW: System design (500+ lines)
├── DEVELOPER_GUIDE.md                 # NEW: Developer docs (400+ lines)
└── IMPLEMENTATION_SUMMARY.md          # NEW: This summary
```

## Configuration Priority

### Local Development (`.env`)
```bash
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://xyz.openai.azure.com
DATABASE_URL=postgresql://localhost:5432/qa_knowledge
LANGFUSE_ENABLED=true
```

### Production (Azure)
```bash
AZURE_OPENAI_API_KEY=<from-key-vault>
DATABASE_URL=<azure-postgresql>
AZURE_KEYVAULT_URL=<key-vault-url>
MONITORING_ENABLED=true
```

## Key Classes & How to Use

### SessionManager
```python
from app.services.chat import SessionManager
from app.db import get_db

db = get_db()
thread = SessionManager.create_thread(db, user_id="user-123")
threads = SessionManager.list_threads(db, user_id="user-123")
archived = SessionManager.archive_thread(db, thread_id=thread.thread_id)
```

### HistoryManager
```python
from app.services.chat import HistoryManager

message = HistoryManager.add_message(
    db=db,
    thread_pk=thread.id,
    sender_role="user",
    content="Your message",
)
history = HistoryManager.get_thread_history(db=db, thread_pk=thread.id)
artifact = HistoryManager.store_artifact(db=db, thread_pk=thread.id, ...)
```

### Tool Registry
```python
from app.tools import get_tool_registry

registry = get_tool_registry()
registry.register(my_tool)
result = await registry.execute_tool("tool_name", **kwargs)
schemas = registry.get_openai_tools_schema()
```

### Guardrails
```python
from app.guardrails import input_validator, output_validator, rate_limiter

valid, error = input_validator.validate_message(user_message)
valid, error = output_validator.validate_response(llm_response)
allowed = rate_limiter.check_user_limit(user_id)
```

### Azure LLM
```python
from app.azure import get_llm

llm = get_llm()  # Returns AzureChatOpenAI or ChatOpenAI
response = llm.invoke([{"role": "user", "content": "..."}])
```

## Common Tasks

### Add a New Jira Tool
1. Create `app/tools/jira/your_tool.py` extending `BaseTool`
2. Register in app initialization:
   ```python
   from app.tools.registry import get_tool_registry
   registry = get_tool_registry()
   registry.register(YourTool())
   ```
3. Update routing prompt

### Run Tests
```bash
pytest tests/ -v
pytest tests/test_tools.py::TestToolRegistry::test_register_tool -v
pytest --cov=app tests/
```

### Create Database Migration
```bash
# After modifying models
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Debug Agent State
```python
from app.orchestration import AgentState

state = AgentState(user_message="...", thread_id="...", user_id="...")
state.add_execution_step("Step 1")
print(state.to_dict())  # View as JSON
```

### Setup Azure Resources
```bash
chmod +x azure-setup.sh
./azure-setup.sh
# Follow prompts to create resource group, OpenAI, DB, Key Vault
```

### Deploy to Azure
```bash
chmod +x azure-deploy.sh
./azure-deploy.sh
# Choose: app-service or container-apps
```

## API Endpoints (Phase 5)

```
POST   /api/v1/chat/send            Send message, get response
GET    /api/v1/chat/threads         List user threads
GET    /api/v1/chat/threads/{id}    Get thread details
GET    /api/v1/chat/artifacts/{id}  Get large output
GET    /api/v1/health               Health check
```

## Environment Variables Reference

| Var | Purpose | Example | Required |
|-----|---------|---------|----------|
| `AZURE_OPENAI_API_KEY` | LLM auth | `sk-...` | Yes (one of) |
| `AZURE_OPENAI_ENDPOINT` | LLM endpoint | `https://xyz.openai.azure.com` | Yes (one of) |
| `OPENAI_API_KEY` | Fallback LLM | `sk-...` | Yes (one of) |
| `DATABASE_URL` | PostgreSQL | `postgresql://...` | Yes |
| `LANGFUSE_ENABLED` | Enable tracing | `true` | No (default: true) |
| `LANGFUSE_PUBLIC_KEY` | Langfuse auth | `pk-...` | If enabled |
| `CHAT_MAX_TOOL_CALLS` | Tool limit | `10` | No (default: 10) |
| `RATE_LIMIT_MESSAGES_PER_MINUTE` | User rate limit | `10` | No (default: 10) |

## Testing Strategy

**Unit Tests**: Test individual components (tools, validators, state)
```bash
pytest tests/test_tools.py
pytest tests/test_guardrails.py
```

**Integration Tests**: Test component interactions
```bash
pytest tests/test_persistence.py
```

**E2E Tests**: Test full chat flow (Phase 5)
```bash
pytest tests/test_integration.py
```

## Performance Tips

1. **Connection pooling**: SQLAlchemy auto-manages (tuned in config)
2. **Artifact compression**: Enabled by default (gzip for large outputs)
3. **Rate limiting**: Per-user (10/min) prevents abuse
4. **Tool timeout**: 30s default, configurable per tool
5. **Message caching**: LLM responses cached in database

## Troubleshooting

### "No LLM configured"
- Set `AZURE_OPENAI_API_KEY` or `OPENAI_API_KEY`

### PostgreSQL connection refused
- Ensure database running: `brew services start postgresql@14`
- Check `DATABASE_URL` format

### Tool not found
- Ensure registered: `registry.register(my_tool)`
- Check tool name matches in LLM response

### Langfuse not tracing
- Verify `LANGFUSE_ENABLED=true`
- Check `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`

### Rate limit too strict
- Increase `RATE_LIMIT_MESSAGES_PER_MINUTE`

## Phase Checklist

### Phase 1 ✅
- [x] Extended config
- [x] Updated requirements.txt
- [x] Created chat models
- [x] Created migrations
- [x] Created services
- [x] Set up Azure integration

### Phase 2 (Next)
- [ ] Create `app/orchestration/graph.py`
- [ ] Implement routing node
- [ ] Implement planning node
- [ ] Implement tool execution node
- [ ] Implement response node
- [ ] Test graph execution

### Phase 3
- [ ] Implement Jira read_issue tool
- [ ] Implement Jira search_issues tool
- [ ] Implement Jira create_issue tool
- [ ] Add response normalization
- [ ] Update routing prompts

### Phase 4
- [ ] Implement checkpoint store
- [ ] Implement artifact store utilities
- [ ] Integrate Langfuse
- [ ] Add Application Insights

### Phase 5
- [ ] Create chat API routes
- [ ] Implement async job handling
- [ ] Extend main.py
- [ ] Add input/output validation

### Phase 6 ✅
- [x] Write tests
- [x] Write documentation
- [x] Create deployment scripts

## Resources

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **LangChain**: https://python.langchain.com/
- **Langfuse**: https://langfuse.com/docs
- **Azure OpenAI**: https://learn.microsoft.com/azure/cognitive-services/openai/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/

## Support Files

- `CHAT_ARCHITECTURE.md` - Design decisions and system architecture
- `DEVELOPER_GUIDE.md` - Detailed implementation guide
- `IMPLEMENTATION_SUMMARY.md` - Status and roadmap

---

**Status**: Phase 1 ✅ Complete | Phase 2 (Orchestration) Ready to Start


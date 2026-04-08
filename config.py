import os
from dotenv import load_dotenv
from typing import Optional, Literal

load_dotenv()


class Settings:
    # ── Existing Settings ──────────────────────────────────────────────
    DATABASE_URL = os.environ.get(
        'DATABASE_URL'
    ) or 'postgresql+psycopg://postgres:postgres@localhost:5432/qa_knowledge'
    JIRA_BASE_URL = os.environ.get('JIRA_BASE_URL', 'https://your-domain.atlassian.net')
    JIRA_USERNAME = os.environ.get('JIRA_USERNAME', 'mock_user')
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN', 'mock_token')
    AZURE_SEARCH_ENDPOINT = os.environ.get('AZURE_SEARCH_ENDPOINT', '')
    AZURE_SEARCH_API_KEY = os.environ.get('AZURE_SEARCH_API_KEY', '')
    AZURE_SEARCH_INDEX_NAME = os.environ.get('AZURE_SEARCH_INDEX_NAME', 'qa-knowledge-rules')

    # ── API Configuration ──────────────────────────────────────────────
    API_PREFIX = '/api/v1'
    APP_NAME = 'QA Knowledge Platform API'

    # ── Azure OpenAI LLM Configuration ─────────────────────────────────
    # Use Azure OpenAI if configured, otherwise fall back to OpenAI
    AZURE_OPENAI_API_KEY: Optional[str] = os.environ.get('AZURE_OPENAI_API_KEY')
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.environ.get('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
    AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
    AZURE_OPENAI_MODEL_NAME = os.environ.get('AZURE_OPENAI_MODEL_NAME', 'gpt-4')

    # Fallback to standard OpenAI if Azure not configured
    OPENAI_API_KEY: Optional[str] = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL_NAME = os.environ.get('OPENAI_MODEL_NAME', 'gpt-4')

    # ── LLM Behavior ───────────────────────────────────────────────────
    LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.7'))
    LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS', '2048'))
    LLM_TIMEOUT_SECONDS = int(os.environ.get('LLM_TIMEOUT_SECONDS', '30'))

    # ── Azure Identity & Key Vault ────────────────────────────────────
    AZURE_TENANT_ID: Optional[str] = os.environ.get('AZURE_TENANT_ID')
    AZURE_CLIENT_ID: Optional[str] = os.environ.get('AZURE_CLIENT_ID')
    AZURE_CLIENT_SECRET: Optional[str] = os.environ.get('AZURE_CLIENT_SECRET')
    AZURE_SUBSCRIPTION_ID: Optional[str] = os.environ.get('AZURE_SUBSCRIPTION_ID')
    AZURE_KEYVAULT_URL: Optional[str] = os.environ.get('AZURE_KEYVAULT_URL')

    # ── Chat Configuration ─────────────────────────────────────────────
    CHAT_MAX_HISTORY_MESSAGES = int(os.environ.get('CHAT_MAX_HISTORY_MESSAGES', '20'))
    CHAT_MAX_INPUT_LENGTH = int(os.environ.get('CHAT_MAX_INPUT_LENGTH', '4096'))
    CHAT_MAX_OUTPUT_LENGTH = int(os.environ.get('CHAT_MAX_OUTPUT_LENGTH', '8192'))
    CHAT_MAX_TOOL_CALLS = int(os.environ.get('CHAT_MAX_TOOL_CALLS', '10'))
    CHAT_TOOL_TIMEOUT_SECONDS = int(os.environ.get('CHAT_TOOL_TIMEOUT_SECONDS', '30'))

    # ── Rate Limiting ──────────────────────────────────────────────────
    RATE_LIMIT_MESSAGES_PER_MINUTE = int(
        os.environ.get('RATE_LIMIT_MESSAGES_PER_MINUTE', '10')
    )
    RATE_LIMIT_MESSAGES_PER_HOUR = int(
        os.environ.get('RATE_LIMIT_MESSAGES_PER_HOUR', '100')
    )

    # ── Artifact Storage ───────────────────────────────────────────────
    ARTIFACT_MAX_SIZE_MB = int(os.environ.get('ARTIFACT_MAX_SIZE_MB', '10'))
    ARTIFACT_COMPRESSION_ENABLED = os.environ.get('ARTIFACT_COMPRESSION_ENABLED', 'true').lower() == 'true'

    # ── Langfuse Observability ────────────────────────────────────────
    LANGFUSE_ENABLED = os.environ.get('LANGFUSE_ENABLED', 'true').lower() == 'true'
    LANGFUSE_PUBLIC_KEY: Optional[str] = os.environ.get('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_SECRET_KEY: Optional[str] = os.environ.get('LANGFUSE_SECRET_KEY')
    LANGFUSE_HOST: Optional[str] = os.environ.get('LANGFUSE_HOST', 'https://cloud.langfuse.com')

    # ── Application Insights / Azure Monitor ───────────────────────────
    AZURE_INSTRUMENTATION_KEY: Optional[str] = os.environ.get('AZURE_INSTRUMENTATION_KEY')
    MONITORING_ENABLED = os.environ.get('MONITORING_ENABLED', 'true').lower() == 'true'

    # ── Environment Detection ──────────────────────────────────────────
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    DEBUG = ENVIRONMENT == 'development'

    # ── Prompt Configuration ───────────────────────────────────────────
    PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'app', 'prompts')
    PROMPT_VERSION = os.environ.get('PROMPT_VERSION', 'v1')


settings = Settings()


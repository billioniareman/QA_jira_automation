"""Azure OpenAI LLM client initialization."""

import logging
from typing import Optional

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from config import settings
from .config import azure_service_manager


logger = logging.getLogger(__name__)

_llm_instance: Optional[object] = None


def get_llm():
    """
    Get or initialize the LLM client.
    
    Prefers Azure OpenAI if configured, falls back to OpenAI.
    
    Returns:
        LangChain LLM instance (AzureChatOpenAI or ChatOpenAI)
    """
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    # Try Azure OpenAI first
    if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
        try:
            logger.info(f'Initializing Azure OpenAI: {settings.AZURE_OPENAI_DEPLOYMENT_NAME}')
            _llm_instance = AzureChatOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                model_name=settings.AZURE_OPENAI_MODEL_NAME,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                request_timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            logger.info('Azure OpenAI LLM initialized successfully')
            return _llm_instance
        except Exception as e:
            logger.warning(f'Failed to initialize Azure OpenAI: {e}. Falling back to OpenAI.')

    # Fallback to standard OpenAI
    if settings.OPENAI_API_KEY:
        try:
            logger.info(f'Initializing OpenAI: {settings.OPENAI_MODEL_NAME}')
            _llm_instance = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL_NAME,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                request_timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            logger.info('OpenAI LLM initialized successfully')
            return _llm_instance
        except Exception as e:
            logger.error(f'Failed to initialize OpenAI: {e}')
            raise RuntimeError(
                'No LLM configured. Set AZURE_OPENAI_API_KEY or OPENAI_API_KEY in environment.'
            )

    raise RuntimeError(
        'No LLM configured. Set AZURE_OPENAI_API_KEY or OPENAI_API_KEY in environment.'
    )


def reset_llm():
    """Reset cached LLM instance (useful for testing)."""
    global _llm_instance
    _llm_instance = None

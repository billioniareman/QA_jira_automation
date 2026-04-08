"""Azure AI Search integration – FastAPI edition.

Uses ``config.settings`` directly instead of Flask ``current_app``.
All DB work uses an explicit SQLAlchemy ``Session`` passed in by the caller
so the request-scoped session is honoured.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from app.models.rule import Rule
from app.models.story import Story

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded embedding model (heavy import; only loaded on first use)
# ---------------------------------------------------------------------------
_model = None


def _get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embedding(text: str) -> list[float]:
    return _get_embedding_model().encode(text).tolist()


# ---------------------------------------------------------------------------
# Credentials helper
# ---------------------------------------------------------------------------

def _get_search_credentials() -> tuple[str, str, str]:
    return (
        settings.AZURE_SEARCH_ENDPOINT,
        settings.AZURE_SEARCH_API_KEY,
        settings.AZURE_SEARCH_INDEX_NAME,
    )


# ---------------------------------------------------------------------------
# Index provisioning
# ---------------------------------------------------------------------------

def create_index_if_not_exists() -> None:
    endpoint, key, index_name = _get_search_credentials()
    if not endpoint or not key:
        logger.warning("Azure Search credentials missing – skipping index creation.")
        return

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    credential = AzureKeyCredential(key)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

    try:
        index_client.get_index(index_name)
        logger.info("Index '%s' already exists.", index_name)
    except Exception:
        logger.info("Index '%s' not found – creating …", index_name)
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw",
                )
            ],
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="jira_key", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="module_filter", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="rule_type", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="source_type", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="verification_status", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=384,
                vector_search_profile_name="myHnswProfile",
            ),
        ]

        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        index_client.create_index(index)
        logger.info("Index '%s' created successfully.", index_name)


# ---------------------------------------------------------------------------
# Sync dirty (un-indexed) rules to Azure
# ---------------------------------------------------------------------------

def sync_dirty_rules_to_azure(db: Session) -> int:
    """Push un-indexed rules to Azure AI Search.

    Returns the number of documents successfully uploaded.
    """
    endpoint, key, index_name = _get_search_credentials()
    if not endpoint or not key:
        logger.warning("Azure Search credentials missing – skipping sync.")
        return 0

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    credential = AzureKeyCredential(key)
    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    dirty_rules = db.execute(select(Rule).where(Rule.is_indexed == False)).scalars().all()  # noqa: E712
    if not dirty_rules:
        return 0

    now = datetime.now(timezone.utc)
    documents: list[dict[str, Any]] = []

    for rule in dirty_rules:
        content = f"Rule Text: {rule.rule_text}\nType: {rule.rule_type}\nStatus: {rule.verification_status}"

        jira_key = rule.source_ref if rule.source_type == "jira" else "UNKNOWN"
        module_filter = "Unknown"

        if rule.source_type == "jira":
            story = db.execute(select(Story).where(Story.jira_key == jira_key)).scalar_one_or_none()
            if story:
                content += f"\nParent Story Title: {story.title}\nCriteria: {story.acceptance_criteria}"
                module_filter = story.module or "Unknown"
                story.is_indexed = True
                story.last_indexed_at = now

        content_vector = generate_embedding(content)

        documents.append(
            {
                "id": str(rule.id),
                "jira_key": jira_key,
                "module_filter": module_filter,
                "rule_type": rule.rule_type,
                "source_type": rule.source_type,
                "verification_status": rule.verification_status,
                "content": content,
                "content_vector": content_vector,
            }
        )

    result = search_client.upload_documents(documents=documents)

    success_count = 0
    for res, rule in zip(result, dirty_rules):
        if res.succeeded:
            rule.is_indexed = True
            rule.last_indexed_at = now
            success_count += 1
        else:
            logger.error("Failed to upload document %s: %s", res.key, res.error_message)

    db.commit()
    return success_count


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------

def search_rules(query: str, module_filter: str | None = None, top: int = 5) -> list[dict] | dict:
    """Hybrid keyword + vector search against the Azure index."""
    endpoint, key, index_name = _get_search_credentials()
    if not endpoint or not key:
        return {"error": "Azure Search credentials missing."}

    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery

    credential = AzureKeyCredential(key)
    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    vector_query = VectorizedQuery(
        vector=generate_embedding(query),
        k_nearest_neighbors=top,
        fields="content_vector",
    )

    filter_expression = f"module_filter eq '{module_filter}'" if module_filter else None

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_expression,
        top=top,
    )

    return [
        {
            "id": r["id"],
            "jira_key": r["jira_key"],
            "module_filter": r["module_filter"],
            "rule_type": r["rule_type"],
            "verification_status": r["verification_status"],
            "content": r["content"],
            "score": r.get("@search.score", 0),
        }
        for r in results
    ]

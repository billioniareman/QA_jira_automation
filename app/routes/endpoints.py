from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.story import Story
from app.models.rule import Rule
from app.models.entity_link import EntityLink
from app.services.jira_service import ingest_jira_issues
from app.services.azure_search_service import (
    create_index_if_not_exists,
    search_rules,
    sync_dirty_rules_to_azure,
)

api_router = APIRouter()


# ── Health check ───────────────────────────────────────────────────────────

@api_router.get('/health', tags=['ops'])
def health_check():
    """Lightweight liveness probe."""
    return {"status": "ok"}


# ── Jira ingestion ────────────────────────────────────────────────────────

@api_router.post('/ingest/jira')
def trigger_jira_ingestion(
    jql_query: Optional[str] = Query(default=None, description="Optional JQL to filter issues"),
    db: Session = Depends(get_db),
):
    """
    Triggers the ingestion of live Jira issues.
    """
    result = ingest_jira_issues(db, jql_query=jql_query)

    if result.get("status") == "success":
        return result
    raise HTTPException(status_code=500, detail=result)


# ── Story detail ──────────────────────────────────────────────────────────

@api_router.get('/stories/{jira_key}')
def get_story(jira_key: str, db: Session = Depends(get_db)):
    """
    Returns story details along with its associated rules.
    """
    story = db.execute(select(Story).where(Story.jira_key == jira_key)).scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail='Story not found')

    links = db.execute(
        select(EntityLink).where(
            EntityLink.from_type == 'story',
            EntityLink.from_id == story.id,
            EntityLink.relation == 'has_rule',
            EntityLink.to_type == 'rule',
        )
    ).scalars().all()
    rule_ids = [link.to_id for link in links]

    rules = []
    if rule_ids:
        rules = db.execute(select(Rule).where(Rule.id.in_(rule_ids))).scalars().all()

    story_data = story.to_dict()
    story_data['rules'] = [rule.to_dict() for rule in rules]

    return story_data


# ── Rules list / filter ───────────────────────────────────────────────────

@api_router.get('/rules')
def get_rules(
    source_ref: Optional[str] = Query(default=None),
    rule_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Returns rule details. Can be filtered by query params.
    """
    query = select(Rule)
    if source_ref:
        query = query.where(Rule.source_ref == source_ref)
    if rule_type:
        query = query.where(Rule.rule_type == rule_type)

    rules = db.execute(query).scalars().all()
    return [rule.to_dict() for rule in rules]


# ── Azure AI Search sync ─────────────────────────────────────────────────

@api_router.post('/sync')
def trigger_azure_sync(db: Session = Depends(get_db)):
    """
    Provisions the Azure AI Search index (if missing) and pushes
    un-indexed rules.
    """
    create_index_if_not_exists()
    synced_count = sync_dirty_rules_to_azure(db)
    if isinstance(synced_count, int):
        return {"status": "success", "synced_rules": synced_count}
    raise HTTPException(
        status_code=500,
        detail="Check server logs or missing Azure credentials",
    )


# ── Hybrid search ─────────────────────────────────────────────────────────

@api_router.get('/search')
def search_knowledge(
    q: str = Query(..., description="Search query text"),
    module: Optional[str] = Query(default=None, description="Filter by module"),
):
    """
    Hybrid keyword + vector search for rules via Azure AI Search.
    """
    results = search_rules(q, module)
    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=500, detail=results["error"])

    return {"results": results}

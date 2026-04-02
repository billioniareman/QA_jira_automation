import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.story import Story
from app.models.rule import Rule
from app.models.entity_link import EntityLink
from app.services.jira_service import ingest_jira_issues

api_router = APIRouter()

@api_router.post('/ingest/jira')
def trigger_jira_ingestion():
    """
    Triggers the ingestion of Jira issues.
    For local testing, we inject the path to sample data.
    """
    # Using local mock data since Phase 1 doesn't have live Jira connection configured
    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'sample_jira_response.json')
    result = ingest_jira_issues(sample_data_path=sample_path)
    
    if result.get("status") == "success":
        return result
    raise HTTPException(status_code=500, detail=result)

@api_router.get('/stories/{jira_key}')
def get_story(jira_key: str, db: Session = Depends(get_db)):
    """
    Returns story details along with its associated rules.
    """
    story = db.execute(select(Story).where(Story.jira_key == jira_key)).scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail='Story not found')
    
    # Fetch linked rules via entity_links
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

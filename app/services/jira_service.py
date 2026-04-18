import logging
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.story import Story
from app.models.rule import Rule
from app.models.entity_link import EntityLink
from app.services.mapping import map_jira_to_module_feature
from app.services.rule_engine import extract_rules
from config import settings

logger = logging.getLogger(__name__)


def ingest_jira_issues(db: Session, jql_query: str | None = None):
    """
    Ingests Jira issues, maps them to module/feature, extracts rules,
    and saves them to the database.

    Args:
        db: SQLAlchemy session (provided by FastAPI Depends).
        jql_query: Optional JQL filter.
    """
    try:
        base_url = settings.JIRA_BASE_URL.rstrip('/')
        auth = (settings.JIRA_USERNAME, settings.JIRA_API_TOKEN)
        
        # 1. Dynamically find the custom field ID for "Acceptance Criteria"
        ac_field_id = "customfield_10000" # Fallback
        fields_url = f"{base_url}/rest/api/3/field"
        fields_response = requests.get(fields_url, auth=auth)
        if fields_response.status_code == 200:
            for field in fields_response.json():
                if field.get("name", "").lower() == "acceptance criteria":
                    ac_field_id = field.get("id")
                    break

        # 2. Fetch Issues
        search_url = f"{base_url}/rest/api/3/search/jql"
        jql = jql_query if jql_query else "project IS NOT EMPTY ORDER BY created DESC"
        params = {"jql": jql, "maxResults": 50, "fields": "*all"}
        
        logger.info(f"Fetching Jira issues with JQL: {jql}")
        response = requests.get(search_url, auth=auth, params=params)
        
        if response.status_code != 200:
            error_msg = f"Failed to fetch from Jira (Status {response.status_code}): {response.text}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

        data = response.json()
        issues = data.get('issues', [])
        saved_stories_count = 0
        saved_rules_count = 0

        for issue in issues:
            key = issue.get('key')
            fields = issue.get('fields', {})
            summary = fields.get('summary', '')
            description = fields.get('description', '')
            # Getting dynamically found acceptance criteria field
            acceptance_criteria = fields.get(ac_field_id)
            if not acceptance_criteria:
                acceptance_criteria = description

            module, feature = map_jira_to_module_feature(issue)

            # Upsert Story
            story = db.execute(select(Story).where(Story.jira_key == key)).scalar_one_or_none()
            if not story:
                story = Story(jira_key=key)
                db.add(story)

            story.title = summary
            story.description = description
            story.acceptance_criteria = acceptance_criteria
            story.module = module
            story.feature = feature
            story.status = fields.get('status', {}).get('name', 'Open')

            db.flush()
            saved_stories_count += 1

            # Extract Rules
            extracted = extract_rules(acceptance_criteria)
            for rule_data in extracted:
                # Basic check to avoid complete duplicates for this story
                existing_rule = db.execute(
                    select(Rule).where(
                        Rule.source_ref == key,
                        Rule.rule_text == rule_data['rule_text'],
                    )
                ).scalar_one_or_none()

                if not existing_rule:
                    rule = Rule(
                        rule_text=rule_data['rule_text'],
                        rule_type=rule_data['rule_type'],
                        source_type=rule_data['source_type'],
                        source_ref=key,
                        verification_status=rule_data['verification_status'],
                        confidence=rule_data['confidence'],
                    )
                    db.add(rule)
                    db.flush()
                    saved_rules_count += 1

                    # Link Rule to Story
                    link = EntityLink(
                        from_type='story',
                        from_id=story.id,
                        relation='has_rule',
                        to_type='rule',
                        to_id=rule.id,
                    )
                    db.add(link)

        db.commit()
        return {"status": "success", "stories_ingested": saved_stories_count, "rules_extracted": saved_rules_count}

    except Exception as e:
        db.rollback()
        logger.error(f"Error during ingestion: {str(e)}")
        return {"status": "error", "message": str(e)}

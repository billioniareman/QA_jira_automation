import json
import logging
from sqlalchemy import select

from app.db import SessionLocal
from app.models.story import Story
from app.models.rule import Rule
from app.models.entity_link import EntityLink
from app.services.mapping import map_jira_to_module_feature
from app.services.rule_engine import extract_rules

logger = logging.getLogger(__name__)

def ingest_jira_issues(sample_data_path=None):
    """
    Ingests Jira issues, maps them to module/feature, extracts rules,
    and saves them to the database.
    Using local sample JSON for now as per user instruction.
    """
    db = SessionLocal()
    try:
        if sample_data_path:
            with open(sample_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # Simulate fetching from API fallback
            data = {"issues": []}

        issues = data.get('issues', [])
        saved_stories_count = 0
        saved_rules_count = 0

        for issue in issues:
            key = issue.get('key')
            fields = issue.get('fields', {})
            summary = fields.get('summary', '')
            description = fields.get('description', '')
            # Using customfield_10000 to represent acceptance criteria in our sample
            acceptance_criteria = fields.get('customfield_10000', description)

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
    finally:
        db.close()

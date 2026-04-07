import os
from flask import Blueprint, jsonify, request
from app.services.jira_service import ingest_jira_issues
from app.models.story import Story
from app.models.rule import Rule
from app.models.entity_link import EntityLink
from app.services.azure_search_service import sync_dirty_rules_to_azure, search_rules, create_index_if_not_exists

api_bp = Blueprint('api', __name__)

@api_bp.route('/ingest/jira', methods=['POST'])
def trigger_jira_ingestion():
    """
    Triggers the ingestion of Jira issues.
    For local testing, we inject the path to sample data.
    """
    # Using local mock data since Phase 1 doesn't have live Jira connection configured
    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'sample_jira_response.json')
    result = ingest_jira_issues(sample_data_path=sample_path)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    return jsonify(result), 500

@api_bp.route('/stories/<jira_key>', methods=['GET'])
def get_story(jira_key):
    """
    Returns story details along with its associated rules.
    """
    story = Story.query.filter_by(jira_key=jira_key).first_or_404()
    
    # Fetch linked rules via entity_links
    links = EntityLink.query.filter_by(from_type='story', from_id=story.id, relation='has_rule', to_type='rule').all()
    rule_ids = [link.to_id for link in links]
    
    rules = Rule.query.filter(Rule.id.in_(rule_ids)).all()
    
    story_data = story.to_dict()
    story_data['rules'] = [rule.to_dict() for rule in rules]
    
    return jsonify(story_data), 200

@api_bp.route('/rules/', methods=['GET'])
def get_rules():
    """
    Returns rule details. Can be filtered by query params.
    """
    source_ref = request.args.get('source_ref')
    rule_type = request.args.get('rule_type')
    
    query = Rule.query
    if source_ref:
        query = query.filter_by(source_ref=source_ref)
    if rule_type:
        query = query.filter_by(rule_type=rule_type)
        
    rules = query.all()
    return jsonify([rule.to_dict() for rule in rules]), 200

@api_bp.route('/sync', methods=['POST'])
def trigger_azure_sync():
    """
    Provisions index (if missing) and pushes dirty rules to Azure AI Search.
    """
    create_index_if_not_exists()
    synced_count = sync_dirty_rules_to_azure()
    if isinstance(synced_count, int):
        return jsonify({"status": "success", "synced_rules": synced_count}), 200
    return jsonify({"status": "error", "message": "Check server logs or missing credentials"}), 500

@api_bp.route('/search', methods=['GET'])
def search_knowledge():
    """
    Hybrid Search for rules utilizing keyword and sentence-transformers vectors.
    """
    query = request.args.get('q')
    module_filter = request.args.get('module')
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required."}), 400

    results = search_rules(query, module_filter)
    if isinstance(results, dict) and "error" in results:
        return jsonify(results), 500
        
    return jsonify({"results": results}), 200

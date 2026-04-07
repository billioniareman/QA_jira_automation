import os
from datetime import datetime
from app.extensions import db
from app.models.rule import Rule
from app.models.story import Story
from sentence_transformers import SentenceTransformer
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile
)
from flask import current_app

# Load the SentenceTransformer model (will download on first run)
model = SentenceTransformer('all-MiniLM-L6-v2') 

def get_search_credentials():
    endpoint = current_app.config.get('AZURE_SEARCH_ENDPOINT')
    key = current_app.config.get('AZURE_SEARCH_API_KEY')
    index_name = current_app.config.get('AZURE_SEARCH_INDEX_NAME')
    return endpoint, key, index_name

def create_index_if_not_exists():
    endpoint, key, index_name = get_search_credentials()
    if not endpoint or not key:
        print("Azure Search credentials missing. Skipping index creation.")
        return

    credential = AzureKeyCredential(key)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    
    try:
        index_client.get_index(index_name)
        print(f"Index '{index_name}' already exists.")
    except Exception as e:
        print(f"Index '{index_name}' not found. Creating...")
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="myHnsw")
            ],
            profiles=[
                VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")
            ]
        )

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="jira_key", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="module_filter", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="rule_type", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="source_type", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="verification_status", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, vector_search_dimensions=384, vector_search_profile_name="myHnswProfile")
        ]

        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        index_client.create_index(index)
        print(f"Index '{index_name}' created successfully.")


def generate_embedding(text):
    return model.encode(text).tolist()

def sync_dirty_rules_to_azure():
    endpoint, key, index_name = get_search_credentials()
    if not endpoint or not key:
        print("Azure Search credentials missing. Skipping sync.")
        return 0

    credential = AzureKeyCredential(key)
    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    dirty_rules = Rule.query.filter_by(is_indexed=False).all()
    if not dirty_rules:
        return 0

    documents = []
    
    for rule in dirty_rules:
        content = f"Rule Text: {rule.rule_text}\nType: {rule.rule_type}\nStatus: {rule.verification_status}"
        
        jira_key = rule.source_ref if rule.source_type == 'jira' else 'UNKNOWN'
        module_filter = 'Unknown'
        
        if rule.source_type == 'jira':
            story = Story.query.filter_by(jira_key=jira_key).first()
            if story:
                content += f"\nParent Story Title: {story.title}\nCriteria: {story.acceptance_criteria}"
                module_filter = story.module if story.module else 'Unknown'
                story.is_indexed = True
                story.last_indexed_at = datetime.utcnow()

        content_vector = generate_embedding(content)

        doc = {
            "id": str(rule.id),
            "jira_key": jira_key,
            "module_filter": module_filter,
            "rule_type": rule.rule_type,
            "source_type": rule.source_type,
            "verification_status": rule.verification_status,
            "content": content,
            "content_vector": content_vector
        }
        documents.append(doc)
    
    result = search_client.upload_documents(documents=documents)
    
    success_count = 0
    for res, rule in zip(result, dirty_rules):
        if res.succeeded:
            rule.is_indexed = True
            rule.last_indexed_at = datetime.utcnow()
            success_count += 1
        else:
            print(f"Failed to upload document {res.key}: {res.error_message}")

    db.session.commit()
    return success_count

from azure.search.documents.models import VectorizedQuery

def search_rules(query, module_filter=None, top=5):
    endpoint, key, index_name = get_search_credentials()
    if not endpoint or not key:
        return {"error": "Azure Search credentials missing."}

    credential = AzureKeyCredential(key)
    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    vector_query = VectorizedQuery(
        vector=generate_embedding(query),
        k_nearest_neighbors=top,
        fields="content_vector"
    )

    filter_expression = None
    if module_filter:
        filter_expression = f"module_filter eq '{module_filter}'"

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_expression,
        top=top
    )

    extracted_results = []
    for result in results:
        extracted_results.append({
            "id": result["id"],
            "jira_key": result["jira_key"],
            "module_filter": result["module_filter"],
            "rule_type": result["rule_type"],
            "verification_status": result["verification_status"],
            "content": result["content"],
            "score": result.get("@search.score", 0)
        })

    return extracted_results

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql+psycopg://postgres:postgres@localhost:5432/qa_knowledge'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JIRA_BASE_URL = os.environ.get('JIRA_BASE_URL', 'https://your-domain.atlassian.net')
    JIRA_USERNAME = os.environ.get('JIRA_USERNAME', 'mock_user')
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN', 'mock_token')
    AZURE_SEARCH_ENDPOINT = os.environ.get('AZURE_SEARCH_ENDPOINT', '')
    AZURE_SEARCH_API_KEY = os.environ.get('AZURE_SEARCH_API_KEY', '')
    AZURE_SEARCH_INDEX_NAME = os.environ.get('AZURE_SEARCH_INDEX_NAME', 'qa-knowledge-rules')

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql+psycopg://postgres:postgres@localhost:5432/qa_knowledge'
    JIRA_BASE_URL = os.environ.get('JIRA_BASE_URL', 'https://your-domain.atlassian.net')
    JIRA_USERNAME = os.environ.get('JIRA_USERNAME', 'mock_user')
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN', 'mock_token')
    API_PREFIX = '/api/v1'
    APP_NAME = 'QA Knowledge Platform API'


settings = Settings()

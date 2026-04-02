QA Knowledge Platform Phase 1 - Code Walkthrough
This document outlines the completion of Phase 1: the backend foundation for your QA Knowledge Platform. The core logic has been constructed strictly in Python (Flask) with PostgreSQL and Alembic.

Implementation Delivered
I've generated the entire structural foundation at c:\Users\Admin\Desktop\QA_automation\qa_knowledge_platform.

1. Database & ORM Setup
Using Alembic (flask-migrate), the schema can be fully migrated from our model definitions. The app/models/ directory implements:

Story: Records Jira issues.
Rule: Structures extracted behaviors along with validation rules.
FrontendSignal: Built as requested for future frontend parsing steps.
EntityLink: Creates lineage tracking from Jira Story to extracted Rule.
2. Services
Rule Engine: Parses the acceptance criteria using heuristic delimiters, spotting keywords like must, valid, cannot, etc., converting free text to structured validation/business constraint rules.
Mapping Service: Defines standard static dictionaries aligning Jira components (e.g., Passenger Details) to Application Modules (Booking).
Jira Service: Contains the ingest_jira_issues() workflow. It pulls our sample_jira_response.json, cascades data through mapping, rule extraction, and properly transacts the records into the database with lineage mapping.
3. Endpoints
Three primary RESTful endpoints created under api/v1:

POST /api/v1/ingest/jira: Pulls the sample JQL data and executes the full extraction logic locally.
GET /api/v1/stories/<jira_key>: Returns nested records mapping a story linearly to its extracted rules.
GET /api/v1/rules/: Standard query endpoint for generated rules.
Local Testing Instructions
You can setup inside your local bash/PowerShell by taking context to the directory we just built:

# Command Prompt
cd C:\Users\Admin\Desktop\QA_automation\qa_knowledge_platform
# 1. Start virtual environment
python -m venv venv
.\venv\Scripts\activate
# 2. Dependencies
pip install -r requirements.txt
# 3. Create your local db (needs psql or pgAdmin) named "qa_knowledge"
# Update the DATABASE_URL within the generated .env if your creds aren't postgres:postgres
# 4. Migrate Schema via Alembic
flask db init
flask db migrate -m "Init Baseline Schema"
flask db upgrade
# 5. Run API
flask run
Then, try out the triggers:

Initialize the Mock JSON payload into DB: curl -X POST http://127.0.0.1:5000/api/v1/ingest/jira
Validate what was pulled: curl http://127.0.0.1:5000/api/v1/stories/BOOK-101

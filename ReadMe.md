QA Knowledge Platform Phase 1 - Code Walkthrough
This document outlines the backend foundation for your QA Knowledge Platform. The core logic is now built in Python with FastAPI, PostgreSQL, SQLAlchemy, and Alembic.

Implementation Delivered
The project foundation is implemented in this repository.

1. Database & ORM Setup
Using Alembic, the schema can be fully migrated from our model definitions. The app/models/ directory implements:

Story: Records Jira issues.
Rule: Structures extracted behaviors along with validation rules.
FrontendSignal: Built as requested for future frontend parsing steps.
EntityLink: Creates lineage tracking from Jira Story to extracted Rule.
2. Services
Rule Engine: Parses the acceptance criteria using heuristic delimiters, spotting keywords like must, valid, cannot, etc., converting free text to structured validation/business constraint rules.
Mapping Service: Defines standard static dictionaries aligning Jira components (e.g., Passenger Details) to Application Modules (Booking).
Jira Service: Contains the ingest_jira_issues() workflow. It pulls our sample_jira_response.json, cascades data through mapping, rule extraction, and properly transacts the records into the database with lineage mapping.
3. Endpoints
Three primary RESTful endpoints are available under /api/v1:

POST /api/v1/ingest/jira: Pulls the sample JQL data and executes the full extraction logic locally.
GET /api/v1/stories/<jira_key>: Returns nested records mapping a story linearly to its extracted rules.
GET /api/v1/rules/: Standard query endpoint for generated rules.
Local Testing Instructions
You can set up and run locally with the commands below.

# 1) Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure PostgreSQL
# Ensure DATABASE_URL is set in .env or environment.

# 4) Run migrations
alembic -c migrations/alembic.ini upgrade head

# 5) Run API
python main.py
Then, try out the triggers:

Initialize mock JSON payload into DB:
curl -X POST http://127.0.0.1:5000/api/v1/ingest/jira

Validate ingested story:
curl http://127.0.0.1:5000/api/v1/stories/BOOK-101

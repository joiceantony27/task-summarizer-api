# AI-Powered Task Summarizer API

A robust REST API service built with FastAPI and PostgreSQL that manages tasks with AI-powered summarization capabilities using OpenAI's GPT model.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📑 Table of Contents

- [Problem Understanding \& Assumptions](#1️⃣-problem-understanding--assumptions)
- [Design Decisions](#2️⃣-design-decisions)
- [Solution Approach](#3️⃣-solution-approach)
- [Error Handling Strategy](#4️⃣-error-handling-strategy)
- [How to Run the Project](#5️⃣-how-to-run-the-project)
- [Testing Strategy](#🧪-testing-strategy)
- [API Documentation](#📚-api-documentation)

---

## 1️⃣ Problem Understanding & Assumptions

### Interpretation

The assessment requires building a REST API service that:
- Acts as a bridge between a local PostgreSQL database and an external API (OpenAI)
- Implements exactly four CRUD endpoints (POST, GET, PUT, DELETE)
- Demonstrates complex data flows with strict validation
- Handles external API integration with proper resilience

### Use Case: AI-Powered Task Summarizer

I chose to implement a **Task Management System** where:
- Users can create, read, update, and delete tasks
- Each task can have an AI-generated summary created by OpenAI's GPT model
- The summary provides a concise, actionable overview of the task

### Assumptions

1. **Authentication/Authorization**: 
   - Not implemented as it was not explicitly required
   - In production, JWT-based authentication would be added

2. **Data Formats**:
   - Task IDs are UUIDs for global uniqueness
   - Timestamps are stored in UTC timezone
   - Description minimum length is 10 characters to ensure meaningful content for AI summarization

3. **External API Reliability**:
   - OpenAI API may be unavailable or rate-limited
   - Summary generation is non-critical; task creation succeeds even if summarization fails
   - Implemented retry logic with exponential backoff (3 attempts)

4. **Business Logic Constraints**:
   - Tasks cannot be created without a title and description
   - Task status follows a defined enum (pending, in_progress, completed, cancelled)
   - Priority levels are fixed (low, medium, high, critical)

5. **API Rate Limits**:
   - OpenAI has rate limits; implemented timeout (30s) and retry mechanisms
   - Graceful degradation when external API is unavailable

---

## 2️⃣ Design Decisions

### Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│                         TASKS TABLE                          │
├─────────────────────────────────────────────────────────────┤
│ id          │ UUID (PK)      │ Unique task identifier       │
│ title       │ VARCHAR(200)   │ Task title (required)        │
│ description │ TEXT           │ Detailed description         │
│ summary     │ TEXT           │ AI-generated summary (null)  │
│ status      │ ENUM           │ Task status                  │
│ priority    │ ENUM           │ Priority level               │
│ due_date    │ TIMESTAMP      │ Optional due date            │
│ created_at  │ TIMESTAMP      │ Creation timestamp           │
│ updated_at  │ TIMESTAMP      │ Last update timestamp        │
└─────────────────────────────────────────────────────────────┘

INDEXES:
- idx_tasks_status (status) - For filtering by status
- idx_tasks_priority (priority) - For filtering by priority  
- idx_tasks_created_at (created_at) - For ordering
- idx_tasks_due_date (due_date) - For due date queries
```

**Indexing Choices**:
- Status and priority indexes optimize filtering operations
- Created_at index supports efficient ordering for pagination
- Due_date index enables future features like reminder notifications

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API endpoint definitions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Application configuration
│   │   └── exceptions.py      # Custom exception classes
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py        # Database connection & session
│   ├── models/
│   │   ├── __init__.py
│   │   └── task.py            # SQLAlchemy ORM models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── task.py            # Pydantic validation schemas
│   └── services/
│       ├── __init__.py
│       ├── openai_client.py   # External API client
│       └── task_service.py    # Business logic layer
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── test_api.py            # Integration tests
│   ├── test_schemas.py        # Schema validation tests
│   ├── test_services.py       # Service layer tests
│   └── test_openai_client.py  # External client tests
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── Dockerfile                # Container configuration
├── docker-compose.yml        # Multi-container setup
└── README.md                 # This file
```

**Architecture: Layered/Clean Architecture**

I chose a layered architecture separating:
- **API Layer** (`api/`): HTTP request/response handling
- **Service Layer** (`services/`): Business logic and orchestration
- **Data Layer** (`models/`, `db/`): Database operations
- **Schema Layer** (`schemas/`): Validation and serialization

Benefits:
- Clear separation of concerns
- Easy to test each layer independently
- Flexible for future changes

### Validation Logic

Beyond basic type checking, the validation includes:

1. **Title Validation**:
   - Not empty or whitespace-only
   - Length between 1-200 characters
   - Automatic whitespace trimming

2. **Description Validation**:
   - Minimum 10 characters (meaningful content for AI)
   - Maximum 5000 characters
   - Automatic whitespace trimming

3. **Enum Validation**:
   - Status must be valid enum value
   - Priority must be valid enum value

4. **Custom Field Validators**:
   - Using Pydantic's `@field_validator` for complex validation rules
   - Separate schemas for Create vs Update operations

### External API Design

**OpenAI Integration**:

```python
# Retry configuration
@retry(
    retry=retry_if_exception_type((TimeoutException, NetworkError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
```

- **Authentication**: Bearer token via `Authorization` header
- **Rate Limits**: Handled with retry logic and exponential backoff
- **Timeouts**: Configurable timeout (default 30 seconds)
- **Error Mapping**: HTTP status codes mapped to custom exceptions

---

## 3️⃣ Solution Approach

### Data Flow Walkthrough

#### 1. Create Task (POST /api/v1/tasks/)

```
┌──────────┐     ┌───────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────▶│  FastAPI  │────▶│  Pydantic   │────▶│  Service │────▶│ OpenAI   │
│          │     │  Router   │     │  Validate   │     │  Layer   │     │   API    │
└──────────┘     └───────────┘     └─────────────┘     └──────────┘     └──────────┘
                                                              │                │
                                                              ▼                │
                                                       ┌──────────┐           │
                                                       │PostgreSQL│◀──────────┘
                                                       │    DB    │   (summary)
                                                       └──────────┘
```

**Step-by-step**:
1. Client sends POST request with task data
2. FastAPI routes to `create_task` endpoint
3. Pydantic validates request body against `TaskCreate` schema
4. TaskService receives validated data
5. If `generate_summary=True`, calls OpenAI API for summary
6. Creates Task model and saves to PostgreSQL
7. Returns created task with `201 Created` status

#### 2. Get Tasks (GET /api/v1/tasks/)

```
┌──────────┐     ┌───────────┐     ┌─────────────┐     ┌──────────┐
│  Client  │────▶│  FastAPI  │────▶│   Service   │────▶│PostgreSQL│
│          │     │  Router   │     │   Layer     │     │    DB    │
└──────────┘     └───────────┘     └─────────────┘     └──────────┘
                       │                  │
                       ▼                  ▼
                 ┌───────────┐     ┌─────────────┐
                 │  Query    │     │  Paginated  │
                 │  Params   │     │   Results   │
                 └───────────┘     └─────────────┘
```

**Step-by-step**:
1. Client sends GET request with optional query params
2. FastAPI validates query parameters (page, page_size, filters)
3. TaskService builds query with filters
4. Executes paginated query on PostgreSQL
5. Returns task list with pagination metadata

#### 3. Update Task (PUT /api/v1/tasks/{task_id})

```
┌──────────┐     ┌───────────┐     ┌─────────────┐     ┌──────────┐
│  Client  │────▶│  FastAPI  │────▶│  Validate   │────▶│  Service │
└──────────┘     └───────────┘     └─────────────┘     └──────────┘
                                                              │
                      ┌───────────────────────────────────────┘
                      ▼
               ┌─────────────┐     ┌──────────┐     ┌──────────┐
               │ Check Task  │────▶│  Update  │────▶│  OpenAI  │
               │   Exists    │     │  Fields  │     │ (if regen)│
               └─────────────┘     └──────────┘     └──────────┘
```

**Step-by-step**:
1. Client sends PUT request with partial update data
2. Pydantic validates against `TaskUpdate` schema
3. Service fetches existing task (404 if not found)
4. Updates only provided fields
5. If `regenerate_summary=True`, calls OpenAI API
6. Saves changes and returns updated task

#### 4. Delete Task (DELETE /api/v1/tasks/{task_id})

```
┌──────────┐     ┌───────────┐     ┌─────────────┐     ┌──────────┐
│  Client  │────▶│  FastAPI  │────▶│   Service   │────▶│PostgreSQL│
└──────────┘     └───────────┘     └─────────────┘     └──────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │  Verify &   │
                                   │   Delete    │
                                   └─────────────┘
```

**Step-by-step**:
1. Client sends DELETE request with task ID
2. Service verifies task exists (404 if not found)
3. Deletes task from PostgreSQL
4. Returns deletion confirmation

---

## 4️⃣ Error Handling Strategy

### Custom Exception Hierarchy

```python
AppException (Base)
├── TaskNotFoundException (404)
├── DatabaseConnectionError (503)
├── ExternalAPIError (502)
├── ExternalAPITimeoutError (504)
└── ValidationError (422)
```

### Global Exception Handlers

Implemented in `app/core/exceptions.py`:

```python
@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
        }
    )
```

### Failure Scenarios

| Scenario | Handling Strategy | HTTP Status |
|----------|-------------------|-------------|
| Task not found | Raise `TaskNotFoundException` | 404 |
| DB connection failure | Raise `DatabaseConnectionError` | 503 |
| OpenAI API down | Log error, return task without summary | 201 (graceful) |
| OpenAI timeout | Retry 3x with backoff, then graceful fail | 201 (graceful) |
| Validation error | Pydantic auto-handles | 422 |
| Unexpected error | Global handler, hide details in production | 500 |

### Resilience Features

1. **Retry Logic**: External API calls retry 3 times with exponential backoff
2. **Circuit Breaker Pattern**: (Future enhancement) Would prevent cascading failures
3. **Graceful Degradation**: Summary generation failure doesn't block task creation
4. **Timeout Handling**: Configurable timeouts prevent hanging requests

---

## 5️⃣ How to Run the Project

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ (or Docker)
- OpenAI API key (optional, for AI summaries)

### Option 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd backend

# Create .env file from template
cp .env.example .env

# Add your OpenAI API key to .env
# OPENAI_API_KEY=your_key_here

# Start services
docker-compose up --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your database URL and OpenAI key

# Run the application
uvicorn main:app --reload

# API available at http://localhost:8000
```

### Required Environment Variables

```bash
# .env file
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/task_summarizer
OPENAI_API_KEY=your_openai_api_key  # Optional
OPENAI_API_URL=https://api.openai.com/v1/chat/completions
APP_ENV=development
DEBUG=true
EXTERNAL_API_TIMEOUT=30
EXTERNAL_API_MAX_RETRIES=3
```

### Example API Calls

#### Create a Task

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete project documentation",
    "description": "Write comprehensive documentation including API reference, setup guide, and architecture overview.",
    "priority": "high",
    "generate_summary": true
  }'
```

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Complete project documentation",
  "description": "Write comprehensive documentation...",
  "summary": "Document the project with API reference, setup guide, and architecture details.",
  "status": "pending",
  "priority": "high",
  "due_date": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Get All Tasks

```bash
curl "http://localhost:8000/api/v1/tasks/?page=1&page_size=10&priority=high"
```

#### Get Task by ID

```bash
curl "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000"
```

#### Update a Task

```bash
curl -X PUT "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "priority": "critical"
  }'
```

#### Delete a Task

```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000"
```

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Testing Strategy

### Test Categories

#### Unit Tests
Test individual components in isolation:
- **Schema Tests** (`test_schemas.py`): Validate Pydantic schema validation rules
- **Service Tests** (`test_services.py`): Test business logic with mocked dependencies
- **Client Tests** (`test_openai_client.py`): Test external API client with mocked HTTP

#### Integration Tests
Test the full API request/response cycle:
- **API Tests** (`test_api.py`): End-to-end endpoint testing with mocked DB and external APIs

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run with coverage report
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Configuration

Tests use:
- **SQLite in-memory database**: Fast, isolated test runs
- **Mocked OpenAI client**: Consistent, reliable external API simulation
- **pytest-asyncio**: Async test support
- **HTTPX AsyncClient**: Testing FastAPI endpoints

### Example Test Output

```
tests/test_api.py::TestCreateTaskEndpoint::test_create_task_success PASSED
tests/test_api.py::TestCreateTaskEndpoint::test_create_task_validation_error PASSED
tests/test_api.py::TestGetTasksEndpoint::test_get_tasks_pagination PASSED
tests/test_services.py::TestTaskServiceCreate::test_create_task_with_summary PASSED
tests/test_schemas.py::TestTaskCreateSchema::test_valid_task_create PASSED

==================== 25 passed in 2.54s ====================
```

---

## 📚 API Documentation

### Endpoints Summary

| Method | Endpoint | Description | Status Codes |
|--------|----------|-------------|--------------|
| POST | `/api/v1/tasks/` | Create a new task | 201, 422, 503 |
| GET | `/api/v1/tasks/` | List all tasks (paginated) | 200, 503 |
| GET | `/api/v1/tasks/{id}` | Get task by ID | 200, 404, 503 |
| PUT | `/api/v1/tasks/{id}` | Update a task | 200, 404, 422, 503 |
| DELETE | `/api/v1/tasks/{id}` | Delete a task | 200, 404, 503 |
| GET | `/health` | Health check | 200 |

### Error Response Format

```json
{
  "success": false,
  "error": "Error message description",
  "error_code": "TASK_NOT_FOUND",
  "details": {
    "task_id": "invalid-uuid"
  }
}
```

---

## 🔄 Trade-offs, Limitations & Future Improvements

### Trade-offs Made

1. **Summary Generation is Async but Blocking**
   - Current: Summary generation blocks the request
   - Alternative: Background job queue (Celery) for async processing
   - Reason: Simplicity for MVP; external API calls are typically fast

2. **SQLite for Testing vs PostgreSQL for Production**
   - Trade-off between test speed and production parity
   - Mitigated by using SQLAlchemy's abstraction layer

3. **No Authentication**
   - Kept out of scope to focus on core requirements
   - Would add JWT/OAuth2 in production

### Limitations

1. No rate limiting on API endpoints
2. No caching layer (Redis would improve GET performance)
3. No background job processing
4. Single-node deployment (no horizontal scaling considerations)

### Future Improvements

1. **Add Redis Caching**: Cache frequently accessed tasks
2. **Implement Background Jobs**: Use Celery for async summary generation
3. **Add Authentication**: JWT-based auth with user management
4. **Implement Rate Limiting**: Protect API from abuse
5. **Add Observability**: Structured logging, metrics, tracing
6. **Database Migrations**: Add Alembic for production-ready migrations
7. **API Versioning**: Support multiple API versions

---

## 📄 License

This project is created for assessment purposes.

---

## 👤 Author

Joice Antony

---

*Built with ❤️ using FastAPI, PostgreSQL, and OpenAI*

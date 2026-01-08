"""
Pytest configuration and fixtures for testing.
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.services.openai_client import OpenAIClient, get_openai_client
from main import app


# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Create a mock OpenAI client."""
    mock_client = MagicMock(spec=OpenAIClient)
    mock_client.generate_task_summary = AsyncMock(
        return_value="This is a mock AI-generated summary for testing purposes."
    )
    return mock_client


@pytest_asyncio.fixture(scope="function")
async def client(test_session, mock_openai_client) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with mocked dependencies."""
    
    async def override_get_db():
        yield test_session
    
    def override_get_openai_client():
        return mock_openai_client
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_openai_client] = override_get_openai_client
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_task_data() -> dict:
    """Sample task data for testing."""
    return {
        "title": "Complete unit tests",
        "description": "Write comprehensive unit tests for all API endpoints and service functions.",
        "priority": "high",
        "generate_summary": True,
    }


@pytest.fixture
def sample_task_data_no_summary() -> dict:
    """Sample task data without summary generation."""
    return {
        "title": "Review code changes",
        "description": "Review the pull request and provide feedback on code quality and design.",
        "priority": "medium",
        "generate_summary": False,
    }


@pytest.fixture
def sample_update_data() -> dict:
    """Sample task update data."""
    return {
        "title": "Updated task title",
        "status": "in_progress",
        "priority": "critical",
    }

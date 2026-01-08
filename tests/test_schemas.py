"""
Unit tests for Pydantic schemas validation.
"""
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate


class TestTaskCreateSchema:
    """Unit tests for TaskCreate schema validation."""

    def test_valid_task_create(self):
        """Test creating a valid task."""
        data = {
            "title": "Valid Task Title",
            "description": "This is a valid task description with enough characters.",
            "priority": "high",
        }
        task = TaskCreate(**data)
        assert task.title == "Valid Task Title"
        assert task.priority == TaskPriority.HIGH
        assert task.generate_summary is True  # default value

    def test_task_create_with_due_date(self):
        """Test creating a task with due date."""
        future_date = datetime.now() + timedelta(days=7)
        data = {
            "title": "Task with Due Date",
            "description": "This task has a due date set for next week.",
            "due_date": future_date.isoformat(),
        }
        task = TaskCreate(**data)
        assert task.due_date is not None

    def test_task_create_title_too_short(self):
        """Test that empty title fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="",
                description="Valid description that is long enough.",
            )
        assert "title" in str(exc_info.value).lower()

    def test_task_create_title_too_long(self):
        """Test that title over 200 chars fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="x" * 201,
                description="Valid description that is long enough.",
            )
        assert "title" in str(exc_info.value).lower()

    def test_task_create_description_too_short(self):
        """Test that description under 10 chars fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="Valid Title",
                description="Short",
            )
        assert "description" in str(exc_info.value).lower()

    def test_task_create_whitespace_title(self):
        """Test that whitespace-only title fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="   ",
                description="Valid description that is long enough.",
            )
        assert "title" in str(exc_info.value).lower()

    def test_task_create_strips_whitespace(self):
        """Test that title and description are trimmed."""
        task = TaskCreate(
            title="  Trimmed Title  ",
            description="  This description should be trimmed  ",
        )
        assert task.title == "Trimmed Title"
        assert task.description == "This description should be trimmed"

    def test_task_create_invalid_priority(self):
        """Test that invalid priority fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(
                title="Valid Title",
                description="Valid description that is long enough.",
                priority="invalid_priority",
            )
        assert "priority" in str(exc_info.value).lower()


class TestTaskUpdateSchema:
    """Unit tests for TaskUpdate schema validation."""

    def test_empty_update(self):
        """Test that empty update is valid (all fields optional)."""
        update = TaskUpdate()
        assert update.title is None
        assert update.description is None
        assert update.status is None

    def test_partial_update(self):
        """Test partial update with only some fields."""
        update = TaskUpdate(
            title="New Title",
            status="completed",
        )
        assert update.title == "New Title"
        assert update.status == TaskStatus.COMPLETED
        assert update.description is None

    def test_update_with_regenerate_summary(self):
        """Test update with summary regeneration flag."""
        update = TaskUpdate(regenerate_summary=True)
        assert update.regenerate_summary is True

    def test_update_invalid_status(self):
        """Test that invalid status fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskUpdate(status="invalid_status")
        assert "status" in str(exc_info.value).lower()


class TestTaskResponseSchema:
    """Unit tests for TaskResponse schema validation."""

    def test_valid_response(self):
        """Test valid response schema."""
        data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Test Task",
            "description": "Test description with enough characters",
            "summary": "AI generated summary",
            "status": "pending",
            "priority": "medium",
            "due_date": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = TaskResponse(**data)
        assert response.id == "123e4567-e89b-12d3-a456-426614174000"
        assert response.status == TaskStatus.PENDING

    def test_response_from_orm(self):
        """Test that response can be created from ORM object attributes."""
        # Simulating ORM object with from_attributes=True
        class MockTask:
            id = "test-uuid"
            title = "Mock Task"
            description = "Mock description with enough chars"
            summary = None
            status = TaskStatus.PENDING
            priority = TaskPriority.LOW
            due_date = None
            created_at = datetime.now()
            updated_at = datetime.now()

        response = TaskResponse.model_validate(MockTask())
        assert response.title == "Mock Task"

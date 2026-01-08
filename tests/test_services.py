"""
Unit tests for TaskService business logic.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TaskNotFoundException
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import TaskService


class TestTaskServiceCreate:
    """Unit tests for TaskService.create_task method."""

    @pytest_asyncio.fixture
    async def service(self, test_session: AsyncSession, mock_openai_client):
        """Create a TaskService instance for testing."""
        return TaskService(db=test_session, openai_client=mock_openai_client)

    @pytest.mark.asyncio
    async def test_create_task_with_summary(self, service: TaskService):
        """Test creating a task with AI summary generation."""
        task_data = TaskCreate(
            title="Test Task",
            description="This is a test task description for testing purposes.",
            priority=TaskPriority.HIGH,
            generate_summary=True,
        )

        task, error = await service.create_task(task_data)

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.summary is not None  # Mock should return summary
        assert error is None

    @pytest.mark.asyncio
    async def test_create_task_without_summary(self, test_session: AsyncSession):
        """Test creating a task without AI summary generation."""
        service = TaskService(db=test_session, openai_client=None)
        
        task_data = TaskCreate(
            title="No Summary Task",
            description="This task should not have an AI-generated summary.",
            generate_summary=False,
        )

        task, error = await service.create_task(task_data)

        assert task.id is not None
        assert task.title == "No Summary Task"
        assert task.summary is None
        assert error is None

    @pytest.mark.asyncio
    async def test_create_task_with_due_date(self, service: TaskService):
        """Test creating a task with a due date."""
        future_date = datetime.now() + timedelta(days=7)
        task_data = TaskCreate(
            title="Task with Due Date",
            description="This task has a due date set for testing purposes.",
            due_date=future_date,
        )

        task, _ = await service.create_task(task_data)

        assert task.due_date is not None

    @pytest.mark.asyncio
    async def test_create_task_summary_failure_graceful(
        self, test_session: AsyncSession
    ):
        """Test that summary generation failure is handled gracefully."""
        mock_client = MagicMock()
        mock_client.generate_task_summary = AsyncMock(
            side_effect=Exception("API Error")
        )
        service = TaskService(db=test_session, openai_client=mock_client)

        task_data = TaskCreate(
            title="Task with Failed Summary",
            description="This task will have a failed summary generation attempt.",
            generate_summary=True,
        )

        task, error = await service.create_task(task_data)

        assert task.id is not None
        assert task.summary is None  # Summary should be None on failure
        assert error is not None  # Error message should be captured


class TestTaskServiceGet:
    """Unit tests for TaskService get methods."""

    @pytest_asyncio.fixture
    async def service_with_tasks(
        self, test_session: AsyncSession, mock_openai_client
    ) -> TaskService:
        """Create a TaskService with pre-populated tasks."""
        service = TaskService(db=test_session, openai_client=mock_openai_client)

        # Create multiple tasks for testing
        for i in range(5):
            task_data = TaskCreate(
                title=f"Test Task {i}",
                description=f"This is test task number {i} for testing pagination.",
                priority=TaskPriority.MEDIUM if i % 2 == 0 else TaskPriority.HIGH,
                generate_summary=False,
            )
            await service.create_task(task_data)

        return service

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, service_with_tasks: TaskService):
        """Test retrieving a task by ID."""
        # First create a task to get
        task_data = TaskCreate(
            title="Findable Task",
            description="This task should be findable by its ID.",
        )
        created_task, _ = await service_with_tasks.create_task(task_data)

        # Now retrieve it
        found_task = await service_with_tasks.get_task_by_id(created_task.id)

        assert found_task.id == created_task.id
        assert found_task.title == "Findable Task"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service_with_tasks: TaskService):
        """Test that getting a non-existent task raises exception."""
        with pytest.raises(TaskNotFoundException):
            await service_with_tasks.get_task_by_id("non-existent-id")

    @pytest.mark.asyncio
    async def test_get_tasks_pagination(self, service_with_tasks: TaskService):
        """Test paginated task retrieval."""
        tasks, total = await service_with_tasks.get_tasks(page=1, page_size=2)

        assert len(tasks) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_tasks_filter_by_priority(self, service_with_tasks: TaskService):
        """Test filtering tasks by priority."""
        tasks, total = await service_with_tasks.get_tasks(
            page=1, page_size=10, priority=TaskPriority.HIGH
        )

        assert all(task.priority == TaskPriority.HIGH for task in tasks)


class TestTaskServiceUpdate:
    """Unit tests for TaskService.update_task method."""

    @pytest_asyncio.fixture
    async def service_with_task(
        self, test_session: AsyncSession, mock_openai_client
    ) -> tuple:
        """Create a TaskService with one task."""
        service = TaskService(db=test_session, openai_client=mock_openai_client)

        task_data = TaskCreate(
            title="Updatable Task",
            description="This task will be updated during testing.",
            priority=TaskPriority.LOW,
        )
        task, _ = await service.create_task(task_data)

        return service, task

    @pytest.mark.asyncio
    async def test_update_task_title(self, service_with_task):
        """Test updating task title."""
        service, task = service_with_task

        update_data = TaskUpdate(title="Updated Title")
        updated_task, _ = await service.update_task(task.id, update_data)

        assert updated_task.title == "Updated Title"
        assert updated_task.description == task.description  # Unchanged

    @pytest.mark.asyncio
    async def test_update_task_status(self, service_with_task):
        """Test updating task status."""
        service, task = service_with_task

        update_data = TaskUpdate(status=TaskStatus.IN_PROGRESS)
        updated_task, _ = await service.update_task(task.id, update_data)

        assert updated_task.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_update_task_regenerate_summary(self, service_with_task):
        """Test regenerating task summary."""
        service, task = service_with_task

        update_data = TaskUpdate(regenerate_summary=True)
        updated_task, _ = await service.update_task(task.id, update_data)

        assert updated_task.summary is not None  # Mock should generate summary

    @pytest.mark.asyncio
    async def test_update_non_existent_task(self, test_session: AsyncSession):
        """Test updating a non-existent task raises exception."""
        service = TaskService(db=test_session, openai_client=None)

        with pytest.raises(TaskNotFoundException):
            await service.update_task(
                "non-existent-id",
                TaskUpdate(title="New Title"),
            )


class TestTaskServiceDelete:
    """Unit tests for TaskService.delete_task method."""

    @pytest.mark.asyncio
    async def test_delete_task(self, test_session: AsyncSession, mock_openai_client):
        """Test deleting a task."""
        service = TaskService(db=test_session, openai_client=mock_openai_client)

        # Create a task
        task_data = TaskCreate(
            title="Deletable Task",
            description="This task will be deleted during testing.",
        )
        task, _ = await service.create_task(task_data)
        task_id = task.id

        # Delete it
        deleted_id = await service.delete_task(task_id)

        assert deleted_id == task_id

        # Verify it's gone
        with pytest.raises(TaskNotFoundException):
            await service.get_task_by_id(task_id)

    @pytest.mark.asyncio
    async def test_delete_non_existent_task(self, test_session: AsyncSession):
        """Test deleting a non-existent task raises exception."""
        service = TaskService(db=test_session, openai_client=None)

        with pytest.raises(TaskNotFoundException):
            await service.delete_task("non-existent-id")

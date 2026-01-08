"""
Integration tests for Task API endpoints.
Tests the full request/response cycle with mocked external dependencies.
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Integration tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestCreateTaskEndpoint:
    """Integration tests for POST /api/v1/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_success(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test successful task creation with AI summary."""
        response = await client.post("/api/v1/tasks/", json=sample_task_data)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_task_data["title"]
        assert data["description"] == sample_task_data["description"]
        assert data["priority"] == sample_task_data["priority"]
        assert data["status"] == "pending"
        assert data["id"] is not None
        assert data["summary"] is not None  # AI-generated summary

    @pytest.mark.asyncio
    async def test_create_task_without_summary(
        self, client: AsyncClient, sample_task_data_no_summary: dict
    ):
        """Test task creation without AI summary generation."""
        response = await client.post("/api/v1/tasks/", json=sample_task_data_no_summary)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_task_data_no_summary["title"]

    @pytest.mark.asyncio
    async def test_create_task_validation_error_empty_title(self, client: AsyncClient):
        """Test that empty title returns 422 validation error."""
        invalid_data = {
            "title": "",
            "description": "Valid description with enough characters.",
        }

        response = await client.post("/api/v1/tasks/", json=invalid_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_validation_error_short_description(
        self, client: AsyncClient
    ):
        """Test that short description returns 422 validation error."""
        invalid_data = {
            "title": "Valid Title",
            "description": "Short",
        }

        response = await client.post("/api/v1/tasks/", json=invalid_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_validation_error_missing_required(
        self, client: AsyncClient
    ):
        """Test that missing required fields returns 422 error."""
        invalid_data = {"priority": "high"}  # Missing title and description

        response = await client.post("/api/v1/tasks/", json=invalid_data)

        assert response.status_code == 422


class TestGetTasksEndpoint:
    """Integration tests for GET /api/v1/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_get_tasks_empty(self, client: AsyncClient):
        """Test getting tasks when none exist."""
        response = await client.get("/api/v1/tasks/")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_tasks_with_data(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test getting tasks after creating some."""
        # Create a task first
        await client.post("/api/v1/tasks/", json=sample_task_data)

        response = await client.get("/api/v1/tasks/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_tasks_pagination(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test pagination of task list."""
        # Create multiple tasks
        for i in range(5):
            task = sample_task_data.copy()
            task["title"] = f"Task {i}"
            await client.post("/api/v1/tasks/", json=task)

        # Get first page
        response = await client.get("/api/v1/tasks/?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_get_tasks_filter_by_priority(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test filtering tasks by priority."""
        # Create tasks with different priorities
        high_task = sample_task_data.copy()
        high_task["priority"] = "high"
        await client.post("/api/v1/tasks/", json=high_task)

        low_task = sample_task_data.copy()
        low_task["title"] = "Low priority task"
        low_task["priority"] = "low"
        await client.post("/api/v1/tasks/", json=low_task)

        # Filter by high priority
        response = await client.get("/api/v1/tasks/?priority=high")

        assert response.status_code == 200
        data = response.json()
        assert all(task["priority"] == "high" for task in data["tasks"])


class TestGetTaskByIdEndpoint:
    """Integration tests for GET /api/v1/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_by_id_success(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test getting a task by its ID."""
        # Create a task
        create_response = await client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Get it by ID
        response = await client.get(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == sample_task_data["title"]

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client: AsyncClient):
        """Test getting a non-existent task returns 404."""
        response = await client.get("/api/v1/tasks/non-existent-uuid")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestUpdateTaskEndpoint:
    """Integration tests for PUT /api/v1/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_success(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test updating a task."""
        # Create a task
        create_response = await client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Update it
        update_data = {
            "title": "Updated Title",
            "status": "in_progress",
        }
        response = await client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "in_progress"
        # Description should remain unchanged
        assert data["description"] == sample_task_data["description"]

    @pytest.mark.asyncio
    async def test_update_task_regenerate_summary(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test regenerating summary during update."""
        # Create a task
        create_response = await client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Update with summary regeneration
        update_data = {"regenerate_summary": True}
        response = await client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] is not None

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, client: AsyncClient):
        """Test updating a non-existent task returns 404."""
        update_data = {"title": "New Title"}
        response = await client.put(
            "/api/v1/tasks/non-existent-uuid", json=update_data
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_validation_error(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test that invalid update data returns 422."""
        # Create a task
        create_response = await client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Try invalid update
        invalid_data = {"status": "invalid_status"}
        response = await client.put(f"/api/v1/tasks/{task_id}", json=invalid_data)

        assert response.status_code == 422


class TestDeleteTaskEndpoint:
    """Integration tests for DELETE /api/v1/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_task_success(
        self, client: AsyncClient, sample_task_data: dict
    ):
        """Test deleting a task."""
        # Create a task
        create_response = await client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(f"/api/v1/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Task deleted successfully"
        assert data["deleted_id"] == task_id

        # Verify it's gone
        get_response = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, client: AsyncClient):
        """Test deleting a non-existent task returns 404."""
        response = await client.delete("/api/v1/tasks/non-existent-uuid")

        assert response.status_code == 404

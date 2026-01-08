"""
API routes for Task endpoints.
Implements POST, GET, PUT, DELETE operations.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskDeleteResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.openai_client import OpenAIClient, get_openai_client
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_task_service(
    db: AsyncSession = Depends(get_db),
    openai_client: OpenAIClient = Depends(get_openai_client),
) -> TaskService:
    """Dependency injection for TaskService."""
    return TaskService(db=db, openai_client=openai_client)


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a new task with optional AI-generated summary. "
    "The summary is generated using OpenAI's GPT model based on the task title and description.",
    responses={
        201: {"description": "Task created successfully"},
        422: {"description": "Validation error"},
        502: {"description": "External API error (summary generation failed)"},
        503: {"description": "Database connection error"},
    },
)
async def create_task(
    task_data: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Create a new task.
    
    - **title**: Task title (1-200 characters)
    - **description**: Detailed task description (10-5000 characters)
    - **priority**: Task priority (low, medium, high, critical)
    - **due_date**: Optional due date
    - **generate_summary**: Whether to generate AI summary (default: true)
    """
    task, _ = await service.create_task(task_data)
    return TaskResponse.model_validate(task)


@router.get(
    "/",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all tasks",
    description="Retrieve a paginated list of tasks with optional filtering by status and priority.",
    responses={
        200: {"description": "Tasks retrieved successfully"},
        503: {"description": "Database connection error"},
    },
)
async def get_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of tasks per page"),
    status_filter: Optional[TaskStatus] = Query(
        None, alias="status", description="Filter by task status"
    ),
    priority_filter: Optional[TaskPriority] = Query(
        None, alias="priority", description="Filter by task priority"
    ),
    service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    """
    Get paginated list of tasks.
    
    - **page**: Page number (default: 1)
    - **page_size**: Tasks per page (default: 10, max: 100)
    - **status**: Optional status filter
    - **priority**: Optional priority filter
    """
    tasks, total = await service.get_tasks(
        page=page,
        page_size=page_size,
        status=status_filter,
        priority=priority_filter,
    )
    
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a task by ID",
    description="Retrieve a single task by its unique identifier.",
    responses={
        200: {"description": "Task retrieved successfully"},
        404: {"description": "Task not found"},
        503: {"description": "Database connection error"},
    },
)
async def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Get a specific task by ID.
    
    - **task_id**: UUID of the task
    """
    task = await service.get_task_by_id(task_id)
    return TaskResponse.model_validate(task)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a task",
    description="Update an existing task. All fields are optional. "
    "Set regenerate_summary to true to generate a new AI summary.",
    responses={
        200: {"description": "Task updated successfully"},
        404: {"description": "Task not found"},
        422: {"description": "Validation error"},
        503: {"description": "Database connection error"},
    },
)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Update an existing task.
    
    - **task_id**: UUID of the task to update
    - **title**: Updated title (optional)
    - **description**: Updated description (optional)
    - **status**: Updated status (optional)
    - **priority**: Updated priority (optional)
    - **due_date**: Updated due date (optional)
    - **regenerate_summary**: Whether to regenerate AI summary (default: false)
    """
    task, _ = await service.update_task(task_id, task_data)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a task",
    description="Permanently delete a task by its ID.",
    responses={
        200: {"description": "Task deleted successfully"},
        404: {"description": "Task not found"},
        503: {"description": "Database connection error"},
    },
)
async def delete_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskDeleteResponse:
    """
    Delete a task.
    
    - **task_id**: UUID of the task to delete
    """
    deleted_id = await service.delete_task(task_id)
    return TaskDeleteResponse(
        message="Task deleted successfully",
        deleted_id=deleted_id,
    )

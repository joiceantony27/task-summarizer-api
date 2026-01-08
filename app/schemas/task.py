"""
Pydantic schemas for Task API request/response validation.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    """Base schema with common task fields."""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title (1-200 characters)",
        examples=["Complete project documentation"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed task description (10-5000 characters)",
        examples=["Write comprehensive documentation for the API including endpoints, examples, and error codes."],
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level",
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="Optional due date for the task",
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Validate that title is not just whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_must_be_meaningful(cls, v: str) -> str:
        """Validate that description has meaningful content."""
        if not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")
        if len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v.strip()


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    generate_summary: bool = Field(
        default=True,
        description="Whether to generate AI summary for the task",
    )


class TaskUpdate(BaseModel):
    """Schema for updating an existing task. All fields are optional."""
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated task title",
    )
    description: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description="Updated task description",
    )
    status: Optional[TaskStatus] = Field(
        default=None,
        description="Updated task status",
    )
    priority: Optional[TaskPriority] = Field(
        default=None,
        description="Updated task priority",
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="Updated due date",
    )
    regenerate_summary: bool = Field(
        default=False,
        description="Whether to regenerate AI summary",
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate that title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip() if v else v

    @field_validator("description")
    @classmethod
    def description_must_be_meaningful(cls, v: Optional[str]) -> Optional[str]:
        """Validate that description has meaningful content if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Description cannot be empty or whitespace only")
            if len(v.strip()) < 10:
                raise ValueError("Description must be at least 10 characters")
        return v.strip() if v else v


class TaskResponse(BaseModel):
    """Schema for task response with all fields."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique task identifier (UUID)")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    summary: Optional[str] = Field(None, description="AI-generated task summary")
    status: TaskStatus = Field(..., description="Current task status")
    priority: TaskPriority = Field(..., description="Task priority level")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""
    tasks: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., ge=0, description="Total number of tasks")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of tasks per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class TaskDeleteResponse(BaseModel):
    """Schema for task deletion response."""
    message: str = Field(..., description="Deletion confirmation message")
    deleted_id: str = Field(..., description="ID of the deleted task")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str = Field(..., description="Error detail message")
    error_code: Optional[str] = Field(None, description="Application-specific error code")


class SummaryGenerationStatus(BaseModel):
    """Schema for summary generation status in response."""
    generated: bool = Field(..., description="Whether summary was generated")
    error: Optional[str] = Field(None, description="Error message if generation failed")

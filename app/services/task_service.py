"""
Task service layer for business logic operations.
"""
import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseConnectionError, TaskNotFoundException
from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class TaskService:
    """
    Service class for task-related business logic.
    Handles CRUD operations and external API integration.
    """

    def __init__(self, db: AsyncSession, openai_client: Optional[OpenAIClient] = None):
        self.db = db
        self.openai_client = openai_client

    async def create_task(self, task_data: TaskCreate) -> Tuple[Task, Optional[str]]:
        """
        Create a new task with optional AI-generated summary.
        
        Args:
            task_data: Validated task creation data
            
        Returns:
            Tuple of (created task, summary generation error if any)
        """
        summary = None
        summary_error = None

        # Generate AI summary if requested and client is available
        if task_data.generate_summary and self.openai_client:
            try:
                summary = await self.openai_client.generate_task_summary(
                    title=task_data.title,
                    description=task_data.description,
                )
            except Exception as e:
                logger.error(f"Summary generation failed: {e}")
                summary_error = str(e)

        try:
            task = Task(
                title=task_data.title,
                description=task_data.description,
                summary=summary,
                priority=task_data.priority,
                due_date=task_data.due_date,
                status=TaskStatus.PENDING,
            )
            
            self.db.add(task)
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Created task with ID: {task.id}")
            return task, summary_error
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating task: {e}")
            raise DatabaseConnectionError(f"Failed to create task: {str(e)}")

    async def get_task_by_id(self, task_id: str) -> Task:
        """
        Retrieve a task by its ID.
        
        Args:
            task_id: UUID of the task
            
        Returns:
            Task instance
            
        Raises:
            TaskNotFoundException: If task doesn't exist
        """
        try:
            result = await self.db.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                raise TaskNotFoundException(task_id)
            
            return task
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching task {task_id}: {e}")
            raise DatabaseConnectionError(f"Failed to fetch task: {str(e)}")

    async def get_tasks(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
    ) -> Tuple[List[Task], int]:
        """
        Retrieve paginated list of tasks with optional filtering.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of tasks per page
            status: Optional status filter
            priority: Optional priority filter
            
        Returns:
            Tuple of (list of tasks, total count)
        """
        try:
            # Build query with filters
            query = select(Task)
            count_query = select(func.count()).select_from(Task)
            
            if status:
                query = query.where(Task.status == status)
                count_query = count_query.where(Task.status == status)
            
            if priority:
                query = query.where(Task.priority == priority)
                count_query = count_query.where(Task.priority == priority)
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination and ordering
            offset = (page - 1) * page_size
            query = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size)
            
            result = await self.db.execute(query)
            tasks = list(result.scalars().all())
            
            return tasks, total
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching tasks: {e}")
            raise DatabaseConnectionError(f"Failed to fetch tasks: {str(e)}")

    async def update_task(
        self, task_id: str, task_data: TaskUpdate
    ) -> Tuple[Task, Optional[str]]:
        """
        Update an existing task.
        
        Args:
            task_id: UUID of the task to update
            task_data: Validated update data
            
        Returns:
            Tuple of (updated task, summary generation error if any)
        """
        task = await self.get_task_by_id(task_id)
        summary_error = None

        try:
            # Update provided fields
            update_data = task_data.model_dump(exclude_unset=True, exclude={"regenerate_summary"})
            
            for field, value in update_data.items():
                if value is not None:
                    setattr(task, field, value)

            # Regenerate summary if requested
            if task_data.regenerate_summary and self.openai_client:
                try:
                    new_summary = await self.openai_client.generate_task_summary(
                        title=task.title,
                        description=task.description,
                    )
                    if new_summary:
                        task.summary = new_summary
                except Exception as e:
                    logger.error(f"Summary regeneration failed: {e}")
                    summary_error = str(e)

            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Updated task with ID: {task.id}")
            return task, summary_error
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating task {task_id}: {e}")
            raise DatabaseConnectionError(f"Failed to update task: {str(e)}")

    async def delete_task(self, task_id: str) -> str:
        """
        Delete a task by its ID.
        
        Args:
            task_id: UUID of the task to delete
            
        Returns:
            ID of deleted task
            
        Raises:
            TaskNotFoundException: If task doesn't exist
        """
        task = await self.get_task_by_id(task_id)

        try:
            await self.db.delete(task)
            await self.db.commit()
            
            logger.info(f"Deleted task with ID: {task_id}")
            return task_id
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting task {task_id}: {e}")
            raise DatabaseConnectionError(f"Failed to delete task: {str(e)}")

"""
External API client for OpenAI integration with retry logic and error handling.
"""
import logging
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import ExternalAPIError, ExternalAPITimeoutError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Async HTTP client for OpenAI API with built-in resilience.
    
    Features:
    - Automatic retry with exponential backoff
    - Timeout handling
    - Proper error mapping
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = settings.OPENAI_API_URL
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.EXTERNAL_API_TIMEOUT
        self.max_retries = settings.EXTERNAL_API_MAX_RETRIES

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _make_request(self, payload: dict) -> dict:
        """
        Make an async HTTP request to OpenAI API with retry logic.
        
        Args:
            payload: Request payload for the API
            
        Returns:
            API response as dictionary
            
        Raises:
            ExternalAPIError: If the API request fails
            ExternalAPITimeoutError: If the request times out
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code == 401:
                    raise ExternalAPIError(
                        message="OpenAI API authentication failed",
                        service="OpenAI",
                        original_error="Invalid API key",
                    )
                
                if response.status_code == 429:
                    raise ExternalAPIError(
                        message="OpenAI API rate limit exceeded",
                        service="OpenAI",
                        original_error="Rate limit exceeded",
                    )
                
                if response.status_code >= 500:
                    raise ExternalAPIError(
                        message="OpenAI API server error",
                        service="OpenAI",
                        original_error=f"HTTP {response.status_code}",
                    )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException as e:
                logger.error(f"OpenAI API timeout: {e}")
                raise ExternalAPITimeoutError(
                    service="OpenAI",
                    timeout=self.timeout,
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API HTTP error: {e}")
                raise ExternalAPIError(
                    message="OpenAI API request failed",
                    service="OpenAI",
                    original_error=str(e),
                )
            except httpx.NetworkError as e:
                logger.error(f"OpenAI API network error: {e}")
                raise ExternalAPIError(
                    message="Network error connecting to OpenAI API",
                    service="OpenAI",
                    original_error=str(e),
                )

    async def generate_task_summary(self, title: str, description: str) -> Optional[str]:
        """
        Generate a concise summary for a task using OpenAI GPT.
        
        Args:
            title: Task title
            description: Task description
            
        Returns:
            Generated summary string or None if generation fails
        """
        if not self.api_key:
            logger.warning("OpenAI API key not configured, skipping summary generation")
            return None

        prompt = f"""You are a task management assistant. Generate a brief, actionable summary (2-3 sentences max) for the following task.

Task Title: {title}

Task Description: {description}

Summary:"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise task summaries.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "max_tokens": 150,
            "temperature": 0.7,
        }

        try:
            response = await self._make_request(payload)
            
            if "choices" in response and len(response["choices"]) > 0:
                summary = response["choices"][0]["message"]["content"].strip()
                logger.info(f"Successfully generated summary for task: {title[:50]}...")
                return summary
            
            logger.warning("OpenAI API returned empty response")
            return None
            
        except (ExternalAPIError, ExternalAPITimeoutError) as e:
            logger.error(f"Failed to generate summary: {e.message}")
            # Return None instead of raising - summary generation is non-critical
            return None


# Singleton instance
openai_client = OpenAIClient()


async def get_openai_client() -> OpenAIClient:
    """Dependency injection for OpenAI client."""
    return openai_client

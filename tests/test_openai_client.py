"""
Unit tests for OpenAI client service.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import ExternalAPIError, ExternalAPITimeoutError
from app.services.openai_client import OpenAIClient


class TestOpenAIClient:
    """Unit tests for OpenAI client."""

    @pytest.fixture
    def client(self):
        """Create an OpenAI client instance."""
        with patch("app.services.openai_client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-api-key"
            mock_settings.OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
            mock_settings.OPENAI_MODEL = "gpt-3.5-turbo"
            mock_settings.EXTERNAL_API_TIMEOUT = 30
            mock_settings.EXTERNAL_API_MAX_RETRIES = 3
            return OpenAIClient()

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, client):
        """Test successful summary generation."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a generated summary."
                    }
                }
            ]
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            summary = await client.generate_task_summary(
                title="Test Task",
                description="Test description for the task.",
            )

            assert summary == "This is a generated summary."
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_no_api_key(self):
        """Test that missing API key returns None gracefully."""
        with patch("app.services.openai_client.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
            mock_settings.OPENAI_MODEL = "gpt-3.5-turbo"
            mock_settings.EXTERNAL_API_TIMEOUT = 30
            mock_settings.EXTERNAL_API_MAX_RETRIES = 3

            client = OpenAIClient()
            summary = await client.generate_task_summary(
                title="Test",
                description="Test description",
            )

            assert summary is None

    @pytest.mark.asyncio
    async def test_generate_summary_api_error(self, client):
        """Test that API errors are handled gracefully."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = ExternalAPIError(
                message="API Error",
                service="OpenAI",
            )

            summary = await client.generate_task_summary(
                title="Test",
                description="Test description",
            )

            assert summary is None

    @pytest.mark.asyncio
    async def test_generate_summary_timeout(self, client):
        """Test that timeout errors are handled gracefully."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = ExternalAPITimeoutError(
                service="OpenAI",
                timeout=30,
            )

            summary = await client.generate_task_summary(
                title="Test",
                description="Test description",
            )

            assert summary is None

    @pytest.mark.asyncio
    async def test_generate_summary_empty_response(self, client):
        """Test handling of empty API response."""
        mock_response = {"choices": []}

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            summary = await client.generate_task_summary(
                title="Test",
                description="Test description",
            )

            assert summary is None

    def test_get_headers(self, client):
        """Test that headers include authorization."""
        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Content-Type"] == "application/json"

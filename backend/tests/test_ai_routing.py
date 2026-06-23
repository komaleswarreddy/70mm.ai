import pytest
from unittest.mock import MagicMock, patch
from app import ai_service
from app.config import settings

@pytest.mark.asyncio
async def test_ai_routing_openai_to_gemini_failover():
    with patch.object(settings, "OPENAI_API_KEY", "mock-openai-key"), \
         patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"):
         
        # Simulate OpenAI failing and Gemini succeeding
        async def mock_post(url, *args, **kwargs):
            mock_response = MagicMock()
            if "api.openai.com" in str(url):
                # Simulate OpenAI exception
                mock_response.raise_for_status.side_effect = Exception("OpenAI API rate limit or outage")
            elif "generativelanguage.googleapis.com" in str(url):
                mock_response.raise_for_status = MagicMock()
                mock_response.json = MagicMock(return_value={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "{\"status\": \"gemini_fallback_success\"}"}
                                ]
                            }
                        }
                    ]
                })
            return mock_response

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            result = await ai_service.call_gemini_api("Generate something")
            assert result == "{\"status\": \"gemini_fallback_success\"}"

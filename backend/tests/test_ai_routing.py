import pytest
from unittest.mock import MagicMock, patch
from app import ai_service
from app.config import settings


def _chat_completion(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"choices": [{"message": {"content": content}}]})
    return mock_response


@pytest.mark.asyncio
async def test_ai_routing_uses_groq_gpt_oss_120b_first():
    sent = []

    async def mock_post(url, *args, **kwargs):
        sent.append((str(url), kwargs.get("json", {}).get("model")))
        return _chat_completion("{\"status\": \"groq_success\"}")

    with patch.object(settings, "GROQ_API_KEY", "mock-groq-key"), \
         patch("httpx.AsyncClient.post", side_effect=mock_post):
        result = await ai_service.call_llm("Generate something")

    assert result == "{\"status\": \"groq_success\"}"
    assert sent == [("https://api.groq.com/openai/v1/chat/completions", "openai/gpt-oss-120b")]


@pytest.mark.asyncio
async def test_ai_routing_groq_to_openai_failover_never_touches_gemini():
    urls = []

    async def mock_post(url, *args, **kwargs):
        urls.append(str(url))
        if "api.groq.com" in str(url):
            failing = MagicMock()
            failing.raise_for_status.side_effect = Exception("Groq outage")
            return failing
        return _chat_completion("{\"status\": \"openai_fallback_success\"}")

    with patch.object(settings, "GROQ_API_KEY", "mock-groq-key"), \
         patch.object(settings, "OPENAI_API_KEY", "mock-openai-key"), \
         patch("httpx.AsyncClient.post", side_effect=mock_post):
        result = await ai_service.call_llm("Generate something")

    assert result == "{\"status\": \"openai_fallback_success\"}"
    assert any("api.openai.com" in u for u in urls)
    assert not any("googleapis" in u or "gemini" in u for u in urls)


def test_no_gemini_code_path_exists():
    assert not hasattr(ai_service, "call_gemini")
    assert not hasattr(ai_service, "call_gemini_api")
    assert not hasattr(settings, "GEMINI_API_KEY")

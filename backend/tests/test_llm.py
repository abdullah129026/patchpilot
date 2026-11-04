import pytest

from app.llm import BedrockClient, GroqClient, ProviderUnavailable


def test_bedrock_without_model_id_is_unavailable(monkeypatch):
    monkeypatch.delenv("PATCHPILOT_BEDROCK_MODEL_ID", raising=False)
    with pytest.raises(ProviderUnavailable):
        BedrockClient(model_id="")


def test_groq_without_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ProviderUnavailable):
        GroqClient(api_key="")

import sys
import types

import pytest

from app.llm import BedrockClient, GroqClient, ProviderUnavailable


def test_bedrock_without_model_id_is_unavailable(monkeypatch):
    monkeypatch.delenv("PATCHPILOT_BEDROCK_MODEL_ID", raising=False)
    with pytest.raises(ProviderUnavailable):
        BedrockClient(model_id="")


def _fake_boto3(monkeypatch):
    """Install a fake boto3 that records how client() was called."""
    calls = {}

    class FakeBedrock:
        def converse(self, **kwargs):
            return {"output": {"message": {"content": [{"text": "hi"}]}}}

    fake = types.ModuleType("boto3")

    def client(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return FakeBedrock()

    fake.client = client
    monkeypatch.setitem(sys.modules, "boto3", fake)
    return calls


def test_bedrock_passes_aws_region_to_boto3(monkeypatch):
    # botocore on the host ignores AWS_REGION, so the client must get
    # the region explicitly or client creation dies with NoRegionError.
    calls = _fake_boto3(monkeypatch)
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    assert BedrockClient(model_id="m").complete("hello") == "hi"
    assert calls["args"] == ("bedrock-runtime",)
    assert calls["kwargs"].get("region_name") == "eu-central-1"


def test_bedrock_falls_back_to_aws_default_region(monkeypatch):
    calls = _fake_boto3(monkeypatch)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
    assert BedrockClient(model_id="m").complete("hello") == "hi"
    assert calls["kwargs"].get("region_name") == "ap-south-1"


def test_bedrock_without_region_env_passes_none(monkeypatch):
    calls = _fake_boto3(monkeypatch)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    assert BedrockClient(model_id="m").complete("hello") == "hi"
    assert calls["kwargs"].get("region_name") is None


def test_groq_without_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ProviderUnavailable):
        GroqClient(api_key="")

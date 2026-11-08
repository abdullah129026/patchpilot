import sys
import types

import pytest

from app.llm import BedrockClient, GroqClient, ProviderUnavailable


def test_bedrock_without_model_id_is_unavailable(monkeypatch):
    monkeypatch.delenv("PATCHPILOT_BEDROCK_MODEL_ID", raising=False)
    with pytest.raises(ProviderUnavailable):
        BedrockClient(model_id="")


def _fake_boto3(monkeypatch, usage=None):
    """Install a fake boto3 that records how client() was called."""
    calls = {}

    class FakeBedrock:
        def converse(self, **kwargs):
            resp = {"output": {"message": {"content": [{"text": "hi"}]}}}
            if usage is not None:
                resp["usage"] = usage
            return resp

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


def test_bedrock_records_token_usage(monkeypatch):
    _fake_boto3(monkeypatch, usage={"inputTokens": 100, "outputTokens": 20})
    client = BedrockClient(model_id="m")
    assert client.complete("hello") == "hi"
    assert client.last_usage == {"input": 100, "output": 20}


def test_bedrock_without_usage_leaves_last_usage_empty(monkeypatch):
    _fake_boto3(monkeypatch)
    client = BedrockClient(model_id="m")
    assert client.complete("hello") == "hi"
    assert client.last_usage is None


def test_groq_records_token_usage(monkeypatch):
    import httpx

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    client = GroqClient(api_key="k")
    assert client.complete("hello") == "hi"
    assert client.last_usage == {"input": 50, "output": 10}

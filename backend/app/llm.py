"""LLM client behind one interface (Phase 0, ADR-003, D8 amended).

The pipeline only ever calls complete(prompt) and treats the reply
as a proposal: verdicts are computed from container evidence, never
from this output. Bedrock is primary (Activate credits); Groq free
stays as fallback. Neither client logs keys, and a missing provider
raises ProviderUnavailable instead of inventing a reply, so the
pipeline can report an honest failed state rather than a fake verdict.
"""

import os

import httpx

from app import config


class ProviderUnavailable(Exception):
    pass


class LLMClient:
    def complete(self, prompt: str) -> str:
        raise NotImplementedError


class BedrockClient(LLMClient):
    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or config.BEDROCK_MODEL_ID
        if not self.model_id:
            raise ProviderUnavailable(
                "No Bedrock model id is configured "
                "(PATCHPILOT_BEDROCK_MODEL_ID). The Phase 3 fixture "
                "suite records the arbitration winner here."
            )

    def complete(self, prompt: str) -> str:
        try:
            import boto3
        except ImportError as exc:
            raise ProviderUnavailable(
                "boto3 is not installed, so Bedrock cannot be reached "
                "from this host."
            ) from exc
        try:
            client = boto3.client("bedrock-runtime")
            resp = client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
            )
            return "".join(
                block.get("text", "") for block in resp["output"]["message"]["content"]
            )
        except Exception as exc:
            # Never include the exception chain's credentials or raw
            # request in the message; the class name is enough to act on.
            raise ProviderUnavailable(
                f"Bedrock request failed: {type(exc).__name__}"
            ) from exc


class GroqClient(LLMClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = model or config.GROQ_MODEL
        if not self.api_key:
            raise ProviderUnavailable("GROQ_API_KEY is not set.")

    def complete(self, prompt: str) -> str:
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"Groq request failed: {type(exc).__name__}"
            ) from exc
        if resp.status_code != 200:
            raise ProviderUnavailable(f"Groq returned {resp.status_code}")
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderUnavailable("Groq returned an unexpected shape") from exc


def build_llm_client() -> LLMClient:
    if config.LLM_PROVIDER == "bedrock":
        return BedrockClient()
    if config.LLM_PROVIDER == "groq":
        return GroqClient()
    raise ProviderUnavailable(f"Unknown LLM provider: {config.LLM_PROVIDER}")

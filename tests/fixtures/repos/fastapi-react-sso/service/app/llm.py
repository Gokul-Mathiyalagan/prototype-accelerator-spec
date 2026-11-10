"""The one place this service calls a model: Azure OpenAI through a small gateway."""

import logging
from pathlib import Path

from app import settings

log = logging.getLogger("team_insights.llm")
PROMPTS = Path(__file__).parent / "prompts"


class LlmGateway:
    """Wraps the Azure OpenAI client: one deployment, retries, and token logging."""

    def __init__(self) -> None:
        self._client = None
        if settings.LLM_MODE == "azure":
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version="2024-10-21",
                max_retries=3,
            )

    def complete(self, prompt_name: str, **values: str) -> str:
        template = (PROMPTS / f"{prompt_name}.prompt.md").read_text()
        prompt = template.format(**values)
        if self._client is None:
            return f"[fake summary of {len(prompt)} characters]"
        response = self._client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = response.usage
        log.info("llm call %s used %s tokens", prompt_name, usage.total_tokens if usage else 0)
        return response.choices[0].message.content or ""


gateway = LlmGateway()

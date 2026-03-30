"""OpenAI API wrapper with retry logic."""

import json
import logging
import time

from openai import OpenAI

log = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 1000, temperature: float = 0.2):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.total_tokens_used = 0

    def call_json(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> dict | None:
        """Call GPT-4o with JSON mode, return parsed dict or None on failure."""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                usage = response.usage
                if usage:
                    self.total_tokens_used += usage.total_tokens
                    log.debug(f"Tokens used: {usage.total_tokens} (total: {self.total_tokens_used})")

                content = response.choices[0].message.content
                return json.loads(content)

            except Exception as e:
                wait = 2 ** attempt
                log.warning(f"OpenAI 呼叫失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    log.info(f"等待 {wait}s 後重試...")
                    time.sleep(wait)

        log.error("OpenAI 呼叫已達最大重試次數，跳過此筆")
        return None

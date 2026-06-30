from __future__ import annotations

import re

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential


class DraftGenerator:
    def __init__(self, api_key: str, model: str = "qwen/qwen3-32b", client=None):
        if not api_key and client is None:
            raise ValueError("GROQ_API_KEY is required")
        self.client = client or Groq(api_key=api_key)
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def generate(self, subject: str, sender: str, body: str) -> str:
        prompt = f"""Write a concise, professional reply to this email.

Rules:
- Return only the final email body.
- Do not include analysis, reasoning, notes, summaries, XML tags, markdown, or explanations.
- Never include <think>, </think>, <penser>, </penser>, "reasoning", or internal thoughts.
- Detect the email language and reply in the same language, French or English.
- Preserve relevant context.
- Do not claim actions you cannot verify.
- Never send email; only compose draft text.

From: {sender}
Subject: {subject}
Message:
{body[:12000]}"""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.25,
            max_completion_tokens=400,
            messages=[
                {
                    "role": "system",
                    "content": "You write only the final email body. No reasoning, no analysis, no tags.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return clean_draft(response.choices[0].message.content)


def clean_draft(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<penser>.*?</penser>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<analysis>.*?</analysis>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"(?is)^.*?</think>\s*", "", cleaned)
    cleaned = re.sub(r"(?is)^.*?</penser>\s*", "", cleaned)
    cleaned = re.sub(r"(?is)^.*?</analysis>\s*", "", cleaned)
    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    cleaned = cleaned.replace("<penser>", "").replace("</penser>", "")
    cleaned = cleaned.replace("<analysis>", "").replace("</analysis>", "")
    cleaned = cleaned.strip()

    # Some reasoning models emit a short preface before the useful draft. Keep
    # the first plausible greeting if present.
    greetings = ("Bonjour", "Bonsoir", "Madame", "Monsieur", "Hello", "Hi", "Dear")
    positions = [cleaned.find(greeting) for greeting in greetings if cleaned.find(greeting) >= 0]
    if positions:
        cleaned = cleaned[min(positions):].strip()

    return cleaned

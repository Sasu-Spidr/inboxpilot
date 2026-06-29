from __future__ import annotations
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
        prompt = f'''Write a concise, professional reply to this email. Preserve relevant context. Detect the email language and reply in it (French or English). Do not claim actions you cannot verify. Return only the email body, no subject.
From: {sender}\nSubject: {subject}\nMessage:\n{body[:12000]}'''
        response = self.client.chat.completions.create(
            model=self.model, temperature=0.35, max_completion_tokens=500,
            messages=[{"role": "system", "content": "You draft helpful business emails. Never send email; only compose text."},
                      {"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()


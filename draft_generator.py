from __future__ import annotations

import logging
import re

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

LOG = logging.getLogger(__name__)


class DraftGenerator:
    def __init__(self, api_key: str, model: str = "qwen/qwen3-32b", client=None):
        if not api_key and client is None:
            raise ValueError("GROQ_API_KEY is required")
        self.client = client or Groq(api_key=api_key)
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def generate(self, subject: str, sender: str, body: str, signature_name: str = "") -> str:
        signature_rule = (
            f'- End with exactly this signature name: "{signature_name}".'
            if signature_name
            else "- End with a polite closing, but do not invent a personal name."
        )
        prompt = f"""Write a concise, professional reply to this email.

Rules:
- Return only the final email body.
- Do not include analysis, reasoning, notes, summaries, XML tags, markdown, or explanations.
- Never include <think>, </think>, <penser>, </penser>, "reasoning", or internal thoughts.
- Detect the email language and reply in the same language, French or English.
- Preserve relevant context.
- Be useful but concise: 4 to 7 short lines maximum unless the email explicitly requires more.
- Answer the concrete request first.
- If the sender asks for a call, propose a simple next step without inventing availability.
- Do not claim actions you cannot verify.
- Never send email; only compose draft text.
{signature_rule}

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
                    "content": "You write only the final email body. Be concise, helpful, and safe. No reasoning, no analysis, no tags.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return clean_draft(response.choices[0].message.content)

    def safe_generate(self, subject: str, sender: str, body: str, signature_name: str = "") -> str:
        try:
            return self.generate(subject, sender, body, signature_name=signature_name)
        except Exception:
            LOG.exception("Draft generation failed; using fallback draft")
            return fallback_draft(subject, body, signature_name)


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

    cleaned = re.sub(r"\[Votre nom\]|\[Your name\]|\[Nom\]", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def fallback_draft(subject: str, body: str, signature_name: str = "") -> str:
    signature = f"\n\nCordialement,\n{signature_name}" if signature_name else "\n\nCordialement,"
    if looks_english(f"{subject}\n{body[:1000]}"):
        signature = f"\n\nBest regards,\n{signature_name}" if signature_name else "\n\nBest regards,"
        return (
            "Hello,\n\n"
            "Thank you for your message. I have received it and will get back to you with the necessary information as soon as possible."
            f"{signature}"
        )
    return (
        "Bonjour,\n\n"
        "Merci pour votre message. Je l'ai bien reçu et je reviens vers vous dès que possible avec les éléments nécessaires."
        f"{signature}"
    )


def looks_english(text: str) -> bool:
    lowered = text.lower()
    english_markers = ("hello", "hi ", "dear", "meeting", "invoice", "payment", "please", "thank you", "regards")
    french_markers = ("bonjour", "merci", "facture", "paiement", "veuillez", "cordialement", "rendez-vous")
    return sum(marker in lowered for marker in english_markers) > sum(marker in lowered for marker in french_markers)

"""
utils/cerebras.py — Cerebras Cloud SDK client for RepoReady.

Two models available:
  FAST  (llama3.1-8b) → Layer 2 (research summarization)
  POWER (llama3.1-8b) → Layer 3 (guide generation)
"""

import json
import asyncio
from typing import TypeVar, Type

from cerebras.cloud.sdk import Cerebras
from pydantic import BaseModel

from config import settings


T = TypeVar("T", bound=BaseModel)


def _strip_markdown_fences(raw: str) -> str:
    """
    Extract the JSON portion from an LLM response.
    Finds the first '{' or '[' and the last '}' or ']' to handle 
    conversational prefixes, suffixes, and markdown fences.
    """
    raw = raw.strip()
    
    start_idx = -1
    end_idx = -1
    
    for i, char in enumerate(raw):
        if char in ('{', '['):
            start_idx = i
            break
            
    for i in range(len(raw) - 1, -1, -1):
        if raw[i] in ('}', ']'):
            end_idx = i
            break
            
    if start_idx != -1 and end_idx != -1 and start_idx <= end_idx:
        return raw[start_idx:end_idx + 1]
        
    return raw


def _get_client() -> Cerebras:
    """Create a Cerebras client using the API key from settings."""
    return Cerebras(api_key=settings.CEREBRAS_API_KEY)


def _sync_chat(model: str, prompt: str, temperature: float) -> str:
    """
    Synchronous Cerebras chat completion call.
    Returns the raw response text.
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise JSON generator. "
                    "Always respond with valid JSON only. "
                    "No markdown, no explanations, no extra text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


async def cerebras_generate(
    prompt: str,
    response_model: Type[T],
    model: str = "llama3.1-8b",
    temperature: float = 0.3,
) -> T:
    """
    Send a prompt to a Cerebras model and parse the response
    into the given Pydantic model.

    Args:
        prompt: The full prompt string.
        response_model: Pydantic class to parse the JSON into.
        model: Which Cerebras model to use (FAST or POWER).
        temperature: Sampling temperature (0.3 for research, 0.7 for generation).

    Returns:
        An instance of response_model.

    Raises:
        ValueError: If JSON parsing fails.
        Exception: On Cerebras API failure.
    """
    try:
        # Cerebras SDK is synchronous — run in thread
        raw = await asyncio.to_thread(_sync_chat, model, prompt, temperature)
        cleaned = _strip_markdown_fences(raw)

        try:
            # Use raw_decode to parse only the first JSON object
            # and ignore any trailing text the LLM appends.
            # strict=False allows unescaped control characters (like \n) inside strings.
            decoder = json.JSONDecoder(strict=False)
            data, _ = decoder.raw_decode(cleaned)
        except json.JSONDecodeError as je:
            raise ValueError(
                f"[cerebras] Failed to parse JSON from Cerebras response: {je}\n"
                f"Raw response (first 500 chars): {raw[:500]}"
            )

        return response_model(**data)

    except ValueError:
        raise
    except Exception as exc:
        raise Exception(f"[cerebras] Cerebras API call failed: {exc}") from exc

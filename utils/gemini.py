"""
utils/gemini.py — Gemini 1.5 Flash client for RepoReady.

Provides a single async function to send prompts to Gemini
and parse the JSON response into a Pydantic model.
"""

import json
import asyncio
from typing import TypeVar, Type

from google import genai
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


def _get_client() -> genai.Client:
    """Create a Gemini client using the API key from settings."""
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def gemini_generate(
    prompt: str,
    response_model: Type[T],
    temperature: float = 0.3,
) -> T:
    """
    Send a prompt to Gemini 1.5 Flash and parse the response
    into the given Pydantic model.

    Args:
        prompt: The full prompt string to send.
        response_model: The Pydantic class to parse the JSON response into.
        temperature: Sampling temperature (default 0.3 for precision).

    Returns:
        An instance of response_model populated from the AI response.

    Raises:
        ValueError: If the response cannot be parsed into valid JSON.
        Exception: On any Gemini API communication failure.
    """
    try:
        client = _get_client()

        # google-genai SDK generate_content is synchronous — run in thread
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-flash-latest",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        cleaned = _strip_markdown_fences(raw)

        try:
            # Use raw_decode to parse only the first JSON object
            # and ignore any trailing text Gemini appends.
            # strict=False allows unescaped control characters (like \n) inside strings.
            decoder = json.JSONDecoder(strict=False)
            data, _ = decoder.raw_decode(cleaned)
        except json.JSONDecodeError as je:
            raise ValueError(
                f"[gemini] Failed to parse JSON from Gemini response: {je}\n"
                f"Raw response (first 500 chars): {raw[:500]}"
            )

        return response_model(**data)

    except ValueError:
        raise
    except Exception as exc:
        raise Exception(f"[gemini] Gemini API call failed: {exc}") from exc

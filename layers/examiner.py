"""
layers/examiner.py — Layer 4: Validator

Uses Gemini 1.5 Flash to validate and auto-fix the SetupGuide.
Checks logical step ordering, command syntax, missing prerequisites,
and overall completeness. Retries up to EXAMINER_MAX_RETRIES times.
"""

import json

from config import settings
from models.schemas import SetupGuide, ValidatedGuide
from utils.gemini import gemini_generate


VALIDATOR_PROMPT_TEMPLATE = """
You are a senior developer reviewer for RepoReady, a tool that generates
beginner-friendly setup guides for GitHub repositories.

You have been given a generated setup guide. Your job is to:
1. Validate logical step ordering (clone before install, install before run).
2. Check command syntax correctness for the detected language/framework.
3. Identify missing prerequisites that should be listed.
4. Ensure the guide is complete (has clone, install, configure, and run steps at minimum).
5. Fix any issues you find AUTOMATICALLY — do not just flag them.

=== GENERATED SETUP GUIDE ===
{guide_json}

Return a CORRECTED and VALIDATED JSON object with this EXACT structure:
{{
  "repo_overview": {{
    "name": "<string>",
    "description": "<string>",
    "language": "<string>",
    "stars": <integer>,
    "topics": [<strings>],
    "plain_explanation": "<string>"
  }},
  "prerequisites": [
    {{
      "name": "<string>",
      "version": "<string>",
      "why": "<string>",
      "download_url": "<string or empty>",
      "status": "<required | optional>"
    }}
  ],
  "dependency_health": {{
    "score": <integer 1-100>,
    "healthy": <integer>,
    "warnings": <integer>,
    "critical": <integer>,
    "details": [
      {{
        "name": "<string>",
        "status": "<healthy | warning | critical>",
        "message": "<string>"
      }}
    ]
  }},
  "setup_steps": [
    {{
      "step_number": <integer>,
      "title": "<string>",
      "command": "<string>",
      "what_it_does": "<string>",
      "what_you_learn": "<string>"
    }}
  ],
  "tech_stack": [
    {{
      "name": "<string>",
      "role": "<string>",
      "explanation": "<string>"
    }}
  ],
  "common_errors": [
    {{
      "error": "<string>",
      "why": "<string>",
      "fix": "<string>"
    }}
  ]
}}

Validation checklist:
- Step numbers must be sequential starting from 1.
- First step should involve cloning the repository.
- Dependencies install step must come before the run step.
- All commands must use correct syntax for the language (e.g. npm install, pip install -r requirements.txt).
- Prerequisites must have valid download URLs where possible.
- There must be at least 3 common_errors entries.
- The plain_explanation must be genuinely beginner-friendly.

If the guide is already correct, return it unchanged but still as valid JSON.
Return ONLY valid JSON. No markdown, no explanations.
"""


async def run_examiner(guide: SetupGuide) -> ValidatedGuide:
    """
    Layer 4 — Validator.

    Validates the SetupGuide using Gemini 1.5 Flash.
    Retries up to EXAMINER_MAX_RETRIES times if validation/parsing fails.

    Args:
        guide: The SetupGuide from Layer 3 to validate.

    Returns:
        A ValidatedGuide — the finalized, checked guide.

    Raises:
        Exception: If validation fails after all retries.
    """
    guide_json = json.dumps(guide.model_dump(), indent=2)
    last_error = None

    for attempt in range(1, settings.EXAMINER_MAX_RETRIES + 1):
        try:
            prompt = VALIDATOR_PROMPT_TEMPLATE.format(guide_json=guide_json)

            validated = await gemini_generate(
                prompt=prompt,
                response_model=ValidatedGuide,
                temperature=0.2,
            )

            # Ensure step numbers are sequential
            for i, step in enumerate(validated.setup_steps):
                step.step_number = i + 1

            return validated

        except Exception as exc:
            last_error = exc
            print(
                f"[examiner] Validation attempt {attempt}/{settings.EXAMINER_MAX_RETRIES} "
                f"failed: {exc}"
            )

    raise Exception(
        f"[examiner] Validation failed after {settings.EXAMINER_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )

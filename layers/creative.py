"""
layers/creative.py — Layer 3: Guide Generator

Takes RepoDNA + DependencyReport and uses Cerebras Llama 70B
to generate a complete, beginner-friendly SetupGuide.
"""

import json

from config import settings
from models.schemas import RepoDNA, DependencyReport, SetupGuide
from utils.cerebras import cerebras_generate


GUIDE_PROMPT_TEMPLATE = """
You are RepoReady — an expert developer tool that creates beginner-friendly
setup guides for GitHub repositories. You must generate a complete, accurate
setup guide based on the repository analysis and dependency research below.

=== REPOSITORY DNA ===
{repo_dna_json}

=== DEPENDENCY RESEARCH REPORT ===
{dependency_report_json}

Generate a JSON object with this EXACT structure:
{{
  "repo_overview": {{
    "name": "{repo_name}",
    "description": "{repo_description}",
    "language": "{repo_language}",
    "stars": {repo_stars},
    "topics": {repo_topics_json},
    "plain_explanation": "<3-4 sentence explanation of what this project does and why someone would use it. Write as if explaining to a smart person who has never programmed.>"
  }},
  "prerequisites": [
    {{
      "name": "<e.g. Node.js, Python, Docker>",
      "version": "<recommended version, e.g. '18.x LTS' or '3.11+'>",
      "why": "<1 sentence — why this is needed>",
      "download_url": "<official download page URL>",
      "status": "<required | optional>"
    }}
  ],
  "dependency_health": {dependency_health_json},
  "setup_steps": [
    {{
      "step_number": 1,
      "title": "<clear step title, e.g. 'Clone the repository'>",
      "command": "<the exact terminal command to run>",
      "what_it_does": "<1-2 sentences explaining what this command does>",
      "what_you_learn": "<1 sentence about what concept this step teaches>"
    }}
  ],
  "tech_stack": [
    {{
      "name": "<technology name>",
      "role": "<its role in the project>",
      "explanation": "<1-2 sentence beginner-friendly explanation>"
    }}
  ],
  "common_errors": [
    {{
      "error": "<exact error message or pattern a beginner might see>",
      "why": "<1-2 sentences explaining why this happens>",
      "fix": "<step-by-step fix instructions>"
    }}
  ]
}}

Rules:
1. Setup steps MUST be in the correct logical order (clone → install deps → configure → run).
2. Include at least 5-8 setup steps covering the full journey from clone to running the app.
3. Commands must use the correct package manager detected from the repo (npm, pip, cargo, etc.).
4. Include at least 3 common errors that beginners are likely to encounter.
5. Prerequisites must include download URLs from official sources.
6. The plain_explanation in repo_overview should be genuinely helpful for a complete beginner.
7. If the repo has a .env.example or environment variables, include a step for configuring them.
8. Return ONLY valid JSON. No markdown, no commentary.
"""


async def run_creative(repo_dna: RepoDNA, dep_report: DependencyReport) -> SetupGuide:
    """
    Layer 3 — Guide Generator.

    Takes the structured RepoDNA from Layer 1 and the DependencyReport from
    Layer 2, then uses Cerebras Llama 70B to generate a complete SetupGuide.

    Args:
        repo_dna: Structured repository analysis from Layer 1.
        dep_report: Dependency health and research notes from Layer 2.

    Returns:
        A SetupGuide model containing the complete beginner-friendly guide.

    Raises:
        Exception: If the guide generation fails.
    """
    try:
        repo_dna_dict = repo_dna.model_dump()
        dep_report_dict = dep_report.model_dump()

        prompt = GUIDE_PROMPT_TEMPLATE.format(
            repo_dna_json=json.dumps(repo_dna_dict, indent=2),
            dependency_report_json=json.dumps(dep_report_dict, indent=2),
            repo_name=repo_dna.repo_overview.name,
            repo_description=repo_dna.repo_overview.description or "No description provided",
            repo_language=repo_dna.repo_overview.language,
            repo_stars=repo_dna.repo_overview.stars,
            repo_topics_json=json.dumps(repo_dna.repo_overview.topics),
            dependency_health_json=json.dumps(dep_report_dict["dependency_health"], indent=2),
        )

        guide = await cerebras_generate(
            prompt=prompt,
            response_model=SetupGuide,
            model=settings.CEREBRAS_POWER_MODEL,
            temperature=0.7,
        )

        return guide

    except Exception as exc:
        raise Exception(f"[creative] Guide generation failed: {exc}") from exc

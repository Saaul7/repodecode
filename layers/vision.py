"""
layers/vision.py — Layer 1: Repo Vision

Fetches all repository data from GitHub, then uses Gemini 1.5 Flash
to analyze the content and produce a structured RepoDNA model.
"""

import json

from models.schemas import RepoDNA
from utils.github import fetch_all_repo_data, parse_github_url, GitHubAuthError, GitHubNotFoundError
from utils.gemini import gemini_generate


VISION_PROMPT_TEMPLATE = """
You are an expert developer tool that analyzes GitHub repositories.
You have been given the following data about a repository. Analyze it
and return a structured JSON response.

=== REPOSITORY METADATA ===
{meta_json}

=== README (first 8000 chars) ===
{readme}

=== FILE TREE (first 500 files) ===
{file_tree}

=== PACKAGE / DEPENDENCY FILES ===
{package_files}

=== .env.example ===
{env_example}

Based on the above information, produce a JSON object with this EXACT structure:
{{
  "repo_overview": {{
    "name": "<repo name>",
    "description": "<short description or 'No description provided'>",
    "language": "<primary programming language>",
    "stars": <star count as integer>,
    "topics": ["<topic1>", "<topic2>"],
    "plain_explanation": "<2-3 sentence explanation of what this project does, written for a beginner>"
  }},
  "tech_stack": [
    {{
      "name": "<technology name>",
      "role": "<what role it plays, e.g. 'web framework', 'database', 'testing'>",
      "explanation": "<1 sentence beginner-friendly explanation of this technology>"
    }}
  ],
  "prerequisites": [
    {{
      "name": "<prerequisite name, e.g. Node.js, Python>",
      "version": "<recommended version>",
      "why": "<why this is needed>",
      "download_url": "<official download URL or empty string>",
      "status": "required"
    }}
  ],
  "raw_dependencies": {{
    "<package_name>": "<version_constraint>"
  }},
  "file_tree_summary": "<2-3 sentence summary of the project structure>",
  "readme_summary": "<3-4 sentence summary of the README content>"
}}

Rules:
- Detect ALL technologies from the file tree and dependency files.
- Extract prerequisites that a beginner would need to install first.
- raw_dependencies should map package name → version from the dependency files.
- If a field is unknown, use a sensible default (empty string, empty list, 0).
- Return ONLY valid JSON. No markdown, no explanations.
"""


async def run_vision(github_url: str) -> RepoDNA:
    """
    Layer 1 — Repo Vision.

    1. Parse the GitHub URL into owner/repo.
    2. Fetch all repository data from GitHub REST API.
    3. Send everything to Gemini 1.5 Flash for structured analysis.
    4. Return a RepoDNA model.

    Raises:
        ValueError: If the GitHub URL is invalid.
        GitHubAuthError: If the GitHub token is bad.
        GitHubNotFoundError: If the repository doesn't exist.
        Exception: If Gemini call fails.
    """
    try:
        owner, repo = parse_github_url(github_url)
    except ValueError:
        raise

    # Fetch repo data — let auth/not-found errors propagate with clear messages
    try:
        repo_data = await fetch_all_repo_data(owner, repo)
    except GitHubAuthError:
        raise  # Let main.py handle this with a proper HTTP response
    except GitHubNotFoundError:
        raise  # Let main.py handle this with 404
    except Exception as exc:
        raise Exception(f"[vision] Failed to fetch repository data: {exc}") from exc

    # Build the prompt
    readme_text = (repo_data.get("readme") or "")[:8000]
    file_tree = repo_data.get("tree", [])[:500]
    package_files = repo_data.get("package_files", {})
    env_example = repo_data.get("env_example") or "Not found"

    # Format package files for the prompt
    package_files_text = ""
    for filename, content in package_files.items():
        package_files_text += f"\n--- {filename} ---\n{content[:3000]}\n"
    if not package_files_text:
        package_files_text = "No package/dependency files detected."

    prompt = VISION_PROMPT_TEMPLATE.format(
        meta_json=json.dumps(repo_data["meta"], indent=2),
        readme=readme_text or "No README found.",
        file_tree="\n".join(file_tree),
        package_files=package_files_text,
        env_example=env_example,
    )

    try:
        repo_dna = await gemini_generate(prompt=prompt, response_model=RepoDNA)
        return repo_dna
    except Exception as exc:
        raise Exception(f"[vision] Gemini analysis failed: {exc}") from exc

"""
layers/research.py — Layer 2: Live Research

Uses Tavily for real-time web search in parallel batches,
then Cerebras Llama 8B to synthesize findings into a DependencyReport.
Tavily logic lives directly in this layer (no separate utils/tavily.py).
"""

import json
import asyncio

from tavily import TavilyClient

from config import settings
from models.schemas import RepoDNA, DependencyReport
from utils.cerebras import cerebras_generate


# ---------------------------------------------------------------------------
# Tavily helpers (sync SDK, wrapped with asyncio.to_thread)
# ---------------------------------------------------------------------------

def _get_tavily_client() -> TavilyClient:
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


def _tavily_search(query: str) -> dict:
    """Run a single Tavily search synchronously."""
    client = _get_tavily_client()
    return client.search(
        query=query,
        max_results=settings.TAVILY_MAX_RESULTS,
        search_depth=settings.TAVILY_SEARCH_DEPTH,
        days=settings.TAVILY_DAYS,
    )


async def _async_tavily_search(query: str) -> dict:
    """Wrap the sync Tavily search for async usage."""
    try:
        return await asyncio.to_thread(_tavily_search, query)
    except Exception as exc:
        print(f"[research] Tavily search failed for query: {query[:80]}... — {exc}")
        return {"results": []}


# ---------------------------------------------------------------------------
# Search query builders
# ---------------------------------------------------------------------------

def _build_search_queries(repo_dna: RepoDNA) -> tuple[list[str], list[str]]:
    """
    Build two batches of search queries from the RepoDNA.
    Batch 1 (3 queries) and Batch 2 (2 queries) run concurrently within each batch,
    with a 1-second gap between batches.
    """
    tech_names = ", ".join(item.name for item in repo_dna.tech_stack[:5])
    dep_names = ", ".join(list(repo_dna.raw_dependencies.keys())[:8])
    language = repo_dna.repo_overview.language
    repo_name = repo_dna.repo_overview.name

    batch_1 = [
        f"{tech_names} official installation guide 2026",
        f"{dep_names} known vulnerabilities CVE 2026",
        f"{language} beginner setup common errors",
    ]

    batch_2 = [
        f"{tech_names} deprecated packages alternatives 2026",
        f"{repo_name} known issues getting started",
    ]

    return batch_1, batch_2


# ---------------------------------------------------------------------------
# Research synthesis prompt
# ---------------------------------------------------------------------------

RESEARCH_SYNTHESIS_PROMPT = """
You are a dependency health analyst for developer tools.
Below are web search results about a repository's tech stack and dependencies.

=== REPOSITORY INFO ===
Name: {repo_name}
Language: {language}
Tech Stack: {tech_stack}
Dependencies: {dependencies}

=== WEB SEARCH RESULTS ===
{search_results}

Analyze the search results and produce a JSON object with this EXACT structure:
{{
  "dependency_health": {{
    "score": <integer 1-100, overall health score>,
    "healthy": <count of healthy dependencies>,
    "warnings": <count of dependencies with warnings>,
    "critical": <count of critical issues>,
    "details": [
      {{
        "name": "<dependency name>",
        "status": "<healthy | warning | critical>",
        "message": "<brief explanation of status>"
      }}
    ]
  }},
  "research_notes": "<2-3 paragraph summary of key findings from the search results, including any security concerns, deprecated packages, or setup gotchas>"
}}

Rules:
- Score each dependency based on search results (maintenance status, CVEs, community health).
- If no concerning info was found for a dependency, mark it "healthy".
- Be specific in messages — mention version numbers, CVE IDs, or alternatives when available.
- Return ONLY valid JSON.
"""


async def run_research(repo_dna: RepoDNA) -> DependencyReport:
    """
    Layer 2 — Live Research.

    1. Build search queries from RepoDNA.
    2. Execute Tavily searches in 2 parallel batches with a 1s gap.
    3. Synthesize all results through Cerebras Llama 8B.
    4. Return a DependencyReport.

    Raises:
        Exception: If research synthesis fails.
    """
    try:
        batch_1, batch_2 = _build_search_queries(repo_dna)

        # Batch 1 — concurrent
        batch_1_results = await asyncio.gather(
            *[_async_tavily_search(q) for q in batch_1]
        )

        # 1 second gap between batches
        await asyncio.sleep(1)

        # Batch 2 — concurrent
        batch_2_results = await asyncio.gather(
            *[_async_tavily_search(q) for q in batch_2]
        )

        # Combine all search results into a readable string
        all_results = batch_1_results + batch_2_results
        all_queries = batch_1 + batch_2
        search_text = ""
        for query, result in zip(all_queries, all_results):
            search_text += f"\n--- Query: {query} ---\n"
            for item in result.get("results", [])[:3]:
                search_text += f"Title: {item.get('title', 'N/A')}\n"
                search_text += f"URL: {item.get('url', 'N/A')}\n"
                search_text += f"Content: {item.get('content', 'N/A')[:500]}\n\n"

        if not search_text.strip():
            search_text = "No search results were returned."

        # Build synthesis prompt
        tech_stack_str = ", ".join(item.name for item in repo_dna.tech_stack)
        dep_str = json.dumps(repo_dna.raw_dependencies, indent=2)

        prompt = RESEARCH_SYNTHESIS_PROMPT.format(
            repo_name=repo_dna.repo_overview.name,
            language=repo_dna.repo_overview.language,
            tech_stack=tech_stack_str,
            dependencies=dep_str,
            search_results=search_text,
        )

        # Cerebras Llama 8B synthesis
        report = await cerebras_generate(
            prompt=prompt,
            response_model=DependencyReport,
            model=settings.CEREBRAS_FAST_MODEL,
            temperature=0.3,
        )

        return report

    except Exception as exc:
        raise Exception(f"[research] Live research failed: {exc}") from exc

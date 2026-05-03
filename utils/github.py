"""
utils/github.py — GitHub REST API client for RepoReady.

Handles all GitHub data fetching: README, file tree, repo metadata,
package/dependency files, and .env.example detection.
"""

import re
import base64
import httpx

from config import settings


# ---------------------------------------------------------------------------
# Custom exceptions for clear error propagation
# ---------------------------------------------------------------------------

class GitHubAuthError(Exception):
    """Raised when GitHub returns 401/403 — invalid or missing token."""
    pass

class GitHubNotFoundError(Exception):
    """Raised when the repository genuinely does not exist (404)."""
    pass

class GitHubAPIError(Exception):
    """Raised for any other GitHub API failure."""
    pass


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.
    Supports:
      https://github.com/owner/repo
      https://github.com/owner/repo.git
      https://github.com/owner/repo/tree/main/...
    """
    pattern = r"github\.com/([^/]+)/([^/?.#]+)"
    match = re.search(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")
    return owner, repo


# ---------------------------------------------------------------------------
# Async HTTP helpers
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _get(path: str) -> dict | list | None:
    """
    Fire a GET request against the GitHub REST API.
    Returns parsed JSON, or None on 404.
    Raises specific exceptions for 401/403 and other errors.
    """
    url = f"{settings.GITHUB_API_BASE}{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers())

        if resp.status_code == 404:
            return None
        if resp.status_code in (401, 403):
            raise GitHubAuthError(
                f"GitHub authentication failed (HTTP {resp.status_code}). "
                "Check your GITHUB_TOKEN in .env — it may be invalid or expired."
            )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------

async def fetch_readme(owner: str, repo: str) -> str:
    """Fetch the decoded README content. Returns empty string if missing."""
    try:
        data = await _get(f"/repos/{owner}/{repo}/readme")
        if data and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return ""
    except GitHubAuthError:
        raise  # Let auth errors bubble up — don't swallow them
    except Exception as exc:
        print(f"[github] Failed to fetch README: {exc}")
        return ""


async def fetch_file(owner: str, repo: str, path: str) -> str | None:
    """Fetch a single file's decoded content. Returns None if not found."""
    try:
        data = await _get(f"/repos/{owner}/{repo}/contents/{path}")
        if data and "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return None
    except GitHubAuthError:
        raise
    except Exception as exc:
        print(f"[github] Failed to fetch file {path}: {exc}")
        return None


async def fetch_tree(owner: str, repo: str) -> list[str]:
    """
    Fetch the full recursive file tree.
    Returns a list of file paths (blobs only, no directories).
    """
    try:
        repo_data = await _get(f"/repos/{owner}/{repo}")
        if not repo_data:
            return []
        default_branch = repo_data.get("default_branch", "main")

        tree_data = await _get(
            f"/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        )
        if not tree_data or "tree" not in tree_data:
            return []

        return [
            item["path"]
            for item in tree_data["tree"]
            if item.get("type") == "blob"
        ]
    except GitHubAuthError:
        raise
    except Exception as exc:
        print(f"[github] Failed to fetch tree: {exc}")
        return []


async def fetch_repo_meta(owner: str, repo: str) -> dict:
    """Fetch repository metadata (name, description, stars, language, topics)."""
    try:
        data = await _get(f"/repos/{owner}/{repo}")
        if not data:
            return {}
        return {
            "name": data.get("name", ""),
            "description": data.get("description") or "No description provided",
            "language": data.get("language") or "Unknown",
            "stars": data.get("stargazers_count", 0),
            "topics": data.get("topics", []),
            "default_branch": data.get("default_branch", "main"),
        }
    except GitHubAuthError:
        raise
    except Exception as exc:
        print(f"[github] Failed to fetch repo metadata: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Package file detection
# ---------------------------------------------------------------------------

KNOWN_PACKAGE_FILES = [
    "package.json",
    "requirements.txt",
    "Cargo.toml",
    "pom.xml",
    "go.mod",
    "Gemfile",
    "pubspec.yaml",
    "composer.json",
    "pyproject.toml",
    "setup.py",
    "build.gradle",
    "build.gradle.kts",
]


def detect_package_files(tree: list[str]) -> list[str]:
    """
    Given a file tree, return paths that match known package/dependency files.
    Only matches files at the repository root level.
    """
    return [
        path for path in tree
        if path in KNOWN_PACKAGE_FILES
    ]


async def fetch_all_repo_data(owner: str, repo: str) -> dict:
    """
    Master function — fetches everything needed for Layer 1 in parallel-ish fashion.
    Returns a dict with: readme, tree, meta, package_files, env_example.
    Raises GitHubAuthError immediately if the token is bad.
    """
    import asyncio

    # First, do a quick auth check with the metadata call
    # If the token is bad, this will raise GitHubAuthError immediately
    meta = await fetch_repo_meta(owner, repo)

    # If meta is empty dict AND no auth error was raised, repo genuinely doesn't exist
    if not meta:
        raise GitHubNotFoundError(f"Repository {owner}/{repo} not found on GitHub.")

    # Now fetch the rest in parallel
    readme_task = asyncio.create_task(fetch_readme(owner, repo))
    tree_task = asyncio.create_task(fetch_tree(owner, repo))
    env_task = asyncio.create_task(fetch_file(owner, repo, ".env.example"))

    readme, tree, env_example = await asyncio.gather(
        readme_task, tree_task, env_task
    )

    package_paths = detect_package_files(tree)

    # Fetch content of each detected package file
    package_contents: dict[str, str] = {}
    if package_paths:
        fetch_tasks = [fetch_file(owner, repo, p) for p in package_paths]
        results = await asyncio.gather(*fetch_tasks)
        for path, content in zip(package_paths, results):
            if content is not None:
                package_contents[path] = content

    return {
        "readme": readme,
        "tree": tree,
        "meta": meta,
        "package_files": package_contents,
        "env_example": env_example,
    }

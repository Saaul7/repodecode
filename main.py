"""
main.py — FastAPI entry point for RepoReady.

Zero business logic. Only wires up CORS, health check,
and the /analyze endpoint which calls the 4-layer pipeline in sequence.

Run with: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import AnalyzeRequest, RepoReadyResponse
from layers.vision import run_vision
from layers.research import run_research
from layers.creative import run_creative
from layers.examiner import run_examiner
from utils.github import parse_github_url, GitHubAuthError, GitHubNotFoundError

app = FastAPI(title="RepoReady API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/analyze", response_model=RepoReadyResponse)
async def analyze_repo(request: AnalyzeRequest):
    """
    Analyze a public GitHub repository and return a complete setup guide.

    Pipeline:
        Layer 1 (Vision)   → RepoDNA
        Layer 2 (Research)  → DependencyReport
        Layer 3 (Creative)  → SetupGuide
        Layer 4 (Examiner)  → ValidatedGuide
    """

    # --- Validate the GitHub URL ---
    try:
        owner, repo = parse_github_url(request.github_url)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid GitHub URL: {request.github_url}. "
                   "Expected format: https://github.com/owner/repo",
        )

    # --- Layer 1: Repo Vision ---
    try:
        repo_dna = await run_vision(request.github_url)
    except GitHubAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Repository not found: {owner}/{repo}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Vision layer failed: {str(exc)}",
        )

    # --- Layer 2: Live Research ---
    try:
        dep_report = await run_research(repo_dna)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Research layer failed: {str(exc)}",
        )

    # --- Layer 3: Guide Generator ---
    try:
        setup_guide = await run_creative(repo_dna, dep_report)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Guide generation failed: {str(exc)}",
        )

    # --- Layer 4: Validator ---
    try:
        validated_guide = await run_examiner(setup_guide)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(exc)}",
        )

    return validated_guide

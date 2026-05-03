# repodecode
RepoReady is a 4-layer autonomous AI system that analyzes any public GitHub repository and instantly generates a complete, beginner-friendly setup guide — including prerequisites, step-by-step commands, dependency health checks, tech stack explanations, and common error predictions. 

THE ENTIRE SETUP GUIDE:
## Setup
1. Clone this repo
2. Create .env with your API keys (see .env.example)
3. pip install -r requirements.txt
4. uvicorn main:app --reload --port 8000
5. Open index.html in browser

## API Keys needed
- GEMINI_API_KEY → aistudio.google.com
- CEREBRAS_API_KEY → cloud.cerebras.ai
- TAVILY_API_KEY → tavily.com
- GITHUB_TOKEN → github.com/settings/tokens

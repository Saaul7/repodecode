from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Keys from .env
    GEMINI_API_KEY: str
    CEREBRAS_API_KEY: str
    TAVILY_API_KEY: str
    GITHUB_TOKEN: str

    # Constants
    GEMINI_MODEL: str = "gemini-flash-latest"
    CEREBRAS_FAST_MODEL: str = "llama3.1-8b"
    CEREBRAS_POWER_MODEL: str = "llama3.1-8b"
    GITHUB_API_BASE: str = "https://api.github.com"
    TAVILY_MAX_RESULTS: int = 8
    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_DAYS: int = 180
    EXAMINER_MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

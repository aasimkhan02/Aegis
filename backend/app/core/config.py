import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load backend/.env if present, otherwise fall back to environment / cwd
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.is_file():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    # Adapter defaults
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_default_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120.0"))
    ragas_faithfulness_timeout_seconds: float = float(os.getenv("RAGAS_FAITHFULNESS_TIMEOUT_SECONDS", "120.0"))
    ragas_context_precision_timeout_seconds: float = float(os.getenv("RAGAS_CONTEXT_PRECISION_TIMEOUT_SECONDS", "120.0"))
    ragas_context_recall_timeout_seconds: float = float(os.getenv("RAGAS_CONTEXT_RECALL_TIMEOUT_SECONDS", "120.0"))
    http_adapter_base_url: str = os.getenv("HTTP_ADAPTER_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    http_adapter_api_key: str = os.getenv("HTTP_ADAPTER_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    http_adapter_default_model: str = os.getenv("HTTP_ADAPTER_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))



settings = Settings()


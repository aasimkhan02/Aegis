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


settings = Settings()


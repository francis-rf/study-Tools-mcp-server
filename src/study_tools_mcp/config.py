"""Configuration management for Study Tools MCP."""

import os
import json
import boto3
from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings


def get_secret(secret_name: str = "study-tools-mcp", region: str = "us-east-1") -> dict:
    """Fetch secrets from AWS Secrets Manager. Returns {} on failure (falls back to .env)."""
    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception:
        return {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Info
    APP_NAME: str = "Study Tools MCP"
    APP_DESCRIPTION: str = "AI-Powered Study Assistant - Generate Quizzes, Flashcards & Summaries"
    APP_VERSION: str = "1.0.0"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    RELOAD: bool = False

    # API Keys
    OPENAI_API_KEY: str = ""

    # AWS
    S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"

    # Model Settings
    USE_LOCAL_MODEL: bool = False
    LOCAL_MODEL_PATH: str = "./models/mistral-7b"
    DEFAULT_MODEL: str = "gpt-5-nano"
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 1.0

    # Paths — relative so they work both locally and in Docker
    BASE_DIR: Path = Path(".")
    DATA_DIR: Path = Path("data")
    NOTES_PATH: Path = Path("data/notes")
    LOGS_DIR: Path = Path("logs")
    STATIC_DIR: Path = Path("static")
    TEMPLATES_DIR: Path = Path("templates")

    # Study Tools Defaults
    DEFAULT_QUIZ_QUESTIONS: int = 5
    DEFAULT_FLASHCARDS: int = 7
    DEFAULT_SUMMARY_LENGTH: Literal["brief", "detailed", "comprehensive"] = "brief"

    # CORS
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_file_required = False

    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories"""
        instance = cls()
        instance.DATA_DIR.mkdir(exist_ok=True, parents=True)
        instance.NOTES_PATH.mkdir(exist_ok=True, parents=True)
        instance.LOGS_DIR.mkdir(exist_ok=True, parents=True)

    @classmethod
    def validate(cls) -> bool:
        return True

    @classmethod
    def display(cls) -> None:
        """Display current configuration"""
        instance = cls()
        print("=" * 60)
        print(f"📚 {instance.APP_NAME} v{instance.APP_VERSION}")
        print("=" * 60)
        print(f"Server:       {instance.HOST}:{instance.PORT}")
        print(f"Model:        {instance.DEFAULT_MODEL}")
        print(f"Temperature:  {instance.TEMPERATURE}")
        print(f"Notes Path:   {instance.NOTES_PATH}")
        print(f"S3 Bucket:    {instance.S3_BUCKET or 'Not set (using local)'}")
        print("=" * 60)


# Load secrets from Secrets Manager and inject into env before Settings loads
_secrets = get_secret()
if _secrets.get("OPENAI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = _secrets["OPENAI_API_KEY"]

# Global settings instance
settings = Settings()

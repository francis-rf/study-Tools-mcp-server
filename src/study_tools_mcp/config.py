"""Configuration management for Study Tools MCP."""

import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Info
    APP_NAME: str = "Study Tools MCP"
    APP_DESCRIPTION: str = "AI-Powered Study Assistant - Generate Quizzes, Flashcards & Summaries"
    APP_VERSION: str = "1.0.0"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    RELOAD: bool = True

    # API Keys
    OPENAI_API_KEY: str = ""

    # Model Settings
    USE_LOCAL_MODEL: bool = False
    LOCAL_MODEL_PATH: str = "./models/mistral-7b"
    DEFAULT_MODEL: str = "gpt-5-nano"
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 1.0

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    SRC_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    NOTES_PATH: Path = BASE_DIR / "data" / "notes"
    LOGS_DIR: Path = BASE_DIR / "logs"
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

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
        """Validate configuration"""
        instance = cls()

        # OPENAI_API_KEY is optional for MCP mode
        # Only required for web UI standalone mode

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
        print(f"Logs Dir:     {instance.LOGS_DIR}")
        print("=" * 60)


# Global settings instance
settings = Settings()

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Git Configuration
    git_repo_path: str = "./git_repo"
    git_user_name: str = "Git-Chat-Log Bot"
    git_user_email: str = "bot@git-chat-log.local"
    github_token: Optional[str] = None

    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "backlogs"

    # Slack Configuration
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    slack_webhook_url: Optional[str] = None

    # Discord Configuration
    discord_bot_token: Optional[str] = None
    discord_channel_id: Optional[str] = None

    # Server Configuration
    host: str = "localhost"  # Changed from 0.0.0.0 for security
    port: int = 8000
    debug: bool = False  # Changed to False for production safety
    reload: bool = False  # Disable reload in production

    # API Security
    api_key: Optional[str] = None  # API key for authentication
    cors_origins: str = ""  # Comma-separated list of allowed origins

    # Environment
    environment: str = "production"  # production, development, or testing

    # Scheduler Configuration
    scheduler_enabled: bool = True
    scheduler_check_interval_hours: int = 24
    overdue_task_check_hour: int = 9
    stale_task_days: int = 7

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_cors_origins(self):
        """Parse CORS origins from comma-separated string"""
        if self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return []

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"

settings = Settings()
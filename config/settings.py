from pydantic_settings import BaseSettings
from typing import Optional

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
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Scheduler Configuration
    scheduler_enabled: bool = True
    scheduler_check_interval_hours: int = 24
    overdue_task_check_hour: int = 9
    stale_task_days: int = 7

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
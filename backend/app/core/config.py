import os

from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class Settings:
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "interview_db")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    CONFIG_DIR: Path = Path(os.getenv("CONFIG_DIR", "config"))
    TOPICS_FILE: str = os.getenv("TOPICS_FILE", "topics.json")

    @property
    def TOPICS_PATH(self) -> Path:
        return self.CONFIG_DIR / self.TOPICS_FILE

    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


settings = Settings()

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
  llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
  ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
  ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

  openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
  openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
  openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

  databases_yaml_path: str = os.getenv("CONFIG_DATABASES_FILE", "./config/databases.yaml")

  host: str = os.getenv("HOST", "0.0.0.0")
  port: int = int(os.getenv("PORT", "8000"))


settings = Settings()


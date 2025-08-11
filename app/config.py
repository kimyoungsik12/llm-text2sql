import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
  llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
  
  # vllm settings
  vllm_base_url: str = os.getenv("VLLM_BASE_URL", "http://localhost:8001")
  vllm_model: str = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
  vllm_tensor_parallel_size: int = int(os.getenv("VLLM_TENSOR_PARALLEL_SIZE", "2"))
  vllm_gpu_memory_utilization: float = float(os.getenv("VLLM_GPU_MEMORY_UTILIZATION", "0.9"))
  
  # ollama settings
  ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
  ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

  # openai settings
  openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
  openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
  openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

  databases_yaml_path: str = os.getenv("CONFIG_DATABASES_FILE", "./config/databases.yaml")

  host: str = os.getenv("HOST", "0.0.0.0")
  port: int = int(os.getenv("PORT", "8000"))


settings = Settings()


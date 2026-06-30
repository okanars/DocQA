from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    embedding_model: str = "all-MiniLM-L6-v2"

    chunk_size: int = 512
    chunk_overlap: int = 50

    top_k: int = 5

    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "documents"

    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()

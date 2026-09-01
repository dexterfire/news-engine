"""Application settings loaded from environment / .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


class Settings:
    def __init__(self) -> None:
        self.database_url = os.environ["DATABASE_URL"]
        self.miniflux_url = os.environ["MINIFLUX_URL"]
        self.miniflux_user = os.environ["MINIFLUX_USER"]
        self.miniflux_password = os.environ["MINIFLUX_PASSWORD"]
        self.searxng_url = os.environ.get("SEARXNG_URL", "http://localhost:8088")
        self.opus_mt_model = os.environ.get("OPUS_MT_MODEL", "Helsinki-NLP/opus-mt-en-ru")
        self.clip_model = os.environ.get("CLIP_MODEL", "ViT-B/32")
        self.local_llm_model = os.environ.get("LOCAL_LLM_MODEL", "llama-cpp")
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")


settings = Settings()

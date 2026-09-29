"""
Project paths and environment configuration.

Replaces the notebook's "Section 0" (Google Drive mount, PROJECT_ROOT,
folder creation, and the Colab Secrets lookup). Everything is resolved
relative to this file, so the project works no matter which directory
it is launched from or where it is copied to.

Values below that come from the notebook (model name, top_k) are kept
exactly as the notebook used them.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# <project_root>/src/config.py -> project root is one level above src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Notebook: <PROJECT_ROOT>/raw_pdfs  ->  local: <project_root>/data/pdfs
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"

# Notebook: <PROJECT_ROOT>/data/chroma_db  (unchanged relative location)
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"

ENV_FILE = PROJECT_ROOT / ".env"

# Notebook cell 27: userdata.get("OPENROUTER_API_KEY"); Generator(model="openai/gpt-4o-mini")
API_KEY_ENV_VAR = "OPENROUTER_API_KEY"
LLM_MODEL = "openai/gpt-4o-mini"

# Notebook cell 30: Conversation(retriever=..., generator=..., top_k=3)
TOP_K = 3


class ConfigError(RuntimeError):
    """A missing/invalid local setup item, with an actionable message."""


def ensure_pdf_directory() -> List[Path]:
    """Return the PDFs found in data/pdfs/, or raise a clear ConfigError.

    Uses the same "*.pdf" pattern the notebook's extractor uses.
    """
    if not PDF_DIR.is_dir():
        raise ConfigError(
            f"PDF directory not found: {PDF_DIR}\n"
            "Create it and copy your PDF files into it."
        )
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise ConfigError(
            f"No PDF files found in: {PDF_DIR}\n"
            "Copy the CareerForge PDF files into that folder and run again."
        )
    return pdfs


def load_api_key() -> str:
    """Load OPENROUTER_API_KEY from the environment (.env is read if present)."""
    load_dotenv(ENV_FILE)
    api_key = os.environ.get(API_KEY_ENV_VAR, "").strip()
    if not api_key or api_key == "your_key_here":
        raise ConfigError(
            f"{API_KEY_ENV_VAR} is not set.\n"
            f"Copy .env.example to .env and put your OpenRouter key in it:\n"
            f"    {API_KEY_ENV_VAR}=<your key>"
        )
    return api_key

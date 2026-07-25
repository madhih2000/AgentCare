"""Vercel entrypoint. The @vercel/python builder looks for an ASGI/WSGI `app`
object in files under api/ — the real app lives at src/backend/main.py and is
normally run locally via `uvicorn backend.main:app --app-dir src`, so this
puts `src` on sys.path the same way `--app-dir` does before importing it."""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.main import app  # noqa: E402

__all__ = ["app"]

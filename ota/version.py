"""
Single source of truth for the app version.

We read `version.json`:
  - during development (repo-relative), or
  - when packaged/frozen (from the executable directory, which is included via PyInstaller `datas`).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _read_version_from_version_json() -> str:
    fallback = "1.0.0"
    try:
        if getattr(sys, "frozen", False):
            candidate = Path(os.path.dirname(sys.executable)) / "version.json"
        else:
            candidate = Path(__file__).resolve().parents[1] / "version.json"

        if not candidate.exists():
            return fallback

        payload = json.loads(candidate.read_text(encoding="utf-8"))
        version = str(payload.get("version") or "").strip()
        return version or fallback
    except Exception:
        return fallback


APP_VERSION = _read_version_from_version_json()


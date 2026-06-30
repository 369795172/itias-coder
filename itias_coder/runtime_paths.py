"""Resolve resource paths for dev installs and PyInstaller bundles."""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_root() -> Path:
    """Read-only bundled assets (profiles, etc.)."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def app_dir() -> Path:
    """Directory next to the executable (writable sidecar files)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def profiles_dir() -> Path:
    return bundle_root() / "config" / "profiles"

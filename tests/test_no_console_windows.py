"""Mechanical anti-regression scan: ffmpeg children must spawn windowless.

User report 2026-10-19 (v0.3.7): every spawned ffmpeg.exe allocated a
fresh black console window that stole foreground focus; the fallback
player spawns two processes per segment, so black windows popped up
every few seconds while coding and could not be moved out of the way.

Fix: every ``subprocess.Popen`` call in ``itias_coder/**`` must pass
``creationflags=no_window_creationflags()`` (``CREATE_NO_WINDOW`` on
Windows, 0 elsewhere — slicer.no_window_creationflags()).

Layer 1 discipline (docs/test.md): reads package sources only; no
imports of itias_coder modules, no Qt, no subprocess, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPO_ROOT / "itias_coder"

_IDENTIFIER_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _extract_call_block(source: str, open_paren_index: int) -> tuple[str, int]:
    """Return (block_text, close_index) for the balanced-paren call."""
    depth = 0
    for i in range(open_paren_index, len(source)):
        ch = source[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return source[open_paren_index : i + 1], i
    return source[open_paren_index:], len(source)


def _iter_popen_blocks(source: str):
    """Yield (lineno, block_text) for each ``subprocess.Popen(`` call."""
    pattern = "subprocess.Popen("
    search_from = 0
    while True:
        idx = source.find(pattern, search_from)
        if idx == -1:
            return
        if idx > 0 and source[idx - 1] in _IDENTIFIER_CHARS | {"."}:
            search_from = idx + len(pattern)
            continue
        open_paren = idx + len(pattern) - 1
        block, close_index = _extract_call_block(source, open_paren)
        lineno = source.count("\n", 0, idx) + 1
        yield lineno, block
        search_from = close_index + 1


def test_every_popen_spawns_windowless():
    """Every Popen call block must pass creationflags= (windowless spawn)."""
    violations: list[str] = []
    popen_count = 0

    py_files = sorted(PACKAGE_DIR.rglob("*.py"))
    assert py_files, f"package sources not found under {PACKAGE_DIR}"

    for path in py_files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        for lineno, block in _iter_popen_blocks(source):
            popen_count += 1
            if "creationflags=" not in block:
                violations.append(f"{rel}:{lineno} Popen without creationflags=")

    assert popen_count > 0, "scan found no Popen calls; scanner may be broken"
    assert not violations, (
        "ffmpeg children must spawn without a console window; "
        "pass creationflags=no_window_creationflags():\n" + "\n".join(violations)
    )


def test_windowless_helper_exists_in_slicer():
    """The helper lives in slicer.py next to find_ffmpeg (single definition)."""
    slicer_source = (PACKAGE_DIR / "slicer.py").read_text(encoding="utf-8")
    assert "def no_window_creationflags()" in slicer_source
    assert "CREATE_NO_WINDOW" in slicer_source
    # Non-Windows branches must fall back to 0 so POSIX Popen stays valid.
    assert re.search(r"return 0\b", slicer_source)

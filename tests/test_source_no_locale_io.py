"""Mechanical anti-regression scan: no locale-dependent text I/O in itias_coder.

Issue #19 class of bug: any ``subprocess`` call using ``text=True`` without an
explicit ``encoding=`` decodes child-process output with the platform locale
(GBK/cp936 on zh-CN Windows), and any ``open()`` without ``encoding=`` in
text mode reads files with the platform locale. Both are forbidden in
``itias_coder/**``.

Rules (pure source scan, balanced-paren call extraction):

- Rule 1: a ``subprocess.run`` / ``subprocess.Popen`` / ``subprocess.check_output``
  call block containing ``text=True`` (or ``universal_newlines=True``) must
  also contain ``encoding=`` in the same call block.
- Rule 2: an ``open()`` call block must contain ``encoding=`` or a binary
  mode argument (mode string containing ``b``); binary mode is exempt.

Red baseline (plan Todo 3): FAILS against current code because
``itias_coder/slicer.py`` calls ``subprocess.run`` and ``subprocess.Popen``
with ``text=True`` and no ``encoding=``. Turns green after the Todo-4 fix.

Layer 1 discipline (docs/test.md): reads package sources only; no imports of
itias_coder modules, no Qt, no subprocess, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPO_ROOT / "itias_coder"

SUBPROCESS_CALL_PATTERNS = (
    "subprocess.run(",
    "subprocess.Popen(",
    "subprocess.check_output(",
)

# Quoted strings usable as an open() mode, e.g. 'rb', "wb", 'r+b'.
_MODE_STRING_RE = re.compile(r"['\"]([rwab+]{1,4})['\"]")

_IDENTIFIER_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _extract_call_block(source: str, open_paren_index: int) -> tuple[str, int]:
    """Return (block_text, close_index) for the balanced-paren call.

    ``open_paren_index`` points at the '(' that opens the call. Simple depth
    scan; the package has few call sites and none carry unbalanced parens
    inside string literals.
    """
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


def _iter_call_blocks(source: str, pattern: str):
    """Yield (lineno, block_text) for each occurrence of ``pattern`` in source.

    Skips matches embedded in a longer identifier (e.g. the ``open(`` inside
    ``Popen(``) so builtin ``open()`` calls are matched exactly.
    """
    search_from = 0
    while True:
        idx = source.find(pattern, search_from)
        if idx == -1:
            return
        if idx > 0 and source[idx - 1] in _IDENTIFIER_CHARS:
            search_from = idx + len(pattern)
            continue
        open_paren = idx + len(pattern) - 1
        block, close_index = _extract_call_block(source, open_paren)
        lineno = source.count("\n", 0, idx) + 1
        yield lineno, block
        search_from = close_index + 1


def _has_binary_mode(block: str) -> bool:
    return any("b" in m.group(1) for m in _MODE_STRING_RE.finditer(block))


def test_no_bare_text_io():
    """No subprocess text-mode call and no text-mode open() without encoding=."""
    violations: list[str] = []

    py_files = sorted(PACKAGE_DIR.rglob("*.py"))
    assert py_files, f"package sources not found under {PACKAGE_DIR}"

    for path in py_files:
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")

        # Rule 1: locale-dependent subprocess text mode.
        for pattern in SUBPROCESS_CALL_PATTERNS:
            for lineno, block in _iter_call_blocks(source, pattern):
                if "text=True" in block or "universal_newlines=True" in block:
                    if "encoding=" not in block:
                        violations.append(
                            f"{rel}:{lineno}: subprocess text-mode call "
                            f"without explicit encoding="
                        )

        # Rule 2: locale-dependent open() text mode.
        for lineno, block in _iter_call_blocks(source, "open("):
            if "encoding=" not in block and not _has_binary_mode(block):
                violations.append(
                    f"{rel}:{lineno}: open() without explicit encoding= "
                    f"(non-binary mode)"
                )

    assert not violations, (
        "Locale-dependent text I/O found (issue #19 class); every subprocess "
        "text-mode call and every non-binary open() must pass encoding= "
        "explicitly:\n" + "\n".join(violations)
    )

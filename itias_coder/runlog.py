"""Runtime log (#21): playback diagnostics the crash log never captured.

The crash log (packaging/entry.py) only fires on startup exceptions; the
Win7 DirectShow playback failures are silent. This module keeps a per-run
log next to the exe (APPDATA fallback), rotating to the newest 5 files.
Every public function is failure-tolerant: logging must never break the app.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

_KEEP_RUNS = 5
_state = {"path": None}


def _log_dirs() -> list[Path]:
    """Candidate directories, best first: exe dir (frozen) / cwd, then APPDATA."""
    if getattr(sys, "frozen", False):
        dirs = [Path(sys.executable).resolve().parent]
    else:
        dirs = [Path.cwd()]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(Path(appdata) / "ITIAS-Coder")
    return dirs


def _rotate(directory: Path) -> None:
    runs = sorted(
        p for p in directory.glob("ITIAS-Coder-run-*.log") if p.is_file()
    )
    for stale in runs[:-_KEEP_RUNS]:
        try:
            stale.unlink()
        except OSError:
            pass


def init_runlog() -> Path | None:
    """Create the run log file and dump the environment header.

    Safe to call multiple times; re-init (e.g. tests) reuses nothing and
    creates a fresh file. Returns the log path or None when unwritable.
    """
    filename = "ITIAS-Coder-run-%s.log" % datetime.now().strftime("%Y%m%d-%H%M%S")
    for directory in _log_dirs():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / filename
            # Probe writability with the handle itself; rotation after.
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(_environment_header())
            _state["path"] = path
            _rotate(directory)
            return path
        except OSError:
            continue
    _state["path"] = None
    return None


def current_log_path() -> Path | None:
    return _state["path"]


def log(category: str, message: str) -> None:
    """Append one timestamped line; never raises."""
    path = _state["path"]
    if path is None:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            stamp = datetime.now().strftime("%H:%M:%S")
            fh.write("[%s] %s: %s\n" % (stamp, category, message))
    except (OSError, ValueError):
        pass


def _windows_media_facts() -> dict:
    """Existence of DirectShow-era media components (#25).

    Stock Win10 ships all of these; N editions and stripped school images
    drop some. Absent flags in the run log identify the exact gap without
    remote debugging.
    """
    import os

    windir = os.environ.get("windir", r"C:\Windows")
    system32 = os.path.join(windir, "System32")
    dlls = {
        "quartz": "quartz.dll",
        "msmpeg2vdec": "msmpeg2vdec.dll",
        "msauddecm": "msauddecm.dll",
        "mfplat": "mfplat.dll",
    }
    facts = {}
    for key, name in dlls.items():
        facts[key] = os.path.isfile(os.path.join(system32, name))
    facts["wmplayer"] = any(
        os.path.isfile(
            os.path.join(program_dir, "Windows Media Player", "wmplayer.exe")
        )
        for program_dir in (
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        )
    )
    return facts


def _format_media_facts(facts: dict) -> str:
    return " ".join("%s=%d" % (k, int(bool(v))) for k, v in sorted(facts.items()))


def _environment_header() -> str:
    import platform

    from itias_coder import __version__
    from itias_coder import qt_bindings

    lines = [
        "ITIAS Coder v%s run log" % __version__,
        "started=%s" % datetime.now().isoformat(timespec="seconds"),
        "python=%s" % sys.version.split()[0],
        "os=%s" % platform.platform(),
        "machine=%s" % platform.machine(),
        "frozen=%s" % bool(getattr(sys, "frozen", False)),
        "qt_api=%d" % qt_bindings.QT_API,
        "qt_runtime=%s" % qt_bindings.QtCore.qVersion(),
        "charts_available=%s" % qt_bindings.CHARTS_AVAILABLE,
    ]
    if sys.platform == "win32":
        try:
            lines.append("media_dlls=%s" % _format_media_facts(_windows_media_facts()))
        except Exception:
            lines.append("media_dlls=probe-failed")
    return "\n".join(lines) + "\n"

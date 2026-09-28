"""Regression tests for issue #19: zh-CN locale (cp936/GBK) decode crash.

Root cause: ``slicer.probe_duration`` (``subprocess.run(..., text=True)``) and
``slicer.SliceWorker.run`` (``subprocess.Popen(..., text=True)``) decode
ffmpeg/ffprobe output with ``locale.getpreferredencoding(False)`` — GBK on
zh-CN Windows. The ffmpeg stderr banner line
``Input #0, ... from 'C:\\Users\\UNIS\\Desktop\\<中文名>'`` contains UTF-8
Chinese lead bytes that are illegal GBK sequences at the read position, so
iterating ``proc.stderr`` raises UnicodeDecodeError, caught at the generic
``except`` in ``run()`` and surfaced as the error popup in the report.

Contract this file pins: both subprocess call sites must pass
``encoding="utf-8"`` and ``errors="replace"`` explicitly.

Red baseline (plan Todo 3): both tests FAIL against current code because the
calls pass ``text=True`` with no ``encoding=``/``errors=``.

Layer 1 discipline (docs/test.md): module import + monkeypatch only, no
QApplication, no widget instantiation, no network, no media files, no real
ffmpeg subprocess. No direct PySide6/PySide2 import; importing
``itias_coder.slicer`` pulls ``qt_bindings`` transitively (same style as
test_selftest.py importing itias_coder.main).
"""

from __future__ import annotations

import io
import locale

import itias_coder.slicer as slicer_module
from itias_coder.slicer import SliceWorker, probe_duration

# ffmpeg stderr banner shaped like the issue #19 report: a legal UTF-8
# Chinese filename (课程) plus the progress ``time=`` line.
BANNER_BYTES = (
    b"Input #0, mov,mp4, from 'C:\\Users\\UNIS\\Desktop"
    b"\\\xe8\xaf\xbe\xe7\xa8\x8b.mp4': time=00:00:03.00\n"
)


def test_popen_passes_explicit_encoding(monkeypatch, tmp_path):
    """SliceWorker.run must launch Popen with encoding='utf-8', errors='replace'.

    The Popen stub decodes the UTF-8 banner exactly the way real subprocess
    text mode would: with the call's own ``encoding``/``errors`` kwargs, or
    with locale.getpreferredencoding(False)/strict when absent — i.e. the
    GBK crash conditions of a zh-CN Windows machine.
    """
    monkeypatch.setattr(slicer_module, "probe_duration", lambda *a, **k: 9.0)

    captured: list[dict] = []

    class PopenStub:
        def __init__(self, cmd, **kwargs):
            captured.append(dict(kwargs))
            # Mirror subprocess text-mode wrapping: without an explicit
            # encoding kwarg this is where zh-CN (cp936) decoding happens.
            self.stderr = io.TextIOWrapper(
                io.BytesIO(BANNER_BYTES),
                encoding=kwargs.get("encoding") or locale.getpreferredencoding(False),
                errors=kwargs.get("errors") or "strict",
            )
            self.stdout = None
            self.returncode = 0

        def wait(self):
            return 0

        def terminate(self):
            pass

    monkeypatch.setattr(slicer_module.subprocess, "Popen", PopenStub)

    worker = SliceWorker(
        video_path=str(tmp_path / "课.mp4"),
        out_folder=str(tmp_path / "out"),
        segment_duration=3,
        ffmpeg_bin="ffmpeg",
    )
    worker.run()

    assert captured, "subprocess.Popen was never called by SliceWorker.run()"
    kwargs = captured[0]
    assert kwargs.get("encoding") == "utf-8", (
        "issue #19: subprocess.Popen must pass encoding='utf-8' so ffmpeg "
        f"stderr is not decoded with the zh-CN locale codec; got kwargs: {kwargs}"
    )
    assert kwargs.get("errors") == "replace", (
        "issue #19: subprocess.Popen must pass errors='replace' so stray "
        f"bytes never abort progress parsing; got kwargs: {kwargs}"
    )


def test_probe_duration_explicit_encoding(monkeypatch):
    """probe_duration must call subprocess.run with encoding='utf-8', errors='replace'."""
    captured: list[dict] = []

    class RunResultStub:
        stdout = "9.0"

    def run_stub(*args, **kwargs):
        captured.append(dict(kwargs))
        return RunResultStub()

    monkeypatch.setattr(slicer_module.subprocess, "run", run_stub)

    duration = probe_duration("x.mp4", "ffmpeg")

    assert duration == 9.0
    assert captured, "subprocess.run was never called by probe_duration()"
    kwargs = captured[0]
    assert kwargs.get("encoding") == "utf-8", (
        "issue #19: subprocess.run must pass encoding='utf-8' so ffprobe "
        f"output is not decoded with the zh-CN locale codec; got kwargs: {kwargs}"
    )
    assert kwargs.get("errors") == "replace", (
        "issue #19: subprocess.run must pass errors='replace' so a decode "
        f"error cannot silently swallow the duration; got kwargs: {kwargs}"
    )

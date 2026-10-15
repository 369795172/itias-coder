"""Tests for issue #21: transcode decision + runtime log.

Layer 1 discipline (docs/test.md): pure functions and tmp files only, no
QApplication, no widget instantiation, no network, no media files, no real
ffmpeg subprocess (probe_streams failure path is exercised with a bogus
binary path instead).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import itias_coder.runlog as runlog_module
import itias_coder.slicer as slicer_module
from itias_coder.slicer import needs_transcode


@pytest.fixture(autouse=True)
def _reset_runlog_state():
    runlog_module._state["path"] = None
    yield
    runlog_module._state["path"] = None


class TestNeedsTranscode:
    def test_hevc_source_requires_transcode(self):
        streams = [
            {"codec_type": "video", "codec_name": "hevc", "pix_fmt": "yuv420p"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
        transcode, reason = needs_transcode(streams)
        assert transcode is True
        assert "hevc" in reason

    def test_h264_aac_yuv420p_uses_copy(self):
        streams = [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
            {"codec_type": "audio", "codec_name": "aac"},
        ]
        transcode, reason = needs_transcode(streams)
        assert transcode is False

    def test_odd_pixel_format_requires_transcode(self):
        streams = [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv444p"},
        ]
        transcode, _ = needs_transcode(streams)
        assert transcode is True

    def test_incompatible_audio_requires_transcode(self):
        streams = [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
            {"codec_type": "audio", "codec_name": "ac3"},
        ]
        transcode, reason = needs_transcode(streams)
        assert transcode is True
        assert "ac3" in reason

    def test_probe_failure_falls_back_to_copy(self):
        transcode, reason = needs_transcode([])
        assert transcode is False
        assert "fallback" in reason

    def test_missing_fields_do_not_crash(self):
        streams = [{"codec_type": "video"}, {"codec_type": "audio"}]
        # Unknown codec cannot be guaranteed DirectShow-compatible: safe side
        # is transcode.
        transcode, _ = needs_transcode(streams)
        assert transcode is True

    def test_mp3_audio_is_compatible(self):
        streams = [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuvj420p"},
            {"codec_type": "audio", "codec_name": "mp3"},
        ]
        assert needs_transcode(streams)[0] is False


class TestFfprobePath:
    """#23: whole-string replace renamed the ffmpeg *directory* too on the
    bundled Windows layout, silently breaking the codec pre-flight."""

    def test_bundled_windows_layout_keeps_directory(self):
        from itias_coder.slicer import ffprobe_path

        assert ffprobe_path(r"C:\App\ITIAS-Coder\ffmpeg\ffmpeg.exe") == (
            r"C:\App\ITIAS-Coder\ffmpeg\ffprobe.exe"
        )

    def test_posix_path(self):
        from itias_coder.slicer import ffprobe_path

        assert ffprobe_path("/opt/homebrew/bin/ffmpeg") == "/opt/homebrew/bin/ffprobe"

    def test_bare_name(self):
        from itias_coder.slicer import ffprobe_path

        assert ffprobe_path("ffmpeg") == "ffprobe"


class TestProbeStreamsFailure:
    def test_bogus_binary_returns_empty(self, tmp_path):
        assert slicer_module.probe_streams(str(tmp_path / "x.mp4"), "/nonexistent/ffmpeg") == []


class TestRunlog:
    def test_init_writes_header_and_log_appends(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = runlog_module.init_runlog()
        assert path is not None and path.exists()
        header = path.read_text(encoding="utf-8")
        assert "ITIAS Coder v" in header
        assert "qt_api=" in header

        runlog_module.log("player", "hello 世界")
        body = path.read_text(encoding="utf-8")
        assert "] player: hello 世界" in body

    def test_log_never_raises_without_init(self, monkeypatch):
        monkeypatch.setitem(runlog_module._state, "path", None)
        runlog_module.log("x", "y")  # must be a no-op

    def test_rotation_keeps_newest_five(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for i in range(8):
            stale = tmp_path / ("ITIAS-Coder-run-2026010%d-00000%d.log" % (i, i))
            stale.write_text("old", encoding="utf-8")
        path = runlog_module.init_runlog()
        assert path is not None
        remaining = sorted(tmp_path.glob("ITIAS-Coder-run-*.log"))
        assert len(remaining) == 5
        assert path in remaining
        assert "ITIAS-Coder-run-20260100-000000.log" not in [p.name for p in remaining]


class TestFfmpegPlayerHelpers:
    """#25 fallback player pure helpers."""

    def test_parse_fps_fraction(self):
        from itias_coder.ffmpeg_player import parse_fps

        assert parse_fps("25/1") == 25.0
        assert parse_fps("30000/1001") > 29.9
        assert parse_fps("22/1") == 22.0

    def test_parse_fps_garbage_defaults(self):
        from itias_coder.ffmpeg_player import parse_fps

        assert parse_fps("abc") == 25.0
        assert parse_fps("") == 25.0
        assert parse_fps("10/0") == 25.0

    def test_even_size_and_frame_bytes(self):
        from itias_coder.ffmpeg_player import even_size, frame_buffer_size

        assert even_size(641, 361) == (640, 360)
        assert even_size(0, 0) == (2, 2)
        assert frame_buffer_size(640, 360) == 640 * 360 * 4
        assert frame_buffer_size(0, 0) == 16

    def test_read_exact_eof(self):
        import io

        from itias_coder.ffmpeg_player import _read_exact

        assert _read_exact(io.BytesIO(b"ab"), 2) == b"ab"
        assert _read_exact(io.BytesIO(b"a"), 2) is None

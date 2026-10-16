"""Layer 2 integration test (#25): FfmpegPlayer end-to-end on synthetic media.

Needs a local ffmpeg and an offscreen-capable Qt (dev machine); skips
elsewhere per docs/test.md Layer 2 (CI not required to run this).
Asserts the FULL chain: spawn -> frames decoded -> frameReady -> real
paintEvent execution with a non-null QImage -> end-of-media fires. The
v0.3.6 user incident was exactly a healthy pipeline with a dead paint
path (PySide2 QImage vs immutable bytes), so counting frames alone is
not sufficient evidence.
"""

import shutil
import subprocess
import sys

import pytest

pytestmark = [
    pytest.mark.skipif(
        shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH"
    ),
    pytest.mark.skipif(
        sys.platform == "win32", reason="dev-machine Layer 2; not for CI windows runner"
    ),
]


def _make_clip(tmp_path, seconds=3):
    out = tmp_path / "ffplayer_test.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=320x240:rate=10",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(out),
        ],
        check=True,
    )
    return str(out)


def test_ffplayer_full_chain_including_paint(tmp_path):
    pytest.importorskip("PySide6.QtWidgets")
    import time

    from itias_coder.qt_bindings import QApplication

    app = QApplication.instance() or QApplication([])

    from itias_coder.ffmpeg_player import FfmpegPlayer, VideoSurface

    clip = _make_clip(tmp_path)
    surface = VideoSurface()
    surface.widget().resize(320, 240)
    surface.widget().show()

    frames = []
    surface.frameReady.connect(lambda d, w, h: frames.append((len(d), w, h)))

    paints = {"n": 0, "with_image": 0}
    original_paint = surface.paint_event

    def counting_paint(event):
        original_paint(event)
        paints["n"] += 1
        if surface._image is not None:
            paints["with_image"] += 1

    surface.paint_event = counting_paint

    ended = {"flag": False}
    player = FfmpegPlayer(surface, "ffmpeg", lambda: (320, 240))
    player.set_end_of_media_callback(lambda: ended.__setitem__("flag", True))
    player.play_file(clip)

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not ended["flag"]:
        app.processEvents()
        time.sleep(0.01)

    player.stop()

    assert len(frames) >= 10, "expected a full second of decoded frames"
    assert frames[0][1] == 320 and frames[0][2] == 240
    assert ended["flag"], "end-of-media must fire for the encoder loop"
    assert paints["with_image"] >= 1, (
        "paintEvent must execute with a decoded frame; a healthy pipeline "
        "with zero paints is exactly the v0.3.6 black-screen incident"
    )

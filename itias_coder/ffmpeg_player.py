"""FFmpeg-direct fallback playback (#25).

On machines whose DirectShow stack cannot decode the slices (school
images without media components), QMediaPlayer fails with
InvalidMedia/ResourceError even for H.264/AAC files. The app already
bundles ffmpeg and the user's own external players prove ffmpeg-class
decoding works on that machine, so this player decodes through the
bundled binary instead of the system:

- one ``-re``-paced ffmpeg process per playback for BGRA video frames,
- one for s16le 44100 Hz stereo PCM fed into QAudioOutput (Qt5) or
  QAudioSink (Qt6),
- frames repainted on the GUI thread via a queued signal; EOF triggers
  the end-of-media callback so the encoder's loop semantics stay.

Only the pure helpers are unit-tested (Layer 1); the process/Qt plumbing
is Layer 3 by docs/test.md.
"""
from __future__ import annotations

import subprocess
import threading
from typing import Optional

from itias_coder.qt_bindings import QObject, QTimer, Signal, QWidget

# Forced decode format so no negotiation is ever needed.
_PCM_RATE = 44100
_PCM_CHANNELS = 2
_AUDIO_CHUNK = 8192


def parse_fps(r_frame_rate: str) -> float:
    """'25/1' -> 25.0; malformed input falls back to 25.0."""
    try:
        num, _, den = r_frame_rate.partition("/")
        den_f = float(den or 1)
        if den_f == 0:
            return 25.0
        return max(1.0, min(120.0, float(num) / den_f))
    except (ValueError, AttributeError):
        return 25.0


def even_size(width: int, height: int) -> tuple[int, int]:
    """Even-dimensioned target size (ffmpeg scale wants even for most pixfmts)."""
    return max(2, int(width) // 2 * 2), max(2, int(height) // 2 * 2)


def frame_buffer_size(width: int, height: int) -> int:
    return even_size(width, height)[0] * even_size(width, height)[1] * 4  # BGRA


def _read_exact(stream, size: int) -> Optional[bytes]:
    buf = bytearray()
    while len(buf) < size:
        chunk = stream.read(size - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


class _SurfaceWidget(QWidget):
    """Black QWidget delegating paintEvent to its VideoSurface owner."""

    def __init__(self, surface, parent=None):
        QWidget.__init__(self, parent)
        self._surface = surface

    def paintEvent(self, event):
        self._surface.paint_event(event)


class VideoSurface(QObject):
    """Black widget the fallback player paints decoded frames onto."""

    frameReady = Signal(bytes, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        from itias_coder.qt_bindings import QSizePolicy, QSizePolicyExpanding

        self._qwidget = _SurfaceWidget(self, parent)
        self._qwidget.setStyleSheet("background: #000;")
        self._qwidget.setSizePolicy(QSizePolicyExpanding, QSizePolicyExpanding)
        self._image = None
        self._size = (0, 0)
        self.frameReady.connect(self._on_frame)

    def widget(self):
        return self._qwidget

    def _on_frame(self, data: bytes, width: int, height: int) -> None:
        # PySide2 QImage rejects immutable bytes buffers (null image -> the
        # widget paints nothing but the pipeline logs healthy frames, the
        # exact "black screen with a working log" the user reported); a
        # writable bytearray copy is the documented cross-version contract.
        self._image = bytearray(data)
        self._size = (width, height)
        self._qwidget.update()

    def paint_event(self, event) -> None:
        from itias_coder.qt_bindings import QColor, QImage, QPainter

        painter = QPainter(self._qwidget)
        try:
            painter.fillRect(self._qwidget.rect(), QColor("#000000"))
            if self._image is not None and self._size != (0, 0):
                img = QImage(
                    self._image, self._size[0], self._size[1],
                    self._size[0] * 4, QImage.Format_ARGB32,
                )
                if img.isNull():
                    return
                painter.drawImage(self._qwidget.rect(), img)
        finally:
            painter.end()


class FfmpegPlayer(QObject):
    """Fallback player mirroring SegmentPlayer's public surface."""

    mediaStatusChanged = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, surface: VideoSurface, ffmpeg_bin: str, get_size):
        super().__init__()
        self._surface = surface
        self._ffmpeg_bin = ffmpeg_bin
        self._get_size = get_size

        self._video_proc: Optional[subprocess.Popen] = None
        self._audio_proc: Optional[subprocess.Popen] = None
        self._audio_output = None
        self._audio_io = None
        self._frame_bytes = 0
        self._frame_w = 0
        self._frame_h = 0
        self._audio_active = False
        self._audio_queue: list[bytes] = []
        self._ended = False
        self._last_file: Optional[str] = None
        self._on_end_of_media = None
        self._first_frame_logged = False

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)

    def set_end_of_media_callback(self, callback) -> None:
        self._on_end_of_media = callback

    def play_file(self, filepath: str) -> None:
        from itias_coder import runlog

        self.stop()
        self._last_file = filepath
        width, height = even_size(*self._get_size())
        if width < 160 or height < 90:
            # Pre-layout geometry race on the freshly-switched surface (#25):
            # a 2x2 scale target decodes "fine" and reads as a black screen.
            runlog.log(
                "ffplayer",
                "target size %dx%d too small, using 640x360" % (width, height),
            )
            width, height = 640, 360
        self._frame_w, self._frame_h = width, height
        self._frame_bytes = frame_buffer_size(width, height)
        self._ended = False
        self._audio_queue = []
        self._first_frame_logged = False

        common = ["-re", "-i", filepath, "-sn", "-dn"]
        video_cmd = [
            self._ffmpeg_bin, *common,
            "-vf", "scale=%d:%d" % (width, height),
            "-an", "-f", "rawvideo", "-pix_fmt", "bgra", "pipe:1",
        ]
        audio_cmd = [
            self._ffmpeg_bin, *common,
            "-vn", "-f", "s16le", "-ar", str(_PCM_RATE), "-ac", str(_PCM_CHANNELS),
            "pipe:1",
        ]
        runlog.log("ffplayer", "spawn %dx%d %s" % (width, height, filepath))
        try:
            self._video_proc = subprocess.Popen(
                video_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            )
            self._audio_proc = subprocess.Popen(
                audio_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            )
        except OSError as exc:
            runlog.log("ffplayer", "ERROR spawn failed: %s" % exc)
            self.errorOccurred.emit(str(exc))
            return

        self._start_audio()
        threading.Thread(target=self._read_video_loop, daemon=True).start()
        threading.Thread(target=self._read_audio_loop, daemon=True).start()
        self.mediaStatusChanged.emit("FfmpegPlaying")
        self._timer.start()

    def replay(self) -> None:
        if self._last_file:
            self.play_file(self._last_file)

    def stop(self) -> None:
        self._timer.stop()
        self._audio_active = False
        for proc in (self._video_proc, self._audio_proc):
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass
        self._video_proc = None
        self._audio_proc = None
        if self._audio_output is not None:
            try:
                self._audio_output.stop()
            except Exception:
                pass
        self._audio_io = None

    # ── internals ─────────────────────────────────────────────────────────

    def _create_audio_output(self):
        """Return the push-mode QIODevice for both Qt stacks.

        Qt5 QAudioOutput and Qt6 QAudioSink have different constructor
        surfaces but the same push contract: start() returns the QIODevice
        that accepts PCM writes. Neither class has a usable ``write()``
        itself (Qt6 QAudioSink.write does not exist; Qt5 QAudioOutput.open
        does not exist).
        """
        from itias_coder import qt_bindings

        if qt_bindings.QT_API == 6:
            from PySide6.QtMultimedia import QAudioFormat, QAudioSink

            fmt = QAudioFormat()
            fmt.setSampleRate(_PCM_RATE)
            fmt.setChannelCount(_PCM_CHANNELS)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            sink = QAudioSink(fmt)
            sink.setBufferSize(16384)
            self._audio_io = sink.start()
            return sink

        from PySide2.QtMultimedia import QAudioFormat, QAudioOutput

        fmt = QAudioFormat()
        fmt.setSampleRate(_PCM_RATE)
        fmt.setChannelCount(_PCM_CHANNELS)
        fmt.setSampleSize(16)
        fmt.setCodec("audio/pcm")
        fmt.setByteOrder(QAudioFormat.LittleEndian)
        fmt.setSampleType(QAudioFormat.SignedInt)
        out = QAudioOutput(fmt)
        out.setBufferSize(16384)
        self._audio_io = out.start()
        return out

    def _start_audio(self) -> None:
        from itias_coder import runlog

        try:
            if self._audio_output is None:
                self._audio_output = self._create_audio_output()
            else:
                # stop() tore down the push device; replay must reopen it.
                self._audio_io = self._audio_output.start()
            self._audio_active = self._audio_io is not None
            runlog.log(
                "ffplayer",
                "audio pipeline started active=%s" % self._audio_active,
            )
        except Exception as exc:
            self._audio_output = None
            self._audio_io = None
            self._audio_active = False
            runlog.log("ffplayer", "audio unavailable (%s); video-only" % exc)

    def _read_video_loop(self) -> None:
        proc = self._video_proc
        if proc is None:
            return
        stream = proc.stdout
        while self._video_proc is proc:
            frame = _read_exact(stream, self._frame_bytes)
            if frame is None:
                break
            if not self._first_frame_logged:
                self._first_frame_logged = True
                from itias_coder import runlog

                runlog.log(
                    "ffplayer",
                    "first frame %dx%d (%d bytes)" % (self._frame_w, self._frame_h, len(frame)),
                )
            self._surface.frameReady.emit(frame, self._frame_w, self._frame_h)
        if self._video_proc is proc:
            self._ended = True

    def _read_audio_loop(self) -> None:
        proc = self._audio_proc
        if proc is None:
            return
        stream = proc.stdout
        while self._audio_proc is proc and self._audio_active:
            chunk = stream.read(_AUDIO_CHUNK)
            if not chunk:
                break
            self._audio_queue.append(chunk)

    def _tick(self) -> None:
        from itias_coder import runlog

        if self._audio_active and self._audio_io is not None:
            while self._audio_queue:
                chunk = self._audio_queue[0]
                try:
                    written = self._audio_io.write(chunk)
                except Exception as exc:
                    self._audio_active = False
                    runlog.log("ffplayer", "audio write failed (%s); video-only" % exc)
                    break
                if written <= 0:
                    break
                if written < len(chunk):
                    self._audio_queue[0] = chunk[written:]
                    break
                self._audio_queue.pop(0)
        if self._ended:
            # Orphaned audio chunks must never hold the end-of-media
            # callback hostage; when audio is off the queue is dead weight.
            if not self._audio_active or not self._audio_queue:
                self._audio_queue.clear()
                self._timer.stop()
                runlog.log("ffplayer", "end of media")
                if self._on_end_of_media is not None:
                    self._on_end_of_media()

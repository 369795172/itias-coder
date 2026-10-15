"""Video slicing using ffmpeg subprocess."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from itias_coder.qt_bindings import QObject, QSettings, QThread, Signal


def find_ffmpeg() -> Optional[str]:
    """Find ffmpeg executable. Returns path or None."""
    from .runtime_paths import app_dir

    bundled_names = ("ffmpeg.exe", "ffmpeg") if os.name == "nt" else ("ffmpeg",)
    for name in bundled_names:
        bundled = app_dir() / "ffmpeg" / name
        if bundled.is_file():
            return str(bundled)

    candidate = shutil.which("ffmpeg")
    if candidate:
        return candidate
    # Common homebrew locations (macOS dev)
    for p in ["/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if os.path.isfile(p):
            return p
    return None


def ffprobe_path(ffmpeg_bin: str) -> str:
    """Derive the ffprobe path from the ffmpeg binary path.

    Only the file name may change: the bundled Windows layout is
    ``.../ffmpeg/ffmpeg.exe`` where the directory itself is named ffmpeg,
    so a whole-string replace would point at ``.../ffprobe/ffprobe.exe``
    and silently break probing (#23). String-based split so Windows-style
    backslash paths behave identically on the macOS dev/CI side.
    """
    for sep in ("/", "\\"):
        if sep in ffmpeg_bin:
            head, _, tail = ffmpeg_bin.rpartition(sep)
            name = "ffprobe.exe" if tail.lower().endswith(".exe") else "ffprobe"
            return head + sep + name
    if ffmpeg_bin.lower().endswith(".exe"):
        return "ffprobe.exe"
    return "ffprobe"


def probe_duration(video_path: str, ffmpeg_bin: str = "ffmpeg") -> Optional[float]:
    """Use ffprobe to get video duration in seconds."""
    ffprobe = ffprobe_path(ffmpeg_bin)
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def probe_streams(video_path: str, ffmpeg_bin: str = "ffmpeg") -> list[dict]:
    """Use ffprobe to list streams (codec_name/codec_type/pix_fmt/profile)."""
    ffprobe = ffprobe_path(ffmpeg_bin)
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error",
             "-show_entries",
             "stream=codec_name,codec_type,pix_fmt,profile",
             "-of", "json", video_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
        )
        import json

        data = json.loads(result.stdout or "{}")
        return list(data.get("streams", []))
    except Exception:
        return []


# DirectShow on stock Win7 decodes these without third-party codec packs.
_COMPAT_VIDEO_CODECS = {"h264"}
_COMPAT_PIX_FMTS = {"yuv420p", "yuvj420p", "nv12", "yuv420p10le"}
_COMPAT_AUDIO_CODECS = {"aac", "mp3"}


def needs_transcode(streams: list[dict]) -> tuple[bool, str]:
    """Decide stream-copy vs compatible re-encode for in-app playback (#21).

    Returns (transcode, reason). Probe failure (empty list) keeps the fast
    copy path so behaviour degrades to pre-0.3.3, never blocks slicing.
    """
    if not streams:
        return False, "probe-unavailable (stream copy fallback)"

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video is None:
        return False, "no-video-stream"

    vcodec = (video.get("codec_name") or "").lower()
    if vcodec not in _COMPAT_VIDEO_CODECS:
        return True, "video codec %s not DirectShow-compatible" % vcodec

    pix_fmt = (video.get("pix_fmt") or "").lower()
    if pix_fmt and pix_fmt not in _COMPAT_PIX_FMTS:
        return True, "pixel format %s not DirectShow-compatible" % pix_fmt

    if audio is not None:
        acodec = (audio.get("codec_name") or "").lower()
        if acodec and acodec not in _COMPAT_AUDIO_CODECS:
            return True, "audio codec %s not DirectShow-compatible" % acodec

    return False, "source already compatible (stream copy)"


class SliceWorker(QObject):
    """Runs ffmpeg slicing in a background thread."""

    progress = Signal(int, int, str)   # current_file, total_files, message
    finished = Signal(int, str)         # segment_count, out_folder
    error = Signal(str)

    def __init__(
        self,
        video_path: str,
        out_folder: str,
        segment_duration: int = 3,
        ffmpeg_bin: str = "ffmpeg",
    ):
        super().__init__()
        self.video_path = video_path
        self.out_folder = out_folder
        self.segment_duration = segment_duration
        self.ffmpeg_bin = ffmpeg_bin
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        if hasattr(self, "_proc") and self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def run(self):
        from itias_coder import runlog

        os.makedirs(self.out_folder, exist_ok=True)

        duration = probe_duration(self.video_path, self.ffmpeg_bin)
        if duration:
            expected_segments = max(1, int(duration / self.segment_duration))
        else:
            expected_segments = 0

        streams = probe_streams(self.video_path, self.ffmpeg_bin)
        transcode, reason = needs_transcode(streams)
        runlog.log(
            "slicer",
            "source=%s transcode=%s reason=%s streams=%s"
            % (self.video_path, transcode, reason, streams),
        )

        video_stem = Path(self.video_path).stem
        out_pattern = os.path.join(self.out_folder, f"{video_stem}_%04d.mp4")

        if transcode:
            mode_msg = "检测到不兼容编码，正在转码为 H.264 兼容格式（比直通模式慢）…"
            cmd = [
                self.ffmpeg_bin,
                "-i", self.video_path,
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libx264", "-preset", "veryfast",
                "-profile:v", "main", "-pix_fmt", "yuv420p",
                "-force_key_frames",
                "expr:gte(t,n_forced*%d)" % self.segment_duration,
                "-c:a", "aac", "-b:a", "128k",
                "-segment_time", str(self.segment_duration),
                "-f", "segment",
                "-reset_timestamps", "1",
                "-y",
                out_pattern,
            ]
        else:
            mode_msg = "启动 ffmpeg（直通切片）..."
            cmd = [
                self.ffmpeg_bin,
                "-i", self.video_path,
                "-c", "copy",
                "-map", "0",
                "-segment_time", str(self.segment_duration),
                "-f", "segment",
                "-reset_timestamps", "1",
                "-y",
                out_pattern,
            ]

        self.progress.emit(0, expected_segments, mode_msg)

        try:
            self._proc = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            # Parse ffmpeg stderr for time= to show progress
            time_re = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
            last_reported = 0

            for line in self._proc.stderr:
                if self._cancelled:
                    break
                m = time_re.search(line)
                if m:
                    h, mn, s = m.groups()
                    elapsed = int(h) * 3600 + int(mn) * 60 + float(s)
                    current_seg = max(1, int(elapsed / self.segment_duration))
                    if current_seg != last_reported:
                        last_reported = current_seg
                        self.progress.emit(
                            current_seg,
                            expected_segments or current_seg + 1,
                            f"处理第 {current_seg} 段...",
                        )

            self._proc.wait()
            if self._cancelled:
                self.error.emit("已取消")
                return
            if self._proc.returncode != 0:
                self.error.emit(f"ffmpeg 返回错误码 {self._proc.returncode}")
                return

        except FileNotFoundError:
            self.error.emit("找不到 ffmpeg，请先安装：brew install ffmpeg")
            return
        except Exception as e:
            self.error.emit(str(e))
            return

        # Count actual output files
        out_files = sorted(
            [f for f in os.listdir(self.out_folder)
             if f.startswith(video_stem) and f.endswith(".mp4")]
        )
        self.finished.emit(len(out_files), self.out_folder)


def collect_segments(folder: str) -> list[str]:
    """Return sorted list of video file paths in folder."""
    exts = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}
    files = []
    for fname in sorted(os.listdir(folder)):
        if Path(fname).suffix.lower() in exts:
            files.append(os.path.join(folder, fname))
    return files

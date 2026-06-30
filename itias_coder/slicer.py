"""Video slicing using ffmpeg subprocess."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal


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


def probe_duration(video_path: str, ffmpeg_bin: str = "ffmpeg") -> Optional[float]:
    """Use ffprobe to get video duration in seconds."""
    ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return None


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
        os.makedirs(self.out_folder, exist_ok=True)

        duration = probe_duration(self.video_path, self.ffmpeg_bin)
        if duration:
            expected_segments = max(1, int(duration / self.segment_duration))
        else:
            expected_segments = 0

        video_stem = Path(self.video_path).stem
        out_pattern = os.path.join(self.out_folder, f"{video_stem}_%04d.mp4")

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

        self.progress.emit(0, expected_segments, "启动 ffmpeg...")

        try:
            self._proc = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
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

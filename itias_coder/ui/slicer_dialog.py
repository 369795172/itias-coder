"""Video slicing dialog."""
from __future__ import annotations

import os

from PySide6.QtCore import QSettings, QThread, Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
)

from ..slicer import SliceWorker, collect_segments, find_ffmpeg


class SlicerDialog(QDialog):
    """Dialog for slicing a video file into fixed-duration segments."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("切片视频")
        self.setMinimumWidth(560)
        self._settings = QSettings("ITIAS-Coder", "itias-coder")
        self._worker: SliceWorker | None = None
        self._thread: QThread | None = None
        self._out_folder: str = ""
        self._segment_count: int = 0
        self._build_ui()
        self._restore_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Input video
        in_group = QGroupBox("输入视频")
        in_lay = QHBoxLayout(in_group)
        self._in_edit = QLineEdit()
        self._in_edit.setPlaceholderText("选择视频文件...")
        in_browse = QPushButton("浏览...")
        in_browse.clicked.connect(self._browse_input)
        in_lay.addWidget(self._in_edit)
        in_lay.addWidget(in_browse)
        layout.addWidget(in_group)

        # Output folder
        out_group = QGroupBox("输出文件夹")
        out_lay = QHBoxLayout(out_group)
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("切片输出到此文件夹...")
        out_browse = QPushButton("浏览...")
        out_browse.clicked.connect(self._browse_output)
        out_lay.addWidget(self._out_edit)
        out_lay.addWidget(out_browse)
        layout.addWidget(out_group)

        # Duration
        dur_group = QGroupBox("片段时长（秒）")
        dur_lay = QHBoxLayout(dur_group)
        self._dur_spin = QSpinBox()
        self._dur_spin.setRange(1, 30)
        self._dur_spin.setValue(3)
        self._dur_spin.setSuffix(" 秒")
        self._dur_spin.setMaximumWidth(120)
        dur_note = QLabel("（ITIAS 标准为 3 秒）")
        dur_note.setStyleSheet("color: gray;")
        dur_lay.addWidget(self._dur_spin)
        dur_lay.addWidget(dur_note)
        dur_lay.addStretch()
        layout.addWidget(dur_group)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.setVisible(False)
        layout.addWidget(self._log)

        # Buttons
        btn_lay = QHBoxLayout()
        self._start_btn = QPushButton("开始切片")
        self._start_btn.setDefault(True)
        self._start_btn.clicked.connect(self._start_slice)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self._cancel)

        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.accept)
        self._close_btn.setEnabled(False)

        btn_lay.addStretch()
        btn_lay.addWidget(self._start_btn)
        btn_lay.addWidget(self._cancel_btn)
        btn_lay.addWidget(self._close_btn)
        layout.addLayout(btn_lay)

    def _restore_settings(self):
        dur = self._settings.value("slicer/duration", 3, type=int)
        self._dur_spin.setValue(max(1, min(30, dur)))
        last_in = self._settings.value("slicer/last_input", "")
        last_out = self._settings.value("slicer/last_output", "")
        if last_in:
            self._in_edit.setText(last_in)
        if last_out:
            self._out_edit.setText(last_out)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.m4v);;所有文件 (*)"
        )
        if path:
            self._in_edit.setText(path)
            # Auto-set output folder alongside input
            if not self._out_edit.text():
                out = os.path.join(os.path.dirname(path), "itias_segments")
                self._out_edit.setText(out)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self._out_edit.setText(folder)

    def _start_slice(self):
        in_path = self._in_edit.text().strip()
        out_path = self._out_edit.text().strip()
        if not in_path or not os.path.isfile(in_path):
            QMessageBox.warning(self, "错误", "请选择有效的视频文件")
            return
        if not out_path:
            QMessageBox.warning(self, "错误", "请选择输出文件夹")
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            QMessageBox.critical(
                self, "找不到 ffmpeg",
                "请先安装 ffmpeg：\n  brew install ffmpeg\n\n"
                "或将 ffmpeg 可执行文件添加到 PATH 中。"
            )
            return

        dur = self._dur_spin.value()
        self._settings.setValue("slicer/duration", dur)
        self._settings.setValue("slicer/last_input", in_path)
        self._settings.setValue("slicer/last_output", out_path)

        self._out_folder = out_path
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # indeterminate initially
        self._log.setVisible(True)
        self._log.clear()
        self._start_btn.setEnabled(False)
        self._close_btn.setEnabled(False)

        self._worker = SliceWorker(in_path, out_path, dur, ffmpeg)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._thread.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self.reject()

    def _on_progress(self, current: int, total: int, message: str):
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(current)
        self._log.append(message)

    def _on_finished(self, count: int, folder: str):
        self._thread.quit()
        self._segment_count = count
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(1)
        self._log.append(f"\n✓ 完成！共切出 {count} 段，保存在：\n  {folder}")
        self._start_btn.setEnabled(True)
        self._close_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._thread.quit()
        self._log.append(f"\n✗ 错误：{msg}")
        self._start_btn.setEnabled(True)
        self._close_btn.setEnabled(True)
        QMessageBox.critical(self, "切片失败", msg)

    def result_folder(self) -> str:
        """Return output folder path after successful slice."""
        return self._out_folder

    def segment_count(self) -> int:
        return self._segment_count

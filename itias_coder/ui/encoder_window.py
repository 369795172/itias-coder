"""Encoder window: video player + ITIAS code buttons."""
from __future__ import annotations

import os
from typing import Optional

from itias_coder.qt_bindings import (
    QCloseEvent, QColor, QDialog, QFileDialog, QFont, QGridLayout, QGroupBox,
    QHBoxLayout, QKeySequence, QLabel, QMainWindow, QMessageBox, MB_NO, MB_YES,
    QProgressBar, QPushButton, QScrollArea, QShortcut, QSizePolicy,
    QSizePolicyExpanding, QSizePolicyFixed, QStatusBar, Qt, QVBoxLayout,
    QWidget, QVideoWidget, SegmentPlayer,
)

from ..models import CodeDef, Profile, Segment, Session
from ..storage import export_excel, export_txt, save_session


class CodeButton(QPushButton):
    """A single ITIAS code button."""

    def __init__(self, code: CodeDef, parent=None):
        super().__init__(parent)
        self.code = code
        self.setText(code.display)
        self.setMinimumHeight(36)
        self.setMinimumWidth(140)
        self.setSizePolicy(QSizePolicyExpanding, QSizePolicyFixed)
        self._base_color = code.color
        self._apply_style(False)

    def _apply_style(self, active: bool):
        bg = self._base_color
        border = "2px solid #888" if active else "1px solid #ccc"
        text_color = "#000"
        # Darken for active
        if active:
            border = "3px solid #333"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: {border};
                border-radius: 5px;
                padding: 4px 8px;
                text-align: left;
                color: {text_color};
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {bg};
                border: 2px solid #555;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background-color: {bg};
                border: 3px solid #222;
            }}
        """)
        if self.code.shortcut:
            self.setToolTip(f"快捷键: {self.code.shortcut.upper()}")


class EncoderWindow(QMainWindow):
    """Main encoding window with video player and ITIAS code buttons."""

    def __init__(self, session: Session, profile: Profile):
        super().__init__()
        self.session = session
        self.profile = profile
        self._current_idx: Optional[int] = None
        self._undo_stack: list[int] = []  # list of segment 0-based indices that were coded
        self._dirty = False  # unsaved work indicator (beyond autosave)

        self.setWindowTitle(f"ITIAS 编码 — {profile.name}")
        self.setMinimumSize(900, 640)

        self._build_ui()
        self._setup_shortcuts()
        self._setup_player()

        # Start from first uncoded
        start_idx = self.session.first_uncoded_index()
        if start_idx is None:
            start_idx = 0
        self._load_segment(start_idx)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Left: video + controls
        left_widget = QWidget()
        left_lay = QVBoxLayout(left_widget)
        left_lay.setContentsMargins(8, 8, 4, 8)

        # Top info bar
        info_bar = QWidget()
        info_bar.setStyleSheet("background: #F5F5F5; border-radius: 4px;")
        info_lay = QHBoxLayout(info_bar)
        info_lay.setContentsMargins(8, 4, 8, 4)

        self._counter_label = QLabel("0 / 0")
        self._counter_label.setFont(QFont("", 14, QFont.Weight.Bold))
        info_lay.addWidget(self._counter_label)

        info_lay.addStretch()

        self._filename_label = QLabel("")
        self._filename_label.setStyleSheet("color: #666; font-size: 12px;")
        info_lay.addWidget(self._filename_label)

        left_lay.addWidget(info_bar)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%v / %m 段已编码")
        self._progress_bar.setMaximumHeight(18)
        left_lay.addWidget(self._progress_bar)

        # Video widget
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(360)
        self._video_widget.setSizePolicy(
            QSizePolicyExpanding, QSizePolicyExpanding
        )
        self._video_widget.setStyleSheet("background: #000;")
        left_lay.addWidget(self._video_widget)

        # Video controls
        ctrl_lay = QHBoxLayout()
        self._replay_btn = QPushButton("↺ 重播")
        self._replay_btn.setToolTip("重新播放当前片段")
        self._replay_btn.clicked.connect(self._replay_current)

        self._undo_btn = QPushButton("⟵ 撤销")
        self._undo_btn.setToolTip("撤销上一条编码，回到该片段 (Ctrl+Z)")
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self._undo_last)

        self._export_btn = QPushButton("导出...")
        self._export_btn.clicked.connect(self._export)

        for btn in [self._replay_btn, self._undo_btn, self._export_btn]:
            btn.setMinimumHeight(34)

        self._undo_btn.setStyleSheet("""
            QPushButton { background: #FF8F00; color: white; border-radius: 5px; }
            QPushButton:hover { background: #E65100; }
            QPushButton:disabled { background: #ddd; color: #aaa; }
        """)
        self._export_btn.setStyleSheet("""
            QPushButton { background: #5C6BC0; color: white; border-radius: 5px; }
            QPushButton:hover { background: #3949AB; }
        """)

        ctrl_lay.addWidget(self._replay_btn)
        ctrl_lay.addWidget(self._undo_btn)
        ctrl_lay.addStretch()
        ctrl_lay.addWidget(self._export_btn)
        left_lay.addLayout(ctrl_lay)

        root.addWidget(left_widget, stretch=3)

        # Right: code buttons
        right_widget = QWidget()
        right_widget.setStyleSheet("background: #FAFAFA; border-left: 1px solid #DDD;")
        right_widget.setMinimumWidth(200)
        right_widget.setMaximumWidth(280)
        right_lay = QVBoxLayout(right_widget)
        right_lay.setContentsMargins(8, 8, 8, 8)
        right_lay.setSpacing(4)

        profile_label = QLabel(self.profile.name)
        profile_label.setFont(QFont("", 11, QFont.Weight.Bold))
        profile_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile_label.setWordWrap(True)
        right_lay.addWidget(profile_label)

        # Current code indicator
        self._current_code_label = QLabel("—")
        self._current_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current_code_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self._current_code_label.setStyleSheet(
            "background: #E3F2FD; border-radius: 4px; padding: 4px; color: #1565C0;"
        )
        right_lay.addWidget(self._current_code_label)

        # Scroll area for buttons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        btn_container = QWidget()
        btn_lay = QVBoxLayout(btn_container)
        btn_lay.setSpacing(3)
        btn_lay.setContentsMargins(0, 0, 0, 0)

        self._code_buttons: dict[int, CodeButton] = {}
        current_category = None
        for code in self.profile.codes:
            if code.category != current_category:
                current_category = code.category
                cat_label = QLabel(self.profile.category_labels.get(code.category, code.category))
                cat_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; margin-top: 4px;")
                btn_lay.addWidget(cat_label)

            btn = CodeButton(code)
            btn.clicked.connect(lambda checked=False, c=code: self._on_code(c))
            self._code_buttons[code.id] = btn
            btn_lay.addWidget(btn)

        btn_lay.addStretch()
        scroll.setWidget(btn_container)
        right_lay.addWidget(scroll)

        root.addWidget(right_widget, stretch=0)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("准备就绪")

    def _setup_shortcuts(self):
        # Undo
        undo_sc = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_sc.activated.connect(self._undo_last)

        # Replay
        replay_sc = QShortcut(QKeySequence("Space"), self)
        replay_sc.activated.connect(self._replay_current)

        # Code shortcuts
        for code in self.profile.codes:
            if code.shortcut:
                sc = QShortcut(QKeySequence(code.shortcut), self)
                sc.activated.connect(lambda c=code: self._on_code(c))

    def _setup_player(self):
        self._segment_player = SegmentPlayer(self._video_widget)
        self._segment_player.set_end_of_media_callback(self._on_segment_end)

    def _on_segment_end(self):
        if self._current_idx is not None:
            seg = self.session.segments[self._current_idx]
            if not seg.is_coded:
                self._segment_player.replay()

    # ── Segment Navigation ────────────────────────────────────────────────────

    def _load_segment(self, idx: int):
        """Load and play segment at 0-based index."""
        if idx < 0 or idx >= len(self.session.segments):
            return
        self._current_idx = idx
        seg = self.session.segments[idx]

        self._counter_label.setText(
            f"第 {seg.index} / {self.session.total} 段"
        )
        self._filename_label.setText(seg.filename)
        self._progress_bar.setMaximum(self.session.total)
        self._progress_bar.setValue(self.session.coded_count)

        # Show existing code if segment already coded
        if seg.is_coded:
            code_def = self.profile.get_code(seg.code_id)
            if code_def:
                self._current_code_label.setText(code_def.display)
                self._current_code_label.setStyleSheet(
                    f"background: {code_def.color}; border-radius: 4px; padding: 4px;"
                )
            self._status_bar.showMessage(f"片段 {seg.index} 已编码为 {seg.code_label}，可重新编码或跳过")
        else:
            self._current_code_label.setText("待编码")
            self._current_code_label.setStyleSheet(
                "background: #E3F2FD; border-radius: 4px; padding: 4px; color: #1565C0;"
            )
            self._status_bar.showMessage(f"正在播放第 {seg.index} 段，请点击右侧按钮编码")

        self._segment_player.play_file(seg.filepath)

    def _replay_current(self):
        """Restart playback of current segment."""
        self._segment_player.replay()

    # ── Coding ────────────────────────────────────────────────────────────────

    def _on_code(self, code: CodeDef):
        if self._current_idx is None:
            return

        seg = self.session.segments[self._current_idx]
        prev_coded = seg.is_coded
        seg.apply_code(code)
        self._dirty = True

        # Track undo
        self._undo_stack.append(self._current_idx)
        self._undo_btn.setEnabled(True)

        # Update UI
        self._current_code_label.setText(code.display)
        self._current_code_label.setStyleSheet(
            f"background: {code.color}; border-radius: 4px; padding: 4px;"
        )
        self._progress_bar.setValue(self.session.coded_count)
        self._status_bar.showMessage(
            f"✓ 第 {seg.index} 段 → {code.display}  （已编码 {self.session.coded_count}/{self.session.total}）"
        )

        # Autosave
        save_session(self.session)

        # Check completion
        if self.session.is_complete:
            self._segment_player.stop()
            reply = QMessageBox.question(
                self, "编码完成！",
                f"全部 {self.session.total} 段已编码完成！\n\n是否立即导出结果？",
                MB_YES | MB_NO,
            )
            if reply == MB_YES:
                self._export()
            return

        # Advance to next uncoded
        next_uncoded = self.session.first_uncoded_index()
        if next_uncoded is not None:
            self._load_segment(next_uncoded)

    # ── Undo ─────────────────────────────────────────────────────────────────

    def _undo_last(self):
        if not self._undo_stack:
            return
        last_idx = self._undo_stack.pop()
        seg = self.session.segments[last_idx]
        seg.clear_code()
        self._dirty = True
        save_session(self.session)
        self._progress_bar.setValue(self.session.coded_count)

        if not self._undo_stack:
            self._undo_btn.setEnabled(False)

        self._status_bar.showMessage(f"↩ 已撤销第 {seg.index} 段的编码")
        self._load_segment(last_idx)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self):
        folder = self.session.segments_folder or os.path.expanduser("~")
        out_path, _ = QFileDialog.getSaveFileName(
            self, "导出编码结果",
            os.path.join(folder, "itias_result.xlsx"),
            "Excel 文件 (*.xlsx)"
        )
        if not out_path:
            return

        try:
            export_excel(self.session, self.profile, out_path)
            txt_path = out_path.replace(".xlsx", ".txt")
            export_txt(self.session, txt_path)
            self._dirty = False
            QMessageBox.information(
                self, "导出成功",
                f"Excel 已保存：\n  {out_path}\n\nTXT 已保存：\n  {txt_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ── Close Confirm ─────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):
        uncoded = self.session.total - self.session.coded_count
        if uncoded > 0:
            reply = QMessageBox.question(
                self,
                "确认关闭",
                f"还有 {uncoded} 段尚未编码。\n"
                f"进度已自动保存，下次打开同一文件夹可继续。\n\n"
                f"是否确认关闭？",
                MB_YES | MB_NO,
                MB_NO,
            )
            if reply == MB_NO:
                event.ignore()
                return

        self._segment_player.stop()
        save_session(self.session)
        event.accept()

"""Main application window — launcher."""
from __future__ import annotations

import os

from itias_coder.qt_bindings import (
    QFileDialog, QFont, QGroupBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, MB_NO, MB_YES, QPushButton, QSettings, Qt, QVBoxLayout,
    QWidget, qt_exec,
)

from ..profile import list_profiles, load_profile
from ..slicer import collect_segments
from ..storage import has_save, load_session


class MainWindow(QMainWindow):
    """Launcher window: choose slice or encode."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITIAS Coder — 课堂互动分析编码工具")
        self.setMinimumSize(480, 340)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("ITIAS 课堂互动分析编码工具")
        title.setFont(QFont("", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QLabel("免费替代 CCIES · 支持18类ITIAS编码 · 顾小清&王炜 2004")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)

        root.addSpacing(8)

        # Step 1: Slice
        slice_group = QGroupBox("第一步：切片视频")
        slice_lay = QVBoxLayout(slice_group)
        slice_desc = QLabel("将课堂录像切分为等长片段（默认3秒/段），用 ffmpeg 处理。")
        slice_desc.setWordWrap(True)
        slice_desc.setStyleSheet("color: #555;")
        slice_btn = QPushButton("切片视频...")
        slice_btn.setMinimumHeight(40)
        slice_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2; color: white;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        slice_btn.clicked.connect(self._open_slicer)
        slice_lay.addWidget(slice_desc)
        slice_lay.addWidget(slice_btn)
        root.addWidget(slice_group)

        # Step 2: Encode
        encode_group = QGroupBox("第二步：开始编码")
        encode_lay = QVBoxLayout(encode_group)
        encode_desc = QLabel("选择切片文件夹，自动逐段播放并使用 ITIAS 18类按钮编码。")
        encode_desc.setWordWrap(True)
        encode_desc.setStyleSheet("color: #555;")

        btn_row = QHBoxLayout()
        encode_btn = QPushButton("开始编码...")
        encode_btn.setMinimumHeight(40)
        encode_btn.setStyleSheet("""
            QPushButton {
                background: #388E3C; color: white;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #2E7D32; }
        """)
        encode_btn.clicked.connect(self._open_encoder)

        resume_btn = QPushButton("导入Excel续作...")
        resume_btn.setMinimumHeight(40)
        resume_btn.setStyleSheet("""
            QPushButton {
                background: #F57C00; color: white;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #E65100; }
        """)
        resume_btn.clicked.connect(self._resume_from_excel)

        btn_row.addWidget(encode_btn)
        btn_row.addWidget(resume_btn)

        encode_lay.addWidget(encode_desc)
        encode_lay.addLayout(btn_row)
        root.addWidget(encode_group)

        # Step 3: Analysis
        analysis_group = QGroupBox("第三步：分析报告")
        analysis_lay = QVBoxLayout(analysis_group)
        analysis_desc = QLabel(
            "加载已编码课程，查看行为矩阵、占比与时序图；或导入多节 Excel 进行对比分析。"
        )
        analysis_desc.setWordWrap(True)
        analysis_desc.setStyleSheet("color: #555;")

        analysis_row = QHBoxLayout()
        single_btn = QPushButton("分析单课...")
        single_btn.setMinimumHeight(40)
        single_btn.setStyleSheet("""
            QPushButton {
                background: #00897B; color: white;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #00695C; }
        """)
        single_btn.clicked.connect(self._open_single_analysis)

        compare_btn = QPushButton("多课对比...")
        compare_btn.setMinimumHeight(40)
        compare_btn.setStyleSheet("""
            QPushButton {
                background: #5E35B1; color: white;
                border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background: #4527A0; }
        """)
        compare_btn.clicked.connect(self._open_compare)

        analysis_row.addWidget(single_btn)
        analysis_row.addWidget(compare_btn)

        analysis_lay.addWidget(analysis_desc)
        analysis_lay.addLayout(analysis_row)
        root.addWidget(analysis_group)

        root.addStretch()

        # Footer
        footer = QLabel("v0.2.0 · ITIAS Coder · open source")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #aaa; font-size: 11px;")
        root.addWidget(footer)

    def _open_slicer(self):
        from .slicer_dialog import SlicerDialog
        dlg = SlicerDialog(self)
        qt_exec(dlg)

    def _open_encoder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择切片文件夹")
        if not folder:
            return
        self._launch_encoder(folder)

    def _resume_from_excel(self):
        folder = QFileDialog.getExistingDirectory(self, "选择切片文件夹")
        if not folder:
            return
        excel_path, _ = QFileDialog.getOpenFileName(
            self, "选择之前导出的 Excel 文件", folder,
            "Excel 文件 (*.xlsx)"
        )
        if not excel_path:
            return
        self._launch_encoder(folder, excel_path=excel_path)

    def _launch_encoder(self, folder: str, excel_path: str | None = None):
        from ..slicer import collect_segments
        from ..models import Segment, Session
        from ..storage import import_from_excel, load_session, save_session
        from ..profile import load_profile

        files = collect_segments(folder)
        if not files:
            QMessageBox.warning(
                self, "没有找到视频文件",
                f"在以下文件夹中没有找到视频文件（mp4/avi/mov/mkv/m4v）：\n{folder}"
            )
            return

        profile = load_profile("itias_default")

        # Try to restore autosave
        session = load_session(folder)
        if session:
            # Reconcile saved segments with current files
            saved_paths = {s.filepath: s for s in session.segments}
            segments = []
            for i, fp in enumerate(files, 1):
                if fp in saved_paths:
                    seg = saved_paths[fp]
                    seg.index = i
                else:
                    seg = Segment(index=i, filepath=fp)
                segments.append(seg)
            session.segments = segments
            coded = sum(1 for s in segments if s.is_coded)
            if coded > 0:
                QMessageBox.information(
                    self, "恢复进度",
                    f"检测到已保存进度（{coded}/{len(segments)} 段已编码），将从上次中断处继续。"
                )
        else:
            settings = QSettings("ITIAS-Coder", "itias-coder")
            segment_duration = settings.value("slicer/duration", 3, type=int)
            segments = [Segment(index=i, filepath=fp) for i, fp in enumerate(files, 1)]
            session = Session(
                segments=segments,
                profile_id=profile.id,
                segments_folder=folder,
                segment_duration=segment_duration,
            )

        # Override with Excel if provided
        if excel_path:
            try:
                from ..storage import import_from_excel
                session.segments = import_from_excel(excel_path, session.segments)
                coded = sum(1 for s in session.segments if s.is_coded)
                QMessageBox.information(
                    self, "导入成功",
                    f"已从 Excel 导入 {coded} 条编码记录。"
                )
            except Exception as e:
                QMessageBox.warning(self, "导入失败", str(e))

        session.segments_folder = folder
        save_session(session)

        from .encoder_window import EncoderWindow
        window = EncoderWindow(session, profile)
        window.show()
        self._encoder_window = window

    def _open_single_analysis(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择课程数据",
            os.path.expanduser("~"),
            "课程数据 (*.itias_save.json *.xlsx);;JSON (*.itias_save.json);;Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            session, profile = self._load_session_for_analysis(path)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))
            return
        if not session.segments:
            QMessageBox.warning(self, "加载失败", "文件中没有编码数据。")
            return
        from .analysis_window import AnalysisWindow
        window = AnalysisWindow(session, profile, self)
        window.show()
        self._analysis_window = window

    def _open_compare(self):
        from .compare_window import CompareWindow
        profile = load_profile("itias_default")
        window = CompareWindow(profile, self)
        window.show()
        self._compare_window = window

    def _load_session_for_analysis(self, path: str):
        import json

        from ..models import Session

        profile = load_profile("itias_default")
        if path.endswith(".json"):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            session = Session.from_dict(data)
            if session.profile_id:
                try:
                    profile = load_profile(session.profile_id)
                except Exception:
                    pass
            return session, profile

        from .compare_window import _session_from_excel
        session = _session_from_excel(path)
        return session, profile

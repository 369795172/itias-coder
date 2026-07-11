"""Multi-lesson comparison window: import up to 30 lessons, compare stats and charts."""
from __future__ import annotations

import os
from pathlib import Path

import openpyxl

from itias_coder.qt_bindings import (
    QChart,
    QChartView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineSeries,
    QMainWindow,
    QMessageBox,
    QFileDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QValueAxis,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..analysis import (
    behavior_counts,
    category_counts,
    time_series_by_category,
)
from ..models import Profile, Segment, Session
from ..profile import load_profile

MAX_LESSONS = 30


def _session_from_excel(path: str) -> Session:
    """Parse an exported Excel file into a Session (analysis-only, no video paths)."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    segments: list[Segment] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        seg_index = int(row[0])
        filepath = str(row[1]) if row[1] else ""
        code_id = int(row[2]) if row[2] else None
        code_label = str(row[3]) if row[3] else None
        coded_at = str(row[5]) if row[5] else None
        segments.append(
            Segment(
                index=seg_index,
                filepath=filepath,
                code_id=code_id,
                code_label=code_label,
                coded_at=coded_at,
            )
        )
    return Session(
        segments=segments,
        profile_id="itias_default",
        segments_folder=str(Path(path).parent),
        segment_duration=3,
    )


class CompareWindow(QMainWindow):
    """Compare behavior statistics across multiple lessons."""

    def __init__(self, profile: Profile | None = None, parent=None):
        super().__init__(parent)
        self.profile = profile or load_profile("itias_default")
        self.sessions: list[Session] = []
        self._lesson_labels: list[str] = []
        self.setWindowTitle("多课对比分析")
        self.setMinimumSize(1100, 720)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        import_btn = QPushButton("导入课程...")
        import_btn.clicked.connect(self._import_lessons)
        import_btn.setStyleSheet(
            "QPushButton { background: #5C6BC0; color: white; border-radius: 5px; padding: 6px 16px; }"
            "QPushButton:hover { background: #3949AB; }"
        )
        self._status_label = QLabel("尚未导入课程（最多 30 节）")
        self._status_label.setStyleSheet("color: #666;")
        toolbar.addWidget(import_btn)
        toolbar.addWidget(self._status_label)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._tabs = QTabWidget()
        self._stats_table = QTableWidget()
        self._tabs.addTab(self._stats_table, "对比统计")

        chart_widget = QWidget()
        chart_lay = QVBoxLayout(chart_widget)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("选择类别："))
        self._category_combo = QComboBox()
        for cat_key, cat_label in self.profile.category_labels.items():
            self._category_combo.addItem(cat_label, cat_key)
        self._category_combo.currentIndexChanged.connect(self._refresh_line_chart)
        filter_row.addWidget(self._category_combo)
        filter_row.addStretch()
        chart_lay.addLayout(filter_row)
        self._line_chart_view = QChartView()
        chart_lay.addWidget(self._line_chart_view)
        self._tabs.addTab(chart_widget, "折线对比")

        layout.addWidget(self._tabs)
        self.setCentralWidget(central)

    def _import_lessons(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择课程 Excel 文件",
            os.path.expanduser("~"),
            "Excel 文件 (*.xlsx)",
        )
        if not paths:
            return
        if len(paths) > MAX_LESSONS:
            QMessageBox.warning(
                self,
                "超出上限",
                f"最多同时对比 {MAX_LESSONS} 节课，已截取前 {MAX_LESSONS} 个文件。",
            )
            paths = paths[:MAX_LESSONS]

        sessions: list[Session] = []
        labels: list[str] = []
        for path in paths:
            try:
                session = _session_from_excel(path)
                if not session.segments:
                    continue
                sessions.append(session)
                labels.append(Path(path).stem)
            except Exception as e:
                QMessageBox.warning(self, "导入失败", f"{path}\n{e}")

        if not sessions:
            QMessageBox.warning(self, "导入失败", "未能从所选文件解析出编码数据。")
            return

        self.sessions = sessions
        self._lesson_labels = labels
        self._status_label.setText(f"已导入 {len(sessions)} 节课")
        self._refresh_stats_table()
        self._refresh_line_chart()

    def _refresh_stats_table(self):
        profile = self.profile
        n_lessons = len(self.sessions)
        n_codes = len(profile.codes)
        n_cats = len(profile.category_labels)
        n_rows = n_codes + n_cats

        table = self._stats_table
        table.clear()
        table.setRowCount(n_rows)
        table.setColumnCount(n_lessons + 2)
        headers = ["编码/类别"] + self._lesson_labels + ["均值"]
        table.setHorizontalHeaderLabels(headers)

        code_avg: dict[int, list[int]] = {c.id: [] for c in profile.codes}
        cat_avg: dict[str, list[int]] = {k: [] for k in profile.category_labels}

        row = 0
        for code in profile.codes:
            table.setItem(row, 0, QTableWidgetItem(code.display))
            counts_row: list[int] = []
            for col, session in enumerate(self.sessions):
                counts = behavior_counts(session, profile)
                count = counts.get(code.id, 0)
                total = session.coded_count
                pct = count / total * 100 if total else 0
                item = QTableWidgetItem(f"{count} ({pct:.1f}%)")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col + 1, item)
                counts_row.append(count)
            code_avg[code.id] = counts_row
            mean = sum(counts_row) / len(counts_row) if counts_row else 0
            table.setItem(row, n_lessons + 1, QTableWidgetItem(f"{mean:.1f}"))
            row += 1

        for cat_key, cat_label in profile.category_labels.items():
            table.setItem(row, 0, QTableWidgetItem(cat_label))
            counts_row = []
            for col, session in enumerate(self.sessions):
                counts = category_counts(session, profile)
                count = counts.get(cat_key, 0)
                total = session.coded_count
                pct = count / total * 100 if total else 0
                item = QTableWidgetItem(f"{count} ({pct:.1f}%)")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col + 1, item)
                counts_row.append(count)
            cat_avg[cat_key] = counts_row
            mean = sum(counts_row) / len(counts_row) if counts_row else 0
            table.setItem(row, n_lessons + 1, QTableWidgetItem(f"{mean:.1f}"))
            row += 1

        table.resizeColumnsToContents()

    def _refresh_line_chart(self):
        if not self.sessions:
            self._line_chart_view.setChart(QChart())
            return

        cat_key = self._category_combo.currentData()
        chart = QChart()
        cat_label = self.profile.category_labels.get(cat_key, cat_key)
        chart.setTitle(f"折线对比 — {cat_label}")

        colors = [
            "#E53935", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA",
            "#00ACC1", "#6D4C41", "#546E7A", "#D81B60", "#3949AB",
        ]

        max_y = 0
        for idx, session in enumerate(self.sessions):
            series_data = time_series_by_category(session, self.profile)
            points = series_data.get(cat_key, [])
            if not points:
                continue
            line = QLineSeries()
            line.setName(self._lesson_labels[idx])
            for ts, count in points:
                line.append(ts, count)
                max_y = max(max_y, count)
            pen = line.pen()
            pen.setColor(colors[idx % len(colors)])
            pen.setWidth(2)
            line.setPen(pen)
            chart.addSeries(line)

        axis_x = QValueAxis()
        axis_x.setTitleText("时间（秒）")
        axis_x.setLabelFormat("%d")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setTitleText("出现次数")
        axis_y.setLabelFormat("%d")
        axis_y.setRange(0, max(max_y, 1))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        for s in chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)

        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self._line_chart_view.setChart(chart)

"""Single-lesson analysis window: matrix table + charts."""
from __future__ import annotations

from itias_coder.qt_bindings import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QHBoxLayout,
    QLabel,
    QLineSeries,
    QMainWindow,
    QPieSeries,
    QSplitter,
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
    bin_labels,
    category_counts,
    proportions,
    time_matrix,
    time_series_by_category,
    total_duration_seconds,
)
from ..models import Profile, Session


class AnalysisWindow(QMainWindow):
    """Analysis report for one encoded lesson."""

    def __init__(self, session: Session, profile: Profile, parent=None):
        super().__init__(parent)
        self.session = session
        self.profile = profile
        self.setWindowTitle(f"分析报告 — {profile.name}")
        self.setMinimumSize(1000, 700)
        self._build_ui()

    def _build_ui(self):
        tabs = QTabWidget()
        tabs.addTab(self._build_matrix_tab(), "行为矩阵")
        tabs.addTab(self._build_proportion_tab(), "行为占比")
        tabs.addTab(self._build_timeseries_tab(), "行为时序")
        self.setCentralWidget(tabs)

    def _build_matrix_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        total_sec = total_duration_seconds(self.session)
        matrix = time_matrix(self.session, self.profile)
        rows = bin_labels(60, total_sec)

        table = QTableWidget(len(rows), len(self.profile.codes))
        table.setHorizontalHeaderLabels(
            [f"{c.id} {c.label}" for c in self.profile.codes]
        )
        table.setVerticalHeaderLabels([label for _, label in rows])

        for col, code in enumerate(self.profile.codes):
            header_item = table.horizontalHeaderItem(col)
            if header_item:
                header_item.setBackground(Qt.GlobalColor.transparent)
            table.horizontalHeader().setStyleSheet(
                f"QHeaderView::section:nth-child({col + 1}) "
                f"{{ background-color: {code.color}; }}"
            )

        for row_idx, (bin_start, _) in enumerate(rows):
            bin_data = matrix.get(bin_start, {})
            for col_idx, code in enumerate(self.profile.codes):
                count = bin_data.get(code.id, 0)
                item = QTableWidgetItem(str(count))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row_idx, col_idx, item)

        table.resizeColumnsToContents()
        note = QLabel(
            f"横轴：18类编码 · 纵轴：60秒时间箱 · "
            f"切片时长 {self.session.segment_duration}s · 总时长约 {total_sec}s"
        )
        note.setStyleSheet("color: #666;")
        layout.addWidget(note)
        layout.addWidget(table)
        return widget

    def _build_proportion_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        cat_counts = category_counts(self.session, self.profile)
        code_counts = behavior_counts(self.session, self.profile)
        total = self.session.coded_count

        # Pie chart — 5 categories
        pie_chart = QChart()
        pie_chart.setTitle("类别占比")
        pie_series = QPieSeries()
        for cat_key, cat_label in self.profile.category_labels.items():
            count = cat_counts.get(cat_key, 0)
            if count > 0:
                pct = count / total * 100 if total else 0
                pie_series.append(f"{cat_label} ({pct:.1f}%)", count)
        pie_chart.addSeries(pie_series)
        pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        pie_view = QChartView(pie_chart)

        # Bar chart — 18 codes
        bar_chart = QChart()
        bar_chart.setTitle("编码次数")
        bar_series = QBarSeries()
        bar_set = QBarSet("次数")
        categories = []
        for code in self.profile.codes:
            categories.append(str(code.id))
            bar_set.append(code_counts.get(code.id, 0))
        bar_series.append(bar_set)
        bar_chart.addSeries(bar_series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        bar_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        bar_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)

        bar_view = QChartView(bar_chart)

        # Stats table
        stats = QTableWidget(len(self.profile.codes) + len(self.profile.category_labels), 3)
        stats.setHorizontalHeaderLabels(["项目", "次数", "占比"])
        row = 0
        for cat_key, cat_label in self.profile.category_labels.items():
            count = cat_counts.get(cat_key, 0)
            pct = proportions(cat_counts, total).get(cat_key, 0.0)
            stats.setItem(row, 0, QTableWidgetItem(cat_label))
            stats.setItem(row, 1, QTableWidgetItem(str(count)))
            stats.setItem(row, 2, QTableWidgetItem(f"{pct:.1f}%"))
            row += 1
        stats.setItem(row, 0, QTableWidgetItem("—"))
        row += 1
        for code in self.profile.codes:
            count = code_counts.get(code.id, 0)
            pct = count / total * 100 if total else 0
            stats.setItem(row, 0, QTableWidgetItem(code.display))
            stats.setItem(row, 1, QTableWidgetItem(str(count)))
            stats.setItem(row, 2, QTableWidgetItem(f"{pct:.1f}%"))
            row += 1
        stats.resizeColumnsToContents()

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.addWidget(QLabel("统计明细"))
        right_lay.addWidget(stats)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        charts = QWidget()
        charts_lay = QVBoxLayout(charts)
        charts_lay.addWidget(pie_view)
        charts_lay.addWidget(bar_view)
        splitter.addWidget(charts)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        return widget

    def _build_timeseries_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        series_data = time_series_by_category(self.session, self.profile)
        chart = QChart()
        chart.setTitle("类别时序折线（60秒分箱）")

        colors = ["#4CAF50", "#2196F3", "#FF9800", "#9E9E9E", "#9C27B0"]
        for idx, (cat_key, cat_label) in enumerate(self.profile.category_labels.items()):
            points = series_data.get(cat_key, [])
            if not points:
                continue
            line = QLineSeries()
            line.setName(cat_label)
            for ts, count in points:
                line.append(ts, count)
            chart.addSeries(line)
            color = colors[idx % len(colors)]
            pen = line.pen()
            pen.setColor(color)
            line.setPen(pen)

        axis_x = QValueAxis()
        axis_x.setTitleText("时间（秒）")
        axis_x.setLabelFormat("%d")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setTitleText("出现次数")
        axis_y.setLabelFormat("%d")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        for s in chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)

        chart_view = QChartView(chart)
        layout.addWidget(chart_view)
        return widget

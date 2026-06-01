# src/ui/widgets/temperature_graph_widget.py
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QWidget, QTabWidget
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from src.config.settings import TUBE_SETTINGS
from src.utils.logger_config import setup_logger

logger = setup_logger('temperature_graph_widget')


class TemperatureGraphWidget(QGroupBox):
    """
    Tube별 탭 + Zone1~8 선택 버튼 + Normal/High 온도 그래프 표시 위젯
    - tube 탭을 바꾸면 해당 tube의 normal/high CSV rows 기준으로 그래프를 다시 그림
    - 외부에서 tube_id별 rows를 받아와서 set_temperature_rows()로 업데이트
    - zone 버튼 누르면 현재 선택된 tube/zone 기준으로 다시 그림
    """

    tube_tab_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__("온도 그래프")
        self.parent = parent
        self.setMinimumHeight(560)

        self.tube_count = int(TUBE_SETTINGS.get('TUBE_COUNT', 4))
        self.current_zone = 1
        self.current_tube_id = 1
        self.tube_graphs = {}
        self.plot_colors = {
            "SP": "#7dd3fc",
            "PTC": "#a78bfa",
            "CTC": "#34d399",
        }

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1) Zone1~8 버튼 줄
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.zone_buttons = []
        for i in range(TUBE_SETTINGS.get('ZONE_COUNT', 8)):
            btn = QPushButton(f"Z{i+1}")
            btn.setObjectName("zoneButton")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(self._make_zone_clicked_handler(i + 1))
            button_layout.addWidget(btn)
            self.zone_buttons.append(btn)

        main_layout.addWidget(button_bar)

        # 2) Tube별 Normal / High 그래프 탭
        self.tube_tabs = QTabWidget()
        self.tube_tabs.setObjectName("temperatureGraphTabs")
        self.tube_tabs.setMinimumHeight(500)

        for tube_id in range(1, self.tube_count + 1):
            tab = QWidget()
            tab.setMinimumHeight(460)
            graph_row = QHBoxLayout(tab)
            graph_row.setContentsMargins(10, 10, 10, 10)
            graph_row.setSpacing(12)

            normal_fig, normal_canvas, normal_ax = self._create_graph("Normal 온도 그래프")
            high_fig, high_canvas, high_ax = self._create_graph("High 온도 그래프")

            graph_row.addWidget(normal_canvas)
            graph_row.addWidget(high_canvas)

            self.tube_graphs[tube_id] = {
                "normal_rows": None,
                "high_rows": None,
                "normal_fig": normal_fig,
                "normal_canvas": normal_canvas,
                "normal_ax": normal_ax,
                "high_fig": high_fig,
                "high_canvas": high_canvas,
                "high_ax": high_ax,
            }
            self.tube_tabs.addTab(tab, f"Tube {tube_id}")

        self.tube_tabs.currentChanged.connect(self._on_tube_tab_changed)
        main_layout.addWidget(self.tube_tabs)

    def _create_graph(self, title):
        fig = Figure(figsize=(4, 3), facecolor="#11151d")
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(420)
        ax = fig.add_subplot(111)
        self._style_axis(ax)
        ax.set_title(title)
        ax.set_xlabel("Time (index)")
        ax.set_ylabel("Temperature")
        return fig, canvas, ax

    def _style_axis(self, ax):
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="#8b949e")
        ax.xaxis.label.set_color("#c9d1d9")
        ax.yaxis.label.set_color("#c9d1d9")
        ax.title.set_color("#f0f6fc")
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    def _style_legend(self, ax):
        legend = ax.legend(facecolor="#11151d", edgecolor="#30363d")
        for text in legend.get_texts():
            text.set_color("#c9d1d9")

    def _current_graph(self):
        return self.tube_graphs[self.current_tube_id]

    def _on_tube_tab_changed(self, index):
        if index < 0:
            return
        self.current_tube_id = index + 1
        self.redraw_all()
        self.tube_tab_changed.emit(index)

    def set_current_tube_index(self, index):
        if index < 0 or index >= self.tube_tabs.count():
            return
        if self.tube_tabs.currentIndex() == index:
            return

        self.tube_tabs.blockSignals(True)
        self.tube_tabs.setCurrentIndex(index)
        self.tube_tabs.blockSignals(False)
        self.current_tube_id = index + 1
        self.redraw_all()

    # ----------------- 버튼 핸들러 -----------------
    def _make_zone_clicked_handler(self, zone: int):
        def handler():
            self.current_zone = zone
            # 토글: 한 개만 체크되도록 처리
            for i, b in enumerate(self.zone_buttons, start=1):
                b.setChecked(i == zone)
            logger.info(f"Tube {self.current_tube_id} Zone {zone} 선택")
            self.redraw_all()
        return handler

    # ----------------- 외부에서 호출하는 API -----------------
    def set_temperature_rows(self, tube_id, normal_rows, high_rows):
        graph = self.tube_graphs.get(tube_id)
        if graph is None:
            logger.warning(f"알 수 없는 tube_id의 그래프 업데이트 요청: tube_id={tube_id}")
            return

        graph["normal_rows"] = normal_rows
        graph["high_rows"] = high_rows
        if tube_id == self.current_tube_id:
            self.redraw_all()

    def set_normal_rows(self, rows):
        """현재 선택된 tube의 normal CSV rows를 업데이트한다. 기존 호출부 호환용."""
        self.tube_graphs[self.current_tube_id]["normal_rows"] = rows
        self.update_normal_graph()

    def set_high_rows(self, rows):
        """현재 선택된 tube의 high CSV rows를 업데이트한다. 기존 호출부 호환용."""
        self.tube_graphs[self.current_tube_id]["high_rows"] = rows
        self.update_high_graph()

    def redraw_all(self):
        self.update_normal_graph()
        self.update_high_graph()

    def _extract_series(self, rows, prefix: str, zone: int):
        """
        rows: CSV 전체 rows (0번: 헤더)
        prefix: 'SP', 'PTC', 'CTC'
        zone: 1~8
        return: 해당 컬럼의 float 리스트
        """
        if not rows or len(rows) < 2:
            return []

        header = rows[0]
        col_name = f"{prefix}{zone}"

        try:
            col_idx = header.index(col_name)
        except ValueError:
            logger.warning(f"헤더에서 컬럼 '{col_name}' 을(를) 찾을 수 없습니다.")
            return []

        series = []
        for row in rows[1:]:  # 데이터 행만
            if len(row) <= col_idx:
                continue
            raw = row[col_idx]
            try:
                series.append(float(raw))
            except (TypeError, ValueError):
                # 숫자로 안 바뀌면 0 처리
                series.append(0.0)

        return series

    def _plot_graph(self, ax, canvas, rows, title_prefix):
        ax.clear()
        self._style_axis(ax)

        if not rows:
            ax.set_title(f"Tube {self.current_tube_id} {title_prefix} 온도 그래프 (데이터 없음)")
            canvas.draw()
            return

        sp = self._extract_series(rows, "SP", self.current_zone)
        ptc = self._extract_series(rows, "PTC", self.current_zone)
        ctc = self._extract_series(rows, "CTC", self.current_zone)

        ptc_original = ptc[:]
        max_ptc = max(ptc_original) if ptc_original else None

        length = max(len(sp), len(ptc), len(ctc))
        x = list(range(length))

        def pad(seq):
            return seq + [seq[-1] if seq else 0.0] * (length - len(seq))

        sp = pad(sp)
        ptc = pad(ptc)
        ctc = pad(ctc)

        ax.plot(x, sp, label="SP", color=self.plot_colors["SP"], linewidth=1.8)
        ax.plot(x, ptc, label="PTC", color=self.plot_colors["PTC"], linewidth=1.8)
        ax.plot(x, ctc, label="CTC", color=self.plot_colors["CTC"], linewidth=1.8)

        ax.grid(True, which="both", linestyle="--", alpha=0.25, color="#30363d")
        ax.set_title(f"Tube {self.current_tube_id} {title_prefix} 온도 그래프 - Z{self.current_zone}")
        ax.set_xlabel("Index")
        ax.set_ylabel("Temperature")
        self._style_legend(ax)

        if max_ptc is not None:
            ax.text(
                0.02, 0.95,
                f"PTC max: {max_ptc:.1f}",
                transform=ax.transAxes,
                va="top",
                color="#f0f6fc",
                bbox={"boxstyle": "round,pad=0.35", "facecolor": "#161b22", "edgecolor": "#30363d"}
            )

        canvas.draw()

    # ----------------- 실제 그래프 그리기 -----------------
    @pyqtSlot()
    def update_normal_graph(self):
        graph = self._current_graph()
        self._plot_graph(
            graph["normal_ax"],
            graph["normal_canvas"],
            graph["normal_rows"],
            "Normal",
        )

    @pyqtSlot()
    def update_high_graph(self):
        graph = self._current_graph()
        self._plot_graph(
            graph["high_ax"],
            graph["high_canvas"],
            graph["high_rows"],
            "High",
        )

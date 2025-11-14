# src/ui/widgets/temperature_graph_widget.py
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QWidget
)
from PyQt6.QtCore import pyqtSlot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from src.utils.logger_config import setup_logger

logger = setup_logger('temperature_graph_widget')


class TemperatureGraphWidget(QGroupBox):
    """
    Zone1~8 선택 버튼 + Normal/High 온도 그래프 표시 위젯
    - 외부에서 normal_rows, high_rows 받아와서 update_normal_graph(), update_high_graph() 호출
    - zone 버튼 누르면 선택된 zone 기준으로 다시 그리기
    """
    def __init__(self, parent=None):
        super().__init__("온도 그래프")
        self.parent = parent

        self.current_zone = 1
        self.normal_rows = None
        self.high_rows = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1) Zone1~8 버튼 줄
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.zone_buttons = []
        for i in range(8):
            btn = QPushButton(f"Z{i+1}")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(self._make_zone_clicked_handler(i + 1))
            button_layout.addWidget(btn)
            self.zone_buttons.append(btn)

        main_layout.addWidget(button_bar)

        # 2) Normal / High 그래프 영역
        graph_row = QHBoxLayout()

        # Normal graph
        self.normal_fig = Figure(figsize=(4, 3))
        self.normal_canvas = FigureCanvas(self.normal_fig)
        self.normal_ax = self.normal_fig.add_subplot(111)
        self.normal_ax.set_title("Normal 온도 그래프")
        self.normal_ax.set_xlabel("Time (index)")
        self.normal_ax.set_ylabel("Temperature")

        # High graph
        self.high_fig = Figure(figsize=(4, 3))
        self.high_canvas = FigureCanvas(self.high_fig)
        self.high_ax = self.high_fig.add_subplot(111)
        self.high_ax.set_title("High 온도 그래프")
        self.high_ax.set_xlabel("Time (index)")
        self.high_ax.set_ylabel("Temperature")

        graph_row.addWidget(self.normal_canvas)
        graph_row.addWidget(self.high_canvas)

        main_layout.addLayout(graph_row)

    # ----------------- 버튼 핸들러 -----------------
    def _make_zone_clicked_handler(self, zone: int):
        def handler():
            self.current_zone = zone
            # 토글: 한 개만 체크되도록 처리
            for i, b in enumerate(self.zone_buttons, start=1):
                b.setChecked(i == zone)
            logger.info(f"Zone {zone} 선택")
            self.redraw_all()
        return handler

    # ----------------- 외부에서 호출하는 API -----------------
    def set_normal_rows(self, rows):
        """TriggerMonitor에서 normal CSV 읽은 rows를 넘겨줄 때 사용"""
        self.normal_rows = rows
        self.update_normal_graph()

    def set_high_rows(self, rows):
        """TriggerMonitor에서 high CSV 읽은 rows를 넘겨줄 때 사용"""
        self.high_rows = rows
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

    # ----------------- 실제 그래프 그리기 -----------------
    @pyqtSlot()
    def update_normal_graph(self):
        self.normal_ax.clear()

        if not self.normal_rows:
            self.normal_ax.set_title("Normal 온도 그래프 (데이터 없음)")
            self.normal_canvas.draw()
            return

        # 현재 선택된 zone 기준으로 SP, PTC, CTC만 뽑기
        sp = self._extract_series(self.normal_rows, "SP", self.current_zone)
        ptc = self._extract_series(self.normal_rows, "PTC", self.current_zone)
        ctc = self._extract_series(self.normal_rows, "CTC", self.current_zone)

        # PTC 원본값(패딩 전)으로 최대값 계산
        ptc_original = ptc[:]  # 복사본
        max_ptc = max(ptc_original) if ptc_original else None

        # x축은 데이터 인덱스 (0,1,2,...)
        length = max(len(sp), len(ptc), len(ctc))
        x = list(range(length))

        # 부족한 쪽은 길이 맞춰주기
        def pad(seq):
            return seq + [seq[-1] if seq else 0.0] * (length - len(seq))

        sp = pad(sp)
        ptc = pad(ptc)
        ctc = pad(ctc)

        self.normal_ax.plot(x, sp, label="SP")
        self.normal_ax.plot(x, ptc, label="PTC")
        self.normal_ax.plot(x, ctc, label="CTC")

        # 그리드 켜기
        self.normal_ax.grid(True, which="both", linestyle="--", alpha=0.4)

        self.normal_ax.set_title(f"Normal 온도 그래프 - Z{self.current_zone}")
        self.normal_ax.set_xlabel("Index")
        self.normal_ax.set_ylabel("Temperature")
        self.normal_ax.legend()

        # PTC 최대값 텍스트로 표시 (좌측 상단)
        if max_ptc is not None:
            self.normal_ax.text(
                0.02, 0.95,
                f"PTC max: {max_ptc:.1f}",
                transform=self.normal_ax.transAxes,
                va="top"
            )

        self.normal_canvas.draw()

    @pyqtSlot()
    def update_high_graph(self):
        self.high_ax.clear()

        if not self.high_rows:
            self.high_ax.set_title("High 온도 그래프 (데이터 없음)")
            self.high_canvas.draw()
            return

        sp = self._extract_series(self.high_rows, "SP", self.current_zone)
        ptc = self._extract_series(self.high_rows, "PTC", self.current_zone)
        ctc = self._extract_series(self.high_rows, "CTC", self.current_zone)

        ptc_original = ptc[:]
        max_ptc = max(ptc_original) if ptc_original else None

        length = max(len(sp), len(ptc), len(ctc))
        x = list(range(length))

        def pad(seq):
            return seq + [seq[-1] if seq else 0.0] * (length - len(seq))

        sp = pad(sp)
        ptc = pad(ptc)
        ctc = pad(ctc)

        self.high_ax.plot(x, sp, label="SP")
        self.high_ax.plot(x, ptc, label="PTC")
        self.high_ax.plot(x, ctc, label="CTC")

        # 그리드 켜기
        self.high_ax.grid(True, which="both", linestyle="--", alpha=0.4)

        self.high_ax.set_title(f"High 온도 그래프 - Z{self.current_zone}")
        self.high_ax.set_xlabel("Index")
        self.high_ax.set_ylabel("Temperature")
        self.high_ax.legend()

        # PTC 최대값 텍스트 표시
        if max_ptc is not None:
            self.high_ax.text(
                0.02, 0.95,
                f"PTC max: {max_ptc:.1f}",
                transform=self.high_ax.transAxes,
                va="top"
            )

        self.high_canvas.draw()


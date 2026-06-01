# src/ui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt  # Qt 추가
from PyQt6.QtGui import QGuiApplication
from src.ui.widgets.connection_widget import ConnectionWidget
from src.ui.widgets.heartbeat_widget import HeartbeatWidget
from src.ui.widgets.trigger_monitor_widget import TriggerMonitorWidget
from src.ui.widgets.temperature_graph_widget import TemperatureGraphWidget
from src.config.settings import UI_SETTINGS
from src.utils.logger_config import setup_logger


logger = setup_logger('main_window')

class PLCMonitoringApp(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("PLC 모니터링 애플리케이션 시작")
        self.graph_widget = TemperatureGraphWidget()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PLC 모니터링 시스템")
        
        # 윈도우 크기 설정: 기본 크기는 1920x1050을 사용하되 사용자가 조절 가능하게 유지
        default_width = 800  # 기본값 설정
        default_height = 600  # 기본값 설정
        initial_width = UI_SETTINGS.get('WINDOW_WIDTH', default_width)
        initial_height = UI_SETTINGS.get('WINDOW_HEIGHT', default_height)
        self.resize(initial_width, initial_height)
        self.setMinimumSize(1280, 720)
        
        # 윈도우를 화면 중앙에 위치
        self.setGeometry(
            (self.screen().availableGeometry().width() - self.width()) // 2,
            (self.screen().availableGeometry().height() - self.height()) // 2,
            self.width(),
            self.height()
        )

        # 윈도우 플래그 설정 - 항상 최상위에 표시
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # 메인 위젯 설정: 컨텐츠 높이가 창보다 커질 수 있으므로 QScrollArea를 중앙 위젯으로 사용
        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setCentralWidget(scroll_area)

        main_widget = QWidget()
        main_widget.setObjectName("appRoot")
        main_widget.setMinimumWidth(1500)
        scroll_area.setWidget(main_widget)

        # 메인 레이아웃을 수직 레이아웃으로 변경
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)  # 여백 추가
        main_layout.setSpacing(12)

        # Codex 느낌의 상단 헤더
        hero_bar = QWidget()
        hero_bar.setObjectName("heroBar")
        hero_bar.setMinimumHeight(92)
        hero_layout = QHBoxLayout(hero_bar)
        hero_layout.setContentsMargins(18, 14, 18, 14)

        title_column = QVBoxLayout()
        title_label = QLabel("DFHT Temperature Monitor")
        title_label.setObjectName("appTitle")
        subtitle_label = QLabel("4-Tube independent trigger logging · parameter tuning console")
        subtitle_label.setObjectName("appSubtitle")
        title_column.addWidget(title_label)
        title_column.addWidget(subtitle_label)

        tube_pill = QLabel("4 TUBE READY")
        tube_pill.setObjectName("statusPill")
        tube_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hero_layout.addLayout(title_column)
        hero_layout.addStretch()
        hero_layout.addWidget(tube_pill)
        main_layout.addWidget(hero_bar)

        # 상단 위젯들을 위한 수평 레이아웃 컨테이너
        top_container = QWidget()
        top_container.setMinimumHeight(250)
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)  # 위젯 간 간격 설정

        # 상단 위젯 추가
        self.connection_widget = ConnectionWidget()
        self.heartbeat_widget = HeartbeatWidget()
        self.trigger_monitor = TriggerMonitorWidget(self.connection_widget.plc_connector)

        self.connection_widget.setMinimumHeight(230)
        self.heartbeat_widget.setMinimumHeight(230)
        self.trigger_monitor.status_container.setMinimumHeight(230)
        self.trigger_monitor.tables_container.setMinimumHeight(300)
        self.trigger_monitor.new_tables_container.setMinimumHeight(300)
        self.graph_widget.setMinimumHeight(560)

        # 각 위젯의 크기 정책 설정
        top_layout.addWidget(self.connection_widget, stretch=1)
        top_layout.addWidget(self.heartbeat_widget, stretch=1)
        top_layout.addWidget(self.trigger_monitor.status_container, stretch=1)

        # 메인 레이아웃에 상단 컨테이너 추가
        main_layout.addWidget(top_container)
        
        # 테이블 컨테이너 추가
        main_layout.addWidget(self.trigger_monitor.tables_container)
        main_layout.addWidget(self.trigger_monitor.new_tables_container)

        # 4~5행: Zone 버튼 + Normal/High 그래프 (그래프 위젯 안에 모두 포함)
        main_layout.addWidget(self.graph_widget)
        self.trigger_monitor.temperature_log_updated.connect(
            self.on_temperature_log_updated
        )

        # 연결 상태에 따른 트리거 모니터링 제어
        self.connection_widget.connection_status_changed.connect(self.handle_connection_status)

        # 위젯 간 시그널 연결
        self.connection_widget.connection_status_changed.connect(
            self.heartbeat_widget.handle_connection_status
        )
        
        # 윈도우를 표시
        self.show()
        
        # 로그 추가
        logger.info(f"윈도우 크기: {self.width()}x{self.height()}")
        logger.info("UI 초기화 완료")

    def center_on_screen(self):
        # 모니터 전체 해상도(작업표시줄 포함)
        screen = self.screen() or QGuiApplication.primaryScreen()
        geo = screen.geometry()

        # 중앙 좌표 계산
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + (geo.height() - self.height()) // 2

        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()
        self.raise_()
        self.activateWindow()

    def handle_connection_status(self, is_connected):
        if is_connected:
            self.trigger_monitor.start_monitoring()
            logger.info("모니터링 시작")
        else:
            self.trigger_monitor.stop_monitoring()
            logger.info("모니터링 중지")

    def on_temperature_log_updated(self, normal_rows, high_rows):
        self.graph_widget.set_normal_rows(normal_rows)
        self.graph_widget.set_high_rows(high_rows)
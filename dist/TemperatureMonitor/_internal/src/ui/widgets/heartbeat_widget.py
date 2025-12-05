# src/ui/widgets/heartbeat_widget.py
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from src.config.settings import PLC_SETTINGS
from src.utils.logger_config import setup_logger

logger = setup_logger('heartbeat_monitor')

class HeartbeatWidget(QGroupBox):
    def __init__(self):
        super().__init__("PLC Heartbeat 모니터링")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 상태 표시
        self.connection_status = QLabel("연결 상태: 미연결")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        
        # Heartbeat 표시기
        self.heartbeat_indicator = QFrame()
        self.heartbeat_indicator.setFixedSize(50, 50)
        self.heartbeat_indicator.setStyleSheet(
            "background-color: red; border-radius: 25px;"
        )
        
        # Heartbeat 카운터
        self.heartbeat_count = QLabel("Heartbeat 카운트: 0")
        self.heartbeat_count_value = 0
        
        # Memory Area 표시
        self.memory_area = QLabel(f"메모리 영역: {PLC_SETTINGS['HEARTBEAT_MEMORY_AREA']:#X}")
        self.word_address = QLabel(f"워드 주소: {PLC_SETTINGS['HEARTBEAT_WORD_ADDR']}")
        
        layout.addWidget(self.connection_status)
        layout.addWidget(self.memory_area)
        layout.addWidget(self.word_address)
        layout.addWidget(self.heartbeat_indicator, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.heartbeat_count, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(layout)
        
        # Heartbeat 타이머 설정
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.update_heartbeat)
        
    def handle_connection_status(self, is_connected):
        if is_connected:
            logger.debug("Heart beat 상태제어 시작")
            self.connection_status.setText("연결 상태: 연결됨")
            logger.debug("Heart beat 상태 변경: 연결됨")
            self.connection_status.setStyleSheet("color: green; font-weight: bold;")
            logger.debug("Heart beat 상태 변경: 색상 변경(녹색)")
            self.heartbeat_timer.start(PLC_SETTINGS['HEARTBEAT_INTERVAL'])
            logger.debug(f"Heart beat 상태 변경: 타이머-{PLC_SETTINGS['HEARTBEAT_INTERVAL']}ms")
        else:
            self.connection_status.setText("연결 상태: 미연결")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
            self.heartbeat_timer.stop()
            self.heartbeat_count_value = 0
            self.heartbeat_count.setText(f"Heartbeat 카운트: {self.heartbeat_count_value}")
            self.heartbeat_indicator.setStyleSheet(
                "background-color: red; border-radius: 25px;"
            )
    
    def update_heartbeat(self):
        self.heartbeat_count_value += 1
        self.heartbeat_count.setText(f"Heartbeat 카운트: {self.heartbeat_count_value}")
        logger.debug(f"Heart beat 상태제어 진행중..카운터: {self.heartbeat_count_value}")
        
        current_color = "green" if self.heartbeat_count_value % 2 == 0 else "Gray"
        self.heartbeat_indicator.setStyleSheet(
            f"background-color: {current_color}; border-radius: 25px;"
        )
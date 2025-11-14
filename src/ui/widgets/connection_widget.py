# src/ui/widgets/connection_widget.py
from PyQt6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                            QLabel, QLineEdit, QPushButton, QSpinBox,QFileDialog)
from PyQt6.QtCore import pyqtSignal
from src.communication.plc_connector import PLCConnector
from src.config.settings import PLC_SETTINGS
from src.utils.logger_config import setup_logger

logger = setup_logger('connection_widget')

class ConnectionWidget(QGroupBox):
    connection_status_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__("PLC 연결 설정")
        self.plc_connector = PLCConnector()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # IP 설정
        ip_layout = QHBoxLayout()
        ip_label = QLabel("PLC IP 주소:")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText(PLC_SETTINGS['DEFAULT_IP'])
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)

        # 포트 설정
        port_layout = QHBoxLayout()
        port_label = QLabel("포트:")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(PLC_SETTINGS['DEFAULT_PORT'])
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)

        # 노드 설정
        node_layout = QHBoxLayout()
        plc_node_label = QLabel("PLC 노드:")
        self.plc_node_input = QSpinBox()
        self.plc_node_input.setRange(0, 255)
        self.plc_node_input.setValue(PLC_SETTINGS['DEFAULT_PLC_NODE'])

        pc_node_label = QLabel("PC 노드:")
        self.pc_node_input = QSpinBox()
        self.pc_node_input.setRange(0, 255)
        self.pc_node_input.setValue(PLC_SETTINGS['DEFAULT_PC_NODE'])

        node_layout.addWidget(plc_node_label)
        node_layout.addWidget(self.plc_node_input)
        node_layout.addWidget(pc_node_label)
        node_layout.addWidget(self.pc_node_input)

        # 로그 파일 경로 설정
        log_layout = QHBoxLayout()
        log_label = QLabel("로그 파일 경로:")
        self.log_path_input = QLineEdit()
        self.log_path_input.setPlaceholderText("예: C:/logs/")
        log_browse_btn = QPushButton("찾기")

        # 파일/폴더 선택 다이얼로그
        log_browse_btn.clicked.connect(self.browse_log_path)

        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_path_input)
        log_layout.addWidget(log_browse_btn)

        # 버튼 그룹
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("통신 시작")
        self.disconnect_button = QPushButton("통신 중단")
        self.disconnect_button.setEnabled(False)

        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)

        # 레이아웃 구성
        layout.addLayout(ip_layout)
        layout.addLayout(port_layout)
        layout.addLayout(node_layout)
        layout.addLayout(log_layout)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 이벤트 연결
        self.connect_button.clicked.connect(self.start_communication)
        self.disconnect_button.clicked.connect(self.stop_communication)

    def browse_log_path(self):
        folder = QFileDialog.getExistingDirectory(self, "로그 폴더 선택")
        if folder:
            self.log_path_input.setText(folder)

    def start_communication(self):
        ip_address = self.ip_input.text() or PLC_SETTINGS['DEFAULT_IP']
        port = self.port_input.value()
        plc_node = self.plc_node_input.value()
        pc_node = self.pc_node_input.value()
        log_path = self.log_path_input.text().strip()
        PLC_SETTINGS['LOG_DIRECTORY'] = log_path

        if self.plc_connector.connect(
            ip_address=ip_address,
            plc_port=port,
            plc_node=plc_node,
            pc_node=pc_node
        ):
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.connection_status_changed.emit(True)
            logger.info(f"PLC 연결 성공: {ip_address}:{port}")
        else:
            logger.error("PLC 연결 실패")

    def stop_communication(self):
        self.plc_connector.disconnect()
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.connection_status_changed.emit(False)
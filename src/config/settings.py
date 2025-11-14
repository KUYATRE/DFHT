# src/config/settings.py
import os

UI_SETTINGS = {
    'WINDOW_WIDTH': 1920,
    'WINDOW_HEIGHT': 1050,
}

PLC_SETTINGS = {
    'DEFAULT_IP': '172.22.80.1',
    'DEFAULT_PORT': 9600,
    'DEFAULT_PLC_NODE': 1,
    'DEFAULT_PC_NODE': 3,
    'HEARTBEAT_INTERVAL': 1000,  # milliseconds
    'HEARTBEAT_MEMORY_AREA': 0xAF,  # EM 영역
    'HEARTBEAT_WORD_ADDR': 0,
    'LOG_DIRECTORY': '',
}

LOGGING_SETTINGS = {
    'LOG_DIR': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs'),
    'MAX_LOG_SIZE': 10 * 1024 * 1024,  # 10MB
    'BACKUP_COUNT': 30,
    'DEBUG_BACKUP_COUNT': 5,
}
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

TUBE_SETTINGS = {
    # Tube 수를 늘릴 때는 이 값과, 필요 시 아래 주소/비트 stride 또는 TRIGGER_ADDRESS_MAP만 조정합니다.
    'TUBE_COUNT': 4,
    'ZONE_COUNT': 6,

    # 튜브별 Trigger bit 기본 매핑: TRIGGER_WORD_ADDR_BASE + (tube_id - 1) * TRIGGER_WORD_STRIDE
    # 기본값은 Tube 1=AF1, Tube 2=AF2, Tube 3=AF3, Tube 4=AF4에서 동일 bit offset을 사용합니다.
    'TRIGGER_MEMORY_AREA': 0xAF,
    'TRIGGER_WORD_ADDR_BASE': 1,
    'TRIGGER_WORD_STRIDE': 1,
    'PARAM_TRIGGER_BIT_OFFSET': 1,
    'TEMP_TRIGGER_BIT_OFFSET': 2,
    'TEMP_NORMAL_BIT_OFFSET': 3,
    'TEMP_HIGH_BIT_OFFSET': 4,

    # PLC 비트 주소가 튜브별로 불규칙하면 아래 dict에 tube_id별 주소를 명시할 수 있습니다.
    # 예: {2: {'param': {'word_addr': 10, 'bit_offset': 1}}}
    'TRIGGER_ADDRESS_MAP': {},

    # 튜브별 Job 정보: AF500, AF502, AF504, ... 에서 [tube, job] 2 words를 읽습니다.
    'JOB_INFO_MEMORY_AREA': 0xAF,
    'JOB_INFO_WORD_ADDR_BASE': 500,
    'JOB_INFO_WORD_STRIDE': 2,

    # 온도 데이터 블록: tube별 base = TEMPERATURE_DATA_BASE + (tube_id - 1) * TEMPERATURE_DATA_STRIDE
    'TEMPERATURE_MEMORY_AREA': 0xA0,
    'TEMPERATURE_DATA_BASE': 17550,
    'TEMPERATURE_DATA_STRIDE': 1000,
    'TEMPERATURE_BLOCK_OFFSETS': {
        'ptc': 0,
        'ctc': 10,
        'sp': 20,
        'mv': 30,
    },

    # 파라미터 테이블 주소: table base + (tube_id - 1) * PARAM_ADDRESS_STRIDE + row_offset + zone * PARAM_ZONE_STRIDE
    'PARAM_MEMORY_AREA': 0xA0,
    'PARAM_ADDRESS_STRIDE': 1000,
    'PARAM_ZONE_STRIDE': 5,
    'PARAM_ADDRESS_BASES': {
        'prev_normal': 840,
        'prev_high': 842,
        'new_normal': 17600,
        'new_high': 17602,
    },
    'PARAM_ROW_OFFSETS': {
        'prev_normal': [0, 1],
        'prev_high': [0, 1],
        'new_normal': [0, 1],
        'new_high': [0, 1],
    },
}

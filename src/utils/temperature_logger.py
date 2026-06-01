import csv
import os
from pathlib import Path
from datetime import datetime
from src.communication.plc_connector import PLCConnector
from src.config.settings import PLC_SETTINGS, TUBE_SETTINGS
from src.utils.logger_config import setup_logger

logger = setup_logger('temperature_logger')
plc_connector = PLCConnector()


def _connector(connector=None):
    if connector is not None:
        return connector
    if not plc_connector.is_connected():
        plc_connector.connect(
            ip_address=PLC_SETTINGS['DEFAULT_IP'],
            plc_port=PLC_SETTINGS['DEFAULT_PORT'],
            plc_node=PLC_SETTINGS['DEFAULT_PLC_NODE'],
            pc_node=PLC_SETTINGS['DEFAULT_PC_NODE'],
        )
    return plc_connector


def _normalize_words(words, count):
    if words is None:
        return [0] * count
    if isinstance(words, int):
        words = [words]
    else:
        words = list(words)
    if len(words) < count:
        words += [0] * (count - len(words))
    elif len(words) > count:
        words = words[:count]
    return words


def init_plc_csv_logger(temp_area: str, tube_id: int | None = None, job_id: int | None = None, plc_connector=None):
    """
    temp_area = "normal" / "high" 같은 문자열
    CSV 로그 파일 생성 + writer 반환
    """
    log_dir = os.path.join(os.getcwd(), "temperature_logs")
    os.makedirs(log_dir, exist_ok=True)

    if tube_id is None or job_id is None:
        read_tube_id, read_job_id = job_info_read(tube_id=tube_id, plc_connector=plc_connector)
        tube_id = tube_id or read_tube_id
        job_id = job_id if job_id is not None else read_job_id

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"temperature_T{tube_id}_{job_id}_{temp_area}_{timestamp}.csv"
    file_path = os.path.join(log_dir, filename)

    log_file = open(file_path, mode="w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)

    zone_count = TUBE_SETTINGS.get('ZONE_COUNT', 8)
    header = ["time", "tube", "job"]
    for prefix in ("PTC", "CTC", "SP", "MV"):
        header.extend(f"{prefix}{zone}" for zone in range(1, zone_count + 1))

    log_writer.writerow(header)
    log_file.flush()

    logger.info(f"Temperature CSV Log Started: {file_path}")
    return log_file, log_writer, file_path


def data_read(tube_id: int | None = None, job_id: int | None = None, plc_connector=None):
    connector = _connector(plc_connector)

    if tube_id is None or job_id is None:
        read_tube_id, read_job_id = job_info_read(tube_id=tube_id, plc_connector=connector)
        tube_id = tube_id or read_tube_id
        job_id = job_id if job_id is not None else read_job_id

    zone_count = TUBE_SETTINGS.get('ZONE_COUNT', 8)
    base = TUBE_SETTINGS['TEMPERATURE_DATA_BASE'] + (tube_id - 1) * TUBE_SETTINGS['TEMPERATURE_DATA_STRIDE']
    mem_area = TUBE_SETTINGS['TEMPERATURE_MEMORY_AREA']
    offsets = TUBE_SETTINGS['TEMPERATURE_BLOCK_OFFSETS']

    ptc = [v / 10 for v in read_block(mem_area, base + offsets['ptc'], zone_count, connector)]
    ctc = [v / 10 for v in read_block(mem_area, base + offsets['ctc'], zone_count, connector)]
    sp = [v / 10 for v in read_block(mem_area, base + offsets['sp'], zone_count, connector)]
    mv = read_block(mem_area, base + offsets['mv'], zone_count, connector)

    row_values = [tube_id, job_id] + ptc + ctc + sp + mv
    logger.debug(f"data_read row_values: {row_values}")
    return row_values


def read_block(mem_area, word_addr: int, count: int, plc_connector=None) -> list[int]:
    connector = _connector(plc_connector)
    data = connector.read_word(
        mem_area=mem_area,
        word_addr=word_addr,
        word_count=count
    )

    if data is None:
        logger.warning(f"read_block: addr={word_addr}, count={count} → None 반환, 0으로 대체")
        return [0] * count

    return _normalize_words(data, count)


def append_temperature_log(log_file, log_writer, tube_id: int | None = None, job_id: int | None = None, plc_connector=None):
    if log_file is None or log_writer is None:
        logger.warning("append_temperature_log: log_file 또는 log_writer가 None 입니다. (초기화 안 됨)")
        return

    values = data_read(tube_id=tube_id, job_id=job_id, plc_connector=plc_connector)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp] + values

    try:
        log_writer.writerow(row)
        log_file.flush()
        logger.debug(f"로그 1줄 추가됨 → {row}")
    except Exception as e:
        logger.exception(f"append_temperature_log 중 예외 발생: {e}")


def job_info_read(tube_id: int | None = None, plc_connector=None):
    connector = _connector(plc_connector)
    word_addr = TUBE_SETTINGS['JOB_INFO_WORD_ADDR_BASE']
    if tube_id is not None:
        word_addr += (tube_id - 1) * TUBE_SETTINGS['JOB_INFO_WORD_STRIDE']

    job_info = connector.read_word(
        mem_area=TUBE_SETTINGS['JOB_INFO_MEMORY_AREA'],
        word_addr=word_addr,
        word_count=2
    )

    if job_info is None:
        logger.warning("job_info 읽기 실패 → 기본값 [tube_id or 0, 0] 사용")
        return tube_id or 0, 0

    job_info = _normalize_words(job_info, 2)
    read_tube_id, job_id = job_info[:2]

    if tube_id is not None:
        read_tube_id = tube_id

    return read_tube_id, job_id


def _get_log_dir() -> Path:
    return Path(os.getcwd()) / "temperature_logs"


def _read_csv_rows(path: Path):
    try:
        rows = []
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
        logger.debug(f"_read_csv_rows: {path} → {len(rows)}행 읽음")
        return rows
    except Exception as e:
        logger.exception(f"_read_csv_rows: CSV 읽기 실패: {path}, 예외: {e}")
        return None


def get_latest_temperature_log(tube_id: int, job_id: int, temp_area: str):
    log_dir = _get_log_dir()

    if not log_dir.exists():
        logger.warning(f"get_latest_temperature_log: 로그 디렉토리가 존재하지 않습니다: {log_dir}")
        return None, None

    pattern = f"temperature_T{tube_id}_{job_id}_{temp_area}_*.csv"
    candidates = list(log_dir.glob(pattern))

    if not candidates:
        logger.info(f"get_latest_temperature_log: 패턴에 맞는 파일 없음: {pattern}")
        return None, None

    latest_path = max(candidates, key=lambda p: p.stat().st_mtime)
    rows = _read_csv_rows(latest_path)

    return latest_path, rows


def get_latest_temperature_logs(tube_id: int, job_id: int):
    normal_path, normal_rows = get_latest_temperature_log(tube_id, job_id, "normal")
    high_path, high_rows = get_latest_temperature_log(tube_id, job_id, "high")

    return {
        "normal": {"path": normal_path, "rows": normal_rows},
        "high": {"path": high_path, "rows": high_rows},
    }

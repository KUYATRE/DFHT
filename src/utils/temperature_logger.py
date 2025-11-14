import csv
import os
from pathlib import Path
from datetime import datetime
from src.communication.plc_connector import PLCConnector
from src.utils.logger_config import setup_logger

logger = setup_logger('temperature_logger')
plc_connector = PLCConnector()
plc_connector.connect(
    ip_address="172.22.80.1",
    plc_port=9600,
    plc_node=1,
    pc_node=3
)

def init_plc_csv_logger(temp_area: str):
    """
    temp_area = "Normal" / "High" 같은 문자열
    CSV 로그 파일 생성 + writer 반환
    """

    # ------------------------------
    # 1) 로그 디렉토리 생성
    # ------------------------------
    log_dir = os.path.join(os.getcwd(), "temperature_logs")
    os.makedirs(log_dir, exist_ok=True)

    # ------------------------------
    # 2) Job 정보 읽기
    # ------------------------------
    job_info = plc_connector.read_word(
        mem_area=0xAF,
        word_addr=500,
        word_count=2
    )

    # 예외 처리
    if job_info is None:
        logger.warning("job_info 읽기 실패 → 기본값으로 로그 생성")
        job_info = [0, 0]

    # 리스트 보정
    if isinstance(job_info, int):
        job_info = [job_info, 0]
    elif isinstance(job_info, (list, tuple)) and len(job_info) < 2:
        job_info = list(job_info) + [0] * (2 - len(job_info))

    tube_id, job_id = job_info[:2]

    # ------------------------------
    # 3) 파일 생성
    # ------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"temperature_T{tube_id}_{job_id}_{temp_area}_{timestamp}.csv"
    file_path = os.path.join(log_dir, filename)

    log_file = open(file_path, mode="w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)

    # ------------------------------
    # 4) 헤더 생성
    # ------------------------------
    header = [
        "time", "tube", "job",
        "PTC1", "PTC2", "PTC3", "PTC4", "PTC5", "PTC6", "PTC7", "PTC8",
        "CTC1", "CTC2", "CTC3", "CTC4", "CTC5", "CTC6", "CTC7", "CTC8",
        "SP1", "SP2", "SP3", "SP4", "SP5", "SP6", "SP7", "SP8",
        "MV1", "MV2", "MV3", "MV4", "MV5", "MV6", "MV7", "MV8"
    ]

    log_writer.writerow(header)
    log_file.flush()

    logger.info(f"Temperature CSV Log Started: {file_path}")

    # ------------------------------
    # 5) 호출자에게 writer 반환
    # ------------------------------
    return log_file, log_writer, file_path

def data_read():
    # 1) Job 정보 읽기
    job_info = plc_connector.read_word(
        mem_area=0xAF,
        word_addr=500,
        word_count=2
    )

    if job_info is None:
        logger.warning("job_info 읽기 실패 → 기본값 [0, 0] 사용")
        job_info = [0, 0]

    if isinstance(job_info, int):
        job_info = [job_info, 0]
    elif isinstance(job_info, (list, tuple)) and len(job_info) < 2:
        job_info = list(job_info) + [0] * (2 - len(job_info))

    tube_id, job_id = job_info[:2]

    # 2) PTC/CTC/SP/MV 블록 읽기
    base = 17550 + (tube_id - 1) * 800

    ptc = [v / 10 for v in read_block(0xA0, base + 0, 8)]   # 17550 ~
    ctc = [v / 10 for v in read_block(0xA0, base + 10, 8)]  # 17560 ~
    sp  = [v / 10 for v in read_block(0xA0, base + 20, 8)]  # 17570 ~
    mv  = read_block(0xA0, base + 30, 8)                    # 17580 ~

    # 3) CSV row에 딱 맞는 평탄화 리스트로 반환
    #    [tube, job, PTC 8개, CTC 8개, SP 8개, MV 8개]
    row_values = [tube_id, job_id] + ptc + ctc + sp + mv

    logger.debug(f"data_read row_values: {row_values}")

    return row_values


def read_block(mem_area, word_addr: int, count: int) -> list[int]:
    """
    PLC에서 특정 word_addr부터 count개 읽어서
    항상 길이 count인 리스트로 반환
    """
    data = plc_connector.read_word(
        mem_area=mem_area,
        word_addr=word_addr,
        word_count=count
    )

    if data is None:
        logger.warning(f"read_block: addr={word_addr}, count={count} → None 반환, 0으로 대체")
        return [0] * count

    # int 하나만 오는 경우
    if isinstance(data, int):
        return [data] + [0] * (count - 1)

    # 리스트/튜플인 경우 길이 보정
    data = list(data)
    if len(data) < count:
        data += [0] * (count - len(data))
    elif len(data) > count:
        data = data[:count]

    return data

def append_temperature_log(log_file, log_writer):
    # log_file 또는 log_writer가 아직 초기화 안 된 경우
    if log_file is None or log_writer is None:
        logger.warning("append_temperature_log: log_file 또는 log_writer가 None 입니다. (초기화 안 됨)")
        return

    # 값 읽기
    values = data_read()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [timestamp] + values

    # CSV append
    try:
        log_writer.writerow(row)
        log_file.flush()
        logger.debug(f"로그 1줄 추가됨 → {row}")
    except Exception as e:
        logger.exception(f"append_temperature_log 중 예외 발생: {e}")

def job_info_read():
    # 1) Job 정보 읽기
    job_info = plc_connector.read_word(
        mem_area=0xAF,
        word_addr=500,
        word_count=2
    )

    if job_info is None:
        logger.warning("job_info 읽기 실패 → 기본값 [0, 0] 사용")
        job_info = [0, 0]

    if isinstance(job_info, int):
        job_info = [job_info, 0]
    elif isinstance(job_info, (list, tuple)) and len(job_info) < 2:
        job_info = list(job_info) + [0] * (2 - len(job_info))

    tube_id, job_id = job_info[:2]

    return tube_id, job_id


def _get_log_dir() -> Path:
    """
    temperature_logs 디렉토리 Path 반환
    (없으면 None 대신 경로만 반환하고, 사용하는 쪽에서 존재 여부 확인)
    """
    return Path(os.getcwd()) / "temperature_logs"


def _read_csv_rows(path: Path):
    """
    주어진 CSV 파일을 모두 읽어서 list[list[str]] 형태로 반환.
    읽기 실패 시 None 반환.
    """
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
    """
    특정 tube_id, job_id, temp_area("normal" 또는 "high")에 대해
    temperature_logs 폴더에서
      temperature_T{tube_id}_{job_id}_{temp_area}_*.csv
    패턴에 해당하는 파일 중 가장 최신 파일을 찾아
    (Path, rows) 튜플로 반환한다.

    파일이 없으면 (None, None) 반환.
    """
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
    """
    편의 함수:
    주어진 tube_id, job_id에 대해
    normal, high 각각의 최신 로그를 찾아 한 번에 반환.

    return:
        {
            "normal": {"path": Path | None, "rows": list[list[str]] | None},
            "high":   {"path": Path | None, "rows": list[list[str]] | None},
        }
    """
    normal_path, normal_rows = get_latest_temperature_log(tube_id, job_id, "normal")
    high_path,   high_rows   = get_latest_temperature_log(tube_id, job_id, "high")

    return {
        "normal": {"path": normal_path, "rows": normal_rows},
        "high":   {"path": high_path,   "rows": high_rows},
    }

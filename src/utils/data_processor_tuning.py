from typing import List, Tuple
from src.utils.logger_config import setup_logger

logger = setup_logger('data_processor_tuning')

def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def max_ptc_zones(rows, zones=8):
    max_ptc_zone = []
    for i in range(zones):
        ptc_list = ptc_scrap(rows, i + 1)
        if ptc_list:
            max_ptc_zone.append(max(ptc_list))
        else:
            max_ptc_zone.append(0.0)
    return max_ptc_zone


def search_temp_retain_point(rows):
    # SP1(zone1) 트렌드로 retain point 찾기
    sp1 = set_point_scrap(rows, 1)

    retain_point = 0
    data_buffer1 = 0.0
    counter = 0
    for index, val in enumerate(sp1):
        if data_buffer1 < val:
            data_buffer1 = val
            counter = 0
        elif data_buffer1 == val:
            counter += 1

        if counter == 100:
            retain_point = index - 100

    return retain_point


def retain_point_ctc_zones(rows, zones=8):
    retain_point = search_temp_retain_point(rows)

    retain_point_ctc_zone = []
    for i in range(zones):
        ctc_list = ctc_scrap(rows, i + 1)
        if 0 <= retain_point < len(ctc_list):
            retain_point_ctc_zone.append(ctc_list[retain_point])
        else:
            retain_point_ctc_zone.append(0.0)

    return retain_point_ctc_zone


def retain_point_ptc_average(rows, zones=8):
    retain_point = search_temp_retain_point(rows)

    retain_point_ptc_average_list = []
    for i in range(zones):
        ptc_list = ptc_scrap(rows, i + 1)

        start = retain_point + 1
        end = retain_point + 61
        start = max(start, 0)
        end = min(end, len(ptc_list))

        if end > start:
            avg = sum(ptc_list[start:end]) / (end - start)
        else:
            avg = 0.0

        retain_point_ptc_average_list.append(avg)

    return retain_point_ptc_average_list


def retain_sp_zones(rows, zones=8):
    retain_point = search_temp_retain_point(rows)

    retain_sp_zone = []
    for i in range(zones):
        sp_list = set_point_scrap(rows, i + 1)
        if 0 <= retain_point < len(sp_list):
            retain_sp_zone.append(sp_list[retain_point])
        else:
            retain_sp_zone.append(0.0)

    return retain_sp_zone


def set_point_scrap(rows, zone):
    """
    rows: CSV 전체 (첫 행은 헤더)
    zone: 1~8
    return: SP(zone) float 리스트
    """
    if not rows:
        return []

    header = rows[0]

    # SP1 위치 찾기
    data_pos_sp = None
    for index, name in enumerate(header):
        if name == 'SP1':
            data_pos_sp = index
            break

    if data_pos_sp is None:
        logger.error("헤더에 'SP1' 컬럼을 찾을 수 없습니다.")
        return []

    result = []
    for row in rows[1:]:  # 헤더는 건너뜀
        idx = data_pos_sp + zone - 1
        if len(row) > idx:
            result.append(_to_float(row[idx]))
        else:
            result.append(0.0)

    return result


def ptc_scrap(rows, zone):
    if not rows:
        return []

    header = rows[0]
    data_pos_ptc = None
    for index, name in enumerate(header):
        if name == 'PTC1':
            data_pos_ptc = index
            break

    if data_pos_ptc is None:
        logger.error("헤더에 'PTC1' 컬럼을 찾을 수 없습니다.")
        return []

    result = []
    for row in rows[1:]:
        idx = data_pos_ptc + zone - 1
        if len(row) > idx:
            result.append(_to_float(row[idx]))
        else:
            result.append(0.0)

    return result


def ctc_scrap(rows, zone):
    if not rows:
        return []

    header = rows[0]
    data_pos_ctc = None
    for index, name in enumerate(header):
        if name == 'CTC1':
            data_pos_ctc = index
            break

    if data_pos_ctc is None:
        logger.error("헤더에 'CTC1' 컬럼을 찾을 수 없습니다.")
        return []

    result = []
    for row in rows[1:]:
        idx = data_pos_ctc + zone - 1
        if len(row) > idx:
            result.append(_to_float(row[idx]))
        else:
            result.append(0.0)

    return result


def mv_scrap(rows, zone):
    if not rows:
        return []

    header = rows[0]
    data_pos_mv = None
    for index, name in enumerate(header):
        if name == 'MV1':
            data_pos_mv = index
            break

    if data_pos_mv is None:
        logger.error("헤더에 'MV1' 컬럼을 찾을 수 없습니다.")
        return []

    result = []
    for row in rows[1:]:
        idx = data_pos_mv + zone - 1
        if len(row) > idx:
            result.append(_to_float(row[idx]))
        else:
            result.append(0.0)

    return result



def p_calculation(rows, zone_count = 8):
    ptc = max_ptc_zones(rows, zone_count)
    sp = retain_sp_zones(rows, zone_count)
    ctc = retain_point_ctc_zones(rows, zone_count)
    rtn_ptc = retain_point_ptc_average(rows, zone_count)

    adjust_p1 = []
    for i in range(zone_count):
        delta = ptc[i] - sp[i]
        # logger.debug(f"ptc[{i}] - sp[{i}]: {delta}")
        if delta <= 1:
            adjust_p1.append(0)
        elif delta > 1:
            adjust_p1.append(int(delta))

    initial_p2 = [int(sp[i] - ctc[i] + 3) for i in range(zone_count)]
    adjust_p2 = [int(rtn_ptc[i] - sp[i]) for i in range(zone_count)]

    logger.debug(f"P1 adjustment values: {adjust_p1}")
    logger.debug(f"Initial P2 values: {initial_p2}")
    logger.debug(f"P2 adjustment values: {adjust_p2}")

    return adjust_p1, initial_p2, adjust_p2


def detect_heater_zones(headers: List[str]) -> int:
    return sum(1 for h in headers if h.strip().startswith("ZONE") and h.strip().endswith("(SP)"))


def is_all_zero(ary):
    return all(v==0 for v in ary)


def ary_sum(ary1, ary2, ary3):
    ary1_16 = ary1 + ary2
    ary2_16 = ary3
    result = [a+b for a,b in zip(ary1_16, ary2_16)]
    return result

def to_int16(value: int) -> int:
    return value - 65536 if value >= 32768 else value
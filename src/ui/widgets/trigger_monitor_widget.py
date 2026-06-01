# src/ui/widgets/trigger_monitor_widget.py
from dataclasses import dataclass, field
from typing import Any

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QGroupBox,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QFrame,
    QTabWidget,
)
from PyQt6.QtCore import QTimer, pyqtSignal

from src.config.settings import TUBE_SETTINGS
from src.utils.logger_config import setup_logger
from src.utils.temperature_logger import (
    init_plc_csv_logger,
    append_temperature_log,
    job_info_read,
    get_latest_temperature_logs,
)
from src.utils.data_processor_tuning import p_calculation, is_all_zero, ary_sum

logger = setup_logger('trigger_monitor')


@dataclass(frozen=True)
class TriggerAddress:
    mem_area: int
    word_addr: int
    bit_offset: int


@dataclass
class TubeMonitorState:
    tube_id: int
    param_trigger: TriggerAddress
    temp_trigger: TriggerAddress
    temp_normal: TriggerAddress
    temp_high: TriggerAddress
    trigger_count: int = 0
    prev_trigger_state: bool = False
    prev_temp_trigger_state: bool = False
    active_temp_area: str | None = None
    log_writer: Any = None
    log_file: Any = None
    log_file_path: str | None = None
    job_id: int | None = None
    latest_normal_log_path: Any = None
    latest_normal_log_rows: list | None = None
    latest_high_log_path: Any = None
    latest_high_log_rows: list | None = None
    prev_left_table_value: list[int] = field(default_factory=list)
    prev_right_table_value: list[int] = field(default_factory=list)
    new_left_table_value: list[int] = field(default_factory=list)
    new_right_table_value: list[int] = field(default_factory=list)
    left_table: QGroupBox | None = None
    right_table: QGroupBox | None = None
    new_left_table: QGroupBox | None = None
    new_right_table: QGroupBox | None = None
    status_label: QLabel | None = None
    trigger_count_label: QLabel | None = None
    trigger_indicator: QFrame | None = None
    temp_trigger_state: QLabel | None = None
    temp_indicator_normal: QFrame | None = None
    temp_indicator_high: QFrame | None = None


class TriggerMonitorWidget(QGroupBox):
    temperature_log_updated = pyqtSignal(list, list)

    PARAM_TABLE_KEYS = {
        "Prev Normal Temp Param": "prev_normal",
        "Prev High Temp Param": "prev_high",
        "New Normal Temp Param": "new_normal",
        "New High Temp Param": "new_high",
    }

    def __init__(self, plc_connector):
        super().__init__("트리거 모니터링")
        self.plc_connector = plc_connector
        self.tube_count = int(TUBE_SETTINGS.get('TUBE_COUNT', 4))
        self.zone_count = int(TUBE_SETTINGS.get('ZONE_COUNT', 8))
        self.tube_states = [self._create_tube_state(tube_id) for tube_id in range(1, self.tube_count + 1)]
        self.init_ui()

    def _create_tube_state(self, tube_id: int) -> TubeMonitorState:
        return TubeMonitorState(
            tube_id=tube_id,
            param_trigger=self._trigger_address(tube_id, 'PARAM_TRIGGER_BIT_OFFSET'),
            temp_trigger=self._trigger_address(tube_id, 'TEMP_TRIGGER_BIT_OFFSET'),
            temp_normal=self._trigger_address(tube_id, 'TEMP_NORMAL_BIT_OFFSET'),
            temp_high=self._trigger_address(tube_id, 'TEMP_HIGH_BIT_OFFSET'),
        )

    def _trigger_address(self, tube_id: int, offset_key: str) -> TriggerAddress:
        explicit_map = TUBE_SETTINGS.get('TRIGGER_ADDRESS_MAP', {})
        tube_map = explicit_map.get(tube_id) or explicit_map.get(str(tube_id)) or {}
        key_map = {
            'PARAM_TRIGGER_BIT_OFFSET': 'param',
            'TEMP_TRIGGER_BIT_OFFSET': 'temperature',
            'TEMP_NORMAL_BIT_OFFSET': 'normal',
            'TEMP_HIGH_BIT_OFFSET': 'high',
        }
        explicit_address = tube_map.get(key_map[offset_key])
        if explicit_address:
            return TriggerAddress(
                mem_area=explicit_address.get('mem_area', TUBE_SETTINGS['TRIGGER_MEMORY_AREA']),
                word_addr=explicit_address.get('word_addr', TUBE_SETTINGS['TRIGGER_WORD_ADDR_BASE']),
                bit_offset=explicit_address.get('bit_offset', TUBE_SETTINGS[offset_key]),
            )

        return TriggerAddress(
            mem_area=TUBE_SETTINGS['TRIGGER_MEMORY_AREA'],
            word_addr=TUBE_SETTINGS['TRIGGER_WORD_ADDR_BASE'] + (tube_id - 1) * TUBE_SETTINGS['TRIGGER_WORD_STRIDE'],
            bit_offset=TUBE_SETTINGS[offset_key],
        )

    def _param_addresses(self, tube_id: int, table_key: str):
        base = TUBE_SETTINGS['PARAM_ADDRESS_BASES'][table_key] + (tube_id - 1) * TUBE_SETTINGS['PARAM_ADDRESS_STRIDE']
        mem_area = TUBE_SETTINGS['PARAM_MEMORY_AREA']
        row_offsets = TUBE_SETTINGS['PARAM_ROW_OFFSETS'][table_key]
        zone_stride = TUBE_SETTINGS['PARAM_ZONE_STRIDE']
        return [
            [(base + row_offset + col * zone_stride, mem_area) for col in range(self.zone_count)]
            for row_offset in row_offsets
        ]

    def init_ui(self):
        main_layout = QVBoxLayout()

        self.status_container = QGroupBox("트리거 모니터링")
        status_layout = QVBoxLayout(self.status_container)
        for state in self.tube_states:
            status_layout.addLayout(self._create_status_row(state))

        self.tables_container = QTabWidget()
        self.new_tables_container = QTabWidget()

        for state in self.tube_states:
            prev_tab = QWidget()
            prev_layout = QHBoxLayout(prev_tab)
            state.left_table = self.create_table(state, "Prev Normal Temp Param")
            state.right_table = self.create_table(state, "Prev High Temp Param")
            prev_layout.addWidget(state.left_table)
            prev_layout.addWidget(state.right_table)
            self.tables_container.addTab(prev_tab, f"Tube {state.tube_id} Prev")

            new_tab = QWidget()
            new_layout = QHBoxLayout(new_tab)
            state.new_left_table = self.create_table(state, "New Normal Temp Param")
            state.new_right_table = self.create_table(state, "New High Temp Param")
            new_layout.addWidget(state.new_left_table)
            new_layout.addWidget(state.new_right_table)
            self.new_tables_container.addTab(new_tab, f"Tube {state.tube_id} New")

        main_layout.addWidget(self.tables_container)
        main_layout.addWidget(self.new_tables_container)
        self.setLayout(main_layout)

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_triggers)

    def _create_status_row(self, state: TubeMonitorState):
        row = QHBoxLayout()

        state.status_label = QLabel(f"Tube {state.tube_id} Parameter read trigger")
        state.trigger_count_label = QLabel("트리거 카운트: 0")
        state.trigger_indicator = self._create_indicator()

        temp_label = QLabel("Temperature read trigger")
        state.temp_trigger_state = QLabel("OFF")
        state.temp_indicator_normal = self._create_indicator()
        state.temp_indicator_high = self._create_indicator()

        row.addWidget(state.status_label)
        row.addWidget(state.trigger_count_label)
        row.addWidget(state.trigger_indicator)
        row.addSpacing(20)
        row.addWidget(temp_label)
        row.addWidget(state.temp_trigger_state)
        row.addWidget(QLabel("Normal"))
        row.addWidget(state.temp_indicator_normal)
        row.addWidget(QLabel("High"))
        row.addWidget(state.temp_indicator_high)
        row.addStretch()
        return row

    def _create_indicator(self):
        indicator = QFrame()
        indicator.setFixedSize(15, 15)
        self._set_indicator(indicator, False)
        return indicator

    @staticmethod
    def _set_indicator(indicator, is_on: bool):
        indicator.setStyleSheet(
            "background-color: green; border-radius: 7px;" if is_on else "background-color: red; border-radius: 7px;"
        )

    def create_table(self, state: TubeMonitorState, title, rows=2, cols=None):
        cols = cols or self.zone_count
        group = QGroupBox(f"Tube {state.tube_id} {title}")
        main_layout = QHBoxLayout()
        table_layout = QVBoxLayout()

        table = QTableWidget(rows, cols)
        table.setObjectName("dataTable")
        table.setHorizontalHeaderLabels([f'Z{i}' for i in range(1, cols + 1)])
        table.setVerticalHeaderLabels(['P1', 'P2'])

        for row in range(rows):
            for col in range(cols):
                table.setItem(row, col, QTableWidgetItem("0"))

        table_layout.addWidget(table)

        button_layout = QVBoxLayout()
        restore_button = QPushButton("Restore")
        restore_button.setObjectName(f"tube_{state.tube_id}_{title}_restore_button")
        restore_button.clicked.connect(lambda _, s=state, t=table, table_title=title: self.restore_table(s, t, table_title))
        if title in ("New Normal Temp Param", "New High Temp Param"):
            self.restore_table(state, table, title)

        button_layout.addStretch()
        button_layout.addWidget(restore_button)
        button_layout.addStretch()

        main_layout.addLayout(table_layout)
        main_layout.addLayout(button_layout)
        group.setLayout(main_layout)

        return group

    def restore_table(self, state: TubeMonitorState, table, title):
        rows = table.rowCount()
        cols = table.columnCount()

        ary = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = table.item(r, c)
                text = item.text() if item else "0"
                try:
                    value = int(text)
                except ValueError:
                    logger.warning(f"Tube {state.tube_id} 테이블 값이 정수가 아님: row={r}, col={c}, text='{text}', 0으로 처리")
                    value = 0
                row_data.append(value)
            ary.append(row_data)

        table_key = self.PARAM_TABLE_KEYS.get(title)
        if not table_key:
            logger.error(f"알 수 없는 테이블 제목: {title}")
            return

        addr_table = self._param_addresses(state.tube_id, table_key)
        if title == "Prev Normal Temp Param":
            state.prev_left_table_value = [value for row in ary for value in row]
        elif title == "Prev High Temp Param":
            state.prev_right_table_value = [value for row in ary for value in row]
        elif title == "New Normal Temp Param":
            state.new_left_table_value = [value for row in ary for value in row]
        elif title == "New High Temp Param":
            state.new_right_table_value = [value for row in ary for value in row]

        if len(ary) != len(addr_table) or any(len(ary[r]) != len(addr_table[r]) for r in range(len(ary))):
            logger.error(
                f"Tube {state.tube_id} 테이블 크기 불일치: 값={len(ary)}x{len(ary[0]) if ary else 0}, "
                f"주소={len(addr_table)}x{len(addr_table[0]) if addr_table else 0}"
            )
            return

        try:
            for r in range(len(addr_table)):
                for c in range(len(addr_table[r])):
                    word_addr, mem_area = addr_table[r][c]
                    value = ary[r][c]
                    logger.debug(
                        f"PLC write -> tube={state.tube_id}, title={title}, r={r}, c={c}, "
                        f"mem_area=0x{mem_area:X}, word_addr={word_addr}, value={value}"
                    )
                    self.plc_connector.write_word(
                        mem_area=mem_area,
                        word_addr=word_addr,
                        word_value=value,
                    )

            logger.info(f"Tube {state.tube_id} {title} 테이블 Restore 완료")

        except Exception as e:
            logger.exception(f"Tube {state.tube_id} {title} Restore 중 예외 발생: {e}")

    def update_plc_data(self, state: TubeMonitorState):
        try:
            left_values = self._read_param_values(state.tube_id, 'prev_normal')
            right_values = self._read_param_values(state.tube_id, 'prev_high')

            self.update_table_values(state.left_table, left_values)
            state.prev_left_table_value = left_values
            logger.debug(f"Tube {state.tube_id} left_values: {state.prev_left_table_value}")

            self.update_table_values(state.right_table, right_values)
            state.prev_right_table_value = right_values
            logger.debug(f"Tube {state.tube_id} right_values: {state.prev_right_table_value}")

        except Exception as e:
            logger.error(f"Tube {state.tube_id} PLC 데이터 읽기 실패: {str(e)}")

    def _read_param_values(self, tube_id: int, table_key: str):
        values = []
        for row in self._param_addresses(tube_id, table_key):
            for addr, mem_area in row:
                value = self.plc_connector.read_word(
                    word_addr=addr,
                    mem_area=mem_area,
                    word_count=1
                )
                if isinstance(value, (list, tuple)):
                    value = value[0] if value else 0
                values.append(0 if value is None else value - 65536 if value >= 32768 else value)
        return values

    def update_table_values(self, group_box, data):
        if not data or not group_box:
            return None

        table = group_box.findChild(QTableWidget)
        if not table:
            return None

        rows = [data[i:i + self.zone_count] for i in range(0, len(data), self.zone_count)]
        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        return table

    def start_monitoring(self):
        self.monitor_timer.start(1000)
        logger.info(f"{self.tube_count}개 튜브 트리거 모니터링 시작")

    def stop_monitoring(self):
        self.monitor_timer.stop()
        for state in self.tube_states:
            self._close_temperature_log(state)
        logger.info("트리거 모니터링 중지")

    def check_triggers(self):
        for state in self.tube_states:
            self.check_trigger(state)
            self.check_trigger_temperature(state)

    def _read_trigger(self, address: TriggerAddress):
        return self.plc_connector.read_trigger_bit(
            mem_area=address.mem_area,
            word_addr=address.word_addr,
            bit_offset=address.bit_offset,
        )

    def check_trigger(self, state: TubeMonitorState):
        trigger_state = self._read_trigger(state.param_trigger)

        if trigger_state is None:
            state.status_label.setText(f"Tube {state.tube_id} 트리거 상태: 통신 오류")
            state.status_label.setStyleSheet("color: red;")
            return

        if trigger_state and not state.prev_trigger_state:
            self.trigger_detected(state)
        elif not trigger_state and state.prev_trigger_state:
            self.trigger_released(state)

        state.prev_trigger_state = trigger_state
        self._set_indicator(state.trigger_indicator, trigger_state)
        state.status_label.setText(f"Tube {state.tube_id} Parameter read trigger")
        state.status_label.setStyleSheet("")

    def check_trigger_temperature(self, state: TubeMonitorState):
        trigger_state = self._read_trigger(state.temp_trigger)
        temp_area_normal = self._read_trigger(state.temp_normal)
        temp_area_high = self._read_trigger(state.temp_high)

        if trigger_state is None:
            state.temp_trigger_state.setText("오류")
            state.temp_trigger_state.setStyleSheet("color: red;")
            return

        requested_area = None
        if trigger_state and temp_area_normal:
            requested_area = "normal"
        elif trigger_state and temp_area_high:
            requested_area = "high"

        if requested_area:
            if (not state.prev_temp_trigger_state) or state.active_temp_area != requested_area:
                self._close_temperature_log(state)
                job_id = self._read_job_id_for_tube(state.tube_id)
                state.job_id = job_id
                state.log_file, state.log_writer, state.log_file_path = init_plc_csv_logger(
                    requested_area,
                    tube_id=state.tube_id,
                    job_id=job_id,
                    plc_connector=self.plc_connector,
                )
                state.active_temp_area = requested_area

            state.prev_temp_trigger_state = True
            append_temperature_log(
                state.log_file,
                state.log_writer,
                tube_id=state.tube_id,
                job_id=state.job_id,
                plc_connector=self.plc_connector,
            )
            state.temp_trigger_state.setText(f"ON ({requested_area})")
            state.temp_trigger_state.setStyleSheet("color: green;")
            self._set_indicator(state.temp_indicator_normal, requested_area == "normal")
            self._set_indicator(state.temp_indicator_high, requested_area == "high")
            return

        if state.prev_temp_trigger_state:
            self._close_temperature_log(state)

        state.prev_temp_trigger_state = False
        state.active_temp_area = None
        state.temp_trigger_state.setText("OFF")
        state.temp_trigger_state.setStyleSheet("color: red;")
        self._set_indicator(state.temp_indicator_normal, False)
        self._set_indicator(state.temp_indicator_high, False)

    def _close_temperature_log(self, state: TubeMonitorState):
        if state.log_file:
            try:
                state.log_file.close()
                logger.info(f"Tube {state.tube_id} Temperature CSV Log 종료: {state.log_file_path}")
            except Exception as e:
                logger.exception(f"Tube {state.tube_id} 로그 파일 종료 중 예외 발생: {e}")
            finally:
                state.log_file = None
                state.log_writer = None
                state.log_file_path = None

    def trigger_detected(self, state: TubeMonitorState):
        state.trigger_count += 1
        state.trigger_count_label.setText(f"트리거 카운트: {state.trigger_count}")
        logger.info(f"Tube {state.tube_id} 트리거 감지 (카운트: {state.trigger_count})")
        self.handle_data_read(state)

    def trigger_released(self, state: TubeMonitorState):
        job_id = self._read_job_id_for_tube(state.tube_id)
        if job_id is None:
            logger.warning(f"Tube {state.tube_id} trigger_released: job_id가 None 입니다.")
            return

        state.job_id = job_id
        logger.info(f"trigger_released: tube_id={state.tube_id}, job_id={state.job_id}")

        logs = get_latest_temperature_logs(state.tube_id, state.job_id)
        normal = logs.get("normal", {})
        high = logs.get("high", {})

        state.latest_normal_log_path = normal.get("path")
        state.latest_normal_log_rows = normal.get("rows")
        state.latest_high_log_path = high.get("path")
        state.latest_high_log_rows = high.get("rows")

        if state.latest_normal_log_path:
            logger.info(f"Tube {state.tube_id} 최신 normal 온도 로그: {state.latest_normal_log_path}")
            normal_p1, normal_init_p2, normal_p2 = p_calculation(state.latest_normal_log_rows, self.zone_count)
            if is_all_zero(state.prev_left_table_value):
                state.new_left_table_value = normal_p1 + normal_init_p2
            else:
                state.new_left_table_value = ary_sum(normal_p1, normal_p2, state.prev_left_table_value)
            table = self.update_table_values(state.new_left_table, state.new_left_table_value)
            self.restore_table(state, table, "New Normal Temp Param")
        else:
            logger.info(f"Tube {state.tube_id} 해당 tube/job에 대한 normal 온도 로그 없음")

        if state.latest_high_log_path:
            logger.info(f"Tube {state.tube_id} 최신 high 온도 로그: {state.latest_high_log_path}")
            high_p1, high_init_p2, high_p2 = p_calculation(state.latest_high_log_rows, self.zone_count)
            if is_all_zero(state.prev_right_table_value):
                state.new_right_table_value = high_p1 + high_init_p2
            else:
                state.new_right_table_value = ary_sum(high_p1, high_p2, state.prev_right_table_value)
            table = self.update_table_values(state.new_right_table, state.new_right_table_value)
            self.restore_table(state, table, "New High Temp Param")
        else:
            logger.info(f"Tube {state.tube_id} 해당 tube/job에 대한 high 온도 로그 없음")

        if state.latest_normal_log_path and state.latest_high_log_path:
            self.temperature_log_updated.emit(
                state.latest_normal_log_rows or [],
                state.latest_high_log_rows or []
            )

    def _read_job_id_for_tube(self, tube_id: int):
        try:
            _, job_id = job_info_read(tube_id=tube_id, plc_connector=self.plc_connector)
            return job_id
        except Exception as e:
            logger.exception(f"Tube {tube_id} job_info_read() 호출 중 예외 발생: {e}")
            return None

    def handle_data_read(self, state: TubeMonitorState):
        try:
            self.update_plc_data(state)
        except Exception as e:
            logger.error(f"Tube {state.tube_id} 데이터 읽기 처리 중 오류 발생: {str(e)}")

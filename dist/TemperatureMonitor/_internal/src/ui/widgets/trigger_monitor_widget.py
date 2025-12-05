# src/ui/widgets/trigger_monitor_widget.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QFrame
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from src.utils.logger_config import setup_logger
from src.utils.temperature_logger import init_plc_csv_logger, append_temperature_log, job_info_read, get_latest_temperature_logs
from src.utils.data_processor_tuning import p_calculation, is_all_zero, ary_sum, to_int16

logger = setup_logger('trigger_monitor')

class TriggerMonitorWidget(QGroupBox):
    temperature_log_updated = pyqtSignal(list, list)

    def __init__(self, plc_connector):
        super().__init__("트리거 모니터링")
        self.plc_connector = plc_connector
        self.prev_trigger_state = False
        self.prev_temp_trigger_state = False
        self.prev_norm_param = None
        self.prev_high_param = None
        self.log_writer = None
        self.log_file = None
        self.log_file_path = None
        self.tube_id = None
        self.job_id = None
        self.latest_normal_log_path = None
        self.latest_normal_log_rows = None
        self.latest_high_log_path = None
        self.latest_high_log_rows = None
        self.prev_left_table_value = None
        self.prev_right_table_value = None
        self.normal_p1 = None
        self.normal_p2 = None
        self.normal_init_p2 = None
        self.high_p1 = None
        self.high_p2 = None
        self.high_init_p2 = None
        self.new_left_table_value = None
        self.new_right_table_value = None

        # PLC 주소 매핑 정의
        self.left_table_addresses = [
            # [(행0열0 주소, 메모리영역), (행0열1 주소, 메모리영역), ...]
            [(840, 0xA0), (845, 0xA0), (850, 0xA0), (855, 0xA0), (860, 0xA0), (865, 0xA0), (870, 0xA0), (875, 0xA0)],
            [(841, 0xA0), (846, 0xA0), (851, 0xA0), (856, 0xA0), (861, 0xA0), (866, 0xA0), (871, 0xA0), (876, 0xA0)]
        ]

        self.right_table_addresses = [
            # [(행0열0 주소, 메모리영역), (행0열1 주소, 메모리영역), ...]
            [(842, 0xA0), (847, 0xA0), (852, 0xA0), (857, 0xA0), (862, 0xA0), (867, 0xA0), (872, 0xA0), (877, 0xA0)],
            [(843, 0xA0), (848, 0xA0), (853, 0xA0), (858, 0xA0), (863, 0xA0), (868, 0xA0), (873, 0xA0), (878, 0xA0)]
        ]

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 상단 상태 표시 영역을 별도의 GroupBox로 생성
        self.status_container = QGroupBox("트리거 모니터링")
        status_layout = QVBoxLayout(self.status_container)

        # --- Parameter Trigger Row ---
        param_row = QHBoxLayout()

        self.status_label = QLabel("Parameter read trigger")
        self.trigger_count_label = QLabel("트리거 카운트: 0")

        self.trigger_indicator = QFrame()
        self.trigger_indicator.setFixedSize(15, 15)
        self.trigger_indicator.setStyleSheet(
            "background-color: red; border-radius: 7px;"
        )

        param_row.addWidget(self.status_label)
        param_row.addWidget(self.trigger_count_label)
        param_row.addWidget(self.trigger_indicator)
        param_row.addStretch()

        # --- Temperature Trigger Row ---
        temp_row = QHBoxLayout()

        self.temp_trigger_label = QLabel("Temperature read trigger")
        self.temp_trigger_state = QLabel("OFF")

        self.temp_indicator_normal = QFrame()
        self.temp_indicator_normal.setFixedSize(15, 15)
        self.temp_indicator_normal.setStyleSheet(
            "background-color: red; border-radius: 7px;"
        )
        self.temp_indicator_high = QFrame()
        self.temp_indicator_high.setFixedSize(15, 15)
        self.temp_indicator_high.setStyleSheet(
            "background-color: red; border-radius: 7px;"
        )

        temp_row.addWidget(self.temp_trigger_label)
        temp_row.addWidget(self.temp_trigger_state)
        temp_row.addWidget(self.temp_indicator_normal)
        temp_row.addWidget(self.temp_indicator_high)
        temp_row.addStretch()

        # 두 줄을 status_container에 삽입
        status_layout.addLayout(param_row)
        status_layout.addLayout(temp_row)

        # 테이블 컨테이너1 생성
        self.tables_container = QWidget()
        tables_layout = QHBoxLayout(self.tables_container)

        # 테이블 생성
        self.left_table = self.create_table("Prev Normal Temp Param")
        self.right_table = self.create_table("Prev High Temp Param")

        tables_layout.addWidget(self.left_table)
        tables_layout.addWidget(self.right_table)

        # 테이블 컨테이너2 생성
        self.new_tables_container = QWidget()
        new_tables_layout = QHBoxLayout(self.new_tables_container)

        # 테이블 생성
        self.new_left_table = self.create_table("New Normal Temp Param")
        self.new_right_table = self.create_table("New High Temp Param")

        new_tables_layout.addWidget(self.new_left_table)
        new_tables_layout.addWidget(self.new_right_table)

        # 메인 레이아웃 설정
        main_layout.addWidget(self.tables_container)
        main_layout.addWidget(self.new_tables_container)
        self.setLayout(main_layout)

        # 모니터링 타이머 설정
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_trigger)
        self.monitor_timer.timeout.connect(self.check_trigger_temperature)
        self.trigger_count = 0

    def create_table(self, title, rows=2, cols=8):
        group = QGroupBox(title)

        # 바깥쪽은 가로 레이아웃: [테이블][Restore 버튼]
        main_layout = QHBoxLayout()

        # 테이블 쪽은 세로 레이아웃 (필요하면 라벨 등을 추가할 수 있음)
        table_layout = QVBoxLayout()

        table = QTableWidget(rows, cols)
        table.setObjectName("dataTable")

        # 열 헤더 설정
        horizontal_headers = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8']
        table.setHorizontalHeaderLabels(horizontal_headers)

        # 행 헤더 설정
        vertical_headers = ['P1', 'P2']
        table.setVerticalHeaderLabels(vertical_headers)

        # 기본 셀 값 설정
        for row in range(rows):
            for col in range(cols):
                table.setItem(row, col, QTableWidgetItem("0"))

        table_layout.addWidget(table)

        # 오른쪽 Restore 버튼
        button_layout = QVBoxLayout()
        restore_button = QPushButton("Restore")
        # 필요하면 objectName으로 어떤 테이블인지 구분
        restore_button.setObjectName(f"{title}_restore_button")

        # 버튼 클릭 시 이 테이블 초기화하는 슬롯 연결 (예시)
        restore_button.clicked.connect(lambda _, t=table: self.restore_table(t,title))

        # 버튼을 세로 중앙 정렬하고 싶으면 위아래로 stretch
        button_layout.addStretch()
        button_layout.addWidget(restore_button)
        button_layout.addStretch()

        # 전체 레이아웃 구성
        main_layout.addLayout(table_layout)
        main_layout.addLayout(button_layout)
        group.setLayout(main_layout)

        return group

    def restore_table(self, table, title):
        # 1) 테이블 → 2차원 배열로 추출
        rows = table.rowCount()
        cols = table.columnCount()

        ary = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = table.item(r, c)
                text = item.text() if item else "0"
                try:
                    value = int(text)  # 안전하게 int 변환
                except ValueError:
                    logger.warning(f"테이블 값이 정수가 아님: row={r}, col={c}, text='{text}', 0으로 처리")
                    value = 0
                row_data.append(value)
            ary.append(row_data)

        logger.info(f"restore_table - title={title}, ary={ary}")

        # 2) 어떤 주소 테이블을 쓸지 결정
        if title == "Prev Normal Temp Param":
            self.prev_norm_param = ary
            addr_table = self.left_table_addresses
        elif title == "New Normal Temp Param":
            self.new_norm_param = ary
            addr_table = self.left_table_addresses
        elif title == "Prev High Temp Param":
            self.prev_high_param = ary
            addr_table = self.right_table_addresses
        elif title == "New High Temp Param":
            self.new_high_param = ary
            addr_table = self.right_table_addresses
        else:
            logger.error(f"알 수 없는 테이블 제목: {title}")
            return

        # 3) 주소/값 길이 체크 (예방 차원)
        if len(ary) != len(addr_table) or any(len(ary[r]) != len(addr_table[r]) for r in range(len(ary))):
            logger.error(
                f"테이블 크기 불일치: 값={len(ary)}x{len(ary[0]) if ary else 0}, "
                f"주소={len(addr_table)}x{len(addr_table[0]) if addr_table else 0}"
            )
            return

        # 4) 실제 PLC write 수행
        try:
            for r in range(len(addr_table)):
                for c in range(len(addr_table[r])):
                    word_addr, mem_area = addr_table[r][c]
                    value = ary[r][c]

                    logger.debug(
                        f"PLC write -> title={title}, r={r}, c={c}, "
                        f"mem_area=0x{mem_area:X}, word_addr={word_addr}, value={value}"
                    )

                    self.plc_connector.write_word(
                        mem_area=mem_area,
                        word_addr=word_addr,
                        word_value=value,
                    )

            logger.info(f"{title} 테이블 Restore 완료")

        except Exception as e:
            logger.exception(f"{title} Restore 중 예외 발생: {e}")

    def update_plc_data(self):
        """PLC에서 데이터 읽어와서 테이블 업데이트"""
        try:
            # 왼쪽 테이블 데이터 읽기
            left_values = []
            for row in self.left_table_addresses:
                row_values = []
                for addr, mem_area in row:
                    value = self.plc_connector.read_word(
                        word_addr=addr,
                        mem_area=mem_area,
                        word_count=1
                    )
                    if value is None:
                        row_values.append(0)
                    else:
                        # ★ signed INT16 변환 적용
                        row_values.append(
                            value - 65536 if value >= 32768 else value
                        )
                left_values.extend(row_values)

            # 오른쪽 테이블 데이터 읽기
            right_values = []
            for row in self.right_table_addresses:
                row_values = []
                for addr, mem_area in row:
                    value = self.plc_connector.read_word(
                        word_addr=addr,
                        mem_area=mem_area,
                        word_count=1
                    )
                    if value is None:
                        row_values.append(0)
                    else:
                        # ★ signed INT16 변환 적용
                        row_values.append(
                            value - 65536 if value >= 32768 else value
                        )
                right_values.extend(row_values)

            # 테이블 업데이트
            self.update_table_values(self.left_table, left_values)
            self.prev_left_table_value = left_values
            logger.debug(f"left_values: {self.prev_left_table_value}")

            self.update_table_values(self.right_table, right_values)
            self.prev_right_table_value = right_values
            logger.debug(f"right_values: {self.prev_right_table_value}")

        except Exception as e:
            logger.error(f"PLC 데이터 읽기 실패: {str(e)}")


    def update_table_values(self, group_box, data):
        """테이블 값 업데이트"""
        if not data:
            return

        table = group_box.findChild(QTableWidget)
        if not table:
            return

        # 1차원 리스트를 2차원으로 변환 (8열 기준)
        rows = [data[i:i + 8] for i in range(0, len(data), 8)]

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        return table

    def start_monitoring(self):
        """트리거 모니터링 시작"""
        self.monitor_timer.start(1000)  # 1000ms 간격으로 체크
        logger.info("트리거 모니터링 시작")
        
    def stop_monitoring(self):
        """트리거 모니터링 중지"""
        self.monitor_timer.stop()
        logger.info("트리거 모니터링 중지")
        
    def check_trigger(self):
        """트리거 비트 상태 확인"""
        trigger_state = self.plc_connector.read_trigger_bit(mem_area=0xAF, word_addr=1, bit_offset=1)
        
        if trigger_state is None:
            self.status_label.setText("트리거 상태: 통신 오류")
            self.status_label.setStyleSheet("color: red;")
            return
            
        # Rising edge 감지 (0 → 1)
        if trigger_state and not self.prev_trigger_state:
            self.trigger_detected()
        elif not trigger_state and self.prev_trigger_state:
            self.trigger_released()
            
        self.prev_trigger_state = trigger_state
        self.trigger_indicator.setStyleSheet(
            "background-color: green; border-radius: 7px;" if trigger_state else "background-color: red; border-radius: 7px;"
        )

    def check_trigger_temperature(self):
        trigger_state = self.plc_connector.read_trigger_bit(mem_area=0xAF, word_addr=1, bit_offset=2)
        temp_area_normal = self.plc_connector.read_trigger_bit(mem_area=0xAF, word_addr=1, bit_offset=3)
        temp_area_high = self.plc_connector.read_trigger_bit(mem_area=0xAF, word_addr=1, bit_offset=4)

        if trigger_state is None:
            self.temp_trigger_state.setText("오류")
            self.temp_trigger_state.setStyleSheet("color: red;")
            return

        if trigger_state and temp_area_normal:
            if not self.prev_temp_trigger_state:
                self.log_file, self.log_writer, self.log_file_path = init_plc_csv_logger("normal")
            self.prev_temp_trigger_state = True
            append_temperature_log(self.log_file, self.log_writer)
            self.temp_trigger_state.setText("ON")
            self.temp_trigger_state.setStyleSheet("color: green;")
            self.temp_indicator_normal.setStyleSheet("background-color: green; border-radius: 7px;")

        elif trigger_state and temp_area_high:
            if not self.prev_temp_trigger_state:
                self.log_file, self.log_writer, self.log_file_path = init_plc_csv_logger("high")
            self.prev_temp_trigger_state = True
            append_temperature_log(self.log_file, self.log_writer)
            self.temp_trigger_state.setText("ON")
            self.temp_trigger_state.setStyleSheet("color: green;")
            self.temp_indicator_high.setStyleSheet("background-color: green; border-radius: 7px;")

        else:
            # 트리거가 1 -> 0 으로 떨어지는 순간에만 파일 닫기
            if self.prev_temp_trigger_state and self.log_file:
                try:
                    self.log_file.close()
                    logger.info(f"Temperature CSV Log 종료: {self.log_file_path}")
                except Exception as e:
                    logger.exception(f"로그 파일 종료 중 예외 발생: {e}")
                finally:
                    self.log_file = None
                    self.log_writer = None
                    self.log_file_path = None

            self.prev_temp_trigger_state = False
            self.temp_trigger_state.setText("OFF")
            self.temp_trigger_state.setStyleSheet("color: red;")
            self.temp_indicator_normal.setStyleSheet("background-color: red; border-radius: 7px;")
            self.temp_indicator_high.setStyleSheet("background-color: red; border-radius: 7px;")

    def trigger_detected(self):
        """트리거 감지시 처리"""
        self.trigger_count += 1
        self.trigger_count_label.setText(f"트리거 카운트: {self.trigger_count}")
        logger.info(f"트리거 감지 (카운트: {self.trigger_count})")
        
        # 데이터 읽기 처리
        self.handle_data_read()

    def trigger_released(self):
        try:
            self.tube_id, self.job_id = job_info_read()
        except Exception as e:
            logger.exception(f"job_info_read() 호출 중 예외 발생: {e}")
            return

        if self.tube_id is None or self.job_id is None:
            logger.warning("trigger_released: tube_id 또는 job_id가 None 입니다.")
            return

        logger.info(f"trigger_released: tube_id={self.tube_id}, job_id={self.job_id}")

        logs = get_latest_temperature_logs(self.tube_id, self.job_id)

        normal = logs.get("normal", {})
        high = logs.get("high", {})

        self.latest_normal_log_path = normal.get("path")
        self.latest_normal_log_rows = normal.get("rows")

        self.latest_high_log_path = high.get("path")
        self.latest_high_log_rows = high.get("rows")

        if self.latest_normal_log_path:
            logger.info(f"최신 normal 온도 로그: {self.latest_normal_log_path}")
            self.normal_p1, self.normal_init_p2, self.normal_p2 = p_calculation(self.latest_normal_log_rows)
            if is_all_zero(self.prev_left_table_value):
                self.new_left_table_value = self.normal_p1 + self.normal_init_p2
                logger.info(f"new_left_table_value: {self.new_left_table_value}")
                self.update_table_values(self.new_left_table, self.new_left_table_value)
            else:
                self.new_left_table_value = ary_sum(self.normal_p1, self.normal_p2, self.prev_left_table_value)
                logger.info(f"new_left_table_value: {self.new_left_table_value}")
                self.update_table_values(self.new_left_table, self.new_left_table_value)
        else:
            logger.info("해당 tube/job에 대한 normal 온도 로그 없음")

        if self.latest_high_log_path:
            logger.info(f"최신 high 온도 로그: {self.latest_high_log_path}")
            self.high_p1, self.high_init_p2, self.high_p2 = p_calculation(self.latest_high_log_rows)
            if is_all_zero(self.prev_right_table_value):
                self.new_right_table_value = self.high_p1 + self.high_init_p2
                logger.info(f"new_right_table_value: {self.new_right_table_value}")
                self.update_table_values(self.new_right_table, self.new_right_table_value)
            else:
                self.new_right_table_value = ary_sum(self.high_p1, self.high_p2, self.prev_right_table_value)
                logger.info(f"new_right_table_value: {self.new_right_table_value}")
                self.update_table_values(self.new_right_table, self.new_right_table_value)
        else:
            logger.info("해당 tube/job에 대한 high 온도 로그 없음")

        if self.latest_normal_log_path and self.latest_high_log_path:
            self.temperature_log_updated.emit(
                self.latest_normal_log_rows or [],
                self.latest_high_log_rows or []
            )
        else:
            logger.info("해당 tube/job에 대한 high 온도 로그 없음")

    def handle_data_read(self):
        """트리거 감지시 데이터 읽기 처리"""
        try:
            # PLC 데이터 업데이트
            self.update_plc_data()

        except Exception as e:
            logger.error(f"데이터 읽기 처리 중 오류 발생: {str(e)}")
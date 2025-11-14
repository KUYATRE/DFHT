from src.communication.fins_comm import FinsUDPClient
from src.utils.logger_config import setup_logger

logger = setup_logger('plc_connector')

class PLCConnector:
    def __init__(self):
        self.connected = False
        self.ip_address = None
        self.fins_client = None
        self.log_file_path = None  # 로그 파일 경로 추가
        logger.info("PLC Connector 초기화")
        self.trigger_handler = None
        self.prev_trigger_state = False
        
    def connect(self, ip_address, plc_port=9600, plc_node=1, pc_node=3):
        try:
            logger.info(f"PLC 연결 시도: IP={ip_address}, Port={plc_port}, PLC Node={plc_node}, PC Node={pc_node}")
            # logger.info(f"로그 파일 경로: {log_file_path}")
            
            self.fins_client = FinsUDPClient(
                plc_ip=ip_address,
                plc_port=plc_port,
                plc_node=plc_node,
                pc_node=pc_node
            )
            
            # 로그 파일 경로 저장
            # self.log_file_path = log_file_path
            
            test_result = self.read_heartbeat(mem_area=0xAF, word_addr=0, bit_offset=0)
            if test_result is not None:
                self.ip_address = ip_address
                self.connected = True
                logger.info(f"PLC 연결 성공: {ip_address}")
                return True
            
            logger.warning(f"PLC 연결 실패: Heartbeat 신호 없음 (IP: {ip_address})")
            return False
            
        except Exception as e:
            logger.exception(f"PLC 연결 중 오류 발생: {str(e)}")
            return False

    def disconnect(self):
        if self.fins_client:
            self.fins_client.close()
            self.fins_client = None
        self.connected = False
        self.ip_address = None
        logger.info("PLC 연결 해제")

    def is_connected(self):
        return self.connected

    def read_heartbeat(self, mem_area=0xAF, word_addr=0, bit_offset=0):
        """Heartbeat 신호 읽기"""
        try:
            return self.fins_client.read_word_bit(word_addr=word_addr, mem_area=mem_area, bit_offset=bit_offset)
        except Exception as e:
            logger.error(f"Heartbeat 읽기 실패: {str(e)}")
            return None
            
    def read_trigger_bit(self, mem_area=0xAF, word_addr=1, bit_offset=1):
        """Trigger 비트 읽기"""
        try:
            return self.fins_client.read_word_bit(mem_area, word_addr, bit_offset)
        except Exception as e:
            logger.error(f"Trigger 비트 읽기 실패: {str(e)}")
            return None
            
    def write_response_bit(self, mem_area=0xAF, word_addr=2, bit_offset=1, turn_on=True):
        """응답 비트 쓰기"""
        try:
            return self.fins_client.write_word_bit(mem_area, word_addr, bit_offset, turn_on)
        except Exception as e:
            logger.error(f"응답 비트 쓰기 실패: {str(e)}")
            return False

    def read_word(self, mem_area, word_addr, word_count):
        try:
            return self.fins_client.read_word(word_addr, mem_area, word_count)
        except Exception as e:
            logger.error(f"PLC word data 읽기 실패: {str(e)}")

    def write_word(self, mem_area, word_addr, word_value):
        try:
            return self.fins_client.write_word(mem_area, word_addr, word_value)
        except Exception as e:
            logger.error(f"PLC write data 실패: {str(e)}")

    def get_latest_log_file(self):
        """지정된 경로에서 가장 최신 로그 파일을 찾아서 내용을 반환"""
        try:
            import os
            import glob
            
            # 지정된 경로의 모든 파일 목록 가져오기
            log_files = glob.glob(os.path.join(self.log_file_path, '*.*'))
            
            if not log_files:
                logger.warning(f"로그 파일을 찾을 수 없음: {self.log_file_path}")
                return None
                
            # 가장 최신 파일 찾기
            latest_file = max(log_files, key=os.path.getctime)
            
            # 파일 내용 읽기
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            logger.info(f"최신 로그 파일 읽기 성공: {latest_file}")
            return content
            
        except Exception as e:
            logger.error(f"로그 파일 읽기 실패: {str(e)}")
            return None
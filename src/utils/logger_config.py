import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

def setup_logger(name, log_dir='logs'):
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 로그 디렉토리가 없으면 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 날짜별 로그 파일 설정
    daily_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, f'{name}.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    daily_handler.setLevel(logging.INFO)
    
    # 크기 기반 상세 로그 파일 설정
    debug_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, f'{name}_debug.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    
    # 콘솔 출력 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s [%(name)s:%(filename)s:%(lineno)d] - %(message)s'
    )
    
    debug_formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s [%(name)s:%(filename)s:%(lineno)d]\n'
        'Thread: %(threadName)s\n'
        'Message: %(message)s\n'
    )
    
    daily_handler.setFormatter(formatter)
    debug_handler.setFormatter(debug_formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    if not logger.handlers:
        logger.addHandler(daily_handler)
        logger.addHandler(debug_handler)
        logger.addHandler(console_handler)
    
    return logger
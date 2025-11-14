# src/utils/mpl_config.py
from matplotlib import rcParams

def setup_korean_font():
    # 윈도우 기본 한글 폰트
    rcParams['font.family'] = 'Malgun Gothic'

    # 마이너스 부호가 깨지는 것 방지
    rcParams['axes.unicode_minus'] = False

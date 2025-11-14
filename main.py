import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import PLCMonitoringApp
from src.config.mpl_config import setup_korean_font

def main():
    app = QApplication(sys.argv)
    
    # 스타일시트 적용 (UTF-8 인코딩 지정)
    with open('src/ui/styles/style.css', 'r', encoding='utf-8') as f:
        app.setStyleSheet(f.read())
    
    window = PLCMonitoringApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    setup_korean_font()
    main()
# main.py
import sys
from ui import MainWindow
from PyQt5.QtWidgets import QApplication
import os

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 加载样式表
    try:
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"样式加载失败: {e}")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
"""Launch directly into the rehabilitation training selection screen."""

import sys

from PyQt5.QtWidgets import QApplication

from app.window import TestWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("康复界面独立测试")
    window = TestWindow()
    window.showMaximized()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

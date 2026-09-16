from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.theme import page_background
from app.widgets.gesture_cards import GestureStageSelector


class TrainingGestureSelectPage(QWidget):
    back_requested = pyqtSignal()
    next_requested = pyqtSignal(list)

    def __init__(self, title):
        super().__init__()
        self.title_text = title
        self.selector = None
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("pageRoot")
        page_background(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 40)
        root.setSpacing(24)

        nav = QHBoxLayout()
        back = QPushButton("◀ 返回")
        back.setObjectName("secondaryButton")
        back.setFixedWidth(180)
        back.clicked.connect(self.back_requested.emit)

        title = QLabel(self.title_text)
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Microsoft YaHei", 42, QFont.Bold))
        title.setStyleSheet("color:#0b347f;")

        next_btn = QPushButton("下一步 ▶")
        next_btn.setFixedWidth(210)
        next_btn.clicked.connect(self.next_step)
        next_btn.setToolTip("界面展示：暂不进入后续训练页面")

        nav.addWidget(back)
        nav.addWidget(title, 1)
        nav.addWidget(next_btn)

        self.selector = GestureStageSelector()

        root.addLayout(nav)
        root.addSpacing(12)
        root.addWidget(self.selector, 1)

    def selected_gestures(self):
        return self.selector.selected()

    def reset_selection(self):
        self.selector.reset_selection()

    def next_step(self):
        # Keep the original button appearance; this demo ends at this page.
        pass

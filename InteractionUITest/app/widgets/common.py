from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QImage
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.theme import apply_card_shadow


class TopBar(QFrame):
    def __init__(self, title, back_text="返回主页", parent=None):
        super().__init__(parent)
        self.setFixedHeight(104)
        self.setObjectName("topGlass")
        self.setStyleSheet(
            """
            QFrame#topGlass {
                background: rgba(255, 255, 255, 0.30);
                border-bottom: 1px solid rgba(255, 255, 255, 0.70);
            }
            QLabel {
                color: #0c367e;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 14, 28, 14)

        self.brand = QLabel("脑卒中康复系统")
        self.brand.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Microsoft YaHei", 34, QFont.Bold))
        self.back_button = QPushButton(back_text.lstrip("←<‹ "))
        self.back_button.setObjectName("topBackButton")
        self.back_button.setStyleSheet(
            "QPushButton {"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:0.58 #eef7ff, stop:1 #cae6ff);"
            "color: #0d63e5; font-size: 26px; font-weight: 900;"
            "border: 2px solid rgba(255,255,255,0.98);"
            "border-radius: 30px; min-height: 64px; padding: 8px 28px;"
            "}"
            "QPushButton:hover {"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ffffff, stop:0.55 #e8f5ff, stop:1 #bfe2ff);"
            "border: 2px solid #74b9ff; color:#0757d0;"
            "}"
        )
        apply_card_shadow(self.back_button, blur=24, y_offset=8, color=(36, 113, 225, 58))

        layout.addWidget(self.brand, 1)
        layout.addWidget(self.title, 2)
        layout.addWidget(self.back_button, 1, Qt.AlignRight)



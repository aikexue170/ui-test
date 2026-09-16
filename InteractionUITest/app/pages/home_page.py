from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.theme import apply_card_shadow, page_background, paint_home_background


class HandIcon(QWidget):
    def __init__(self, variant="rehab", parent=None):
        super().__init__(parent)
        self.variant = variant
        self.setFixedSize(190, 190)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)

        glow = QLinearGradient(0, 0, self.width(), self.height())
        glow.setColorAt(0, QColor(255, 255, 255, 210))
        glow.setColorAt(1, QColor(216, 236, 255, 160))
        painter.setBrush(glow)
        painter.setPen(QPen(QColor(255, 255, 255, 230), 2))
        painter.drawEllipse(center, 90, 90)

        painter.setPen(QPen(QColor("#1f77f2"), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        base_x = center.x() - 31
        base_y = center.y() + 45
        for index, height in enumerate((76, 93, 82, 62)):
            x = base_x + index * 21
            painter.drawLine(QPointF(x, base_y), QPointF(x, base_y - height))

        painter.drawLine(QPointF(base_x - 12, base_y - 17), QPointF(base_x - 54, base_y - 54))
        painter.drawArc(QRectF(center.x() - 76, center.y() - 2, 140, 96), 196 * 16, 128 * 16)

        painter.setPen(QPen(QColor("#8fc6ff"), 5, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(QRectF(center.x() - 74, center.y() + 20, 148, 70), 190 * 16, 160 * 16)

        if self.variant == "add":
            painter.setBrush(QColor("#1f77f2"))
            painter.setPen(QPen(QColor(255, 255, 255), 4))
            painter.drawEllipse(QPointF(center.x() + 62, center.y() + 58), 30, 30)
            painter.setPen(QPen(QColor(255, 255, 255), 7, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(center.x() + 46, center.y() + 58), QPointF(center.x() + 78, center.y() + 58))
            painter.drawLine(QPointF(center.x() + 62, center.y() + 42), QPointF(center.x() + 62, center.y() + 74))
        elif self.variant == "evaluation":
            badge_center = QPointF(center.x() + 60, center.y() + 58)
            painter.setBrush(QColor("#1f77f2"))
            painter.setPen(QPen(QColor(255, 255, 255), 4))
            painter.drawEllipse(badge_center, 30, 30)
            painter.setPen(QPen(QColor(255, 255, 255), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawRect(QRectF(badge_center.x() - 15, badge_center.y() - 15, 24, 27))
            chart = QPainterPath()
            chart.moveTo(badge_center.x() - 11, badge_center.y() + 4)
            chart.lineTo(badge_center.x() - 5, badge_center.y() - 2)
            chart.lineTo(badge_center.x() + 1, badge_center.y() + 2)
            chart.lineTo(badge_center.x() + 6, badge_center.y() - 7)
            painter.drawPath(chart)
            painter.drawEllipse(QPointF(badge_center.x() + 13, badge_center.y() + 10), 8, 8)
            painter.drawLine(QPointF(badge_center.x() + 9, badge_center.y() + 10), QPointF(badge_center.x() + 12, badge_center.y() + 13))
            painter.drawLine(QPointF(badge_center.x() + 12, badge_center.y() + 13), QPointF(badge_center.x() + 18, badge_center.y() + 6))


class GlassActionCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title, subtitle, variant="rehab", parent=None):
        super().__init__(parent)
        self.setObjectName("homeActionCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(340, 430)
        self.setMaximumSize(560, 660)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        apply_card_shadow(self, blur=32, y_offset=10, color=(36, 113, 225, 42))
        self.setStyleSheet(
            """
            QFrame#homeActionCard {
                background: rgba(255, 255, 255, 0.36);
                border: 3px solid rgba(255, 255, 255, 0.92);
                border-radius: 58px;
            }
            QFrame#homeActionCard:hover {
                background: rgba(255, 255, 255, 0.52);
                border: 3px solid rgba(255, 255, 255, 1.0);
            }
            QLabel#homeTitle {
                color: #0b347f;
                font-size: 40px;
                font-weight: 900;
                background: transparent;
            }
            QLabel#homeSub {
                color: #1f5fae;
                font-size: 23px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#homeLine {
                background: #1597ff;
                border-radius: 4px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 38, 32, 38)
        layout.setSpacing(12)
        layout.addStretch(1)
        layout.addWidget(HandIcon(variant), alignment=Qt.AlignCenter)
        layout.addSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("homeTitle")
        title_label.setAlignment(Qt.AlignCenter)
        sub_label = QLabel(subtitle)
        sub_label.setObjectName("homeSub")
        sub_label.setAlignment(Qt.AlignCenter)
        line = QLabel()
        line.setObjectName("homeLine")
        line.setFixedSize(60, 8)

        layout.addWidget(title_label)
        layout.addWidget(sub_label)
        layout.addSpacing(16)
        layout.addWidget(line, alignment=Qt.AlignCenter)
        layout.addStretch(1)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)



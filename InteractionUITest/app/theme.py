APP_STYLE = """
QWidget {
    font-family: "Microsoft YaHei";
    font-size: 24px;
    color: #0f2f6e;
}
QLineEdit, QComboBox {
    min-height: 64px;
    border: 1px solid rgba(114, 164, 236, 0.42);
    border-radius: 18px;
    padding: 4px 18px;
    background: rgba(255, 255, 255, 0.84);
    color: #11316f;
    selection-background-color: #2578f4;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #2384ff;
    background: white;
}
QPushButton {
    min-height: 66px;
    border: none;
    border-radius: 22px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1297ff, stop:1 #256df4);
    color: white;
    padding: 10px 28px;
    font-size: 27px;
    font-weight: 700;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2ba7ff, stop:1 #1761ee);
}
QPushButton:pressed {
    background: #0f61d9;
}
QPushButton:disabled {
    background: #a7b4c8;
    color: #edf4ff;
}
QPushButton#secondaryButton {
    background: rgba(255, 255, 255, 0.74);
    color: #1764dc;
    border: 1px solid rgba(255, 255, 255, 0.92);
}
QPushButton#secondaryButton:hover {
    background: rgba(237, 247, 255, 0.94);
}
QPushButton#dangerButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff706a, stop:1 #e11d48);
}
QPushButton#profilePill {
    min-height: 88px;
    border-radius: 44px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255, 255, 255, 0.96),
        stop:0.62 rgba(238, 247, 255, 0.92),
        stop:1 rgba(210, 233, 255, 0.86)
    );
    color: #0d63e5;
    border: 2px solid rgba(255, 255, 255, 0.98);
    font-size: 31px;
    font-weight: 900;
    padding: 8px 30px;
}
QPushButton#profilePill:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffffff,
        stop:0.55 #e8f5ff,
        stop:1 #bfe2ff
    );
    border: 2px solid #74b9ff;
    color: #0757d0;
}
QFrame#panel, QFrame#softPanel {
    background: rgba(255, 255, 255, 0.56);
    border: 2px solid rgba(255, 255, 255, 0.86);
    border-radius: 34px;
}
QFrame#glassPanel {
    background: rgba(255, 255, 255, 0.50);
    border: 2px solid rgba(255, 255, 255, 0.90);
    border-radius: 42px;
}
QLabel#sectionTitle {
    color: #0f3478;
    font-size: 34px;
    font-weight: 800;
}
QLabel#subText {
    color: #3f6ba9;
    font-size: 24px;
}
QTableWidget {
    background: rgba(255, 255, 255, 0.70);
    border: 2px solid rgba(255, 255, 255, 0.90);
    border-radius: 24px;
    gridline-color: rgba(80, 140, 220, 0.20);
    selection-background-color: #d9ecff;
    selection-color: #0f3478;
}
QHeaderView::section {
    background: rgba(220, 239, 255, 0.92);
    color: #0f3478;
    font-size: 22px;
    font-weight: 700;
    border: none;
    padding: 12px;
}
"""


def page_background(widget):
    widget.setStyleSheet(APP_STYLE + """
    QWidget#pageRoot {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 #d8ecff, stop:0.34 #f8fcff, stop:0.66 #ddecff, stop:1 #7fc2ff
        );
    }
    """)


def apply_card_shadow(widget, blur=34, y_offset=12, color=(45, 115, 210, 64)):
    from PyQt5.QtGui import QColor
    from PyQt5.QtWidgets import QGraphicsDropShadowEffect

    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(*color))
    widget.setGraphicsEffect(shadow)


def paint_home_background(widget, painter):
    from PyQt5.QtCore import QPointF, QRectF, Qt
    from PyQt5.QtGui import QColor, QLinearGradient, QPainterPath, QPen

    painter.setRenderHint(painter.Antialiasing)
    rect = QRectF(widget.rect())

    bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
    bg.setColorAt(0, QColor("#d7ecff"))
    bg.setColorAt(0.34, QColor("#f9fcff"))
    bg.setColorAt(0.68, QColor("#ddecff"))
    bg.setColorAt(1, QColor("#7fc2ff"))
    painter.fillRect(rect, bg)

    painter.setPen(QPen(QColor(255, 255, 255, 145), 2))
    for offset in (0, 54, 110):
        path = QPainterPath()
        path.moveTo(-60, widget.height() * 0.46 + offset)
        path.cubicTo(
            widget.width() * 0.22,
            widget.height() * 0.72 + offset,
            widget.width() * 0.48,
            widget.height() * 0.96 + offset,
            widget.width() + 80,
            widget.height() * 0.66 + offset,
        )
        painter.drawPath(path)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(255, 255, 255, 105))
    for row in range(8):
        for col in range(11):
            painter.drawEllipse(QPointF(10 + col * 16, widget.height() - 280 + row * 18), 3, 3)
            painter.drawEllipse(QPointF(236 + col * 16, 250 + row * 16), 2.5, 2.5)

    painter.setPen(QPen(QColor("#b9d9ff"), 2))
    painter.setBrush(QColor("#b9d9ff"))
    start_x = widget.width() - 380
    start_y = widget.height() * 0.39
    points = [
        QPointF(start_x, start_y),
        QPointF(start_x + 62, start_y + 50),
        QPointF(start_x + 116, start_y + 18),
        QPointF(start_x + 168, start_y + 74),
        QPointF(start_x + 232, start_y + 42),
    ]
    for p1, p2 in zip(points, points[1:]):
        painter.drawLine(p1, p2)
    for point in points:
        painter.drawEllipse(point, 8, 8)

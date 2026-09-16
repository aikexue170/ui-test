"""悬浮的语音控制条：麦克风按钮 + 一句状态反馈。

挂在主窗口上而不是某个页面上，所以切页不会丢。
位置贴底居中，窗口尺寸变化时自动跟随（靠事件过滤器，不改 window.py 的布局）。
"""

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from app.theme import apply_card_shadow

_STATUS_COLORS = {
    "idle": "#1f5fae",
    "info": "#1f5fae",
    "busy": "#0d63e5",
    "ok": "#0a7a4a",
    "warn": "#b3541e",
}


class AiOverlay(QFrame):
    mic_clicked = pyqtSignal()
    text_submitted = pyqtSignal(str)

    def __init__(self, window, config):
        super().__init__(window)
        self.setObjectName("aiOverlay")
        self._window = window
        self._config = config
        self.setFixedHeight(78)
        self.setMinimumWidth(560)
        self.setStyleSheet(
            """
            QFrame#aiOverlay {
                background: rgba(255, 255, 255, 0.94);
                border: 2px solid rgba(255, 255, 255, 1.0);
                border-radius: 39px;
            }
            """
        )
        apply_card_shadow(self, blur=30, y_offset=8, color=(36, 113, 225, 70))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 26, 12)
        layout.setSpacing(16)

        self.mic_button = QPushButton("🎤 语音操控")
        self.mic_button.setObjectName("aiMicButton")
        self.mic_button.setCursor(Qt.PointingHandCursor)
        self.mic_button.setFixedHeight(54)
        self.mic_button.setMinimumWidth(190)
        self.mic_button.setStyleSheet(
            """
            QPushButton#aiMicButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1297ff,stop:1 #256df4);
                color: white; border: none; border-radius: 27px;
                font-family: 'Microsoft YaHei'; font-size: 22px; font-weight: 800;
                padding: 4px 20px;
            }
            QPushButton#aiMicButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2ba7ff,stop:1 #1761ee);
            }
            QPushButton#aiMicButton:disabled {
                background: #dde5f0; color: #7c8ca6;
            }
            QPushButton#aiMicButton[recording="true"] {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ff706a,stop:1 #e11d48);
            }
            """
        )
        self.mic_button.clicked.connect(self.mic_clicked.emit)
        layout.addWidget(self.mic_button)

        self.status_label = QLabel("点左边的麦克风说话，我会帮你点到对应的地方")
        self.status_label.setWordWrap(False)
        self.status_label.setStyleSheet(
            "font-family:'Microsoft YaHei'; font-size:20px; font-weight:700;"
            "color:%s; background:transparent;" % _STATUS_COLORS["idle"]
        )
        layout.addWidget(self.status_label, 1)

        self.text_input = None
        if config.debug_text_input:
            self.text_input = QLineEdit()
            self.text_input.setPlaceholderText("无麦克风时在这里打字，回车提交")
            self.text_input.setFixedWidth(280)
            self.text_input.setStyleSheet(
                "font-family:'Microsoft YaHei'; font-size:18px; min-height:44px;"
                "border:1px solid rgba(114,164,236,0.5); border-radius:22px;"
                "padding:2px 16px; background:rgba(255,255,255,0.9); color:#11316f;"
            )
            self.text_input.returnPressed.connect(self._submit_text)
            layout.addWidget(self.text_input)

        window.installEventFilter(self)

    # ------------------------------------------------------------ 对外
    def set_status(self, text, level="info"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            "font-family:'Microsoft YaHei'; font-size:20px; font-weight:700;"
            "color:%s; background:transparent;" % _STATUS_COLORS.get(level, _STATUS_COLORS["info"])
        )

    def set_recording(self, recording, enabled=True):
        self.mic_button.setEnabled(enabled)
        self.mic_button.setProperty("recording", "true" if recording else "false")
        self.mic_button.setText("■ 结束录音" if recording else "🎤 语音操控")
        # 改 property 后必须重刷样式，否则 QSS 选择器不生效
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)

    def reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        width = max(self.minimumWidth(), min(self.sizeHint().width(), parent.width() - 80))
        self.setFixedWidth(width)
        self.move((parent.width() - width) // 2, parent.height() - self.height() - 16)
        self.raise_()

    # ------------------------------------------------------------ 事件
    def eventFilter(self, obj, event):
        if obj is self._window and event.type() in (QEvent.Resize, QEvent.Show):
            self.reposition()
        return super().eventFilter(obj, event)

    def _submit_text(self):
        text = self.text_input.text().strip()
        if text:
            self.text_input.clear()
            self.text_submitted.emit(text)

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.pages.home_page import GlassActionCard
from app.theme import page_background, paint_home_background
from app.widgets.common import TopBar


def _use_home_style_topbar(top):
    top.setStyleSheet(
        """
        QFrame#topGlass {
            background: transparent;
            border: none;
        }
        QLabel {
            color: #0c367e;
            background: transparent;
        }
        """
    )


class RehabModePage(QWidget):
    home_requested = pyqtSignal()
    active_requested = pyqtSignal()
    passive_requested = pyqtSignal()
    mirror_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("pageRoot")
        page_background(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(70, 24, 70, 34)
        root.setSpacing(18)

        top = TopBar("康复训练")
        _use_home_style_topbar(top)
        top.back_button.clicked.connect(self.home_requested.emit)
        root.addWidget(top)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 22, 0, 8)
        actions.setSpacing(70)

        active = GlassActionCard("主动训练", "意图识别 · 辅助动作")
        passive = GlassActionCard("被动训练", "循环执行 · 规范引导")
        mirror = GlassActionCard("镜像训练", "手势校准 · 实时预测", "add")
        active.clicked.connect(self.active_requested.emit)
        passive.clicked.connect(self.passive_requested.emit)
        mirror.clicked.connect(self.mirror_requested.emit)
        actions.addWidget(active)
        actions.addWidget(passive)
        actions.addWidget(mirror)

        root.addLayout(actions, 1)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        paint_home_background(self, painter)


class MirrorModePage(QWidget):
    back_requested = pyqtSignal()
    gesture_requested = pyqtSignal()
    rehab_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("pageRoot")
        page_background(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(70, 24, 70, 34)
        root.setSpacing(18)

        top = TopBar("镜像训练")
        _use_home_style_topbar(top)
        top.back_button.clicked.connect(self.back_requested.emit)
        root.addWidget(top)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 36, 0, 18)
        actions.setSpacing(70)

        gesture = GlassActionCard("添加手势", "模型校准 · 动作采集", "add")
        rehab = GlassActionCard("康复训练", "加载模型 · 实时预测")
        gesture.clicked.connect(self.gesture_requested.emit)
        rehab.clicked.connect(self.rehab_requested.emit)
        actions.addStretch(1)
        actions.addWidget(gesture)
        actions.addWidget(rehab)
        actions.addStretch(1)

        root.addLayout(actions, 1)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        paint_home_background(self, painter)

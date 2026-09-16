from functools import lru_cache
from pathlib import Path

from PyQt5.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QLayout,
)

from app.gesture_config import GESTURE_GROUPS, group_of_gesture, image_name_for_gesture


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def _find_image_path(file_name):
    if not file_name:
        return None
    path = PROJECT_ROOT / "assets" / "gestures" / file_name
    return path if path.is_file() else None


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hspacing=28, vspacing=28):
        super().__init__(parent)
        self._items = []
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._hspacing
            if next_x - self._hspacing > effective.right() and line_height > 0:
                x = effective.x()
                y += line_height + self._vspacing
                next_x = x + hint.width() + self._hspacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


class GestureImageCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, gesture_name, parent=None):
        super().__init__(parent)
        self.setObjectName("gestureImageCard")
        self._gesture_name = gesture_name
        self._checked = False
        self._pixmap = QPixmap()
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(360, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedHeight(218)
        self.image_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.image_label)

        self.name_label = QLabel(gesture_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(
            "font-family:'Microsoft YaHei'; font-size:30px; font-weight:900; color:#12315f; background: transparent;"
        )
        self.name_label.setFixedHeight(48)
        layout.addWidget(self.name_label)

        self.check_label = QLabel("✓", self)
        self.check_label.setAlignment(Qt.AlignCenter)
        self.check_label.setFixedSize(44, 44)
        self.check_label.setStyleSheet(
            "background:#176cff; color:white; border-radius:22px; "
            "font-family:'Arial'; font-size:30px; font-weight:900;"
        )
        self.check_label.hide()

        self._load_pixmap()
        self._apply_state()

    def text(self):
        return self._gesture_name

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = bool(checked)
        self._apply_state()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.setChecked(not self._checked)
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        image_top_right = self.image_label.geometry().topRight()
        self.check_label.move(
            image_top_right.x() - self.check_label.width() - 8,
            self.image_label.geometry().top() + 8,
        )
        self._update_image()

    def _load_pixmap(self):
        image_path = _find_image_path(image_name_for_gesture(self._gesture_name))
        if image_path:
            self._pixmap = QPixmap(str(image_path))
        if self._pixmap.isNull():
            self.image_label.setText("暂无图片")
            self.image_label.setStyleSheet(
                "font-size:20px; color:#6b7fa6; background:rgba(255,255,255,0.52); border-radius:18px;"
            )

    def _update_image(self):
        if self._pixmap.isNull():
            return
        target = self.image_label.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        self.image_label.setPixmap(self._pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _apply_state(self):
        if self._checked:
            self.setStyleSheet(
                "QFrame#gestureImageCard { background:rgba(246,251,255,0.98); border:3px solid #176cff; "
                "border-radius:26px; }"
            )
            self.check_label.show()
            self.check_label.raise_()
        else:
            self.setStyleSheet(
                "QFrame#gestureImageCard { background:rgba(255,255,255,0.92); border:1px solid rgba(225,235,248,0.96); "
                "border-radius:26px; }"
                "QFrame#gestureImageCard:hover { background:white; border:2px solid rgba(23,108,255,0.48); }"
            )
            self.check_label.hide()


class GestureStageSelector(QFrame):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gestureStageSelector")
        self._selected = set()
        self._active_group = next(iter(GESTURE_GROUPS))
        self._tab_buttons = {}
        self._visible_cards = {}
        self.setStyleSheet(
            """
            QFrame#gestureStageSelector {
                background:rgba(239,247,255,0.86);
                border-radius:26px;
            }
            QPushButton#stageTab {
                background:transparent;
                color:#202734;
                border:none;
                border-radius:18px;
                font-family:'Microsoft YaHei';
                font-size:29px;
                font-weight:800;
                min-height:82px;
            }
            QPushButton#stageTab:checked {
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1d78ff,stop:1 #1765df);
                color:white;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(44, 40, 44, 36)
        root.setSpacing(28)

        tabs_shell = QFrame()
        tabs_shell.setStyleSheet(
            "QFrame { background:rgba(255,255,255,0.92); border-radius:20px; }"
        )
        tabs = QHBoxLayout(tabs_shell)
        tabs.setContentsMargins(0, 0, 0, 0)
        tabs.setSpacing(0)
        for index, group_name in enumerate(GESTURE_GROUPS):
            button = QPushButton(group_name)
            button.setObjectName("stageTab")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, name=group_name: self.set_active_group(name))
            self._tab_buttons[group_name] = button
            tabs.addWidget(button, 1)
            if index < len(GESTURE_GROUPS) - 1:
                line = QFrame()
                line.setFixedWidth(1)
                line.setStyleSheet("background:#dce6f2; border:none; margin-top:16px; margin-bottom:16px;")
                tabs.addWidget(line)
        root.addWidget(tabs_shell)

        info = QHBoxLayout()
        icon = QLabel("i")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(34, 34)
        icon.setStyleSheet(
            "background:#176cff; color:white; border-radius:17px; font-size:24px; font-weight:900;"
        )
        info_text = QLabel("请选择适合当前阶段的训练手势")
        info_text.setStyleSheet("font-size:24px; font-weight:700; color:#1765df;")
        info.addWidget(icon)
        info.addWidget(info_text)
        info.addStretch(1)
        root.addLayout(info)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(self.scroll, 1)

        self.set_active_group(self._active_group)

    def selected(self):
        ordered = []
        seen = set()
        for gestures in GESTURE_GROUPS.values():
            for gesture in gestures:
                if gesture in self._selected and gesture not in seen:
                    ordered.append(gesture)
                    seen.add(gesture)
        return ordered

    def set_selected(self, selected_names):
        self._selected = set(selected_names or [])
        self._sync_visible_cards()

    def reset_selection(self):
        self._selected = set()
        self.set_active_group(next(iter(GESTURE_GROUPS)))

    def set_gesture_selected(self, gesture_name, selected=True):
        """以「用户点了一下卡片」的等价方式设置勾选状态。

        不能只调 card.setChecked()：卡片自身的 _checked 与本类的 _selected
        是两处状态，只改前者会让 selected() 和界面显示不一致。

        ⚠️ 分组选择：同一个手势往往同时属于多个分期分组（20 个手势里有 14 个
        是多分组的，比如「五指伸展」在一期/二期/三期/自由选择里都有）。
        所以**必须先看当前分组里有没有它**，有就在当前分组勾选，
        绝不能直接跳到「第一个包含它的分组」——那会把用户从当前分期硬拽走。
        只有当前分组确实没有这个手势时，才切到包含它的分组。
        """
        if gesture_name not in GESTURE_GROUPS.get(self._active_group, ()):
            group = group_of_gesture(gesture_name)
            if group is None:
                return False
            self.set_active_group(group)
        card = self._visible_cards.get(gesture_name)
        if card is None:
            return False
        if card.isChecked() != bool(selected):
            card.setChecked(bool(selected))
            card.clicked.emit()
        return True

    def set_active_group(self, group_name):
        if group_name not in GESTURE_GROUPS:
            return
        self._active_group = group_name
        for name, button in self._tab_buttons.items():
            button.setChecked(name == group_name)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        flow = FlowLayout(content, margin=0, hspacing=34, vspacing=30)
        self._visible_cards = {}
        for gesture in GESTURE_GROUPS[group_name]:
            card = GestureImageCard(gesture)
            card.setChecked(gesture in self._selected)
            card.clicked.connect(lambda name=gesture, widget=card: self._toggle_selection(name, widget))
            self._visible_cards[gesture] = card
            flow.addWidget(card)
        self.scroll.setWidget(content)

    def _toggle_selection(self, gesture_name, card):
        if card.isChecked():
            self._selected.add(gesture_name)
        else:
            self._selected.discard(gesture_name)
        self.selection_changed.emit()

    def _sync_visible_cards(self):
        for name, card in self._visible_cards.items():
            card.setChecked(name in self._selected)


class GestureGroupPanel(QFrame):
    """Compatibility wrapper for older imports."""

    selection_changed = pyqtSignal()

    def __init__(self, title, gestures, parent=None):
        super().__init__(parent)
        self.buttons = []
        layout = QVBoxLayout(self)
        for name in gestures:
            card = GestureImageCard(name)
            card.clicked.connect(self.selection_changed.emit)
            self.buttons.append(card)
            layout.addWidget(card)

    def selected(self):
        return [btn.text() for btn in self.buttons if btn.isChecked()]

    def set_selected(self, selected_names):
        selected = set(selected_names or [])
        for btn in self.buttons:
            btn.setChecked(btn.text() in selected)

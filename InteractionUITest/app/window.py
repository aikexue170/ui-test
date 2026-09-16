"""Independent, display-only navigation for the four retained pages."""

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QStackedWidget

from app.ai.controller import AiController
from app.pages.rehab_mode_page import MirrorModePage, RehabModePage
from app.pages.training_gesture_select_page import TrainingGestureSelectPage


class TestWindow(QStackedWidget):
    # A future voice worker can emit this signal to navigate on the GUI thread.
    navigate_requested = pyqtSignal(str)
    page_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("脑卒中康复系统")
        self.resize(1600, 900)
        self.home = RehabModePage()
        self.active = TrainingGestureSelectPage("选择主动训练手势")
        self.passive = TrainingGestureSelectPage("选择被动训练手势")
        self.mirror = MirrorModePage()
        self.pages = {
            "home": self.home,
            "active": self.active,
            "passive": self.passive,
            "mirror": self.mirror,
        }
        for name, page in self.pages.items():
            page.setProperty("page_id", name)
            self.addWidget(page)

        self.home.active_requested.connect(lambda: self.show_page("active"))
        self.home.passive_requested.connect(lambda: self.show_page("passive"))
        self.home.mirror_requested.connect(lambda: self.show_page("mirror"))
        self.home.home_requested.connect(lambda: self.show_page("home"))
        for page in (self.active, self.passive, self.mirror):
            page.back_requested.connect(lambda: self.show_page("home"))
        self.navigate_requested.connect(self.show_page)
        self.show_page("home")

        # 语音/AI 操控入口。用 AI_ENABLE=0 可整体关闭。
        self.ai = AiController(self)

    def closeEvent(self, event):
        self.ai.shutdown()
        super().closeEvent(event)

    @pyqtSlot(str)
    def show_page(self, page_id):
        """Select home/active/passive/mirror; unknown IDs leave the page as is."""
        page = self.pages.get(page_id)
        if page is None:
            return
        if page in (self.active, self.passive) and self.currentWidget() is not page:
            page.reset_selection()
        self.setCurrentWidget(page)
        self.page_changed.emit(page_id)

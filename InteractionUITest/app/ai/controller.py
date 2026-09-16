"""把动作注册表、意图路由、语音线程和悬浮条装配到一起。

window.py 里只需要两行：
    from app.ai.controller import AiController
    self.ai = AiController(self)
"""

from PyQt5.QtCore import QObject, pyqtSignal

from app.ai.actions import build_registry, page_id_of
from app.ai.config import CONFIG
from app.ai.overlay import AiOverlay
from app.ai.router import IntentRouter
from app.ai.server import LlamaServerManager


class AiController(QObject):
    """界面上的语音操控入口。任何时候都可以 handle_text() 喂一句话进去。"""

    text_recognized = pyqtSignal(str)

    # 语音依赖缺失时置 True，用来压住服务状态提示
    _voice_blocked = False

    def __init__(self, window, config=CONFIG, parent=None):
        super().__init__(parent if parent is not None else window)
        self.window = window
        self.config = config
        self.registry = build_registry(window)
        self.router = IntentRouter(window, self.registry, config)
        self.overlay = None
        self._voice = None
        # 语音线程的强引用池：QThread 绝不能在运行中被回收（见 router.py 顶部说明）
        self._voice_workers = []
        # 本地 llama-server 的自动拉起/探测（已经在跑就不会重复起）
        self.llm_server = LlamaServerManager(config, parent=self)
        self.llm_server.status_changed.connect(self._on_server_status)
        if config.enabled:
            self.llm_server.start()

        if config.enabled and config.show_overlay:
            self.overlay = AiOverlay(window, config)
            self.overlay.mic_clicked.connect(self.toggle_recording)
            self.overlay.text_submitted.connect(self.handle_text)
            self.overlay.show()
            self.overlay.reposition()

            self.router.decided.connect(self._on_decided)
            self.router.rejected.connect(self._on_rejected)
            self.router.thinking_changed.connect(self._on_thinking)

            # QStackedLayout 每次切页都会 raise 当前页，把悬浮条压到下面，
            # 所以切页后必须重新置顶。
            window.page_changed.connect(self._on_page_changed)

        # 语音依赖缺失的提示优先级最高，盖过服务状态
        if self.overlay is not None and self.config.voice_enabled:
            from app.ai.voice import missing_voice_packages

            missing = missing_voice_packages()
            if missing:
                self.overlay.set_recording(False, enabled=False)
                self.overlay.set_status(
                    "语音不可用（缺 %s），改用文字输入" % "、".join(missing), "warn"
                )
                self._voice_blocked = True

    # ------------------------------------------------------------ 对外
    def handle_text(self, text):
        """把一句话交给路由去决定点哪里。必须在主线程调用。"""
        text = (text or "").strip()
        if not text:
            return
        self.text_recognized.emit(text)
        if self.overlay is not None:
            self.overlay.set_status("听到：%s" % text, "info")
        self.router.handle_text(text)

    def toggle_recording(self):
        if self._voice is not None and self._voice.isRunning():
            self._voice.stop_recording()
            return

        if not self.config.voice_enabled:
            self._warn("语音功能已关闭")
            return

        from app.ai.voice import VoiceWorker, missing_voice_packages

        missing = missing_voice_packages()
        if missing:
            self._warn("语音不可用（缺 %s）" % "、".join(missing))
            return

        # 顺手清理已结束的旧线程：此刻它们都 running=False，丢掉引用是安全的
        self._voice_workers = [v for v in self._voice_workers if v.isRunning()]
        self._voice = VoiceWorker(self.config, parent=self)
        self._voice_workers.append(self._voice)
        self._voice.status.connect(lambda text: self._status(text, "busy"))
        self._voice.recognized.connect(self._on_recognized)
        self._voice.failed.connect(self._on_voice_failed)
        self._voice.finished.connect(lambda: self._set_recording(False))
        self._voice.start()
        self._set_recording(True)

    def shutdown(self):
        """窗口关闭时调用：先收语音线程，再等 AI 判断线程收尾。

        必须在窗口销毁前把线程等回来，否则解释器退出时析构一个仍在运行的
        QThread 会直接 qFatal（SIGABRT）。
        """
        if self._voice is not None and self._voice.isRunning():
            self._voice.stop_recording()
            self._voice.wait(10000)
        self.router.shutdown()
        # 只结束"自己拉起来的" llama-server；别人起的服务不碰
        self.llm_server.stop()

    # ------------------------------------------------------------ 内部
    def _set_recording(self, recording):
        if self.overlay is not None:
            self.overlay.set_recording(recording)

    def _status(self, text, level="info"):
        if self.overlay is not None:
            self.overlay.set_status(text, level)

    def _warn(self, text):
        self._status(text, "warn")

    def _on_recognized(self, text):
        self._set_recording(False)
        if not text:
            self._warn("没听清，请再说一次")
            return
        self.handle_text(text)

    def _on_voice_failed(self, message):
        self._set_recording(False)
        self._warn(message)

    def _on_page_changed(self, page_id):
        if self.overlay is not None:
            self.overlay.reposition()  # 内部会 raise_()

    def _on_thinking(self, thinking):
        if thinking:
            self._status("正在判断该点哪里…", "busy")

    def _on_decided(self, page_id, action_id, label, source):
        self._status("已点击「%s」（%s）" % (label, source), "ok")

    def _on_server_status(self, text, level):
        """服务状态只在"用户没在等结果"时占用状态条。"""
        if self._voice_blocked or self.router.busy:
            return
        self._status(text, level)

    def _on_rejected(self, message):
        # 服务还在加载模型时，把"连不上"翻译成人话
        if "连不上" in message and self.llm_server.starting:
            message = "AI 服务还在启动，请稍等几秒再试"
        self._status(message, "warn")

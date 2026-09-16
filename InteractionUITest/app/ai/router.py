"""意图路由：一句文本 -> 点一个控件。

三种结果：
  1. 正则快速通道命中（0ms，不调模型）
  2. 交给 LLM 工具调用判断（工作线程，不阻塞界面）
  3. 拿到 "none" 或非法 id -> 不点击，只给反馈

执行动作永远发生在主线程：LlmWorker 只发信号，Qt 会自动把信号
排队回主线程，槽函数里再去碰控件。

=========================================================================
⚠️ QThread 生命周期（这里踩过一次崩溃，别再改错）

崩溃现场：主线程在槽函数里执行 self._worker = None，QThread 析构时
Qt 发现线程还在运行 -> qFatal("QThread: Destroyed while thread is still
running") -> SIGABRT（退出码 134，systemd 报 Signal 6）。

为什么丢引用时线程还在跑：
    QThread 内部顺序是
        run() 返回 -> sip 释放包装引用 -> d->running = false -> emit finished
                                 ^^^ 就是这一段，线程还没被标记为结束
    如果在此之前 Python 侧已经不持有这个 QThread 对象，最后一个引用就会
    在"线程仍在运行"的窗口里被释放。

因此本模块的铁律：
    **LlmWorker 的引用只能在线程发出 finished 之后释放**，
    也就是只在 _release_worker() 里做 self._workers.discard()。
    finished_with_id / failed 槽里绝对不许动引用。
=========================================================================
"""

import time

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from app.ai.llm import LlmError, NONE_ID, choose_action


class LlmWorker(QThread):
    """在后台线程里问一次模型，只发信号，不碰任何控件。"""

    finished_with_id = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, text, actions, page_id, page_label, config, parent=None):
        super().__init__(parent)
        self.text = text
        self.page_id = page_id
        self._actions = actions
        self._page_label = page_label
        self._config = config

    def run(self):
        try:
            action_id = choose_action(
                self.text, self._actions, self._page_label, self._config
            )
        except LlmError as error:
            self.failed.emit(str(error))
            return
        except Exception as error:  # 兜底，绝不让线程里抛出去
            self.failed.emit("AI 调用异常：%s" % error)
            return
        self.finished_with_id.emit(action_id)


class IntentRouter(QObject):
    """把一个页面 + 一句话，变成一个动作。"""

    # (页面标识, 动作 id, 动作名称, 来源)
    decided = pyqtSignal(str, str, str, str)
    # 没能执行，附人类可读原因
    rejected = pyqtSignal(str)
    # 开始/结束一次 AI 判断（用于界面显示"思考中"）
    thinking_changed = pyqtSignal(bool)

    SOURCE_REGEX = "正则"
    SOURCE_LLM = "AI"

    def __init__(self, window, registry, config, parent=None):
        super().__init__(parent)
        self._window = window
        self._registry = registry
        self._config = config
        # 强引用池：worker 在这里待到线程真正结束，防止被 GC 提前回收
        self._workers = set()
        self._busy = None
        self._history = []

    # ------------------------------------------------------------ 对外
    @property
    def history(self):
        return list(self._history)

    @property
    def busy(self):
        return self._busy is not None

    def actions_for(self, page_id):
        return self._registry.get(page_id, [])

    def handle_text(self, text):
        """入口：这里假设已经在主线程。"""
        text = (text or "").strip()
        if not text:
            return

        page_id = self._current_page_id()
        if page_id is None:
            self.rejected.emit("当前没有可操作的页面")
            return

        actions = self.actions_for(page_id)
        if not actions:
            self.rejected.emit("这个页面上没有可操作的东西")
            return

        if self._config.regex_first:
            matched = self._fast_match(text, actions)
            if matched is not None:
                self._execute(page_id, matched, self.SOURCE_REGEX)
                return

        if self._busy is not None:
            self.rejected.emit("上一条指令还在处理，请稍等")
            return

        worker = LlmWorker(
            text, actions, page_id, self._page_label(page_id), self._config
        )
        # 顺序很重要：先入池拿到强引用，再接线，最后才 start()
        self._workers.add(worker)
        self._busy = worker
        worker.finished_with_id.connect(
            lambda action_id, w=worker: self._on_llm_result(w, action_id)
        )
        worker.failed.connect(
            lambda message, w=worker: self._on_llm_failed(w, message)
        )
        worker.finished.connect(lambda w=worker: self._release_worker(w))
        worker.start()
        self.thinking_changed.emit(True)

    def shutdown(self, wait_ms=8000):
        """窗口关闭时调用；等线程收尾，避免退出瞬间被析构。"""
        for worker in list(self._workers):
            worker.wait(wait_ms)

    # ------------------------------------------------------------ 内部
    def _current_page_id(self):
        widget = self._window.currentWidget()
        return widget.property("page_id") if widget is not None else None

    def _page_label(self, page_id):
        from app.ai.actions import PAGE_LABELS

        return PAGE_LABELS.get(page_id, page_id)

    def _fast_match(self, text, actions):
        """只对 fast=True 的动作做别名匹配；有歧义就交给模型。"""
        hits = []
        for action in actions:
            if not action.get("fast"):
                continue
            for alias in action.get("aliases", ()):
                if alias and alias in text:
                    hits.append((len(alias), action))
                    break
        if not hits:
            return None
        hits.sort(key=lambda item: -item[0])
        if len(hits) > 1 and hits[0][0] == hits[1][0]:
            return None  # 同样长的别名撞车 -> 不猜
        return hits[0][1]

    def _on_llm_result(self, worker, action_id):
        """注意：这里【不能】释放 worker 的引用，见文件头的说明。"""
        if worker is not self._busy:
            return  # 过期结果
        page_id = worker.page_id
        # 页面可能在等待期间被切走了，此时结果作废
        if self._current_page_id() != page_id:
            self.rejected.emit("页面已经切换，本条指令作废")
            return
        if not action_id or action_id == NONE_ID:
            self.rejected.emit("没听懂，这个页面上没有对应的操作")
            return
        action = self._find_action(page_id, action_id)
        if action is None:
            # 回表校验：模型给出的 id 必须真实存在于当前页动作表
            self.rejected.emit("AI 给了一个页面上不存在的操作，已忽略")
            return
        self._execute(page_id, action, self.SOURCE_LLM)

    def _on_llm_failed(self, worker, message):
        if worker is not self._busy:
            return
        self.rejected.emit(message)

    def _release_worker(self, worker):
        """只在这里释放引用 —— 此时 Qt 已把线程标记为结束。"""
        self._workers.discard(worker)
        if self._busy is worker:
            self._busy = None
        self.thinking_changed.emit(False)
        worker.deleteLater()

    def _find_action(self, page_id, action_id):
        for action in self.actions_for(page_id):
            if action["id"] == action_id:
                return action
        return None

    def _execute(self, page_id, action, source):
        try:
            action["run"]()
        except Exception as error:
            self.rejected.emit("执行「%s」出错：%s" % (action["label"], error))
            return
        self._history.append(
            {
                "at": time.time(),
                "page": page_id,
                "action_id": action["id"],
                "label": action["label"],
                "source": source,
            }
        )
        self.decided.emit(page_id, action["id"], action["label"], source)

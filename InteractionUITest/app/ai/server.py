"""自动拉起本地 llama-server，省掉每次手动敲启动指令。

行为：
   1. 先探测健康检查地址。**已经有服务在跑就什么都不做**——绝不重复起一个
      （两个 llama-server 抢同一个端口，第二个会绑定失败直接退出）。
   2. 探测不到才启动，参数与手动敲的那条完全一致，日志落到文件。
   3. 只结束"自己拉起来的"进程；别人起的服务不碰。
   4. 窗口关闭时自动收尾，不会留下孤儿进程。

实现上刻意用 threading.Thread 而不是 QThread：这是个要跑几十秒的启动任务，
放在 QThread 里会再次踩到 router.py 顶部写的那条生命周期铁律，没必要。
后台线程只通过 pyqtSignal 回主线程，停止时靠 _stop 事件让线程停止发信号。
"""

import atexit
import os
import shlex
import subprocess
import threading
import time
import urllib.error
import urllib.request

from PyQt5.QtCore import QObject, pyqtSignal

# 自动探测顺序（都不在时再看 PATH）
_CANDIDATE_BINARIES = (
    os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
    os.path.expanduser("~/llama.cpp/llama-server"),
    "/usr/local/bin/llama-server",
    "/usr/bin/llama-server",
)


def find_llama_server(explicit=""):
    """返回 llama-server 可执行文件路径；找不到返回 None。"""
    if explicit:
        return explicit if os.path.isfile(explicit) and os.access(explicit, os.X_OK) else None
    for path in _CANDIDATE_BINARIES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    # 最后看 PATH
    import shutil

    return shutil.which("llama-server")


def probe_health(url, timeout=1.5):
    """健康检查：有任何东西在 http 上正常应答就算活着。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


class LlamaServerManager(QObject):
    """负责"本地 LLM 服务在不在、不在就拉起来"。"""

    # (人类可读文本, 级别 info/ok/busy/warn)
    status_changed = pyqtSignal(str, str)
    # "external"（用别人起的）| "started"（自己拉起来的）
    ready = pyqtSignal(str)

    IDLE, PROBING, STARTING, READY, FAILED, EXTERNAL = (
        "idle", "probing", "starting", "ready", "failed", "external",
    )

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._proc = None          # 只有自己起的进程才有值
        self._log_file = None
        self._thread = None
        self._stop = threading.Event()
        self._state = self.IDLE
        atexit.register(self.stop)

    # ------------------------------------------------------------ 状态
    @property
    def state(self):
        return self._state

    @property
    def starting(self):
        """还在准备中（第一次请求前可以先等等）。"""
        return self._state in (self.IDLE, self.PROBING, self.STARTING)

    @property
    def owned(self):
        """服务是不是本进程拉起来的。"""
        return self._state == self.READY

    # ------------------------------------------------------------ 对外
    def start(self):
        if not self._config.llm_autostart or self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="llama-server-launcher", daemon=True
        )
        self._thread.start()

    def stop(self):
        """关闭窗口/退出时调用；幂等。"""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        self._kill_owned_process()

    # ------------------------------------------------------------ 内部
    def _emit(self, text, level="info"):
        if not self._stop.is_set():
            self.status_changed.emit(text, level)

    def _fail(self, message):
        self._state = self.FAILED
        self._emit(message, "warn")

    def _kill_owned_process(self):
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass

    def _run(self):
        config = self._config

        # 1) 已经有人在跑？那就不动手
        self._state = self.PROBING
        if probe_health(config.health_url):
            self._state = self.EXTERNAL
            self._emit("AI 服务已在线", "ok")
            self.ready.emit("external")
            return
        if self._stop.is_set():
            return

        # 2) 找可执行文件和模型
        binary = find_llama_server(config.llama_server_bin)
        if binary is None:
            self._fail(
                "找不到 llama-server；请用 AI_LLAMA_SERVER 指定路径"
            )
            return
        if not os.path.isfile(config.llm_model):
            self._fail("找不到模型文件：%s（用 AI_LLM_MODEL 指定）" % config.llm_model)
            return

        # 3) 起进程，参数和手动敲的一致
        host, port = config.llm_endpoint
        command = [
            binary, "-m", config.llm_model,
            "--host", host, "--port", str(port),
        ] + shlex.split(config.llama_extra_args)

        log_path = config.llama_log_path
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            self._log_file = open(log_path, "ab", buffering=0)
            self._log_file.write(
                ("\n=== %s ===\n%s\n" % (time.strftime("%F %T"), " ".join(command))).encode()
            )
        except OSError:
            self._log_file = subprocess.DEVNULL

        self._state = self.STARTING
        self._emit("正在启动 AI 服务（首次加载模型要几十秒）…", "busy")
        try:
            self._proc = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=self._log_file,
                stderr=subprocess.STDOUT,
            )
        except OSError as error:
            self._fail("启动 llama-server 失败：%s" % error)
            return

        # 4) 等模型加载完（llama-server 是先加载模型、后绑端口）
        deadline = time.time() + config.llm_startup_timeout
        while time.time() < deadline:
            if self._stop.is_set():
                self._kill_owned_process()
                return
            code = self._proc.poll()
            if code is not None:
                self._proc = None
                self._fail(
                    "AI 服务启动失败（退出码 %s），日志：%s" % (code, log_path)
                )
                return
            if probe_health(config.health_url, 1.0):
                self._state = self.READY
                self._emit("AI 服务已就绪，点麦克风说话", "ok")
                self.ready.emit("started")
                return
            time.sleep(0.5)

        if not self._stop.is_set():
            self._kill_owned_process()
            self._fail("AI 服务启动超时，日志：%s" % log_path)

"""AI 语音操控模块。

子模块职责：
    config.py     可调参数（环境变量覆盖）
    actions.py    动作注册表：页面上能点的东西 + 怎么点
    llm.py        本地 llama-server 的工具调用客户端
    router.py     一句话 -> 动作（正则快速通道 / LLM / 回表校验）
    voice.py      Qwen3-ASR 录音识别工作线程
    overlay.py    悬浮控制条
    controller.py 装配以上所有
"""

__all__ = ["AiController"]


def __getattr__(name):
    # 延迟导入，避免只想用 actions/llm 时被迫拉起整个 Qt 界面栈
    if name == "AiController":
        from app.ai.controller import AiController

        return AiController
    raise AttributeError(name)

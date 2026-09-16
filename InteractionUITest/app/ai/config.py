"""AI 语音操控的可调参数。所有项都可用环境变量覆盖，无需改代码。"""

import os
from urllib.parse import urlsplit


def _flag(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class AiConfig:
    """运行时配置。整体单例，见文件末尾的 CONFIG。"""

    def __init__(self):
        # 总开关
        self.enabled = _flag("AI_ENABLE", True)
        # 界面上的悬浮控制条
        self.show_overlay = _flag("AI_SHOW_OVERLAY", True)
        # 悬浮条里额外挂一个文本框，方便没有麦克风时用键盘联调
        self.debug_text_input = _flag("AI_TEXT_DEBUG", False)

        # ---- LLM 服务（OpenAI 兼容接口）----
        self.llm_url = os.environ.get(
            "AI_LLM_URL", "http://127.0.0.1:8081/v1/chat/completions"
        )
        self.llm_timeout_s = _int("AI_LLM_TIMEOUT", 60)
        self.max_tokens = _int("AI_LLM_MAX_TOKENS", 512)
        # 正则快速通道：命中则 0ms 出结果，不调模型
        self.regex_first = _flag("AI_REGEX_FIRST", True)

        # ---- 自动拉起本地 llama-server（省掉手动起服务）----
        # 1 = 打不开 llm_url 时自动启动；0 = 必须自己起
        self.llm_autostart = _flag("AI_LLM_AUTOSTART", True)
        # 留空则自动探测：PATH -> ~/llama.cpp/build/bin/llama-server
        self.llama_server_bin = os.environ.get("AI_LLAMA_SERVER", "")
        self.llm_model = os.path.expanduser(
            os.environ.get(
                "AI_LLM_MODEL", "~/模型/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"
            )
        )
        # 追加给 llama-server 的参数
        self.llama_extra_args = os.environ.get(
            "AI_LLAMA_EXTRA_ARGS", "-ngl 99 -c 8192 --jinja"
        )
        # 等模型加载完的最长时间（秒）
        self.llm_startup_timeout = _int("AI_LLM_STARTUP_TIMEOUT", 180)
        # 自动拉起的服务把日志写在这里
        self.llama_log_path = os.path.expanduser(
            os.environ.get("AI_LLAMA_LOG", "~/.cache/ui-test/llama-server.log")
        )

        # ---- 语音识别（Qwen3-ASR）----
        self.voice_enabled = _flag("AI_VOICE", True)
        self.asr_model = os.path.expanduser(
            os.environ.get("AI_ASR_MODEL", "~/模型/Qwen--Qwen3-ASR-0.6B-hf")
        )
        self.sample_rate = 16000
        # 短于这个秒数的录音直接丢弃
        self.min_audio_s = 0.3

    # ------------------------------------------------------------ 派生属性
    @property
    def llm_endpoint(self):
        """从 llm_url 推出 (host, port)，拉起服务时用。"""
        parts = urlsplit(self.llm_url)
        return parts.hostname or "127.0.0.1", parts.port or 8081

    @property
    def health_url(self):
        """llama-server 的健康检查地址。"""
        host, port = self.llm_endpoint
        scheme = urlsplit(self.llm_url).scheme or "http"
        return "%s://%s:%d/health" % (scheme, host, port)


CONFIG = AiConfig()

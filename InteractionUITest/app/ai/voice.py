"""语音识别工作线程：录音 -> Qwen3-ASR -> 文本。

改造自 TTS-LLM-STT/stt_demo.py。三处关键改动：
  1. 模型只在第一次用到时加载一次并常驻（原来是每次运行都加载）；
  2. 录音不再靠回车阻塞，改为「再点一次结束」，主线程通过 stop_recording() 通知；
  3. 识别结果用 pyqtSignal 抛出，绝不在这里碰任何 Qt 控件。

torch / transformers / sounddevice 只在 ai 环境里有，所以全部延迟导入；
缺依赖时 voice_available() 返回 False，界面降级而不是崩溃。
"""

import os
import queue

from PyQt5.QtCore import QThread, pyqtSignal


def voice_available():
    """语音链路是否可用。不抛异常，纯探测。"""
    try:
        import numpy  # noqa: F401
        import sounddevice  # noqa: F401
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except Exception:
        return False
    return True


def missing_voice_packages():
    missing = []
    for name in ("numpy", "sounddevice", "torch", "transformers"):
        try:
            __import__(name)
        except Exception:
            missing.append(name)
    return missing


def _load_engine(model_path):
    """加载 Qwen3-ASR，进程内只加载一次。"""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import torch
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained(model_path)
    model = (
        AutoModelForMultimodalLM.from_pretrained(model_path, dtype=torch.bfloat16)
        .to(device)
        .eval()
    )
    return processor, model, device


def transcribe_audio(processor, model, audio):
    """numpy 音频 -> 文本。"""
    import torch

    inputs = processor.apply_transcription_request(audio=audio).to(
        model.device, model.dtype
    )
    with torch.inference_mode():
        output_ids = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    generated = output_ids[:, inputs["input_ids"].shape[1]:]
    return processor.decode(generated, return_format="transcription_only")[0]


def transcribe_wav(path, model_path):
    """离线识别一个 wav 文件。用于没有麦克风时验证整条链路。"""
    import numpy as np
    import soundfile as sf

    audio, rate = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if rate != 16000:
        count = int(len(audio) * 16000 / rate)
        audio = np.interp(
            np.linspace(0, 1, count, endpoint=False),
            np.linspace(0, 1, len(audio), endpoint=False),
            audio,
        ).astype("float32")
    processor, model, _device = _load_engine(model_path)
    return transcribe_audio(processor, model, audio)


class VoiceWorker(QThread):
    """一段录音 = 一个线程实例。start() 开始录，stop_recording() 结束并识别。"""

    status = pyqtSignal(str)
    recognized = pyqtSignal(str)
    failed = pyqtSignal(str)

    _engine = None  # 类级缓存，跨实例复用

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._stop = False

    def stop_recording(self):
        self._stop = True

    def run(self):
        try:
            processor, model, _device = self._ensure_engine()
        except Exception as error:
            self.failed.emit("语音模型加载失败：%s" % error)
            return

        try:
            audio = self._record()
        except Exception as error:
            self.failed.emit("录音失败：%s" % error)
            return

        import numpy as np

        if audio is None or len(audio) < self._config.sample_rate * self._config.min_audio_s:
            self.failed.emit("录音太短，已忽略")
            return

        self.status.emit("正在识别…")
        try:
            text = transcribe_audio(processor, model, audio)
        except Exception as error:
            self.failed.emit("识别失败：%s" % error)
            return
        self.recognized.emit((text or "").strip())

    # ------------------------------------------------------------ 内部
    def _ensure_engine(self):
        if VoiceWorker._engine is None:
            self.status.emit("正在加载语音模型…")
            VoiceWorker._engine = _load_engine(self._config.asr_model)
        return VoiceWorker._engine

    def _record(self):
        import numpy as np
        import sounddevice as sd

        chunks = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                pass  # 录音溢出之类，忽略即可
            chunks.put(indata.copy())

        self.status.emit("录音中…再点一次结束")
        with sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
        ):
            while not self._stop:
                self.msleep(50)

        frames = []
        while not chunks.empty():
            frames.append(chunks.get())
        if not frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(frames, axis=0).ravel().astype(np.float32)

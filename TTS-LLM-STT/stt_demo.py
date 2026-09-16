"""Qwen3-ASR 录音识别演示。

运行:  (在 conda 的 ai 环境下)
    python stt_demo.py

用法:
    按回车 -> 开始录音
    再按回车 -> 结束录音, 输出识别出的文字
    想退出时直接按 Ctrl+C
"""

import os
import queue
import sys

import numpy as np
import sounddevice as sd
import torch

# ---- 模型路径 (按需修改) ----
os.environ.setdefault("HF_HUB_OFFLINE", "1")   # 用本地模型, 不联网
MODEL_PATH = os.path.expanduser("~/模型/Qwen--Qwen3-ASR-0.6B-hf")

SAMPLE_RATE = 16000          # 模型要求的采样率
CHANNELS = 1                 # 单声道
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_model():
    """加载模型和处理器, 只加载一次。"""
    from transformers import AutoModelForMultimodalLM, AutoProcessor

    print(f"正在加载模型 (device={DEVICE}) ...")
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    model = (
        AutoModelForMultimodalLM.from_pretrained(MODEL_PATH, dtype=torch.bfloat16)
        .to(DEVICE)
        .eval()
    )
    print("模型加载完成。\n")
    return processor, model


def record_audio():
    """非阻塞录音: 回车开始时调用, 结束时返回 float32 单声道 16kHz numpy 数组。"""
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    print("● 录音中 ... (再按一次回车结束)")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
    ):
        input()  # 阻塞在这里, 等回车结束录音
    print("■ 录音结束, 正在识别 ...")

    frames = []
    while not q.empty():  # 取出已录的数据
        frames.append(q.get())
    if not frames:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(frames, axis=0).ravel().astype(np.float32)


def transcribe(processor, model, audio):
    """把 numpy 音频送进模型, 返回识别文本。"""
    inputs = processor.apply_transcription_request(audio=audio).to(model.device, model.dtype)
    with torch.inference_mode():
        output_ids = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    generated = output_ids[:, inputs["input_ids"].shape[1]:]
    return processor.decode(generated, return_format="transcription_only")[0]


def main():
    processor, model = load_model()
    print("按回车开始录音, 再按回车结束录音。Ctrl+C 退出。\n")

    # 提示当前使用的麦克风默认输入设备
    try:
        in_dev = sd.default.device[0]
        print("默认输入设备:", sd.query_devices(in_dev)["name"], "\n")
    except Exception:
        pass

    while True:
        try:
            input("▶ 按回车开始录音 ...")
            audio = record_audio()
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            return

        if len(audio) < SAMPLE_RATE * 0.3:  # 少于 0.3 秒视为没录到
            print("(录音太短, 已忽略)\n")
            continue

        text = transcribe(processor, model, audio)
        print(f"\n识别结果: {text}\n")


if __name__ == "__main__":
    main()

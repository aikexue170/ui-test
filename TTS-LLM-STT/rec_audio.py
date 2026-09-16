"""录音导出脚本: 回车开始录音, 再按回车停止, 保存为 wav (16kHz 单声道)。

运行:  python rec_audio.py
可以连续录多条, 文件保存在 脚本目录/recordings/rec_<时间戳>.wav, Ctrl+C 退出。
"""

import os
import queue
import sys
from datetime import datetime

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000          # 采样率 (ASR 常用 16k)
CHANNELS = 1                 # 单声道
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")


def record_audio():
    """回车开始时调用, 结束时返回 float32 单声道 16kHz numpy 数组。"""
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
    print("■ 录音结束")

    frames = []
    while not q.empty():
        frames.append(q.get())
    if not frames:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(frames, axis=0).ravel().astype(np.float32)


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    try:
        in_dev = sd.default.device[0]
        print("默认输入设备:", sd.query_devices(in_dev)["name"])
    except Exception:
        pass
    print(f"录音保存位置: {SAVE_DIR}\n")

    while True:
        try:
            input("▶ 按回车开始录音 ...")
            audio = record_audio()
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            return

        if len(audio) < SAMPLE_RATE * 0.1:  # 少于 0.1 秒当手滑, 不保存
            print("(录音太短, 未保存)\n")
            continue

        path = os.path.join(
            SAVE_DIR,
            datetime.now().strftime("rec_%Y%m%d_%H%M%S.wav"),
        )
        sf.write(path, audio, SAMPLE_RATE)
        print(f"\n已保存: {path}  ({len(audio) / SAMPLE_RATE:.1f} s)\n")


if __name__ == "__main__":
    main()

"""Qwen3-ASR 推理基准: 纯GPU / 纯CPU / 混合(GPU加速+CPU层) 三种模式对比。

模式说明:
  gpu    - 整个模型 (bf16) 放 GPU
  cpu    - 整个模型 (bf16) 放 CPU
  hybrid - audio塔/projector/词嵌入/上层14个decoder层 放 GPU, 下层14个decoder层 放 CPU
           (靠 accelerate 的 device_map 按层切分, 模块间张量自动搬运)

运行:
  python bench_asr.py --mode gpu
  python bench_asr.py --mode cpu
  python bench_asr.py --mode hybrid
  (可选) --wav 路径  --runs 3

每种模式建议单独进程跑, 内存数字才干净。
"""

import argparse
import glob
import json
import os
import resource
import sys
import time

import numpy as np
import soundfile as sf
import torch

MODEL_PATH = os.path.expanduser("~/模型/Qwen--Qwen3-ASR-0.6B-hf")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
MAX_NEW_TOKENS = 256

N_LOWER_CPU = 14  # hybrid 模式下放 CPU 的 decoder 层数 (layers.0..13)
N_LAYERS = 28


def load_audio(path):
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != 16000:
        n = int(len(x) * 16000 / sr)
        x = np.interp(np.linspace(0, 1, n, endpoint=False),
                      np.linspace(0, 1, len(x), endpoint=False), x).astype("float32")
    return x


def build_inputs(processor, audio):
    return processor.apply_transcription_request(
        audio=audio
    ).to(model_device_for_inputs(), torch.bfloat16)


def model_device_for_inputs():
    # device_map 模式下输入留在 cpu, 交给 accelerate 的 hook 自动搬运
    return "cpu"


def load_model(mode):
    from transformers import AutoProcessor, AutoModelForMultimodalLM

    processor = AutoProcessor.from_pretrained(MODEL_PATH)

    t0 = time.perf_counter()
    if mode == "gpu":
        model = AutoModelForMultimodalLM.from_pretrained(
            MODEL_PATH, dtype=torch.bfloat16
        ).to("cuda").eval()
    elif mode == "cpu":
        torch.set_num_threads(os.cpu_count())
        model = AutoModelForMultimodalLM.from_pretrained(
            MODEL_PATH, dtype=torch.bfloat16
        ).to("cpu").eval()
    elif mode == "hybrid":
        device_map = {
            "model.audio_tower": "cuda:0",
            "model.multi_modal_projector": "cuda:0",
            "model.language_model.embed_tokens": "cuda:0",
        }
        for i in range(N_LAYERS):
            dev = "cpu" if i < N_LOWER_CPU else "cuda:0"
            device_map[f"model.language_model.layers.{i}"] = dev
        device_map["model.language_model.norm"] = "cuda:0"
        device_map["lm_head"] = "cuda:0"
        model = AutoModelForMultimodalLM.from_pretrained(
            MODEL_PATH, dtype=torch.bfloat16, device_map=device_map
        ).eval()
    else:
        raise ValueError(mode)
    load_s = time.perf_counter() - t0
    return processor, model, load_s


def generate_once(model, inputs):
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["gpu", "cpu", "hybrid"], required=True)
    default_wav = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings", "*.wav")))
    ap.add_argument("--wav", default=default_wav[-1] if default_wav else None)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    if not args.wav or not os.path.exists(args.wav):
        print("找不到录音文件 (recordings/ 里没有 wav)", file=sys.stderr)
        sys.exit(1)
    audio = load_audio(args.wav)

    processor, model, load_s = load_model(args.mode)
    inputs = build_inputs(processor, audio)

    # 预热一次 (显存分配 / JIT / 线程初始化)
    warm = generate_once(model, inputs)
    gen_warm = warm[:, inputs["input_ids"].shape[1]:]
    text = processor.decode(gen_warm, return_format="transcription_only")[0]

    times = []
    for _ in range(args.runs):
        t0 = time.perf_counter()
        generate_once(model, inputs)
        times.append(time.perf_counter() - t0)

    if torch.cuda.is_available():
        gpu_alloc = torch.cuda.max_memory_allocated("cuda:0") / 1e9
        gpu_reserved = torch.cuda.max_memory_reserved("cuda:0") / 1e9
    else:
        gpu_alloc = gpu_reserved = 0.0
    ram_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024

    n_tokens = gen_warm.shape[1]
    print(json.dumps({
        "mode": args.mode,
        "wav": os.path.basename(args.wav),
        "audio_s": round(len(audio) / 16000, 2),
        "load_s": round(load_s, 2),
        "n_tokens": n_tokens,
        "gen_times_s": [round(t, 2) for t in times],
        "gen_avg_s": round(sum(times) / len(times), 2),
        "gpu_mem_alloc_GB": round(gpu_alloc, 2),
        "gpu_mem_reserved_GB": round(gpu_reserved, 2),
        "ram_peak_GB": round(ram_peak, 2),
        "text": text,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

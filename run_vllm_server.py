#!/usr/bin/env python3
"""
vLLM 서버 실행 (로컬 모델 고정)
- 항상 /models/Qwen2.5-7B-Instruct 만 사용
- 2개 GPU(TP=2), 포트 8001
"""

import os
import sys
import subprocess

MODEL_DIR = "/models/Qwen2.5-7B-Instruct"
HOST = "0.0.0.0"
PORT = "8001"
TP = "4"                 # tensor-parallel-size (GPU 2장)
MAX_MODEL_LEN = "8192"
GPU_UTIL = "0.9"

def main():
    # 반드시 로컬 디렉터리만 사용
    if not (os.path.isdir(MODEL_DIR) and os.path.isfile(os.path.join(MODEL_DIR, "config.json"))):
        print(f"❌ 모델 디렉터리 확인 실패: {MODEL_DIR}\n"
              f" - 폴더와 config.json 존재 여부를 확인하세요.")
        sys.exit(1)

    # 사용할 GPU 고정 (필요 시 바꾸세요: "0,1" / "0" 등)
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0,1,2,3")
    
    # 시간대 설정 (한국 시간)
    os.environ["TZ"] = "Asia/Seoul"
    os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":/usr/share/zoneinfo"

    print("🚀 vLLM 서버 시작 (로컬 모델 고정)")
    print(f"📁 MODEL_DIR = {MODEL_DIR}")
    print(f"🖥️  CUDA_VISIBLE_DEVICES = {os.environ['CUDA_VISIBLE_DEVICES']}")
    print(f"⏰ 시간대: {os.environ['TZ']}")
    print(f"🌐 http://{HOST}:{PORT}")
    print("=" * 60)

    cmd = [
        "python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_DIR,
        "--tokenizer", MODEL_DIR,           # 토크나이저도 같은 경로로 고정
        "--served-model-name", "Qwen/Qwen2.5-7B-Instruct",
        "--host", HOST, "--port", PORT,
        "--tensor-parallel-size", TP,
        "--gpu-memory-utilization", GPU_UTIL,
        "--max-model-len", MAX_MODEL_LEN,
        "--trust-remote-code",
        "--dtype", "auto",
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 서버 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

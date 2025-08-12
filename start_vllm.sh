#!/bin/bash

# vLLM 서버 실행 스크립트
# Qwen2.5-7B-Instruct 모델을 2개 GPU로 실행

# 시간대 설정 (한국 시간)
export TZ=Asia/Seoul

echo "vLLM 서버를 시작합니다..."
echo "모델: Qwen2.5-7B-Instruct"
echo "GPU 수: 2"
echo "포트: 8001"
echo "시간대: $TZ"
echo "================================"

# vLLM 서버 실행
python3 -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --download-dir /models \
  --tensor-parallel-size 2 \
  --host 0.0.0.0 \
  --port 8001 \
  --trust-remote-code \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9 
# syntax=docker/dockerfile:1.7
FROM node:24-trixie AS airi-build

ARG AIRI_REPO=https://github.com/moeru-ai/airi.git
ARG AIRI_REF=55e850d71a4db8e5128f56491de59eab26df7e64
ARG VITE_ENABLE_POSTHOG=false
ENV VITE_ENABLE_POSTHOG=${VITE_ENABLE_POSTHOG}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential ca-certificates curl git python3 python3-setuptools \
    && rm -rf /var/lib/apt/lists/*
RUN git init /src/airi \
    && cd /src/airi \
    && git remote add origin "${AIRI_REPO}" \
    && git fetch --depth 1 origin "${AIRI_REF}" \
    && git checkout --detach FETCH_HEAD

WORKDIR /src/airi
RUN corepack enable \
    && corepack prepare pnpm@10.33.0 --activate
RUN --mount=type=cache,id=pnpm-store,target=/root/.pnpm-store \
    pnpm install --frozen-lockfile
RUN pnpm -F @proj-airi/stage-web run build \
    && pnpm -F @proj-airi/docs run build:base \
    && mv ./docs/.vitepress/dist ./apps/stage-web/dist/docs \
    && pnpm -F @proj-airi/stage-ui run story:build \
    && mv ./packages/stage-ui/.histoire/dist ./apps/stage-web/dist/ui

FROM python:3.12-slim AS model-assets

ARG LLM_GGUF_REPO=ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho
ARG LLM_GGUF_FILE=gguf/EXAONE-3.5-7.8B-Instruct-Yaho-Q4_K_M.gguf
ARG STT_MODEL_REPO=mobiuslabsgmbh/faster-whisper-large-v3-turbo
ARG TTS_CUSTOM_MODEL_REPO=Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
ARG TTS_CLONE_MODEL_REPO=Qwen/Qwen3-TTS-12Hz-0.6B-Base

ENV HF_HOME=/tmp/huggingface \
    XDG_CACHE_HOME=/tmp/xdg \
    HF_HUB_DISABLE_TELEMETRY=1

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir huggingface_hub

RUN python - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id=os.environ["LLM_GGUF_REPO"],
    local_dir="/opt/models/llm",
    allow_patterns=[os.environ["LLM_GGUF_FILE"]],
)

snapshot_download(
    repo_id=os.environ["STT_MODEL_REPO"],
    local_dir="/opt/models/stt",
    allow_patterns=[
        "config.json",
        "preprocessor_config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.*",
    ],
)

snapshot_download(
    repo_id=os.environ["TTS_CUSTOM_MODEL_REPO"],
    local_dir="/opt/models/tts/custom",
    ignore_patterns=["*.md", ".gitattributes"],
)

snapshot_download(
    repo_id=os.environ["TTS_CLONE_MODEL_REPO"],
    local_dir="/opt/models/tts/base",
    ignore_patterns=["*.md", ".gitattributes"],
)
PY

FROM ghcr.io/ggml-org/llama.cpp:server-cuda

LABEL org.opencontainers.image.title="exaone-yaho-airi-stage2" \
      org.opencontainers.image.description="AIRI, EXAONE-Yaho, Korean STT, and Qwen3-TTS voice cloning for gcube" \
      org.opencontainers.image.source="https://github.com/vfxceo-ai/exaone-yaho-airi-gcube" \
      org.opencontainers.image.licenses="Apache-2.0 AND MIT AND LicenseRef-EXAONE-AI-Model-License-1.1-NC"

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/cache/airi/huggingface \
    HF_HUB_CACHE=/var/cache/airi/huggingface/hub \
    XDG_CACHE_HOME=/var/cache/airi \
    TOKENIZERS_PARALLELISM=false \
    CUDA_MODULE_LOADING=LAZY \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    LLM_MODEL_ID=ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho \
    LLM_MODEL_PATH=/models/llm/gguf/EXAONE-3.5-7.8B-Instruct-Yaho-Q4_K_M.gguf \
    LLM_HEALTH_URL=http://127.0.0.1:8000/health \
    STT_MODEL_ID=/models/stt \
    STT_COMPUTE_TYPE=int8_float16 \
    STT_LANGUAGE=ko \
    TTS_CUSTOM_MODEL_ID=/models/tts/custom \
    TTS_CLONE_MODEL_ID=/models/tts/base \
    TTS_LANGUAGE=Korean \
    TTS_DEFAULT_VOICE=sohee \
    TTS_CLONE_VOICE=yaho \
    TTS_REFERENCE_AUDIO=/mnt/dropbox/gcube/AIRI/voices/yaho/reference.wav \
    TTS_REFERENCE_TEXT=/mnt/dropbox/gcube/AIRI/voices/yaho/reference.txt \
    TTS_DTYPE=bfloat16 \
    TTS_ATTENTION=sdpa \
    TTS_DEVICE=cuda:0 \
    TTS_MAX_INPUT_CHARS=1000 \
    LLAMA_CTX_SIZE=4096 \
    LLAMA_N_GPU_LAYERS=99 \
    LLAMA_PARALLEL=1 \
    LOG_LEVEL=INFO

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl ffmpeg libsndfile1 libsox-fmt-all nginx python3 python3-pip python3-venv sox supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app
COPY requirements-stt.txt /opt/app/requirements-stt.txt
COPY requirements-tts.txt /opt/app/requirements-tts.txt
RUN python3 -m venv /opt/voice-venv \
    && /opt/voice-venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/voice-venv/bin/python -m pip install --no-cache-dir \
       torch==2.12.1 torchaudio==2.12.1 \
       --index-url https://download.pytorch.org/whl/cu130 \
    && /opt/voice-venv/bin/python -m pip install --no-cache-dir \
       -r /opt/app/requirements-stt.txt \
       -r /opt/app/requirements-tts.txt

COPY app /opt/app/app
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /usr/local/bin/airi-entrypoint.sh
COPY --from=airi-build /src/airi/apps/stage-web/dist /usr/share/nginx/html
COPY --from=model-assets /opt/models /models

RUN chmod 0755 /usr/local/bin/airi-entrypoint.sh \
    && mkdir -p \
       /var/cache/airi/huggingface \
       /var/cache/nginx \
       /var/lib/nginx \
       /mnt/dropbox/gcube/AIRI/voices/yaho \
       /run

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/airi-entrypoint.sh"]

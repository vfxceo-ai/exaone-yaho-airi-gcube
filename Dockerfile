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

FROM vllm/vllm-openai:v0.24.0-cu129-ubuntu2404

LABEL org.opencontainers.image.title="exaone-yaho-airi-stage1" \
      org.opencontainers.image.description="AIRI, EXAONE-Yaho vLLM, and Korean faster-whisper STT for gcube" \
      org.opencontainers.image.source="https://github.com/vfxceo-ai/exaone-yaho-airi-gcube" \
      org.opencontainers.image.licenses="Apache-2.0 AND MIT AND LicenseRef-EXAONE-AI-Model-License-1.1-NC"

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/var/cache/airi/huggingface \
    XDG_CACHE_HOME=/var/cache/airi \
    LLM_MODEL_ID=ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho \
    STT_MODEL_ID=large-v3-turbo \
    STT_COMPUTE_TYPE=int8_float16 \
    STT_LANGUAGE=ko \
    VLLM_GPU_MEMORY_UTILIZATION=0.52 \
    VLLM_MAX_MODEL_LEN=4096 \
    VLLM_MAX_NUM_SEQS=1 \
    LOG_LEVEL=INFO

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl ffmpeg libsndfile1 nginx python3-venv supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app
COPY requirements-stt.txt /opt/app/requirements-stt.txt
RUN python3 -m venv --system-site-packages /opt/stt-venv \
    && /opt/stt-venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/stt-venv/bin/python -m pip install --no-cache-dir \
       -r /opt/app/requirements-stt.txt

COPY app /opt/app/app
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /usr/local/bin/airi-entrypoint.sh
COPY --from=airi-build /src/airi/apps/stage-web/dist /usr/share/nginx/html

RUN chmod 0755 /usr/local/bin/airi-entrypoint.sh \
    && mkdir -p /var/cache/airi/huggingface /var/cache/nginx /var/lib/nginx /run

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/airi-entrypoint.sh"]

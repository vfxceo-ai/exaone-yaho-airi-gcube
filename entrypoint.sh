#!/usr/bin/env bash
set -Eeuo pipefail

: "${API_KEY:?API_KEY is required}"
: "${LLM_MODEL_PATH:?LLM_MODEL_PATH is required}"

if [[ ! "${API_KEY}" =~ ^[A-Za-z0-9_-]{32,128}$ ]]; then
  echo "[ ERROR ] API_KEY must be 32-128 URL-safe characters." >&2
  exit 64
fi

if [[ ! -f "${LLM_MODEL_PATH}" ]]; then
  echo "[ ERROR ] LLM model file not found: ${LLM_MODEL_PATH}" >&2
  exit 66
fi

if [[ ! -d "${STT_MODEL_ID}" ]]; then
  echo "[ ERROR ] STT model directory not found: ${STT_MODEL_ID}" >&2
  exit 66
fi

if [[ ! -d "${TTS_CUSTOM_MODEL_ID}" ]]; then
  echo "[ ERROR ] TTS custom voice model directory not found: ${TTS_CUSTOM_MODEL_ID}" >&2
  exit 66
fi

if [[ ! -d "${TTS_CLONE_MODEL_ID}" ]]; then
  echo "[ ERROR ] TTS clone model directory not found: ${TTS_CLONE_MODEL_ID}" >&2
  exit 66
fi

echo "[ START ] AIRI gateway + EXAONE-Yaho GGUF + Korean STT + Qwen3-TTS"
echo "[ START ] LLM model=${LLM_MODEL_ID} file=${LLM_MODEL_PATH} ctx=${LLAMA_CTX_SIZE} gpu_layers=${LLAMA_N_GPU_LAYERS} parallel=${LLAMA_PARALLEL}"
echo "[ START ] STT model_dir=${STT_MODEL_ID} compute_type=${STT_COMPUTE_TYPE}"
echo "[ START ] TTS custom=${TTS_CUSTOM_MODEL_ID} clone=${TTS_CLONE_MODEL_ID} attention=${TTS_ATTENTION}"
echo "[ START ] TTS voices=${TTS_DEFAULT_VOICE},${TTS_CLONE_VOICE} reference=${TTS_REFERENCE_AUDIO}"

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf

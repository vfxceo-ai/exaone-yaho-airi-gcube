#!/usr/bin/env bash
set -Eeuo pipefail

: "${API_KEY:?API_KEY is required}"

if [[ ! "${API_KEY}" =~ ^[A-Za-z0-9_-]{32,128}$ ]]; then
  echo "[ ERROR ] API_KEY must be 32-128 URL-safe characters." >&2
  exit 64
fi

echo "[ START ] AIRI gateway + EXAONE-Yaho + Korean STT"
echo "[ START ] LLM model=${LLM_MODEL_ID} max_len=${VLLM_MAX_MODEL_LEN} max_seqs=${VLLM_MAX_NUM_SEQS}"
echo "[ START ] STT model=${STT_MODEL_ID} compute_type=${STT_COMPUTE_TYPE}"

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf

#!/usr/bin/env bash
set -Eeuo pipefail

: "${BASE_URL:?BASE_URL is required}"
: "${API_KEY:?API_KEY is required}"

curl -fsS "${BASE_URL}/" | grep -qi '<!doctype html'
curl -fsS "${BASE_URL}/healthz"
curl -fsS "${BASE_URL}/llm/v1/models" \
  -H "Authorization: Bearer ${API_KEY}"
curl -fsS "${BASE_URL}/stt/v1/models" \
  -H "Authorization: Bearer ${API_KEY}"
curl -fsS "${BASE_URL}/tts/v1/models" \
  -H "Authorization: Bearer ${API_KEY}"

speech_file="$(mktemp --suffix=.mp3)"
trap 'rm -f "${speech_file}"' EXIT
curl -fsS "${BASE_URL}/tts/v1/audio/speech" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  --data '{"model":"qwen3-tts","input":"안녕! 음성 연결 테스트야.","voice":"sohee","response_format":"mp3"}' \
  --output "${speech_file}"
test -s "${speech_file}"

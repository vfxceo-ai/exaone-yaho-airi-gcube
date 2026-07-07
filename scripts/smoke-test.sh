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

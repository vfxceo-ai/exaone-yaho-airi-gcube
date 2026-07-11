# EXAONE-Yaho AIRI Stage 2 Voice

Stage 2 packages one RTX 5090 32 GB gcube workload that serves:

- AIRI Stage Web at `/`
- EXAONE-Yaho through `llama.cpp` GGUF at `/llm/v1/`
- Korean STT through `faster-whisper` at `/stt/v1/`
- Korean TTS through `Qwen3-TTS-12Hz-0.6B` at `/tts/v1/`

The TTS service has two voice modes:

- `sohee`: Qwen's built-in Korean female voice, available immediately
- `yaho`: a clone made from the user's reference audio in Dropbox

## What is inside

- `Dockerfile`: multi-stage AIRI build plus the GPU runtime
- `app/`: authenticated OpenAI-compatible STT and TTS adapter
- `nginx.conf`: same-origin routing for AIRI, LLM, STT, and TTS
- `supervisord.conf`: process lifecycle for `nginx`, `llama-server`, and `uvicorn`
- `workload-stage2.template.yaml`: gcube manifest template with a deployment-time GPU code
- `scripts/render-workload.ps1`: renders a private manifest without committing secrets
- `config/exaone-yaho.character.json`: AIRI character card bundled with this Stage 1 package

## Local verification

Create a virtual environment, install test dependencies, and run the unit tests:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
$env:PYTHONPATH='.'
python -m unittest discover -s tests -v
```

Shell syntax and smoke test script:

```powershell
"C:\Program Files\Git\bin\bash.exe" -n entrypoint.sh
"C:\Program Files\Git\bin\bash.exe" -n scripts/smoke-test.sh
```

If Docker is available:

```powershell
docker build --check -f Dockerfile .
docker build -t exaone-yaho-airi:stage1 .
```

## Required environment variables

```dotenv
API_KEY=replace-with-a-random-url-safe-value-of-at-least-32-characters
LLM_MODEL_ID=ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho
LLM_MODEL_PATH=/models/llm/gguf/EXAONE-3.5-7.8B-Instruct-Yaho-Q4_K_M.gguf
LLM_HEALTH_URL=http://127.0.0.1:8000/health
STT_MODEL_ID=/models/stt
STT_COMPUTE_TYPE=int8_float16
STT_LANGUAGE=ko
TTS_CUSTOM_MODEL_ID=/models/tts/custom
TTS_CLONE_MODEL_ID=/models/tts/base
TTS_LANGUAGE=Korean
TTS_DEFAULT_VOICE=sohee
TTS_CLONE_VOICE=yaho
TTS_REFERENCE_AUDIO=/mnt/dropbox/gcube/AIRI/voices/yaho/reference.wav
TTS_REFERENCE_TEXT=/mnt/dropbox/gcube/AIRI/voices/yaho/reference.txt
TTS_DTYPE=bfloat16
TTS_ATTENTION=sdpa
TTS_DEVICE=cuda:0
TTS_MAX_INPUT_CHARS=1000
LLAMA_CTX_SIZE=4096
LLAMA_N_GPU_LAYERS=99
LLAMA_PARALLEL=1
LOG_LEVEL=INFO
```

`API_KEY` must be shared by `/llm/v1/`, `/stt/v1/`, and `/tts/v1/`.
`LLM_MODEL_PATH` points at the GGUF file baked into the image during the GitHub Actions build.
`STT_MODEL_ID=/models/stt` points at the faster-whisper CTranslate2 directory baked into the same image, so Stage 1 no longer depends on outbound Hugging Face access at runtime.

## AIRI provider values

After the workload is running, open the AIRI UI and set:

```text
Chat provider: OpenAI Compatible
Chat base URL: https://<gcube-service-url>/llm/v1/
Chat model: use the first id returned by GET /llm/v1/models

Transcription provider: OpenAI Compatible
Transcription base URL: https://<gcube-service-url>/stt/v1/
Transcription model: whisper-1

Speech provider: OpenAI Compatible
Speech base URL: https://<gcube-service-url>/tts/v1/
Speech model: qwen3-tts
Speech voice: sohee
Speech speed: 1.0

API key: the same deployment API_KEY
```

AIRI stores provider credentials in the browser, not in the container environment.
Because Stage 1 now uses llama.cpp GGUF instead of the old vLLM alias, do not assume the chat model id is still `exaone-yaho` until `/llm/v1/models` confirms it.

To import the bundled persona:

1. Open `Settings` -> `AIRI Card`.
2. Upload `config/exaone-yaho.character.json`.
3. Activate the imported `갸루귀신` card.
4. Confirm the card uses `openai-compatible / exaone-yaho`.

## gcube deployment

Render the Stage 2 private manifest after checking the current RTX 5090 code with
`gcube -o json gpu list`:

```powershell
$ApiKey = 'replace-with-a-real-random-value'
.\scripts\render-workload.ps1 -GhcrOwner 'vfxceo-ai' -ApiKey $ApiKey -Stage stage2 -GpuCode '023'
```

Then register a new workload:

```powershell
gcube workload register --file .\workload-stage2.private.yaml
```

This template keeps:

- one RTX 5090 32 GB GPU selected by the verified current code
- `maxConnection: 20`
- Dropbox storage SER `98` mounted at `/mnt/dropbox`
- single public port `8080`

For gcube manifests, keep `repo: ghcr.io` and omit the registry prefix from `containerImage`. The rendered value should be `vfxceo-ai/exaone-yaho-airi:stage2`, not `ghcr.io/vfxceo-ai/exaone-yaho-airi:stage2`.

Use Dropbox only for small persistent files like future voice samples or exported config. Model caches stay on the workload-local disk under `/var/cache/airi`.
With the offline image layout, the EXAONE GGUF, STT, and both TTS checkpoints are copied into `/models` at build time instead of being downloaded during container startup.

## Voice clone upload

The reference should ideally be a clean 3-15 second clip with one speaker and no music.
Providing the exact transcript improves clone quality. Uploading without a transcript is
supported but uses speaker embedding only.

```powershell
.\scripts\upload-voice.ps1 `
  -BaseUrl 'https://<gcube-service-url>' `
  -ApiKey $ApiKey `
  -AudioPath 'D:\voice\reference.wav' `
  -Transcript '안녕, 나는 야호야. 오늘도 완전 신나게 놀아보자!'
```

The server normalizes the clip to mono 24 kHz WAV, stores it under
`/mnt/dropbox/gcube/AIRI/voices/yaho/`, and caches the clone prompt. After the upload
returns `"ready": true`, change the AIRI Speech voice from `sohee` to `yaho`.

## Stage 2 operating limits

- TTS GPU generation is serialized to one request to avoid VRAM spikes.
- `maxConnection: 20` remains available for the AIRI web UI and API traffic.
- The clone checkpoint loads lazily only when a `yaho` sample exists.
- The OpenAI-compatible Speech endpoint currently returns MP3 or WAV, not streaming audio.

## Image publishing

The GitHub Actions workflow pushes:

- `ghcr.io/<owner>/exaone-yaho-airi:stage2`
- `ghcr.io/<owner>/exaone-yaho-airi:<git-sha>`

GitHub Container Registry packages start as `private` on first publish. If you want gcube to pull anonymously, change the package visibility to `public` after the first successful push. If the package stays private, switch the manifest to credentialed pulls before registering the workload.

# EXAONE-Yaho AIRI Stage 1

Stage 1 packages one RTX 5090 32 GB gcube workload that serves:

- AIRI Stage Web at `/`
- EXAONE-Yaho through `llama.cpp` GGUF at `/llm/v1/`
- Korean STT through `faster-whisper` at `/stt/v1/`

TTS is intentionally excluded from Stage 1. Voice cloning and `/tts/v1/` wait for Stage 2.

## What is inside

- `Dockerfile`: multi-stage AIRI build plus the GPU runtime
- `app/`: authenticated OpenAI-compatible STT adapter
- `nginx.conf`: same-origin routing for AIRI, LLM, and STT
- `supervisord.conf`: process lifecycle for `nginx`, `llama-server`, and `uvicorn`
- `workload-stage1.template.yaml`: gcube manifest template for GPU `024`
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
LLAMA_CTX_SIZE=4096
LLAMA_N_GPU_LAYERS=99
LLAMA_PARALLEL=1
LOG_LEVEL=INFO
```

`API_KEY` must be shared by both `/llm/v1/` and `/stt/v1/`.
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

Render the private manifest first:

```powershell
$ApiKey = 'replace-with-a-real-random-value'
.\scripts\render-workload.ps1 -GhcrOwner 'vfxceo-ai' -ApiKey $ApiKey
```

Then register a new workload:

```powershell
gcube workload register --file .\workload-stage1.private.yaml
```

This template is pinned to:

- GPU code `024`
- `maxConnection: 20`
- Dropbox storage SER `98` mounted at `/mnt/dropbox`
- single public port `8080`

For gcube manifests, keep `repo: ghcr.io` and omit the registry prefix from `containerImage`. The rendered value should be `vfxceo-ai/exaone-yaho-airi:stage1`, not `ghcr.io/vfxceo-ai/exaone-yaho-airi:stage1`.

Use Dropbox only for small persistent files like future voice samples or exported config. Model caches stay on the workload-local disk under `/var/cache/airi`.
With the offline image layout, the EXAONE GGUF and STT assets are copied into `/models` at build time instead of being downloaded during container startup.

## Stage 1 limitations

- No `/tts/v1/` route
- No voice sample upload
- No voice cloning yet
- Future Stage 2 voice sample path: `/mnt/dropbox/gcube/AIRI/voices/yaho/`

## Image publishing

The GitHub Actions workflow pushes:

- `ghcr.io/<owner>/exaone-yaho-airi:stage1`
- `ghcr.io/<owner>/exaone-yaho-airi:<git-sha>`

GitHub Container Registry packages start as `private` on first publish. If you want gcube to pull anonymously, change the package visibility to `public` after the first successful push. If the package stays private, switch the manifest to credentialed pulls before registering the workload.

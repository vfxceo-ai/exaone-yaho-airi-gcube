# EXAONE-Yaho AIRI Stage 1

Stage 1 packages one RTX 5090 32 GB gcube workload that serves:

- AIRI Stage Web at `/`
- EXAONE-Yaho through `vLLM` at `/llm/v1/`
- Korean STT through `faster-whisper` at `/stt/v1/`

TTS is intentionally excluded from Stage 1. Voice cloning and `/tts/v1/` wait for Stage 2.

## What is inside

- `Dockerfile`: multi-stage AIRI build plus the GPU runtime
- `app/`: authenticated OpenAI-compatible STT adapter
- `nginx.conf`: same-origin routing for AIRI, LLM, and STT
- `supervisord.conf`: process lifecycle for `nginx`, `vllm`, and `uvicorn`
- `workload-stage1.template.yaml`: gcube manifest template for GPU `025`
- `scripts/render-workload.ps1`: renders a private manifest without committing secrets
- `config/exaone-yaho.character.json`: AIRI character card bundled with this Stage 1 package

## Local verification

Create a virtual environment, install test dependencies, and run the unit tests:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
$env:PYTHONPATH='.'
python -m pytest tests -v
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
STT_MODEL_ID=large-v3-turbo
STT_COMPUTE_TYPE=int8_float16
STT_LANGUAGE=ko
VLLM_GPU_MEMORY_UTILIZATION=0.52
VLLM_MAX_MODEL_LEN=4096
VLLM_MAX_NUM_SEQS=1
LOG_LEVEL=INFO
```

`API_KEY` must be shared by both `/llm/v1/` and `/stt/v1/`.

## AIRI provider values

After the workload is running, open the AIRI UI and set:

```text
Chat provider: OpenAI Compatible
Chat base URL: https://<gcube-service-url>/llm/v1/
Chat model: exaone-yaho

Transcription provider: OpenAI Compatible
Transcription base URL: https://<gcube-service-url>/stt/v1/
Transcription model: whisper-1

API key: the same deployment API_KEY
```

AIRI stores provider credentials in the browser, not in the container environment.

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

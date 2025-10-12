# PPTAgent Quick Start

This guide walks through the exact steps we used locally to go from a clean checkout to generating a presentation from `docs/pptagent.pdf`.

## 1. Prerequisites

- macOS / Linux shell
- Python 3.11+ (we tested with 3.12 inside conda)
- Node.js 18+ (ships with `npm`)
- A running MinerU API (or compatible adapter) reachable at `http://localhost:8000/file_parse`
- An OpenAI-compatible API key that can access the chosen models

## 2. Python environment

```bash
conda create -n pptagent python=3.12 -y
conda activate pptagent
pip install -e ".[full]"
# customised python-pptx build required by the project
pip install "git+https://github.com/Force1ess/python-pptx@219513d7d81a61961fc541578c1857d08b43aa2a"
```

The editable install pulls in all Python dependencies (`fastapi`, `aiohttp`, `oaib`, etc.).

## 3. Front-end dependencies

```bash
cd pptagent_ui
npm install
cd ..
```

The Vue CLI service (`vue-cli-service`) becomes available after this step.

## 4. Required environment variables

Export the variables in the same terminal session that will launch the backend:

```bash
export OPENAI_API_KEY="your_key"
export API_BASE="http://your_service_provider/v1"  # Optional, defaults to OpenAI's base URL
export LANGUAGE_MODEL="gpt-5-nano" # or any supported chat model
export VISION_MODEL="gpt-5-nano"
export MINERU_API="http://localhost:8000/file_parse"
# Optional: extend or override PYTHONPATH as needed
```

> If you want to test without a working LLM key, set `ALLOW_MISSING_LLM=1` before step 5 to start the backend in a degraded mode.

## 5. Start the backend

```bash
./run_backend.sh
```

The script now traps `Ctrl+C` and will tidy up the helper process automatically.

## 6. Start the front-end

In another terminal:

```bash
cd pptagent_ui
npm run serve
```

Open the URL reported by Vue CLI (usually `http://localhost:8080`).

## 7. Upload and generate

1. In the web UI, upload `docs/pptagent.pdf`.  
   Optional: upload a PPTX template (e.g. `runs/pptx/default_template/source.pptx`) if you want to reuse a custom layout.
2. Submit the form. The page keeps the WebSocket connection open and streams stage updates (`PPT Parsing`, `PDF Parsing`, etc.).
3. When the status reaches “Success!”, a download button appears. The generated file is also saved at:
   ```
   pptagent/runs/<task_id>/final.pptx
   ```

## 8. Troubleshooting

- **Port 9297 already in use** – simply press `Ctrl+C` in the backend terminal to shut down cleanly, then restart.
- **PDF parsing timeouts** – ensure your MinerU endpoint is reachable and returns within a few minutes. You can validate it manually:
  ```bash
  curl -s -o /tmp/check.zip -w "%{http_code}\n" \
    -F "files=@docs/pptagent.pdf" \
    -F "return_images=True" -F "response_format_zip=True" \
    "$MINERU_API"
  ```
- **Stale results** – delete cached runs (`rm -rf pptagent/runs`) before rerunning.

Following these steps reproduces the end‑to‑end pipeline we verified: backend + front-end running, PDF uploaded, and `final.pptx` generated successfully.

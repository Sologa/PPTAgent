#!/usr/bin/env bash
set -euo pipefail

# run_backend.sh
# A convenience script to prepare environment and run the backend server.
# Usage: ./run_backend.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
# If the user has environment variables (e.g., OPENAI_API_KEY) in their shell
# rc, source it first so those vars are available to the helper process.
if [ -f "$HOME/.zshrc" ]; then
	# shellcheck disable=SC1090
	source "$HOME/.zshrc" || true
fi

# Try to activate the conda environment if conda is present. This will make
# the correct `python` and exported env vars available to the helper.
if command -v conda >/dev/null 2>&1; then
	# Allow failure here (user may not want conda activated from script)
	conda activate pptagent || true
fi

# Resolve python after environment activation
PYTHON="${PYTHON:-$(which python || echo python)}"

LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

cleanup() {
	# terminate any background job we started (tee + helper)
	if [[ -n "${HELPER_PID:-}" ]]; then
		kill "$HELPER_PID" 2>/dev/null || true
		wait "$HELPER_PID" 2>/dev/null || true
	fi
}
trap cleanup INT TERM EXIT

echo "[run_backend] repo root: $REPO_ROOT"
echo "[run_backend] using python: $PYTHON"

# Export PYTHONPATH so uvicorn can import package modules in editable checkout
if [ -z "${PYTHONPATH+x}" ]; then
	export PYTHONPATH="$REPO_ROOT"
else
	export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"
fi

# Default endpoints / envs (can be overridden in your shell)
export MINERU_API="${MINERU_API:-http://localhost:8000/file_parse}"
export API_BASE="${API_BASE:-https://api.openai.com/v1}"

# IMPORTANT: Set your OpenAI API key in your shell environment
# For example: export OPENAI_API_KEY="sk-..."
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# default openai models
export LANGUAGE_MODEL=gpt-5
export VISION_MODEL=gpt-5


if [ -z "${OPENAI_API_KEY+x}" ]; then
	echo "[run_backend] WARNING: OPENAI_API_KEY is not set in the environment."
	echo "[run_backend] If you need LLM functionality, export OPENAI_API_KEY before running this script."
	echo "[run_backend] Continuing startup: some features may fail until the key is set."
fi

echo "[run_backend] invoking helper (will check deps and start uvicorn)..."
"$PYTHON" "$REPO_ROOT/tools/run_backend_helper.py" "$@" 2>&1 | tee "$LOG_DIR/backend_helper.log" &
HELPER_PID=$!
wait "$HELPER_PID"

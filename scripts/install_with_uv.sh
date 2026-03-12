#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -d .venv ]]; then
  uv venv .venv
fi

uv pip install --python .venv/bin/python -e .

echo "Install complete. Activate with: source .venv/bin/activate"
echo "Then run: qa-logger --help"

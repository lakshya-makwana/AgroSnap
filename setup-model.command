#!/bin/zsh
# AgroSnap: set up TensorFlow for the backend, compare the trained models, install the best one.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
LOG="$ROOT/ml/candidates/setup-model.log"
exec > >(tee "$LOG") 2>&1
echo "== AgroSnap model setup ($(date)) =="

# 1) Models + evaluation images are already unpacked in ml/candidates
cd "$ROOT/backend"

# 2) TensorFlow needs Python 3.12 (your Homebrew Python is 3.14, too new). uv fetches 3.12 without touching the system.
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
  echo "Installing uv (Python manager)..."; curl -LsSf https://astral.sh/uv/install.sh | sh
fi
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info[:2] > (3, 13))'; then
  [ -d .venv ] && mv .venv ".venv-old-$(date +%s)"
  uv venv --python 3.12 .venv
fi
echo "Installing backend + TensorFlow (first time takes a few minutes)..."
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-ml.txt -r requirements-dev.txt

# 3) Compare and install
.venv/bin/python "$ROOT/ml/candidates/eval_models.py"
echo ""
echo "DONE. Results are in ml/candidates/comparison.txt. You can close this window."

#!/bin/bash
# ============================================================================
# Run MANDATE Pipeline with Live LLM on Mac mini M4 Pro
# ============================================================================
#
# Prerequisites:
#   1. Ollama running: ollama serve
#   2. MANDATE models loaded: ./setup_mandate_llm.sh (from AEGIS root)
#   3. AEGIS venv: source .venv/bin/activate
#
# This script runs all 8 paper-claim scenarios through the pipeline with
# the production LLM config (per-role fine-tuned Qwen3 models).
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AEGIS_ROOT="$(cd "$SCRIPT_DIR/../../AEGIS" && pwd)"

echo "============================================"
echo "  MANDATE Live LLM Pipeline Run"
echo "  $(date)"
echo "============================================"

# Check Ollama is running
if ! curl -s --max-time 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama is not running at localhost:11434"
    echo "Start it with: ollama serve"
    exit 1
fi

echo "[OK] Ollama is running"

# Check models are loaded
MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "import json,sys; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null)
echo "[INFO] Available models:"
echo "$MODELS" | sed 's/^/  /'

# Check for mandate models
for role in intake interpreter decomp procedure binding validation; do
    if echo "$MODELS" | grep -q "mandate-$role"; then
        echo "[OK] mandate-$role found"
    else
        echo "[WARN] mandate-$role not found — will use base model or fallback"
    fi
done

# Activate venv
cd "$AEGIS_ROOT"
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    echo "[OK] AEGIS venv activated"
else
    echo "ERROR: AEGIS venv not found at $AEGIS_ROOT/.venv"
    exit 1
fi

# Run with production config
echo ""
echo "Running 8 scenarios with production LLM config..."
echo ""
python "$SCRIPT_DIR/run_with_production_config.py" 2>&1 | tee "$SCRIPT_DIR/mac_mini_run_output.txt"

echo ""
echo "============================================"
echo "  Run complete. Output saved to:"
echo "  $SCRIPT_DIR/mac_mini_run_output.txt"
echo "  $SCRIPT_DIR/outputs_production_config/"
echo "============================================"

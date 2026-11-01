#!/bin/sh
# Start the Forager app for one user-study session in its own runtime folder (see docs/user-study.md).
# Usage: eval/study_app.sh P1 clarification|free_text
# Paid calls go through the lab copy that holds the course key; set FORAGER_LAB_DIR to use another.
set -e
[ $# -eq 2 ] || { echo "usage: $0 P1 clarification|free_text"; exit 1; }
case "$2" in clarification|free_text) ;; *) echo "condition must be clarification or free_text"; exit 1;; esac
cd "$(dirname "$0")/.."
export FORAGER_RUNTIME_DIR="$PWD/runtime/study/$1/$2"
export FORAGER_LAB_DIR="${FORAGER_LAB_DIR:-$HOME/Desktop/Human-AI/forager-lab-own-key}"
mkdir -p "$FORAGER_RUNTIME_DIR"
echo "Runtime folder: $FORAGER_RUNTIME_DIR"
exec .venv/bin/streamlit run forager/app.py --server.port 8501 --browser.gatherUsageStats false

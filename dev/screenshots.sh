#!/bin/bash
# Refresh the README screenshots: anonymised demo from the reports Home Assistant made, then screenshots.
# Development only (needs this machine's reports, the dev venv, Node and Playwright).
#   dev/screenshots.sh [month]
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=${HIR_REPORTS:-/config/home_in_review}
PY=${HIR_PY:-/data/claude/hir-venv/bin/python}
NODE=${HIR_NODE:-/data/claude/tools/node-v24.21.0-linux-x64/bin/node}
export PLAYWRIGHT=${PLAYWRIGHT:-/config/dev/thus/frontend/maison/node_modules/playwright/index.mjs}
"$PY" dev/demo.py "$SRC"
"$NODE" dev/screenshots.mjs "$@"

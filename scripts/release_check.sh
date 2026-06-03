#!/usr/bin/env bash
set -euo pipefail
python -m pytest -q
python -m lookbook.cli demo /tmp/lookbook-demo
echo "Release check passed."

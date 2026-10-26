#!/usr/bin/env bash
# 画角調整を 45 秒ごとに撮る。PC から SSH できないときはラズパイ上で実行する。

set -euo pipefail
cd "$(dirname "$0")/.."
INTERVAL="${FRAMING_INTERVAL_SEC:-45}"

# shellcheck source=/dev/null
source venv/bin/activate

while true; do
  date -Is
  python camera_control.py --width 640 --height 480 -o latest_change.jpg || true
  sleep "$INTERVAL"
done

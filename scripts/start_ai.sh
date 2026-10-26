#!/usr/bin/env bash
# Soracom (wwan0) 経由で MQTT 送信する ai.py をバックグラウンド起動する。
# 空のエレベーターで実行する。Wi-Fi が無くてもラズパイ上で動く。

set -euo pipefail
cd "$(dirname "$0")/.."

if ip route show default 2>/dev/null | head -n1 | grep -qv wwan0; then
  echo "注意: 既定経路が wwan0 ではありません。ip route を確認してください。"
fi

systemctl is-active elevator-ai.service 2>/dev/null | grep -q active &&
  sudo systemctl stop elevator-ai.service || true

pkill -f '[/]ai.py' 2>/dev/null || true
sleep 1

# shellcheck source=/dev/null
source venv/bin/activate
nohup python ai.py >> /tmp/ai.log 2>&1 &
echo "ai.py を起動しました (PID $!). ログ: tail -f /tmp/ai.log"

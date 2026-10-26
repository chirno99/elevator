#!/usr/bin/env bash
# 手動起動した ai.py と画角ループを止める。

pkill -f 'scripts/framing_loop.sh' 2>/dev/null || true
pkill -f '[/]ai.py' 2>/dev/null || true
pkill -f '[/]camera_control.py' 2>/dev/null || true
echo "停止しました。systemctl の elevator-ai.service は触りません。"

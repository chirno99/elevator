README.md
Markdown
# Elevator Tracker System

エレベーター内の様子をAI（YOLOv5）で解析し、リアルタイムで物体の検知・追跡、およびその結果をMQTTで配信するシステムです。

## プロジェクト構成

- `ai.py`: 推論エンジンおよびメインロジック。
- `Elevator_Trackerv5.pt`: 学習済みのYOLOv5カスタムモデルファイル。
- `mqtt_pub.py`: 検知したデータを外部システム（サーバー、ダッシュボード等）へ送信するためのMQTTパブリッシャー。
- `config.py`: カメラのURL、MQTTサーバーの設定、閾値などの設定管理。
- `.env.example`: 環境変数のテンプレート。

## 特徴

- **カスタムAIモデル**: エレベーター内の特定の状況（混雑度、不審な挙動など）を検知するために最適化されたモデルを使用。
- **リアルタイム通信**: MQTTプロトコルを使用し、低遅延で検知結果を通知。
- **柔軟な設定**: `config.py` または `.env` ファイルにより、環境ごとの設定変更が容易。

## セットアップ

### 1. 依存関係のインストール

Python 3.8以上を推奨します。

```bash
pip install -r requirements.txt
# (注: リポジトリにrequirements.txtがない場合は、torch, opencv-python, paho-mqtt 等を個別にインストールしてください)
2. 環境設定
.env.example をコピーして .env を作成し、必要な情報を記入します。

Bash
cp .env.example .env
3. 実行
Bash
python ai.py
言語
Python 100%

更新履歴
2026/02/19: 最新アップデート（リポジトリ情報に基づく）


---

### 補足
リポジトリ内に詳細なドキュメントがなかったため、ファイル構成から一般的な構成を推測して作成しています。
- **`Elevator_Trackerv5.pt`** はPyTorchの重みファイルであるため、実行には `torch` および `ultralytics` (YOLO) のライブラリが必要になる可能性が高いです。
- **MQTT**を使用しているため、動作確認には Mosquitto などのブローカーが必要です。
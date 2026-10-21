# Elevator Tracker System

エレベーターの階・矢印・人数をカメラで推定し、MQTT で配信するエッジ側のプログラムです。画像の収集と学習は別リポジトリ [current-v3](https://github.com/BRUCE-R-YOUNG/current-v3) です。

## ファイル

| ファイル | 役割 |
|---|---|
| `ai.py` | 推論ループ。検出の直後に観測時刻を付けて MQTT へ渡す |
| `mqtt_pub.py` | 9 バイト payload の組み立てと送信 |
| `config.py` | `.env` の読み込み |
| `camera_control.py` | 画角確認。1 枚撮って中央の十字と階表示の枠を描き、`latest_change.jpg` を出す |
| `best.pt` | 階・矢印モデル（2026-10-14 から使用） |
| `elevatorTrackerv7.pt` ほか | 以前の階・矢印モデル。戻すとき用に残している |
| `.env.example` | 環境変数のひな型。本番の値は `.env`（Git には入れない） |

人数モデル `yolo26n.pt` は公式の YOLO 重みです。同じフォルダに置きます。リポジトリには同梱していません。

## MQTT

| 項目 | 値 |
|---|---|
| ブローカー | `broker.hivemq.com:1883`（TLS なし、匿名） |
| トピック | `elevator/status` |
| QoS | 1 |
| 形式 | リトルエンディアン `<HbbbI`、9 バイト |

| フィールド | 型 | 意味 |
|---|---|---|
| 号機 | `H` | 1〜99。`E001`=1、`E002`=2、`E003`=3 |
| 階 | `b` | 1〜32。0 階と範囲外は送らない |
| 人数 | `b` | そのフレームで検出した人数 |
| 方向 | `b` | 0=停止、1=上、2=下。不明は 0 |
| 時刻 | `I` | 観測を確定したときの UTC Unix 秒 |

同じ号機で階・人数・方向が変わらないあいだは送りません。未接続のときも送りません。

## 人数の数え方

いまの人数は、1 フレームの中で検出した person の数です。ラインを跨いだ IN/OUT の累積カウントはまだありません。`camera_control.py` の白い線は画角を合わせるための描画です。

## セットアップ

Python 3.10 以上。

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Raspberry Pi
# source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` のホスト名は `MQTT_HOST` です。`MQTT_BROKER` という名前は `config.py` が読みません。`DEVICE_ID` はこの端末では `E003` です。

```bash
python ai.py
python camera_control.py
```

必要なときだけ起動します。`elevator-ai.service` での常時起動はしていません。再起動すると手動起動のプロセスは戻りません。

## 更新履歴

- 2026-10-21: 受信仕様に合わせ、payload を 9 バイト `<HbbbI` にした。トピックは `elevator/status`。階 0 と 1〜32 の外、号機 1〜99 の外は送らない。階・矢印モデルを `best.pt` にした
- 2026-06-03: 画角確認の `camera_control.py` を追加
- 2026-02-19: リポジトリ作成

# Elevator Tracker System

エレベーターの階・矢印・人数をカメラで推定し、MQTT で配信するエッジ側のプログラムです。画像の収集と学習は別リポジトリ [current-v3](https://github.com/BRUCE-R-YOUNG/current-v3) です。

## ファイル

| ファイル | 役割 |
|---|---|
| `ai.py` | 推論ループ。検出の直後に観測時刻を付けて MQTT へ渡す |
| `mqtt_pub.py` | 9 バイト payload の組み立てと送信 |
| `config.py` | `.env` の読み込み |
| `people_counter.py` | 人数ラインを跨いだ IN/OUT から乗車人数を出す |
| `camera_control.py` | 画角調整。640x480 で1枚撮り、緑枠と人数ラインを `latest_change.jpg` に描く |
| `camera_framing.yaml` | 承認済みの階表示枠と人数ライン（幅・高さに対する比率） |
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

MQTT の人数は、そのフレームに映っている人数ではありません。`camera_framing.yaml` の `count_line` を人物の中心が跨いだ回数です。

- 乗車（IN）: 扉側からカメラ側へ跨ぐ（`enter_direction: toward_camera`）
- 降車（OUT）: カメラ側から扉側へ跨ぐ
- 送る人数: IN − OUT。0未満にはせず、127を超える分は切る

`ai.py` は空のエレベーターで起動します。起動前から乗っている人は数に入りません。IN と OUT が逆だったら `enter_direction` を `toward_door` にします。

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

`camera_control.py` は本番と同じ 640x480 で撮ります。`latest_change.jpg` で、左右の黒い階表示が緑枠の中に入っているかを見ます。入っていれば、赤い人数ラインも `camera_framing.yaml` の位置です。枠から外れていればカメラの向きを直して、もう一度実行します。

必要なときだけ起動します。`elevator-ai.service` での常時起動はしていません。再起動すると手動起動のプロセスは戻りません。

## Soracom のみ（学校 Wi-Fi に届かない場所）

ラズパイの `wwan0` が Soracom ドングルです。`ip route` で `default` が `wwan0` なら、MQTT は Soracom 経由で外に出ます。PC からラズパイへ SSH するには同じ Wi-Fi が要るため、**現地ではラズパイのターミナルで**起動します（Tailscale は使いません）。

```bash
cd /home/pi/elevator
chmod +x scripts/*.sh
# 推論（空のかごで）
./scripts/start_ai.sh
# 画角を 45 秒ごと（別窓。止めるときは ./scripts/stop_edge.sh）
nohup ./scripts/framing_loop.sh >> /tmp/framing_loop.log 2>&1 &
```

画角の確認画像は `/home/pi/elevator/latest_change.jpg`。ログは `/tmp/ai.log` と `/tmp/framing_loop.log`。

## 更新履歴

- 2026-10-25: 人数を検知ライン跨ぎの乗車人数（IN − OUT）にして `ai.py` に接続した
- 2026-10-23: 画角調整を承認済みの青枠・赤線に切り替え、撮影を 640x480 にした
- 2026-10-21: 受信仕様に合わせ、payload を 9 バイト `<HbbbI` にした。トピックは `elevator/status`。階 0 と 1〜32 の外、号機 1〜99 の外は送らない。階・矢印モデルを `best.pt` にした
- 2026-06-03: 画角確認の `camera_control.py` を追加
- 2026-02-19: リポジトリ作成

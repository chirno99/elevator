import paho.mqtt.client as mqtt
import json
import time
import random
import config
import struct

# 接続時のコールバック関数
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"MQTTブローカーに接続成功: {config.settings.MQTT_HOST}:{config.settings.MQTT_PORT}")
    else:
        print(f"MQTTブローカーに接続失敗、エラーコード: {rc}")

# メッセージ送信用のクライアントを初期化
def connect_mqtt_publisher():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="elevator_publisher")
    client.on_connect = on_connect
    client.connect(config.settings.MQTT_HOST, config.settings.MQTT_PORT, keepalive=60) # keepaliveは接続維持の時間（秒）
    client.loop_start() # バックグラウンドでネットワークループを開始
    return client

# MQTTメッセージを公開する関数
def publish_elevator_status(client, topic, elevator_id, current_floor, occupancy, direction):
    # 状態保存用の辞書を初期化（初回のみ）
    if not hasattr(publish_elevator_status, "last_sent"):
        publish_elevator_status.last_sent = {}

    # 1. データの安全な変換
    # .upper() を付けて、"down" でも "DOWN" でも一致するようにします
    direction_map = {"STOP": 0, "UP": 1, "DOWN": 2}

    # direction が文字列なら大文字に変換、そうでなければそのまま扱う
    d_key = direction.upper() if isinstance(direction, str) else direction
    direction_val = direction_map.get(d_key, 0)

    try:
        # IDから数字を抽出
        id_num = int(''.join(filter(str.isdigit, elevator_id)))
        # current_floor と occupancy も確実に整数(int)に変換する
        c_floor = int(current_floor)
        occ = int(occupancy)
    except (ValueError, TypeError):
        # 変換に失敗した場合は 0 をデフォルトにする
        id_num = 0
        c_floor = 0
        occ = 0

    # 2. 変化チェック
    current_status = (c_floor, occ, direction_val)
    if publish_elevator_status.last_sent.get(elevator_id) == current_status:
        return

    # 3. 未接続状態での送信防止
    if not client.is_connected():
        return

    # 4. バイナリパッキング
    # すべての変数を確実に int にした状態で渡します
    binary_payload = struct.pack('<Hbbb', id_num, c_floor, occ, direction_val)

    # 送信処理 (mqtt_pub.py 内に client.publish があるはずです)
    client.publish(topic, binary_payload)

    # 状態を保存
    publish_elevator_status.last_sent[elevator_id] = current_status

    # 5. 送信
    result = client.publish(topic, binary_payload, qos=1)


    # 6. 送信結果の確認とログ
    if result.rc == 0:
        publish_elevator_status.last_sent[elevator_id] = current_status
        hex_payload = binary_payload.hex().upper()
        print(f"--- [変化検知] MQTT送信 ---")
        # print(f"ID: {elevator_id}, Floor: {current_floor}, Occupancy: {occupancy}, Dir: {direction}")
        print(f"Hex: {hex_payload}")
    else:
        print(f"MQTT送信エラー: {result.rc}")
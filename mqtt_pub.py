import struct
import time

import paho.mqtt.client as mqtt

import config

PAYLOAD_FORMAT = "<HbbbI"
PAYLOAD_SIZE = struct.calcsize(PAYLOAD_FORMAT)
ELEVATOR_NUMERIC_ID = {"E001": 1, "E002": 2, "E003": 3}
DIRECTION_MAP = {"STOP": 0, "UP": 1, "DOWN": 2}


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(
            f"MQTTブローカーに接続成功: {config.settings.MQTT_HOST}:{config.settings.MQTT_PORT}"
        )
    else:
        print(f"MQTTブローカーに接続失敗、エラーコード: {rc}")


def connect_mqtt_publisher():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="elevator_publisher")
    client.on_connect = on_connect
    client.connect(config.settings.MQTT_HOST, config.settings.MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def _elevator_id_to_uint16(elevator_id) -> int:
    key = str(elevator_id).upper()
    if key in ELEVATOR_NUMERIC_ID:
        return ELEVATOR_NUMERIC_ID[key]
    digits = "".join(ch for ch in key if ch.isdigit())
    if digits:
        return int(digits)
    return 0


def _direction_to_byte(direction) -> int:
    if isinstance(direction, str):
        return DIRECTION_MAP.get(direction.upper(), 0)
    if isinstance(direction, (int, float)):
        value = int(direction)
        if value in (0, 1, 2):
            return value
    return 0


def build_elevator_payload(elevator_id, current_floor, occupancy, direction, observed_at: int) -> bytes:
    id_num = _elevator_id_to_uint16(elevator_id)
    direction_val = _direction_to_byte(direction)
    try:
        c_floor = int(current_floor)
        occ = int(occupancy)
    except (TypeError, ValueError):
        c_floor = 0
        occ = 0
    observed = int(observed_at)
    payload = struct.pack(PAYLOAD_FORMAT, id_num, c_floor, occ, direction_val, observed)
    if len(payload) != PAYLOAD_SIZE:
        raise ValueError(f"MQTT payload must be {PAYLOAD_SIZE} bytes, got {len(payload)}")
    return payload


def publish_elevator_status(
    client,
    topic,
    elevator_id,
    current_floor,
    occupancy,
    direction,
    observed_at: int | None = None,
):
    if not hasattr(publish_elevator_status, "last_sent"):
        publish_elevator_status.last_sent = {}

    direction_val = _direction_to_byte(direction)
    try:
        c_floor = int(current_floor)
        occ = int(occupancy)
    except (TypeError, ValueError):
        c_floor = 0
        occ = 0

    # Server keeps floors 1-32 only. Floor 0 and anything outside that range is discarded.
    if not 1 <= c_floor <= 32:
        return
    id_num = _elevator_id_to_uint16(elevator_id)
    if not 1 <= id_num <= 99:
        return

    current_status = (c_floor, occ, direction_val)
    if publish_elevator_status.last_sent.get(elevator_id) == current_status:
        return

    if not client.is_connected():
        return

    if observed_at is None:
        observed_at = int(time.time())
    binary_payload = build_elevator_payload(
        elevator_id, current_floor, occupancy, direction, observed_at
    )

    result = client.publish(topic, binary_payload, qos=1)
    if result.rc == 0:
        publish_elevator_status.last_sent[elevator_id] = current_status
        print("--- [変化検知] MQTT送信 ---")
        print(f"bytes={len(binary_payload)} hex={binary_payload.hex().upper()}")
    else:
        print(f"MQTT送信エラー: {result.rc}")

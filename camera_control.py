"""
画角調整。camera_framing.yaml の緑枠と人数ラインを1枚に重ねる。

緑枠（LEFT / RIGHT DISP）の中に黒い階表示が入るようにカメラを合わせる。
枠が合えば、同じ設定の赤い COUNT LINE も所定の位置に来る。

  python camera_control.py
  python camera_control.py --image path/to/frame.jpg -o preview.jpg

撮影サイズの初期値は本番 ai.py と同じ 640x480。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import yaml

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "camera_framing.yaml"


def load_framing(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def scale_point(x_norm: float, y_norm: float, w: int, h: int) -> tuple[int, int]:
    return int(round(x_norm * w)), int(round(y_norm * h))


def scale_box(box: dict, w: int, h: int) -> tuple[tuple[int, int], tuple[int, int]]:
    return (
        scale_point(box["x1"], box["y1"], w, h),
        scale_point(box["x2"], box["y2"], w, h),
    )


def draw_framing_overlay(frame, framing: dict) -> None:
    h, w = frame.shape[:2]

    for key, label in (("left_display", "LEFT DISP"), ("right_display", "RIGHT DISP")):
        start, end = scale_box(framing[key], w, h)
        cv2.rectangle(frame, start, end, (0, 255, 0), 2)
        cv2.putText(
            frame,
            label,
            (start[0], max(20, start[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    line = framing["count_line"]
    p1 = scale_point(line["x1"], line["y1"], w, h)
    p2 = scale_point(line["x2"], line["y2"], w, h)
    cv2.line(frame, p1, p2, (0, 0, 255), 3, cv2.LINE_AA)
    cv2.putText(
        frame,
        "COUNT LINE",
        (p1[0], max(20, min(p1[1], p2[1]) - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        1,
        cv2.LINE_AA,
    )


def capture_frame(camera_id: int, width: int, height: int):
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print("エラー: カメラを開けませんでした。")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("エラー: 画像取得に失敗しました。")
        sys.exit(1)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="画角調整（黒い階表示の枠と人数ライン）")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--image", type=Path, help="既存画像に重ねる（カメラは使わない）")
    parser.add_argument("-o", "--output", type=Path, default=Path("latest_change.jpg"))
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()

    framing = load_framing(args.config)

    if args.image:
        frame = cv2.imread(str(args.image))
        if frame is None:
            print(f"エラー: 画像を読めません: {args.image}")
            sys.exit(1)
    else:
        frame = capture_frame(args.camera, args.width, args.height)

    draw_framing_overlay(frame, framing)
    cv2.imwrite(str(args.output), frame)
    h, w = frame.shape[:2]
    left = scale_box(framing["left_display"], w, h)
    right = scale_box(framing["right_display"], w, h)
    line = framing["count_line"]
    p1 = scale_point(line["x1"], line["y1"], w, h)
    p2 = scale_point(line["x2"], line["y2"], w, h)
    print(f"保存: {args.output.resolve()} ({w}x{h})")
    print(f"LEFT DISP  {left[0]} - {left[1]}")
    print(f"RIGHT DISP {right[0]} - {right[1]}")
    print(f"COUNT LINE {p1} - {p2}")
    print("黒い階表示が左右の緑枠に入っていれば、この画角です。")


if __name__ == "__main__":
    main()

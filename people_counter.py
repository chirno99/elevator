"""人数検知ラインを跨いだ乗車人数。

車内カメラが扉を見ている前提では、画面の奥（線より上）が扉側、
手前（線より下）がカメラ側。扉側からカメラ側へ跨ぐと乗車、逆で降車。
乗車人数は IN − OUT（0未満にはしない）。
"""

from __future__ import annotations

from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "camera_framing.yaml"


class LineOccupancyCounter:
    def __init__(
        self,
        count_line: dict,
        enter_direction: str = "toward_camera",
        deadband: float = 0.02,
        x_margin: float = 0.04,
        stale_frames: int = 45,
    ):
        self.x1 = float(count_line["x1"])
        self.y1 = float(count_line["y1"])
        self.x2 = float(count_line["x2"])
        self.y2 = float(count_line["y2"])
        if enter_direction not in ("toward_camera", "toward_door"):
            raise ValueError(f"enter_direction が不明です: {enter_direction}")
        self.enter_direction = enter_direction
        self.deadband = deadband
        self.x_margin = x_margin
        self.stale_frames = stale_frames
        self._side: dict[int, int] = {}
        self._seen: dict[int, int] = {}
        self._frame = 0
        self.entered = 0
        self.exited = 0

    @classmethod
    def from_yaml(cls, config_path: Path = DEFAULT_CONFIG) -> "LineOccupancyCounter":
        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(
            data["count_line"],
            enter_direction=data.get("enter_direction", "toward_camera"),
        )

    def _signed_distance(self, x: float, y: float) -> float:
        cross = (self.x2 - self.x1) * (y - self.y1) - (self.y2 - self.y1) * (x - self.x1)
        length = ((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2) ** 0.5
        if length == 0:
            return 0.0
        return cross / length

    def side_of(self, x: float, y: float) -> int:
        """+1 はカメラ側（手前）、-1 は扉側（奥）、0 は線のすぐ近く。"""
        distance = self._signed_distance(x, y)
        if distance > self.deadband:
            return 1
        if distance < -self.deadband:
            return -1
        return 0

    def _on_span(self, x: float) -> bool:
        lo, hi = sorted((self.x1, self.x2))
        return (lo - self.x_margin) <= x <= (hi + self.x_margin)

    @property
    def occupancy(self) -> int:
        # MQTT の人数は符号付き1バイト。127を超えると送れない。
        return min(127, max(0, self.entered - self.exited))

    def update(self, centers: list[tuple[float, float]], track_ids: list[int]) -> dict:
        self._frame += 1
        events: list[tuple[str, int]] = []
        for (x, y), track_id in zip(centers, track_ids):
            track_id = int(track_id)
            self._seen[track_id] = self._frame
            side = self.side_of(x, y)
            if side == 0:
                continue
            previous = self._side.get(track_id)
            self._side[track_id] = side
            if previous is None or previous == side or not self._on_span(x):
                continue
            entered_now = self._is_enter(previous, side)
            if entered_now:
                self.entered += 1
                events.append(("in", track_id))
            else:
                self.exited += 1
                events.append(("out", track_id))

        stale = [track_id for track_id, frame in self._seen.items() if self._frame - frame > self.stale_frames]
        for track_id in stale:
            self._seen.pop(track_id, None)
            self._side.pop(track_id, None)

        return {
            "occupancy": self.occupancy,
            "entered": self.entered,
            "exited": self.exited,
            "events": events,
        }

    def _is_enter(self, previous: int, side: int) -> bool:
        toward_camera = previous == -1 and side == 1
        if self.enter_direction == "toward_camera":
            return toward_camera
        return not toward_camera


def _self_check() -> None:
    line = {"x1": 0.35, "y1": 0.6817, "x2": 0.7734, "y2": 0.6435}
    counter = LineOccupancyCounter(line, enter_direction="toward_camera")
    assert counter.side_of(0.55, 0.90) == 1
    assert counter.side_of(0.55, 0.30) == -1
    assert counter.side_of(0.55, 0.66) == 0

    # 扉側から手前へ。乗車。
    counter.update([(0.55, 0.30)], [1])
    result = counter.update([(0.55, 0.90)], [1])
    assert result["occupancy"] == 1 and result["entered"] == 1, result

    # 手前から扉側へ。降車。
    result = counter.update([(0.55, 0.30)], [1])
    assert result["occupancy"] == 0 and result["exited"] == 1, result

    # 扉の幅の外では数えない。
    counter.update([(0.05, 0.30)], [2])
    result = counter.update([(0.05, 0.90)], [2])
    assert result["entered"] == 1 and result["events"] == [], result

    flipped = LineOccupancyCounter(line, enter_direction="toward_door")
    flipped.update([(0.55, 0.90)], [3])
    result = flipped.update([(0.55, 0.30)], [3])
    assert result["occupancy"] == 1 and result["entered"] == 1, result
    print("people_counter self-check ok")


if __name__ == "__main__":
    _self_check()

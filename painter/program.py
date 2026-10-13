"""PaintProgram: the intermediate representation shared by the simulator and machine backends.

Coordinates in strokes are canvas millimetres (origin = canvas top-left, y down).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Union


@dataclass
class StrokePoint:
    x: float
    y: float
    pressure: float  # 0 (touching) .. 1 (full press)
    angle: float  # brush rotation in degrees (flat brush faces along this direction)
    speed: float  # mm/s


@dataclass
class Stroke:
    brush_id: str
    color_id: int
    layer: int
    points: list[StrokePoint]

    def length(self) -> float:
        total = 0.0
        for a, b in zip(self.points, self.points[1:]):
            total += ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
        return total


@dataclass
class ToolChange:
    brush_id: str
    type: str = "tool_change"


@dataclass
class Dip:
    color_id: int
    amount: float
    type: str = "dip"


@dataclass
class Wash:
    type: str = "wash"


@dataclass
class Wipe:
    type: str = "wipe"


@dataclass
class Paint:
    stroke: Stroke
    type: str = "paint"


@dataclass
class Pause:
    reason: str
    color_id: int | None = None
    type: str = "pause"


Action = Union[ToolChange, Dip, Wash, Wipe, Paint, Pause]


@dataclass
class PaletteColor:
    id: int
    rgb: tuple[int, int, int]
    coverage: float  # fraction of canvas area


@dataclass
class PaintProgram:
    canvas_size: tuple[float, float]  # (width, height) mm
    palette: list[PaletteColor]
    actions: list[Action] = field(default_factory=list)
    source_image: str | None = None

    def strokes(self) -> list[Stroke]:
        return [a.stroke for a in self.actions if isinstance(a, Paint)]

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")

    @classmethod
    def from_dict(cls, d: dict) -> "PaintProgram":
        return cls(
            canvas_size=tuple(d["canvas_size"]),
            palette=[PaletteColor(c["id"], tuple(c["rgb"]), c["coverage"]) for c in d["palette"]],
            actions=[_action_from_dict(a) for a in d["actions"]],
            source_image=d.get("source_image"),
        )

    @classmethod
    def load(cls, path: str | Path) -> "PaintProgram":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _action_from_dict(d: dict) -> Action:
    t = d["type"]
    if t == "tool_change":
        return ToolChange(d["brush_id"])
    if t == "dip":
        return Dip(d["color_id"], d["amount"])
    if t == "wash":
        return Wash()
    if t == "wipe":
        return Wipe()
    if t == "pause":
        return Pause(d["reason"], d.get("color_id"))
    if t == "paint":
        s = d["stroke"]
        return Paint(Stroke(s["brush_id"], s["color_id"], s["layer"], [StrokePoint(**p) for p in s["points"]]))
    raise ValueError(f"unknown action type: {t}")

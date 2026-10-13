"""Paint bookkeeping: how much paint the brush carries and how much is left in each palette slot."""

from __future__ import annotations

from dataclasses import dataclass, field

from painter.config import Brush
from painter.program import Stroke


def stroke_paint_cost(stroke: Stroke) -> float:
    """Brush load (in mm of full-pressure stroke) used by a stroke. Light pressure lays down less paint."""
    cost = 0.0
    for a, b in zip(stroke.points, stroke.points[1:]):
        seg = ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
        cost += seg * (0.3 + 0.7 * (a.pressure + b.pressure) / 2)
    return cost


@dataclass
class BrushLoad:
    brush: Brush
    color_id: int | None = None  # paint currently on the bristles (None = clean)
    remaining: float = 0.0  # load left, same unit as Brush.capacity

    def dip(self, color_id: int) -> None:
        self.color_id = color_id
        self.remaining = self.brush.capacity

    def clean(self) -> None:
        self.color_id = None
        self.remaining = 0.0

    def fraction(self) -> float:
        return max(self.remaining / self.brush.capacity, 0.0)


@dataclass
class PaletteStock:
    capacity: float
    threshold: float
    levels: dict[int, float] = field(default_factory=dict)
    used: dict[int, float] = field(default_factory=dict)

    def take(self, color_id: int, amount: float) -> None:
        self.levels[color_id] = self.level(color_id) - amount
        self.used[color_id] = self.used.get(color_id, 0.0) + amount

    def level(self, color_id: int) -> float:
        return self.levels.get(color_id, self.capacity)

    def needs_refill(self, color_id: int, amount: float) -> bool:
        return self.level(color_id) - amount < self.threshold

    def refill(self, color_id: int) -> None:
        self.levels[color_id] = self.capacity

"""Process planning: order strokes and insert tool changes, washing, dipping and refill pauses.

Rules
- Layers are painted coarse -> fine (one brush per layer), as a painter blocks in before adding detail.
- Within a layer strokes are grouped by color, dark -> light, so each color needs only one wash.
- Before a different color touches the brush: Wash (oil jar) -> Wipe (rag) -> Dip (new color).
- A brush is washed and wiped before it is put back in the rack.
- When the brush runs out of paint it is re-dipped in the same color (no wash).
- When a palette slot drops below the refill threshold, the machine pauses for a human refill.
"""

from __future__ import annotations

import numpy as np

from painter.config import MachineConfig
from painter.planner.paint_model import BrushLoad, PaletteStock, stroke_paint_cost
from painter.program import Action, Dip, Paint, Pause, Stroke, ToolChange, Wash, Wipe


def order_by_travel(strokes: list[Stroke]) -> list[Stroke]:
    """Greedy nearest-neighbour ordering (end of one stroke -> start of the next) to cut travel time."""
    if len(strokes) < 2:
        return list(strokes)
    starts = np.array([[s.points[0].x, s.points[0].y] for s in strokes])
    remaining = np.ones(len(strokes), bool)
    i = 0
    order = [0]
    remaining[0] = False
    for _ in range(len(strokes) - 1):
        end = np.array([strokes[i].points[-1].x, strokes[i].points[-1].y])
        d = np.where(remaining, ((starts - end) ** 2).sum(1), np.inf)
        i = int(d.argmin())
        order.append(i)
        remaining[i] = False
    return [strokes[k] for k in order]


def plan(strokes: list[Stroke], config: MachineConfig) -> list[Action]:
    brush_order = {b.id: i for i, b in enumerate(config.brushes)}
    groups: dict[tuple[int, str, int], list[Stroke]] = {}
    for s in strokes:
        groups.setdefault((s.layer, s.brush_id, s.color_id), []).append(s)
    keys = sorted(groups, key=lambda k: (k[0], brush_order[k[1]], k[2]))

    stock = PaletteStock(config.palette.slot_capacity, config.palette.refill_threshold)
    actions: list[Action] = []
    load: BrushLoad | None = None

    def wash_and_wipe(load: BrushLoad) -> None:
        actions.append(Wash())
        actions.append(Wipe())
        load.clean()

    def dip(load: BrushLoad, color_id: int) -> None:
        amount = load.brush.paint_per_dip
        if stock.needs_refill(color_id, amount):
            actions.append(Pause(f"refill palette slot {color_id}", color_id))
            stock.refill(color_id)
        stock.take(color_id, amount)
        actions.append(Dip(color_id, amount))
        load.dip(color_id)

    for layer, brush_id, color_id in keys:
        if load is None or load.brush.id != brush_id:
            if load is not None and load.color_id is not None:
                wash_and_wipe(load)
            actions.append(ToolChange(brush_id))
            load = BrushLoad(config.brush(brush_id))
        if load.color_id is not None and load.color_id != color_id:
            wash_and_wipe(load)
        for stroke in order_by_travel(groups[(layer, brush_id, color_id)]):
            cost = stroke_paint_cost(stroke)
            if load.color_id != color_id or load.remaining < min(cost, load.brush.capacity):
                dip(load, color_id)
            actions.append(Paint(stroke))
            load.remaining -= cost

    if load is not None and load.color_id is not None:
        wash_and_wipe(load)
    return actions


def paint_usage(actions: list[Action]) -> dict[int, float]:
    used: dict[int, float] = {}
    for a in actions:
        if isinstance(a, Dip):
            used[a.color_id] = used.get(a.color_id, 0.0) + a.amount
    return used

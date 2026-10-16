"""A stand-in for the physical canvas in simulation.

The planner's brush model is never exactly right on a real machine. The simulated world paints with deliberately
different physics so that the closed loop has something to correct:
- bristles splay: strokes come out wider than modeled,
- paint is thinner / brushes hold less than modeled: lower coverage, the brush runs dry sooner,
- the gantry is not perfectly repeatable: each stroke lands slightly offset,
- the human mixes the palette colors by eye: every slot is a little off the target color.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from painter.config import MachineConfig
from painter.program import PaintProgram, Stroke, StrokePoint
from painter.sim.renderer import Renderer


@dataclass
class RealityParams:
    width_scale: float = 1.15
    opacity: float = 0.75
    capacity_scale: float = 0.8
    position_noise_mm: float = 0.6  # per-stroke offset (sigma)
    mix_error_rgb: float = 6.0  # per-slot color error (sigma, 0-255 per channel)
    seed: int = 1


class SimWorld(Renderer):
    def __init__(self, program: PaintProgram, config: MachineConfig, px_per_mm: float = 2.0,
                 reality: RealityParams = RealityParams()):
        world_config = config.model_copy(deep=True)
        for b in world_config.brushes:
            b.width *= reality.width_scale
            b.capacity *= reality.capacity_scale
        super().__init__(program, world_config, px_per_mm, seed=reality.seed)
        self.reality = reality
        self.opacity = reality.opacity
        self.world_rng = np.random.default_rng(reality.seed + 1000)
        self.palette = {k: np.clip(v + self.world_rng.normal(0, reality.mix_error_rgb, 3), 0, 255).astype(np.float32)
                        for k, v in self.palette.items()}

    def render_stroke(self, stroke: Stroke) -> None:
        dx, dy = self.world_rng.normal(0, self.reality.position_noise_mm, 2)
        moved = Stroke(stroke.brush_id, stroke.color_id, stroke.layer,
                       [StrokePoint(p.x + dx, p.y + dy, p.pressure, p.angle, p.speed) for p in stroke.points])
        super().render_stroke(moved)

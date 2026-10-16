"""Virtual canvas: renders strokes with a simple physical brush model.

- Footprint: a flat brush is a thin rotated ellipse across the direction of travel, a round brush a circle.
  Footprint size grows with pressure.
- Opacity follows the paint load: a freshly dipped brush covers well, a nearly empty one drags and shows the canvas.
- Bristle streaks: a 1-D noise pattern across the stroke modulates coverage; with little paint left it breaks up
  into "dry brush" gaps.
- Paint mixes wet-on-wet with what is already on the canvas (alpha blending).
"""

from __future__ import annotations

import cv2
import numpy as np

from painter.config import MachineConfig
from painter.program import Dip, Paint, PaintProgram, Stroke, Wash
from painter.planner.paint_model import stroke_paint_cost


class Renderer:
    def __init__(self, program: PaintProgram, config: MachineConfig, px_per_mm: float = 2.0, seed: int = 0):
        self.config = config
        self.px_per_mm = px_per_mm
        w, h = program.canvas_size
        self.canvas = np.full((int(round(h * px_per_mm)), int(round(w * px_per_mm)), 3), 255.0, np.float32)
        self.palette = {c.id: np.array(c.rgb, np.float32) for c in program.palette}
        self.rng = np.random.default_rng(seed)
        self.load_fraction = 0.0
        self.opacity = 1.0  # coverage scale (the simulated "real" world uses < 1 for thinner paint than modeled)

    def apply(self, action) -> None:
        if isinstance(action, Dip):
            self.load_fraction = 1.0
        elif isinstance(action, Wash):
            self.load_fraction = 0.0
        elif isinstance(action, Paint):
            self.render_stroke(action.stroke)

    def render_stroke(self, stroke: Stroke) -> None:
        brush = self.config.brush(stroke.brush_id)
        s = self.px_per_mm
        width_px = brush.width * s
        pts = np.array([[p.x * s, p.y * s] for p in stroke.points], np.float32)
        pressure = np.array([p.pressure for p in stroke.points], np.float32)
        angle = np.array([p.angle for p in stroke.points], np.float32)

        # Densify so stamps overlap (spacing ~ 1/4 of the footprint).
        seg = np.hypot(*np.diff(pts, axis=0).T)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        n = max(int(cum[-1] / max(width_px * 0.15, 0.7)) + 2, 2)
        t = np.linspace(0, cum[-1], n)
        xs, ys = np.interp(t, cum, pts[:, 0]), np.interp(t, cum, pts[:, 1])
        pr = np.interp(t, cum, pressure)
        an = np.interp(t, cum, angle)

        pad = int(width_px) + 3
        x0, y0 = max(int(xs.min()) - pad, 0), max(int(ys.min()) - pad, 0)
        x1 = min(int(xs.max()) + pad, self.canvas.shape[1])
        y1 = min(int(ys.max()) + pad, self.canvas.shape[0])
        if x1 <= x0 or y1 <= y0:
            return
        mask = np.zeros((y1 - y0, x1 - x0), np.float32)

        load0 = self.load_fraction
        load1 = max(load0 - stroke_paint_cost(stroke) / brush.capacity, 0.0)
        loads = np.linspace(load0, load1, n)
        for x, y, p, a, ld in zip(xs, ys, pr, an, loads):
            if p <= 0.02:
                continue
            size = width_px * (0.35 + 0.65 * p)
            alpha = min(0.95 * self.opacity * (0.35 + 0.65 * ld), 1.0)
            center = (float(x - x0), float(y - y0))
            if brush.kind == "flat":
                # broad side across the direction of travel
                axes = (size / 2, max(width_px * 0.12, 0.8))
                box = (center, (axes[1] * 2, axes[0] * 2), float(a))
            else:
                box = (center, (size, size), 0.0)
            cv2.ellipse(mask, box, float(alpha), -1, lineType=cv2.LINE_AA)
        self.load_fraction = load1

        # Bristle streaks across the stroke.
        mean_dir = np.radians(np.mean(an))
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        u = -np.sin(mean_dir) * xx + np.cos(mean_dir) * yy
        bristles = self.rng.random(int(width_px * 4) + 8).astype(np.float32)
        tex = np.interp((u * 2.0) % len(bristles), np.arange(len(bristles)), bristles).astype(np.float32)
        dryness = 1.0 - (load0 + load1) / 2
        streak = np.clip(0.8 + 0.2 * tex - dryness * 0.3 * (tex < 0.3), 0.0, 1.0)
        mask = np.clip(mask * streak, 0.0, 1.0)[..., None]

        color = self.palette[stroke.color_id]
        region = self.canvas[y0:y1, x0:x1]
        region[:] = region * (1 - mask) + color * mask

    def image(self) -> np.ndarray:
        return np.clip(self.canvas, 0, 255).astype(np.uint8)


def render_program(program: PaintProgram, config: MachineConfig, px_per_mm: float = 2.0, seed: int = 0) -> np.ndarray:
    r = Renderer(program, config, px_per_mm, seed)
    for a in program.actions:
        r.apply(a)
    return r.image()

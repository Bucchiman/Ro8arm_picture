"""Closed-loop painting: paint a layer, photograph the canvas, plan the next layer from the photo.

    blank canvas photo -> flat-field
    for each brush (coarse -> fine), then touch-up rounds with the finest brush:
        photo -> rectify + flat-field -> what is really on the canvas
        strokes where the photo still differs from the target -> humanize -> process plan (wash/dip/...) -> paint
    the loop stops touching up once a round no longer improves the picture.

The same code drives the simulator (SimWorld + SimCamera) and, later, the machine (Klipper + OpenCVCamera):
`execute(actions)` and `camera.capture()` are the only two points of contact with the world.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from painter.analysis.palette import rgb_to_lab
from painter.config import MachineConfig
from painter.feedback.camera import FlatField, rectify
from painter.planner.paint_model import PaletteStock
from painter.planner.sequencer import plan
from painter.program import Action, PaintProgram, PaletteColor
from painter.sim.animator import ssim
from painter.strokes.human_motion import MotionParams, humanize
from painter.strokes.painterly import StrokeParams, generate_layer


@dataclass
class LoopParams:
    threshold: float = 12.0
    threshold_growth: float = 0.5
    touchup_rounds: int = 2  # extra passes with the finest brush, driven by the photo
    touchup_min_gain: float = 0.15  # stop touching up when mean delta E improves less than this
    touchup_level: int = 1  # threshold of touch-ups = threshold * (1 + growth * level); lower = stricter
    seed: int = 0


@dataclass
class Step:
    index: int
    name: str
    brush: str | None
    strokes: int
    ssim: float  # photo vs target
    delta_e: float  # mean Lab difference photo vs target
    off_fraction: float  # share of the canvas still clearly off (delta E > 20)
    images: dict[str, str] = field(default_factory=dict)


def compare(seen_rgb: np.ndarray, target_rgb: np.ndarray) -> tuple[float, float, float, np.ndarray]:
    de = np.sqrt(((rgb_to_lab(seen_rgb) - rgb_to_lab(target_rgb)) ** 2).sum(-1))
    return ssim(seen_rgb, target_rgb), float(de.mean()), float((de > 20).mean()), de


def error_heatmap(de: np.ndarray) -> np.ndarray:
    """delta E map -> BGR heatmap (0 = blue, >= 40 = red)."""
    return cv2.applyColorMap(np.clip(de / 40 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_TURBO)


def paint_closed_loop(
    target_rgb: np.ndarray,
    palette: list[PaletteColor],
    config: MachineConfig,
    camera,
    execute: Callable[[list[Action]], None],
    px_per_mm: float,
    params: LoopParams = LoopParams(),
    out_dir: str | Path | None = None,
    source_image: str | None = None,
    on_step: Callable[[Step, np.ndarray], None] | None = None,
) -> tuple[PaintProgram, list[Step]]:
    """`execute` paints a list of actions in the world; `on_step(step, delta_e_map)` is called after every photo."""
    out = Path(out_dir) if out_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    palette_rgb = np.array([c.rgb for c in palette], np.uint8)
    h, w = target_rgb.shape[:2]
    painted = np.zeros((h, w), bool)
    rng = np.random.default_rng(params.seed)
    motion_rng = np.random.default_rng(params.seed)
    mp = MotionParams(seed=params.seed)
    sp = StrokeParams(px_per_mm=px_per_mm, threshold=params.threshold, threshold_growth=params.threshold_growth,
                      seed=params.seed)
    stock = PaletteStock(config.palette.slot_capacity, config.palette.refill_threshold)
    kinds = {b.id: b.kind for b in config.brushes}
    actions: list[Action] = []
    steps: list[Step] = []

    blank = camera.capture()
    flat = FlatField(rectify(blank, config, px_per_mm))

    def look(index: int, name: str, brush_id: str | None, n_strokes: int, frame=None) -> np.ndarray:
        frame = camera.capture() if frame is None else frame
        seen = flat.apply(rectify(frame, config, px_per_mm))
        s, de_mean, off, de = compare(seen, target_rgb)
        step = Step(index, name, brush_id, n_strokes, round(s, 4), round(de_mean, 2), round(off, 4))
        if out:
            stem = f"step_{index:02d}"
            paths = {"camera": out / f"{stem}_camera.jpg", "seen": out / f"{stem}_seen.png",
                     "error": out / f"{stem}_error.png"}
            cv2.imwrite(str(paths["camera"]), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            cv2.imwrite(str(paths["seen"]), cv2.cvtColor(seen, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(paths["error"]), error_heatmap(de))
            step.images = {k: str(v) for k, v in paths.items()}
        steps.append(step)
        if on_step:
            on_step(step, de)
        return seen

    seen = look(0, "blank canvas", None, 0, blank)

    schedule = [(f"layer {i}: {b.id}", b, i) for i, b in enumerate(config.brushes)]
    finest = len(config.brushes) - 1
    schedule += [(f"touch-up {r + 1}: {config.brushes[finest].id}", config.brushes[finest], params.touchup_level)
                 for r in range(params.touchup_rounds)]
    for layer, (name, brush, level) in enumerate(schedule):
        canvas = seen.copy()  # plan on what the camera saw, not on the internal model
        raw = generate_layer(target_rgb, palette_rgb, brush, layer, canvas, painted, sp, rng, level)
        if not raw:
            break
        strokes = [humanize(r, px_per_mm, config.motion.paint_speed, kinds[r.brush_id], mp, motion_rng) for r in raw]
        chunk = plan(strokes, config, stock)
        execute(chunk)
        actions.extend(chunk)
        before = steps[-1].delta_e
        seen = look(len(steps), name, brush.id, len(strokes))
        if layer >= len(config.brushes) and before - steps[-1].delta_e < params.touchup_min_gain:
            break

    program = PaintProgram((config.canvas.width, config.canvas.height), palette, actions, source_image)
    return program, steps


def steps_to_dict(steps: list[Step]) -> list[dict]:
    return [asdict(s) for s in steps]


def steps_sheet(steps: list[Step], tile_w: int = 320) -> np.ndarray:
    """One column per step: what the camera saw (top) and where it still differs from the target (bottom)."""
    cols = []
    for s in steps:
        seen = cv2.imread(s.images["seen"])
        err = cv2.imread(s.images["error"])
        th = int(seen.shape[0] * tile_w / seen.shape[1])
        col = np.full((th * 2 + 60, tile_w, 3), 255, np.uint8)
        col[30 : 30 + th] = cv2.resize(seen, (tile_w, th), interpolation=cv2.INTER_AREA)
        col[60 + th - 30 : 60 + 2 * th - 30] = cv2.resize(err, (tile_w, th), interpolation=cv2.INTER_AREA)
        cv2.putText(col, s.name[:40], (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.putText(col, f"dE {s.delta_e:.1f}  off {s.off_fraction:.0%}  +{s.strokes} strokes", (4, 2 * th + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
        cols.append(col)
    return np.hstack(cols)

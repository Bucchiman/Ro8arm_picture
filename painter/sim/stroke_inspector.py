"""Close-up of single strokes: how the brush moves, presses, turns and how fast it goes.

Left: zoomed canvas around the stroke (with everything painted before it), the stroke being laid down and the
brush footprint at the current point. Right: Z depth, speed and brush angle over time with a cursor.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from painter.config import MachineConfig
from painter.program import Paint, PaintProgram, Stroke, StrokePoint
from painter.sim.renderer import Renderer

VIEW = 520  # zoom view size (px)
GRAPH_W = 560
FONT = cv2.FONT_HERSHEY_SIMPLEX


@dataclass
class StrokeTiming:
    t: np.ndarray  # time at each point (s)
    z: np.ndarray  # brush tip Z (mm)
    speed: np.ndarray
    angle: np.ndarray
    length: float

    @property
    def duration(self) -> float:
        return float(self.t[-1])


def timing(stroke: Stroke, config: MachineConfig) -> StrokeTiming:
    brush = config.brush(stroke.brush_id)
    pts = stroke.points
    t = [0.0]
    length = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = float(np.hypot(b.x - a.x, b.y - a.y))
        length += seg
        t.append(t[-1] + seg / max((a.speed + b.speed) / 2, 1e-3))
    z = np.array([config.canvas.surface_z - p.pressure * brush.press_depth for p in pts])
    return StrokeTiming(np.array(t), z, np.array([p.speed for p in pts]), np.array([p.angle for p in pts]), length)


def select_strokes(program: PaintProgram, indices: list[int] | None, random_n: int, seed: int) -> list[int]:
    n = len(program.strokes())
    if indices:
        bad = [i for i in indices if not 0 <= i < n]
        if bad:
            raise SystemExit(f"stroke index out of range (0..{n - 1}): {bad}")
        return sorted(set(indices))
    if random_n:
        rng = np.random.default_rng(seed)
        return sorted(rng.choice(n, size=min(random_n, n), replace=False).tolist())
    # default: the first stroke of each brush, i.e. one stroke per layer
    seen, out = set(), []
    for i, s in enumerate(program.strokes()):
        if s.brush_id not in seen:
            seen.add(s.brush_id)
            out.append(i)
    return out


def inspect(program: PaintProgram, config: MachineConfig, indices: list[int], out_dir, px_per_mm: float = 2.0,
            slow: float = 1.0, fps: int = 30) -> list[dict]:
    """Write stroke_XXXXX.mp4 and .png for each stroke index. Strokes are numbered in painting order."""
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    renderer = Renderer(program, config, px_per_mm)
    wanted = set(indices)
    results = []
    k = -1
    for action in program.actions:
        if isinstance(action, Paint):
            k += 1
            if k in wanted:
                results.append(_inspect_one(renderer, action.stroke, k, config, out_dir, slow, fps))
                wanted.discard(k)
                if not wanted:
                    break
        renderer.apply(action)  # context: everything painted before (and the stroke itself afterwards)
    return results


def _inspect_one(renderer: Renderer, stroke: Stroke, index: int, config: MachineConfig, out_dir, slow, fps) -> dict:
    s = renderer.px_per_mm
    brush = config.brush(stroke.brush_id)
    tm = timing(stroke, config)
    before = renderer.canvas.copy()
    load0 = renderer.load_fraction

    # Zoom window around the stroke.
    xs = np.array([p.x for p in stroke.points]) * s
    ys = np.array([p.y for p in stroke.points]) * s
    margin = brush.width * s * 1.5 + 6
    x0, x1 = xs.min() - margin, xs.max() + margin
    y0, y1 = ys.min() - margin, ys.max() + margin
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0, y0 = cx - side / 2, cy - side / 2
    zoom = VIEW / side

    def view(img_f32):
        M = np.array([[zoom, 0, -x0 * zoom], [0, zoom, -y0 * zoom]], np.float32)
        img = cv2.warpAffine(np.clip(img_f32, 0, 255).astype(np.uint8), M, (VIEW, VIEW), flags=cv2.INTER_NEAREST,
                             borderValue=(235, 235, 235))
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def to_view(x_mm, y_mm):
        return int((x_mm * s - x0) * zoom), int((y_mm * s - y0) * zoom)

    n_frames = max(int(tm.duration * slow * fps), 2)
    path = out_dir / f"stroke_{index:05d}.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (VIEW + GRAPH_W, VIEW + 60))
    hold = fps  # keep the last frame for a second
    last = None
    for f in range(n_frames + hold):
        tc = min(f / (n_frames - 1), 1.0) * tm.duration
        upto = int(np.searchsorted(tm.t, tc, side="right"))
        partial = _partial_stroke(stroke, tm, tc, upto)
        renderer.canvas = before.copy()
        renderer.load_fraction = load0
        renderer.rng = np.random.default_rng(index)  # same bristle pattern every frame
        if len(partial.points) >= 2:
            renderer.render_stroke(partial)
        img = view(renderer.canvas)
        cur = partial.points[-1]
        _draw_footprint(img, cur, brush, s * zoom, to_view(cur.x, cur.y))
        # planned path (thin) for reference
        cv2.polylines(img, [np.array([to_view(p.x, p.y) for p in stroke.points], np.int32)], False,
                      (0, 0, 255), 1, cv2.LINE_AA)
        graphs = _graphs(tm, tc, brush, config)
        frame = np.full((VIEW + 60, VIEW + GRAPH_W, 3), 250, np.uint8)
        frame[:VIEW, :VIEW] = img
        frame[:VIEW, VIEW:] = graphs
        c = renderer.palette[stroke.color_id]
        cv2.rectangle(frame, (10, VIEW + 15), (40, VIEW + 45), (int(c[2]), int(c[1]), int(c[0])), -1)
        cv2.putText(frame, f"stroke #{index}  layer {stroke.layer}  {brush.id} ({brush.kind}, {brush.width:g} mm)  "
                           f"color {stroke.color_id}  length {tm.length:.1f} mm  duration {tm.duration:.2f} s  "
                           f"load {load0:.0%}", (50, VIEW + 36), FONT, 0.45, (0, 0, 0), 1)
        cv2.putText(frame, f"zoom: {VIEW / side * s:.1f} px/mm  playback x{1 / slow:g}", (10, 18), FONT, 0.45,
                    (0, 0, 0), 1)
        writer.write(frame)
        last = frame
    writer.release()
    png = out_dir / f"stroke_{index:05d}.png"
    cv2.imwrite(str(png), last)
    renderer.canvas = before
    renderer.load_fraction = load0
    return {"index": index, "brush": brush.id, "color": stroke.color_id, "length_mm": round(tm.length, 1),
            "duration_s": round(tm.duration, 2), "min_z": round(float(tm.z.min()), 3),
            "video": str(path), "image": str(png)}


def _partial_stroke(stroke: Stroke, tm: StrokeTiming, tc: float, upto: int) -> Stroke:
    pts = list(stroke.points[:upto])
    if 0 < upto < len(stroke.points):
        a, b = stroke.points[upto - 1], stroke.points[upto]
        u = (tc - tm.t[upto - 1]) / max(tm.t[upto] - tm.t[upto - 1], 1e-9)
        lerp = lambda p, q: p + (q - p) * u
        pts.append(StrokePoint(lerp(a.x, b.x), lerp(a.y, b.y), lerp(a.pressure, b.pressure), lerp(a.angle, b.angle),
                               lerp(a.speed, b.speed)))
    return Stroke(stroke.brush_id, stroke.color_id, stroke.layer, pts or stroke.points[:1])


def _draw_footprint(img, p: StrokePoint, brush, px_per_mm_view: float, center) -> None:
    size = brush.width * px_per_mm_view * (0.35 + 0.65 * p.pressure)
    if brush.kind == "flat":
        box = (center, (max(brush.width * 0.12 * px_per_mm_view * 2, 2), size), float(p.angle))
        pts = cv2.boxPoints(box).astype(np.int32)
        cv2.polylines(img, [pts], True, (0, 0, 0), 2, cv2.LINE_AA)
    else:
        cv2.circle(img, center, max(int(size / 2), 1), (0, 0, 0), 2, cv2.LINE_AA)
    rad = np.radians(p.angle)
    tip = (int(center[0] + np.cos(rad) * size), int(center[1] + np.sin(rad) * size))
    cv2.arrowedLine(img, center, tip, (0, 0, 0), 1, cv2.LINE_AA, tipLength=0.25)


def _graphs(tm: StrokeTiming, tc: float, brush, config: MachineConfig) -> np.ndarray:
    g = np.full((VIEW, GRAPH_W, 3), 255, np.uint8)
    surface = config.canvas.surface_z
    rows = [
        ("Z (mm) - brush tip, lower = more pressure", tm.z, (surface - brush.press_depth * 1.1, surface + 0.3),
         [(surface, "surface"), (surface - brush.press_depth, "full press")], (200, 60, 0)),
        ("speed (mm/s)", tm.speed, (0, max(float(tm.speed.max()) * 1.15, 1)), [], (0, 140, 0)),
        ("brush angle (deg)", tm.angle, (float(tm.angle.min()) - 10, float(tm.angle.max()) + 10), [], (0, 0, 200)),
    ]
    h = VIEW // 3
    T = max(tm.duration, 1e-6)
    for r, (title, ys, (lo, hi), refs, color) in enumerate(rows):
        top, left, w, hh = r * h + 22, 50, GRAPH_W - 70, h - 46
        cv2.putText(g, title, (left, top - 6), FONT, 0.45, (0, 0, 0), 1)
        cv2.rectangle(g, (left, top), (left + w, top + hh), (200, 200, 200), 1)
        fy = lambda v: int(top + (hi - v) / max(hi - lo, 1e-6) * hh)
        fx = lambda t: int(left + t / T * w)
        for v, name in refs:
            cv2.line(g, (left, fy(v)), (left + w, fy(v)), (160, 160, 160), 1)
            cv2.putText(g, name, (left + w - 80, fy(v) - 3), FONT, 0.35, (120, 120, 120), 1)
        cv2.putText(g, f"{hi:.1f}", (2, top + 10), FONT, 0.33, (90, 90, 90), 1)
        cv2.putText(g, f"{lo:.1f}", (2, top + hh), FONT, 0.33, (90, 90, 90), 1)
        pts = np.array([[fx(t), fy(v)] for t, v in zip(tm.t, ys)], np.int32)
        cv2.polylines(g, [pts], False, color, 2, cv2.LINE_AA)
        cv2.line(g, (fx(tc), top), (fx(tc), top + hh), (0, 0, 0), 1)
        cur = float(np.interp(tc, tm.t, ys))
        cv2.circle(g, (fx(tc), fy(cur)), 4, (0, 0, 0), -1)
        cv2.putText(g, f"{cur:.2f}", (min(fx(tc) + 6, left + w - 45), fy(cur) - 6), FONT, 0.4, (0, 0, 0), 1)
    cv2.putText(g, f"time 0 .. {T:.2f} s", (50, VIEW - 6), FONT, 0.4, (0, 0, 0), 1)
    return g

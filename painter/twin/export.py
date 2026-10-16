"""Digital twin export: run an image through plan -> G-code -> G-code simulation (with the Klipper macros) and pack
what a 3D viewer needs to replay the machine painting it.

The viewer (painter/twin/viewer.html) rebuilds the machine from the config and replays:
  motion   every move of the head (t, x, y, z, a) as the G-code simulator timed it
  strokes  the strokes rebuilt from the contact moves (points, pressure, brush angle, paint load), drawn on the canvas
  events   tool changes, dips, washes and refill pauses; the activity (macro) running at each moment

Binary arrays are gzip + base64 so a 17 h painting (~400k moves, ~30k strokes) fits in a few MB.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
from pathlib import Path

import cv2
import numpy as np

from painter.backends.klipper_gcode import to_gcode
from painter.config import MachineConfig
from painter.program import Dip, Stroke, Wash
from painter.planner.paint_model import stroke_paint_cost
from painter.sim.gcode_sim import run_gcode

VIEWER = Path(__file__).with_name("viewer.html")
XY_Q = 0.02    # mm per unit (uint16: 0 .. 1310 mm)
Z_Q = 0.01     # mm per unit (int16: +-327 mm)
CANVAS_Q = 0.01


def macros_for_config(template: str, config: MachineConfig) -> str:
    """The Klipper macro file with its _PAINTER_VARS station positions taken from the config."""
    c = config
    values = {
        "travel_z": c.motion.travel_z,
        "palette_x0": c.palette.origin[0], "palette_y0": c.palette.origin[1],
        "palette_dx": c.palette.pitch[0], "palette_dy": c.palette.pitch[1], "palette_cols": c.palette.columns,
        "wash_x": c.wash.position[0], "wash_y": c.wash.position[1], "wash_r": c.wash.radius * 0.5,
        "wash_z": c.wash.depth_z, "wash_circles": c.wash.circles,
        "wipe_x": c.wipe.position[0], "wipe_y": c.wipe.position[1], "wipe_len": c.wipe.length,
        "wipe_passes": c.wipe.passes,
        "rack_x": c.brush_rack.origin[0], "rack_y0": c.brush_rack.origin[1], "rack_dy": c.brush_rack.pitch,
    }
    out = template
    for k, v in values.items():
        v = int(v) if float(v).is_integer() else v
        out, n = re.subn(rf"^variable_{k}:.*$", f"variable_{k}: {v}", out, flags=re.M)
        if n != 1:
            raise ValueError(f"variable_{k} not found exactly once in the macro template")
    return out


def _pack(arr: np.ndarray) -> str:
    return base64.b64encode(gzip.compress(np.ascontiguousarray(arr).tobytes(), 6)).decode("ascii")


def motion_arrays(interp) -> dict:
    segs = interp.segments
    n = len(segs) + 1
    p = np.empty((n, 4), np.float64)
    t = np.empty(n, np.float64)
    p[0], t[0] = segs[0].p0, segs[0].t0
    for i, s in enumerate(segs, 1):
        p[i], t[i] = s.p1, s.t1
    # context (macro / stroke) as run-length change points
    ctx_names: list[str] = []
    ctx_t, ctx_i = [], []
    last = None
    for s in segs:
        if s.context != last:
            if s.context not in ctx_names:
                ctx_names.append(s.context)
            ctx_t.append(s.t0)
            ctx_i.append(ctx_names.index(s.context))
            last = s.context
    return {
        "n": n,
        "t": _pack(t.astype(np.float64)),
        "xy": _pack(np.clip(np.round(p[:, :2] / XY_Q), 0, 65535).astype(np.uint16)),
        "z": _pack(np.clip(np.round(p[:, 2] / Z_Q), -32768, 32767).astype(np.int16)),
        "a": _pack(p[:, 3].astype(np.float32)),
        "ctx_names": ctx_names, "ctx_t": [round(v, 3) for v in ctx_t], "ctx_i": ctx_i,
    }


def stroke_arrays(checker, config: MachineConfig) -> dict:
    """Strokes in canvas mm with start/end times and the paint load the renderer would use."""
    brush_ids = [b.id for b in config.brushes]
    meta, pts = [], []
    load = 0.0
    for t, item in checker.timeline:
        if isinstance(item, Dip):
            load = 1.0
        elif isinstance(item, Wash):
            load = 0.0
        elif isinstance(item, Stroke):
            brush = config.brush(item.brush_id)
            load1 = max(load - stroke_paint_cost(item) / brush.capacity, 0.0)
            dur = 0.0
            for a, b in zip(item.points, item.points[1:]):
                dur += float(np.hypot(b.x - a.x, b.y - a.y)) / max(b.speed, 1e-6)
            meta.append((t - dur, t, item.color_id, brush_ids.index(item.brush_id), load, load1, len(item.points)))
            for q in item.points:
                pts.append((q.x, q.y, q.pressure, q.angle % 360.0))
            load = load1
    m = np.array(meta, np.float64) if meta else np.zeros((0, 7))
    P = np.array(pts, np.float64) if pts else np.zeros((0, 4))
    return {
        "n": len(meta),
        "t0": _pack(m[:, 0].astype(np.float32)), "t1": _pack(m[:, 1].astype(np.float32)),
        "color": _pack(m[:, 2].astype(np.int8)), "brush": _pack(m[:, 3].astype(np.uint8)),
        "load": _pack(np.round(m[:, 4:6] * 255).astype(np.uint8)), "npts": _pack(m[:, 6].astype(np.uint16)),
        "xy": _pack(np.clip(np.round(P[:, :2] / CANVAS_Q), 0, 65535).astype(np.uint16)),
        "pressure": _pack(np.round(np.clip(P[:, 2], 0, 1) * 255).astype(np.uint8)),
        "angle": _pack(np.round(P[:, 3] * 100).astype(np.uint16)),
    }


def event_lists(interp, checker) -> dict:
    tools = [(round(e.t, 3), int(e.text)) for e in interp.events if e.kind == "tool"]
    pauses = [(round(e.t, 3), e.text) for e in interp.events if e.kind == "pause"]
    dips, washes = [], []
    for t, item in checker.timeline:
        if isinstance(item, Dip):
            dips.append((round(t, 3), item.color_id))
        elif isinstance(item, Wash):
            washes.append(round(t, 3))
    return {"tools": tools, "pauses": pauses, "dips": dips, "washes": washes}


def machine_dict(config: MachineConfig) -> dict:
    c = config
    return {
        "canvas": {"origin": list(c.canvas.origin), "size": [c.canvas.width, c.canvas.height],
                   "surface_z": c.canvas.surface_z},
        "motion": {"x_range": list(c.motion.x_range), "y_range": list(c.motion.y_range),
                   "z_range": list(c.motion.z_range), "travel_z": c.motion.travel_z},
        "palette": [list(c.palette.slot_position(i)) for i in range(c.palette.slots)],
        "wash": {"position": list(c.wash.position), "radius": c.wash.radius, "depth_z": c.wash.depth_z},
        "wipe": {"position": list(c.wipe.position), "length": c.wipe.length},
        "rack": [list(c.rack_position(b.id)) for b in c.brushes],
        "brushes": [{"id": b.id, "kind": b.kind, "width": b.width, "press_depth": b.press_depth} for b in c.brushes],
        "camera_park": list(c.camera.park),
    }


def _jpeg_b64(rgb: np.ndarray, quality: int = 82, max_w: int = 900) -> str:
    if rgb.shape[1] > max_w:
        h = int(round(rgb.shape[0] * max_w / rgb.shape[1]))
        rgb = cv2.resize(rgb, (max_w, h), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
    assert ok
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def build_twin(program, config: MachineConfig, macros_template: str, source_rgb: np.ndarray | None,
               title: str, px_per_mm: float = 2.0) -> tuple[dict, dict]:
    """Returns (twin data for the viewer, G-code simulation report)."""
    from painter.sim.gcode_player import render_canvas

    gcode = to_gcode(program, config)
    macros = macros_for_config(macros_template, config)
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".cfg", delete=False, encoding="utf-8") as f:
        f.write(macros)
        macros_path = f.name
    try:
        interp, checker = run_gcode(gcode, config, macros_path)
    finally:
        Path(macros_path).unlink(missing_ok=True)
    report = interp.report.to_dict()
    final = render_canvas(interp, checker, config, px_per_mm)
    palette = {c.id: "#%02x%02x%02x" % tuple(c.rgb) for c in interp.palette}
    data = {
        "version": 1,
        "title": title,
        "machine": machine_dict(config),
        "palette": palette,
        "total_s": float(interp.t),
        "motion": motion_arrays(interp),
        "strokes": stroke_arrays(checker, config),
        "events": event_lists(interp, checker),
        "report": {k: report[k] for k in ("total_time_h", "strokes_rebuilt", "macro_calls", "pauses", "errors",
                                          "warnings", "issues_by_kind", "travel_mm", "contact_mm", "max_abs_a")},
        "images": {"final": _jpeg_b64(final), **({"source": _jpeg_b64(source_rgb, 80, 600)}
                                                if source_rgb is not None else {})},
    }
    return data, report


LOCAL_HEAD = ('<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n')


def write_viewer(data: dict, out_dir: Path) -> Path:
    """out_dir/index.html (the viewer) + out_dir/twin_data.json, which the viewer fetches.

    The viewer source has no <html>/<head> skeleton (the artifact host adds one); the local copy gets a minimal one.
    Open it through a local web server (fetch does not work on file://):  python -m http.server -d OUT_DIR
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "twin_data.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    html = VIEWER.read_text(encoding="utf-8")
    (out_dir / "index.html").write_text(LOCAL_HEAD + html + "\n</body></html>\n", encoding="utf-8")
    return out_dir / "index.html"

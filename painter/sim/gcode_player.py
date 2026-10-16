"""Playback of a simulated G-code run: top view with the head path, plus Z gauge and brush rotation dial."""

from __future__ import annotations

import math

import cv2
import numpy as np

from painter.config import MachineConfig
from painter.program import Stroke
from painter.sim.animator import _compose_frame
from painter.sim.gcode_sim import Checker, Interpreter, program_shell
from painter.sim.renderer import Renderer

PANEL_W = 260


def render_canvas(interp: Interpreter, checker: Checker, config: MachineConfig, px_per_mm: float) -> np.ndarray:
    renderer = Renderer(program_shell(config, interp.palette), config, px_per_mm)
    for _, item in checker.timeline:
        renderer.apply(item) if not isinstance(item, Stroke) else renderer.render_stroke(item)
    return renderer.image()


def play(interp: Interpreter, checker: Checker, config: MachineConfig, video_path: str, px_per_mm: float = 2.0,
         speed: float | None = None, start: float = 0.0, end: float | None = None, fps: int = 30,
         target_seconds: float = 60.0) -> dict:
    """Write a video of the run. `speed` = machine seconds per video second (default: fit into target_seconds)."""
    total = interp.t
    end = total if end is None else min(end, total)
    if speed is None:
        speed = max((end - start) / target_seconds, 1e-3)
    dt = speed / fps
    s = px_per_mm
    program = program_shell(config, interp.palette)
    renderer = Renderer(program, config, px_per_mm)
    colors = {c.id: c.rgb for c in program.palette}

    segs = interp.segments
    timeline = checker.timeline
    events = sorted(interp.events, key=lambda e: e.t)
    issues_by_line: dict[int, int] = {}
    for iss in checker.issues:
        issues_by_line[iss.line] = issues_by_line.get(iss.line, 0) + 1

    first = _compose_frame(renderer.image(), program, config, np.zeros(2), None, "", px_per_mm)
    H, W = first.shape[:2]
    trail = np.zeros((H, W), np.float32)  # fading head path
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W + PANEL_W, H))

    si = ti = ei = 0
    brush_index = -1
    on_brush: int | None = None
    message = ""
    issues_seen = 0
    counted_lines: set[int] = set()
    wet: list[tuple[int, int]] = []  # contact path of the stroke in progress (pixels)
    frames = 0
    t = start
    while t <= end + 1e-9:
        # Advance the canvas and the state up to time t.
        while ti < len(timeline) and timeline[ti][0] <= t:
            item = timeline[ti][1]
            if isinstance(item, Stroke):
                renderer.render_stroke(item)
                wet = []
            else:
                renderer.apply(item)
                on_brush = getattr(item, "color_id", None)
            ti += 1
        while ei < len(events) and events[ei].t <= t:
            ev = events[ei]
            if ev.kind == "tool":
                brush_index = int(ev.text)
                if brush_index >= 0:
                    on_brush = None
            elif ev.kind == "pause":
                message = "PAUSED (human refill) -> RESUME"
            elif ev.kind == "message":
                message = ev.text
            ei += 1
        trail *= 0.92
        while si < len(segs) and segs[si].t0 <= t:
            seg = segs[si]
            u = 1.0 if seg.t1 <= t else (t - seg.t0) / max(seg.t1 - seg.t0, 1e-9)
            p0 = seg.p0
            p1 = seg.p0 + (seg.p1 - seg.p0) * u
            a = (int(p0[0] * s), int(p0[1] * s))
            b = (int(p1[0] * s), int(p1[1] * s))
            if p1[2] < config.canvas.surface_z - 0.05 and checker.zone(p1[0], p1[1])[0] == "canvas":
                wet.append(b)
            else:
                cv2.line(trail, a, b, 1.0, 1, cv2.LINE_AA)
            if seg.t1 <= t and seg.line not in counted_lines:
                counted_lines.add(seg.line)
                issues_seen += issues_by_line.get(seg.line, 0)
            if seg.t1 > t:
                break
            si += 1
        cur = segs[min(si, len(segs) - 1)]
        u = min(max((t - cur.t0) / max(cur.t1 - cur.t0, 1e-9), 0.0), 1.0)
        pos = cur.p0 + (cur.p1 - cur.p0) * u

        brush = config.brushes[brush_index] if 0 <= brush_index < len(config.brushes) else None
        label = f"t={_hms(t)}  line {cur.line}  [{cur.context}]"
        frame = _compose_frame(renderer.image(), program, config, pos[:2], brush.id if brush else None, label, s)
        frame = frame.astype(np.float32)
        frame[trail > 0.02] = frame[trail > 0.02] * (1 - trail[trail > 0.02, None]) + np.array([200, 80, 0]) * trail[trail > 0.02, None]
        frame = frame.astype(np.uint8)
        if len(wet) > 1 and brush is not None and on_brush in colors:
            c = colors[on_brush]
            cv2.polylines(frame, [np.array(wet, np.int32)], False, (int(c[2]), int(c[1]), int(c[0])),
                          max(int(brush.width * s * 0.6), 1), cv2.LINE_AA)
        panel = _panel(H, pos, brush, on_brush, colors, config, message, issues_seen, t, total)
        writer.write(np.hstack([frame, panel]))
        frames += 1
        t += dt
    writer.release()
    return {"frames": frames, "speed": round(speed, 3), "start_s": start, "end_s": round(end, 1)}


def _hms(t: float) -> str:
    h, rem = divmod(int(t), 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _panel(H, pos, brush, on_brush, colors, config, message, issues, t, total) -> np.ndarray:
    """BGR side panel: Z gauge, brush rotation dial, state text."""
    p = np.full((H, PANEL_W, 3), 250, np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    x, y, z, a = (float(v) for v in pos)
    m = config.motion
    surface = config.canvas.surface_z

    # Z gauge
    top, bot = 40, min(H - 200, 360)
    zmin, zmax = m.z_range[0], min(m.z_range[1], m.travel_z + 5)
    zy = lambda v: int(top + (zmax - v) / (zmax - zmin) * (bot - top))
    cv2.putText(p, "Z (mm)", (20, 25), font, 0.5, (0, 0, 0), 1)
    cv2.rectangle(p, (30, top), (50, bot), (220, 220, 220), -1)
    cv2.line(p, (22, zy(surface)), (58, zy(surface)), (0, 120, 0), 2)
    cv2.putText(p, "surface", (62, zy(surface) + 4), font, 0.4, (0, 120, 0), 1)
    if brush is not None:
        cv2.line(p, (26, zy(surface - brush.press_depth)), (54, zy(surface - brush.press_depth)), (0, 0, 200), 1)
        cv2.putText(p, "full press", (62, zy(surface - brush.press_depth) + 4), font, 0.35, (0, 0, 200), 1)
    cv2.line(p, (22, zy(config.wash.depth_z)), (58, zy(config.wash.depth_z)), (150, 120, 40), 1)
    cv2.putText(p, "oil jar", (62, zy(config.wash.depth_z) + 4), font, 0.35, (150, 120, 40), 1)
    cv2.rectangle(p, (28, zy(z) - 3), (52, zy(z) + 3), (0, 0, 0), -1)
    cv2.putText(p, f"{z:6.2f}", (150, zy(z) + 4), font, 0.45, (0, 0, 0), 1)

    # Brush rotation dial
    cx, cy, r = 130, bot + 85, 55
    cv2.putText(p, f"A {a:7.1f} deg", (20, bot + 22), font, 0.5, (0, 0, 0), 1)
    cv2.circle(p, (cx, cy), r, (200, 200, 200), 1, cv2.LINE_AA)
    rad = math.radians(a)
    dx, dy = math.cos(rad), math.sin(rad)
    if brush is not None and brush.kind == "flat":
        # broad side across the direction the brush is set to travel
        hw, ht = r * 0.8, 6
        pts = np.array([[cx - dy * hw - dx * ht, cy + dx * hw - dy * ht], [cx + dy * hw - dx * ht, cy - dx * hw - dy * ht],
                        [cx + dy * hw + dx * ht, cy - dx * hw + dy * ht], [cx - dy * hw + dx * ht, cy + dx * hw + dy * ht]])
        cv2.fillPoly(p, [pts.astype(np.int32)], (60, 40, 20), cv2.LINE_AA)
    elif brush is not None:
        cv2.circle(p, (cx, cy), 10, (60, 40, 20), -1, cv2.LINE_AA)
    cv2.arrowedLine(p, (cx, cy), (int(cx + dx * r), int(cy + dy * r)), (0, 0, 200), 1, cv2.LINE_AA, tipLength=0.15)

    # State
    ty = cy + r + 30
    lines = [f"brush: {brush.id if brush else '-'}",
             f"paint on brush: {'-' if on_brush is None else 'slot %d' % on_brush}",
             f"XY: {x:6.1f}, {y:6.1f}",
             f"time: {_hms(t)} / {_hms(total)}",
             f"issues so far: {issues}"]
    for i, txt in enumerate(lines):
        cv2.putText(p, txt, (12, ty + i * 20), font, 0.42, (0, 0, 200) if "issues" in txt and issues else (0, 0, 0), 1)
    if on_brush in colors:
        c = colors[on_brush]
        cv2.rectangle(p, (200, ty + 8), (240, ty + 26), (int(c[2]), int(c[1]), int(c[0])), -1)
    if message:
        cv2.putText(p, message[:34], (12, ty + len(lines) * 20 + 10), font, 0.4, (0, 0, 200), 1)
    return p

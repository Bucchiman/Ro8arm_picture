"""Process simulation: head travel, time estimate, quality metrics and a process video."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

from painter.analysis.palette import rgb_to_lab
from painter.config import MachineConfig
from painter.planner.sequencer import paint_usage
from painter.program import Dip, Paint, PaintProgram, Pause, ToolChange, Wash, Wipe
from painter.sim.renderer import Renderer

# Fixed durations (s) of station routines on top of the travel to reach them. Design guesses for phase 1.
TOOL_CHANGE_S = 8.0
DIP_S = 4.0
WASH_S = 12.0
WIPE_S = 4.0


@dataclass
class Report:
    strokes: int = 0
    tool_changes: int = 0
    dips: int = 0
    washes: int = 0
    wipes: int = 0
    refill_pauses: int = 0
    paint_length_mm: float = 0.0
    travel_length_mm: float = 0.0
    estimated_time_s: float = 0.0
    paint_used: dict[int, float] = field(default_factory=dict)
    strokes_per_brush: dict[str, int] = field(default_factory=dict)
    ssim: float | None = None
    mean_delta_e: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["estimated_time_h"] = round(self.estimated_time_s / 3600, 2)
        return d


def station_position(action, config: MachineConfig):
    if isinstance(action, ToolChange):
        return config.rack_position(action.brush_id)
    if isinstance(action, Dip):
        return config.palette.slot_position(action.color_id)
    if isinstance(action, Wash):
        return config.wash.position
    if isinstance(action, Wipe):
        return config.wipe.position
    if isinstance(action, Paint):
        p = action.stroke.points[0]
        return config.canvas_to_machine(p.x, p.y)
    return None


def simulate(program: PaintProgram, config: MachineConfig, target_rgb: np.ndarray | None = None,
             px_per_mm: float = 2.0, video_path: str | None = None, video_frames: int = 600, fps: int = 30):
    renderer = Renderer(program, config, px_per_mm)
    report = Report(paint_used=paint_usage(program.actions))
    m = config.motion
    head = np.array([0.0, 0.0])
    writer = None
    n_paint = sum(isinstance(a, Paint) for a in program.actions)
    frame_every = max(n_paint // video_frames, 1)
    painted = 0
    current_brush = None
    if video_path:
        frame = _compose_frame(renderer.image(), program, config, head, None, "start", px_per_mm)
        writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame.shape[1], frame.shape[0]))

    for action in program.actions:
        pos = station_position(action, config)
        if pos is not None:
            d = float(np.hypot(*(np.array(pos) - head)))
            report.travel_length_mm += d
            report.estimated_time_s += d / m.travel_speed + 2 * (m.travel_z - m.hover_z) / m.z_speed
            head = np.array(pos, float)

        renderer.apply(action)
        label = None
        if isinstance(action, ToolChange):
            report.tool_changes += 1
            report.estimated_time_s += TOOL_CHANGE_S
            current_brush = action.brush_id
            label = f"tool change -> {action.brush_id}"
        elif isinstance(action, Dip):
            report.dips += 1
            report.estimated_time_s += DIP_S
        elif isinstance(action, Wash):
            report.washes += 1
            report.estimated_time_s += WASH_S
            label = "wash in oil jar"
        elif isinstance(action, Wipe):
            report.wipes += 1
            report.estimated_time_s += WIPE_S
        elif isinstance(action, Pause):
            report.refill_pauses += 1
            label = f"PAUSE: {action.reason}"
        elif isinstance(action, Paint):
            s = action.stroke
            report.strokes += 1
            report.strokes_per_brush[s.brush_id] = report.strokes_per_brush.get(s.brush_id, 0) + 1
            for a, b in zip(s.points, s.points[1:]):
                seg = float(np.hypot(b.x - a.x, b.y - a.y))
                report.paint_length_mm += seg
                report.estimated_time_s += seg / max((a.speed + b.speed) / 2, 1e-3)
            end = s.points[-1]
            head = np.array(config.canvas_to_machine(end.x, end.y))
            painted += 1
            if painted % frame_every == 0:
                label = f"{s.brush_id} color {s.color_id}  stroke {painted}/{n_paint}"

        if writer is not None and label is not None:
            writer.write(_compose_frame(renderer.image(), program, config, head, current_brush, label, px_per_mm))

    final = renderer.image()
    if writer is not None:
        last = _compose_frame(final, program, config, head, current_brush, "done", px_per_mm)
        for _ in range(fps * 2):
            writer.write(last)
        writer.release()

    if target_rgb is not None:
        tgt = cv2.resize(target_rgb, (final.shape[1], final.shape[0]), interpolation=cv2.INTER_AREA)
        report.ssim = round(ssim(final, tgt), 4)
        report.mean_delta_e = round(float(np.sqrt(((rgb_to_lab(final) - rgb_to_lab(tgt)) ** 2).sum(-1)).mean()), 2)
    report.paint_length_mm = round(report.paint_length_mm, 1)
    report.travel_length_mm = round(report.travel_length_mm, 1)
    report.estimated_time_s = round(report.estimated_time_s, 1)
    report.paint_used = {k: round(v, 2) for k, v in sorted(report.paint_used.items())}
    return final, report


def ssim(a_rgb: np.ndarray, b_rgb: np.ndarray) -> float:
    a = cv2.cvtColor(a_rgb, cv2.COLOR_RGB2GRAY).astype(np.float64)
    b = cv2.cvtColor(b_rgb, cv2.COLOR_RGB2GRAY).astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    blur = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_a, mu_b = blur(a), blur(b)
    var_a = blur(a * a) - mu_a**2
    var_b = blur(b * b) - mu_b**2
    cov = blur(a * b) - mu_a * mu_b
    s = ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / ((mu_a**2 + mu_b**2 + c1) * (var_a + var_b + c2))
    return float(s.mean())


def _compose_frame(canvas_rgb, program, config, head, brush_id, label, px_per_mm):
    """Canvas plus a side panel showing the stations (palette, oil jar, rag, brush rack) and the head."""
    s = px_per_mm
    xs = [config.canvas.origin[0] + config.canvas.width, config.palette.origin[0], config.wash.position[0],
          config.wipe.position[0] + config.wipe.length / 2, config.brush_rack.origin[0]]
    ys = [config.canvas.origin[1] + config.canvas.height,
          config.palette.slot_position(config.palette.slots - 1)[1],
          config.brush_rack.origin[1] + len(config.brushes) * config.brush_rack.pitch]
    W, H = int((max(xs) + 40) * s), int((max(ys) + 40) * s)
    H = max(H, canvas_rgb.shape[0] + 40)
    frame = np.full((H + 30, W, 3), 235, np.uint8)
    ox, oy = int(config.canvas.origin[0] * s), int(config.canvas.origin[1] * s)
    frame[oy : oy + canvas_rgb.shape[0], ox : ox + canvas_rgb.shape[1]] = canvas_rgb

    def P(xy):
        return int(xy[0] * s), int(xy[1] * s)

    r = int(14 * s)
    colors = {c.id: c.rgb for c in program.palette}
    for slot in range(config.palette.slots):
        c = colors.get(slot)
        fill = tuple(int(v) for v in c) if c else (250, 250, 250)
        cv2.circle(frame, P(config.palette.slot_position(slot)), r, fill, -1, cv2.LINE_AA)
        cv2.circle(frame, P(config.palette.slot_position(slot)), r, (80, 80, 80), 1, cv2.LINE_AA)
    cv2.circle(frame, P(config.wash.position), int(config.wash.radius * s), (200, 170, 90), -1, cv2.LINE_AA)
    cv2.putText(frame, "oil", P(config.wash.position), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    wx, wy = config.wipe.position
    cv2.rectangle(frame, P((wx - config.wipe.length / 2, wy - 10)), P((wx + config.wipe.length / 2, wy + 10)),
                  (210, 210, 255), -1)
    cv2.putText(frame, "rag", P((wx - 8, wy + 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    for b in config.brushes:
        bx, by = config.rack_position(b.id)
        on_head = b.id == brush_id
        cv2.rectangle(frame, P((bx - 20, by - 3)), P((bx + 20, by + 3)), (120, 120, 120) if on_head else (60, 40, 20), -1)
        cv2.putText(frame, b.id + (" (head)" if on_head else ""), P((bx - 20, by - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
    cv2.drawMarker(frame, P(head), (255, 0, 0), cv2.MARKER_CROSS, int(12 * s), 2)
    cv2.putText(frame, label, (10, H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

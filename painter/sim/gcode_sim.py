"""G-code simulator: runs the generated G-code (with the Klipper macros expanded) and checks it.

It interprets G0/G1/G2/G3 with X/Y/Z/A, tracks which brush is on the head (from the macro variables), works out
what the brush touches (canvas, palette slot, oil jar, rag) and rebuilds the painted strokes from canvas contact,
so the canvas it renders comes from the G-code itself, not from the PaintProgram.

Checks
- soft limits (X/Y/Z ranges, |A| limit)
- the brush touches nothing but the canvas and the stations
- painting without a brush / with a clean brush
- dipping into a palette slot with paint of another color on the brush (contamination)
- pressing deeper than the brush's press depth on the canvas
- racking a dirty brush
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from painter.config import MachineConfig
from painter.program import Dip, PaintProgram, PaletteColor, Stroke, StrokePoint, Wash
from painter.sim.klipper_macros import MacroEngine, parse_macros, parse_params

CONTACT_EPS = 0.05  # mm below a surface counts as touching
SLOT_RADIUS = 15.0  # paint pile radius on the palette
RAG_HALF_WIDTH = 12.0


@dataclass
class State:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    a: float = 0.0

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z, self.a])


@dataclass
class Segment:
    t0: float
    t1: float
    p0: np.ndarray  # x, y, z, a
    p1: np.ndarray
    feed: float  # mm/s
    rapid: bool
    line: int  # line number in the source G-code
    context: str  # top-level command (macro name or "stroke")


@dataclass
class Event:
    t: float
    kind: str  # pause | message | tool
    text: str
    line: int


@dataclass
class Issue:
    severity: str  # error | warning
    kind: str
    message: str
    line: int
    position: tuple[float, float, float, float]


@dataclass
class GcodeReport:
    lines: int = 0
    moves: int = 0
    total_time_s: float = 0.0
    travel_mm: float = 0.0
    contact_mm: float = 0.0
    strokes_rebuilt: int = 0
    macro_calls: dict[str, int] = field(default_factory=dict)
    pauses: int = 0
    max_abs_a: float = 0.0
    min_z: float = 0.0
    errors: int = 0
    warnings: int = 0
    issues_by_kind: dict[str, int] = field(default_factory=dict)
    first_issues: list[dict] = field(default_factory=list)
    unknown_commands: dict[str, int] = field(default_factory=dict)
    canvas_diff_vs_program: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_time_h"] = round(self.total_time_s / 3600, 2)
        return d


_WORD = re.compile(r"([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
IGNORED = {"G21", "G90", "M84", "M117", "RESPOND", "MANUAL_STEPPER", "RESUME"}


class Interpreter:
    """Expands macros and turns the G-code into timed motion segments and events."""

    def __init__(self, config: MachineConfig, macros_path: str | Path):
        self.config = config
        self.engine = MacroEngine(parse_macros(macros_path))
        self.state = State(z=config.motion.travel_z)
        self.feed = config.motion.travel_speed
        self.t = 0.0
        self.segments: list[Segment] = []
        self.events: list[Event] = []
        self.report = GcodeReport()
        self.palette: list[PaletteColor] = []

    # -- public -----------------------------------------------------------------------------------------------
    def run(self, gcode_text: str) -> None:
        context = "program"
        for lineno, raw in enumerate(gcode_text.splitlines(), 1):
            self.report.lines += 1
            if raw.startswith("; palette slots:"):
                self.palette = _parse_palette(raw)
            line = raw.split(";", 1)[0].strip()
            if not line:
                if raw.startswith("; stroke"):
                    context = "stroke"
                continue
            cmd = line.split()[0].upper()
            if self.engine.is_macro(cmd):
                context = cmd
            self._execute(line, lineno, context, depth=0)

    # -- internals --------------------------------------------------------------------------------------------
    def _execute(self, line: str, lineno: int, context: str, depth: int) -> None:
        if depth > 20:
            raise RecursionError(f"macro recursion too deep at line {lineno}")
        parts = line.split(maxsplit=1)
        cmd = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        if self.engine.is_macro(cmd):
            self.report.macro_calls[cmd] = self.report.macro_calls.get(cmd, 0) + 1
            for sub in self.engine.render(cmd, parse_params(args)):
                self._execute(sub.split(";", 1)[0].strip(), lineno, context, depth + 1)
            return
        if not cmd:
            return
        if cmd in ("G0", "G1"):
            self._linear(args, lineno, context, rapid=cmd == "G0")
        elif cmd in ("G2", "G3"):
            self._arc(args, lineno, context, clockwise=cmd == "G2")
        elif cmd == "G28":
            self.state = State(0.0, 0.0, self.config.motion.travel_z, 0.0)
        elif cmd == "SET_GCODE_VARIABLE":
            params = parse_params(args)
            self.engine.set_variable(params)
            if params.get("VARIABLE", "").lower() == "current_brush":
                self.events.append(Event(self.t, "tool", params["VALUE"], lineno))
        elif cmd == "PAUSE":
            self.report.pauses += 1
            self.events.append(Event(self.t, "pause", context, lineno))
        elif cmd in ("M117", "RESPOND"):
            self.events.append(Event(self.t, "message", args, lineno))
        elif cmd in IGNORED:
            pass
        else:
            self.report.unknown_commands[cmd] = self.report.unknown_commands.get(cmd, 0) + 1

    def _words(self, args: str) -> dict[str, float]:
        return {k.upper(): float(v) for k, v in _WORD.findall(args)}

    def _move_to(self, target: np.ndarray, rapid: bool, lineno: int, context: str) -> None:
        p0 = self.state.as_array()
        xyz = float(np.linalg.norm(target[:3] - p0[:3]))
        # Klipper: the feed rate applies to the XYZ distance; a pure A move uses it for A.
        dist = xyz if xyz > 1e-9 else abs(target[3] - p0[3])
        if dist < 1e-9:
            return
        dt = dist / max(self.feed, 1e-6)
        self.segments.append(Segment(self.t, self.t + dt, p0, target.copy(), self.feed, rapid, lineno, context))
        self.t += dt
        self.report.moves += 1
        self.state = State(*target.tolist())

    def _linear(self, args: str, lineno: int, context: str, rapid: bool) -> None:
        w = self._words(args)
        if "F" in w:
            self.feed = w["F"] / 60.0
        s = self.state
        target = np.array([w.get("X", s.x), w.get("Y", s.y), w.get("Z", s.z), w.get("A", s.a)])
        self._move_to(target, rapid, lineno, context)

    def _arc(self, args: str, lineno: int, context: str, clockwise: bool) -> None:
        w = self._words(args)
        if "F" in w:
            self.feed = w["F"] / 60.0
        s = self.state
        cx, cy = s.x + w.get("I", 0.0), s.y + w.get("J", 0.0)
        ex, ey = w.get("X", s.x), w.get("Y", s.y)
        r = math.hypot(s.x - cx, s.y - cy)
        a0 = math.atan2(s.y - cy, s.x - cx)
        a1 = math.atan2(ey - cy, ex - cx)
        # Y grows downward on screen but arcs are defined in machine coordinates (standard G2 = clockwise).
        sweep = a1 - a0
        if clockwise:
            sweep = sweep - 2 * math.pi if sweep >= 0 else sweep
        else:
            sweep = sweep + 2 * math.pi if sweep <= 0 else sweep
        n = max(int(abs(sweep) * r / 1.0), 8)
        z0, z1 = s.z, w.get("Z", s.z)
        for i in range(1, n + 1):
            ang = a0 + sweep * i / n
            pt = np.array([cx + r * math.cos(ang), cy + r * math.sin(ang), z0 + (z1 - z0) * i / n, s.a])
            self._move_to(pt, False, lineno, context)


def _parse_palette(line: str) -> list[PaletteColor]:
    out = []
    for slot, hexcode in re.findall(r"(\d+)=#([0-9A-Fa-f]{6})", line):
        rgb = tuple(int(hexcode[i : i + 2], 16) for i in (0, 2, 4))
        out.append(PaletteColor(int(slot), rgb, 0.0))
    return out


class Checker:
    """Follows the brush through the segments: what it touches, which paint it carries, and safety limits."""

    def __init__(self, config: MachineConfig, palette: list[PaletteColor], max_listed: int = 50):
        self.config = config
        self.palette = palette
        self.max_listed = max_listed
        self.brush_index: int = -1
        self.color: int | None = None  # paint on the bristles
        self.issues: list[Issue] = []
        self.contact: str | None = None
        self.current_points: list[StrokePoint] = []
        self.strokes: list[Stroke] = []
        # (time, Dip | Wash | Stroke) in the order they happen, for rendering the canvas from the G-code.
        self.timeline: list[tuple[float, object]] = []
        self.travel_mm = 0.0
        self.contact_mm = 0.0
        self.max_abs_a = 0.0
        self.min_z = float("inf")
        self._reported: set[tuple[str, int]] = set()

    @property
    def brush(self):
        if 0 <= self.brush_index < len(self.config.brushes):
            return self.config.brushes[self.brush_index]
        return None

    def issue(self, severity, kind, message, line, p) -> None:
        key = (kind, line)
        if key in self._reported:
            return
        self._reported.add(key)
        self.issues.append(Issue(severity, kind, message, line, tuple(round(float(v), 2) for v in p)))

    def zone(self, x: float, y: float) -> tuple[str, int | None]:
        c = self.config
        cx, cy = c.canvas.origin
        if cx <= x <= cx + c.canvas.width and cy <= y <= cy + c.canvas.height:
            return "canvas", None
        for slot in range(c.palette.slots):
            sx, sy = c.palette.slot_position(slot)
            if math.hypot(x - sx, y - sy) <= SLOT_RADIUS:
                return "palette", slot
        if math.hypot(x - c.wash.position[0], y - c.wash.position[1]) <= c.wash.radius:
            return "wash", None
        wx, wy = c.wipe.position
        if abs(x - wx) <= c.wipe.length / 2 + 2 and abs(y - wy) <= RAG_HALF_WIDTH:
            return "wipe", None
        return "none", None

    def on_tool_event(self, value: str, t: float, line: int, p) -> None:
        new = int(value)
        if new < 0 and self.color is not None:
            self.issue("warning", "dirty_brush_racked", "brush returned to the rack with paint on it", line, p)
        if new >= 0:
            self.color = None
        self.brush_index = new

    def step(self, seg: Segment, seg_index: int) -> None:
        c = self.config
        m = c.motion
        dist = float(np.linalg.norm(seg.p1[:3] - seg.p0[:3]))
        # Sample along the segment so a long move is checked along its whole length.
        n = max(int(dist / 2.0), 1)
        for i in range(1, n + 1):
            p = seg.p0 + (seg.p1 - seg.p0) * (i / n)
            self._check_point(p, seg, seg_index)
        self.max_abs_a = max(self.max_abs_a, abs(float(seg.p1[3])))
        self.min_z = min(self.min_z, float(seg.p1[2]))
        if self.contact == "canvas":
            self.contact_mm += dist
        else:
            self.travel_mm += dist
        x, y, z, a = seg.p1
        if not (m.x_range[0] <= x <= m.x_range[1] and m.y_range[0] <= y <= m.y_range[1]):
            self.issue("error", "soft_limit_xy", "outside the gantry travel", seg.line, seg.p1)
        if not (m.z_range[0] <= z <= m.z_range[1]):
            self.issue("error", "soft_limit_z", "Z outside its travel", seg.line, seg.p1)
        if abs(a) > m.a_limit:
            self.issue("error", "a_limit", f"|A| {abs(a):.0f} deg exceeds {m.a_limit:.0f}", seg.line, seg.p1)

    def _check_point(self, p: np.ndarray, seg: Segment, seg_index: int) -> None:
        x, y, z, a = (float(v) for v in p)
        surface = self.config.canvas.surface_z
        touching = z < surface - CONTACT_EPS
        zone, slot = self.zone(x, y) if touching else (None, None)
        new_contact = zone if touching else None

        if self.contact == "canvas" and new_contact != "canvas":
            self._finish_stroke(seg.t1, seg_index)
        if new_contact is None:
            self.contact = None
            return

        brush = self.brush
        if brush is None:
            self.issue("error", "no_brush", f"touching {zone} with no brush on the head", seg.line, p)
        if zone == "none":
            self.issue("error", "unexpected_contact", "brush touches outside canvas and stations", seg.line, p)
        elif zone == "canvas":
            if brush is not None:
                depth = surface - z
                if depth > brush.press_depth * 1.05:
                    self.issue("error", "too_deep", f"pressing {depth:.1f} mm (max {brush.press_depth})", seg.line, p)
                if self.contact != "canvas" and self.color is None:
                    self.issue("warning", "clean_brush_on_canvas", "painting with a clean brush", seg.line, p)
                pressure = min(max(depth / brush.press_depth, 0.0), 1.0)
                cx, cy = self.config.canvas.origin
                self.current_points.append(StrokePoint(x - cx, y - cy, pressure, a, seg.feed))
        elif zone == "palette" and self.contact != "palette":
            if self.color is not None and self.color != slot:
                self.issue("error", "contamination",
                           f"brush carries color {self.color} but dips into slot {slot}", seg.line, p)
            self.color = slot
            self.timeline.append((seg.t1, Dip(slot, 0.0)))
        elif zone == "wash" and self.contact != "wash":
            self.color = None
            self.timeline.append((seg.t1, Wash()))
        self.contact = new_contact

    def _finish_stroke(self, t: float, seg_index: int) -> None:
        pts = self.current_points
        self.current_points = []
        brush = self.brush
        if brush is None or len(pts) < 1:
            return
        if len(pts) == 1:
            pts = pts * 2
        stroke = Stroke(brush.id, self.color if self.color is not None else -1, 0, pts)
        self.strokes.append(stroke)
        self.timeline.append((t, stroke))


def run_gcode(gcode_text: str, config: MachineConfig, macros_path: str | Path):
    interp = Interpreter(config, macros_path)
    interp.run(gcode_text)
    checker = Checker(config, interp.palette)
    events = sorted(interp.events, key=lambda e: e.t)
    ei = 0
    for i, seg in enumerate(interp.segments):
        while ei < len(events) and events[ei].t <= seg.t0:
            ev = events[ei]
            if ev.kind == "tool":
                checker.on_tool_event(ev.text, ev.t, ev.line, seg.p0)
            ei += 1
        checker.step(seg, i)
    for ev in events[ei:]:
        if ev.kind == "tool":
            checker.on_tool_event(ev.text, ev.t, ev.line, interp.state.as_array())
    if checker.contact == "canvas":
        checker._finish_stroke(interp.t, len(interp.segments) - 1)

    r = interp.report
    r.total_time_s = round(interp.t, 1)
    r.travel_mm = round(checker.travel_mm, 1)
    r.contact_mm = round(checker.contact_mm, 1)
    r.strokes_rebuilt = len(checker.strokes)
    r.max_abs_a = round(checker.max_abs_a, 2)
    r.min_z = round(checker.min_z, 3) if checker.min_z != float("inf") else 0.0
    r.errors = sum(i.severity == "error" for i in checker.issues)
    r.warnings = sum(i.severity == "warning" for i in checker.issues)
    for i in checker.issues:
        r.issues_by_kind[i.kind] = r.issues_by_kind.get(i.kind, 0) + 1
    r.first_issues = [asdict(i) for i in checker.issues[: checker.max_listed]]
    return interp, checker


def load_gcode(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def program_shell(config: MachineConfig, palette: list[PaletteColor]) -> PaintProgram:
    """An empty PaintProgram carrying the canvas size and palette, for the Renderer."""
    # id -1 = paint of unknown color (a stroke made with a clean brush); shown in gray
    return PaintProgram((config.canvas.width, config.canvas.height), list(palette) + [PaletteColor(-1, (128, 128, 128), 0)])

from pathlib import Path

import cv2
import numpy as np
import pytest

from painter.analysis.palette import extract_palette
from painter.backends.klipper_gcode import to_gcode
from painter.cli import DEFAULT_CONFIG, DEFAULT_MACROS, build_program, main
from painter.config import load_config
from painter.planner.sequencer import plan
from painter.program import Dip, Paint, PaintProgram, Pause, Stroke, StrokePoint, ToolChange, Wash, Wipe
from painter.sim.animator import simulate
from painter.strokes.human_motion import MotionParams, brush_angles, pressure_profile


@pytest.fixture(scope="module")
def config():
    return load_config(DEFAULT_CONFIG)


@pytest.fixture(scope="module")
def image_path(tmp_path_factory):
    """Synthetic scene: sky gradient, a dark mountain, a red sun."""
    h, w = 318, 410
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = np.linspace([235, 200, 150], [180, 120, 60], h)[:, None, :].astype(np.uint8)  # BGR sky
    pts = np.array([[0, h], [w // 2, 90], [w, h]], np.int32)
    cv2.fillPoly(img, [pts], (70, 50, 40))
    cv2.circle(img, (320, 70), 30, (40, 40, 220), -1)
    path = tmp_path_factory.mktemp("img") / "scene.png"
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture(scope="module")
def program(image_path, config):
    prog, _ = build_program(image_path, config, n_colors=5, px_per_mm=1.0, seed=0, threshold=12.0,
                            threshold_growth=0.5, max_strokes_per_layer=None)
    return prog


def test_palette_sorted_and_complete():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (40, 50, 3), dtype=np.uint8)
    pal = extract_palette(img, 6)
    assert pal.colors_rgb.shape == (6, 3)
    assert pal.labels.shape == (40, 50)
    assert set(np.unique(pal.labels)) <= set(range(6))
    assert pal.coverage.sum() == pytest.approx(1.0)
    lightness = cv2.cvtColor(pal.colors_rgb.reshape(1, -1, 3), cv2.COLOR_RGB2LAB)[0, :, 0]
    assert list(lightness) == sorted(lightness)


def test_pressure_profile_has_entry_and_lift_off():
    t = np.linspace(0, 1, 101)
    p = pressure_profile(t, MotionParams())
    assert p[0] == pytest.approx(0.25)
    assert p[50] == pytest.approx(0.7)
    assert p[-1] == pytest.approx(0.05)


def test_flat_brush_angles_unwrap_mod_180():
    # A path reversing direction: a flat brush should not spin 180 degrees.
    path = np.array([[0, 0], [1, 0], [2, 0], [1, 0], [0, 0]], float)
    ang = brush_angles(path, symmetric=True)
    assert np.abs(np.diff(ang)).max() <= 90


def test_strokes_inside_canvas(program, config):
    strokes = program.strokes()
    assert len(strokes) > 50
    for s in strokes:
        for p in s.points:
            assert -0.5 <= p.x <= config.canvas.width + 0.5
            assert -0.5 <= p.y <= config.canvas.height + 0.5
            assert 0.0 <= p.pressure <= 1.0
    # coarse brush paints first
    layers = [s.layer for s in strokes]
    assert layers == sorted(layers)


def test_process_invariants(program, config):
    """Brush is clean before a new color, the right color is on it when painting, and washed before racking."""
    holding = None
    on_brush = None  # color on the bristles
    seen_tool_changes = 0
    for a in program.actions:
        if isinstance(a, ToolChange):
            assert on_brush is None, "brush must be washed before it goes back to the rack"
            holding = a.brush_id
            seen_tool_changes += 1
        elif isinstance(a, Dip):
            assert holding is not None
            assert on_brush in (None, a.color_id), "dipping a new color onto a dirty brush"
            on_brush = a.color_id
        elif isinstance(a, Wash):
            on_brush = None
        elif isinstance(a, Paint):
            assert a.stroke.brush_id == holding
            assert a.stroke.color_id == on_brush
    assert on_brush is None
    assert seen_tool_changes == len({s.brush_id for s in program.strokes()})
    # every wash is followed by a wipe
    for a, b in zip(program.actions, program.actions[1:]):
        if isinstance(a, Wash):
            assert isinstance(b, Wipe)


def test_refill_pause_when_slot_runs_low(config):
    small = config.model_copy(deep=True)
    small.palette.slot_capacity = 5.0
    small.palette.refill_threshold = 1.0
    pts = [StrokePoint(x, 10.0, 0.7, 0.0, 50.0) for x in np.linspace(0, 300, 50)]
    strokes = [Stroke("flat_large", 0, 0, list(pts)) for _ in range(20)]
    actions = plan(strokes, small)
    assert any(isinstance(a, Pause) and a.color_id == 0 for a in actions)


def test_json_roundtrip(program, tmp_path):
    path = tmp_path / "p.json"
    program.save(path)
    again = PaintProgram.load(path)
    assert again.to_dict() == PaintProgram.from_dict(program.to_dict()).to_dict()
    assert len(again.actions) == len(program.actions)


def test_simulation_covers_canvas(program, config, image_path):
    final, report = simulate(program, config, None, px_per_mm=1.0)
    assert report.strokes == len(program.strokes())
    assert report.washes == report.wipes
    unpainted = (final.min(-1) > 250).mean()
    assert unpainted < 0.01


def test_gcode(program, config):
    g = to_gcode(program, config)
    assert g.count("TOOL_CHANGE") == sum(isinstance(a, ToolChange) for a in program.actions)
    assert g.count("\nWASH") == sum(isinstance(a, Wash) for a in program.actions)
    a_values = [float(tok[1:]) for line in g.splitlines() if line.startswith(("G0", "G1"))
                for tok in line.split() if tok.startswith("A")]
    assert a_values and max(abs(v) for v in a_values) <= config.motion.a_limit
    # brush never goes deeper than its press depth
    deepest = min(config.canvas.surface_z - b.press_depth for b in config.brushes)
    z = [float(tok[1:]) for line in g.splitlines() if line.startswith("G1")
         for tok in line.split() if tok.startswith("Z")]
    assert min(z) >= deepest - 1e-6


def test_cli_run(image_path, tmp_path):
    main(["--px-per-mm", "1", "run", image_path, "-o", str(tmp_path), "--colors", "4"])
    for name in ["program.json", "palette_sheet.png", "canvas.png", "report.json", "program.gcode"]:
        assert (Path(tmp_path) / name).exists()


# --- G-code simulator ---------------------------------------------------------------------------------------------

from painter.sim.gcode_sim import run_gcode  # noqa: E402
from painter.sim.gcode_player import render_canvas  # noqa: E402
from painter.sim.klipper_macros import MacroEngine, parse_macros  # noqa: E402
from painter.sim.renderer import render_program  # noqa: E402
from painter.sim.stroke_inspector import inspect, select_strokes  # noqa: E402


def test_generated_gcode_runs_clean(program, config):
    """The generated G-code, run through the real macros, raises no safety issue and paints the same picture."""
    interp, checker = run_gcode(to_gcode(program, config), config, DEFAULT_MACROS)
    r = interp.report
    assert r.errors == 0 and r.warnings == 0, r.first_issues[:5]
    assert r.unknown_commands == {}
    assert r.strokes_rebuilt == len(program.strokes())
    assert r.macro_calls["WASH"] == sum(isinstance(a, Wash) for a in program.actions)
    canvas = render_canvas(interp, checker, config, 1.0)
    expected = render_program(program, config, 1.0)
    assert np.abs(canvas.astype(float) - expected).mean() / 255 < 0.02


def test_wash_macro_stays_in_jar(config):
    """Regression: `{-x}` in a Klipper template is Jinja whitespace control and silently drops the sign."""
    engine = MacroEngine(parse_macros(DEFAULT_MACROS))
    arcs = [ln for ln in engine.render("WASH", {}) if ln.startswith("G2")]
    assert arcs and all(" I-" in ln for ln in arcs)


def _issues(gcode, config):
    interp, _ = run_gcode(gcode, config, DEFAULT_MACROS)
    return interp.report.issues_by_kind


def test_checker_detects_contamination(config):
    assert "contamination" in _issues("PAINTER_START\nTOOL_CHANGE BRUSH=0\nDIP SLOT=0\nDIP SLOT=1\n", config)
    assert "contamination" not in _issues("PAINTER_START\nTOOL_CHANGE BRUSH=0\nDIP SLOT=0\nWASH\nWIPE\nDIP SLOT=1\n", config)


def test_checker_detects_unsafe_moves(config):
    g = "\n".join([
        "PAINTER_START", "TOOL_CHANGE BRUSH=3", "DIP SLOT=0",
        "G0 X100 Y100", "G1 Z-5 F600",                 # round_small presses 1.5 mm at most
        "G0 Z15", "G0 X20 Y390", "G1 Z-1",              # nothing to touch there
        "G0 Z15", "G0 X100 Y100 A300",                  # rotation beyond the limit
        "G0 X700",                                      # beyond the gantry
    ])
    kinds = _issues(g, config)
    assert {"too_deep", "unexpected_contact", "a_limit", "soft_limit_xy"} <= set(kinds)


def test_checker_detects_painting_without_brush(config):
    assert "no_brush" in _issues("PAINTER_START\nG0 X100 Y100\nG1 Z-1\n", config)


def test_stroke_inspector(program, config, tmp_path):
    idx = select_strokes(program, None, 0, 0)
    assert len(idx) == len({s.brush_id for s in program.strokes()})
    results = inspect(program, config, idx[:1], tmp_path, px_per_mm=1.0, slow=1.0)
    assert Path(results[0]["video"]).stat().st_size > 0
    assert Path(results[0]["image"]).exists()
    assert results[0]["min_z"] >= config.canvas.surface_z - config.brush(results[0]["brush"]).press_depth - 1e-6


def test_cli_gcode_sim(program, config, tmp_path):
    program.save(tmp_path / "p.json")
    (tmp_path / "p.gcode").write_text(to_gcode(program, config))
    code = main(["--px-per-mm", "1", "gcode-sim", str(tmp_path / "p.gcode"), "-o", str(tmp_path / "sim"),
                 "--program", str(tmp_path / "p.json"), "--video", "--end", "60", "--speed", "4"])
    assert code == 0
    assert (tmp_path / "sim" / "gcode_sim.mp4").stat().st_size > 0


# --- closed loop (camera) -----------------------------------------------------------------------------------------

from painter.feedback.camera import FlatField, SimCamera, rectify  # noqa: E402
from painter.feedback.loop import LoopParams, compare, paint_closed_loop  # noqa: E402
from painter.feedback.world import RealityParams, SimWorld  # noqa: E402


def _world(program, config, reality=RealityParams()):
    return SimWorld(PaintProgram(program.canvas_size, program.palette), config, 1.0, reality)


def test_camera_rectify_recovers_canvas(program, config):
    """Photo -> rectify + flat-field gives back what is on the canvas despite perspective and uneven light."""
    world = _world(program, config, RealityParams(width_scale=1, opacity=1, capacity_scale=1, position_noise_mm=0,
                                                  mix_error_rgb=0))
    cam = SimCamera(world, config)
    flat = FlatField(rectify(cam.capture(), config, 1.0))
    for a in program.actions:
        world.apply(a)
    seen = flat.apply(rectify(cam.capture(), config, 1.0))
    _, de, _, _ = compare(seen, world.image())
    assert seen.shape == world.image().shape
    assert de < 5.0


def test_closed_loop_beats_open_loop(program, config, image_path, tmp_path):
    target = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
    open_world = _world(program, config)
    for a in program.actions:
        open_world.apply(a)
    _, de_open, off_open, _ = compare(open_world.image(), target)

    world = _world(program, config)
    prog, steps = paint_closed_loop(target, program.palette, config, SimCamera(world, config),
                                    lambda chunk: [world.apply(a) for a in chunk], 1.0,
                                    LoopParams(touchup_rounds=1), tmp_path)
    _, de_closed, off_closed, _ = compare(world.image(), target)
    assert steps[0].name == "blank canvas" and len(steps) >= len(config.brushes) + 1
    assert steps[-1].delta_e < steps[1].delta_e  # every photo-driven layer improves the picture
    assert de_closed < de_open and off_closed < off_open
    # the combined program is still a valid process (washed before color changes, valid G-code)
    interp, _ = run_gcode(to_gcode(prog, config), config, DEFAULT_MACROS)
    assert interp.report.errors == 0

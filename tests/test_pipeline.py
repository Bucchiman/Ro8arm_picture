from pathlib import Path

import cv2
import numpy as np
import pytest

from painter.analysis.palette import extract_palette
from painter.backends.klipper_gcode import to_gcode
from painter.cli import DEFAULT_CONFIG, build_program, main
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
    a_values = [float(tok[1:]) for line in g.splitlines() if line.startswith("G0 X")
                for tok in line.split() if tok.startswith("A")]
    assert a_values and max(abs(v) for v in a_values) <= 180.0
    # brush never goes deeper than its press depth
    deepest = min(config.canvas.surface_z - b.press_depth for b in config.brushes)
    z = [float(tok[1:]) for line in g.splitlines() if line.startswith("G1")
         for tok in line.split() if tok.startswith("Z")]
    assert min(z) >= deepest - 1e-6


def test_cli_run(image_path, tmp_path):
    main(["--px-per-mm", "1", "run", image_path, "-o", str(tmp_path), "--colors", "4"])
    for name in ["program.json", "palette_sheet.png", "canvas.png", "report.json", "program.gcode"]:
        assert (Path(tmp_path) / name).exists()

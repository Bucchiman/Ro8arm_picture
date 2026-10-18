import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("manifold3d")
pytest.importorskip("trimesh")

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "machine" / "cad" / "machine.py"


@pytest.fixture(scope="module")
def cad():
    spec = importlib.util.spec_from_file_location("machine_cad", CAD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["machine_cad"] = mod   # dataclasses look the module up while the file runs
    spec.loader.exec_module(mod)
    return mod


def test_all_checks_pass(cad):
    ok, results = cad.check(verbose=False)
    assert ok, "\n".join(r for r in results if r.startswith("NG"))


def test_layout_follows_the_config(cad):
    """The CAD reads its stations from configs/machine_final.yaml, the same file the twin and the G-code use."""
    from painter.config import load_config

    c = load_config(ROOT / "configs" / "machine_final.yaml")
    assert cad.slot_xy(3) == c.palette.slot_position(3)
    assert cad.rack_xy(2) == c.rack_position(c.brushes[2].id)
    assert cad.WASH_R == c.wash.radius * 0.5
    macros = (ROOT / "klipper" / "macros.cfg").read_text(encoding="utf-8")
    assert f"variable_rack_slide: {cad.RACK_SLIDE:g}" in macros


def test_printed_parts_are_watertight(cad, tmp_path):
    parts, labels = cad.labeled_parts()
    for name, m in parts.items():
        assert labels[name] and labels[name].startswith(f"{cad.PREFIX}{cad.VERSION}"), name
        t = cad.save_stl(m, tmp_path / f"{name}.stl")
        assert t.is_watertight and t.volume > 0, name
        assert abs(t.bounds[0][2]) < 1e-6, f"{name} is not on the bed"


def test_travel_check_catches_a_park_in_the_rack_column(cad, monkeypatch):
    """Regression: the first layout parked the camera at (690, 440); moving there with a brush crosses the rack."""
    monkeypatch.setitem(cad.CAM, "park", [cad.RACK["origin"][0], 440])
    ok, results = cad.check(verbose=False)
    assert not ok
    assert any(r.startswith("NG") and "park" in r for r in results)


def test_glb_export(cad, tmp_path):
    import trimesh

    path = tmp_path / "a.glb"
    cad.save_glb(cad.assembly(230.0, 200.0, cad.TRAVEL_Z, 30.0, "flat_large"), path)
    s = trimesh.load(path)
    assert len(s.geometry) > 40
    assert 0.8 < s.extents[0] < 1.2   # metres


def test_version_bumped_when_geometry_changes(cad):
    parts, _ = cad.labeled_parts()
    problems = cad.check_manifest(str(CAD.parent / "out" / "manifest.json"), f"{cad.PREFIX}{cad.VERSION}", parts)
    assert not problems, problems


def test_manifest_detects_a_forgotten_bump(cad, tmp_path):
    from manifold3d import Manifold

    parts, labels = cad.labeled_parts()
    path = str(tmp_path / "manifest.json")
    cad.write_manifest(path, "M1", parts, labels)
    assert cad.check_manifest(path, "M1", parts) == []
    changed = dict(parts, foot=parts["foot"] + Manifold.cube((1, 1, 1)).translate((50, 50, 0)))
    assert "バージョン" in cad.check_manifest(path, "M1", changed)[0]
    assert "古い" in cad.check_manifest(path, "M2", changed)[0]

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("manifold3d")
pytest.importorskip("trimesh")

RIG = Path(__file__).resolve().parent.parent / "rig" / "cad" / "rig.py"


@pytest.fixture(scope="module")
def rig():
    spec = importlib.util.spec_from_file_location("rig_cad", RIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_all_checks_pass(rig, capsys):
    ok = rig.check()
    out = capsys.readouterr().out
    assert ok, "\n".join(line for line in out.splitlines() if line.startswith("NG"))


def test_parts_are_watertight_and_fit_bed(rig, tmp_path):
    for name, m in rig.print_orient().items():
        t = rig.save_stl(m, tmp_path / f"{name}.stl")
        size = t.bounds[1] - t.bounds[0]
        assert t.is_watertight and t.volume > 0, name
        assert size[0] <= rig.BED_W and size[1] <= rig.BED_D, name
        assert abs(t.bounds[0][2]) < 1e-6, f"{name} is not on the bed"


def test_layout_json_is_relative_to_marker0(rig):
    lay = rig.layout_json()
    assert lay["bed"]["markers"]["0"] == [0.0, 0.0]
    assert lay["head"]["brush_offset_from_nozzle"] == [0.0, rig.BRUSH_Y, -rig.TIP_BELOW_NOZZLE]
    assert set(lay["bed"]["stations"]) == {"paint_a", "paint_b", "wash", "wipe"}

import base64
import gzip
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from painter.cli import DEFAULT_MACROS, build_program, main
from painter.config import load_config
from painter.twin.export import build_twin, macros_for_config

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "configs" / "machine_final.yaml"


def unpack(b64, dtype):
    return np.frombuffer(gzip.decompress(base64.b64decode(b64)), dtype)


@pytest.fixture(scope="module")
def final_config():
    return load_config(FINAL)


@pytest.fixture(scope="module")
def image_path(tmp_path_factory):
    h, w = 318, 410
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = np.linspace([235, 200, 150], [180, 120, 60], h)[:, None, :].astype(np.uint8)
    cv2.fillPoly(img, [np.array([[0, h], [w // 2, 90], [w, h]], np.int32)], (70, 50, 40))
    cv2.circle(img, (320, 70), 30, (40, 40, 220), -1)
    p = tmp_path_factory.mktemp("img") / "scene.png"
    cv2.imwrite(str(p), img)
    return p


def test_macros_follow_the_config(final_config):
    text = macros_for_config(DEFAULT_MACROS.read_text(encoding="utf-8"), final_config)
    assert "variable_palette_x0: 500\n" in text and "variable_wash_x: 630\n" in text
    assert "variable_rack_x: 640\n" in text and "variable_rack_y0: 280\n" in text
    with pytest.raises(ValueError):
        macros_for_config("no variables here", final_config)


def test_twin_data_replays_a_clean_run(final_config, image_path):
    program, _ = build_program(str(image_path), final_config, 4, 2.0, 0, 12.0, 2.0, 300)
    data, report = build_twin(program, final_config, DEFAULT_MACROS.read_text(encoding="utf-8"), None, "t")
    assert report["errors"] == 0, report["first_issues"][:3]   # the final layout + generated macros are consistent
    m, s = data["motion"], data["strokes"]
    t = unpack(m["t"], np.float64)
    xy = unpack(m["xy"], np.uint16).reshape(-1, 2) * 0.02
    assert len(t) == m["n"] and np.all(np.diff(t) >= 0) and abs(t[-1] - data["total_s"]) < 1e-6
    (x0, x1), (y0, y1) = final_config.motion.x_range, final_config.motion.y_range
    assert x0 - 0.05 <= xy[:, 0].min() and xy[:, 0].max() <= x1 + 0.05      # inside the gantry travel
    assert y0 - 0.05 <= xy[:, 1].min() and xy[:, 1].max() <= y1 + 0.05
    assert s["n"] == report["strokes_rebuilt"] > 0
    t0, t1 = unpack(s["t0"], np.float32), unpack(s["t1"], np.float32)
    assert np.all(t1 >= t0) and np.all(np.diff(t1) >= 0)
    assert unpack(s["npts"], np.uint16).sum() == len(unpack(s["pressure"], np.uint8))
    assert len(data["events"]["tools"]) >= 2 and data["images"]["final"].startswith("data:image/jpeg;base64,")


def test_cli_twin_writes_viewer(image_path, tmp_path):
    out = tmp_path / "twin"
    main(["-c", str(FINAL), "twin", str(image_path), "-o", str(out), "--colors", "4", "--threshold-growth", "2.0",
          "--max-strokes-per-layer", "200"])
    html = (out / "index.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and "twin_data.json" in html
    data = json.loads((out / "twin_data.json").read_text(encoding="utf-8"))
    assert data["machine"]["motion"]["x_range"] == [0.0, 700.0] and data["title"] == "scene"

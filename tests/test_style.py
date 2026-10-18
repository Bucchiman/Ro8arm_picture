import json

import cv2
import numpy as np
import pytest

from painter.analysis.palette import crop_to_aspect
from painter.cli import DEFAULT_CONFIG
from painter.config import load_config
from painter.style.presets import CUSTOM, PRESETS
from painter.style.stylizer import Stylizer, generation_size, make_request
from painter.webui import Session


class FakeBackend:
    """Stands in for SDXL: posterizes the input so the simulator has something to paint."""

    def __init__(self):
        self.calls = []

    def __call__(self, image_rgb, control_rgb, req):
        self.calls.append((image_rgb.shape, control_rgb.shape, req))
        return (image_rgb // 64 * 64 + 32).astype(np.uint8)


@pytest.fixture(scope="module")
def config():
    return load_config(DEFAULT_CONFIG)


@pytest.fixture
def photo():
    """Portrait-shaped image (wrong aspect for the landscape canvas) with a dark triangle and a red disc."""
    img = np.full((600, 400, 3), (150, 190, 230), np.uint8)
    cv2.fillPoly(img, [np.array([[0, 600], [200, 250], [400, 600]], np.int32)], (60, 50, 70))
    cv2.circle(img, (300, 200), 40, (220, 40, 40), -1)
    return img


def test_presets_have_prompts():
    assert len(PRESETS) >= 8
    for key, p in PRESETS.items():
        assert p.label
        assert key == CUSTOM or p.prompt
        assert 0 < p.strength <= 1 and 0 <= p.controlnet_scale <= 2


def test_crop_to_aspect():
    img = np.zeros((600, 400, 3), np.uint8)
    out = crop_to_aspect(img, 410 / 318)
    assert out.shape[1] == 400 and abs(out.shape[1] / out.shape[0] - 410 / 318) < 0.01
    wide = crop_to_aspect(np.zeros((300, 1000, 3), np.uint8), 410 / 318)
    assert wide.shape[0] == 300 and abs(wide.shape[1] / 300 - 410 / 318) < 0.01


def test_generation_size_multiple_of_64():
    w, h = generation_size(410 / 318)
    assert w % 64 == 0 and h % 64 == 0
    assert abs(w / h - 410 / 318) < 0.05
    assert 0.8e6 < w * h < 1.2e6


def test_make_request():
    r = make_request("ukiyoe", seed=3)
    assert "ukiyo-e" in r.prompt and r.strength == PRESETS["ukiyoe"].strength and r.seed == 3
    assert make_request("ukiyoe", "sunset").prompt.endswith(", sunset")
    assert make_request(CUSTOM, "a cubist painting", strength=0.5).prompt == "a cubist painting"
    with pytest.raises(ValueError):
        make_request(CUSTOM, "  ")


def test_stylizer_crops_and_seeds(config, photo):
    fake = FakeBackend()
    out = Stylizer(config.canvas.width / config.canvas.height, fake).stylize(photo, make_request("monet", seed=7), 3)
    assert len(out) == 3
    shape, control_shape, _ = fake.calls[0]
    assert shape == control_shape and shape[:2] == generation_size(410 / 318)[::-1]
    assert [c[2].seed for c in fake.calls] == [7, 8, 9]


def test_session_stylize_then_simulate(config, photo, tmp_path):
    session = Session(config, out_root=tmp_path, backend=FakeBackend())
    paths = session.stylize(photo, "impasto_oil", n_images=2)
    assert [p.name for p in paths] == ["styled_0.png", "styled_1.png"]
    run_dir = paths[0].parent
    assert (run_dir / "input.png").exists()
    meta = json.loads((run_dir / "style.json").read_text(encoding="utf-8"))
    assert meta["preset"] == "impasto_oil" and meta["n_images"] == 2

    r = session.simulate(paths[1], n_colors=4, threshold_growth=2.0)
    assert r["dir"] == run_dir / "sim_1"
    for key in ("canvas", "palette", "gcode"):
        assert r[key].exists() and r[key].stat().st_size > 0
    assert r["video"] is None
    assert r["report"]["strokes"] > 0
    assert all(isinstance(k, str) for k in r["report"]["paint_used"])  # gradio's JSON component rejects int keys
    assert (r["dir"] / "report.json").exists() and (r["dir"] / "program.json").exists()


def test_build_ui(config, tmp_path):
    pytest.importorskip("gradio")
    from painter.webui import build_ui

    demo = build_ui(Session(config, out_root=tmp_path, backend=FakeBackend()))
    assert demo is not None


@pytest.fixture
def heic_path(photo, tmp_path):
    """The portrait photo stored as HEIC, sideways on disk with EXIF orientation 6 (rotate 90° CW), like an iPhone."""
    pytest.importorskip("pillow_heif")
    from PIL import Image
    from pillow_heif import register_heif_opener

    register_heif_opener()
    sideways = np.ascontiguousarray(np.rot90(photo, k=1))  # 90° CCW: EXIF 6 rotates it back
    exif = Image.Exif()
    exif[0x0112] = 6
    path = tmp_path / "photo.HEIC"
    Image.fromarray(sideways).save(path, format="HEIF", quality=95, exif=exif.tobytes())
    return path


def test_read_rgb_heic_upright(photo, heic_path):
    from painter.analysis.palette import read_rgb

    rgb = read_rgb(heic_path)
    assert rgb.shape == photo.shape and rgb.dtype == np.uint8
    assert np.abs(rgb.astype(int) - photo).mean() < 6  # lossy, but upright and same content


def test_read_rgb_errors(tmp_path):
    from painter.analysis.palette import read_rgb

    with pytest.raises(FileNotFoundError):
        read_rgb(tmp_path / "missing.heic")
    bad = tmp_path / "bad.heic"
    bad.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        read_rgb(bad)


def test_cli_run_heic(heic_path, tmp_path):
    from painter.cli import main

    out = tmp_path / "run"
    main(["run", str(heic_path), "-o", str(out), "--colors", "4", "--threshold-growth", "2.0"])
    assert (out / "canvas.png").exists() and (out / "program.gcode").exists()


def test_webui_upload_heic(config, photo, heic_path, tmp_path):
    pytest.importorskip("gradio")
    from painter.webui import build_ui

    demo = build_ui(Session(config, out_root=tmp_path, backend=FakeBackend()))
    on_upload = next(f.fn for f in demo.fns.values() if f.fn.__name__ == "on_upload")
    preview, state = on_upload(str(heic_path))
    assert preview.shape == photo.shape and state is preview
    assert on_upload(None) == (None, None)


class FakeGeminiModels:
    """Mimics client.models: records the request, answers with a 4:3 image or with the given outcome."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def generate_content(self, model, contents, config):
        from google.genai import types

        self.requests.append((model, contents, config))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome == "image":
            img = np.zeros((864, 1184, 3), np.uint8)
            img[:, :592] = (0, 0, 255)  # left half red (BGR)
            part = types.Part.from_bytes(data=cv2.imencode(".png", img)[1].tobytes(), mime_type="image/png")
            return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(parts=[part]))])
        return types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text=outcome)]), finish_reason=types.FinishReason.SAFETY)])


def gemini_backend(*outcomes):
    pytest.importorskip("google.genai")
    from types import SimpleNamespace

    from painter.style.gemini import GeminiBackend

    models = FakeGeminiModels(outcomes)
    return GeminiBackend(client=SimpleNamespace(models=models), log=lambda m: None), models


def test_gemini_backend_returns_input_sized_image(config, photo):
    backend, models = gemini_backend("image", "image")
    st = Stylizer(config.canvas.width / config.canvas.height, backend)
    out = st.stylize(photo, make_request("ukiyoe", seed=5), n_images=2)
    w, h = generation_size(410 / 318)
    assert [o.shape for o in out] == [(h, w, 3)] * 2
    assert out[0][h // 2, 10, 0] > 200 and out[0][h // 2, -10, 0] < 50  # left red, right black survived the resize
    model, contents, cfg = models.requests[0]
    assert model == "gemini-2.5-flash-image"
    assert contents[0].inline_data.mime_type == "image/jpeg" and "ukiyo-e" in contents[1]
    assert cfg.response_modalities == ["IMAGE"] and cfg.image_config.aspect_ratio == "5:4"
    assert [r[2].seed for r in models.requests] == [5, 6]


def test_gemini_backend_errors(config, photo):
    pytest.importorskip("google.genai")
    from google.genai import errors

    quota = errors.APIError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    backend, models = gemini_backend(quota, "image")
    backend.retries, sleep = 1, __import__("time").sleep
    import painter.style.gemini as g

    g.time.sleep = lambda s: None
    try:
        st = Stylizer(410 / 318, backend)
        assert st.stylize(photo, make_request("monet"))[0].ndim == 3  # retried once after 429
        assert len(models.requests) == 2

        backend, _ = gemini_backend(errors.APIError(400, {"error": {"message": "API key not valid"}}))
        with pytest.raises(RuntimeError, match="400.*API key not valid"):
            Stylizer(410 / 318, backend).stylize(photo, make_request("monet"))

        backend, _ = gemini_backend("I can't help with that")
        with pytest.raises(RuntimeError, match="SAFETY.*can't help"):
            Stylizer(410 / 318, backend).stylize(photo, make_request("monet"))
    finally:
        g.time.sleep = sleep


def test_gemini_needs_api_key(monkeypatch):
    pytest.importorskip("google.genai")
    from painter.style.gemini import GeminiBackend

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiBackend()


def test_nearest_aspect_ratio():
    from painter.style.gemini import nearest_aspect_ratio

    assert nearest_aspect_ratio(410 / 318) == "5:4"  # 1.289: 5:4 (1.25) is closer than 4:3 (1.333)
    assert nearest_aspect_ratio(1.0) == "1:1"
    assert nearest_aspect_ratio(0.56) == "9:16"


def test_make_backend_auto_falls_back_to_gemini(monkeypatch):
    pytest.importorskip("google.genai")
    import painter.style.stylizer as s

    monkeypatch.setattr(s, "local_gpu_status", lambda: "no CUDA GPU")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    logs = []
    backend = s.make_backend("auto", log=logs.append)
    assert backend.name == "gemini" and "no CUDA GPU" in logs[0]
    monkeypatch.setattr(s, "local_gpu_status", lambda: None)
    assert s.make_backend("auto", log=logs.append).name == "sdxl"  # lazy: nothing loaded yet


def test_build_ui_gemini_hides_sdxl_sliders(config, tmp_path):
    pytest.importorskip("gradio")
    from painter.webui import build_ui

    backend, _ = gemini_backend("image")
    demo = build_ui(Session(config, out_root=tmp_path, backend=backend))
    comps = {getattr(c, "label", None): c for c in demo.blocks.values()}
    assert comps["steps"].visible is False and comps["seed"].visible is not False

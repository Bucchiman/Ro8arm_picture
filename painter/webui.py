"""Web UI: upload an image -> restyle it (oil, Van Gogh, ukiyo-e, ...) -> run the oil painting simulator on a result.

  painter webui [--host 0.0.0.0] [--port 7860] [--backend auto|sdxl|gemini] [--offload] [--gemini-model NAME]

Every run is kept under out/webui/<timestamp>/: input.png, styled_<n>.png + style.json, and per simulated image
sim_<n>/ with program.json, canvas.png, palette_sheet.png, report.json, program.gcode and optionally process.mp4.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np

from painter.analysis.palette import HEIF_SUFFIXES, load_target, palette_sheet, read_rgb
from painter.backends.klipper_gcode import to_gcode
from painter.config import MachineConfig, load_config
from painter.sim.animator import simulate
from painter.style.presets import PRESETS
from painter.style.stylizer import Backend, Stylizer, make_request

DEFAULT_OUT = Path("out/webui")


def _save_rgb(path: Path, rgb: np.ndarray) -> None:
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


class Session:
    """UI-independent logic so it can be tested without gradio or a GPU."""

    def __init__(self, config: MachineConfig, out_root: Path = DEFAULT_OUT, backend: Backend | None = None,
                 px_per_mm: float = 2.0):
        self.config = config
        self.out_root = Path(out_root)
        self.px_per_mm = px_per_mm
        self.stylizer = Stylizer(config.canvas.width / config.canvas.height, backend)

    def _new_run_dir(self) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for i in range(1000):
            d = self.out_root / (stamp if i == 0 else f"{stamp}_{i}")
            try:
                d.mkdir(parents=True)
                return d
            except FileExistsError:
                continue
        raise RuntimeError(f"cannot create a run directory under {self.out_root}")

    def stylize(self, image_rgb: np.ndarray, preset_key: str, custom_prompt: str = "", strength: float | None = None,
                controlnet_scale: float | None = None, steps: int = 30, seed: int = 0, n_images: int = 1
                ) -> list[Path]:
        req = make_request(preset_key, custom_prompt, strength, controlnet_scale, steps, seed)
        t0 = time.time()
        images = self.stylizer.stylize(image_rgb, req, n_images)
        run_dir = self._new_run_dir()
        _save_rgb(run_dir / "input.png", image_rgb)
        paths = []
        for i, img in enumerate(images):
            p = run_dir / f"styled_{i}.png"
            _save_rgb(p, img)
            paths.append(p)
        meta = {"preset": preset_key, **req.__dict__, "n_images": n_images, "seconds": round(time.time() - t0, 1)}
        (run_dir / "style.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return paths

    def simulate(self, styled_path: Path, n_colors: int = 10, threshold: float = 12.0, threshold_growth: float = 0.5,
                 video: bool = False, seed: int = 0) -> dict:
        from painter.cli import build_program  # cli imports this module for the webui subcommand

        styled_path = Path(styled_path)
        out = styled_path.parent / f"sim_{styled_path.stem.removeprefix('styled_')}"
        out.mkdir(parents=True, exist_ok=True)
        program, pal = build_program(str(styled_path), self.config, n_colors, self.px_per_mm, seed, threshold,
                                     threshold_growth, None)
        program.save(out / "program.json")
        _save_rgb(out / "palette_sheet.png", palette_sheet(pal.colors_rgb, pal.coverage))
        c = self.config.canvas
        target = load_target(str(styled_path), c.width, c.height, self.px_per_mm)
        video_path = str(out / "process.mp4") if video else None
        final, report = simulate(program, self.config, target, self.px_per_mm, video_path)
        _save_rgb(out / "canvas.png", final)
        report_json = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        (out / "report.json").write_text(report_json, encoding="utf-8")
        report_d = json.loads(report_json)  # str keys (paint_used is keyed by slot int), as the UI's JSON view needs
        (out / "program.gcode").write_text(to_gcode(program, self.config), encoding="utf-8")
        return {
            "dir": out, "canvas": out / "canvas.png", "palette": out / "palette_sheet.png",
            "video": Path(video_path) if video_path else None, "gcode": out / "program.gcode", "report": report_d,
        }


def _summary(report: dict) -> str:
    return (f"ストローク {report['strokes']:,} / 筆替え {report['tool_changes']} / 洗浄 {report['washes']} / "
            f"補充停止 {report['refill_pauses']}  \n推定描画時間 **{report['estimated_time_h']} 時間** / "
            f"SSIM {report['ssim']} / ΔE {report['mean_delta_e']}")


def build_ui(session: Session):
    import gradio as gr

    choices = [(p.label, k) for k, p in PRESETS.items()]
    backend = session.stylizer.backend
    local = getattr(backend, "name", "") != "gemini"  # strength / ControlNet / steps only mean something for SDXL
    if local:
        engine = "変換エンジン: **SDXL（ローカル GPU）**"
    else:
        engine = (f"変換エンジン: **Gemini（クラウド, `{backend.model}`）** — アップロードした画像は Google に送信されます。"
                  "生成ごとに API の料金がかかります")

    def on_preset(key):
        p = PRESETS[key]
        return gr.update(value=p.strength), gr.update(value=p.controlnet_scale)

    def on_upload(path):
        # decoded here rather than by gr.Image so HEIC works and the preview is a browser-viewable re-encode;
        # the full-quality array is kept in a State for the generator
        if not path:
            return None, None
        try:
            rgb = read_rgb(path)
        except (ValueError, OSError) as e:
            raise gr.Error(f"画像を読み込めません: {e}") from e
        return rgb, rgb

    def on_stylize(image, key, prompt, strength, cn_scale, steps, seed, n):
        if image is None:
            raise gr.Error("画像をアップロードしてください")
        try:
            paths = session.stylize(image, key, prompt, strength, cn_scale, int(steps), int(seed), int(n))
        except (ValueError, RuntimeError) as e:
            raise gr.Error(str(e)) from e
        files = [str(p) for p in paths]
        return files, files, (files[0] if files else None)

    def on_select(files, evt):
        return files[evt.index]

    on_select.__annotations__["evt"] = gr.SelectData  # real class, not a postponed string, so gradio injects it

    def on_simulate(selected, n_colors, growth, video):
        if not selected:
            raise gr.Error("先に変換して、シミュレーションする画像を選んでください")
        r = session.simulate(Path(selected), int(n_colors), threshold_growth=float(growth), video=bool(video))
        return (str(r["canvas"]), str(r["palette"]), str(r["video"]) if r["video"] else None,
                _summary(r["report"]), r["report"], str(r["gcode"]))

    with gr.Blocks(title="Ro8arm スタイル変換") as demo:
        gr.Markdown("## Ro8arm スタイル変換 → 油絵シミュレーション")
        gr.Markdown(engine)
        files_state = gr.State([])
        selected = gr.State(None)
        image = gr.State(None)  # decoded upload, RGB uint8
        with gr.Row():
            with gr.Column():
                upload = gr.File(label="入力画像（jpg / png / webp / heic など）", type="filepath",
                                 file_types=["image", *sorted(HEIF_SUFFIXES)])
                preview = gr.Image(label="プレビュー", type="numpy", interactive=False, height=300)
                preset = gr.Dropdown(choices, value="impasto_oil", label="スタイル")
                prompt = gr.Textbox(label="プロンプト（自由入力では必須、プリセットでは追加の指示）",
                                    placeholder="e.g. sunset, warm colors")
                with gr.Accordion("詳細設定", open=False):
                    strength = gr.Slider(0.3, 1.0, value=PRESETS["impasto_oil"].strength, step=0.05,
                                         label="変換の強さ (strength)", visible=local)
                    cn_scale = gr.Slider(0.0, 1.5, value=PRESETS["impasto_oil"].controlnet_scale, step=0.05,
                                         label="輪郭の保持 (ControlNet scale)", visible=local)
                    steps = gr.Slider(10, 50, value=30, step=1, label="steps", visible=local)
                    seed = gr.Number(value=0, precision=0, label="seed")
                    n = gr.Slider(1, 4, value=1, step=1, label="枚数")
                stylize_btn = gr.Button("変換", variant="primary")
            with gr.Column():
                gallery = gr.Gallery(label="変換結果（クリックで選択）", columns=2, height=420)
                with gr.Row():
                    n_colors = gr.Slider(2, session.config.palette.slots, value=min(10, session.config.palette.slots),
                                         step=1, label="パレット色数")
                    growth = gr.Slider(0.0, 3.0, value=0.5, step=0.1,
                                       label="細部の抑制 (threshold-growth、大きいほど時間短縮)")
                video = gr.Checkbox(label="工程動画を作る（少し時間が延びます）")
                sim_btn = gr.Button("油絵シミュレーション", variant="primary")
        with gr.Row():
            canvas = gr.Image(label="シミュレーション結果", type="filepath")
            palette = gr.Image(label="パレットに置く色", type="filepath")
        summary = gr.Markdown()
        with gr.Row():
            process = gr.Video(label="工程動画")
            with gr.Column():
                report = gr.JSON(label="report.json")
                gcode = gr.File(label="Klipper G-code")

        preset.change(on_preset, preset, [strength, cn_scale])
        upload.change(on_upload, upload, [preview, image])
        stylize_btn.click(on_stylize, [image, preset, prompt, strength, cn_scale, steps, seed, n],
                          [gallery, files_state, selected])
        gallery.select(on_select, files_state, selected)
        sim_btn.click(on_simulate, [selected, n_colors, growth, video], [canvas, palette, process, summary, report, gcode])
    return demo


def launch(config_path: str, host: str = "127.0.0.1", port: int = 7860, offload: bool | None = None,
           px_per_mm: float = 2.0, backend: str = "auto", gemini_model: str | None = None) -> None:
    from painter.style.stylizer import make_backend

    try:
        engine = make_backend(backend, offload=offload, gemini_model=gemini_model)
    except RuntimeError as e:
        raise SystemExit(str(e)) from e
    session = Session(load_config(config_path), backend=engine, px_per_mm=px_per_mm)
    demo = build_ui(session)
    demo.queue(default_concurrency_limit=1).launch(server_name=host, server_port=port, show_error=True,
                                                   allowed_paths=[str(session.out_root.resolve())])

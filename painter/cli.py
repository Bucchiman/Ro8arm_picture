"""Command line interface.

  painter plan IMAGE -o out/program.json      image -> palette + strokes + process plan
  painter simulate out/program.json -o out    virtual canvas, process video, report
  painter gcode out/program.json -o out/program.gcode
  painter run IMAGE -o out                    all of the above
  painter webui                               upload -> style transfer -> simulate (needs .[style] or .[gemini])
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from painter.analysis.palette import extract_palette, load_target, palette_sheet
from painter.backends.klipper_gcode import to_gcode
from painter.config import MachineConfig, load_config
from painter.planner.sequencer import plan
from painter.program import PaintProgram, PaletteColor
from painter.sim.animator import simulate
from painter.strokes.human_motion import MotionParams, humanize
from painter.strokes.painterly import StrokeParams, generate_strokes

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "machine.yaml"


def build_program(image: str, config: MachineConfig, n_colors: int, px_per_mm: float, seed: int,
                  threshold: float, threshold_growth: float, max_strokes_per_layer: int | None):
    if n_colors > config.palette.slots:
        raise SystemExit(f"--colors {n_colors} exceeds palette slots ({config.palette.slots})")
    target = load_target(image, config.canvas.width, config.canvas.height, px_per_mm)
    pal = extract_palette(target, n_colors, seed)
    raw = generate_strokes(
        target, pal.colors_rgb, config.brushes,
        StrokeParams(px_per_mm=px_per_mm, threshold=threshold, threshold_growth=threshold_growth,
                     max_strokes_per_layer=max_strokes_per_layer, seed=seed),
    )
    rng = np.random.default_rng(seed)
    mp = MotionParams(seed=seed)
    kinds = {b.id: b.kind for b in config.brushes}
    strokes = [humanize(r, px_per_mm, config.motion.paint_speed, kinds[r.brush_id], mp, rng) for r in raw]
    program = PaintProgram(
        canvas_size=(config.canvas.width, config.canvas.height),
        palette=[PaletteColor(i, (int(c[0]), int(c[1]), int(c[2])), round(float(cov), 4))
                 for i, (c, cov) in enumerate(zip(pal.colors_rgb, pal.coverage))],
        actions=plan(strokes, config),
        source_image=str(image),
    )
    return program, pal


def _save_rgb(path: Path, rgb: np.ndarray) -> None:
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def cmd_plan(args) -> PaintProgram:
    config = load_config(args.config)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    program, pal = build_program(args.image, config, args.colors, args.px_per_mm, args.seed, args.threshold,
                                 args.threshold_growth, args.max_strokes_per_layer)
    program.save(out)
    _save_rgb(out.with_name("palette_sheet.png"), palette_sheet(pal.colors_rgb, pal.coverage))
    _save_rgb(out.with_name("quantized.png"), pal.quantized())
    print(f"wrote {out} ({len(program.strokes())} strokes, {len(program.actions)} actions)")
    print(f"wrote {out.with_name('palette_sheet.png')} (mix these colors into the palette slots)")
    return program


def cmd_simulate(args) -> None:
    config = load_config(args.config)
    program = PaintProgram.load(args.program)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    target = None
    if program.source_image and Path(program.source_image).exists():
        target = load_target(program.source_image, config.canvas.width, config.canvas.height, args.px_per_mm)
    video = str(out / "process.mp4") if args.video else None
    final, report = simulate(program, config, target, args.px_per_mm, video)
    _save_rgb(out / "canvas.png", final)
    (out / "report.json").write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    print(f"wrote {out / 'canvas.png'}" + (f", {video}" if video else ""))


def cmd_gcode(args) -> None:
    config = load_config(args.config)
    program = PaintProgram.load(args.program)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_gcode(program, config), encoding="utf-8")
    print(f"wrote {out}")


def cmd_run(args) -> None:
    out = Path(args.output)
    args.output = str(out / "program.json")
    cmd_plan(args)
    args.program, args.output = str(out / "program.json"), str(out)
    cmd_simulate(args)
    args.output = str(out / "program.gcode")
    cmd_gcode(args)


def cmd_webui(args) -> None:
    from painter.webui import launch

    launch(args.config, args.host, args.port, True if args.offload else None, args.px_per_mm, args.backend,
           args.gemini_model)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="painter")
    ap.add_argument("-c", "--config", default=str(DEFAULT_CONFIG))
    sub = ap.add_subparsers(dest="cmd", required=True)

    def plan_args(p):
        p.add_argument("image")
        p.add_argument("--colors", type=int, default=10, help="number of pre-mixed palette colors")
        p.add_argument("--threshold", type=float, default=12.0, help="Lab difference that triggers a stroke")
        p.add_argument("--threshold-growth", type=float, default=0.5,
                       help="finer brush layers need threshold * (1 + growth * layer); higher = fewer detail strokes")
        p.add_argument("--max-strokes-per-layer", type=int, default=None)
        p.add_argument("--seed", type=int, default=0)

    def sim_args(p):
        p.add_argument("--video", action="store_true", help="write process.mp4")

    ap.add_argument("--px-per-mm", type=float, default=2.0)

    p = sub.add_parser("plan")
    plan_args(p)
    p.add_argument("-o", "--output", default="out/program.json")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("simulate")
    p.add_argument("program")
    p.add_argument("-o", "--output", default="out")
    sim_args(p)
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("gcode")
    p.add_argument("program")
    p.add_argument("-o", "--output", default="out/program.gcode")
    p.set_defaults(func=cmd_gcode)

    p = sub.add_parser("run")
    plan_args(p)
    sim_args(p)
    p.add_argument("-o", "--output", default="out")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("webui")
    p.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open it to other machines")
    p.add_argument("--port", type=int, default=7860)
    p.add_argument("--backend", choices=["auto", "sdxl", "gemini"], default="auto",
                   help="auto = local SDXL if the GPU has >= 12 GiB VRAM, else Gemini (needs GEMINI_API_KEY)")
    p.add_argument("--offload", action="store_true",
                   help="sdxl: always use CPU offload (default: only when free VRAM is short)")
    p.add_argument("--gemini-model", default=None, help="gemini: model name (default gemini-2.5-flash-image)")
    p.set_defaults(func=cmd_webui)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

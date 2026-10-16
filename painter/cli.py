"""Command line interface.

  painter plan IMAGE -o out/program.json      image -> palette + strokes + process plan
  painter simulate out/program.json -o out    virtual canvas, process video, report
  painter gcode out/program.json -o out/program.gcode
  painter run IMAGE -o out                    all of the above
  painter inspect out/program.json -o out/inspect [--stroke N ...]   close-up of single strokes
  painter gcode-sim out/program.gcode -o out/gcode_sim [--video]     run the G-code (with Klipper macros) + checks
  painter loop IMAGE -o out/loop [--video]    closed loop: photograph the canvas after every layer, replan from it
  painter -c configs/machine_final.yaml twin IMAGE -o out/twin    3D digital twin viewer of the final machine
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
from painter.program import Paint, PaintProgram, PaletteColor
from painter.sim.animator import simulate
from painter.strokes.human_motion import MotionParams, humanize
from painter.strokes.painterly import StrokeParams, generate_strokes

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "machine.yaml"
DEFAULT_MACROS = Path(__file__).resolve().parent.parent / "klipper" / "macros.cfg"


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


def cmd_inspect(args) -> None:
    from painter.sim.stroke_inspector import inspect, select_strokes

    config = load_config(args.config)
    program = PaintProgram.load(args.program)
    indices = select_strokes(program, args.stroke, args.random, args.seed)
    results = inspect(program, config, indices, args.output, args.px_per_mm, args.slow)
    for r in results:
        print(json.dumps(r, ensure_ascii=False))


def cmd_gcode_sim(args) -> int:
    from painter.sim.animator import ssim
    from painter.sim.gcode_player import play, render_canvas
    from painter.sim.gcode_sim import load_gcode, run_gcode
    from painter.sim.renderer import render_program

    config = load_config(args.config)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    interp, checker = run_gcode(load_gcode(args.gcode), config, args.macros)
    report = interp.report
    canvas = render_canvas(interp, checker, config, args.px_per_mm)
    _save_rgb(out / "canvas_from_gcode.png", canvas)
    if args.program:
        expected = render_program(PaintProgram.load(args.program), config, args.px_per_mm)
        report.canvas_diff_vs_program = round(float(np.abs(canvas.astype(float) - expected).mean() / 255), 4)
    d = report.to_dict()
    if args.video:
        d["video"] = play(interp, checker, config, str(out / "gcode_sim.mp4"), args.px_per_mm, args.speed,
                          args.start, args.end)
    (out / "gcode_report.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {k: v for k, v in d.items() if k != "first_issues"}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    for issue in d["first_issues"][:10]:
        print(f"  {issue['severity']:7s} line {issue['line']:>7d}  {issue['kind']}: {issue['message']}  at {issue['position']}")
    print(f"wrote {out / 'gcode_report.json'}, {out / 'canvas_from_gcode.png'}" + (f", {out / 'gcode_sim.mp4'}" if args.video else ""))
    return 1 if report.errors else 0


def cmd_loop(args) -> None:
    """Closed loop in simulation: the simulated world paints with different physics than the planner assumes;
    the loop sees it through a simulated camera. With --compare, the open-loop plan is painted in the same world."""
    from painter.feedback.camera import SimCamera
    from painter.feedback.loop import LoopParams, error_heatmap, compare, paint_closed_loop, steps_sheet, steps_to_dict
    from painter.feedback.world import RealityParams, SimWorld

    config = load_config(args.config)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    px = args.px_per_mm
    target = load_target(args.image, config.canvas.width, config.canvas.height, px)
    pal = extract_palette(target, args.colors, args.seed)
    palette = [PaletteColor(i, (int(c[0]), int(c[1]), int(c[2])), round(float(cov), 4))
               for i, (c, cov) in enumerate(zip(pal.colors_rgb, pal.coverage))]
    _save_rgb(out / "palette_sheet.png", palette_sheet(pal.colors_rgb, pal.coverage))
    reality = RealityParams(width_scale=args.width_scale, opacity=args.opacity, position_noise_mm=args.position_noise,
                            mix_error_rgb=args.mix_error, seed=args.seed + 1)
    shell = PaintProgram((config.canvas.width, config.canvas.height), palette)
    world = SimWorld(shell, config, px, reality)
    camera = SimCamera(world, config, args.seed)

    writer = None
    panel = {"err": None}
    if args.video:
        vw, vh = 800, 600
        writer = cv2.VideoWriter(str(out / "camera_loop.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (vw * 2, vh))

    def frame_out(label: str) -> None:
        cam = cv2.resize(camera.capture(), (800, 600), interpolation=cv2.INTER_AREA)
        cv2.putText(cam, "camera: " + label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        err = np.full((600, 800, 3), 40, np.uint8)
        if panel["err"] is not None:
            e = panel["err"]
            k = min(800 / e.shape[1], 600 / e.shape[0])
            ew, eh = int(e.shape[1] * k), int(e.shape[0] * k)
            y, x = (600 - eh) // 2, (800 - ew) // 2
            err[y : y + eh, x : x + ew] = cv2.resize(e, (ew, eh), interpolation=cv2.INTER_AREA)
        cv2.putText(err, "still off from the target (last photo)", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2)
        writer.write(np.hstack([cam, err]))

    counter = {"strokes": 0}

    def execute(chunk) -> None:
        for a in chunk:
            world.apply(a)
            if isinstance(a, Paint):
                counter["strokes"] += 1
                if writer is not None and counter["strokes"] % args.video_every == 0:
                    frame_out(f"{a.stroke.brush_id}  stroke {counter['strokes']}")
        if writer is not None:
            for _ in range(15):  # park + photo
                frame_out("photo")

    def on_step(step, de) -> None:
        panel["err"] = error_heatmap(de)
        print(f"  {step.name:28s} +{step.strokes:6d} strokes   photo vs target: dE {step.delta_e:5.2f}  "
              f"SSIM {step.ssim:.3f}  off {step.off_fraction:.1%}")

    params = LoopParams(threshold=args.threshold, threshold_growth=args.threshold_growth,
                        touchup_rounds=args.touchup, touchup_level=args.touchup_level, seed=args.seed)
    print("closed loop (simulated world + camera):")
    program, steps = paint_closed_loop(target, palette, config, camera, execute, px, params, out / "steps",
                                       args.image, on_step)
    if writer is not None:
        for _ in range(60):
            frame_out("done")
        writer.release()
    program.save(out / "program.json")
    (out / "program.gcode").write_text(to_gcode(program, config), encoding="utf-8")
    cv2.imwrite(str(out / "camera_steps.png"), steps_sheet(steps))
    closed_true = world.image()
    _, report = simulate(program, config, None, px_per_mm=0.5)  # time estimate only
    captures = len(steps)
    result = {
        "closed_loop": {
            "strokes": len(program.strokes()), "photos": captures,
            "estimated_time_h": round((report.estimated_time_s + captures * config.camera.capture_s) / 3600, 2),
            "washes": report.washes, "steps": steps_to_dict(steps),
        },
        "reality": vars(reality),
    }
    rows = [("target", target, None)]
    if args.compare:
        # Open loop: the whole painting planned up front from the internal brush model, painted in the same world.
        print("open loop (same world, planned up front without looking):")
        open_prog, _ = build_program(args.image, config, args.colors, px, args.seed, args.threshold,
                                     args.threshold_growth, None)
        open_world = SimWorld(shell, config, px, reality)
        for a in open_prog.actions:
            open_world.apply(a)
        open_true = open_world.image()
        _, open_report = simulate(open_prog, config, None, px_per_mm=0.5)
        s_o, de_o, off_o, _ = compare(open_true, target)
        result["open_loop"] = {"strokes": len(open_prog.strokes()), "ssim": round(s_o, 4), "delta_e": round(de_o, 2),
                               "off_fraction": round(off_o, 4),
                               "estimated_time_h": round(open_report.estimated_time_s / 3600, 2)}
        print(f"  {'final':28s} +{len(open_prog.strokes()):6d} strokes   true canvas vs target: dE {de_o:5.2f}  "
              f"SSIM {s_o:.3f}  off {off_o:.1%}")
        rows.append((f"open loop  dE {de_o:.1f}  off {off_o:.0%}", open_true, None))
    s_c, de_c, off_c, _ = compare(closed_true, target)
    result["closed_loop"].update({"ssim": round(s_c, 4), "delta_e": round(de_c, 2), "off_fraction": round(off_c, 4)})
    rows.append((f"closed loop (camera)  dE {de_c:.1f}  off {off_c:.0%}", closed_true, None))
    cv2.imwrite(str(out / "comparison.png"), _side_by_side([(name, img) for name, img, _ in rows]))
    _save_rgb(out / "canvas.png", closed_true)
    (out / "loop_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {'final (true canvas)':28s} {len(program.strokes()):7d} strokes   dE {de_c:5.2f}  SSIM {s_c:.3f}  "
          f"off {off_c:.1%}   ~{result['closed_loop']['estimated_time_h']} h")
    print(f"wrote {out / 'comparison.png'}, {out / 'camera_steps.png'}, {out / 'loop_report.json'}, "
          f"{out / 'program.json'}, {out / 'program.gcode'}" + (f", {out / 'camera_loop.mp4'}" if writer else ""))


def _side_by_side(items: list[tuple[str, np.ndarray]], tile_w: int = 520) -> np.ndarray:
    tiles = []
    for name, rgb in items:
        th = int(rgb.shape[0] * tile_w / rgb.shape[1])
        tile = np.full((th + 40, tile_w, 3), 255, np.uint8)
        tile[40:] = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (tile_w, th), interpolation=cv2.INTER_AREA)
        cv2.putText(tile, name, (6, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(tile)
    return np.hstack(tiles)


def cmd_run(args) -> None:
    out = Path(args.output)
    args.output = str(out / "program.json")
    cmd_plan(args)
    args.program, args.output = str(out / "program.json"), str(out)
    cmd_simulate(args)
    args.output = str(out / "program.gcode")
    cmd_gcode(args)


def cmd_twin(args) -> None:
    from painter.twin.export import build_twin, write_viewer

    config = load_config(args.config)
    out = Path(args.output)
    program, _ = build_program(args.image, config, args.colors, args.px_per_mm, args.seed, args.threshold,
                               args.threshold_growth, args.max_strokes_per_layer)
    data, report = build_twin(program, config, Path(args.macros).read_text(encoding="utf-8"), cv2.cvtColor(cv2.imread(args.image), cv2.COLOR_BGR2RGB),
                              args.title or Path(args.image).stem, args.px_per_mm)
    index = write_viewer(data, out)
    size = (out / "twin_data.json").stat().st_size / 2**20
    print(f"G-code sim: {report['total_time_h']} h, {report['strokes_rebuilt']} strokes, "
          f"errors {report['errors']}, warnings {report['warnings']}")
    print(f"wrote {index} + twin_data.json ({size:.1f} MB)   view: python -m http.server -d {out}")


def main(argv: list[str] | None = None) -> int:
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

    p = sub.add_parser("inspect", help="close-up animation + graphs of single strokes")
    p.add_argument("program")
    p.add_argument("-o", "--output", default="out/inspect")
    p.add_argument("--stroke", type=int, nargs="*", help="stroke numbers in painting order (default: first of each brush)")
    p.add_argument("--random", type=int, default=0, help="pick N random strokes instead")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--slow", type=float, default=4.0, help="slow motion factor")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("gcode-sim", help="simulate G-code incl. Klipper macros, check safety, render")
    p.add_argument("gcode")
    p.add_argument("-o", "--output", default="out/gcode_sim")
    p.add_argument("--macros", default=str(DEFAULT_MACROS))
    p.add_argument("--program", help="PaintProgram JSON to compare the rendered canvas against")
    p.add_argument("--video", action="store_true")
    p.add_argument("--speed", type=float, default=None,
                   help="machine seconds per video second (default: fit the time range into 60 s)")
    p.add_argument("--start", type=float, default=0.0, help="start of the time range (machine seconds)")
    p.add_argument("--end", type=float, default=None, help="end of the time range (machine seconds)")
    p.set_defaults(func=cmd_gcode_sim)

    p = sub.add_parser("loop", help="closed loop with a (simulated) camera: photograph after every layer, replan")
    plan_args(p)
    p.add_argument("-o", "--output", default="out/loop")
    p.add_argument("--touchup", type=int, default=2, help="max touch-up rounds with the finest brush")
    p.add_argument("--touchup-level", type=int, default=1,
                   help="touch-ups fix spots off by more than threshold * (1 + growth * level); lower = stricter")
    p.add_argument("--no-compare", dest="compare", action="store_false", help="skip the open-loop comparison")
    p.add_argument("--video", action="store_true", help="write camera_loop.mp4 (camera view + error map)")
    p.add_argument("--video-every", type=int, default=40, help="one video frame every N strokes")
    g = p.add_argument_group("simulated world (how the real machine differs from the planner's model)")
    g.add_argument("--width-scale", type=float, default=1.15, help="bristles splay: strokes this much wider")
    g.add_argument("--opacity", type=float, default=0.75, help="paint covers this much of what the model assumes")
    g.add_argument("--position-noise", type=float, default=0.6, help="per-stroke position error sigma (mm)")
    g.add_argument("--mix-error", type=float, default=6.0, help="palette color mixing error sigma (RGB)")
    p.set_defaults(func=cmd_loop)

    p = sub.add_parser("twin", help="3D digital twin: replay the machine painting the image in a browser viewer")
    plan_args(p)
    p.add_argument("-o", "--output", default="out/twin")
    p.add_argument("--macros", default=str(DEFAULT_MACROS),
                   help="macro template; its station variables are replaced with the config's positions")
    p.add_argument("--title", default=None, help="name shown in the viewer (default: image file name)")
    p.set_defaults(func=cmd_twin)

    p = sub.add_parser("run")
    plan_args(p)
    sim_args(p)
    p.add_argument("-o", "--output", default="out")
    p.set_defaults(func=cmd_run)

    args = ap.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Turn geometric stroke paths into human-like brush motion.

A painter's stroke has an entry (the brush is set down and pressed in), a body at steady pressure, and an exit
where the brush is lifted while still moving (taper). Speed is slow at both ends and fastest in the middle, and a
flat brush is turned to keep its broad side across the direction of travel. Small random jitter keeps strokes from
looking mechanical (the same idea as the noise in the legacy `src/fuji.py` drawing decorator).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from painter.program import Stroke, StrokePoint
from painter.strokes.painterly import RawStroke


@dataclass
class MotionParams:
    spacing_mm: float = 1.5  # resample spacing along the stroke
    smooth_iterations: int = 2  # Chaikin corner cutting
    entry_fraction: float = 0.15
    exit_fraction: float = 0.3
    entry_pressure: float = 0.25
    body_pressure: float = 0.7
    exit_pressure: float = 0.05
    min_speed_ratio: float = 0.35  # speed at the ends relative to nominal
    pressure_jitter: float = 0.05
    angle_jitter_deg: float = 3.0
    seed: int = 0


def chaikin(path: np.ndarray, iterations: int) -> np.ndarray:
    for _ in range(iterations):
        if len(path) < 3:
            return path
        q = 0.75 * path[:-1] + 0.25 * path[1:]
        r = 0.25 * path[:-1] + 0.75 * path[1:]
        mid = np.empty((2 * (len(path) - 1), 2), path.dtype)
        mid[0::2], mid[1::2] = q, r
        path = np.vstack([path[:1], mid[1:-1], path[-1:]])
    return path


def resample(path: np.ndarray, spacing: float) -> np.ndarray:
    seg = np.hypot(*np.diff(path, axis=0).T)
    total = seg.sum()
    if total < 1e-6:
        return path[:1].repeat(2, axis=0)
    n = max(int(np.ceil(total / spacing)) + 1, 2)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.linspace(0.0, total, n)
    return np.stack([np.interp(t, s, path[:, 0]), np.interp(t, s, path[:, 1])], axis=1)


def pressure_profile(t: np.ndarray, p: MotionParams) -> np.ndarray:
    """t in [0, 1] along the stroke -> pressure. Smooth ramps for the entry and the lift-off."""
    pr = np.full_like(t, p.body_pressure)
    e = t < p.entry_fraction
    u = t[e] / p.entry_fraction
    pr[e] = p.entry_pressure + (p.body_pressure - p.entry_pressure) * (3 * u**2 - 2 * u**3)
    x = t > 1 - p.exit_fraction
    u = (t[x] - (1 - p.exit_fraction)) / p.exit_fraction
    pr[x] = p.body_pressure + (p.exit_pressure - p.body_pressure) * (3 * u**2 - 2 * u**3)
    return pr


def speed_profile(t: np.ndarray, nominal: float, p: MotionParams) -> np.ndarray:
    """Bell-shaped speed: slow when setting down and lifting, fastest mid-stroke."""
    return nominal * (p.min_speed_ratio + (1 - p.min_speed_ratio) * np.sin(np.pi * t) ** 0.7)


def brush_angles(path: np.ndarray, symmetric: bool) -> np.ndarray:
    """Direction of travel in degrees, unwrapped so the rotation axis never jumps.

    A flat brush looks the same rotated by 180 degrees, so for it angles are unwrapped modulo 180.
    """
    d = np.gradient(path, axis=0)
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    period = 180.0 if symmetric else 360.0
    out = ang.copy()
    for i in range(1, len(out)):
        delta = (out[i] - out[i - 1] + period / 2) % period - period / 2
        out[i] = out[i - 1] + delta
    return out


def humanize(
    raw: RawStroke, px_per_mm: float, nominal_speed: float, brush_kind: str, params: MotionParams, rng: np.random.Generator
) -> Stroke:
    path_mm = raw.path_px.astype(np.float64) / px_per_mm
    path_mm = chaikin(path_mm, params.smooth_iterations)
    path_mm = resample(path_mm, params.spacing_mm)
    t = np.linspace(0.0, 1.0, len(path_mm))
    pressure = pressure_profile(t, params)
    # Jitter must never lift the brush off mid-stroke: keep at least the lift-off pressure.
    jitter = rng.normal(0, params.pressure_jitter, len(t)) * (pressure > 0.1)
    pressure = np.clip(pressure + jitter, min(params.exit_pressure, params.entry_pressure), 1.0)
    speed = speed_profile(t, nominal_speed, params)
    angle = brush_angles(path_mm, symmetric=brush_kind == "flat") + rng.normal(0, params.angle_jitter_deg)
    points = [
        StrokePoint(round(float(x), 3), round(float(y), 3), round(float(pr), 3), round(float(a), 2), round(float(v), 2))
        for (x, y), pr, a, v in zip(path_mm, pressure, angle, speed)
    ]
    return Stroke(raw.brush_id, raw.color_id, raw.layer, points)

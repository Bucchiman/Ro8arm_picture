"""Layered painterly stroke generation (after Hertzmann, "Painterly Rendering with Curved Brush Strokes", 1998).

Each brush (coarse -> fine) produces one layer. For every grid cell where the current canvas differs from a
blurred reference, a curved stroke starts at the worst pixel and follows the direction perpendicular to the image
gradient (i.e. along edges/contours), like a painter following a form. Stroke colors are restricted to the
pre-mixed palette.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from painter.analysis.palette import rgb_to_lab
from painter.config import Brush


@dataclass
class StrokeParams:
    px_per_mm: float = 2.0
    threshold: float = 12.0  # mean Lab difference in a cell that triggers a stroke
    threshold_growth: float = 0.5  # finer layers need a larger difference: threshold * (1 + growth * layer)
    grid_factor: float = 1.0  # grid step = grid_factor * brush radius
    blur_factor: float = 0.5  # reference blur sigma = blur_factor * brush radius
    max_length_factor: float = 10.0  # max stroke length = factor * brush width
    min_length_factor: float = 1.0  # strokes shorter than this (x width) stop only on max length
    curvature: float = 0.6  # direction filter: 0 = straight, 1 = follow gradient fully
    edge_gradient: float = 4.0  # Sobel magnitude above which the local edge direction is followed
    hatch_angle_deg: float = 30.0  # default stroke direction where the image has no structure at all
    max_strokes_per_layer: int | None = None
    seed: int = 0


@dataclass
class RawStroke:
    """A stroke in pixel coordinates before human-like motion is applied."""

    brush_id: str
    color_id: int
    layer: int
    path_px: np.ndarray  # (K, 2) float x, y
    width_px: float = field(default=0.0)


def _lab_diff(a_lab: np.ndarray, b_lab: np.ndarray) -> np.ndarray:
    return np.sqrt(((a_lab - b_lab) ** 2).sum(-1))


def generate_strokes(
    target_rgb: np.ndarray,
    palette_rgb: np.ndarray,
    brushes: list[Brush],
    params: StrokeParams = StrokeParams(),
) -> list[RawStroke]:
    rng = np.random.default_rng(params.seed)
    h, w = target_rgb.shape[:2]
    canvas = np.full_like(target_rgb, 255)
    painted = np.zeros((h, w), bool)
    pal_lab = rgb_to_lab(palette_rgb.reshape(1, -1, 3)).reshape(-1, 3)

    strokes: list[RawStroke] = []
    for layer, brush in enumerate(brushes):
        width_px = brush.width * params.px_per_mm
        radius = max(width_px / 2.0, 1.0)
        sigma = max(params.blur_factor * radius, 0.5)
        reference = cv2.GaussianBlur(target_rgb, (0, 0), sigma)
        ref_lab = rgb_to_lab(reference)

        # Each pixel's reference color snapped to the palette (what the painter can actually mix).
        d = ((ref_lab[:, :, None, :] - pal_lab[None, None, :, :]) ** 2).sum(-1)
        ref_idx = d.argmin(-1)
        ref_q_lab = pal_lab[ref_idx]

        tx, ty = _flow_field(reference, radius, params)

        canvas_lab = rgb_to_lab(canvas)
        diff = _lab_diff(canvas_lab, ref_q_lab)
        diff[~painted] = 1e3  # unpainted canvas always needs paint

        step = max(int(round(params.grid_factor * radius)), 1)
        layer_threshold = params.threshold * (1 + params.threshold_growth * layer)
        layer_strokes: list[RawStroke] = []
        for y0 in range(0, h, step):
            for x0 in range(0, w, step):
                cell = diff[y0 : y0 + step, x0 : x0 + step]
                if cell.mean() <= layer_threshold:
                    continue
                iy, ix = np.unravel_index(np.argmax(cell), cell.shape)
                sx, sy = x0 + ix, y0 + iy
                color_id = int(ref_idx[sy, sx])
                path = _trace_stroke(
                    sx, sy, color_id, pal_lab, ref_lab, canvas_lab, painted, tx, ty, radius, width_px, params
                )
                layer_strokes.append(RawStroke(brush.id, color_id, layer, path, width_px))

        rng.shuffle(layer_strokes)
        if params.max_strokes_per_layer is not None:
            layer_strokes = layer_strokes[: params.max_strokes_per_layer]
        for s in layer_strokes:
            _quick_render(canvas, painted, s, palette_rgb)
        strokes.extend(layer_strokes)
    return strokes


def _flow_field(reference_rgb: np.ndarray, radius: float, params: StrokeParams) -> tuple[np.ndarray, np.ndarray]:
    """Unit stroke direction per pixel: along edges where there are edges, otherwise the dominant orientation of
    the surrounding structure (smoothed structure tensor), otherwise a default hatching angle. This way flat
    color areas are filled with strokes that flow with their surroundings instead of with dabs."""
    gray = cv2.cvtColor(reference_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gmag = np.hypot(gx, gy)

    sigma = 4 * radius + 8
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), sigma)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), sigma)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), sigma)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2  # tangent = perpendicular to dominant gradient
    energy = np.sqrt(jxx + jyy)
    hatch = np.radians(params.hatch_angle_deg)
    theta = np.where(energy > 1.0, theta, hatch)

    edge = gmag > params.edge_gradient
    safe = np.maximum(gmag, 1e-6)
    tx = np.where(edge, -gy / safe, np.cos(theta)).astype(np.float32)
    ty = np.where(edge, gx / safe, np.sin(theta)).astype(np.float32)
    return tx, ty


def _trace_stroke(sx, sy, color_id, pal_lab, ref_lab, canvas_lab, painted, tx, ty, radius, width_px, params):
    h, w = ref_lab.shape[:2]
    color_lab = pal_lab[color_id]
    pts = [(float(sx), float(sy))]
    x, y = float(sx), float(sy)
    dx, dy = 0.0, 0.0
    max_len = params.max_length_factor * width_px
    min_len = params.min_length_factor * width_px
    length = 0.0
    while length < max_len:
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= ix < w and 0 <= iy < h):
            break
        if length > min_len and painted[iy, ix]:
            ref_vs_canvas = np.linalg.norm(ref_lab[iy, ix] - canvas_lab[iy, ix])
            ref_vs_stroke = np.linalg.norm(ref_lab[iy, ix] - color_lab)
            if ref_vs_canvas < ref_vs_stroke:
                break
        if length > min_len and np.linalg.norm(ref_lab[iy, ix] - color_lab) > 25.0:
            break
        ndx, ndy = float(tx[iy, ix]), float(ty[iy, ix])
        if dx * ndx + dy * ndy < 0:  # the field has no sign: keep moving forward
            ndx, ndy = -ndx, -ndy
        if dx != 0 or dy != 0:
            ndx = params.curvature * ndx + (1 - params.curvature) * dx
            ndy = params.curvature * ndy + (1 - params.curvature) * dy
        n = np.hypot(ndx, ndy)
        if n < 1e-6:
            break
        dx, dy = ndx / n, ndy / n
        x, y = x + radius * dx, y + radius * dy
        length += radius
        pts.append((x, y))
    path = np.array(pts, np.float32)
    path[:, 0] = np.clip(path[:, 0], 0, w - 1)
    path[:, 1] = np.clip(path[:, 1], 0, h - 1)
    if len(path) == 1:  # a dab: give it a short body so it can be painted as a stroke
        path = np.vstack([path, path + [[radius * 0.5, 0.0]]])
        path[:, 0] = np.clip(path[:, 0], 0, w - 1)
    return path


def _quick_render(canvas, painted, stroke: RawStroke, palette_rgb):
    pts = np.round(stroke.path_px).astype(np.int32).reshape(-1, 1, 2)
    color = tuple(int(v) for v in palette_rgb[stroke.color_id])
    thickness = max(int(round(stroke.width_px)), 1)
    cv2.polylines(canvas, [pts], False, color, thickness, lineType=cv2.LINE_AA)
    # Count only the stroke core as painted: real strokes taper at both ends and show dry-brush gaps,
    # so a conservative mask makes later layers fill what the coarse brush missed.
    mask = np.zeros(painted.shape, np.uint8)
    cv2.polylines(mask, [pts], False, 1, max(int(round(stroke.width_px * 0.6)), 1))
    painted |= mask.astype(bool)

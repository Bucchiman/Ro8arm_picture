"""Color analysis: reduce the target image to N pre-mixable palette colors."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PaletteResult:
    colors_rgb: np.ndarray  # (N, 3) uint8, sorted dark -> light
    labels: np.ndarray  # (H, W) int, index into colors_rgb
    coverage: np.ndarray  # (N,) fraction of pixels per color

    def quantized(self) -> np.ndarray:
        return self.colors_rgb[self.labels]


def load_target(path: str, canvas_w_mm: float, canvas_h_mm: float, px_per_mm: float) -> np.ndarray:
    """Load an image as RGB and center-crop/resize it to the canvas aspect ratio."""
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    target_ratio = canvas_w_mm / canvas_h_mm
    if w / h > target_ratio:
        new_w = int(round(h * target_ratio))
        x0 = (w - new_w) // 2
        rgb = rgb[:, x0 : x0 + new_w]
    else:
        new_h = int(round(w / target_ratio))
        y0 = (h - new_h) // 2
        rgb = rgb[y0 : y0 + new_h]
    size = (int(round(canvas_w_mm * px_per_mm)), int(round(canvas_h_mm * px_per_mm)))
    return cv2.resize(rgb, size, interpolation=cv2.INTER_AREA)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """uint8 RGB -> float Lab (L 0..100, a/b roughly -128..127)."""
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    return lab


def extract_palette(rgb: np.ndarray, n_colors: int, seed: int = 0) -> PaletteResult:
    """k-means in Lab space. Colors are sorted by lightness (dark first)."""
    lab = rgb_to_lab(rgb).reshape(-1, 3)
    cv2.setRNGSeed(seed)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
    _, labels, centers = cv2.kmeans(lab, n_colors, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    labels = labels.ravel()

    order = np.argsort(centers[:, 0])
    remap = np.empty_like(order)
    remap[order] = np.arange(n_colors)
    centers = centers[order]
    labels = remap[labels]

    centers_rgb = cv2.cvtColor(centers.reshape(1, -1, 3).astype(np.float32), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    colors_rgb = np.clip(np.round(centers_rgb * 255), 0, 255).astype(np.uint8)
    coverage = np.bincount(labels, minlength=n_colors) / labels.size
    return PaletteResult(colors_rgb, labels.reshape(rgb.shape[:2]), coverage)


def nearest_palette_index(rgb_pixels: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """Map RGB pixels (..., 3) to the nearest palette entry in Lab space."""
    shape = rgb_pixels.shape[:-1]
    lab = rgb_to_lab(rgb_pixels.reshape(1, -1, 3).astype(np.uint8)).reshape(-1, 3)
    pal = rgb_to_lab(palette_rgb.reshape(1, -1, 3)).reshape(-1, 3)
    d = ((lab[:, None, :] - pal[None, :, :]) ** 2).sum(-1)
    return d.argmin(1).reshape(shape)


def palette_sheet(colors_rgb: np.ndarray, coverage: np.ndarray, swatch: int = 120) -> np.ndarray:
    """Image for the human: which pre-mixed color goes into which palette slot. Returns RGB."""
    n = len(colors_rgb)
    cols = min(n, 4)
    rows = (n + cols - 1) // cols
    sheet = np.full((rows * (swatch + 50), cols * swatch, 3), 255, np.uint8)
    for i, (c, cov) in enumerate(zip(colors_rgb, coverage)):
        r, k = divmod(i, cols)
        y, x = r * (swatch + 50), k * swatch
        cv2.rectangle(sheet, (x + 6, y + 6), (x + swatch - 6, y + swatch - 6), tuple(int(v) for v in c), -1)
        cv2.rectangle(sheet, (x + 6, y + 6), (x + swatch - 6, y + swatch - 6), (60, 60, 60), 1)
        hexcode = "#%02X%02X%02X" % tuple(int(v) for v in c)
        cv2.putText(sheet, f"slot {i}", (x + 8, y + swatch + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.putText(sheet, f"{hexcode} {cov * 100:.0f}%", (x + 8, y + swatch + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    return sheet

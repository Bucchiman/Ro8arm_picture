"""Overhead camera: capture, rectify to canvas coordinates, and correct uneven lighting.

The camera looks down at the flat canvas at a slight angle. A photo is turned into a canvas-aligned image with the
homography from the four canvas corners (configs/machine.yaml: camera.canvas_corners). Uneven lighting and the
color cast of the light are removed with a flat-field taken of the blank canvas before painting starts.
"""

from __future__ import annotations

import cv2
import numpy as np

from painter.config import MachineConfig


def canvas_px_corners(config: MachineConfig, px_per_mm: float) -> np.ndarray:
    w, h = config.canvas.width * px_per_mm, config.canvas.height * px_per_mm
    return np.float32([[0, 0], [w, 0], [w, h], [0, h]])


def rectify(frame_bgr: np.ndarray, config: MachineConfig, px_per_mm: float) -> np.ndarray:
    """Camera photo (BGR) -> canvas-aligned RGB image at px_per_mm."""
    dst = canvas_px_corners(config, px_per_mm)
    H = cv2.getPerspectiveTransform(np.float32(config.camera.canvas_corners), dst)
    size = (int(round(dst[2, 0])), int(round(dst[2, 1])))
    rect = cv2.warpPerspective(frame_bgr, H, size, flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    return cv2.cvtColor(rect, cv2.COLOR_BGR2RGB)


class FlatField:
    """Lighting/white-balance correction from a photo of the blank (white) canvas."""

    def __init__(self, blank_rgb: np.ndarray):
        self.white = np.maximum(cv2.GaussianBlur(blank_rgb.astype(np.float32), (0, 0), 15), 1.0)

    def apply(self, rgb: np.ndarray) -> np.ndarray:
        return np.clip(rgb.astype(np.float32) / self.white * 255.0, 0, 255).astype(np.uint8)


class SimCamera:
    """Photographs a SimWorld the way a real overhead camera would: perspective, light falloff, a warm color cast,
    slight blur and sensor noise."""

    def __init__(self, world, config: MachineConfig, seed: int = 0):
        self.world = world
        self.config = config
        self.rng = np.random.default_rng(seed)
        w, h = config.camera.resolution
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r2 = ((xx - w * 0.45) / w) ** 2 + ((yy - h * 0.4) / h) ** 2
        gain = (1.02 - 0.55 * r2) * (0.94 + 0.08 * xx / w)  # vignetting + light from one side
        self.gain = gain[..., None] * np.float32([0.88, 0.97, 1.0])  # BGR: warm light, less blue

    def capture(self) -> np.ndarray:
        canvas = self.world.image()
        src = canvas_px_corners(self.config, self.world.px_per_mm)
        H = cv2.getPerspectiveTransform(src, np.float32(self.config.camera.canvas_corners))
        frame = cv2.warpPerspective(cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR), H, tuple(self.config.camera.resolution),
                                    flags=cv2.INTER_LINEAR, borderValue=(70, 85, 100))  # wooden table
        frame = frame.astype(np.float32) * self.gain
        frame = cv2.GaussianBlur(frame, (0, 0), 0.8)
        frame += self.rng.normal(0, 2.5, frame.shape).astype(np.float32)
        return np.clip(frame, 0, 255).astype(np.uint8)


class OpenCVCamera:
    """A USB/UVC camera on the machine."""

    def __init__(self, config: MachineConfig, device: int = 0):
        self.cap = cv2.VideoCapture(device)
        w, h = config.camera.resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # fixed exposure so photos are comparable

    def capture(self) -> np.ndarray:
        for _ in range(5):  # drop stale buffered frames
            self.cap.grab()
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("camera capture failed")
        return frame

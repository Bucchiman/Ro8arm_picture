"""印刷用 ArUco マーカー（DICT_4X4_50、ID 0-3）。board_frame の四隅の窪み（20.4mm 角）に貼る。

  .venv/bin/python rig/cad/markers.py               # rig/cad/out/aruco_4x4_50_id0-3_20mm.png（600dpi、A4 の左上に配置）
  .venv/bin/python rig/cad/markers.py --size 30     # 完成機の四隅（machine/cad、30mm）

印刷は「実際のサイズ / 100%」で。下の 50mm の目盛りを定規で測って確かめる。
解析ソフト（docs/rig_plan.md §5）も同じ辞書 DICT_4X4_50 を使う。
"""

from __future__ import annotations

import argparse
import os

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DPI = 600


def mm(v):
    return int(round(v / 25.4 * DPI))


def sheet(size_mm: float) -> np.ndarray:
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    W, H = mm(210), mm(297)
    img = np.full((H, W), 255, np.uint8)
    pitch = size_mm + 15
    x0, y0 = mm(15), mm(20)
    for i in range(4):
        x, y = x0 + mm(i * pitch), y0
        m = cv2.aruco.generateImageMarker(d, i, mm(size_mm))
        img[y:y + m.shape[0], x:x + m.shape[1]] = m
        s = mm(size_mm)
        g = mm(1.5)   # 切り取り線（マーカーの外側 1.5mm、細い点線）
        for k in range(0, s + 2 * g, mm(1.2)):
            for px, py in ((x - g + k, y - g), (x - g + k, y + s + g), (x - g, y - g + k), (x + s + g, y - g + k)):
                if 0 <= px < W and 0 <= py < H:
                    img[py, px] = 120
        cv2.putText(img, f"ID {i}", (x, y + s + mm(7)), cv2.FONT_HERSHEY_SIMPLEX, mm(0.12), 0, max(mm(0.25), 1))
    # 50mm の目盛り
    yb = y0 + mm(size_mm + 18)
    cv2.line(img, (x0, yb), (x0 + mm(50), yb), 0, max(mm(0.3), 1))
    for k in range(0, 51, 10):
        cv2.line(img, (x0 + mm(k), yb - mm(2)), (x0 + mm(k), yb + mm(2)), 0, max(mm(0.3), 1))
    cv2.putText(img, f"50 mm  (print at 100%)  DICT_4X4_50  marker {size_mm:g} mm", (x0, yb + mm(8)),
                cv2.FONT_HERSHEY_SIMPLEX, mm(0.1), 0, max(mm(0.2), 1))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=float, default=20.0, help="marker size in mm (rig 20, final machine 30)")
    args = ap.parse_args()
    out = os.path.join(HERE, "out", f"aruco_4x4_50_id0-3_{args.size:g}mm.png")
    Image.fromarray(sheet(args.size)).save(out, dpi=(DPI, DPI))
    print("wrote", out)


if __name__ == "__main__":
    main()

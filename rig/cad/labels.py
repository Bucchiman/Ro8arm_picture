"""印刷部品にバージョンを刻む（試験装置 rig.py と完成機 machine/cad/machine.py で共通）。

刻む場所はまず**印刷向きでベッドに着く底面**（鏡文字、裏返すと読める）。底面に入らない部品（溝や穴で埋まって
いる・細い）は、印刷すると天面になる上向きの平らな面に普通の文字で刻む。深さ 0.4mm（0.2mm 積層の 2 層分）。

  - 底面の断面（z = 0.2）を 1mm 内側に縮めた領域に、文字の外接長方形がまるごと入る位置を探す
  - 「R1 mount」のように部品名つきから試し、入らなければ「R1」だけ、文字の高さは 4 → 2.5mm
  - 部品の形が変わったのにバージョンが同じなら、テストで止める（manifest.json の形状の指紋と比べる）
"""

from __future__ import annotations

import json
import os

import numpy as np
from manifold3d import CrossSection, FillRule, JoinType, Manifold

DEPTH = 0.4
MARGIN = 1.0
HEIGHTS = (4.0, 3.5, 3.0, 2.5)
_TEXT: dict = {}


def text_2d(s: str, h: float) -> CrossSection:
    key = (s, h)
    if key not in _TEXT:
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath
        tp = TextPath((0, 0), s, size=h / 0.729, prop=FontProperties(family="DejaVu Sans", weight="bold"))
        cs = CrossSection([p[:-1].tolist() for p in tp.to_polygons()], FillRule.EvenOdd)
        b = cs.bounds()
        _TEXT[key] = cs.translate((-(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2))
    return _TEXT[key]


def find_spot(region: CrossSection, w: float, h: float):
    """region の中に w×h の長方形（文字の外接 + 余白）が入る中心の候補のうち、region の重心に最も近いもの。"""
    if region.is_empty():
        return None
    x0, y0, x1, y1 = region.bounds()
    pts = np.concatenate([np.asarray(p) for p in region.to_polygons()])
    cx, cy = pts.mean(axis=0)
    cands = [(x, y) for x in np.arange(x0 + w / 2, x1 - w / 2 + 1e-9, 0.5)
             for y in np.arange(y0 + h / 2, y1 - h / 2 + 1e-9, 0.5)]
    cands.sort(key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    rect = CrossSection.square((w, h), True)
    for x, y in cands:
        if (rect.translate((x, y)) - region).area() < 1e-6:
            return x, y
    return None


def up_faces(m: Manifold, min_area: float = 20.0) -> list[float]:
    """上を向いた水平な面の高さ（面積の大きい順）。印刷すると天面になる面で、刻んでも形の機能に影響しにくい。"""
    mesh = m.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3]
    T = V[np.asarray(mesh.tri_verts)]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    up = n[:, 2] / (2 * area + 1e-12) > 0.999
    zs = np.round(T[up, 0, 2], 2)
    acc: dict[float, float] = {}
    for z, a in zip(zs, area[up]):
        acc[z] = acc.get(z, 0.0) + a
    return [z for z, a in sorted(acc.items(), key=lambda kv: -kv[1]) if a >= min_area and z > 0.5]


def engrave_label(m: Manifold, texts: list[str]):
    """m（印刷向き、底面 z = 0）にバージョンを刻む。返り値 (部品, 刻んだ文字と場所 or None)。
    1) 底面（鏡文字、裏返すと読める）  2) 入らなければ上向きの平らな面（普通の文字）"""
    bottom = m.slice(0.2).offset(-MARGIN, JoinType.Miter)
    faces = [("底面", 0.0, bottom)]
    for z in up_faces(m):
        region = (m.slice(z - 0.2) - m.slice(z + 0.2)).offset(-MARGIN, JoinType.Miter)
        faces.append((f"上面 z={z:g}", z, region))
    for s in texts:
        for where, z, region in faces:
            for h in HEIGHTS:
                t = text_2d(s, h)
                b = t.bounds()
                spot = find_spot(region, b[2] - b[0] + 1.0, b[3] - b[1] + 1.0)
                if spot is None:
                    continue
                if z == 0.0:
                    cut = t.mirror((1, 0)).translate(spot).extrude(DEPTH + 0.01).translate((0, 0, -0.01))
                else:
                    cut = t.translate(spot).extrude(DEPTH + 0.01).translate((0, 0, z - DEPTH))
                return m - cut, f"{s} ({h:g}mm, {where})"
    return m, None


def label_texts(prefix: str, version: str, name: str) -> list[str]:
    return [f"{prefix}{version} {name}", f"{prefix}{version}"]


def signature(m: Manifold) -> list[float]:
    b = m.bounding_box()
    return [round(m.volume(), 0)] + [round(v, 1) for v in b]


def write_manifest(path: str, version: str, parts: dict[str, Manifold], labels: dict[str, str | None]):
    data = {"version": version, "parts": {k: {"signature": signature(m), "label": labels.get(k)} for k, m in parts.items()}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def check_manifest(path: str, version: str, parts: dict[str, Manifold]) -> list[str]:
    """出力（out/manifest.json）と今の設計を比べる。問題があれば理由のリスト。"""
    if not os.path.exists(path):
        return [f"{path} がない（スクリプトを実行して出力を作る）"]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    changed = [k for k, m in parts.items()
               if k not in data["parts"] or data["parts"][k]["signature"] != signature(m)]
    gone = [k for k in data["parts"] if k not in parts]
    if data["version"] == version and (changed or gone):
        return [f"形が変わった部品があるのにバージョンが {version} のまま: {', '.join(changed + gone)} → VERSION を上げて出力し直す"]
    if data["version"] != version:
        return [f"出力が古い（out は {data['version']}、設計は {version}）→ スクリプトを実行して出力し直す"]
    return []

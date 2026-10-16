"""筆1本の試験装置（docs/rig_plan.md §3）の 3D 部品。manifold3d の CSG、寸法はすべて下の定数。

  .venv/bin/python rig/cad/rig.py          # STL を rig/cad/out/、プレビュー PNG を rig/cad/preview/ に出す
  .venv/bin/python rig/cad/rig.py --check  # 寸法チェックだけ

対象プリンタは Bambu Lab H2C。ツールヘッドの寸法は公開されていないので ★ の値は推定。
最初に fit_test.stl（クランプの輪切り + 穴径のテスト片）を印刷して ★ を実測値に直す。

座標（ヘッド側の部品）: 原点 = ノズル先端、X = 右、Y = 奥（ツールヘッド側が +Y）、Z = 上。
ツールヘッド前面が y = 0 で、筆ホルダーはその手前（y < 0）に付く。
座標（ベッド側の部品）: 原点 = ボード枠の中心、X = 右、Y = 奥、Z = 上（ベッド面が z = 0）。

部品（ねじはすべて M3。手持ちが M3 だけのため）:
  mount        ツールヘッドを左右から挟む U 字クランプ。前板にガイドを留めるナットトラップ 2 個
  guide        Ø4 シャフト 2 本を支える上下の耳 + 背板。背板の縦長穴で筆の高さを ±8mm 調整
  slider       LM4UU ×2 を圧入。中央に筆の柄の割りクランプ（M3）。上面にばね座
  pad ×2       クランプのねじ先に貼る当て板（TPU 推奨。ツールヘッドに傷を付けない）
  board_frame  キャンバス（ボード / 紙 + 裏板）を入れる枠 190×150。四隅に ArUco マーカーの窪み
  station_tray 色 A・色 B・洗浄皿・拭き取り布の位置決め。枠の前辺にあり溝で差し込む
  fit_test     クランプの輪切り（幅・奥行きの確認）+ シャフト穴・軸受穴・柄の穴の 3 段階テスト片
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from manifold3d import CrossSection, FillRule, Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PREV = os.path.join(HERE, "preview")
SEG = 64

# ---------------------------------------------------------------- H2C ツールヘッド（★ = 推定、fit_test で実測）
TH_W = 78.0          # ★ ツールヘッド本体の幅（クランプで挟む左右の面の間隔）
TH_D = 60.0          # ★ 前面から、クランプの腕が届く奥までの深さ（腕はこの 2/3 まで）
TH_Z0 = 12.0         # ★ 本体下端のノズル先端からの高さ（腕はこれより上だけを掴む）
TH_H = 70.0          # ★ 本体の高さ（プレビューのダミー用）
CLAMP_CLR = 1.0      # 片側の隙間（ねじ + 当て板で詰める）

# ---------------------------------------------------------------- 筆（平筆中 10mm、柄 Ø6.5）
HANDLE_D = 6.5       # 柄の径（パラメータ。fit_test で 3 段階を確認）
HANDLE_CLR = 0.3     # 柄の穴の直径クリアランス（割りクランプで締める）
TIP_BELOW_NOZZLE = 45.0  # 筆先はノズルより 45mm 以上下（rig_plan §3.1）
TIP_BELOW_CLAMP = 58.0   # 割りクランプ中心から筆先まで（毛 + 金具 + 柄の一部）。筆を挟む位置をこれに合わせる
#                          （guide を 8mm 下げても、ホルダー最下面が洗浄皿の縁より 5mm 上に残る値）
BRUSH_Y = -24.0      # 筆の軸の位置（ツールヘッド前面から手前へ 24mm）

# ---------------------------------------------------------------- 直動（Ø4 シャフト + LM4UU）
SHAFT_D = 4.0
SHAFT_FIT = -0.1     # 耳のシャフト穴 = 3.9（圧入）。fit_test で ±0.1 を確認
SHAFT_DX = 12.0      # シャフトの x = ±12（間隔 24）
SHAFT_LEN = 60.0
LM_D, LM_L = 8.0, 12.0   # LM4UU 外径・長さ
LM_FIT = 0.05        # 軸受穴 = 8.05（軽圧入。緩ければ瞬間接着剤）
STROKE = 12.0        # スライダーが上へ逃げられる量
SPRING_OD = 10.0     # 圧縮ばね 外径 10 / 内径 8〜9 / 自由長 25 / 線径 0.5〜0.7（ばね定数 0.2〜0.4 N/mm 目安）
SPRING_FREE = 25.0
PRELOAD = 4.0        # 静止時のばねの縮み（筆が揺れず、軽く当たれば逃げる）
SPRING_SOLID = 6.0   # ★ 密着長（線径 0.6 × 約 10 巻）

# ---------------------------------------------------------------- ねじ
M3_HOLE = 3.4
M3_NUT_AF, M3_NUT_T = 5.7, 2.6   # ナットトラップ（二面幅 5.5 + 0.2）
M3_HEAD_D, M3_HEAD_H = 6.0, 3.2

# ---------------------------------------------------------------- 部品の厚み・高さ
WALL = 5.0
PLATE_T = 6.0        # mount 前板（ナットトラップ 2.6 を入れるため 6）
GUIDE_T = 5.0        # guide 背板
EAR_T = 8.0          # 上下の耳の厚み
SLIDER_H = 14.0      # LM4UU 12 + 上下 1
SLIDER_DEPTH = 24.0  # Y 方向
SLIDER_W = 2 * (SHAFT_DX + LM_D / 2 + 3)   # = 38
SEAT_D, SEAT_DEPTH = SPRING_OD + 0.6, 1.5  # ばね座
ADJ = 8.0            # guide の高さ調整 ±8mm（縦長穴）

# ---------------------------------------------------------------- ベッド側（220×220 想定、H2C では 1 枚に収まる）
BED_W, BED_D = 320.0, 320.0   # ★ H2C の造形範囲（印刷できるかの確認用）
FRAME_W, FRAME_D, FRAME_T = 190.0, 150.0, 6.0
POCKET_W, POCKET_D, POCKET_T = 142.0, 102.0, 3.0   # キャンバスボード / 紙 + 裏板（厚み 3 まで）。マーカーの窪みと 1.5mm 以上離す
DRAW_W, DRAW_D = 136.0, 96.0                       # 描画エリア（ポケットの縁から 3mm 内側）
MARKER = 20.0        # ArUco マーカー 20mm（ID 0-3）
MARKER_RECESS = 0.6  # 普通紙 + 両面テープ
MARKER_C = (FRAME_W / 2 - 2 - MARKER / 2 - 0.2, FRAME_D / 2 - 2 - MARKER / 2 - 0.2)  # 縁 2mm を残す
TRAY_W, TRAY_D, TRAY_T = 190.0, 60.0, 4.0
DISH_PAINT_D = 40.0  # ★ 絵の具皿（小さい陶器皿）の外径 + 1
DISH_WASH_D = 51.0   # 洗浄皿 Ø50 + 1（高さ 30 以下）
WIPE_W, WIPE_D = 40.0, 44.0  # 拭き取り布（両面テープ or クリップで固定）
DOVE_W, DOVE_D, DOVE_ANG = 16.0, 6.0, 15.0   # 蟻溝（上から差し込む）
DOVE_CLR = 0.25

ZONE_Z = 30.0        # 洗浄皿の高さ。筆先が皿の底にあるとき、ホルダーの最下面はこれより 5mm 以上上
# 筆の軸に沿った高さ（ノズル先端 z = 0 基準）
TIP_Z = -TIP_BELOW_NOZZLE
CLAMP_Z = TIP_Z + TIP_BELOW_CLAMP          # 割りクランプ中心 = スライダー中心（静止時）
SLIDER_Z0 = CLAMP_Z - SLIDER_H / 2
LOWER_EAR_Z1 = SLIDER_Z0                    # スライダーは下の耳の上に乗って静止
LOWER_EAR_Z0 = LOWER_EAR_Z1 - EAR_T
UPPER_EAR_Z0 = SLIDER_Z0 + SLIDER_H - SEAT_DEPTH + (SPRING_FREE - PRELOAD) - SEAT_DEPTH   # 座の底どうしの間隔 = 自由長 - 予圧
UPPER_EAR_Z1 = UPPER_EAR_Z0 + EAR_T
SHAFT_Z0 = LOWER_EAR_Z0
SHAFT_Z1 = SHAFT_Z0 + SHAFT_LEN

_TEXT_CACHE: dict = {}


# ================================================================ 形状の小道具
def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_z(r, z0, z1, x=0.0, y=0.0, seg=SEG):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate((x, y, z0))


def cyl_x(r, x0, x1, y=0.0, z=0.0, seg=SEG):
    return Manifold.cylinder(x1 - x0, r, r, seg).rotate((0, 90, 0)).translate((x0, y, z))


def cyl_y(r, y0, y1, x=0.0, z=0.0, seg=SEG):
    return Manifold.cylinder(y1 - y0, r, r, seg).rotate((-90, 0, 0)).translate((x, y0, z))


def hex_y(af, y0, y1, x, z):
    """Y 方向に伸びる六角穴（ナットトラップ）。"""
    r = af / np.sqrt(3)
    return Manifold.cylinder(y1 - y0, r, r, 6).rotate((-90, 0, 0)).translate((x, y0, z))


def hex_x(af, x0, x1, y, z):
    r = af / np.sqrt(3)
    return Manifold.cylinder(x1 - x0, r, r, 6).rotate((0, 90, 0)).translate((x0, y, z))


def slot_y(width, z0, z1, y0, y1, x):
    """Y 方向に貫通する、Z 方向の縦長穴（丸端）。"""
    r = width / 2
    return (cyl_y(r, y0, y1, x, z0) + cyl_y(r, y0, y1, x, z1) + box(x - r, x + r, y0, y1, z0, z1))


def text_2d(s, h):
    key = (s, h)
    if key not in _TEXT_CACHE:
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath
        prop = FontProperties(family="DejaVu Sans", weight="bold")
        tp = TextPath((0, 0), s, size=h / 0.729, prop=prop)
        cs = CrossSection([p[:-1].tolist() for p in tp.to_polygons()], FillRule.EvenOdd)
        b = cs.bounds()
        _TEXT_CACHE[key] = cs.translate((-(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2))
    return _TEXT_CACHE[key]


def engrave_top(m, s, h, x, y, z_top, depth=0.6):
    return m - text_2d(s, h).extrude(depth + 0.01).translate((x, y, z_top - depth))


def dovetail_2d(w, d, ang, grow=0.0):
    """蟻の断面（XY）。y = 0 が根元（幅 w）、y = -d が先端（広い）。grow で全周を太らせる。"""
    t = d * np.tan(np.radians(ang))
    pts = [(-w / 2 - grow, 0 + grow), (-w / 2 - t - grow, -d - grow), (w / 2 + t + grow, -d - grow), (w / 2 + grow, 0 + grow)]
    return CrossSection([pts])


# ================================================================ ヘッド側
def mount():
    """U 字クランプ。前板（y∈[-PLATE_T, 0]）+ 左右の腕（ツールヘッドの側面を M3 + 当て板で押す）。"""
    inner = TH_W / 2 + CLAMP_CLR
    z0 = min(z for _, z in guide_bolt_xz()) - ADJ - 6   # 前板は guide のボルト周りだけ（下へ出すと皿の縁に当たる）
    z1 = max(TH_Z0 + 48.0, max(z for _, z in guide_bolt_xz()) + ADJ + 6)
    arm_z0 = TH_Z0 + 4.0
    arm_len = TH_D * 2 / 3
    m = box(-inner - WALL, inner + WALL, -PLATE_T, 0, z0, z1)
    for s in (-1, 1):
        x0, x1 = sorted((s * inner, s * (inner + WALL)))
        m += box(x0, x1, -PLATE_T, arm_len, arm_z0, z1)
    # 腕の M3 押しねじ（外から内へ）。ナットは腕の外側に六角穴で受ける
    for s in (-1, 1):
        for y in (arm_len * 0.35, arm_len * 0.8):
            zc = (arm_z0 + z1) / 2
            x_in, x_out = s * inner, s * (inner + WALL)
            m -= cyl_x(M3_HOLE / 2, min(x_in, x_out) - 1, max(x_in, x_out) + 1, y, zc)
            nx0 = x_out - s * M3_NUT_T if s > 0 else x_out
            m -= hex_x(M3_NUT_AF, min(nx0, nx0 + s * (M3_NUT_T + 1)), max(nx0, nx0 + s * (M3_NUT_T + 1)), y, zc)
        # 予備: 面ファスナーのバンド（幅 20）を通すスロット
        m -= box(min(s * inner, s * (inner + WALL)) - 1, max(s * inner, s * (inner + WALL)) + 1,
                 arm_len * 0.5 - 1.5, arm_len * 0.5 + 1.5, (arm_z0 + z1) / 2 - 11, (arm_z0 + z1) / 2 + 11)
    # guide を留める M3 ×2（前から差し、ナットは前板の奥側 = ツールヘッド側のトラップ）
    for x, z in guide_bolt_xz():
        m -= cyl_y(M3_HOLE / 2, -PLATE_T - 1, 1, x, z)
        m -= hex_y(M3_NUT_AF, -M3_NUT_T, 1, x, z)
    return m


def guide_bolt_xz():
    """guide ↔ mount の M3 の位置（guide を高さ 0 にしたとき）。"""
    zc = (LOWER_EAR_Z0 + UPPER_EAR_Z1) / 2
    return [(-SHAFT_DX - 10, zc), (SHAFT_DX + 10, zc)]


def guide():
    """背板（y∈[-PLATE_T-GUIDE_T, -PLATE_T]）+ 上下の耳。シャフトは耳の穴に圧入、筆の柄は耳を通る。"""
    yb1 = -PLATE_T
    yb0 = yb1 - GUIDE_T
    ear_y0 = BRUSH_Y - SLIDER_DEPTH / 2 - 2
    half = SHAFT_DX + SHAFT_D / 2 + 5
    back_half = SHAFT_DX + 16
    m = box(-back_half, back_half, yb0, yb1, LOWER_EAR_Z0, UPPER_EAR_Z1)
    for z0, z1 in ((LOWER_EAR_Z0, LOWER_EAR_Z1), (UPPER_EAR_Z0, UPPER_EAR_Z1)):
        m += box(-half, half, ear_y0, yb1, z0, z1)
    for sx in (-1, 1):
        m -= cyl_z((SHAFT_D + SHAFT_FIT) / 2, LOWER_EAR_Z0 - 1, UPPER_EAR_Z1 + 1, sx * SHAFT_DX, BRUSH_Y)
    # 柄の通し穴（上下の耳）と、上の耳の下面のばね座
    m -= cyl_z(HANDLE_D / 2 + 1.0, LOWER_EAR_Z0 - 1, UPPER_EAR_Z1 + 1, 0, BRUSH_Y)
    m -= cyl_z(SEAT_D / 2, UPPER_EAR_Z0 - 0.01, UPPER_EAR_Z0 + SEAT_DEPTH, 0, BRUSH_Y)
    # 高さ調整の縦長穴（M3）
    for x, z in guide_bolt_xz():
        m -= slot_y(M3_HOLE, z - ADJ, z + ADJ, yb0 - 1, yb1 + 1, x)
    # マイクロスイッチ（任意）の座: 上の耳の右前に M2 下穴 2 個（間隔 9.5）。レバーがスライダー上面に当たる
    m -= cyl_z(1.0, UPPER_EAR_Z0 - 1, UPPER_EAR_Z1 + 1, half - 4, ear_y0 + 3)
    m -= cyl_z(1.0, UPPER_EAR_Z0 - 1, UPPER_EAR_Z1 + 1, half - 4, ear_y0 + 3 + 9.5)
    return m


def slider():
    z0, z1 = SLIDER_Z0, SLIDER_Z0 + SLIDER_H
    y0, y1 = BRUSH_Y - SLIDER_DEPTH / 2, BRUSH_Y + SLIDER_DEPTH / 2
    m = box(-SLIDER_W / 2, SLIDER_W / 2, y0, y1, z0, z1)
    for sx in (-1, 1):
        m -= cyl_z((LM_D + LM_FIT) / 2, z0 - 1, z1 + 1, sx * SHAFT_DX, BRUSH_Y)
    # 柄の割りクランプ: 穴 + 手前へのスリット + 横からの M3
    m -= cyl_z((HANDLE_D + HANDLE_CLR) / 2, z0 - 1, z1 + 1, 0, BRUSH_Y)
    m -= box(-0.75, 0.75, y0 - 1, BRUSH_Y, z0 - 1, z1 + 1)
    ys = y0 + 3.6
    xs = SHAFT_DX - LM_D / 2 - 0.6     # 軸受穴の手前で止める
    m -= cyl_x(M3_HOLE / 2, -SLIDER_W / 2 - 1, SLIDER_W / 2 + 1, ys, (z0 + z1) / 2)
    m -= cyl_x(M3_HEAD_D / 2, -SLIDER_W / 2 - 1, -xs, ys, (z0 + z1) / 2)
    m -= hex_x(M3_NUT_AF, xs, SLIDER_W / 2 + 1, ys, (z0 + z1) / 2)
    # 上面のばね座
    m -= cyl_z(SEAT_D / 2, z1 - SEAT_DEPTH, z1 + 0.01, 0, BRUSH_Y)
    return m


def pad():
    m = box(-7, 7, -7, 7, 0, 2.4)
    return m - cyl_z(1.8, 1.4, 2.5)     # ねじ先が入るくぼみ


# ================================================================ ベッド側
def marker_centers():
    mx, my = MARKER_C
    return {0: (-mx, my), 1: (mx, my), 2: (mx, -my), 3: (-mx, -my)}   # 0 = 左奥から時計回り


def board_frame():
    m = box(-FRAME_W / 2, FRAME_W / 2, -FRAME_D / 2, FRAME_D / 2, 0, FRAME_T)
    m -= box(-POCKET_W / 2, POCKET_W / 2, -POCKET_D / 2, POCKET_D / 2, FRAME_T - POCKET_T, FRAME_T + 1)
    # ボードを取り出す指かけ（左右）
    for s in (-1, 1):
        m -= cyl_z(9, FRAME_T - POCKET_T, FRAME_T + 1, s * POCKET_W / 2, 0)
    for i, (x, y) in marker_centers().items():
        h = MARKER / 2 + 0.2
        m -= box(x - h, x + h, y - h, y + h, FRAME_T - MARKER_RECESS, FRAME_T + 1)
        # マーカー ID の刻印（窪みの内側寄り）
        lx = x - np.sign(x) * (h + 4)
        m = engrave_top(m, str(i), 4, lx, y, FRAME_T)
    # 前辺の蟻溝（トレイを上から差し込む）
    for x in tray_dove_x():
        sock = dovetail_2d(DOVE_W, DOVE_D, DOVE_ANG, grow=DOVE_CLR).extrude(FRAME_T + 2).translate((x, 0, -1))
        m -= sock.mirror((0, 1, 0)).translate((0, -FRAME_D / 2, 0))   # 口（狭い側）が前辺、奥が広い
    return m


def tray_dove_x():
    return (-FRAME_W / 4, FRAME_W / 4)


def station_layout():
    """トレイ上の各ステーション中心（枠の中心基準、mm）。"""
    yc = -FRAME_D / 2 - TRAY_D / 2
    gap = (TRAY_W - 2 * DISH_PAINT_D - DISH_WASH_D - WIPE_W) / 5
    x = -TRAY_W / 2 + gap
    out = {}
    for name, w in (("paint_a", DISH_PAINT_D), ("paint_b", DISH_PAINT_D), ("wash", DISH_WASH_D), ("wipe", WIPE_W)):
        out[name] = (x + w / 2, yc)
        x += w + gap
    return out


def station_tray():
    y0, y1 = -FRAME_D / 2 - TRAY_D, -FRAME_D / 2
    m = box(-TRAY_W / 2, TRAY_W / 2, y0, y1, 0, TRAY_T)
    st = station_layout()
    for k in ("paint_a", "paint_b"):
        m -= cyl_z(DISH_PAINT_D / 2, TRAY_T - 2, TRAY_T + 1, *st[k])
    m -= cyl_z(DISH_WASH_D / 2, TRAY_T - 2, TRAY_T + 1, *st["wash"])
    wx, wy = st["wipe"]
    m -= box(wx - WIPE_W / 2, wx + WIPE_W / 2, wy - WIPE_D / 2, wy + WIPE_D / 2, TRAY_T - 1, TRAY_T + 1)
    for k, s in (("paint_a", "A"), ("paint_b", "B"), ("wash", "W")):
        x, y = st[k]
        r = (DISH_WASH_D if k == "wash" else DISH_PAINT_D) / 2
        m = engrave_top(m, s, 3.5, x, y - r + 3.5, TRAY_T - 2)
    # 枠の蟻溝に入る蟻（根元はトレイの奥辺）
    for x in tray_dove_x():
        tongue = dovetail_2d(DOVE_W, DOVE_D, DOVE_ANG).extrude(TRAY_T).translate((x, 0, 0))
        m += tongue.mirror((0, 1, 0)).translate((0, y1, 0))
    return m


# ================================================================ 合わせ用テスト片
def fit_test():
    """1) クランプの輪切り（高さ 8）: ツールヘッドに差して幅・腕の奥行きを確認
    2) 穴のテスト片: シャフト（3.8/3.9/4.0）、軸受（7.95/8.05/8.15）、柄（6.6/6.8/7.0）"""
    inner = TH_W / 2 + CLAMP_CLR
    arm_len = TH_D * 2 / 3
    ring = box(-inner - 3, inner + 3, -3, 0, 0, 8)
    for s in (-1, 1):
        x0, x1 = sorted((s * inner, s * (inner + 3)))
        ring += box(x0, x1, -3, arm_len, 0, 8)
    coupons = Manifold()
    cases = [("S", [3.8, 3.9, 4.0]), ("B", [7.95, 8.05, 8.15]), ("H", [6.6, 6.8, 7.0])]
    for row, (tag, ds) in enumerate(cases):
        y = -25 - row * 16
        bar = box(-27, 27, y - 7, y + 7, 0, 5)
        for i, d in enumerate(ds):
            x = -14 + i * 14
            bar -= cyl_z(d / 2, -1, 6, x, y + 1)
            bar = engrave_top(bar, f"{d:g}", 2.5, x, y - 5, 5, 0.5)
        bar = engrave_top(bar, tag, 4, -23, y + 1, 5)
        coupons += bar
    return ring + coupons


# ================================================================ 組立・チェック
def brush_dummy(rise=0.0):
    """筆のダミー: 柄 + 金具 + 毛（平筆 10mm 幅 × 3mm）。rise = スライダーの持ち上がり。"""
    z_tip = TIP_Z + rise
    m = cyl_z(HANDLE_D / 2, CLAMP_Z + rise - 15, UPPER_EAR_Z1 + 12 + rise, 0, BRUSH_Y)
    m += box(-5, 5, BRUSH_Y - 2, BRUSH_Y + 2, z_tip + 14, CLAMP_Z + rise - 15)   # 金具
    m += box(-5, 5, BRUSH_Y - 1.5, BRUSH_Y + 1.5, z_tip, z_tip + 14)            # 毛
    return m


def toolhead_dummy():
    return box(-TH_W / 2, TH_W / 2, 0, TH_D, TH_Z0, TH_Z0 + TH_H) + cyl_z(3, 0, TH_Z0, 0, TH_D / 3)


def head_parts():
    return {"mount": mount(), "guide": guide(), "slider": slider()}


def bed_parts():
    return {"board_frame": board_frame(), "station_tray": station_tray()}


def shafts():
    return sum((cyl_z(SHAFT_D / 2, SHAFT_Z0, SHAFT_Z1, sx * SHAFT_DX, BRUSH_Y) for sx in (-1, 1)), Manifold())


def check(verbose=True):
    ok = True

    def req(cond, msg):
        nonlocal ok
        print(("OK  " if cond else "NG  ") + msg)
        ok &= bool(cond)

    H = head_parts()
    B = bed_parts()
    low = min(H["mount"].bounding_box()[2], H["guide"].bounding_box()[2] - ADJ)   # guide を一番下げたとき
    req(low - TIP_Z >= ZONE_Z + 5,
        f"筆先が洗浄皿の底にあるとき、ホルダー最下面は皿の縁より上: 最下面 - 筆先 = {low - TIP_Z:.1f} mm (>= {ZONE_Z + 5})")
    print(f"    ホルダー最下面 z = {low:.1f}、筆先 z = {TIP_Z:.1f}（ノズル先端 = 0）")
    gap_rest = UPPER_EAR_Z0 + SEAT_DEPTH - (SLIDER_Z0 + SLIDER_H - SEAT_DEPTH)
    gap_up = gap_rest - STROKE
    req(abs(SPRING_FREE - gap_rest - PRELOAD) < 1e-6, f"ばねの予圧 {SPRING_FREE - gap_rest:.1f} mm（座の間隔 {gap_rest:.1f}、自由長 {SPRING_FREE}）")
    req(gap_up > SPRING_SOLID + 1, f"ストローク {STROKE} 上がっても密着しない: {gap_up:.1f} > 密着長 {SPRING_SOLID} + 1")
    req(SHAFT_DX - SHAFT_D / 2 > SPRING_OD / 2 + 1, f"ばね外径がシャフトに当たらない: {SHAFT_DX - SHAFT_D / 2:.1f} > {SPRING_OD / 2 + 1}")
    req(SHAFT_Z1 >= UPPER_EAR_Z1, f"シャフト {SHAFT_LEN} mm が上の耳を貫く: 上端 {SHAFT_Z1:.1f} >= {UPPER_EAR_Z1:.1f}")
    req((H["slider"] ^ H["guide"]).volume() < 1e-3, "スライダー（静止時）と guide が重ならない")
    up = H["slider"].translate((0, 0, STROKE))
    req((up ^ H["guide"]).volume() < 1e-3, f"スライダーが {STROKE} mm 上がっても上の耳に当たらない")
    req((H["guide"] ^ H["mount"]).volume() < 1e-3, "guide と mount が重ならない")
    for dz in (-ADJ, ADJ):
        req((H["guide"].translate((0, 0, dz)) ^ H["mount"]).volume() < 1e-3, f"guide を {dz:+.0f} mm ずらしても mount と重ならない")
    for k in ("mount", "guide", "slider"):
        req((H[k] ^ toolhead_dummy()).volume() < 1e-3, f"{k} がツールヘッド（ダミー）に食い込まない")
    req((brush_dummy() ^ (H["guide"] + H["mount"])).volume() < 1e-3, "筆（ダミー）が guide / mount に当たらない")
    req((B["board_frame"] ^ B["station_tray"]).volume() < 1e-3, "トレイの蟻と枠の蟻溝が重ならない（クリアランスあり）")
    mx, my = MARKER_C
    req(mx - MARKER / 2 >= DRAW_W / 2 + 3 and my - MARKER / 2 >= DRAW_D / 2 + 3,
        f"マーカーと描画エリア {DRAW_W:.0f}×{DRAW_D:.0f} が 3mm 以上離れる")
    req(mx - MARKER / 2 - 0.2 >= POCKET_W / 2 + 1.5 and my - MARKER / 2 - 0.2 >= POCKET_D / 2 + 1.5,
        "マーカーの窪みとキャンバスのポケットの間に 1.5mm 以上の壁が残る")
    for k, m in {**H, **B, "fit_test": fit_test(), "pad": pad()}.items():
        req(m.status().name == "NoError" and m.volume() > 0, f"{k} の形状が正常（体積 {m.volume() / 1000:.1f} cm3）")
    for k, m in {**H, **B}.items():
        b = m.bounding_box()
        req(b[3] - b[0] <= BED_W and b[4] - b[1] <= BED_D, f"{k} がベッドに収まる: {b[3]-b[0]:.0f}×{b[4]-b[1]:.0f}×{b[5]-b[2]:.0f}")
    total_d = FRAME_D + TRAY_D
    req(total_d <= BED_D and FRAME_W <= BED_W, f"枠 + トレイ {FRAME_W:.0f}×{total_d:.0f} がプリンタのベッドに置ける")
    return ok


def save_stl(m, path):
    import trimesh
    mesh = m.to_mesh()
    t = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)
    assert t.is_watertight, path
    t.export(path)
    return t


def on_bed(m):
    b = m.bounding_box()
    return m.translate((-(b[0] + b[3]) / 2, -(b[1] + b[4]) / 2, -b[2]))


def print_orient():
    """印刷向き: mount は前板を下（腕が上）、guide は背板を下（耳が上）、他はそのまま。"""
    H, B = head_parts(), bed_parts()
    return {
        "mount": on_bed(H["mount"].rotate((90, 0, 0))),      # 前板（y-）をベッドへ
        "guide": on_bed(H["guide"].rotate((-90, 0, 0))),     # 背板（y+ 側）をベッドへ
        "slider": on_bed(H["slider"]),
        "pad": on_bed(pad()),
        "board_frame": on_bed(B["board_frame"]),
        "station_tray": on_bed(B["station_tray"]),
        "fit_test": on_bed(fit_test()),
    }


def layout_json():
    """ソフト側（configs/rig.yaml 予定）に渡す設計値。ベッド側はマーカー 0 の中心基準の mm（X 右・Y 奥）。"""
    m0 = np.array(marker_centers()[0])
    rel = lambda p: [round(float(v), 2) for v in (np.array(p) - m0)]
    return {
        "note": "design values; jog only marker 0 (rig_plan 3.2). head: origin = nozzle tip",
        "head": {"brush_offset_from_nozzle": [0.0, BRUSH_Y, TIP_Z], "stroke_mm": STROKE,
                 "spring_preload_mm": round(SPRING_FREE - (UPPER_EAR_Z0 + SEAT_DEPTH - (SLIDER_Z0 + SLIDER_H - SEAT_DEPTH)), 2),
                 "height_adjust_mm": [-ADJ, ADJ]},
        "bed": {"markers": {str(i): rel(c) for i, c in marker_centers().items()},
                "marker_size_mm": MARKER,
                "draw_area": {"center": rel((0, 0)), "size": [DRAW_W, DRAW_D]},
                "stations": {k: {"center": rel(v), "diameter" if k != "wipe" else "size":
                                 ({"paint_a": DISH_PAINT_D, "paint_b": DISH_PAINT_D, "wash": DISH_WASH_D}[k]
                                  if k != "wipe" else [WIPE_W, WIPE_D])}
                             for k, v in station_layout().items()},
                "wash_dish_height_max_mm": ZONE_Z},
    }


def render(groups, path, title, lim, elev=22, azim=-60, alpha=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(8, 7), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    tris, fcs = [], []
    for m, c in groups:
        mesh = m.to_mesh()
        V = np.asarray(mesh.vert_properties)[:, :3]
        tri = V[np.asarray(mesh.tri_verts)]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.45 + 0.55 * np.clip(n @ light, 0, 1)
        rgba = np.array(matplotlib.colors.to_rgba(c))
        fc = np.tile(rgba, (len(tri), 1)); fc[:, :3] = np.clip(rgba[:3] * shade[:, None], 0, 1)
        tris.append(tri); fcs.append(fc)
    ax.add_collection3d(Poly3DCollection(np.concatenate(tris), facecolors=np.concatenate(fcs), edgecolor="none"))
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_zlim(*lim[2])
    ax.set_box_aspect([l[1] - l[0] for l in lim])
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def bed_plan(B, path):
    """ベッド側の上面図（上面付近の断面）。窪み・ポケット・蟻溝と、ソフトに渡す座標（マーカー 0 基準）を描く。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path as MPath

    fig, ax = plt.subplots(figsize=(8, 9), dpi=120)
    for m, z, c in ((B["board_frame"], FRAME_T - 0.3, "#8d99ae"), (B["board_frame"], FRAME_T - POCKET_T - 0.3, "#d9dee5"),
                    (B["station_tray"], TRAY_T - 0.3, "#c9a227"), (B["station_tray"], 0.3, "#efe0a0")):
        polys = [np.asarray(q) for q in m.slice(z).to_polygons()]
        cpath = MPath.make_compound_path(*[MPath(np.vstack([q, q[:1]]), closed=True) for q in polys])
        ax.add_patch(PathPatch(cpath, fc=c, lw=0.4, ec="#33333355", zorder=1 if c in ("#d9dee5", "#efe0a0") else 2))
    ax.add_patch(Rectangle((-DRAW_W / 2, -DRAW_D / 2), DRAW_W, DRAW_D, fill=False, ls="--", ec="#c0392b", lw=1.2, zorder=3))
    ax.text(0, DRAW_D / 2 - 6, f"draw area {DRAW_W:.0f}×{DRAW_D:.0f}", ha="center", color="#c0392b", fontsize=9, zorder=4)
    ax.text(0, -DRAW_D / 2 + 4, f"canvas pocket {POCKET_W:.0f}×{POCKET_D:.0f}, depth {POCKET_T:.0f}", ha="center",
            fontsize=8, zorder=4)
    m0 = np.array(marker_centers()[0])
    for i, (x, y) in marker_centers().items():
        ax.plot(x, y, "k+", ms=8, zorder=4)
        ax.text(x, y + MARKER / 2 + 2, f"ArUco {i}  ({x - m0[0]:.1f}, {y - m0[1]:.1f})", ha="center", fontsize=7, zorder=4)
    for k, (x, y) in station_layout().items():
        ax.plot(x, y, "k+", ms=8, zorder=4)
        ax.text(x, y - 4, f"{k}\n({x - m0[0]:.1f}, {y - m0[1]:.1f})", ha="center", va="top", fontsize=7, zorder=4)
    ax.set_aspect("equal")
    ax.set_xlim(-FRAME_W / 2 - 8, FRAME_W / 2 + 8)
    ax.set_ylim(-FRAME_D / 2 - TRAY_D - 8, FRAME_D / 2 + 8)
    ax.set_title("bed layout (top view, mm from frame center; labels = from marker 0)", fontsize=10)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="checks only, no files")
    args = ap.parse_args()
    ok = check()
    if args.check:
        sys.exit(0 if ok else 1)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREV, exist_ok=True)
    for k, m in print_orient().items():
        t = save_stl(m, os.path.join(OUT, f"{k}.stl"))
        b = t.bounds
        print(f"wrote {k}.stl  {b[1][0]-b[0][0]:.0f}×{b[1][1]-b[0][1]:.0f}×{b[1][2]-b[0][2]:.0f} mm  {t.volume/1000:.1f} cm3")
    with open(os.path.join(OUT, "rig_layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout_json(), f, indent=2, ensure_ascii=False)
    H = head_parts()
    head = [(toolhead_dummy(), (0.75, 0.75, 0.78, 0.35)), (H["mount"], "#4f7cac"), (H["guide"], "#d08c60"),
            (H["slider"], "#6a994e"), (shafts(), "#555555"), (brush_dummy(), "#7f5539")]
    lim = ((-60, 60), (-60, 60), (-50, 70))
    render(head, os.path.join(PREV, "head_assembly.png"), "brush holder on H2C toolhead (dummy, ★ dims)", lim)
    render(head, os.path.join(PREV, "head_front.png"), "front view", lim, elev=5, azim=-90)
    up = [(toolhead_dummy(), (0.75, 0.75, 0.78, 0.35)), (H["mount"], "#4f7cac"), (H["guide"], "#d08c60"),
          (H["slider"].translate((0, 0, STROKE)), "#6a994e"), (shafts(), "#555555"), (brush_dummy(STROKE), "#7f5539")]
    render(up, os.path.join(PREV, "head_side_pressed.png"), f"side view, slider raised {STROKE:.0f} mm", lim,
           elev=5, azim=0)
    bed_plan(bed_parts(), os.path.join(PREV, "bed_layout.png"))
    print("previews in", PREV)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

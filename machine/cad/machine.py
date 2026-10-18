"""完成機（docs/rig_plan.md §2 の平台プロッタ型）の CAD。manifold3d の CSG。

  .venv/bin/python machine/cad/machine.py          # STL・組立 GLB・部品表・プレビュー・天板の切り出し図を出す
  .venv/bin/python machine/cad/machine.py --check  # 寸法・干渉チェックだけ

ステーションの位置・作業範囲・筆は configs/machine_final.yaml から読む（ソフトとデジタルツインと同じ値）。
機構の寸法はこのファイルの定数。★ は購入品の代表寸法（買う物が決まったら実測で直す）。

座標: 機械座標そのまま。X = 右、Y = 手前（Y = 0 が奥、カメラの柱側）、Z = 上。
Z = 0 はキャンバス表面、ヘッドの座標は「筆先」の位置（G-code の X Y Z と同じ）。
ヘッドの部品は「筆先 = 原点、Z = 0、A = 0」の位置で作り、組立のときに (X, Y, Z) へ動かし A で回す。
ガントリーの梁はヘッドの手前側（+Y）にある（待機位置で梁がカメラとキャンバスの間に入らないため）。

構成（買う物）: アルミフレーム 2040/2020、MGN12 レール（Y×2・X）、MGN9 レール（Z）、NEMA17 ×4（X・Y×2・Z）、
NEMA14 ×1（A）、GT2 ベルト、T8 送りねじ、608 ×2、LM6UU ×2、天板 MDF 12mm、ガラス瓶 ×2、カメラ。
印刷部品は PETG（溶剤・油に PLA より強い）。ねじは M3（印刷部品どうし・小物）と M5（フレーム）。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass

import numpy as np
import yaml
from manifold3d import CrossSection, FillRule, Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "rig", "cad"))
from labels import check_manifest, engrave_label, label_texts, write_manifest  # noqa: E402

# 部品の形を 1 か所でも変えたら上げる。全部の印刷部品の底面に「M<VERSION>」を刻む（M = 完成機）
VERSION = "1"
PREFIX = "M"
OUT = os.path.join(HERE, "out")
PREV = os.path.join(HERE, "preview")
CONFIG = os.path.join(ROOT, "configs", "machine_final.yaml")
SEG = 48

with open(CONFIG, encoding="utf-8") as _f:
    CFG = yaml.safe_load(_f)
MOT = CFG["motion"]
X_RANGE, Y_RANGE, Z_RANGE = MOT["x_range"], MOT["y_range"], MOT["z_range"]
TRAVEL_Z = MOT["travel_z"]
CANVAS = CFG["canvas"]
PAL = CFG["palette"]
WASH = CFG["wash"]
WIPE = CFG["wipe"]
RACK = CFG["brush_rack"]
CAM = CFG["camera"]
BRUSHES = CFG["brushes"]

# ---------------------------------------------------------------- ソフト側（klipper/macros.cfg）と合わせる値
DIP_Z = -1.0          # DIP / WIPE で筆先を下げる高さ
WASH_R = WASH["radius"] * 0.5   # WASH の円の半径（painter.twin.export が wash.radius の半分を wash_r にする）
RACK_SLIDE = 35.0     # TOOL_PICK / TOOL_PLACE で筆をラックに出し入れする X の距離（macros.cfg の rack_slide）
DIP_SWEEP = 6.0       # DIP で筆を左右に動かす量（±）

# ---------------------------------------------------------------- 高さの積み上げ（Z = 0 がキャンバス表面）
CANVAS_T = 5.0        # キャンバスボードの厚み（F6、★）
DECK_T = 12.0         # 天板 MDF
DECK_TOP = -CANVAS_T
DECK_BOT = DECK_TOP - DECK_T
BASE_TOP = DECK_BOT   # 下枠 2040（縦置き）の上面に天板を載せる
BASE_BOT = BASE_TOP - 40.0
FOOT_H = 20.0

# ---------------------------------------------------------------- 筆ホルダー（筆先から上へ。全部の筆で同じになるよう、ゲージで突き出しを合わせる）
STICK_OUT = 30.0      # 筆先 → ホルダー下端（毛と金具の一部が出る）。ゲージ length_gauge で合わせる
COLLET_D, COLLET_Z = 22.0, (30.0, 46.0)
FLANGE_D, FLANGE_Z = 24.0, (46.0, 54.0)    # 下のつば: ラックから外すとき、フォークの下面に当たって磁石を引き離す
NECK_D, NECK_Z = 14.0, (54.0, 62.0)        # 首: ラックのフォークの溝に入る
DISC_D, DISC_Z = 28.0, (62.0, 70.0)        # 上の円板: 上面がカップリング面。ラックではフォークの上に載って吊られる
FACE_Z = DISC_Z[1]                         # カップリング面（筆先から 70mm）
BALL_D, BALL_R = 6.0, 10.0                 # 鋼球 Ø6 ×3（主軸側）、半径 10 の円周上 120° おき
MAG_D, MAG_T = 8.0, 3.0                    # ネオジム磁石 Ø8×3 ×3（主軸側）+ 同寸の磁石 ×3（ホルダー側）
HANDLE_D = {"flat_large": 8.0, "flat_medium": 6.5, "round_medium": 5.5, "round_small": 4.5}   # ★ 柄の径
HAIR_L = {"flat_large": 25.0, "flat_medium": 18.0, "round_medium": 14.0, "round_small": 10.0}  # ★ 毛の長さ

# ---------------------------------------------------------------- 主軸・フロート（ばねで上に逃げる部分）
COUPLER_Z = (70.0, 78.0)
SPINDLE_D, SPINDLE_Z = 8.0, (72.0, 140.0)  # Ø8 シャフト
BRG_OD, BRG_W = 22.0, 7.0                  # 608ZZ
HOUSING_D, HOUSING_Z = 32.0, (80.0, 104.0)
PLATE_Z = (104.0, 110.0)
PULLEY_Z = (112.0, 128.0)
GT2_PITCH = 2.0
A_TEETH = (20, 40)                         # モーター 20T → 主軸 40T（1:2）
A_BELT_L = 140.0                           # GT2 閉ループ 140mm
SHAFT6_X, SHAFT6_Y = 14.0, 26.0            # フロートの Ø6 シャフト（±14, 26）
LM6_D, LM6_L = 12.0, 19.0
FLOAT_STROKE = 10.0
SPRING_FREE, SPRING_PRELOAD, SPRING_SOLID = 27.0, 4.0, 8.0   # 内径 6.5・外径 10・自由長 27 ×2（シャフトに通す）
NEMA14 = 35.2
NEMA14_L = 34.0
NEMA14_HOLES = 26.0
NEMA17 = 42.3
NEMA17_L = 48.0
NEMA17_HOLES = 31.0

# ---------------------------------------------------------------- Z 軸（z_slide が MGN9 で上下、T8 で駆動）
ZS_PLATE_Y = (36.0, 42.0)
ZS_Z = (72.0, 141.0)
EAR_T = 8.0
MGN9_H, MGN9_BLOCK_L, MGN9_BLOCK_W = 10.0, 39.9, 20.0     # ★ レール底からブロック上面 10
MGN9_RAIL_W, MGN9_RAIL_H = 9.0, 6.5
Z_RAIL_Z = (75.0, 225.0)                                   # MGN9 150mm（下端はラックの筆より上）
ZS_BLOCK_ZC = ZS_Z[1] - MGN9_BLOCK_L / 2                   # MGN9H は z_slide の上寄りに付ける
SCREW_XY = (-36.0, 47.0)                                   # T8 の軸
T8_NUT_FLANGE = 22.0
T8_Z = (81.0, 201.0)                                       # T8×120

# ---------------------------------------------------------------- X キャリッジ・ガントリー
XC_PLATE_Y = (52.0, 58.0)
XC_X = (-20.0, 20.0)
XC_Z = (75.0, 226.0)          # 下端はラックに吊った筆（~69）より上: X キャリッジは Z で動かない
ZMOTOR_SHELF_Z = (226.0, 232.0)
MGN12_H, MGN12_BLOCK_L, MGN12_BLOCK_W = 13.0, 45.4, 27.0  # ★ MGN12H
MGN12_RAIL_W, MGN12_RAIL_H = 12.0, 8.0
BEAM_Y = (71.0, 91.0)                                      # 2040 縦置き（奥行 20・高さ 40）
BEAM_Z = (160.0, 200.0)
BEAM_X = (-66.0, 796.0)
X_RAIL_X = (-50.0, 750.0)                                  # MGN12 800mm
BELT_Z = (203.0, 209.0)
X_PULLEY_X, X_IDLER_X = -86.0, 816.0
GANTRY_Y = sum(BEAM_Y) / 2                                 # 梁の中心（筆先からの Y オフセット）

# ---------------------------------------------------------------- フレーム（Y レールは左右の 2040 の上）
Y_BEAM_X = (-65.0, 795.0)                                  # 左右の Y 梁の中心
Y_BEAM_Z = (97.0, 137.0)
Y_BEAM_Y = (11.0, 601.0)
Y_RAIL_Y = (31.0, 581.0)                                   # MGN12 550mm
Y_CAR_TOP = Y_BEAM_Z[1] + MGN12_H                          # = 150
Y_BELT_DX = -33.4                                          # Y ベルトの軸（梁の外側、左は -X 側）
Y_PULLEY_Y, Y_IDLER_Y = -4.0, 600.0
POST_Y = ((11.0, 51.0), (561.0, 601.0))
BASE_X = (-75.0, 805.0)
BASE_Y = (-80.0, 660.0)
CROSS_Y = (210.0, 400.0)                                   # 天板を支える横材（瓶の下を避ける）
MIRROR_X = Y_BEAM_X[0] + Y_BEAM_X[1]                       # 左右対称の軸 x = 365 の 2 倍

# ---------------------------------------------------------------- ステーション（印刷部品）
WELL_D, WELL_DEPTH = 34.0, 6.0
PAL_TOP = 3.0                                              # パレットの上面（皿の縁）。絵の具は底 -3 から盛って 0 付近
JAR_OD, JAR_H, JAR_WALL = 56.0, 55.0, 2.5                  # ★ ガラス瓶（内側の半径 25.5 >= wash.radius）
JAR_RIM = 3.0                                              # 瓶の縁の高さ
JAR_FILL = -8.0                                            # 溶き油の液面
RINSE = (WASH["position"][0], WASH["position"][1] + 68.0)  # 仕上げ洗い用の 2 つ目の瓶（ソフトは 1 つ目だけ使う）
RAG_W = 40.0
RACK_FORK_Z = (55.0, 61.0)
SLOT_W = 15.0
MARKER = 30.0                                              # ArUco 30mm（ID 0-3）
MARKER_OFF = 26.0                                          # キャンバスの上下の縁からマーカー中心まで（Y 方向）
MARKER_IN = 15.0                                           # キャンバスの左右の縁からマーカー中心まで（内側へ、X 方向）
#   斜め外に置くと右側のマーカーがパレットに重なるので、上下の縁の外に置く

# ---------------------------------------------------------------- カメラ
CAM_XY = (CANVAS["origin"][0] + CANVAS["width"] / 2, CANVAS["origin"][1] + CANVAS["height"] / 2)
CAM_Z = 600.0                                              # レンズ下端の高さ
SENSOR = (6.287, 4.712)                                    # ★ Raspberry Pi HQ Camera（IMX477）
LENS_F = 6.0                                               # ★ 6mm レンズ
SENSOR_PX = (4056, 3040)
MAST_Y = (-120.0, -100.0)

# ---------------------------------------------------------------- ねじ・印刷
M3, M5 = 3.4, 5.5
M3_NUT_AF, M3_NUT_T = 5.7, 2.6
PRINT_BED = (320.0, 320.0, 320.0)                          # Bambu Lab H2C の造形範囲（★）
CLEAR = 3.0                                                # 動く部品と止まっている部品の最小すき間

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


def tube_z(r_out, r_in, z0, z1, x=0.0, y=0.0):
    return cyl_z(r_out, z0, z1, x, y) - cyl_z(r_in, z0 - 1, z1 + 1, x, y)


def hex_z(af, z0, z1, x, y):
    r = af / math.sqrt(3)
    return Manifold.cylinder(z1 - z0, r, r, 6).translate((x, y, z0))


def holes_z(pts, d, z0, z1):
    return sum((cyl_z(d / 2, z0, z1, x, y, 24) for x, y in pts), Manifold())


def holes_y(pts_xz, d, y0, y1):
    return sum((cyl_y(d / 2, y0, y1, x, z, 24) for x, z in pts_xz), Manifold())


def holes_x(pts_yz, d, x0, x1):
    return sum((cyl_x(d / 2, x0, x1, y, z, 24) for y, z in pts_yz), Manifold())


def square_pts(cx, cy, s):
    return [(cx + sx * s / 2, cy + sy * s / 2) for sx in (-1, 1) for sy in (-1, 1)]


def polar_pts(r, angles_deg, cx=0.0, cy=0.0):
    return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in angles_deg]


def text_2d(s, h):
    key = (s, h)
    if key not in _TEXT_CACHE:
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath
        tp = TextPath((0, 0), s, size=h / 0.729, prop=FontProperties(family="DejaVu Sans", weight="bold"))
        cs = CrossSection([p[:-1].tolist() for p in tp.to_polygons()], FillRule.EvenOdd)
        b = cs.bounds()
        _TEXT_CACHE[key] = cs.translate((-(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2))
    return _TEXT_CACHE[key]


def engrave_top(m, s, h, x, y, z_top, depth=0.6):
    return m - text_2d(s, h).extrude(depth + 0.01).translate((x, y, z_top - depth))


def mirror_x(m):
    """左右対称の部品・配置（x → MIRROR_X - x）。"""
    return m.mirror((1, 0, 0)).translate((MIRROR_X, 0, 0))


def bbox(m):
    b = m.bounding_box()
    return np.array(b[:3]), np.array(b[3:])


# ================================================================ 計算で決まる寸法
def pitch_d(teeth):
    return teeth * GT2_PITCH / math.pi


def a_center_distance():
    """GT2 閉ループ A_BELT_L で 20T と 40T をつなぐ軸間距離。"""
    d1, d2 = (pitch_d(t) for t in A_TEETH)
    f = lambda c: 2 * c + math.pi * (d1 + d2) / 2 + (d2 - d1) ** 2 / (4 * c) - A_BELT_L
    lo, hi = 1.0, A_BELT_L / 2
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


A_C = a_center_distance()


def slot_xy(slot):
    col, row = slot % PAL["columns"], slot // PAL["columns"]
    return PAL["origin"][0] + col * PAL["pitch"][0], PAL["origin"][1] + row * PAL["pitch"][1]


def rack_xy(i):
    return RACK["origin"][0], RACK["origin"][1] + i * RACK["pitch"]


def canvas_rect():
    x0, y0 = CANVAS["origin"]
    return x0, y0, x0 + CANVAS["width"], y0 + CANVAS["height"]


def marker_centers():
    x0, y0, x1, y1 = canvas_rect()
    o, i = MARKER_OFF, MARKER_IN
    return {0: (x0 + i, y0 - o), 1: (x1 - i, y0 - o), 2: (x1 - i, y1 + o), 3: (x0 + i, y1 + o)}


# ================================================================ ヘッド（筆先 = 原点、Z = 0、A = 0）
def holder(brush_id):
    """筆ホルダー。下から: 割りクランプ（柄）→ 下のつば → 首（ラックの溝）→ 上の円板（カップリング面）。"""
    hd = HANDLE_D[brush_id] + 0.3
    m = (cyl_z(COLLET_D / 2, *COLLET_Z) + cyl_z(FLANGE_D / 2, *FLANGE_Z) + cyl_z(NECK_D / 2, *NECK_Z)
         + cyl_z(DISC_D / 2, *DISC_Z))
    m -= cyl_z(hd / 2, COLLET_Z[0] - 1, NECK_Z[1])                 # 柄の穴（円板の下で止める = 突き当て）
    m -= box(-0.75, 0.75, -COLLET_D, 0, COLLET_Z[0] - 1, COLLET_Z[1] - 2)   # 割り
    zc = sum(COLLET_Z) / 2
    m -= cyl_x(M3 / 2, -COLLET_D, COLLET_D, -hd / 2 - 3.2, zc)      # 締めねじ M3（割りを横切る）
    m -= cyl_x(3.1, -COLLET_D, -4.5, -hd / 2 - 3.2, zc)             # 頭の座ぐり
    r = M3_NUT_AF / math.sqrt(3)
    m -= Manifold.cylinder(COLLET_D, r, r, 6).rotate((0, 90, 0)).translate((4.5, -hd / 2 - 3.2, zc))
    # 上面: 鋼球を受ける溝 ×3（半径方向、丸溝）と磁石 ×3
    for a in (90, 210, 330):
        g = Manifold.cylinder(DISC_D, BALL_D / 2, BALL_D / 2, 24).rotate((0, 90, 0)).translate((2, 0, FACE_Z))
        m -= g.rotate((0, 0, a))
    for x, y in polar_pts(BALL_R, (30, 150, 270)):
        m -= cyl_z(MAG_D / 2 + 0.1, FACE_Z - MAG_T - 0.2, FACE_Z + 1, x, y, 24)
    return m


def coupler():
    """主軸の先の円板。下面に鋼球 ×3（半分埋める）と磁石 ×3、軸穴 Ø8 + 止めねじ M3。"""
    m = cyl_z(DISC_D / 2, *COUPLER_Z)
    m -= cyl_z(SPINDLE_D / 2 + 0.1, COUPLER_Z[0] + 2, COUPLER_Z[1] + 1)
    for x, y in polar_pts(BALL_R, (90, 210, 330)):
        m -= Manifold.sphere(BALL_D / 2 + 0.05, 24).translate((x, y, COUPLER_Z[0] + 1))
    for x, y in polar_pts(BALL_R, (30, 150, 270)):
        m -= cyl_z(MAG_D / 2 + 0.1, COUPLER_Z[0] - 1, COUPLER_Z[0] + MAG_T + 0.2, x, y, 24)
    zc = COUPLER_Z[0] + 5
    m -= cyl_y(M3 / 2, 0, DISC_D, 0, zc)
    m -= hex_z(M3_NUT_AF, zc - 3, COUPLER_Z[1] + 1, 0, 6.5)
    return m


def float_body():
    """フロート: 608 ×2 の軸受ハウジング + 板（A モーター NEMA14 を下から吊る）+ LM6UU ×2 のブロック。"""
    z0, z1 = HOUSING_Z
    m = cyl_z(HOUSING_D / 2, z0, z1)
    m += box(-20, A_C + NEMA14 / 2 + 3, -NEMA14 / 2 - 2, SHAFT6_Y + 8, *PLATE_Z)
    m += box(-SHAFT6_X - 10, SHAFT6_X + 10, SHAFT6_Y - 8, SHAFT6_Y + 8, z0, PLATE_Z[1])
    m += box(-8, 8, 0, SHAFT6_Y, z0, PLATE_Z[1])                       # ハウジングとブロックをつなぐ
    m -= cyl_z(BRG_OD / 2 + 0.05, z0 - 1, z0 + BRG_W)                 # 608（下）
    m -= cyl_z(BRG_OD / 2 + 0.05, z1 - BRG_W, z1 + 0.01)              # 608（上）
    m -= cyl_z(6.0, z0 - 1, PLATE_Z[1] + 1)                           # 主軸の通り（内輪だけに当てる）
    for sx in (-1, 1):
        x = sx * SHAFT6_X
        m -= cyl_z((LM6_D + 0.05) / 2, z0 + 3, z0 + 3 + LM6_L, x, SHAFT6_Y)
        m -= cyl_z(3.4, z0 - 1, PLATE_Z[1] + 1, x, SHAFT6_Y)
    m -= cyl_z(11.25, PLATE_Z[0] - 1, PLATE_Z[1] + 1, A_C, 0)         # NEMA14 のボス
    m -= holes_z(square_pts(A_C, 0, NEMA14_HOLES), M3, PLATE_Z[0] - 1, PLATE_Z[1] + 1)
    for p in square_pts(A_C, 0, NEMA14_HOLES):                        # 頭の座ぐり（上から締める）
        m -= cyl_z(3.1, PLATE_Z[1] - 2.5, PLATE_Z[1] + 1, *p, 24)
    return m


def z_slide():
    """MGN9 のブロックに付く縦板 + 上下の耳（Ø6 シャフトを圧入）+ T8 ナットの台。"""
    y0, y1 = ZS_PLATE_Y
    z0, z1 = ZS_Z
    m = box(-26, 26, y0, y1, z0, z1)
    ear_y = (SHAFT6_Y - 10, y0)
    m += box(-SHAFT6_X - 10, SHAFT6_X + 10, *ear_y, z0, z0 + EAR_T)
    m += box(-SHAFT6_X - 10, SHAFT6_X + 10, *ear_y, z1 - EAR_T, z1)
    for sx in (-1, 1):
        m -= cyl_z(2.95, z0 - 1, z1 + 1, sx * SHAFT6_X, SHAFT6_Y, 24)
    m -= cyl_z(6.5, z0 - 1, z1 + 1, 0, 0)                            # 主軸の逃げ（念のため）
    # MGN9H のねじ（15 × 16、M3）
    zc = ZS_BLOCK_ZC
    m -= holes_y([(sx * 7.5, zc + sz * 8) for sx in (-1, 1) for sz in (-1, 1)], M3, y0 - 1, y1 + 1)
    # T8 ナットの台（左後ろ）
    sx, sy = SCREW_XY
    m += box(sx - 14, -24, y0, sy + 11, z1 - EAR_T, z1)
    m -= cyl_z(5.25, z1 - EAR_T - 1, z1 + 1, sx, sy)
    m -= holes_z(polar_pts(8, (45, 135, 225, 315), sx, sy), M3, z1 - EAR_T - 1, z1 + 1)
    # タッチプローブ用マイクロスイッチ（上の耳の下、M2 下穴 ×2、間隔 9.5）。フロートが ~1mm 上がると ON
    for dy in (0.0, 9.5):
        m -= cyl_z(1.0, z1 - EAR_T - 1, z1 + 1, SHAFT6_X - 2, SHAFT6_Y - 6 + dy, 16)
    return m


def x_carriage():
    """MGN12H（梁の前面）に付く縦板。前面に MGN9 レール、上に Z モーターの棚、後ろに X ベルトの留め具。"""
    y0, y1 = XC_PLATE_Y
    m = box(*XC_X, y0, y1, *XC_Z)
    zc = sum(BEAM_Z) / 2
    m -= holes_y([(sx * 10, zc + sz * 10) for sx in (-1, 1) for sz in (-1, 1)], M3, y0 - 1, y1 + 1)   # MGN12H 20×20
    m -= holes_y([(0, z) for z in np.arange(Z_RAIL_Z[0] + 10, Z_RAIL_Z[1], 20)], M3, y0 - 1, y1 + 1)  # MGN9 レール（20 ピッチ）
    sx, sy = SCREW_XY
    s0, s1 = ZMOTOR_SHELF_Z
    m += box(sx - NEMA17 / 2 - 1, XC_X[1], sy - NEMA17 / 2, sy + NEMA17 / 2, s0, s1)
    m += box(-8, 8, y0 - 6, y1, s0 - 30, s0)                          # 棚の補強（リブ）
    m -= cyl_z(11.5, s0 - 1, s1 + 1, sx, sy)
    m -= holes_z(square_pts(sx, sy, NEMA17_HOLES), M3, s0 - 1, s1 + 1)
    # X ベルトの留め具: 梁の上へ伸びる腕 + ベルトを挟む 2 か所（溝 + 結束バンドの穴）
    arm_z = (BELT_Z[1] + 2, BELT_Z[1] + 8)
    m += box(*XC_X, y1, BEAM_Y[1] + 4, *arm_z)
    for x in (XC_X[0] + 6, XC_X[1] - 6):
        jaw = box(x - 5, x + 5, GANTRY_Y - pitch_d(20) / 2 - 3, GANTRY_Y - pitch_d(20) / 2 + 3, BELT_Z[0] - 2, arm_z[0])
        jaw -= box(x - 6, x + 6, GANTRY_Y - pitch_d(20) / 2 - 1.1, GANTRY_Y - pitch_d(20) / 2 + 1.1, BELT_Z[0] - 3, BELT_Z[1])
        m += jaw
        m -= cyl_y(1.6, BEAM_Y[0] - 10, BEAM_Y[1] + 10, x, BELT_Z[0] - 0.5, 16)
    return m


def gantry_end(left=True):
    """梁の端板: Y キャリッジに載る足 + 縦の板（梁を M5 で留める）+ 上の棚（左: X モーター、右: アイドラー）
    + Y ベルトの留め具。右は左の鏡像（棚の中身だけ違う）。左の座標で作り、右は mirror_x で配置する。"""
    yb = Y_BEAM_X[0]
    gy0, gy1 = GANTRY_Y - 23, GANTRY_Y + 23
    m = box(yb - 15, yb + 15, gy0, gy1, Y_CAR_TOP, Y_CAR_TOP + 6)                 # 足
    m += box(BEAM_X[0] - 10, BEAM_X[0], BEAM_Y[0] - 10, BEAM_Y[1] + 10, Y_CAR_TOP, BELT_Z[1] + 3)   # 縦の板
    shelf_z = (BELT_Z[1] + 3, BELT_Z[1] + 9)
    m += box(X_PULLEY_X - NEMA17 / 2 - 2, BEAM_X[0], GANTRY_Y - NEMA17 / 2 - 1, GANTRY_Y + NEMA17 / 2 + 1, *shelf_z)
    m += box(BEAM_X[0] - 10, BEAM_X[0], BEAM_Y[0] - 10, BEAM_Y[1] + 10, Y_CAR_TOP, shelf_z[1])
    # MGN12H（Y）のねじ 20×20
    m -= holes_z([(yb + sx * 10, GANTRY_Y + sy * 10) for sx in (-1, 1) for sy in (-1, 1)], M3, Y_CAR_TOP - 1, Y_CAR_TOP + 7)
    # 梁の端（2040 の芯穴 2 つ、M5）
    m -= holes_x([(GANTRY_Y, BEAM_Z[0] + 10), (GANTRY_Y, BEAM_Z[1] - 10)], M5, BEAM_X[0] - 11, BEAM_X[0] + 1)
    # 棚: 左は NEMA17（軸を下へ）、右はアイドラーの軸 M5
    if left:
        m -= cyl_z(11.5, shelf_z[0] - 1, shelf_z[1] + 1, X_PULLEY_X, GANTRY_Y)
        m -= holes_z(square_pts(X_PULLEY_X, GANTRY_Y, NEMA17_HOLES), M3, shelf_z[0] - 1, shelf_z[1] + 1)
    else:
        m -= cyl_z(M5 / 2, shelf_z[0] - 1, shelf_z[1] + 1, X_PULLEY_X, GANTRY_Y)
    # Y ベルトの留め具（梁の外側の耳。ベルトは z 141..147、x = 梁 + Y_BELT_DX + 6.4）
    bx = yb + Y_BELT_DX + pitch_d(20) / 2
    ear = box(bx - 6, yb - 15, gy0, gy1, Y_BEAM_Z[1] + 1, Y_CAR_TOP + 6)
    ear -= box(bx - 1.1, bx + 1.1, gy0 - 1, gy1 + 1, Y_BEAM_Z[1], Y_BEAM_Z[1] + 12)
    ear -= holes_x([(gy0 + 8, Y_BEAM_Z[1] + 6), (gy1 - 8, Y_BEAM_Z[1] + 6)], 3.2, bx - 7, yb - 14)
    m += ear
    return m


def y_end_mount(back=True):
    """Y 梁の端（奥 = モーター、手前 = アイドラー）。梁の上面に M5 で留める板。左の座標で作る。"""
    yb = Y_BEAM_X[0]
    py = Y_PULLEY_Y if back else Y_IDLER_Y
    beam_end = Y_BEAM_Y[0] if back else Y_BEAM_Y[1]
    seat = (beam_end, Y_RAIL_Y[0] - 1) if back else (Y_RAIL_Y[1] + 1, beam_end)
    px = yb + Y_BELT_DX
    z0 = Y_BEAM_Z[1] + 10
    m = box(yb - 10, yb + 10, *seat, Y_BEAM_Z[1], z0)                              # 梁の上の台
    y_lo, y_hi = min(seat[0], py - NEMA17 / 2 - 2), max(seat[1], py + NEMA17 / 2 + 2)
    m += box(px - NEMA17 / 2 - 2, yb + 10, y_lo, y_hi, z0, z0 + 6)
    m -= holes_z([(yb, (seat[0] + seat[1]) / 2)], M5, Y_BEAM_Z[1] - 1, z0 + 7)
    m -= cyl_z(5.0, z0 - 1, z0 + 7, yb, (seat[0] + seat[1]) / 2)                  # M5 頭の座ぐり（上から）
    if back:
        m -= cyl_z(11.5, z0 - 1, z0 + 7, px, py)
        m -= holes_z(square_pts(px, py, NEMA17_HOLES), M3, z0 - 1, z0 + 7)
    else:
        m -= cyl_z(M5 / 2, z0 - 1, z0 + 7, px, py)
    return m


# ================================================================ ステーション（天板の上）
def palette_tray():
    xs = [slot_xy(i)[0] for i in range(PAL["slots"])]
    ys = [slot_xy(i)[1] for i in range(PAL["slots"])]
    m = box(min(xs) - 20, max(xs) + 20, min(ys) - 20, max(ys) + 20, DECK_TOP, PAL_TOP)
    for i in range(PAL["slots"]):
        x, y = slot_xy(i)
        m -= cyl_z(WELL_D / 2, PAL_TOP - WELL_DEPTH, PAL_TOP + 1, x, y)
    for i in range(0, PAL["slots"], 2):
        x, y = slot_xy(i)
        m = engrave_top(m, str(i), 4, min(xs) - 13, y, PAL_TOP, 0.5)
        m = engrave_top(m, str(i + 1), 4, max(xs) + 13, y, PAL_TOP, 0.5)
    for x, y in palette_pins():
        m -= cyl_z(3.1, DECK_TOP - 1, DECK_TOP + 4, x, y, 24)
    return m


def palette_pins():
    xs = [slot_xy(i)[0] for i in range(PAL["slots"])]
    ys = [slot_xy(i)[1] for i in range(PAL["slots"])]
    cx = (min(xs) + max(xs)) / 2
    return [(cx, min(ys) - 12), (cx, max(ys) + 12)]


def jar_cup(pos):
    """天板の穴に差す瓶の受け（縁 + 筒 + 底）。瓶の縁が JAR_RIM、底が JAR_RIM - JAR_H。"""
    x, y = pos
    bottom = JAR_RIM - JAR_H
    m = tube_z(JAR_OD / 2 + 0.5 + 2.5, JAR_OD / 2 + 0.5, bottom - 3, DECK_TOP + 3, x, y)
    m += cyl_z(JAR_OD / 2 + 3, bottom - 3, bottom, x, y)
    m += tube_z(JAR_OD / 2 + 5, JAR_OD / 2 + 0.5, DECK_TOP, DECK_TOP + 3, x, y)      # 天板に載る縁
    m -= cyl_z(8, bottom - 4, bottom + 1, x, y)                                       # 水抜き・指押し
    return m


def wipe_block():
    x, y = WIPE["position"]
    L = WIPE["length"]
    x0, x1 = x - L / 2 - 10, x + L / 2 + 10            # 布はブラシの通り道より 10mm ずつ長い
    m = box(x0 - 8, x1 + 8, y - RAG_W / 2, y + RAG_W / 2, DECK_TOP, DECK_TOP + 2)
    for xb in (x0 - 8, x1):                            # 布の両端を押さえる棒（通り道の外）
        m += box(xb, xb + 8, y - RAG_W / 2, y + RAG_W / 2, DECK_TOP + 2, 2.0)
        m -= holes_z([(xb + 4, y - RAG_W / 2 + 6), (xb + 4, y + RAG_W / 2 - 6)], M3, DECK_TOP - 1, 3)
    return m


def rag():
    x, y = WIPE["position"]
    L = WIPE["length"]
    return box(x - L / 2 - 10, x + L / 2 + 10, y - RAG_W / 2 + 2, y + RAG_W / 2 - 2, DECK_TOP + 2, 0.0)


def tool_rack():
    """筆ラック: フォーク板（-X 向きに開いた溝 ×4、首が入る）+ 背の壁（天板に M5）。"""
    n = len(BRUSHES)
    x = RACK["origin"][0]
    ys = [rack_xy(i)[1] for i in range(n)]
    y0, y1 = min(ys) - RACK["pitch"] / 2 - 5, max(ys) + RACK["pitch"] / 2 + 5
    fx0 = x - DISC_D / 2 - 1
    wall = (x + DISC_D / 2 + 1, x + DISC_D / 2 + 16)
    m = box(fx0, wall[1], y0, y1, *RACK_FORK_Z)
    for y in ys:
        m -= box(fx0 - 1, x, y - SLOT_W / 2, y + SLOT_W / 2, RACK_FORK_Z[0] - 1, RACK_FORK_Z[1] + 1)
        m -= cyl_z(SLOT_W / 2, RACK_FORK_Z[0] - 1, RACK_FORK_Z[1] + 1, x, y)
    m += box(*wall, y0, y1, DECK_TOP, RACK_FORK_Z[1])
    m += box(wall[0], wall[1] + 15, y0, y1, DECK_TOP, DECK_TOP + 6)               # 足（壁の後ろだけ。前には筆先がある）
    m -= holes_z([(wall[1] + 8, y0 + 15), (wall[1] + 8, y1 - 15)], M5, DECK_TOP - 1, DECK_TOP + 7)
    for i, y in enumerate(ys):
        m = engrave_top(m, str(i), 5, wall[0] + 7.5, y, RACK_FORK_Z[1], 0.6)
    return m


def canvas_corner(i):
    """キャンバスの四隅の L 字の当て + ArUco マーカーの窪み（30mm、深さ 0.6）。0 = 左奥（基準）から時計回り。
    高さは天板から -1 まで（キャンバス表面より 1mm 低く、筆が当たらない）。"""
    x0, y0, x1, y1 = canvas_rect()
    cx, cy = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)][i]
    sx, sy = [(-1, -1), (1, -1), (1, 1), (-1, 1)][i]
    top = -1.0
    arm, w = 50.0, 8.0
    m = box(*sorted((cx, cx - sx * arm)), *sorted((cy + sy * 0.0, cy + sy * w)), DECK_TOP, top)
    m += box(*sorted((cx + sx * 0.0, cx + sx * w)), *sorted((cy, cy - sy * arm)), DECK_TOP, top)
    m += box(*sorted((cx, cx + sx * w)), *sorted((cy, cy + sy * w)), DECK_TOP, top)      # 角（2 本の腕をつなぐ）
    mx, my = marker_centers()[i]
    h = MARKER / 2 + 4
    m += box(mx - h, mx + h, my - h, my + h, DECK_TOP, top)
    m += box(*sorted((cx, mx)), *sorted((cy, my)), DECK_TOP, top)
    m -= box(mx - MARKER / 2 - 0.2, mx + MARKER / 2 + 0.2, my - MARKER / 2 - 0.2, my + MARKER / 2 + 0.2, top - 0.6, top + 1)
    m = engrave_top(m, str(i), 4, mx + sx * (h - 3.5), my - sy * (h - 3.5), top, 0.5)
    m -= holes_z([(mx - sx * (h - 4), my + sy * (h - 4))], M3, DECK_TOP - 1, top + 1)
    return m


def length_gauge():
    """筆の突き出しを STICK_OUT に合わせる治具: ホルダーの下端を当て、筆先が底に着く深さの穴。"""
    m = box(-20, 20, -15, 15, 0, STICK_OUT + 5)
    m -= cyl_z(COLLET_D / 2 + 0.5, 5, STICK_OUT + 6, -5, 0)            # ホルダー下端が穴の縁 z = 5 + STICK_OUT に当たる
    m -= box(6, 21, -2, 2, 5, STICK_OUT + 6)                            # 平筆の毛の逃げ
    return m


def foot():
    m = box(-20, 20, -20, 20, 0, FOOT_H)
    m -= cyl_z(M5 / 2, -1, FOOT_H + 1)
    m -= cyl_z(5.0, -1, FOOT_H - 6)
    return m


def camera_bracket():
    """2020 の腕の先に付けるカメラ台（Raspberry Pi HQ Camera 38×38、M2.5 穴 30×30）。レンズは下向き。"""
    x, y = CAM_XY
    top = CAM_Z + 40
    m = box(x - 25, x + 25, y - 28, y + 30, top - 6, top)                        # 腕の下面に M5 ×2
    m -= holes_z([(x, y - 12), (x, y + 18)], M5, top - 7, top + 1)
    m += box(x - 25, x + 25, y - 28, y - 22, CAM_Z + 4, top)                     # 縦の板（カメラの基板の後ろ）
    m += box(x - 22, x + 22, y - 22, y + 22, CAM_Z + 4, CAM_Z + 8)              # カメラの板
    m -= cyl_z(9, CAM_Z + 3, CAM_Z + 9, x, y)                                    # レンズの穴
    m -= holes_z(square_pts(x, y, 30), 2.7, CAM_Z + 3, CAM_Z + 9)
    return m


def light_clip(sx):
    """2020 の横棒に LED バー（幅 20）を 30° 内向きに付けるクリップ。"""
    x = CAM_XY[0] + sx * LIGHT_DX
    y = CAM_XY[1]
    m = box(x - 15, x + 15, y - 15, y + 15, CAM_Z + 40 - 6, CAM_Z + 40)
    m -= cyl_z(M5 / 2, CAM_Z + 33, CAM_Z + 41, x, y)
    m += box(x - 15, x + 15, y - 15, y - 9, CAM_Z + 10, CAM_Z + 40)
    return m


LIGHT_DX = 230.0


# ================================================================ 購入品のダミー（組立図・干渉チェック用、寸法は ★）
def ext(x0, x1, y0, y1, z0, z1):
    return box(x0, x1, y0, y1, z0, z1)


def nema(size, length, cx, cy, face_z, down=True):
    """モーター: face_z が取付面。down=True なら本体は面の上、軸は下（棚に下向きで付ける）。"""
    body = box(cx - size / 2, cx + size / 2, cy - size / 2, cy + size / 2, face_z, face_z + length) if down else \
        box(cx - size / 2, cx + size / 2, cy - size / 2, cy + size / 2, face_z - length, face_z)
    shaft = cyl_z(2.5, face_z - 20, face_z, cx, cy, 16) if down else cyl_z(2.5, face_z, face_z + 20, cx, cy, 16)
    return body + shaft


def pulley(teeth, cx, cy, z0, z1):
    return cyl_z(pitch_d(teeth) / 2 + 0.6, z0, z1, cx, cy, 32)


def brush_dummy(brush_id):
    b = next(b for b in BRUSHES if b["id"] == brush_id)
    w, hair = b["width"], HAIR_L[brush_id]
    if b["kind"] == "flat":
        m = box(-w / 2, w / 2, -1.5, 1.5, 0, hair)                                       # 毛（A = 0 で X 方向に幅）
        m += box(-w * 0.45, w * 0.45, -2.2, 2.2, hair, COLLET_Z[0] + 8)                  # 金具
    else:
        m = Manifold.cylinder(hair, w * 0.15, w / 2, 24).translate((0, 0, 0))
        m += cyl_z(w * 0.5, hair, COLLET_Z[0] + 8, 0, 0, 24)
    m += cyl_z(HANDLE_D[brush_id] / 2, COLLET_Z[0] + 8, NECK_Z[1], 0, 0, 24)              # 柄（突き当てまで）
    return m


def hair_only(brush_id):
    b = next(b for b in BRUSHES if b["id"] == brush_id)
    w, hair = b["width"], HAIR_L[brush_id]
    if b["kind"] == "flat":
        return box(-w / 2, w / 2, -1.5, 1.5, 0, hair)
    return Manifold.cylinder(hair, w * 0.15, w / 2, 24)


@dataclass
class Part:
    name: str
    mesh: Manifold
    color: str
    kind: str          # printed | purchased | stock
    group: str         # static | gantry | xcar | head | tool | hair


PRINTED = "#e07a2f"
ALU = "#b9bec4"
STEEL = "#5c6168"
BLACK = "#24272c"
GLASS = "#9fd3e6"
MDF = "#c8a978"
WHITE = "#f4f1ea"


def head_parts():
    """ヘッド（Z とともに動く）: フロート一式 + z_slide + MGN9 ブロック。筆先 = 原点の座標。"""
    C = A_C
    zc = ZS_BLOCK_ZC
    parts = [
        Part("z_slide", z_slide(), PRINTED, "printed", "head"),
        Part("float", float_body(), PRINTED, "printed", "head"),
        Part("coupler", coupler(), PRINTED, "printed", "head"),
        Part("spindle_8mm", cyl_z(SPINDLE_D / 2, *SPINDLE_Z, 0, 0, 24), STEEL, "purchased", "head"),
        Part("bearing_608", cyl_z(BRG_OD / 2, HOUSING_Z[0], HOUSING_Z[0] + BRG_W, 0, 0, 32)
             + cyl_z(BRG_OD / 2, HOUSING_Z[1] - BRG_W, HOUSING_Z[1], 0, 0, 32) - cyl_z(4, 0, 200, 0, 0, 16),
             STEEL, "purchased", "head"),
        Part("pulley_40T", pulley(40, 0, 0, *PULLEY_Z) - cyl_z(4, 0, 200, 0, 0, 16), STEEL, "purchased", "head"),
        Part("pulley_20T_A", pulley(20, C, 0, *PULLEY_Z), STEEL, "purchased", "head"),
        Part("motor_A_nema14", nema(NEMA14, NEMA14_L, C, 0, PLATE_Z[0], down=False), BLACK, "purchased", "head"),
        Part("belt_A", (cyl_z(pitch_d(40) / 2 + 1, PULLEY_Z[0] + 5, PULLEY_Z[0] + 11, 0, 0, 32)
                        - cyl_z(pitch_d(40) / 2, 0, 300, 0, 0, 32)), BLACK, "purchased", "head"),
        Part("shafts_6mm", sum((cyl_z(3, ZS_Z[0], ZS_Z[1], sx * SHAFT6_X, SHAFT6_Y, 24) for sx in (-1, 1)), Manifold()),
             STEEL, "purchased", "head"),
        Part("springs", sum((tube_z(5, 3.25, PLATE_Z[1], ZS_Z[1] - EAR_T, sx * SHAFT6_X, SHAFT6_Y) for sx in (-1, 1)),
                            Manifold()), "#8a9099", "purchased", "head"),
        Part("mgn9h_block", box(-MGN9_BLOCK_W / 2, MGN9_BLOCK_W / 2, ZS_PLATE_Y[1], XC_PLATE_Y[0] - 1.5,
                                zc - MGN9_BLOCK_L / 2, zc + MGN9_BLOCK_L / 2), STEEL, "purchased", "head"),
        Part("t8_nut", cyl_z(T8_NUT_FLANGE / 2, ZS_Z[1], ZS_Z[1] + 3.5, *SCREW_XY, 32)
             + cyl_z(5.1, ZS_Z[1] - 12, ZS_Z[1], *SCREW_XY, 24), "#b08d57", "purchased", "head"),
    ]
    return parts


def xcar_parts():
    """X キャリッジ（X とともに動き、Z では動かない）。ヘッド座標で Z = 0 のときの位置。"""
    zc = sum(BEAM_Z) / 2
    sx, sy = SCREW_XY
    return [
        Part("x_carriage", x_carriage(), PRINTED, "printed", "xcar"),
        Part("mgn12h_block_x", box(-MGN12_BLOCK_L / 2, MGN12_BLOCK_L / 2, XC_PLATE_Y[1], BEAM_Y[0] - 1.5,
                                   zc - MGN12_BLOCK_W / 2, zc + MGN12_BLOCK_W / 2), STEEL, "purchased", "xcar"),
        Part("mgn9_rail_z", box(-MGN9_RAIL_W / 2, MGN9_RAIL_W / 2, XC_PLATE_Y[0] - MGN9_RAIL_H, XC_PLATE_Y[0],
                                *Z_RAIL_Z), STEEL, "purchased", "xcar"),
        Part("motor_Z_nema17", nema(NEMA17, NEMA17_L, sx, sy, ZMOTOR_SHELF_Z[1]), BLACK, "purchased", "xcar"),
        Part("t8_screw", cyl_z(4, *T8_Z, sx, sy, 24), STEEL, "purchased", "xcar"),
        Part("coupler_5_8", cyl_z(9.5, T8_Z[1], ZMOTOR_SHELF_Z[0] - 0.5, sx, sy, 24), "#9aa0a6", "purchased", "xcar"),
    ]


def gantry_parts():
    """ガントリー（Y とともに動く）。Y = 0 のときの位置（梁はヘッドの手前 GANTRY_Y）。"""
    yb = Y_BEAM_X[0]
    left, right = gantry_end(True), mirror_x(gantry_end(False))
    car = lambda x: (box(x - MGN12_BLOCK_W / 2, x + MGN12_BLOCK_W / 2, GANTRY_Y - MGN12_BLOCK_L / 2,
                         GANTRY_Y + MGN12_BLOCK_L / 2, Y_BEAM_Z[1] + 1.5, Y_CAR_TOP)
                     - box(x - MGN12_RAIL_W / 2 - 0.3, x + MGN12_RAIL_W / 2 + 0.3, -1e4, 1e4, Y_BEAM_Z[1],
                           Y_BEAM_Z[1] + MGN12_RAIL_H + 0.3))
    belt_x = (box(X_PULLEY_X, X_IDLER_X, GANTRY_Y - pitch_d(20) / 2 - 0.8, GANTRY_Y - pitch_d(20) / 2 + 0.8, *BELT_Z)
              + box(X_PULLEY_X, X_IDLER_X, GANTRY_Y + pitch_d(20) / 2 - 0.8, GANTRY_Y + pitch_d(20) / 2 + 0.8, *BELT_Z))
    return [
        Part("gantry_end_L", left, PRINTED, "printed", "gantry"),
        Part("gantry_end_R", right, PRINTED, "printed", "gantry"),
        Part("beam_2040_X", ext(*BEAM_X, *BEAM_Y, *BEAM_Z), ALU, "stock", "gantry"),
        Part("mgn12_rail_x", box(*X_RAIL_X, BEAM_Y[0] - MGN12_RAIL_H, BEAM_Y[0], sum(BEAM_Z) / 2 - MGN12_RAIL_W / 2,
                                 sum(BEAM_Z) / 2 + MGN12_RAIL_W / 2), STEEL, "purchased", "gantry"),
        Part("mgn12h_blocks_y", car(yb) + car(MIRROR_X - yb), STEEL, "purchased", "gantry"),
        Part("motor_X_nema17", nema(NEMA17, NEMA17_L, X_PULLEY_X, GANTRY_Y, BELT_Z[1] + 9), BLACK, "purchased", "gantry"),
        Part("pulley_X", pulley(20, X_PULLEY_X, GANTRY_Y, BELT_Z[0] - 4, BELT_Z[1] + 2), STEEL, "purchased", "gantry"),
        Part("idler_X", pulley(20, MIRROR_X - X_PULLEY_X, GANTRY_Y, BELT_Z[0] - 4, BELT_Z[1] + 2), STEEL, "purchased",
             "gantry"),
        Part("belt_X", belt_x, BLACK, "purchased", "gantry"),
    ]


def static_parts(carried=None):
    """止まっている部品（フレーム・天板・ステーション・ラックの筆・カメラ）。carried はヘッドが持っている筆。"""
    P = []
    yb = Y_BEAM_X[0]
    # 下枠 2040（縦置き）
    frame = ext(BASE_X[0], BASE_X[0] + 20, BASE_Y[0] + 20, BASE_Y[1] - 20, BASE_BOT, BASE_TOP)
    frame += ext(BASE_X[1] - 20, BASE_X[1], BASE_Y[0] + 20, BASE_Y[1] - 20, BASE_BOT, BASE_TOP)
    frame += ext(*BASE_X, BASE_Y[0], BASE_Y[0] + 20, BASE_BOT, BASE_TOP)
    frame += ext(*BASE_X, BASE_Y[1] - 20, BASE_Y[1], BASE_BOT, BASE_TOP)
    for y in CROSS_Y:
        frame += ext(BASE_X[0] + 20, BASE_X[1] - 20, y - 10, y + 10, BASE_BOT, BASE_TOP)
    for x in (yb, MIRROR_X - yb):
        for py in POST_Y:
            frame += ext(x - 10, x + 10, *py, BASE_TOP, Y_BEAM_Z[0])
        frame += ext(x - 10, x + 10, *Y_BEAM_Y, *Y_BEAM_Z)
    P.append(Part("frame_2040", frame, ALU, "stock", "static"))
    rails = sum((box(x - MGN12_RAIL_W / 2, x + MGN12_RAIL_W / 2, *Y_RAIL_Y, Y_BEAM_Z[1], Y_BEAM_Z[1] + MGN12_RAIL_H)
                 for x in (yb, MIRROR_X - yb)), Manifold())
    P.append(Part("mgn12_rails_y", rails, STEEL, "purchased", "static"))
    for back in (True, False):
        m = y_end_mount(back)
        P.append(Part(f"y_{'motor' if back else 'idler'}_mount_L", m, PRINTED, "printed", "static"))
        P.append(Part(f"y_{'motor' if back else 'idler'}_mount_R", mirror_x(m), PRINTED, "printed", "static"))
    z0 = Y_BEAM_Z[1] + 16
    for x in (yb + Y_BELT_DX, MIRROR_X - yb - Y_BELT_DX):
        P.append(Part("motor_Y_nema17", nema(NEMA17, NEMA17_L, x, Y_PULLEY_Y, z0), BLACK, "purchased", "static"))
        pz = (Y_BEAM_Z[1] - 1, Y_BEAM_Z[1] + 9)          # 板の下（ベルトは梁の上面の高さ）
        P.append(Part("pulley_idler_Y", (pulley(20, x, Y_PULLEY_Y, *pz) + pulley(20, x, Y_IDLER_Y, *pz))
                      - cyl_z(2.6, pz[0] - 1, pz[1] + 1, x, Y_PULLEY_Y, 16), STEEL, "purchased", "static"))
    for (x, y) in ((BASE_X[0] + 20, BASE_Y[0] + 20), (BASE_X[1] - 20, BASE_Y[0] + 20),
                   (BASE_X[0] + 20, BASE_Y[1] - 20), (BASE_X[1] - 20, BASE_Y[1] - 20)):
        P.append(Part("foot", foot().translate((x, y, BASE_BOT - FOOT_H)), PRINTED, "printed", "static"))
    P.append(Part("deck_mdf", deck(), MDF, "stock", "static"))
    P.append(Part("canvas_board", canvas_board(), WHITE, "purchased", "canvas"))
    for i in range(4):
        P.append(Part(f"canvas_corner_{i}", canvas_corner(i), PRINTED, "printed", "edge"))
    P.append(Part("palette_tray", palette_tray(), PRINTED, "printed", "static"))
    for name, pos in (("wash", WASH["position"]), ("rinse", RINSE)):
        P.append(Part(f"jar_cup_{name}", jar_cup(pos), PRINTED, "printed", "static"))
        P.append(Part(f"jar_{name}", jar(pos), GLASS, "purchased", "static"))
    P.append(Part("wipe_block", wipe_block(), PRINTED, "printed", "static"))
    P.append(Part("rag", rag(), "#d9534f", "purchased", "canvas"))
    P.append(Part("tool_rack", tool_rack(), PRINTED, "printed", "static"))
    for i, b in enumerate(BRUSHES):
        if b["id"] == carried:
            continue
        x, y = rack_xy(i)
        drop = RACK_FORK_Z[1] - DISC_Z[0]          # ラックでは円板の下面がフォークの上面に載る
        P.append(Part(f"holder_{b['id']}_parked", holder(b["id"]).translate((x, y, drop)), PRINTED, "printed", "static"))
        P.append(Part(f"brush_{b['id']}_parked", brush_dummy(b["id"]).translate((x, y, drop)), "#7f5539", "purchased",
                      "static"))
    # カメラの柱・腕・照明
    cx, cy = CAM_XY
    mast = ext(cx - 20, cx + 20, *MAST_Y, BASE_BOT, CAM_Z + 60)
    arm = ext(cx - 10, cx + 10, MAST_Y[1], cy + 30, CAM_Z + 40, CAM_Z + 60)
    cross = ext(cx - LIGHT_DX - 20, cx + LIGHT_DX + 20, cy - 10, cy + 10, CAM_Z + 40, CAM_Z + 60)
    P.append(Part("camera_mast_2040", mast, ALU, "stock", "static"))
    P.append(Part("camera_arm_2020", arm + cross.translate((0, 0, 20)), ALU, "stock", "static"))
    P.append(Part("camera_bracket", camera_bracket(), PRINTED, "printed", "static"))
    P.append(Part("camera_hq", box(cx - 19, cx + 19, cy - 19, cy + 19, CAM_Z + 8, CAM_Z + 14)
                  + cyl_z(8.5, CAM_Z, CAM_Z + 8, cx, cy, 32), BLACK, "purchased", "static"))
    for sx in (-1, 1):
        P.append(Part("light_clip", light_clip(sx).translate((0, 0, 20)), PRINTED, "printed", "static"))
        x = cx + sx * LIGHT_DX
        P.append(Part("led_bar", box(x - 12, x + 12, cy - 150, cy + 150, CAM_Z + 22, CAM_Z + 30), "#fff3b0", "purchased",
                      "static"))
    P.append(Part("electronics_box", box(450, 750, -300, -130, BASE_BOT - FOOT_H, BASE_BOT - FOOT_H + 90), "#3a3f47",
                  "purchased", "static"))
    return P


def canvas_board():
    x0, y0, x1, y1 = canvas_rect()
    return box(x0, x1, y0, y1, DECK_TOP, 0.0)


def jar(pos):
    x, y = pos
    bottom = JAR_RIM - JAR_H
    return tube_z(JAR_OD / 2, JAR_OD / 2 - JAR_WALL, bottom + 3, JAR_RIM, x, y) + cyl_z(JAR_OD / 2, bottom, bottom + 3, x, y)


def deck_holes():
    """天板に開ける穴: 瓶 ×2（Ø56）、パレットのピン ×2（Ø6）、ラック・拭き取り・四隅の固定（M3/M5 下穴）。"""
    holes = [("jar", pos, JAR_OD + 7.0) for pos in (WASH["position"], RINSE)]
    holes += [("pin", p, 6.0) for p in palette_pins()]
    return holes


def post_notches():
    yb = Y_BEAM_X[0]
    return [(x - 10.5, x + 10.5, py[0] - 0.5, py[1] + 0.5) for x in (yb, MIRROR_X - yb) for py in POST_Y]


def deck():
    m = box(*BASE_X, *BASE_Y, DECK_BOT, DECK_TOP)
    for x0, x1, y0, y1 in post_notches():
        m -= box(x0, x1, y0, y1, DECK_BOT - 1, DECK_TOP + 1)
    for _, (x, y), d in deck_holes():
        m -= cyl_z(d / 2, DECK_BOT - 1, DECK_TOP + 1, x, y)
    return m


def place(parts, x, y, z, a_deg=0.0, carried=None):
    """ヘッド座標の部品を機械の位置へ。主軸から下（カップリング・ホルダー・筆）は A で回す。"""
    out = []
    for p in parts:
        m = p.mesh
        if p.group in ("tool", "hair") or p.name == "coupler":
            m = m.rotate((0, 0, a_deg))
        if p.group == "xcar":
            m = m.translate((x, y, 0))
        elif p.group == "gantry":
            m = m.translate((0, y, 0))
        else:
            m = m.translate((x, y, z))
        out.append(Part(p.name, m, p.color, p.kind, p.group))
    return out


def tool_parts(brush_id):
    return [Part(f"holder_{brush_id}", holder(brush_id), PRINTED, "printed", "tool"),
            Part(f"brush_{brush_id}", brush_dummy(brush_id), "#7f5539", "purchased", "tool")]


def assembly(x, y, z, a=0.0, carried="flat_large"):
    moving = head_parts() + xcar_parts() + gantry_parts() + (tool_parts(carried) if carried else [])
    return static_parts(carried) + place(moving, x, y, z, a, carried)


# ================================================================ チェック
def macro_paths():
    """ブラシを持って travel_z で動く直線（G-code のマクロの順番どおり）: 各ステーションの出入り口の間の全組み合わせ。
    ラックは TOOL_PICK 後の (rack_x - 30, y) と TOOL_PLACE 前の (rack_x - 30, y)。"""
    pts = {}
    for i in range(PAL["slots"]):
        x, y = slot_xy(i)
        pts[f"dip{i}"] = (x - DIP_SWEEP, y)
    wx, wy = WASH["position"]
    pts["wash"] = (wx + WASH_R, wy)
    px, py = WIPE["position"]
    pts["wipe_in"] = (px - WIPE["length"] / 2, py)
    pts["wipe_out"] = (px + WIPE["length"] / 2, py)
    x0, y0, x1, y1 = canvas_rect()
    for k, p in {"canvas_tl": (x0, y0), "canvas_tr": (x1, y0), "canvas_br": (x1, y1), "canvas_bl": (x0, y1)}.items():
        pts[k] = p
    for i in range(len(BRUSHES)):
        x, y = rack_xy(i)
        pts[f"rack{i}"] = (x - RACK_SLIDE, y)
    pts["park"] = tuple(CAM["park"])
    keys = list(pts)
    return pts, [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]


def check(verbose=True):
    ok = True
    results = []

    def req(cond, msg):
        nonlocal ok
        line = ("OK  " if cond else "NG  ") + msg
        results.append(line)
        if verbose:
            print(line)
        ok &= bool(cond)

    x0r, x1r = X_RANGE
    y0r, y1r = Y_RANGE
    inside = lambda x, y, m=0.0: x0r + m <= x <= x1r - m and y0r + m <= y <= y1r - m

    # --- 1. 届く範囲
    cx0, cy0, cx1, cy1 = canvas_rect()
    req(inside(cx0, cy0) and inside(cx1, cy1), f"キャンバス {CANVAS['width']}×{CANVAS['height']} が作業範囲 {x1r}×{y1r} に入る")
    req(all(inside(slot_xy(i)[0] - DIP_SWEEP, slot_xy(i)[1]) and inside(slot_xy(i)[0] + DIP_SWEEP, slot_xy(i)[1])
            for i in range(PAL["slots"])), "パレット 12 穴の DIP（±6）が作業範囲に入る")
    wx, wy = WASH["position"]
    req(inside(wx - WASH_R, wy - WASH_R) and inside(wx + WASH_R, wy + WASH_R), "洗浄の円が作業範囲に入る")
    px, py = WIPE["position"]
    req(inside(px - WIPE["length"] / 2, py) and inside(px + WIPE["length"] / 2, py), "拭き取りの往復が作業範囲に入る")
    req(all(inside(*rack_xy(i)) and inside(rack_xy(i)[0] - RACK_SLIDE, rack_xy(i)[1]) for i in range(len(BRUSHES))),
        "ラックの各スロットと出入り口（-30）が作業範囲に入る")
    req(inside(*CAM["park"]), f"カメラ撮影時の待機位置 {CAM['park']} が作業範囲に入る")

    # --- 2. 高さ（Z = 0 がキャンバス表面）
    req(abs(DECK_TOP + CANVAS_T) < 1e-9, f"天板の上面 {DECK_TOP} + キャンバス {CANVAS_T} = 0（キャンバス表面）")
    floor = PAL_TOP - WELL_DEPTH
    req(floor < DIP_Z < PAL_TOP <= TRAVEL_Z - 10,
        f"パレット: 穴の底 {floor} < DIP の筆先 {DIP_Z} < 縁 {PAL_TOP} <= travel_z - 10")
    req(JAR_RIM <= TRAVEL_Z - 10, f"瓶の縁 {JAR_RIM} が travel_z {TRAVEL_Z} より 10mm 以上下")
    req(JAR_FILL - WASH["depth_z"] >= 8, f"洗浄で毛が {JAR_FILL - WASH['depth_z']:.0f}mm 液に浸かる（>= 8）")
    req(JAR_RIM - JAR_H + 3 <= WASH["depth_z"] - 5, f"瓶の底 {JAR_RIM - JAR_H + 3:.0f} が洗浄の筆先 {WASH['depth_z']} より 5mm 以上下")
    widest = max(b["width"] for b in BRUSHES)
    inner = JAR_OD / 2 - JAR_WALL
    req(WASH_R + widest / 2 <= inner - 1, f"平筆大（{widest:.0f}mm）が円を描いても瓶の内壁に当たらない: {WASH_R + widest / 2:.1f} <= {inner - 1:.1f}")
    req(WASH["depth_z"] + COLLET_Z[0] >= JAR_RIM + 3,
        f"洗浄中もホルダーの下端 {WASH['depth_z'] + COLLET_Z[0]:.0f} が瓶の縁 {JAR_RIM} より 3mm 以上上")
    req(min(Z_RANGE) + COLLET_Z[0] >= JAR_RIM + 2,
        f"Z の下限 {min(Z_RANGE)} でもホルダーの下端が瓶の縁より上（{min(Z_RANGE) + COLLET_Z[0]:.0f} >= {JAR_RIM + 2}）")
    req(-1.5 <= rag().bounding_box()[5] <= 0, "拭き取り布の上面が 0 付近（筆先 -1 で 1mm 押し当てる）")
    req(JAR_RIM - JAR_H > BASE_BOT, f"瓶の受けの底 {JAR_RIM - JAR_H - 3:.0f} が下枠の下面 {BASE_BOT} より上（机に当たらない）")

    req(MARKER_OFF - MARKER / 2 >= widest / 2 + 1,
        f"キャンバスの縁を塗る平筆大（半幅 {widest / 2:.0f}）がマーカーに届かない: 縁からマーカーまで {MARKER_OFF - MARKER / 2:.0f}mm")
    req(MARKER_IN >= MARKER / 2, "マーカーはキャンバスの左右の縁より内側（上下の縁の外）にある")
    holes = [h for h in deck_holes() if h[0] == "jar"]
    gap_j = math.dist(holes[0][1], holes[1][1]) - 2 * (JAR_OD / 2 + 5)
    req(gap_j >= 1, f"2 つの瓶の受けの縁の間に {gap_j:.0f}mm 残る")
    px_, py_ = WIPE["position"]
    req(RINSE[1] + JAR_OD / 2 + 5 <= py_ - RAG_W / 2 - 1, "仕上げ洗いの瓶の受けと拭き取り台が重ならない")

    # --- 3. ラックと持ち替え
    drop = RACK_FORK_Z[1] - DISC_Z[0]
    req(NECK_Z[1] - NECK_Z[0] - (RACK_FORK_Z[1] - RACK_FORK_Z[0]) >= 1.5,
        f"首の高さ {NECK_Z[1] - NECK_Z[0]:.0f} がフォークの厚み {RACK_FORK_Z[1] - RACK_FORK_Z[0]:.0f} より 1.5mm 以上大きい")
    req(-1.5 <= drop <= -0.5, f"ラックの筆は {drop:+.1f}mm 下がって吊られ、Z = 0 で主軸が近づくと磁石で吸い付く")
    req(0 < RACK_FORK_Z[0] - (FLANGE_Z[1] + drop) <= 2.5,
        f"TOOL_PLACE で持ち上げると {RACK_FORK_Z[0] - (FLANGE_Z[1] + drop):.1f}mm でつばがフォークの下面に当たり、磁石が外れる")
    req(SLOT_W >= NECK_D + 0.8 and SLOT_W <= min(FLANGE_D, DISC_D) - 6, f"溝 {SLOT_W} は首 Ø{NECK_D} より広く、つば・円板より十分狭い")
    req(DISC_D <= RACK["pitch"] - 1.5, f"円板 Ø{DISC_D} がラックのピッチ {RACK['pitch']} に収まる（すき間 >= 1.5）")
    empty_gap = TRAVEL_Z + COUPLER_Z[0] - (DISC_Z[1] + drop) - 0
    req(TRAVEL_Z + FACE_Z - (FACE_Z + drop) >= 10, f"空のヘッドが travel_z でラックの上を通っても主軸とホルダーの間に {empty_gap:.0f}mm 残る")
    fork_x0 = RACK["origin"][0] - DISC_D / 2 - 1
    req(RACK["origin"][0] - RACK_SLIDE + DISC_D / 2 + 1 <= fork_x0,
        f"出入り口（rack_x - 30）で持った筆の円板がフォークに当たらない: {RACK['origin'][0] - RACK_SLIDE + DISC_D / 2:.0f} < {fork_x0:.0f}")
    req(all(b["id"] in HANDLE_D for b in BRUSHES), "全部の筆の柄の径が決まっている")

    # --- 4. ブラシを持った移動とラックの筆（平面の距離）
    pts, pairs = macro_paths()
    racked = [rack_xy(i) for i in range(len(BRUSHES))]
    need = DISC_D + CLEAR
    fork = box_xy_rack()
    worst = (1e9, None)
    for a, b in pairs:
        pa, pb = np.array(pts[a]), np.array(pts[b])
        for t in np.linspace(0, 1, 120):
            p = pa + (pb - pa) * t
            for i, r in enumerate(racked):
                if a == f"rack{i}" and t < 1e-9 or b == f"rack{i}" and t > 1 - 1e-9:
                    continue   # そのスロットの出入り口そのもの（スロットは空）
                d = float(np.hypot(*(p - r)))
                if d < worst[0]:
                    worst = (d, (a, b, i))
            dfork = dist_to_rect(p, fork) - DISC_D / 2
            if dfork < worst[0] - need + DISC_D / 2 and dfork < CLEAR:
                worst = min(worst, (need - CLEAR + dfork, (a, b, "fork")))
    d, info = worst
    req(d >= need, f"筆を持った移動（{len(pairs)} 通り）がラックの筆・フォークに近づかない: 最小 {d:.1f}mm >= {need:.0f}"
        + ("" if d >= need else f"  ← {info[0]} → {info[1]} がスロット {info[2]} に接近"))

    # --- 5. 軸の長さ・はみ出し
    zc = ZS_BLOCK_ZC
    blk = [zc + Z_RANGE[0] - MGN9_BLOCK_L / 2, zc + Z_RANGE[1] + MGN9_BLOCK_L / 2]
    req(Z_RAIL_Z[0] <= blk[0] and blk[1] <= Z_RAIL_Z[1], f"Z: ブロックが z_range {Z_RANGE} でレール {Z_RAIL_Z} の中")
    req(ZS_Z[1] + Z_RANGE[1] + 3.5 + 2 <= T8_Z[1] and ZS_Z[1] - 12 + Z_RANGE[0] >= T8_Z[0],
        f"T8（{T8_Z[1] - T8_Z[0]:.0f}mm）がナットの全行程を通る")
    req(T8_Z[1] < ZMOTOR_SHELF_Z[0] - 5, "T8 の上端とモーターの間にカップリング（25mm）が入る")
    blk = [X_RANGE[0] - MGN12_BLOCK_L / 2, X_RANGE[1] + MGN12_BLOCK_L / 2]
    req(X_RAIL_X[0] <= blk[0] and blk[1] <= X_RAIL_X[1], f"X: ブロックが x_range {X_RANGE} でレール {X_RAIL_X} の中")
    blk = [Y_RANGE[0] + GANTRY_Y - MGN12_BLOCK_L / 2, Y_RANGE[1] + GANTRY_Y + MGN12_BLOCK_L / 2]
    req(Y_RAIL_Y[0] <= blk[0] and blk[1] <= Y_RAIL_Y[1], f"Y: ブロックが y_range {Y_RANGE} でレール {Y_RAIL_Y} の中")
    H = head_parts() + xcar_parts() + tool_parts("flat_large")
    lo = min(bbox(p.mesh)[0][0] for p in H)
    hi = max(bbox(p.mesh)[1][0] for p in H)
    req(X_RANGE[0] + lo >= BEAM_X[0] + CLEAR and X_RANGE[1] + hi <= MIRROR_X - BEAM_X[0] - CLEAR,
        f"X の端でもヘッドが端板に当たらない: {X_RANGE[0] + lo:.0f} > {BEAM_X[0]}、{X_RANGE[1] + hi:.0f} < {MIRROR_X - BEAM_X[0]:.0f}")
    req(Y_BEAM_Z[0] - BASE_TOP > 0 and BEAM_Z[0] > DISC_Z[1] + 40, "梁の下面が天板の上の物（ラックの筆 ~70）より 40mm 以上上")
    c = A_C
    req(c - NEMA14 / 2 >= HOUSING_D / 2 + 2, f"A モーター（軸間 {c:.1f}mm）がハウジングに当たらない")
    gap = ZS_Z[1] - EAR_T - PLATE_Z[1]
    req(abs(SPRING_FREE - gap - SPRING_PRELOAD) < 1e-6, f"フロートのばね: 予圧 {SPRING_FREE - gap:.0f}mm（座の間隔 {gap:.0f}）")
    req(gap - FLOAT_STROKE > SPRING_SOLID + 1, f"フロートが {FLOAT_STROKE:.0f}mm 上がってもばねが密着しない（{gap - FLOAT_STROKE:.0f} > {SPRING_SOLID + 1}）")

    # --- 6. カメラ
    fov = [2 * CAM_Z * s / 2 / LENS_F for s in SENSOR]
    ms = marker_centers()
    mx = [p[0] for p in ms.values()]
    my = [p[1] for p in ms.values()]
    need_w = max(abs(v - CAM_XY[0]) for v in mx) * 2 + MARKER
    need_h = max(abs(v - CAM_XY[1]) for v in my) * 2 + MARKER
    req(fov[0] >= need_w and fov[1] >= need_h,
        f"カメラ（{LENS_F:.0f}mm レンズ、高さ {CAM_Z:.0f}）の視野 {fov[0]:.0f}×{fov[1]:.0f} がマーカーまで {need_w:.0f}×{need_h:.0f} を写す")
    ppm = SENSOR_PX[0] / fov[0]
    req(ppm >= 4, f"キャンバス上の解像度 {ppm:.1f} px/mm（>= 4）")
    occ = camera_occlusion()
    req(occ == 0, f"待機位置 {CAM['park']} でガントリーとヘッドがキャンバスとマーカーを隠さない（隠れる割合 {occ:.1%}）")
    gantry_top = max(bbox(p.mesh)[1][2] for p in xcar_parts() + gantry_parts())
    head_top = max(bbox(p.mesh)[1][2] for p in head_parts()) + Z_RANGE[1]
    req(CAM_Z + 40 - max(gantry_top, head_top) >= 30, f"カメラの腕（z {CAM_Z + 40:.0f}）がガントリーの最上部 {max(gantry_top, head_top):.0f} より 30mm 以上上")

    # --- 7. 部品どうしの干渉（代表的な姿勢）
    poses = interference_poses()
    bad = []
    for name, (x, y, z, a, carried, allow) in poses.items():
        hits = interference(x, y, z, a, carried, allow)
        if hits:
            bad.append(f"{name}: " + ", ".join(hits[:4]))
    req(not bad, f"代表的な {len(poses)} 姿勢で、動く部品と止まっている部品が重ならない" + ("" if not bad else "\n      " + "\n      ".join(bad[:8])))

    st = [p for p in static_parts(None) if p.name not in ("frame_2040", "deck_mdf", "mgn12_rails_y")]
    clash = []
    for i, a_ in enumerate(st):
        la, ha = bbox(a_.mesh)
        for b_ in st[i + 1:]:
            lb, hb = bbox(b_.mesh)
            if np.any(ha < lb) or np.any(hb < la):
                continue
            if {a_.name.split("_parked")[0].replace("holder_", "").replace("brush_", "")} == \
               {b_.name.split("_parked")[0].replace("holder_", "").replace("brush_", "")}:
                continue   # 同じ筆のホルダーと筆（柄はホルダーの中）
            if {a_.name, b_.name} <= {"jar_cup_wash", "jar_wash"} or {a_.name, b_.name} <= {"jar_cup_rinse", "jar_rinse"}:
                continue
            v = (a_.mesh ^ b_.mesh).volume()
            if v > 1e-2:
                clash.append(f"{a_.name}×{b_.name} {v:.0f}mm3")
    base = [p for p in static_parts(None) if p.name in ("frame_2040", "deck_mdf")]
    for p_ in static_parts(None):
        if p_.name in ("frame_2040", "deck_mdf", "mgn12_rails_y") or p_.name.startswith(("y_", "foot", "camera_mast", "electronics")):
            continue
        for b_ in base:
            v = (p_.mesh ^ b_.mesh).volume()
            if v > 1e-2 and not (p_.name.startswith("jar") and b_.name == "deck_mdf" and v < 1):
                clash.append(f"{p_.name}×{b_.name} {v:.0f}mm3")
    req(not clash, "止まっている部品どうし（ステーション・ラック・四隅・カメラ）と天板・下枠が重ならない"
        + ("" if not clash else "\n      " + "\n      ".join(clash[:10])))

    # --- 8. 印刷部品（底面にバージョン）
    parts_l, labels_l = labeled_parts()
    for name, lab in labels_l.items():
        req(lab is not None, f"{name} の底面にバージョンを刻める: {lab or '入る場所がない'}")
    for name, m in parts_l.items():
        lo_, hi_ = bbox(m)
        size = hi_ - lo_
        fits = sorted(size)[:2] <= sorted(PRINT_BED)[:2] and max(size) <= max(PRINT_BED)
        req(m.status().name == "NoError" and m.volume() > 0 and fits and watertight(m),
            f"{name}: 形状が正常、{size[0]:.0f}×{size[1]:.0f}×{size[2]:.0f} が H2C に収まる（{m.volume() / 1000:.1f} cm3）")
    return ok, results


def watertight(m):
    import trimesh
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True).is_watertight


def box_xy_rack():
    n = len(BRUSHES)
    x = RACK["origin"][0]
    ys = [rack_xy(i)[1] for i in range(n)]
    return (x - DISC_D / 2 - 1, x + DISC_D / 2 + 16, min(ys) - RACK["pitch"] / 2 - 5, max(ys) + RACK["pitch"] / 2 + 5)


def dist_to_rect(p, r):
    x0, x1, y0, y1 = r
    dx = max(x0 - p[0], 0, p[0] - x1)
    dy = max(y0 - p[1], 0, p[1] - y1)
    return math.hypot(dx, dy)


def camera_occlusion(n=40):
    """待機位置でのガントリー・ヘッドが、カメラからキャンバス + マーカーへの視線を遮る割合（格子点で数える）。"""
    x, y = CAM["park"]
    movers = place(head_parts() + xcar_parts() + gantry_parts() + tool_parts("flat_large"), x, y, TRAVEL_Z)
    boxes = [bbox(p.mesh) for p in movers]
    ms = marker_centers()
    xs = np.linspace(min(p[0] for p in ms.values()) - MARKER / 2, max(p[0] for p in ms.values()) + MARKER / 2, n)
    ys = np.linspace(min(p[1] for p in ms.values()) - MARKER / 2, max(p[1] for p in ms.values()) + MARKER / 2, n)
    cam = np.array([CAM_XY[0], CAM_XY[1], CAM_Z])
    blocked = 0
    for gx in xs:
        for gy in ys:
            p0 = np.array([gx, gy, 0.0])
            d = cam - p0
            for lo, hi in boxes:
                # 線分と箱の交差（スラブ法）
                t0, t1 = 0.0, 1.0
                hit = True
                for k in range(3):
                    if abs(d[k]) < 1e-12:
                        if p0[k] < lo[k] or p0[k] > hi[k]:
                            hit = False
                            break
                    else:
                        a, b = (lo[k] - p0[k]) / d[k], (hi[k] - p0[k]) / d[k]
                        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
                        if t0 > t1:
                            hit = False
                            break
                if hit:
                    blocked += 1
                    break
    return blocked / (n * n)


def interference_poses():
    """名前 → (X, Y, Z, A, 持っている筆, 重なってよい止まっている部品の名前の接頭辞)。"""
    poses = {}
    x0, y0, x1, y1 = canvas_rect()
    for k, (x, y) in {"canvas_tl": (x0, y0), "canvas_br": (x1, y1), "canvas_c": ((x0 + x1) / 2, (y0 + y1) / 2)}.items():
        poses[k] = (x, y, -4.0, 0.0, "flat_large", ("canvas",))
    for i in (0, PAL["slots"] - 1):
        x, y = slot_xy(i)
        poses[f"dip{i}"] = (x + DIP_SWEEP, y, DIP_Z, 90.0, "flat_large", ())
    wx, wy = WASH["position"]
    for a in (0.0, 90.0):
        poses[f"wash_a{a:.0f}"] = (wx + WASH_R, wy, WASH["depth_z"], a, "flat_large", ())
    poses["wash_zmin"] = (wx, wy, Z_RANGE[0], 0.0, "flat_large", ())
    poses["rinse"] = (RINSE[0] - WASH_R, RINSE[1], WASH["depth_z"], 0.0, "flat_large", ())
    px, py = WIPE["position"]
    poses["wipe_end"] = (px + WIPE["length"] / 2, py, DIP_Z, 0.0, "flat_large", ("canvas",))
    for i, b in enumerate(BRUSHES):
        x, y = rack_xy(i)
        poses[f"rack{i}_in"] = (x, y, 0.0, 0.0, b["id"], ())
        poses[f"rack{i}_out"] = (x - RACK_SLIDE, y, 0.0, 0.0, b["id"], ())
    poses["park"] = (*CAM["park"], TRAVEL_Z, 0.0, "flat_large", ())
    for k, (x, y) in {"xy_min": (X_RANGE[0], Y_RANGE[0]), "xy_max": (X_RANGE[1], Y_RANGE[1]),
                      "x0_y1": (X_RANGE[0], Y_RANGE[1]), "x1_y0": (X_RANGE[1], Y_RANGE[0])}.items():
        poses[k + "_zmax"] = (x, y, Z_RANGE[1], 0.0, "flat_large", ())
        poses[k + "_travel"] = (x, y, TRAVEL_Z, 0.0, "flat_large", ())
    return poses


def interference(x, y, z, a, carried, allow=(), tol=1e-2):
    """止まっている部品と動く部品の重なり（体積 > tol mm3）の組。毛はキャンバス・布に入ってよい。"""
    static = [p for p in static_parts(carried) if p.group != "canvas" or "canvas" not in allow]
    moving = place(head_parts() + xcar_parts() + gantry_parts() + tool_parts(carried), x, y, z, a, carried)
    hits = []
    for mv in moving:
        lo_m, hi_m = bbox(mv.mesh)
        for st in static:
            if st.group in ("canvas", "edge") and mv.name.startswith("brush_"):
                continue   # 毛はキャンバス・布に押し当てる。キャンバスの縁では毛が四隅の当て（キャンバスより低い）に触れる
            lo_s, hi_s = bbox(st.mesh)
            if np.any(hi_m < lo_s) or np.any(hi_s < lo_m):
                continue
            v = (mv.mesh ^ st.mesh).volume()
            if v > tol:
                hits.append(f"{mv.name}×{st.name} {v:.0f}mm3")
    return hits


# ================================================================ 出力
def printed_parts():
    """印刷する部品（印刷の向き）。"""
    P = {
        "x_carriage": rot(x_carriage(), (90, 0, 0)),          # 板を下に
        "z_slide": rot(z_slide(), (90, 0, 0)),
        "float": on_bed(float_body()),
        "coupler": rot(coupler(), (180, 0, 0)),               # 鋼球の面を上に
        "gantry_end_L": rot(gantry_end(True), (0, 90, 0)),    # 縦の板を下に
        "gantry_end_R": rot(gantry_end(False).mirror((1, 0, 0)), (0, -90, 0)),
        "y_motor_mount_L": on_bed(y_end_mount(True)),
        "y_motor_mount_R": on_bed(y_end_mount(True).mirror((1, 0, 0))),
        "y_idler_mount_L": on_bed(y_end_mount(False)),
        "y_idler_mount_R": on_bed(y_end_mount(False).mirror((1, 0, 0))),
        "tool_rack": on_bed(tool_rack()),
        "palette_tray": on_bed(palette_tray()),
        "jar_cup": rot(jar_cup((0, 0)), (180, 0, 0)),         # 縁を下に
        "wipe_block": on_bed(wipe_block()),
        "canvas_corner_0": on_bed(canvas_corner(0)),
        "canvas_corner_1": on_bed(canvas_corner(1)),
        "canvas_corner_2": on_bed(canvas_corner(2)),
        "canvas_corner_3": on_bed(canvas_corner(3)),
        "camera_bracket": rot(camera_bracket(), (180, 0, 0)),
        "light_clip": on_bed(light_clip(1)),
        "foot": on_bed(foot()),
        "length_gauge": on_bed(length_gauge()),
    }
    for b in BRUSHES:
        P[f"holder_{b['id']}"] = rot(holder(b["id"]), (180, 0, 0))   # カップリング面を下に
    return P


PRINT_QTY = {"jar_cup": 2, "light_clip": 2, "foot": 4}


def labeled_parts():
    """印刷向きの部品の底面にバージョンを刻んだもの（STL に書くのはこれ）。返り値 (部品, 刻んだ文字)。"""
    parts, labels = {}, {}
    for k, m in printed_parts().items():
        parts[k], labels[k] = engrave_label(m, label_texts(PREFIX, VERSION, k))
    return parts, labels


def on_bed(m):
    lo, hi = bbox(m)
    return m.translate((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))


def rot(m, r):
    return on_bed(m.rotate(r))


def save_stl(m, path):
    import trimesh
    mesh = m.to_mesh()
    t = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)
    t.export(path)
    return t


def save_glb(parts, path):
    import trimesh
    from matplotlib.colors import to_rgba
    scene = trimesh.Scene()
    for i, p in enumerate(parts):
        mesh = p.mesh.to_mesh()
        v = np.asarray(mesh.vert_properties)[:, :3]
        if len(v) == 0:
            continue
        t = trimesh.Trimesh(v, np.asarray(mesh.tri_verts), process=False)
        rgba = (np.array(to_rgba(p.color)) * 255).astype(np.uint8)
        if p.color == GLASS:
            rgba[3] = 110
        mat = trimesh.visual.material.PBRMaterial(baseColorFactor=rgba, metallicFactor=0.6 if p.kind != "printed" else 0.0,
                                                  roughnessFactor=0.5, alphaMode="BLEND" if rgba[3] < 255 else "OPAQUE")
        t.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(t, node_name=f"{i:03d}_{p.name}", geom_name=f"{i:03d}_{p.name}")
    # glTF は Y が上: Z 上 → Y 上、mm → m
    T = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
    S = np.diag([0.001, 0.001, 0.001, 1])
    scene.apply_transform(S @ T)
    scene.export(path)


def extrusion_cut_list():
    yb = Y_BEAM_X[0]
    base_inner = BASE_Y[1] - BASE_Y[0] - 40
    return [
        ("2040", "下枠 前・後", BASE_X[1] - BASE_X[0], 2),
        ("2040", "下枠 左・右", base_inner, 2),
        ("2040", "下枠 横材（天板の支え）", BASE_X[1] - BASE_X[0] - 40, len(CROSS_Y)),
        ("2040", "柱", Y_BEAM_Z[0] - BASE_TOP, 4),
        ("2040", "Y 梁", Y_BEAM_Y[1] - Y_BEAM_Y[0], 2),
        ("2040", "X 梁（ガントリー）", BEAM_X[1] - BEAM_X[0], 1),
        ("2040", "カメラの柱", CAM_Z + 60 - BASE_BOT, 1),
        ("2020", "カメラの腕", CAM_XY[1] + 30 - MAST_Y[1], 1),
        ("2020", "照明の横棒", 2 * LIGHT_DX + 40, 1),
    ]


def bom():
    """部品表（購入品）。数量・長さは設計から計算。"""
    x_belt = 2 * (MIRROR_X - X_PULLEY_X - X_PULLEY_X) + math.pi * pitch_d(20)
    y_belt = 2 * (Y_IDLER_Y - Y_PULLEY_Y) + math.pi * pitch_d(20)
    rows = [
        ("フレーム", "アルミフレーム 2040 / 2020（切断は下の表）", "", "2020 系 6mm 溝"),
        ("フレーム", "コーナーブラケット 2020 系 + M5×10 + T ナット", "24 組", "柱・横材・カメラの柱"),
        ("フレーム", "M5 T ナット + M5×10 / ×16（印刷部品・レールの固定）", "約 80 組", ""),
        ("直動", "MGN12 レール 550mm + MGN12H ブロック", "2", "Y（左右）"),
        ("直動", "MGN12 レール 800mm + MGN12H ブロック", "1", "X（梁の前面）"),
        ("直動", "MGN9 レール 150mm + MGN9H ブロック", "1", "Z"),
        ("直動", "LM6UU + Ø6×70 シャフト", "各 2", "フロート（筆圧のばね）"),
        ("直動", "圧縮ばね 内径 6.5・外径 10・自由長 27・線径 0.6〜0.8", "2", "予圧 4mm・行程 10mm"),
        ("駆動", "NEMA17 ステッピングモーター 48mm", "4", "X・Y 左・Y 右・Z"),
        ("駆動", "NEMA14 ステッピングモーター 34mm", "1", "A（筆の回転）"),
        ("駆動", "GT2 6mm ベルト（オープン）", f"{x_belt / 1000 + 2 * y_belt / 1000 + 0.3:.1f} m",
         f"X {x_belt:.0f}mm、Y {y_belt:.0f}mm ×2（+余り）"),
        ("駆動", "GT2 プーリー 20T 穴 5mm", "4", "X・Y×2・A（モーター側）"),
        ("駆動", "GT2 アイドラー 20T 穴 5mm（歯付き）", "3", "X・Y×2"),
        ("駆動", "GT2 プーリー 40T 穴 8mm", "1", "A（主軸側）"),
        ("駆動", f"GT2 閉ループベルト {A_BELT_L:.0f}mm 6mm", "1", f"A（軸間 {A_C:.1f}mm）"),
        ("駆動", "T8 送りねじ リード 2mm 120mm + 真鍮ナット（フランジ Ø22）", "1", "Z（リード 2mm で自重で落ちにくい）"),
        ("駆動", "カップリング 5mm-8mm", "1", "Z"),
        ("主軸", "608ZZ ベアリング", "2", ""),
        ("主軸", "Ø8 シャフト 70mm（主軸）", "1", ""),
        ("主軸", "鋼球 Ø6", "3", "カップリング（主軸側）"),
        ("主軸", "ネオジム磁石 Ø8×3", f"{3 + 3 * len(BRUSHES)}", "主軸 3 + ホルダー 3×筆の数（向きをそろえて吸い合う側に）"),
        ("主軸", "マイクロスイッチ（M2、穴間隔 9.5）", "1", "タッチプローブ（フロートの持ち上がりで ON）"),
        ("ステーション", "天板 MDF 12mm", f"{BASE_X[1] - BASE_X[0]:.0f}×{BASE_Y[1] - BASE_Y[0]:.0f}", "deck_cut.svg のとおりに切る"),
        ("ステーション", f"ガラス瓶 外径 {JAR_OD:.0f}・高さ {JAR_H:.0f}", "2", "洗浄・仕上げ洗い"),
        ("ステーション", "布（拭き取り）", f"{WIPE['length'] + 20:.0f}×{RAG_W - 4:.0f}", "定期的に交換"),
        ("ステーション", "キャンバスボード F6", "1", f"厚み {CANVAS_T:.0f}mm 前後"),
        ("ステーション", f"ArUco マーカー {MARKER:.0f}mm（ID 0-3、印刷して貼る）", "4", ""),
        ("カメラ", "Raspberry Pi HQ Camera + 6mm レンズ", "1", f"高さ {CAM_Z:.0f}mm から {SENSOR_PX[0] / (2 * CAM_Z * SENSOR[0] / 2 / LENS_F):.1f} px/mm"),
        ("カメラ", "円偏光フィルター（レンズ用）+ 偏光フィルム（照明用）", "1 + 2", "直交偏光で油のツヤを消す"),
        ("カメラ", "LED バー 300mm（高演色 Ra95 以上）+ 拡散板", "2", ""),
        ("電装", "BTT Octopus（TMC2209 ×5）または同等", "1", "Y は 2 モーター（stepper_y / stepper_y1）"),
        ("電装", "Raspberry Pi 5（Klipper / Moonraker / カメラ）", "1", ""),
        ("電装", "24V 電源 350W", "1", ""),
        ("電装", "エンドストップ（X・Y 左・Y 右）", "3", "Y は左右で直角を出す"),
        ("電装", "ケーブルチェーン（X・Y）、配線", "一式", ""),
    ]
    return rows


def write_bom(path):
    lines = [f"# 完成機 部品表 {PREFIX}{VERSION}（自動生成: machine/cad/machine.py）", "",
             "## 購入品", "", "| 区分 | 品名 | 数量 | メモ |", "| --- | --- | --- | --- |"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in bom()]
    lines += ["", f"印刷部品の底面に「{PREFIX}{VERSION} 部品名」（入らない部品は「{PREFIX}{VERSION}」）を鏡文字で刻んである。"]
    lines += ["", "## アルミフレームの切断", "", "| 規格 | 用途 | 長さ (mm) | 本数 |", "| --- | --- | --- | --- |"]
    total = {}
    for spec, use, L, n in extrusion_cut_list():
        lines.append(f"| {spec} | {use} | {L:.0f} | {n} |")
        total[spec] = total.get(spec, 0) + L * n
    lines += ["", "合計: " + "、".join(f"{k} {v / 1000:.2f} m" for k, v in total.items()), "",
              "## 印刷部品（PETG）", "", "| STL | 個数 | 大きさ (mm) | 体積 (cm3) |", "| --- | --- | --- | --- |"]
    vol = 0.0
    for name, m in printed_parts().items():
        lo, hi = bbox(m)
        q = PRINT_QTY.get(name, 1)
        vol += m.volume() / 1000 * q
        lines.append(f"| `{name}.stl` | {q} | {hi[0] - lo[0]:.0f}×{hi[1] - lo[1]:.0f}×{hi[2] - lo[2]:.0f} | {m.volume() / 1000:.1f} |")
    lines += ["", f"印刷部品の合計 {vol:.0f} cm3（充填率 100% 換算。PETG 約 {vol * 1.27 / 1000:.2f} kg、実際は充填 30〜40% で半分ほど）", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_deck_svg(path):
    """天板の切り出し図（1:1、mm）。外形・柱の切り欠き・穴・ステーションの位置（参考線）。"""
    x0, x1 = BASE_X
    y0, y1 = BASE_Y
    W, H = x1 - x0, y1 - y0
    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="{x0} {y0} {W} {H}">')
    s.append(f'<rect x="{x0}" y="{y0}" width="{W}" height="{H}" fill="none" stroke="black" stroke-width="0.3"/>')
    for a, b, c, d in post_notches():
        s.append(f'<rect x="{a}" y="{c}" width="{b - a}" height="{d - c}" fill="none" stroke="red" stroke-width="0.3"/>')
    for kind, (x, y), dd in deck_holes():
        s.append(f'<circle cx="{x}" cy="{y}" r="{dd / 2}" fill="none" stroke="red" stroke-width="0.3"/>')
    cx0, cy0, cx1, cy1 = canvas_rect()
    s.append(f'<rect x="{cx0}" y="{cy0}" width="{cx1 - cx0}" height="{cy1 - cy0}" fill="none" stroke="blue" '
             f'stroke-width="0.3" stroke-dasharray="4 2"/>')
    s.append(f'<text x="{cx0 + 5}" y="{cy0 + 12}" font-size="8" fill="blue">canvas {CANVAS["width"]}x{CANVAS["height"]} '
             f'(origin {CANVAS["origin"]})</text>')
    for i in range(PAL["slots"]):
        x, y = slot_xy(i)
        s.append(f'<circle cx="{x}" cy="{y}" r="{WELL_D / 2}" fill="none" stroke="blue" stroke-width="0.2" stroke-dasharray="2 2"/>')
    for i in range(len(BRUSHES)):
        x, y = rack_xy(i)
        s.append(f'<circle cx="{x}" cy="{y}" r="{DISC_D / 2}" fill="none" stroke="blue" stroke-width="0.2" stroke-dasharray="2 2"/>')
    s.append(f'<text x="{x0 + 5}" y="{y1 - 5}" font-size="8">deck MDF {DECK_T:.0f}mm, {W:.0f}x{H:.0f} mm, machine coords '
             f'(Y = 0 at the back). red = cut, blue = reference</text>')
    s.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(s))


def layout_json():
    return {
        "note": "design values from machine/cad/machine.py; machine coordinates, Z = 0 at the canvas surface, head = brush tip",
        "config": os.path.relpath(CONFIG, ROOT),
        "version": f"{PREFIX}{VERSION}",
        "work_area": {"x": X_RANGE, "y": Y_RANGE, "z": Z_RANGE},
        "heights": {"deck_top": DECK_TOP, "palette_top": PAL_TOP, "palette_floor": PAL_TOP - WELL_DEPTH,
                    "jar_rim": JAR_RIM, "jar_fill": JAR_FILL, "rack_fork_top": RACK_FORK_Z[1], "camera_lens": CAM_Z},
        "tool": {"stick_out": STICK_OUT, "coupling_face_from_tip": FACE_Z, "handle_d": HANDLE_D},
        "head": {"a_motor_center_distance": round(A_C, 2), "float_stroke": FLOAT_STROKE, "spring_preload": SPRING_PRELOAD},
        "rinse_jar": list(RINSE),
        "markers": {str(k): [round(v[0], 1), round(v[1], 1)] for k, v in marker_centers().items()},
        "frame": {"x": BASE_X, "y": BASE_Y, "z": [BASE_BOT - FOOT_H, CAM_Z + 60]},
    }


def render(parts, path, title, lim, elev=24, azim=-58, figsize=(10, 8)):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=figsize, dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    light = np.array([0.35, 0.5, 0.8])
    light /= np.linalg.norm(light)
    tris, fcs = [], []
    for p in parts:
        mesh = p.mesh.to_mesh()
        V = np.asarray(mesh.vert_properties)[:, :3]
        if len(V) == 0:
            continue
        tri = V[np.asarray(mesh.tri_verts)]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.5 + 0.5 * np.clip(n @ light, 0, 1)
        rgba = np.array(matplotlib.colors.to_rgba(p.color))
        if p.color == GLASS:
            rgba[3] = 0.45
        fc = np.tile(rgba, (len(tri), 1))
        fc[:, :3] = np.clip(rgba[:3] * shade[:, None], 0, 1)
        tris.append(tri)
        fcs.append(fc)
    ax.add_collection3d(Poly3DCollection(np.concatenate(tris), facecolors=np.concatenate(fcs), edgecolor="none"))
    ax.set_xlim(*lim[0])
    ax.set_ylim(*lim[1])
    ax.set_zlim(*lim[2])
    ax.set_box_aspect([l[1] - l[0] for l in lim])
    ax.view_init(elev=elev, azim=azim)
    ax.invert_yaxis()   # Y = 0 が奥
    ax.set_axis_off()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plan_view(path):
    """上面図: 天板の上の配置（キャンバス・パレット・瓶・布・ラック・マーカー）と作業範囲、カメラの視野。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    fig, ax = plt.subplots(figsize=(11, 9), dpi=110)
    ax.add_patch(Rectangle((BASE_X[0], BASE_Y[0]), BASE_X[1] - BASE_X[0], BASE_Y[1] - BASE_Y[0], fc=MDF, ec="k", lw=0.8))
    ax.add_patch(Rectangle((X_RANGE[0], Y_RANGE[0]), X_RANGE[1] - X_RANGE[0], Y_RANGE[1] - Y_RANGE[0], fill=False,
                           ls="--", ec="#444", lw=1))
    ax.text(X_RANGE[0] + 3, Y_RANGE[0] + 12, f"brush tip reach {X_RANGE[1]:.0f}×{Y_RANGE[1]:.0f}", fontsize=8, color="#444")
    cx0, cy0, cx1, cy1 = canvas_rect()
    ax.add_patch(Rectangle((cx0, cy0), cx1 - cx0, cy1 - cy0, fc=WHITE, ec="k"))
    ax.text((cx0 + cx1) / 2, (cy0 + cy1) / 2, f"canvas F6 {CANVAS['width']}×{CANVAS['height']}", ha="center", fontsize=10)
    for i, (x, y) in marker_centers().items():
        ax.add_patch(Rectangle((x - MARKER / 2, y - MARKER / 2), MARKER, MARKER, fc="k"))
        ax.text(x, y, str(i), color="w", ha="center", va="center", fontsize=8)
    for i in range(PAL["slots"]):
        x, y = slot_xy(i)
        ax.add_patch(Circle((x, y), WELL_D / 2, fc="#f2d0a4", ec="k", lw=0.5))
        ax.text(x, y, str(i), ha="center", va="center", fontsize=7)
    for name, pos in (("wash", WASH["position"]), ("rinse", RINSE)):
        ax.add_patch(Circle(pos, JAR_OD / 2, fc=GLASS, ec="k", lw=0.6))
        ax.text(*pos, name, ha="center", va="center", fontsize=7)
    px, py = WIPE["position"]
    ax.add_patch(Rectangle((px - WIPE["length"] / 2 - 10, py - RAG_W / 2 + 2), WIPE["length"] + 20, RAG_W - 4, fc="#d9534f"))
    ax.text(px, py, "rag", ha="center", va="center", fontsize=7, color="w")
    r = box_xy_rack()
    ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc=PRINTED, ec="k", lw=0.5, alpha=0.6))
    for i, b in enumerate(BRUSHES):
        x, y = rack_xy(i)
        ax.add_patch(Circle((x, y), DISC_D / 2, fc="#7f5539", ec="k", lw=0.5))
        ax.text(x + DISC_D / 2 + 18, y, b["id"], va="center", fontsize=6)
    pts, pairs = macro_paths()
    for a, b in pairs:
        if a.startswith("rack") or b.startswith("rack") or "park" in (a, b):
            ax.plot(*zip(pts[a], pts[b]), color="#2a9d8f", lw=0.25, alpha=0.6)
    ax.plot(*CAM["park"], "s", color="#264653")
    ax.text(CAM["park"][0] + 6, CAM["park"][1], "camera park", fontsize=7)
    fov = [2 * CAM_Z * s / 2 / LENS_F for s in SENSOR]
    ax.add_patch(Rectangle((CAM_XY[0] - fov[0] / 2, CAM_XY[1] - fov[1] / 2), *fov, fill=False, ec="#e76f51", ls=":", lw=1.2))
    ax.text(CAM_XY[0] - fov[0] / 2 + 3, CAM_XY[1] + fov[1] / 2 - 8, f"camera view at {CAM_Z:.0f} mm", color="#e76f51", fontsize=8)
    for x0, x1, y0, y1 in post_notches():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=ALU, ec="k", lw=0.5))
    ax.set_xlim(BASE_X[0] - 20, BASE_X[1] + 20)
    ax.set_ylim(BASE_Y[1] + 20, BASE_Y[0] - 60)
    ax.set_aspect("equal")
    ax.set_title("deck layout (machine coordinates, mm; Y = 0 at the back). green = travel moves with a brush to/from the rack")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="checks only, no files")
    args = ap.parse_args()
    ok, _ = check()
    if args.check:
        sys.exit(0 if ok else 1)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREV, exist_ok=True)
    parts_l, labels_l = labeled_parts()
    for name, m in parts_l.items():
        save_stl(m, os.path.join(OUT, f"{name}.stl"))
    write_manifest(os.path.join(OUT, "manifest.json"), f"{PREFIX}{VERSION}", parts_l, labels_l)
    print(f"wrote {len(parts_l)} STL ({PREFIX}{VERSION}) to {OUT}")
    pose = (230.0, 200.0, TRAVEL_Z, 30.0, "flat_large")
    save_glb(assembly(*pose), os.path.join(OUT, "machine_assembly.glb"))
    write_bom(os.path.join(OUT, "bom.md"))
    write_deck_svg(os.path.join(OUT, "deck_cut.svg"))
    with open(os.path.join(OUT, "machine_layout.json"), "w", encoding="utf-8") as f:
        json.dump(layout_json(), f, indent=2, ensure_ascii=False)
    print("wrote machine_assembly.glb, bom.md, deck_cut.svg, machine_layout.json")
    parts = assembly(*pose)
    lim = ((BASE_X[0] - 60, BASE_X[1] + 60), (BASE_Y[0] - 260, BASE_Y[1] + 40), (BASE_BOT - FOOT_H, CAM_Z + 80))
    render(parts, os.path.join(PREV, "machine_iso.png"), "final machine (flat-bed plotter), head at X230 Y200", lim)
    render(parts, os.path.join(PREV, "machine_front.png"), "front view", lim, elev=4, azim=-90)
    hx, hy = 690.0, 280.0   # ラックで筆を掴むところ
    near = assembly(hx, hy, 0.0, 0.0, "flat_large")
    keep = [p for p in near if p.group != "static" or bbox(p.mesh)[1][2] > -60 and
            np.all(bbox(p.mesh)[0][:2] < np.array([hx + 140, hy + 160])) and np.all(bbox(p.mesh)[1][:2] > np.array([hx - 140, hy - 160]))]
    render(keep, os.path.join(PREV, "head_at_rack.png"), "head picking flat_large from the rack (Z = 0)",
           ((hx - 120, hx + 120), (hy - 140, hy + 140), (-60, 280)), elev=18, azim=-40, figsize=(9, 9))
    hp = place(head_parts() + xcar_parts() + tool_parts("flat_medium"), 0, 0, 0, 0)
    render(hp, os.path.join(PREV, "head_closeup.png"), "head: Z slide, spring float, A belt, spindle, tool holder",
           ((-80, 100), (-60, 120), (-5, 280)), elev=12, azim=-35, figsize=(8, 10))
    plan_view(os.path.join(PREV, "deck_layout.png"))
    print("previews in", PREV)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

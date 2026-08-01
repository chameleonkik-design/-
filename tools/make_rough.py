#!/usr/bin/env python3
"""『へったのに、ふえた』のカラーラフ（色つき絵コンテ）を描く。

これは完成原画ではありません。**構図・キャラ配置・りんごの残量・人数**を
確定させるためのラフです。イラストレーターへのレイアウト指定にも、
KDPテンプレートに流し込んで余白を検証するのにも使えます。

    python3 tools/make_rough.py            # 既定のサンプルページ
    python3 tools/make_rough.py --all      # 定義済みの全ページ

平面図形＋6色限定パレットという作画指示書のスタイル規定に沿って描いています。
水彩の質感は出せないため、そこは最終画で足す前提です。
"""

from __future__ import annotations

import argparse
import math
import os

from PIL import Image, ImageDraw

# --- パレット (manuscript/作画指示書.md のスタイルバイブル) --------------------
CREAM = (247, 241, 227)
APPLE = (217, 79, 69)
APPLE_D = (183, 62, 54)
LEAF = (107, 163, 104)
LEAF_D = (84, 133, 82)
SOIL = (139, 111, 82)
SKY = (168, 203, 224)
INK = (58, 50, 38)

# 動物の色（同じ色family内で彩度・明度だけ振り分け）
FUR = {
    "bear":     (156, 124, 92),
    "mouse":    (168, 162, 152),
    "rabbit":   (240, 236, 226),
    "fox":      (214, 138, 74),
    "squirrel": (182, 110, 72),
    "bird":     (150, 190, 216),
}

SS = 3            # スーパーサンプリング倍率
SIZE = 1080       # 出力の一辺(px)


class Page:
    """0.0-1.0 の正規化座標で描けるようにした薄いラッパ。"""

    def __init__(self, bg=CREAM):
        self.n = SIZE * SS
        self.img = Image.new("RGB", (self.n, self.n), bg)
        self.d = ImageDraw.Draw(self.img)

    def px(self, v: float) -> int:
        return int(v * self.n)

    def lw(self, v: float = 0.006) -> int:
        return max(1, int(v * self.n))

    def circle(self, cx, cy, r, fill, outline=INK, w=0.006):
        x, y, rr = self.px(cx), self.px(cy), self.px(r)
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr],
                       fill=fill, outline=outline, width=self.lw(w) if outline else 0)

    def oval(self, cx, cy, rx, ry, fill, outline=INK, w=0.006):
        x, y, ax, ay = self.px(cx), self.px(cy), self.px(rx), self.px(ry)
        self.d.ellipse([x - ax, y - ay, x + ax, y + ay],
                       fill=fill, outline=outline, width=self.lw(w) if outline else 0)

    def poly(self, pts, fill, outline=INK, w=0.006):
        p = [(self.px(a), self.px(b)) for a, b in pts]
        self.d.polygon(p, fill=fill, outline=outline, width=self.lw(w) if outline else 0)

    def line(self, pts, fill=INK, w=0.006):
        p = [(self.px(a), self.px(b)) for a, b in pts]
        self.d.line(p, fill=fill, width=self.lw(w), joint="curve")

    def arcband(self, cx, cy, r, a0, a1, fill, w=0.02):
        x, y, rr = self.px(cx), self.px(cy), self.px(r)
        self.d.arc([x - rr, y - rr, x + rr, y + rr], a0, a1, fill=fill, width=self.lw(w))

    def save(self, path):
        out = self.img.resize((SIZE, SIZE), Image.LANCZOS)
        out.save(path)


# --- パーツ -------------------------------------------------------------------

def apple(p: Page, cx, cy, r, stem=True):
    p.circle(cx, cy, r, APPLE)
    p.oval(cx - r * 0.34, cy - r * 0.30, r * 0.16, r * 0.22, (255, 255, 255), outline=None)
    if stem and r > 0.012:
        p.line([(cx, cy - r * 0.92), (cx + r * 0.10, cy - r * 1.45)], INK, w=0.005)
        p.oval(cx + r * 0.62, cy - r * 1.30, r * 0.44, r * 0.24, LEAF)


def half_apple(p: Page, cx, cy, r, flip=False):
    """断面を見せた半分のりんご。"""
    s = -1 if flip else 1
    x, y, rr = p.px(cx), p.px(cy), p.px(r)
    a0, a1 = (270, 90) if not flip else (90, 270)
    p.d.pieslice([x - rr, y - rr, x + rr, y + rr], a0, a1,
                 fill=APPLE, outline=INK, width=p.lw(0.006))
    # 断面
    p.d.pieslice([x - int(rr * .82), y - int(rr * .88), x + int(rr * .82), y + int(rr * .88)],
                 a0, a1, fill=(250, 238, 220), outline=None)
    for k in (-0.30, 0.0, 0.30):
        p.oval(cx + s * r * 0.16, cy + r * k, r * 0.07, r * 0.11, INK, outline=None)


def face(p: Page, cx, cy, r, col, eye_dx=0.34, smile=True):
    p.circle(cx, cy, r, col)
    p.circle(cx - r * eye_dx, cy - r * 0.12, r * 0.085, INK, outline=None)
    p.circle(cx + r * eye_dx, cy - r * 0.12, r * 0.085, INK, outline=None)
    if smile:
        p.arcband(cx, cy + r * 0.10, r * 0.42, 20, 160, INK, w=0.005)


def bear(p: Page, cx, cy, r):
    p.circle(cx - r * 0.72, cy - r * 0.72, r * 0.30, FUR["bear"])
    p.circle(cx + r * 0.72, cy - r * 0.72, r * 0.30, FUR["bear"])
    face(p, cx, cy, r, FUR["bear"])
    p.oval(cx, cy + r * 0.34, r * 0.36, r * 0.26, (232, 220, 200))


def mouse(p: Page, cx, cy, r):
    p.circle(cx - r * 0.78, cy - r * 0.62, r * 0.44, FUR["mouse"])
    p.circle(cx + r * 0.78, cy - r * 0.62, r * 0.44, FUR["mouse"])
    face(p, cx, cy, r, FUR["mouse"])
    p.line([(cx + r * 0.9, cy + r * 0.7), (cx + r * 1.7, cy + r * 0.4),
            (cx + r * 1.9, cy + r * 1.0)], INK, w=0.005)


def rabbit(p: Page, cx, cy, r):
    for s in (-1, 1):
        p.oval(cx + s * r * 0.38, cy - r * 1.35, r * 0.20, r * 0.62, FUR["rabbit"])
    face(p, cx, cy, r, FUR["rabbit"])


def fox(p: Page, cx, cy, r):
    for s in (-1, 1):
        p.poly([(cx + s * r * 0.34, cy - r * 0.72), (cx + s * r * 1.02, cy - r * 1.28),
                (cx + s * r * 0.96, cy - r * 0.44)], FUR["fox"])
    p.oval(cx - r * 1.30, cy + r * 0.62, r * 0.62, r * 0.34, FUR["fox"])
    face(p, cx, cy, r, FUR["fox"])
    p.oval(cx, cy + r * 0.40, r * 0.24, r * 0.18, (250, 244, 232))


def squirrel(p: Page, cx, cy, r):
    p.oval(cx + r * 1.15, cy - r * 0.30, r * 0.46, r * 0.86, FUR["squirrel"])
    for s in (-1, 1):
        p.oval(cx + s * r * 0.62, cy - r * 0.86, r * 0.24, r * 0.30, FUR["squirrel"])
    face(p, cx, cy, r, FUR["squirrel"])


def bird(p: Page, cx, cy, r):
    p.oval(cx, cy, r, r * 0.86, FUR["bird"])
    p.poly([(cx + r * 0.80, cy), (cx + r * 1.34, cy + r * 0.10),
            (cx + r * 0.80, cy + r * 0.24)], (226, 150, 82))
    p.circle(cx + r * 0.34, cy - r * 0.24, r * 0.10, INK, outline=None)
    p.oval(cx - r * 0.12, cy + r * 0.10, r * 0.38, r * 0.24, (124, 168, 198))


ANIMALS = {"bear": bear, "mouse": mouse, "rabbit": rabbit,
           "fox": fox, "squirrel": squirrel, "bird": bird}


def stand(p: Page, kind, cx, ground_y, r, arms=None):
    """足を ground_y に接地させて全身で立たせる。

    arms: [(x, y), ...] 手先の座標。指定すると胴から腕を伸ばして描く。
    戻り値は頭の中心座標。
    """
    col = FUR[kind]
    torso_cy = ground_y - r * 0.95
    head_cy = ground_y - r * 2.45
    # 足
    for s in (-1, 1):
        p.oval(cx + s * r * 0.44, ground_y - r * 0.10, r * 0.30, r * 0.17, col)
    # 腕（胴より先に描いて肩に隠す）
    for hx, hy in (arms or []):
        p.line([(cx + (r * 0.55 if hx > cx else -r * 0.55), torso_cy - r * 0.25),
                (hx, hy)], INK, w=0.010)
    # 胴
    p.oval(cx, torso_cy, r * 0.80, r * 1.00, col)
    ANIMALS[kind](p, cx, head_cy, r)
    return cx, head_cy


def ground(p: Page, y=0.80, col=LEAF):
    p.d.rectangle([0, p.px(y), p.n, p.n], fill=col)
    p.d.line([(0, p.px(y)), (p.n, p.px(y))], fill=INK, width=p.lw(0.005))


def simple_tree(p: Page, cx, base_y, h, apples=0):
    trunk_w = h * 0.11
    p.d.rectangle([p.px(cx - trunk_w / 2), p.px(base_y - h * 0.55),
                   p.px(cx + trunk_w / 2), p.px(base_y)],
                  fill=SOIL, outline=INK, width=p.lw(0.005))
    p.circle(cx, base_y - h * 0.72, h * 0.34, LEAF)
    for i in range(apples):
        a = 2 * math.pi * i / max(1, apples)
        apple(p, cx + math.cos(a) * h * 0.22, base_y - h * 0.72 + math.sin(a) * h * 0.20,
              h * 0.045, stem=False)


# --- ページ -------------------------------------------------------------------

def forest_bg():
    """p3 と p33 が共有する背景。円環はこれが一致することで成立する。"""
    p = Page()
    p.d.rectangle([0, 0, p.n, p.px(0.80)], fill=SKY)
    ground(p)
    simple_tree(p, 0.24, 0.80, 0.46)
    simple_tree(p, 0.80, 0.80, 0.34)
    return p


def page_03():
    """もりに、りんごが ひとつ。（p33と同じ画角）"""
    p = forest_bg()
    apple(p, 0.50, 0.762, 0.034)
    stand(p, "bear", 0.885, 0.800, 0.030)   # 遠くに小さく
    return p, "p03_もりにりんごがひとつ"


def page_06():
    """コロは いいました。「はんぶん、こ！」"""
    p = Page()
    p.d.rectangle([0, 0, p.n, p.px(0.86)], fill=SKY)
    ground(p, 0.86)
    stand(p, "bear", 0.50, 0.86, 0.115, arms=[(0.245, 0.455), (0.755, 0.455)])
    half_apple(p, 0.215, 0.455, 0.070, flip=True)
    half_apple(p, 0.785, 0.455, 0.070, flip=False)
    for dx, dy in ((-0.10, 0.33), (0.10, 0.32), (0.0, 0.28), (-0.17, 0.38), (0.17, 0.37)):
        p.circle(0.50 + dx, dy, 0.007, APPLE_D, outline=None)
    return p, "p06_はんぶんこ1"


def page_21():
    """しゃく。ろくにんに なった。"""
    p = Page()
    p.d.rectangle([0, 0, p.n, p.px(0.78)], fill=SKY)
    ground(p, 0.78)
    order = ["bear", "mouse", "rabbit", "fox", "squirrel", "bird"]
    sizes = [0.088, 0.052, 0.070, 0.076, 0.064, 0.042]
    xs = [0.13, 0.28, 0.42, 0.58, 0.735, 0.88]
    for name, r, x in zip(order, sizes, xs):
        ANIMALS[name](p, x, 0.62 - r * 0.2, r)
        apple(p, x, 0.62 + r * 1.25, 0.011, stem=False)
    return p, "p21_ろくにんになった"


def page_30():
    """りんごが、いっぱい。（真下から見上げた大樹）"""
    p = Page()
    p.d.rectangle([0, 0, p.n, p.n], fill=SKY)
    p.d.rectangle([p.px(0.44), p.px(0.62), p.px(0.56), p.n], fill=SOIL,
                  outline=INK, width=p.lw(0.005))
    for cx, cy, r in ((0.50, 0.34, 0.34), (0.20, 0.42, 0.20), (0.80, 0.42, 0.20),
                      (0.33, 0.18, 0.17), (0.68, 0.18, 0.17), (0.50, 0.62, 0.14)):
        p.circle(cx, cy, r, LEAF)
    for cx, cy, r in ((0.20, 0.42, 0.20), (0.80, 0.42, 0.20), (0.50, 0.34, 0.34)):
        p.circle(cx - r * .3, cy + r * .3, r * 0.55, LEAF_D, outline=None)
    spots = [(0.50, 0.16), (0.36, 0.30), (0.63, 0.29), (0.50, 0.44), (0.24, 0.48),
             (0.76, 0.47), (0.40, 0.53), (0.60, 0.55), (0.16, 0.36), (0.84, 0.35),
             (0.30, 0.14), (0.70, 0.13), (0.50, 0.58), (0.28, 0.60), (0.72, 0.60)]
    for cx, cy in spots:
        apple(p, cx, cy, 0.040, stem=False)
    return p, "p30_りんごがいっぱい"


def page_33():
    """さあ、「はんぶん、こ！」（p3と同じ画角にコロを足す）"""
    p = forest_bg()                       # p3 とまったく同じ背景
    stand(p, "bear", 0.46, 0.800, 0.105, arms=[(0.665, 0.610)])
    apple(p, 0.700, 0.605, 0.048)         # 読者に差し出している
    return p, "p33_さあはんぶんこ"


PAGES = {
    "3": page_03, "6": page_06, "21": page_21, "30": page_30, "33": page_33,
}
SAMPLE = ["3", "6", "21", "30", "33"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="build/rough")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--pages", nargs="*", help="ページ番号を指定")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    keys = args.pages or (sorted(PAGES, key=int) if args.all else SAMPLE)

    for k in keys:
        if k not in PAGES:
            print(f"  ページ {k} は未定義（定義済み: {', '.join(sorted(PAGES, key=int))}）")
            continue
        p, name = PAGES[k]()
        path = os.path.join(args.out, name + ".png")
        p.save(path)
        print(f"  {path}")


if __name__ == "__main__":
    main()

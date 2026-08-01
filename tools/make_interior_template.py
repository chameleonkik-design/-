#!/usr/bin/env python3
"""『へったのに、ふえた』本文テンプレートPDFを生成する。

KDPペーパーバック(8.5x8.5in / 裁ち落としあり / 36ページ)の
正しい寸法・ノド位置・セーフエリアを持つ下敷きを出力します。

イラストが出来る前に、この PDF をそのまま KDP のプレビューアに通すことで
「ページ数」「綴じ方向」「マージン違反」を先に潰せます。

    python3 tools/make_interior_template.py            # ガイド入り(制作用)
    python3 tools/make_interior_template.py --clean    # ガイドなし(入稿試験用)

裁ち落としは天・地・小口の3辺のみに付き、ノド(綴じ側)には付きません。
そのため仕上がり範囲の左右位置は奇数/偶数ページで反転します。
"""

from __future__ import annotations

import argparse
import sys

from reportlab.lib.colors import Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

# --- 寸法 (すべて pt, 1in = 72pt) ------------------------------------------
INCH = 72.0
MM = INCH / 25.4

TRIM = 8.5 * INCH          # 仕上がり 8.5in 角 = 612pt
BLEED = 0.125 * INCH       # 裁ち落とし 3.2mm = 9pt

PAGE_W = TRIM + BLEED      # 621pt : 小口側の1辺だけ
PAGE_H = TRIM + BLEED * 2  # 630pt : 天地の2辺

SAFE_OUTER = 15 * MM       # 天地・小口から文字を離す距離
SAFE_GUTTER = 20 * MM      # ノドから文字を離す距離

CREAM = HexColor("#F7F1E3")
INK = HexColor("#3A3226")
GUIDE_TRIM = Color(0.85, 0.25, 0.20, alpha=0.55)
GUIDE_SAFE = Color(0.20, 0.45, 0.75, alpha=0.55)
GUIDE_NOTE = Color(0.45, 0.42, 0.36, alpha=0.9)

FONT = "HeiseiKakuGo-W5"   # reportlab 同梱の日本語CIDフォント

# --- 本文 -------------------------------------------------------------------
# (ページ番号, 役割, 本文) — 本文の改行は \n。manuscript/本文原稿.md と対応。
PAGES: list[tuple[int, str, str]] = [
    (1,  "中扉",       "へったのに、ふえた"),
    (2,  "献辞",       "わけてくれた\nぜんぶの ひとへ"),
    (3,  "本編",       "もりに、\nりんごが ひとつ。"),
    (4,  "本編",       "くまの コロの\nりんご。"),
    (5,  "本編",       "「いいなあ」\n\nねずみの チッチ。"),
    (6,  "本編",       "コロは いいました。\n\n「はんぶん、こ！」"),
    (7,  "本編",       "しゃく、しゃく。\n\nふたりに なった。"),
    (8,  "本編",       "「いいなあ」\n\nうさぎの ミミ。"),
    (9,  "本編",       "チッチは いいました。\n\n「はんぶん、こ！」"),
    (10, "本編",       "しゃく、しゃく。\n\nさんにんに なった。"),
    (11, "本編",       "「いいなあ」\n\nきつねの コン。"),
    (12, "本編",       "ミミは いいました。\n\n「はんぶん、こ！」"),
    (13, "本編",       "しゃく、しゃく。\n\nよにんに なった。"),
    (14, "本編",       "「いいなあ」\n\nりすの クル。"),
    (15, "本編",       "コンは いいました。\n\n「はんぶん、こ！」"),
    (16, "本編",       "しゃく、しゃく。\n\nごにんに なった。"),
    (17, "本編",       "「いいなあ」\n\nことりの ピピ。"),
    (18, "本編",       "クルの りんごは、\nもう こんなに ちいさい。"),
    (19, "本編★ため",  "それでも、\nクルは いいました。"),
    (20, "本編★山",    "「はんぶん、こ！」"),
    (21, "本編",       "しゃく。\n\nろくにんに なった。"),
    (22, "本編",       "りんごは、\nもう ない。"),
    (23, "本編",       "ぽとん。\n\nたねが ひとつ。"),
    (24, "本編",       "みんなで\nつちを かけた。"),
    (25, "本編★ため",  "まった。\n\nなにも おきない。"),
    (26, "本編",       "ざあざあ。\nぐうぐう。\n\nつちの なかは、ないしょ。"),
    (27, "本編",       "ぴょこん。"),
    (28, "本編",       "はるが きて、\nなつが きて、"),
    (29, "本編★ため",  "あきが きて、\nふゆが きて。"),
    (30, "本編★山",    "りんごが、いっぱい。"),
    (31, "本編",       "ひとつが、\nいっぱいに なった。"),
    (32, "本編",       "コロは、りんごを\nひとつ もって。"),
    (33, "本編★環",    "さあ、\n\n「はんぶん、こ！」"),
    (34, "おうちのかたへ", "（おうちのかたへ／本文は原稿参照）"),
    (35, "奥付",       "（著者紹介・奥付）"),
    (36, "白",         ""),
]

TOTAL_PAGES = 36


def trim_origin_x(page_no: int) -> float:
    """仕上がり範囲の左端X。

    左開きなので 奇数=右ページ / 偶数=左ページ。
    裁ち落としは小口(外側)にだけ付くので、仕上がり範囲は綴じ側へ寄る。
    """
    if page_no % 2 == 1:          # 右ページ: ノドが左 → 仕上がりは左寄せ
        return 0.0
    return BLEED                   # 左ページ: ノドが右 → 仕上がりは右寄せ


def gutter_is_left(page_no: int) -> bool:
    """ノド(綴じ側)が左端にあるか。奇数=右ページはノドが左。"""
    return page_no % 2 == 1


def draw_guides(c: canvas.Canvas, page_no: int) -> None:
    tx = trim_origin_x(page_no)
    ty = BLEED

    # 仕上がり線
    c.setStrokeColor(GUIDE_TRIM)
    c.setLineWidth(0.7)
    c.rect(tx, ty, TRIM, TRIM, stroke=1, fill=0)

    # 文字セーフエリア (ノドだけ広くとる)
    left_pad = SAFE_GUTTER if gutter_is_left(page_no) else SAFE_OUTER
    right_pad = SAFE_OUTER if gutter_is_left(page_no) else SAFE_GUTTER
    c.setStrokeColor(GUIDE_SAFE)
    c.setDash(3, 3)
    c.rect(
        tx + left_pad,
        ty + SAFE_OUTER,
        TRIM - left_pad - right_pad,
        TRIM - SAFE_OUTER * 2,
        stroke=1,
        fill=0,
    )
    c.setDash()

    # 注記
    side = "右ページ／ノド=左" if gutter_is_left(page_no) else "左ページ／ノド=右"
    c.setFillColor(GUIDE_NOTE)
    c.setFont(FONT, 7)
    c.drawString(tx + 6, ty + 6, f"p{page_no}  {side}  赤=仕上がり  青破線=文字セーフ")


def draw_text_block(c: canvas.Canvas, page_no: int, role: str, body: str) -> None:
    if not body:
        return
    tx = trim_origin_x(page_no)
    ty = BLEED
    left_pad = SAFE_GUTTER if gutter_is_left(page_no) else SAFE_OUTER
    right_pad = SAFE_OUTER if gutter_is_left(page_no) else SAFE_GUTTER
    box_w = TRIM - left_pad - right_pad

    size = 30 if "★山" in role else 22
    leading = size * 1.7
    lines = body.split("\n")

    # セーフエリアの上寄せ (作画指示書の既定の文字位置)
    y = ty + TRIM - SAFE_OUTER - size
    c.setFillColor(INK)
    c.setFont(FONT, size)
    for line in lines:
        if line:
            c.drawCentredString(tx + left_pad + box_w / 2, y, line)
        y -= leading


def build(path: str, clean: bool) -> None:
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    c.setTitle("へったのに、ふえた 本文テンプレート")

    for page_no, role, body in PAGES:
        # 全面ベタ (裁ち落としまで塗る = 実際の絵の入る領域)
        c.setFillColor(CREAM)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

        draw_text_block(c, page_no, role, body)
        if not clean:
            draw_guides(c, page_no)

        c.showPage()

    c.save()

    print(f"生成: {path}")
    print(f"  ページ数        : {len(PAGES)} (KDP最小24 → {'OK' if len(PAGES) >= 24 else 'NG'})")
    print(f"  PDFページサイズ : {PAGE_W:.0f} x {PAGE_H:.0f} pt "
          f"({PAGE_W / INCH:.3f} x {PAGE_H / INCH:.3f} in)")
    print(f"  仕上がり        : {TRIM / INCH:.1f} x {TRIM / INCH:.1f} in")
    print(f"  裁ち落とし      : {BLEED / MM:.1f} mm (天地=2辺, 小口=1辺, ノド=なし)")
    print(f"  300dpi換算      : {round(PAGE_W / INCH * 300)} x {round(PAGE_H / INCH * 300)} px")
    print(f"  文字セーフ      : 天地小口 {SAFE_OUTER / MM:.0f}mm / ノド {SAFE_GUTTER / MM:.0f}mm")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--out", default="build/interior_template.pdf")
    ap.add_argument("--clean", action="store_true", help="ガイド線を描かない")
    args = ap.parse_args(argv)

    if len(PAGES) != TOTAL_PAGES:
        print(f"ページ定義が{len(PAGES)}件です（{TOTAL_PAGES}件であるべき）", file=sys.stderr)
        return 1

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    build(args.out, args.clean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

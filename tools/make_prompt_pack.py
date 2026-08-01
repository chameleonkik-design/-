#!/usr/bin/env python3
"""画像生成ツールにそのまま貼れるプロンプト集を生成する。

プロンプトの定義はこのファイルが唯一の出典。ここから
  manuscript/プロンプト集.md   （リポジトリで読む用）
  site/prompts.html            （コピーボタン付きの作業用ページ）
の2つを書き出すので、両者がずれることがない。

    python3 tools/make_prompt_pack.py
"""

from __future__ import annotations

import html
import json
import os

# --- 全プロンプトに付ける共通の接尾辞 -----------------------------------------
STYLE = (
    "children's picture book illustration, watercolor and colored pencil, "
    "visible paper texture, thick hand-drawn outlines, flat simple shading, "
    "limited palette (cream #F7F1E3, apple red #D94F45, leaf green #6BA368, "
    "warm brown #8B6F52, sky blue #A8CBE0, dark ink #3A3226), "
    "dot eyes with no whites, generous negative space, square 1:1 composition, "
    "no text, no lettering, no watermark"
)

CAST = """Koro: a round brown bear cub, big and soft, small round ears
Chicchi: a tiny grey mouse, round ears, long thin tail
Mimi: a white rabbit with two long upright ears
Kon: an orange fox, pointed nose, thick bushy tail
Kuru: a reddish-brown squirrel with a big fluffy tail
Pipi: a very small blue bird with a tiny orange beak"""

# (id, 見出し, 日本語の狙い, 素のプロンプト)
ITEMS: list[tuple[str, str, str, str]] = [
    ("cast", "キャラクターシート", "最初に作る。以降の全ページの参照画像になる。",
     "A character reference sheet on a plain cream background, six small forest "
     "animals each drawn three times (front view, side view, back view), evenly "
     "spaced in three rows: a round brown bear cub with small round ears; a tiny "
     "grey mouse with round ears and a long thin tail; a white rabbit with two "
     "long upright ears; an orange fox with a pointed nose and thick bushy tail; "
     "a reddish-brown squirrel with a big fluffy tail; a very small blue bird "
     "with a tiny orange beak"),

    ("p1", "p1 中扉", "タイトルを載せる余白を上部に大きく残す。",
     "A single red apple resting alone on an empty cream background, tiny soft "
     "shadow beneath it, large empty space above"),
    ("p2", "p2 献辞", "ほぼ余白。",
     "A single apple leaf lying in the lower right corner of an otherwise "
     "completely empty cream page"),
    ("p3", "p3 もりに、りんごが ひとつ。", "★2番目に作る。この背景を以降で使い回す。p33と同一画角。",
     "A wide calm forest scene, two or three simple trees, one red apple lying "
     "on the grass under a tree, a small brown bear cub far away in the "
     "distance, gentle morning light, large empty sky at the top"),
    ("p4", "p4 くまの コロの りんご。", "まだかじっていない。",
     "A round brown bear cub holding one whole red apple with both paws close to "
     "his face, happy closed-eye smile, simple forest background, plain open "
     "area on the right"),
    ("p5", "p5 「いいなあ」ねずみの チッチ。", "以降 p8/p11/p14/p17 も同じ構図で反復する。",
     "A tiny grey mouse peeking out from tall grass at the bottom corner of the "
     "frame, looking up longingly at something outside the frame, big empty "
     "space above"),
    ("p6", "p6 「はんぶん、こ！」①", "表紙もこの構図を使う。",
     "A brown bear cub breaking a red apple into two halves with both paws, arms "
     "spread wide, tiny juice droplets in the air, joyful open mouth, cream "
     "background, plain area at the bottom"),
    ("p7", "p7 しゃく、しゃく。ふたりに なった。", "2人。りんごは1/2。",
     "A brown bear cub and a tiny grey mouse sitting side by side, each biting "
     "into half of a red apple, cheerful, simple grass ground line, empty sky "
     "above"),
    ("p8", "p8 「いいなあ」うさぎの ミミ。", "p5と同じ構図。動物だけ替える。",
     "A white rabbit with two long upright ears peeking out from tall grass at "
     "the bottom corner of the frame, looking up longingly at something outside "
     "the frame, big empty space above"),
    ("p9", "p9 「はんぶん、こ！」②", "1/2 を 1/4 ×2 に。",
     "A tiny grey mouse splitting a half of a red apple into two quarters with "
     "both paws, arms spread wide, tiny juice droplets, joyful, cream background"),
    ("p10", "p10 さんにんに なった。", "3人。りんごは1/4。",
     "A brown bear cub, a tiny grey mouse and a white rabbit sitting side by "
     "side in a row, each nibbling a quarter piece of red apple, cheerful, "
     "simple grass ground line, empty sky above"),
    ("p11", "p11 「いいなあ」きつねの コン。", "p5と同じ構図。",
     "An orange fox with a pointed nose and thick bushy tail peeking out from "
     "tall grass at the bottom corner of the frame, looking up longingly at "
     "something outside the frame, big empty space above"),
    ("p12", "p12 「はんぶん、こ！」③", "1/4 を 1/8 ×2 に。",
     "A white rabbit splitting a quarter piece of red apple into two smaller "
     "pieces with both paws, arms spread wide, joyful, cream background"),
    ("p13", "p13 よにんに なった。", "4人。りんごは1/8。",
     "A brown bear cub, a tiny grey mouse, a white rabbit and an orange fox "
     "sitting side by side in a row, each nibbling a small piece of red apple, "
     "cheerful, simple grass ground line, empty sky above"),
    ("p14", "p14 「いいなあ」りすの クル。", "p5と同じ構図。",
     "A reddish-brown squirrel with a big fluffy tail peeking out from tall "
     "grass at the bottom corner of the frame, looking up longingly at something "
     "outside the frame, big empty space above"),
    ("p15", "p15 「はんぶん、こ！」④", "1/8 を 1/16 ×2 に。",
     "An orange fox splitting a small piece of red apple into two even smaller "
     "pieces with both paws, arms spread wide, joyful, cream background"),
    ("p16", "p16 ごにんに なった。", "5人。りんごは1/16。",
     "Five small forest animals — a brown bear cub, a grey mouse, a white "
     "rabbit, an orange fox and a reddish squirrel — sitting side by side in a "
     "row, each nibbling a very small piece of red apple, empty sky above"),
    ("p17", "p17 「いいなあ」ことりの ピピ。", "ここまでで最も小さく描く。",
     "A very small blue bird with a tiny orange beak perched on a low twig, "
     "looking down longingly, mostly empty cream background"),
    ("p18", "p18 もう こんなに ちいさい。", "小ささが主役。",
     "Close-up of a squirrel's two open paws holding one extremely tiny sliver "
     "of red apple, the smallness is the subject of the image, softly blurred "
     "background, huge empty space above"),
    ("p19", "p19 それでも、クルは いいました。", "★ため。静かなページ。",
     "Portrait of a reddish-brown squirrel looking straight ahead with a calm, "
     "resolute expression, plain cream background, quiet and still"),
    ("p20", "p20 「はんぶん、こ！」⑤", "★本作でいちばん明るい1枚。",
     "A reddish-brown squirrel splitting a minuscule piece of apple with both "
     "paws, arms wide open, warm light rays radiating outward, small floating "
     "light specks and petals, the most joyful and radiant image in the book, "
     "cream background"),
    ("p21", "p21 ろくにんに なった。", "6人勢揃い。りんごは1/32。",
     "Six small forest animals — a brown bear cub, a grey mouse, a white rabbit, "
     "an orange fox, a reddish squirrel and a tiny blue bird — sitting in a row, "
     "each nibbling a very tiny piece of apple, warm and content, empty sky above"),
    ("p22", "p22 りんごは、もう ない。", "さみしさではなく、静けさ。",
     "An empty patch of grass and soil with no apple anywhere, only the feet of "
     "small animals visible at the edges of the frame, quiet and still, soft "
     "light, large empty space"),
    ("p23", "p23 ぽとん。たねが ひとつ。", "★いちばん小さい者が種を持つ。",
     "A tiny blue bird looking down, one small dark apple seed falling through "
     "the air just below its beak, caught mid-fall before touching the ground, "
     "cream background, soft shadow on the soil below"),
    ("p24", "p24 みんなで つちを かけた。", "上から見下ろす構図。",
     "Six small forest animals gathered in a circle seen from slightly above, "
     "patting soil over a spot in the ground with their paws, working together "
     "gently, warm light"),
    ("p25", "p25 まった。なにも おきない。", "★意図的に退屈に描く。",
     "A bare patch of brown soil in the center of a wide quiet field, six small "
     "animals sitting some distance away simply waiting, nothing happening, "
     "mostly empty sky, deliberately uneventful and still"),
    ("p26", "p26 つちの なかは、ないしょ。", "★読者だけが見られる断面。",
     "Cross-section view of the ground: above, a rainy night sky with six small "
     "animals sleeping curled up together; below, underground, a seed with white "
     "roots spreading through dark brown soil, secret and warm, painterly "
     "cutaway diagram"),
    ("p27", "p27 ぴょこん。", "動物の反応は描かない。",
     "One tiny green sprout with two leaves just emerging from brown soil, "
     "morning light, close-up, huge empty space around it, cream background"),
    ("p28", "p28 はるが きて、なつが きて、", "1枚の中で左から右へ育つ。",
     "The same young apple tree shown twice across one square frame: on the left "
     "in spring with pale pink blossoms, on the right in summer with deep green "
     "leaves, the tree grows taller from left to right, one seamless scene"),
    ("p29", "p29 あきが きて、ふゆが きて。", "★冬で終わるので少しさびしい。",
     "The same apple tree shown twice across one square frame: on the left in "
     "autumn with red-orange leaves, on the right in winter with bare branches "
     "and snow, the tree is much larger now, quiet and cold, one seamless scene"),
    ("p30", "p30 りんごが、いっぱい。", "★クライマックス。最も密度の高い1枚。",
     "Looking straight up at a huge apple tree from below, branches completely "
     "full of red apples, dense green leaves, sunlight breaking through, "
     "overwhelming abundance, the richest and most detailed image in the book"),
    ("p31", "p31 ひとつが、いっぱいに なった。", "p30と対になる引きの構図。",
     "Wide view of six small forest animals standing under a giant apple tree, "
     "arms full of red apples, more apples scattered on the grass around them, "
     "joyful, warm afternoon light"),
    ("p32", "p32 コロは、りんごを ひとつ もって。", "隅にまだ名前のない小さな動物。",
     "A brown bear cub seen from behind, walking while carrying one single red "
     "apple, a small unnamed young animal standing alone at the edge of the "
     "frame, soft evening light, gentle and quiet"),
    ("p33", "p33 さあ、「はんぶん、こ！」", "★p3を入力にした img2img で作る。円環の要。",
     "The exact same forest scene and camera angle as the opening image, same "
     "trees and same light, but now a brown bear cub stands in the center "
     "turning toward the viewer, holding out one red apple directly to the "
     "camera, warm inviting smile, large empty sky at the top"),

    ("cover1", "表紙（表1）", "上部にタイトルの余白を大きく。サムネイルで判別できるか要確認。",
     "Book cover illustration: a round brown bear cub facing the viewer, "
     "breaking one red apple into two halves with both paws, arms spread wide, "
     "big joyful smile, tiny juice droplets, warm cream background with soft "
     "forest shapes, large clear empty space at the top for a title"),
    ("cover4", "裏表紙（表4）", "右下にバーコード用の白地を空ける。",
     "Six small forest animals sitting in a row nibbling tiny pieces of apple, "
     "placed small in the upper half of a mostly empty cream page, plenty of "
     "blank space below"),
]

WORKFLOW = [
    ("キャラクターシートを作る",
     "6匹の造形をここで確定させる。以降すべてのページで参照画像として渡す。"),
    ("p3 の背景を完成させる",
     "以降の森はこの1枚から切り出して使い回す。ここで画角と光を決める。"),
    ("p33 を p3 の img2img で作る",
     "円環が成立するかを最初に検証する。ここが崩れると本の設計が崩れる。"),
    ("繰り返しブロック（p5〜p16）を一括生成",
     "同じシード・同じ構図で。構図を変えないことがこの絵本の設計。"),
    ("単独ページ（p17〜p33）を作り込む",
     "p20 と p30 に最も時間をかける。ここが本の山。"),
    ("表紙を最後に作る",
     "本文の色調が固まってから。サムネイル160px幅で判別できるか必ず縮小確認。"),
]

TOOLS = [
    ("Midjourney",
     "<code>--ar 1:1</code> を必ず付ける。キャラの一貫性は <code>--cref [シートのURL] --cw 100</code>、"
     "画風の一貫性は <code>--sref</code>。同じ構図を反復したいページは <code>--seed</code> を固定する。"),
    ("ChatGPT / GPT Image",
     "会話で直せるのが強み。キャラクターシートを最初にアップロードし、"
     "「このキャラで」と指定し続ける。修正指示が自然言語で通る。"),
    ("Google Gemini（Nano Banana 系）",
     "参照画像を渡したうえでの編集と一貫性維持が得意。p3→p33 の img2img はここが有利。"),
    ("Adobe Firefly",
     "学習データの都合で商用利用の条件が明快。KDPで売る前提なら安全側。"),
]

NOTES = [
    ("正方形で出す",
     "判型が 8.5×8.5in なので、1:1 以外で作ると後で切ることになり構図が壊れます。"),
    ("文字を絶対に入れさせない",
     "接尾辞の <code>no text, no lettering, no watermark</code> は消さないこと。"
     "生成AIは絵本の絵に読めない文字を描き込みます。"),
    ("上部に余白を残す",
     "本文の文字はページ上部に置く設計です。そこを絵で埋めると文字が乗りません。"),
    ("最終的に 2588 × 2625 px / CMYK",
     "正方形で作った絵を、裁ち落とし込みの非正方形キャンバスに配置します。"
     "生成時は大きめに出しておくこと。"),
    ("KDPでのAI申告",
     "生成AIを使った場合、入稿時の申告が必須です。あわせて使ったツールの"
     "商用利用条件も確認してください。"),
]


def full(raw: str) -> str:
    return raw + ", " + STYLE


def write_markdown(path: str) -> None:
    L: list[str] = []
    L.append("# プロンプト集『へったのに、ふえた』\n")
    L.append("画像生成ツールにそのまま貼れる完成形です。"
             "共通の画風指定は各プロンプトに連結済みなので、追記は不要です。\n")
    L.append("> このファイルは `tools/make_prompt_pack.py` が生成しています。"
             "直接編集せず、スクリプト側を直してください。\n")

    L.append("\n## 制作順序\n")
    for i, (t, d) in enumerate(WORKFLOW, 1):
        L.append(f"{i}. **{t}** — {d}")

    L.append("\n## ツール別のコツ\n")
    for name, tip in TOOLS:
        L.append(f"- **{name}** — {tip.replace('<code>', '`').replace('</code>', '`')}")

    L.append("\n## 必ず守ること\n")
    for name, tip in NOTES:
        L.append(f"- **{name}** — {tip.replace('<code>', '`').replace('</code>', '`')}")

    L.append("\n## 登場人物（参照用）\n")
    L.append("```\n" + CAST + "\n```\n")
    L.append("## 共通の画風指定（各プロンプトに連結済み）\n")
    L.append("```\n" + STYLE + "\n```\n")

    L.append("\n---\n\n## 各ページ\n")
    for _id, title, note, raw in ITEMS:
        L.append(f"### {title}\n")
        L.append(f"{note}\n")
        L.append("```\n" + full(raw) + "\n```\n")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"  {path}")


def write_html(path: str) -> None:
    data = [{"id": i, "title": t, "note": n, "prompt": full(r)} for i, t, n, r in ITEMS]
    payload = json.dumps(data, ensure_ascii=False)

    steps = "\n".join(
        f'<li><span class="st">{html.escape(t)}</span>'
        f'<span class="sd">{html.escape(d)}</span></li>'
        for t, d in WORKFLOW)
    tools = "\n".join(
        f'<div class="tool"><p class="tn">{html.escape(n)}</p><p class="tt">{tip}</p></div>'
        for n, tip in TOOLS)
    notes = "\n".join(
        f'<li><strong>{html.escape(n)}</strong>{tip}</li>' for n, tip in NOTES)

    doc = TEMPLATE.replace("__STEPS__", steps).replace("__TOOLS__", tools)
    doc = doc.replace("__NOTES__", notes)
    doc = doc.replace("__CAST__", html.escape(CAST))
    doc = doc.replace("__STYLE__", html.escape(STYLE))
    doc = doc.replace("__COUNT__", str(len(ITEMS)))
    doc = doc.replace("__DATA__", payload.replace("</", "<\\/"))

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"  {path}")


TEMPLATE = r"""<title>プロンプト集 — へったのに、ふえた</title>
<style>
:root{
  --ground:#D9D2C2; --panel:#EFE9DA; --field:#F7F1E3;
  --ink:#3A3226; --ink-soft:#6B6153; --muted:#857A69;
  --apple:#B93E37; --leaf:#4F8557; --rule:#C2B9A6; --shadow:rgba(58,50,38,.16);
  --gothic:"Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic Medium","Yu Gothic","Noto Sans JP","Meiryo",sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root{--ground:#17150F; --panel:#211E19; --field:#2A2620;
        --ink:#EDE5D3; --ink-soft:#C0B5A2; --muted:#948976;
        --apple:#E7796B; --leaf:#8CBB86; --rule:#3D372F; --shadow:rgba(0,0,0,.5);}
}
:root[data-theme="dark"]{--ground:#17150F; --panel:#211E19; --field:#2A2620;
  --ink:#EDE5D3; --ink-soft:#C0B5A2; --muted:#948976;
  --apple:#E7796B; --leaf:#8CBB86; --rule:#3D372F; --shadow:rgba(0,0,0,.5);}
:root[data-theme="light"]{--ground:#D9D2C2; --panel:#EFE9DA; --field:#F7F1E3;
  --ink:#3A3226; --ink-soft:#6B6153; --muted:#857A69;
  --apple:#B93E37; --leaf:#4F8557; --rule:#C2B9A6; --shadow:rgba(58,50,38,.16);}

*{box-sizing:border-box;}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:var(--gothic);line-height:1.8;-webkit-font-smoothing:antialiased;}
.wrap{max-width:900px;margin:0 auto;padding:0 20px;}
header{padding:64px 0 34px;}
.eyebrow{font-size:.7rem;letter-spacing:.2em;color:var(--muted);margin:0 0 16px;text-transform:uppercase;}
h1{font-size:clamp(1.7rem,4.6vw,2.5rem);letter-spacing:.02em;margin:0 0 12px;font-weight:700;text-wrap:balance;}
.lede{color:var(--ink-soft);margin:0;max-width:44em;font-size:.95rem;}
h2{font-size:1.05rem;letter-spacing:.06em;margin:0 0 6px;font-weight:700;}
.sub{font-size:.82rem;color:var(--muted);margin:0 0 22px;}
section{padding:34px 0;border-top:1px solid var(--rule);}

ol.steps{list-style:none;counter-reset:s;padding:0;margin:0;display:flex;flex-direction:column;gap:2px;}
ol.steps li{counter-increment:s;background:var(--panel);padding:14px 18px 14px 52px;position:relative;}
ol.steps li::before{content:counter(s);position:absolute;left:18px;top:14px;
  font-family:var(--mono);font-size:.78rem;color:var(--apple);font-weight:700;}
.st{display:block;font-size:.92rem;font-weight:700;}
.sd{display:block;font-size:.82rem;color:var(--ink-soft);line-height:1.7;}

.tools{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);}
.tool{background:var(--panel);padding:18px;}
.tn{margin:0 0 6px;font-size:.86rem;font-weight:700;}
.tt{margin:0;font-size:.8rem;color:var(--ink-soft);line-height:1.75;}

ul.notes{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:12px;}
ul.notes li{font-size:.85rem;color:var(--ink-soft);line-height:1.75;
  border-left:3px solid var(--apple);padding-left:16px;}
ul.notes strong{display:block;color:var(--ink);font-size:.88rem;}

.block{background:var(--field);border:1px solid var(--rule);padding:16px 18px;position:relative;}
pre{margin:0;font-family:var(--mono);font-size:.76rem;line-height:1.75;
  white-space:pre-wrap;word-break:break-word;color:var(--ink);}

.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 20px;}
.count{font-family:var(--mono);font-size:.75rem;color:var(--muted);}
button{font-family:var(--gothic);font-size:.75rem;letter-spacing:.06em;
  background:var(--apple);color:#fff;border:0;padding:7px 14px;border-radius:2px;cursor:pointer;}
button.ghost{background:transparent;color:var(--ink-soft);border:1px solid var(--rule);}
button:hover{filter:brightness(1.08);}
button:focus-visible{outline:2px solid var(--leaf);outline-offset:2px;}
button.done{background:var(--leaf);}

.card{background:var(--panel);border:1px solid var(--rule);margin-bottom:2px;}
.card .hd{display:flex;gap:12px;align-items:baseline;justify-content:space-between;
  padding:14px 18px 0;flex-wrap:wrap;}
.card h3{margin:0;font-size:.92rem;font-weight:700;letter-spacing:.02em;}
.card .nt{margin:2px 18px 12px;font-size:.78rem;color:var(--muted);line-height:1.7;}
.card .body{padding:0 18px 16px;}
.card pre{background:var(--field);border:1px solid var(--rule);padding:13px 15px;}
.star h3{color:var(--apple);}
footer{padding:44px 0 80px;border-top:1px solid var(--rule);font-size:.8rem;color:var(--muted);}
a{color:var(--apple);text-underline-offset:3px;}
@media (prefers-reduced-motion:reduce){*{transition:none!important;}}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">へったのに、ふえた ／ 作画用</p>
  <h1>プロンプト集</h1>
  <p class="lede">画像生成ツールにそのまま貼れる完成形です。共通の画風指定は各プロンプトに連結済みなので、追記は不要です。全__COUNT__点。</p>
</header>

<section>
  <h2>制作順序</h2>
  <p class="sub">この順で作るとキャラクターの造形が崩れにくくなります。</p>
  <ol class="steps">__STEPS__</ol>
</section>

<section>
  <h2>ツール別のコツ</h2>
  <p class="sub">どれを使う場合も、キャラクターシートを参照画像として渡し続けるのが前提です。</p>
  <div class="tools">__TOOLS__</div>
</section>

<section>
  <h2>必ず守ること</h2>
  <ul class="notes">__NOTES__</ul>
</section>

<section>
  <h2>登場人物（参照用）</h2>
  <p class="sub">キャラクターシートが崩れたとき、この定義を貼り直してください。</p>
  <div class="block"><pre id="cast">__CAST__</pre></div>
  <div class="toolbar" style="margin-top:12px;"><button data-copy="cast">コピー</button></div>

  <h2 style="margin-top:30px;">共通の画風指定</h2>
  <p class="sub">下の各プロンプトには連結済みです。単体で使いたいとき用。</p>
  <div class="block"><pre id="style">__STYLE__</pre></div>
  <div class="toolbar" style="margin-top:12px;"><button data-copy="style">コピー</button></div>
</section>

<section>
  <h2>各ページ</h2>
  <p class="sub">★は特に作り込むページです。</p>
  <div class="toolbar">
    <button id="copyall">全部まとめてコピー</button>
    <span class="count" id="count"></span>
  </div>
  <div id="list"></div>
</section>

<footer>
  出典は <code>tools/make_prompt_pack.py</code>。このページと <code>manuscript/プロンプト集.md</code> は同じ定義から生成しています。<br>
  生成AIを使った場合、KDPへの申告が必須です。
</footer>
</div>

<script>
const ITEMS = __DATA__;

function flash(btn, label){
  const old = btn.textContent;
  btn.textContent = label; btn.classList.add("done");
  setTimeout(function(){ btn.textContent = old; btn.classList.remove("done"); }, 1400);
}
async function copy(text, btn){
  try{
    await navigator.clipboard.writeText(text);
    flash(btn, "コピーしました");
  }catch(e){
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    try{ document.execCommand("copy"); flash(btn, "コピーしました"); }
    catch(e2){ flash(btn, "コピーできません"); }
    document.body.removeChild(ta);
  }
}

document.querySelectorAll("button[data-copy]").forEach(function(b){
  b.addEventListener("click", function(){
    copy(document.getElementById(b.dataset.copy).textContent, b);
  });
});

const list = document.getElementById("list");
ITEMS.forEach(function(it){
  const card = document.createElement("div");
  card.className = "card" + (it.note.indexOf("★") >= 0 ? " star" : "");

  const hd = document.createElement("div"); hd.className = "hd";
  const h3 = document.createElement("h3"); h3.textContent = it.title;
  const btn = document.createElement("button"); btn.textContent = "コピー";
  btn.addEventListener("click", function(){ copy(it.prompt, btn); });
  hd.appendChild(h3); hd.appendChild(btn);

  const nt = document.createElement("p"); nt.className = "nt"; nt.textContent = it.note;
  const body = document.createElement("div"); body.className = "body";
  const pre = document.createElement("pre"); pre.textContent = it.prompt;
  body.appendChild(pre);

  card.appendChild(hd); card.appendChild(nt); card.appendChild(body);
  list.appendChild(card);
});

document.getElementById("count").textContent = ITEMS.length + " 点";
document.getElementById("copyall").addEventListener("click", function(){
  const all = ITEMS.map(function(i){ return "## " + i.title + "\n" + i.prompt; }).join("\n\n");
  copy(all, this);
});
</script>
"""


def main() -> None:
    print("生成:")
    write_markdown("manuscript/プロンプト集.md")
    write_html("site/prompts.html")
    print(f"  （{len(ITEMS)} 点）")


if __name__ == "__main__":
    main()

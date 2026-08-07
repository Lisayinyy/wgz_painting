#!/usr/bin/env python3
"""Build a 2x2 grid of (original|ink) pairs, mimicking a Wu Guanzhong before/after plate.

Each pair is laid out like image 5: original on the left, ink on the right, equal height,
labels below ("原图" / "水墨"), centred under their half.

Usage:
  python3 make_pair_plate.py -o out.jpg \
    --pair source1.jpg ink1.png:晨雾村落 \
    --pair source2.jpg ink2.png:临河船家 \
    --pair source3.jpg ink3.png:石桥远山 \
    --pair source4.jpg ink4.png:春桥樱花 \
    --title "乌镇 / 周庄 / 同里 · 吴冠中笔下的江南" \
    --subtitle "四幅实拍 · 同一种水墨语言 · 江南水乡路"

Requires Pillow.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PAPER = (247, 244, 236)
INK = (46, 44, 40)
GREY = (135, 130, 122)
RULE = (216, 211, 201)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]


def resolve_font(explicit):
    for path in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if path and os.path.exists(path):
            return path
    sys.exit("No CJK font found. Pass one with --font.")


def parse_pair(spec):
    parts = spec.split(":")
    if len(parts) < 3:
        sys.exit(f"Pair spec must be ORIG:INK:TITLE  (got {spec})")
    orig, ink, title = parts[0], parts[1], parts[2]
    if not os.path.isfile(orig):
        sys.exit(f"Original image not found: {orig}")
    if not os.path.isfile(ink):
        sys.exit(f"Ink image not found: {ink}")
    return orig, ink, title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", action="append", required=True,
                    help="ORIG:INK:TITLE — repeat 4x")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--height", type=int, default=1100, help="per-panel height in px")
    ap.add_argument("--pair-gap", type=int, default=12, help="gap between orig and ink in a pair")
    ap.add_argument("--pair-margin", type=int, default=18, help="margin inside the pair cell")
    ap.add_argument("--cell-gap", type=int, default=56, help="gap between cells")
    ap.add_argument("--outer-margin", type=int, default=72)
    ap.add_argument("--font", default=None)
    args = ap.parse_args()

    font_path = resolve_font(args.font)

    def font(size):
        return ImageFont.truetype(font_path, size)

    pairs = [parse_pair(p) for p in args.pair]
    assert len(pairs) == 4, "Need exactly 4 pairs for 2x2 grid"

    H = args.height

    # pre-load images at target size, then derive actual cell width from real panel widths
    loaded = []
    cell_w_inner = 0
    for orig, ink, title in pairs:
        o = Image.open(orig).convert("RGB")
        i = Image.open(ink).convert("RGB")
        o = o.resize((max(1, int(o.width * H / o.height)), H), Image.LANCZOS)
        i = i.resize((max(1, int(i.width * H / i.height)), H), Image.LANCZOS)
        cell_w_inner = max(cell_w_inner, o.width + args.pair_gap + i.width)
        loaded.append((o, i, title))

    # each cell: pair image (orig|ink side by side, with margin) + label below
    cell_w = cell_w_inner + args.pair_margin * 2
    cap_h = 132  # for "原图" / "水墨" labels + scene title
    cell_h = H + cap_h

    canvas_w = args.outer_margin * 2 + cell_w * 2 + args.cell_gap
    title_h = 200 if (args.title or args.subtitle) else args.outer_margin
    canvas_h = args.outer_margin + cell_h * 2 + args.cell_gap + title_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), PAPER)
    draw = ImageDraw.Draw(canvas)

    f_label = font(34)  # "原图" / "水墨"
    f_scene = font(30)  # scene name
    f_title = font(54)
    f_sub = font(26)

    positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for (col, row), (o, i, scene) in zip(positions, loaded):
        cx = args.outer_margin + col * (cell_w + args.cell_gap)
        cy = args.outer_margin + row * (cell_h + args.cell_gap)

        # paste orig (left) and ink (right) inside the cell
        oy = cy
        ix = cx + args.pair_margin + o.width + args.pair_gap
        iy = cy
        canvas.paste(o, (cx + args.pair_margin, oy))
        canvas.paste(i, (ix, iy))

        # thin separator line between orig and ink
        midx = cx + args.pair_margin + o.width + args.pair_gap // 2
        draw.line([(midx, cy + 8), (midx, cy + H - 8)], fill=RULE, width=2)

        # label band
        lab_y = cy + H + 18
        # divider line above the label
        draw.line([(cx, lab_y - 14), (cx + cell_w, lab_y - 14)], fill=RULE, width=2)
        # "原图" under orig
        w1 = draw.textlength("原图", font=f_label)
        draw.text((cx + args.pair_margin + (o.width - w1) / 2, lab_y), "原图", font=f_label, fill=INK)
        # "水墨" under ink
        w2 = draw.textlength("水墨", font=f_label)
        draw.text((ix + (i.width - w2) / 2, lab_y), "水墨", font=f_label, fill=INK)
        # scene title, centred in the cell
        ws = draw.textlength(scene, font=f_scene)
        draw.text((cx + (cell_w - ws) / 2, lab_y + 56), scene, font=f_scene, fill=GREY)

    # outer title
    if args.title or args.subtitle:
        ty = args.outer_margin + cell_h * 2 + args.cell_gap + 22
        if args.title:
            ft = font(54)
            w = draw.textlength(args.title, font=ft)
            draw.text(((canvas_w - w) / 2, ty), args.title, font=ft, fill=INK)
        if args.subtitle:
            fs = font(26)
            w = draw.textlength(args.subtitle, font=fs)
            draw.text(((canvas_w - w) / 2, ty + (74 if args.title else 0)),
                      args.subtitle, font=fs, fill=GREY)

    canvas.save(args.output, quality=95)
    print(f"saved {args.output} {canvas.size}")


if __name__ == "__main__":
    main()

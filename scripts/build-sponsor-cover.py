#!/usr/bin/env python3
"""Build the Buy Me a Coffee cover image: snippets/sponsor-cover.png.

    python3 scripts/build-sponsor-cover.py                 # rebuild the cover
    python3 scripts/build-sponsor-cover.py --preview F.png # also draw how BMC shows it

Rerun it when JellyRock's Home screen changes, commit the PNG, then upload it on
buymeacoffee.com (Edit page > cover). BMC has no upload API, so that step stays by hand.

Needs Pillow (with WebP support) and the Barlow font installed (fc-match must find it).

How BMC shows the cover (from its CSS, checked 2026-11-08), which sets the layout:
  - width 100% of the window, height 25vw: the whole 4:1 image shows...
  - ...except at windows >= 1900px, where height is 16.67vw and the image is
    cropped to its middle two-thirds (object-fit: cover, centered).
  - On desktop the page's cards overlap the bottom 80px (-mt-20), across the
    middle ~1010px; on phones the profile photo overlaps the bottom-center (56px).
  - BMC serves the cover at most 1920px wide, so this writes exactly 1920x480.
So text stays between 17% and 64% of the height, on the left.
"""
import argparse
import io
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCREENSHOT = "https://raw.githubusercontent.com/jellyrock/jellyrock/main/docs/screenshots/en_US/home.webp"
TAGLINE = "Open-source Jellyfin client for Roku"
OUT = Path(__file__).resolve().parent.parent / "snippets" / "sponsor-cover.png"

# Drawn at 3200x800 and scaled down to 1920x480 for smooth edges.
W, H = 3200, 800
BG = (13, 17, 23)          # jellyrock.app --jr-bg-primary
TEXT = (240, 240, 240)     # --jr-text-primary
MUTED = (168, 168, 168)    # --jr-text-secondary
PURPLE = (139, 92, 246)    # --jr-primary
BLUE = (59, 130, 246)      # --jr-secondary


def font(style, size):
    path = subprocess.run(["fc-match", "-f", "%{file}", f"Barlow:style={style}"],
                          capture_output=True, text=True).stdout
    if "Barlow" not in Path(path).name:
        sys.exit(f"Barlow {style} isn't installed (fc-match found {path or 'nothing'}). "
                 "Install it from https://fonts.google.com/specimen/Barlow")
    return ImageFont.truetype(path, size)


def solve(a, b):
    """Gaussian elimination for the 8x8 perspective system (keeps numpy out)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def perspective_coeffs(dst, src):
    a, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return solve(a, b)


def glow(canvas, cx, cy, r, color, alpha):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (alpha,))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(r * 0.45)))


def build(shot):
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    glow(canvas, 2350, 420, 520, PURPLE, 70)
    glow(canvas, 2850, 300, 420, BLUE, 55)

    # The Home screen as a card, turned slightly toward the text; it runs off the
    # right and bottom edges so the cut lands in a poster row, not on text.
    sw, sh = 1650, round(1650 * shot.height / shot.width)
    shot = shot.convert("RGBA").resize((sw, sh), Image.LANCZOS)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, sh - 1), 28, fill=255)
    shot.putalpha(mask)
    ImageDraw.Draw(shot).rounded_rectangle((0, 0, sw - 1, sh - 1), 28, outline=(255, 255, 255, 40), width=3)
    ox, oy, lift = 1700, 175, 70
    dst = [(0, 0), (sw, lift), (sw, sh - lift), (0, sh)]
    card = shot.transform((sw, sh), Image.PERSPECTIVE,
                          perspective_coeffs(dst, [(0, 0), (sw, 0), (sw, sh), (0, sh)]), Image.BICUBIC)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sm = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ImageDraw.Draw(sm).polygon(dst, fill=(0, 0, 0, 190))
    shadow.paste(sm, (ox + 30, oy + 40), sm)
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(40)))
    canvas.alpha_composite(card, (ox, oy))

    d = ImageDraw.Draw(canvas)
    tx = 200
    d.text((tx, 322), "JellyRock", font=font("ExtraBold", 210), fill=TEXT, anchor="ls")
    for i in range(240):  # accent bar, purple to blue
        t = i / 239
        d.line((tx + i, 382, tx + i, 394), fill=tuple(round(p + (b - p) * t) for p, b in zip(PURPLE, BLUE)))
    d.text((tx, 494), TAGLINE, font=font("Medium", 76), fill=MUTED, anchor="ls")
    return canvas.convert("RGB").resize((1920, 480), Image.LANCZOS)


def preview(cover, path):
    """Draw the cover the way BMC shows it at a phone and three desktop widths."""
    label_font = font("Medium", 22)
    rows = []
    for v in (390, 1280, 1899, 2545):
        img = cover.resize((v, v // 4), Image.LANCZOS)
        if v >= 1900:
            h = round(v / 6); top = (v // 4 - h) // 2
            img = img.crop((0, top, v, top + h))
        img = img.convert("RGBA")
        o = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(o)
        if v < 768:   # profile photo
            d.rounded_rectangle((v // 2 - 50, img.height - 56, v // 2 + 50, img.height + 40), 12, fill=(245, 245, 245, 230))
        else:         # the two cards
            for x0, x1 in ((v // 2 - 505, v // 2 - 8), (v // 2 + 5, v // 2 + 505)):
                d.rounded_rectangle((x0, img.height - 80, x1, img.height + 20), 16, fill=(40, 40, 46, 235))
        img.alpha_composite(o)
        scale = 2.5 if v == 390 else 1000 / v
        img = img.resize((round(v * scale), round(img.height * scale)), Image.LANCZOS)
        rows.append((f"{v}px window" + (" (phone, enlarged 2.5x)" if v == 390 else ""), img))
    sheet = Image.new("RGB", (1000, sum(r.height + 40 for _, r in rows)), (255, 255, 255))
    d = ImageDraw.Draw(sheet); y = 0
    for label, r in rows:
        d.text((4, y + 8), label, font=label_font, fill=(0, 0, 0))
        sheet.paste(r.convert("RGB"), (0, y + 36)); y += r.height + 40
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--preview", metavar="PNG", help="also write a sheet showing how BMC displays it")
    args = ap.parse_args()
    with urllib.request.urlopen(SCREENSHOT, timeout=30) as r:
        shot = Image.open(io.BytesIO(r.read()))
    cover = build(shot)
    cover.save(OUT, optimize=True)
    print(f"wrote {OUT}")
    if args.preview:
        preview(cover, args.preview)
        print(f"wrote {args.preview}")


if __name__ == "__main__":
    main()

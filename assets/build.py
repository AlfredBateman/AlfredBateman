"""Builds the README's SVGs: hero and divider, light and dark.

Text is outlined to paths (an SVG shown through <img> cannot load web fonts).
Fonts and tokens come from AlfredBateman/portfolio-v3 (src/fonts, src/styles/tokens.css).

    pip install fonttools brotli uharfbuzz
    python assets/build.py path/to/archivo-100_900-normal.woff2 path/to/anek-devanagari-ishan.woff2
"""
import io
import math
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OUT = Path(__file__).parent
W = 1012  # GitHub's README width

# portfolio-v3 tokens.css; dark swaps chart and graphite and keeps the needle red
PALETTES = {
    "light": dict(bg="#edeeea", fg="#121315", muted="#4f535a", line="rgb(18 19 21 / 0.14)", accent="#c4221a"),
    "dark": dict(bg="#121315", fg="#edeeea", muted="#a3a6a2", line="rgb(237 238 234 / 0.14)", accent="#c4221a"),
}


def num(n):
    return f"{n:.1f}".rstrip("0").rstrip(".") if abs(n) >= 0.05 else "0"


class Face:
    def __init__(self, path):
        tt = TTFont(path)
        buf = io.BytesIO()
        tt.flavor = None
        tt.save(buf)
        self.tt = TTFont(io.BytesIO(buf.getvalue()))
        self.hb = hb.Face(buf.getvalue())
        self.upem = self.tt["head"].unitsPerEm
        self.order = self.tt.getGlyphOrder()

    def run(self, text, axes, size, tracking=0.0):
        """Shape `text`; return (glyphs [(name, x_units)], advance_units, glyphset)."""
        font = hb.Font(self.hb)
        font.set_variations(axes)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"kern": True, "liga": True})
        x, glyphs = 0, []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append((self.order[info.codepoint], x + pos.x_offset))
            x += pos.x_advance + tracking * self.upem
        x -= tracking * self.upem  # no tracking after the last glyph
        return glyphs, x, self.tt.getGlyphSet(location=axes)

    def path(self, text, axes, size, x, y, tracking=0.0, anchor="start", center_y=None):
        """Outline text as one path `d`. anchor: start | middle (bbox-centred on x, and on center_y if given)."""
        glyphs, adv, gs = self.run(text, axes, size, tracking)
        s = size / self.upem
        if anchor == "middle":
            bp = BoundsPen(gs)
            for name, gx in glyphs:
                gs[name].draw(TransformPen(bp, Transform(1, 0, 0, 1, gx, 0)))
            x0, y0, x1, y1 = bp.bounds
            x -= (x0 + x1) / 2 * s
            if center_y is not None:
                y = center_y + (y0 + y1) / 2 * s
        pen = SVGPathPen(gs, ntos=num)
        for name, gx in glyphs:
            gs[name].draw(TransformPen(pen, Transform(s, 0, 0, -s, x + gx * s, y)))
        return pen.getCommands()

    def width(self, text, axes, size, tracking=0.0):
        return self.run(text, axes, size, tracking)[1] * size / self.upem

    def cap(self, size):
        return self.tt["OS/2"].sCapHeight * size / self.upem


DISPLAY = {"wdth": 125, "wght": 800}  # DESIGN.md display: wdth 125, wght 800, uppercase, -0.045em
TRACK = -0.045


def at(deg, r):
    a = math.radians(deg - 90)
    return r * math.cos(a), r * math.sin(a)


def dial(archivo, anek, p, cx, cy, s):
    """The portfolio-v3 compass (src/components/Compass.astro), drawn at scale s around (cx, cy)."""
    R = 98
    out = [f'<g transform="translate({num(cx)} {num(cy)}) scale({s})">',
           f'<circle r="{R}" fill="none" stroke="{p["fg"]}" stroke-width="{round(1 / s, 3)}"/>']
    for d in range(0, 360, 5):
        ln = 13 if d % 45 == 0 else 8 if d % 15 == 0 else 4
        col, sw = (p["accent"], 3) if d == 45 else (p["fg"], 2 if d % 45 == 0 else 1)
        out.append(f'<line y1="{-R}" y2="{-R + ln}" stroke="{col}" stroke-width="{round(sw / s, 3)}"'
                   f' transform="rotate({d})"/>')
    labels = []
    for d, t in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
        lx, ly = at(d, 74)
        labels.append(archivo.path(t, {"wdth": 125, "wght": 700}, 9, lx, 0, anchor="middle", center_y=ly))
    out.append(f'<path fill="{p["fg"]}" d="{"".join(labels)}"/>')
    nums = []
    for d in [30, 60, 120, 150, 210, 240, 300, 330]:
        lx, ly = at(d, 80)
        nums.append(archivo.path(str(d), {"wdth": 100, "wght": 500}, 5, lx, 0, anchor="middle", center_y=ly))
    out.append(f'<path fill="{p["muted"]}" d="{"".join(nums)}"/>')
    nx, ny = at(45, 117)  # outside the ring: the needle points at the word
    out.append(f'<path fill="{p["accent"]}" d="{anek.path("ईशान", {"wdth": 112, "wght": 800}, 13, nx, 0, anchor="middle", center_y=ny)}"/>')
    w = 5.5
    out.append(f'<g class="n"><polygon fill="{p["accent"]}" points="0,-86 {w},0 {-w},0"/>'
               f'<polygon fill="{p["fg"]}" points="0,86 {w},0 {-w},0"/>'
               f'<circle r="3.5" fill="{p["bg"]}" stroke="{p["fg"]}" stroke-width="{round(1.5 / s, 3)}"/></g>')
    out.append("</g>")
    return "".join(out)


# One settle to 045°, overshooting once like the site's damped spring. Static under reduced motion.
MOTION = ("<style>.n{transform:rotate(45deg);transform-box:fill-box;transform-origin:center;"
          "animation:settle 1.6s ease-out .3s both}"
          "@keyframes settle{0%{transform:rotate(-40deg)}55%{transform:rotate(54deg)}"
          "80%{transform:rotate(42deg)}100%{transform:rotate(45deg)}}"
          "@media (prefers-reduced-motion:reduce){.n{animation:none}}</style>")


def hero(archivo, anek, p):
    H, M = 420, 48
    name = "ISHAN SHARMA"
    size = (W - 2 * M) / archivo.width(name, DISPLAY, 1, TRACK)
    base = H - M
    top = base - archivo.cap(size)
    s = (top - 20 - 36) / (2 * 98)  # dial fits between the top margin and the name
    r = 98 * s
    cx, cy = W - M - 64 - r * 0.6, 36 + r
    tag = {"wdth": 100, "wght": 500}
    t1 = archivo.path("Software engineer,", tag, 34, M, M + 26)
    t2 = archivo.path("backend and full-stack", tag, 34, M, M + 26 + 44)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"'
            f' role="img" aria-label="Ishan Sharma, software engineer, backend and full-stack">{MOTION}'
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" fill="{p["bg"]}" stroke="{p["line"]}"/>'
            f'<path fill="{p["muted"]}" d="{t1}{t2}"/>'
            f'{dial(archivo, anek, p, cx, cy, round(s, 3))}'
            f'<path fill="{p["fg"]}" d="{archivo.path(name, DISPLAY, size, M, base, TRACK)}"/></svg>')


def divider(p):
    """A bearing scale, 0 to 360 degrees, ticks hanging from a hairline like the dial's, 045 in red."""
    H = 24
    step = (W - 1) / 72
    ticks = []
    for i in range(73):
        d = i * 5
        ln = 14 if d % 45 == 0 else 8 if d % 15 == 0 else 4
        col, sw = (p["accent"], 3) if d == 45 else (p["fg"], 2 if d % 45 == 0 else 1)
        x = num(0.5 + i * step)
        ticks.append(f'<line x1="{x}" x2="{x}" y1="0" y2="{ln}" stroke="{col}" stroke-width="{sw}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"'
            f' role="img" aria-label="Divider: a compass bearing scale, 045 degrees marked in red">'
            f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>'
            f'<line x2="{W}" y1=".5" y2=".5" stroke="{p["fg"]}"/>{"".join(ticks)}</svg>')


def contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


if __name__ == "__main__":
    archivo, anek = Face(sys.argv[1]), Face(sys.argv[2])
    for mode, p in PALETTES.items():
        (OUT / f"hero-{mode}.svg").write_text(hero(archivo, anek, p), encoding="utf-8")
        (OUT / f"divider-{mode}.svg").write_text(divider(p), encoding="utf-8")
        for k in ("fg", "muted", "accent"):
            print(f"{mode}: {k} on bg {contrast(p[k], p['bg']):.2f}:1")

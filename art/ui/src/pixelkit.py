"""
pixelkit — tiny reusable pixel-art toolkit for the gothic ARPG UI mockups.

Everything is drawn into palette-index numpy arrays at native resolution and
only converted to RGB at export time (upscaled with NEAREST), so the result
can never contain colours outside PALETTE.

Contents
  PALETTE / RAMPS ........ the unified 32-colour palette and material ramps
  Canvas ................. palette-index drawing surface (rects, lines, discs,
                           polygons, dithering, sprites, text)
  FONT5x7 / FONT3x5 ...... hand-made bitmap fonts (uppercase, digits, punct.)
  Lit ................... world layer: (ramp, level, emissive) buffers that get
                           banded/dithered lighting before flattening
  sprite tools ........... material-letter sprites with auto shading/outline
  widgets ................ stone panels, slots, buttons, bars, orbs, labels
  icons .................. skill icons, menu icons, potions
"""
import json
import math
import numpy as np
from PIL import Image, ImageDraw

# --------------------------------------------------------------------------
# PALETTE (32 colours) — index: (name, hex)
# --------------------------------------------------------------------------
PALETTE = [
    ("ink",        "#0a090c"),  # 0  outlines, deepest shadow
    ("abyss",      "#18141b"),  # 1
    ("shadow",     "#28222b"),  # 2
    ("stone_dk",   "#3a333b"),  # 3
    ("stone",      "#524a4e"),  # 4
    ("stone_lt",   "#74685f"),  # 5
    ("bone",       "#a8987c"),  # 6
    ("parchment",  "#ece0c2"),  # 7  text / brightest neutral
    ("earth_dk",   "#2b2219"),  # 8
    ("earth",      "#45351f"),  # 9
    ("moss_dk",    "#3d3b20"),  # 10 dead grass
    ("moss",       "#5b5629"),  # 11
    ("moss_lt",    "#7f7639"),  # 12
    ("iron_dk",    "#262b33"),  # 13
    ("iron",       "#434b56"),  # 14
    ("iron_lt",    "#6f7a84"),  # 15
    ("gold_dk",    "#4e3510"),  # 16
    ("gold",       "#8a5e1c"),  # 17
    ("gold_lt",    "#c8962f"),  # 18
    ("gold_hi",    "#f0d27a"),  # 19
    ("blood",      "#3a0a0e"),  # 20
    ("red_dk",     "#6c1116"),  # 21
    ("red",        "#a5231d"),  # 22
    ("red_lt",     "#df4b32"),  # 23
    ("navy",       "#0d1440"),  # 24
    ("blue_dk",    "#1d3594"),  # 25
    ("blue",       "#3f6cd6"),  # 26
    ("blue_lt",    "#9cc0f4"),  # 27
    ("ember",      "#e8801f"),  # 28
    ("flame",      "#ffd94e"),  # 29
    ("violet_dk",  "#3d1458"),  # 30
    ("violet",     "#9246c0"),  # 31
]
C = {name: i for i, (name, _) in enumerate(PALETTE)}
RGB = np.array([[int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)] for _, h in PALETTE],
               dtype=np.uint8)

# Material ramps (palette indices, dark -> light). Lighting walks down a ramp.
RAMPS = {
    "ink":    [0],
    "stone":  [0, 1, 2, 3, 4, 5, 6, 7],
    "bone":   [0, 1, 2, 3, 5, 6, 7],
    "grass":  [0, 1, 8, 10, 11, 12],
    "earth":  [0, 1, 8, 9, 5, 6],
    "wood":   [0, 1, 8, 9, 17, 18],
    "iron":   [0, 1, 13, 14, 15, 7],
    "gold":   [0, 1, 16, 17, 18, 19],
    "red":    [0, 1, 20, 21, 22, 23],
    "blue":   [0, 1, 24, 25, 26, 27],
    "violet": [0, 1, 30, 31, 27],
    "fire":   [21, 22, 23, 28, 29, 7],      # emissive
}
RAMP_NAMES = list(RAMPS)
RAMP_ID = {n: i for i, n in enumerate(RAMP_NAMES)}
_MAXR = max(len(r) for r in RAMPS.values())
RAMP_LUT = np.zeros((len(RAMPS), _MAXR), dtype=np.uint8)
for _n, _r in RAMPS.items():
    RAMP_LUT[RAMP_ID[_n], :len(_r)] = _r
    RAMP_LUT[RAMP_ID[_n], len(_r):] = _r[-1]
RAMP_LEN = np.array([len(RAMPS[n]) for n in RAMP_NAMES])

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0


def bayer(h, w, ox=0, oy=0):
    ys = (np.arange(h) + oy) % 4
    xs = (np.arange(w) + ox) % 4
    return BAYER4[ys[:, None], xs[None, :]]


def hash2(x, y, seed=0):
    """Deterministic integer hash -> float in [0,1)."""
    h = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def value_noise(h, w, cell, seed=0):
    rng = np.random.default_rng(seed)
    gh, gw = h // cell + 2, w // cell + 2
    g = rng.random((gh, gw))
    ys = np.arange(h) / cell
    xs = np.arange(w) / cell
    y0 = ys.astype(int); x0 = xs.astype(int)
    fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def save_palette(png_path, json_path, sw=32):
    cols = 8
    rows = (len(PALETTE) + cols - 1) // cols
    cv = Canvas(cols * sw, rows * (sw + 10), fill=C["ink"])
    for i, (name, hx) in enumerate(PALETTE):
        x, y = (i % cols) * sw, (i // cols) * (sw + 10)
        cv.frame(x + 1, y + 1, sw - 2, sw - 2, C["bone"])
        cv.rect(x + 2, y + 2, sw - 4, sw - 4, i)
        cv.text(x + 2, y + sw + 2, str(i), C["parchment"], font=FONT3x5, shadow=None)
    cv.save(png_path, scale=4)
    with open(json_path, "w") as f:
        json.dump({"count": len(PALETTE),
                   "colors": [{"index": i, "name": n, "hex": h} for i, (n, h) in enumerate(PALETTE)],
                   "ramps": {k: [PALETTE[i][0] for i in v] for k, v in RAMPS.items()}},
                  f, indent=2)


# --------------------------------------------------------------------------
# FONTS
# --------------------------------------------------------------------------
def _font(src, h):
    out = {}
    for ch, rows in src.items():
        rows = rows.split(",")
        assert len(rows) == h, (ch, rows)
        w = max(len(r) for r in rows)
        out[ch] = np.array([[1 if c == "#" else 0 for c in r.ljust(w, ".")] for r in rows], dtype=bool)
    return out


_F57 = {
 "A": ".###.,#...#,#...#,#####,#...#,#...#,#...#",
 "B": "####.,#...#,#...#,####.,#...#,#...#,####.",
 "C": ".###.,#...#,#....,#....,#....,#...#,.###.",
 "D": "####.,#...#,#...#,#...#,#...#,#...#,####.",
 "E": "#####,#....,#....,####.,#....,#....,#####",
 "F": "#####,#....,#....,####.,#....,#....,#....",
 "G": ".###.,#...#,#....,#.###,#...#,#...#,.####",
 "H": "#...#,#...#,#...#,#####,#...#,#...#,#...#",
 "I": "###,.#.,.#.,.#.,.#.,.#.,###",
 "J": "..###,...#.,...#.,...#.,#..#.,#..#.,.##..",
 "K": "#...#,#..#.,#.#..,##...,#.#..,#..#.,#...#",
 "L": "#....,#....,#....,#....,#....,#....,#####",
 "M": "#...#,##.##,#.#.#,#.#.#,#...#,#...#,#...#",
 "N": "#...#,##..#,#.#.#,#..##,#...#,#...#,#...#",
 "O": ".###.,#...#,#...#,#...#,#...#,#...#,.###.",
 "P": "####.,#...#,#...#,####.,#....,#....,#....",
 "Q": ".###.,#...#,#...#,#...#,#.#.#,#..#.,.##.#",
 "R": "####.,#...#,#...#,####.,#.#..,#..#.,#...#",
 "S": ".####,#....,#....,.###.,....#,....#,####.",
 "T": "#####,..#..,..#..,..#..,..#..,..#..,..#..",
 "U": "#...#,#...#,#...#,#...#,#...#,#...#,.###.",
 "V": "#...#,#...#,#...#,#...#,#...#,.#.#.,..#..",
 "W": "#...#,#...#,#...#,#.#.#,#.#.#,##.##,#...#",
 "X": "#...#,#...#,.#.#.,..#..,.#.#.,#...#,#...#",
 "Y": "#...#,#...#,.#.#.,..#..,..#..,..#..,..#..",
 "Z": "#####,....#,...#.,..#..,.#...,#....,#####",
 "0": ".###.,#...#,#..##,#.#.#,##..#,#...#,.###.",
 "1": ".#.,##.,.#.,.#.,.#.,.#.,###",
 "2": ".###.,#...#,....#,...#.,..#..,.#...,#####",
 "3": "####.,....#,....#,.###.,....#,....#,####.",
 "4": "...#.,..##.,.#.#.,#..#.,#####,...#.,...#.",
 "5": "#####,#....,####.,....#,....#,#...#,.###.",
 "6": ".###.,#....,#....,####.,#...#,#...#,.###.",
 "7": "#####,....#,...#.,..#..,.#...,.#...,.#...",
 "8": ".###.,#...#,#...#,.###.,#...#,#...#,.###.",
 "9": ".###.,#...#,#...#,.####,....#,....#,.###.",
 " ": "..,..,..,..,..,..,..",
 "-": "...,...,...,###,...,...,...",
 ".": ".,.,.,.,.,.,#",
 ",": "..,..,..,..,..,.#,#.",
 ":": ".,.,#,.,.,#,.",
 "'": "#,#,.,.,.,.,.",
 "!": "#,#,#,#,#,.,#",
 "/": "....#,...#.,...#.,..#..,.#...,.#...,#....",
 "+": ".....,..#..,..#..,#####,..#..,..#..,.....",
 "%": "##..#,##.#.,...#.,..#..,.#...,.#.##,#..##",
 "(": "..#,.#.,#..,#..,#..,.#.,..#",
 ")": "#..,.#.,..#,..#,..#,.#.,#..",
 "?": ".###.,#...#,....#,...#.,..#..,.....,..#..",
 "#": ".#.#.,.#.#.,#####,.#.#.,#####,.#.#.,.#.#.",
}
_F35 = {
 "0": "###,#.#,#.#,#.#,###", "1": ".#.,##.,.#.,.#.,###", "2": "##.,..#,.#.,#..,###",
 "3": "##.,..#,.#.,..#,##.", "4": "#.#,#.#,###,..#,..#", "5": "###,#..,##.,..#,##.",
 "6": ".##,#..,###,#.#,###", "7": "###,..#,.#.,.#.,.#.", "8": "###,#.#,###,#.#,###",
 "9": "###,#.#,###,..#,##.",
 "A": ".#.,#.#,###,#.#,#.#", "B": "##.,#.#,##.,#.#,##.", "C": ".##,#..,#..,#..,.##",
 "D": "##.,#.#,#.#,#.#,##.", "E": "###,#..,##.,#..,###", "F": "###,#..,##.,#..,#..",
 "G": ".##,#..,#.#,#.#,.##", "H": "#.#,#.#,###,#.#,#.#", "I": "###,.#.,.#.,.#.,###",
 "J": "..#,..#,..#,#.#,.#.", "K": "#.#,#.#,##.,#.#,#.#", "L": "#..,#..,#..,#..,###",
 "M": "#...#,##.##,#.#.#,#...#,#...#", "N": "#..#,##.#,#.##,#..#,#..#",
 "O": ".#.,#.#,#.#,#.#,.#.", "P": "##.,#.#,##.,#..,#..", "Q": ".#.,#.#,#.#,##.,.##",
 "R": "##.,#.#,##.,#.#,#.#", "S": ".##,#..,.#.,..#,##.", "T": "###,.#.,.#.,.#.,.#.",
 "U": "#.#,#.#,#.#,#.#,###", "V": "#.#,#.#,#.#,#.#,.#.", "W": "#...#,#...#,#.#.#,##.##,#...#",
 "X": "#.#,#.#,.#.,#.#,#.#", "Y": "#.#,#.#,.#.,.#.,.#.", "Z": "###,..#,.#.,#..,###",
 " ": "..,..,..,..,..", "-": "...,...,###,...,...", ".": ".,.,.,.,#", ":": ".,#,.,#,.",
 "/": "..#,..#,.#.,#..,#..", "+": "...,.#.,###,.#.,...", "'": "#,#,.,.,.",
 "%": "#.#,..#,.#.,#..,#.#", "!": "#,#,#,.,#",
 "(": ".#,#.,#.,#.,.#", ")": "#.,.#,.#,.#,#.", ",": "..,..,..,.#,#.", "?": "##.,..#,.#.,...,.#.",
}
# Cyrillic uppercase (5x7). Letters shaped like Latin ones reuse those glyphs.
_F57_CYR = {
 "Б": "#####,#....,#....,####.,#...#,#...#,####.",
 "Г": "#####,#....,#....,#....,#....,#....,#....",
 "Д": ".####,.#..#,.#..#,.#..#,.#..#,#####,#...#",
 "Ё": ".#.#.,#####,#....,####.,#....,#....,#####",
 "Ж": "#.#.#,#.#.#,.###.,..#..,.###.,#.#.#,#.#.#",
 "З": ".###.,#...#,....#,..##.,....#,#...#,.###.",
 "И": "#...#,#...#,#..##,#.#.#,##..#,#...#,#...#",
 "Й": ".#.#.,..#..,#...#,#..##,#.#.#,##..#,#...#",
 "Л": "..###,.#..#,.#..#,.#..#,.#..#,.#..#,#...#",
 "П": "#####,#...#,#...#,#...#,#...#,#...#,#...#",
 "У": "#...#,#...#,#...#,.####,....#,#...#,.###.",
 "Ф": "..#..,.###.,#.#.#,#.#.#,#.#.#,.###.,..#..",
 "Ц": "#..#.,#..#.,#..#.,#..#.,#..#.,#####,....#",
 "Ч": "#...#,#...#,#...#,.####,....#,....#,....#",
 "Ш": "#.#.#,#.#.#,#.#.#,#.#.#,#.#.#,#.#.#,#####",
 "Щ": "#.#.#.,#.#.#.,#.#.#.,#.#.#.,#.#.#.,######,.....#",
 "Ъ": "##...,.#...,.#...,.###.,.#..#,.#..#,.###.",
 "Ы": "#...#,#...#,#...#,##..#,#.#.#,#.#.#,##..#",
 "Ь": "#....,#....,#....,####.,#...#,#...#,####.",
 "Э": ".###.,#...#,....#,..###,....#,#...#,.###.",
 "Ю": "#..#.,#.#.#,#.#.#,###.#,#.#.#,#.#.#,#..#.",
 "Я": ".####,#...#,#...#,.####,..#.#,.#..#,#...#",
}
for _lat, _cy in zip("ABEKMHOPCTX", "АВЕКМНОРСТХ"):
    _F57_CYR[_cy] = _F57[_lat]
_F57.update(_F57_CYR)
FONT5x7 = {"glyphs": _font(_F57, 7), "h": 7, "sp": 1}
FONT3x5 = {"glyphs": _font(_F35, 5), "h": 5, "sp": 1}


def _chars(s, g):
    """Glyph keys for string s: exact char if the font has it, else uppercase."""
    out = []
    for ch in s:
        if ch in g:
            out.append(ch)
        elif ch.upper() in g:
            out.append(ch.upper())
    return out


def text_width(s, font=FONT5x7):
    g = font["glyphs"]
    return sum(g[ch].shape[1] + font["sp"] for ch in _chars(s, g)) - font["sp"]


# --------------------------------------------------------------------------
# CANVAS — palette index surface
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.a = np.full((h, w), fill, dtype=np.uint8)

    # ---- primitives -----------------------------------------------------
    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def rect(self, x, y, w, h, c):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = c

    def frame(self, x, y, w, h, c):
        self.rect(x, y, w, 1, c); self.rect(x, y + h - 1, w, 1, c)
        self.rect(x, y, 1, h, c); self.rect(x + w - 1, y, 1, h, c)

    def hline(self, x, y, w, c): self.rect(x, y, w, 1, c)
    def vline(self, x, y, h, c): self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy

    def mask_disc(self, cx, cy, r):
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r

    def disc(self, cx, cy, r, c):
        self.a[self.mask_disc(cx, cy, r)] = c

    def mask_poly(self, pts):
        m = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(m).polygon([(round(x), round(y)) for x, y in pts], fill=1)
        return np.array(m, dtype=bool)

    def poly(self, pts, c, outline=None):
        self.a[self.mask_poly(pts)] = c
        if outline is not None:
            p = [(round(x), round(y)) for x, y in pts]
            for i in range(len(p)):
                self.line(*p[i], *p[(i + 1) % len(p)], outline)

    def dither(self, x, y, w, h, c, density=0.5, ox=0, oy=0):
        """Ordered-dither overlay of colour c with given density."""
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        b = bayer(y1 - y0, x1 - x0, x0 + ox, y0 + oy)
        sub = self.a[y0:y1, x0:x1]
        sub[b < density] = c

    def remap(self, x, y, w, h, lut):
        """Recolour region through a 32-entry lookup (e.g. darken for overlays)."""
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        self.a[y0:y1, x0:x1] = np.asarray(lut, dtype=np.uint8)[self.a[y0:y1, x0:x1]]

    def blit(self, spr, x, y):
        """spr: int array with -1 transparent."""
        h, w = spr.shape
        for j in range(h):
            for i in range(w):
                if spr[j, i] >= 0:
                    self.px(x + i, y + j, int(spr[j, i]))

    def stamp(self, rows, legend, x, y):
        """Direct palette sprite: rows of chars, legend char->palette index ('.' = clear)."""
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch != "." and ch in legend:
                    self.px(x + i, y + j, legend[ch])

    # ---- text -------------------------------------------------------------
    def text(self, x, y, s, c, font=FONT5x7, shadow=C["ink"], outline=False):
        g = font["glyphs"]
        cx = x
        for ch in _chars(s, g):
            m = g[ch]
            hh, ww = m.shape
            if outline:
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        self._glyph(m, cx + ox, y + oy, outline)
            elif shadow is not None:
                self._glyph(m, cx + 1, y + 1, shadow)
            cx += ww + font["sp"]
        cx = x
        for ch in _chars(s, g):
            m = g[ch]
            self._glyph(m, cx, y, c)
            cx += m.shape[1] + font["sp"]
        return cx - x - font["sp"]

    def text_c(self, cx, y, s, c, font=FONT5x7, **kw):
        return self.text(cx - text_width(s, font) // 2, y, s, c, font, **kw)

    def text_r(self, rx, y, s, c, font=FONT5x7, **kw):
        return self.text(rx - text_width(s, font), y, s, c, font, **kw)

    def _glyph(self, m, x, y, c):
        ys, xs = np.nonzero(m)
        for j, i in zip(ys, xs):
            self.px(x + i, y + j, c)

    # ---- export -----------------------------------------------------------
    def rgb(self):
        return Image.fromarray(RGB[self.a], "RGB")

    def save(self, path, scale=1):
        im = self.rgb()
        if scale != 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        im.save(path)
        return im


# --------------------------------------------------------------------------
# SPRITES — material-letter maps with automatic shading + outline
# --------------------------------------------------------------------------
# legend value: (ramp, base_level, autoshade, emissive)
def make_sprite(rows, legend, outline=True, light=(-1, -1)):
    """Returns dict of arrays: ramp, lvl, em, mask (all HxW)."""
    w = max(len(r) for r in rows)
    pad = 1 if outline else 0
    H, W = len(rows) + 2 * pad, w + 2 * pad
    ch = np.full((H, W), ".", dtype="<U1")
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            ch[j + pad, i + pad] = c
    ramp = np.full((H, W), -1, dtype=np.int16)
    lvl = np.zeros((H, W), dtype=np.int16)
    em = np.zeros((H, W), dtype=bool)
    for j in range(H):
        for i in range(W):
            c = ch[j, i]
            if c == "." or c not in legend:
                continue
            rn, base, auto, emi = legend[c][:4]
            pat = legend[c][4] if len(legend[c]) > 4 else None
            l = base
            if auto:
                def diff(dx, dy):
                    jj, ii = j + dy, i + dx
                    if not (0 <= jj < H and 0 <= ii < W):
                        return True
                    return ch[jj, ii] != c
                s = 0
                if diff(light[0], 0) or diff(0, light[1]): s += 1
                if diff(-light[0], 0) or diff(0, -light[1]): s -= 1
                l = base + max(-1, min(1, s))
            if pat == "mail" and ((i + (j // 2) % 2) % 2 == 0) and j % 2 == 0:
                l -= 1
            elif pat == "grain" and (hash2(i // 3, j, 17) < 0.25):
                l -= 1
            elif pat == "fur" and hash2(i, j // 2, 23) < 0.3:
                l -= 1
            elif pat == "dither" and (i + j) % 2 == 0:
                l -= 1
            ramp[j, i] = RAMP_ID[rn]
            lvl[j, i] = max(0, min(RAMP_LEN[RAMP_ID[rn]] - 1, l))
            em[j, i] = emi
    mask = ramp >= 0
    if outline:
        m = mask
        nb = np.zeros_like(m)
        nb[1:, :] |= m[:-1, :]; nb[:-1, :] |= m[1:, :]
        nb[:, 1:] |= m[:, :-1]; nb[:, :-1] |= m[:, 1:]
        o = nb & ~m
        ramp[o] = RAMP_ID["ink"]; lvl[o] = 0
        mask = mask | o
    return {"ramp": ramp, "lvl": lvl, "em": em, "mask": mask, "w": W, "h": H}


def sprite_to_index(spr):
    """Flatten a material sprite into a palette-index array (-1 transparent)."""
    out = np.full(spr["ramp"].shape, -1, dtype=np.int16)
    m = spr["mask"]
    out[m] = RAMP_LUT[spr["ramp"][m], spr["lvl"][m]]
    return out


def flip(spr):
    return {k: (v[:, ::-1].copy() if isinstance(v, np.ndarray) else v) for k, v in spr.items()}


# --------------------------------------------------------------------------
# LIT LAYER — world buffers with banded / dithered lighting
# --------------------------------------------------------------------------
class Lit:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ramp = np.full((h, w), RAMP_ID["ink"], dtype=np.int16)
        self.lvl = np.zeros((h, w), dtype=np.int16)
        self.em = np.zeros((h, w), dtype=bool)

    def put(self, mask, ramp, lvl, em=False):
        self.ramp[mask] = RAMP_ID[ramp] if isinstance(ramp, str) else ramp
        self.lvl[mask] = lvl if np.isscalar(lvl) else lvl[mask]
        self.em[mask] = em

    def shade(self, mask, d):
        self.lvl[mask] = np.maximum(0, self.lvl[mask] + d)

    def sprite(self, spr, x, y):
        """Place sprite with top-left at (x,y)."""
        h, w = spr["mask"].shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        sm = spr["mask"][y0 - y:y1 - y, x0 - x:x1 - x]
        for k, buf in (("ramp", self.ramp), ("lvl", self.lvl), ("em", self.em)):
            sub = buf[y0:y1, x0:x1]
            sub[sm] = spr[k][y0 - y:y1 - y, x0 - x:x1 - x][sm]

    def flatten(self, light, extra=None):
        """light: float array (h,w) of level offsets (<=0). Returns palette index array."""
        off = light.copy()
        if extra is not None:
            off = off + extra
        b = bayer(self.h, self.w)
        d = np.floor(off + b).astype(np.int16)
        d[self.em] = 0
        lv = self.lvl + d
        lv = np.clip(lv, 0, RAMP_LEN[self.ramp] - 1)
        return RAMP_LUT[self.ramp, lv]


def light_field(w, h, sources, ambient=0.15, depth=4.5, ysquash=1.6, gamma=1.0):
    """sources: list of (x, y, radius, intensity). Returns level offset field (<=0)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    B = np.full((h, w), ambient)
    for (sx, sy, r, inten) in sources:
        d = np.sqrt((xx - sx) ** 2 + ((yy - sy) * ysquash) ** 2) / r
        B += inten * np.clip(1 - d, 0, 1) ** gamma
    B = np.clip(B, 0, 1)
    return -depth * (1 - B)


# --------------------------------------------------------------------------
# WIDGETS
# --------------------------------------------------------------------------
def stone_fill(cv, x, y, w, h, seed=1, base=3, brick=(16, 8), mortar=C["abyss"]):
    """Dark carved stone blocks with per-block tone, bevel and grit."""
    bw, bh = brick
    for j in range(h):
        row = (j) // bh
        for i in range(w):
            xx, yy = x + i, y + j
            off = (row % 2) * (bw // 2)
            col = (i + off) // bw
            lj, li = j % bh, (i + off) % bw
            t = hash2(col, row, seed)
            tone = base + (1 if t > 0.75 else 0) - (1 if t < 0.2 else 0)
            if lj == 0 or li == 0:
                c = mortar
            elif lj == 1 or li == 1:
                c = min(tone + 1, 5)          # top/left bevel
            elif lj == bh - 1 or li == bw - 1:
                c = max(tone - 1, 1)          # bottom/right bevel
            else:
                g = hash2(xx, yy, seed + 7)
                c = tone - 1 if g < 0.10 else (tone + 1 if g > 0.95 else tone)
            cv.px(xx, yy, c)


def bevel(cv, x, y, w, h, light=C["stone_lt"], dark=C["ink"], outer=C["ink"], inset=False):
    if outer is not None:
        cv.frame(x, y, w, h, outer)
        x, y, w, h = x + 1, y + 1, w - 2, h - 2
    a, b = (dark, light) if inset else (light, dark)
    cv.hline(x, y, w, a); cv.vline(x, y, h, a)
    cv.hline(x, y + h - 1, w, b); cv.vline(x + w - 1, y, h, b)


def gold_trim(cv, x, y, w, h):
    """Worn gold frame line with darker inner line."""
    cv.frame(x, y, w, h, C["gold"])
    cv.hline(x + 1, y, w - 2, C["gold_lt"]); cv.vline(x, y + 1, h - 2, C["gold_lt"])
    # worn spots
    for k in range(0, w, 7):
        if hash2(x + k, y, 3) < 0.35:
            cv.px(x + k, y, C["gold"])
    cv.frame(x + 1, y + 1, w - 2, h - 2, C["gold_dk"])


def rivet(cv, x, y):
    cv.px(x, y, C["iron_lt"]); cv.px(x + 1, y, C["iron"])
    cv.px(x, y + 1, C["iron"]); cv.px(x + 1, y + 1, C["ink"])


def corner_studs(cv, x, y, w, h):
    for (cx, cy) in ((x, y), (x + w - 3, y), (x, y + h - 3), (x + w - 3, y + h - 3)):
        cv.rect(cx, cy, 3, 3, C["gold_dk"])
        cv.px(cx, cy, C["gold_hi"]); cv.px(cx + 1, cy, C["gold_lt"]); cv.px(cx, cy + 1, C["gold_lt"])
        cv.px(cx + 1, cy + 1, C["gold"])


def slot(cv, x, y, w, h, active=False):
    """Recessed square slot: iron rim, sunken dark well, gold corners."""
    cv.frame(x, y, w, h, C["ink"])
    cv.frame(x + 1, y + 1, w - 2, h - 2, C["iron"])
    cv.hline(x + 1, y + 1, w - 2, C["iron_lt"]); cv.vline(x + 1, y + 1, h - 2, C["iron_lt"])
    cv.hline(x + 2, y + h - 2, w - 3, C["iron_dk"]); cv.vline(x + w - 2, y + 2, h - 3, C["iron_dk"])
    cv.rect(x + 2, y + 2, w - 4, h - 4, C["ink"])
    cv.rect(x + 3, y + 3, w - 6, h - 6, C["abyss"])
    cv.dither(x + 3, y + h // 2, w - 6, h // 2 - 3, C["shadow"], 0.25)
    if active:
        cv.frame(x, y, w, h, C["gold_lt"])
        cv.frame(x + 1, y + 1, w - 2, h - 2, C["gold"])
        for px_, py_ in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
            cv.px(px_, py_, C["gold_hi"])
    else:
        for px_, py_ in ((x + 1, y + 1), (x + w - 2, y + 1), (x + 1, y + h - 2), (x + w - 2, y + h - 2)):
            cv.px(px_, py_, C["gold_lt"])


def key_label(cv, x, y, s, c=C["parchment"]):
    """Small hotkey tag: 3x5 font on an ink plate."""
    w = text_width(s, FONT3x5)
    cv.rect(x, y, w + 2, 7, C["ink"])
    cv.text(x + 1, y + 1, s, c, font=FONT3x5, shadow=None)
    return w + 2


def bar(cv, x, y, w, h, ratio, ramp="red", ticks=0, trim=True):
    """Horizontal liquid bar with banded shading and optional segment ticks."""
    r = RAMPS[ramp]
    cv.rect(x, y, w, h, C["ink"])
    fw = int(round((w - 2) * ratio))
    hi, mid, lo = r[-1], r[-2], r[-3]
    for j in range(h - 2):
        c = hi if j == 0 else (lo if j == h - 3 else mid)
        cv.hline(x + 1, y + 1 + j, fw, c)
    if h - 2 >= 3:
        cv.dither(x + 1, y + 2, fw, 1, r[-1], 0.25)
    # empty part
    cv.rect(x + 1 + fw, y + 1, w - 2 - fw, h - 2, C["abyss"])
    cv.dither(x + 1 + fw, y + 1, w - 2 - fw, h - 2, C["shadow"], 0.25)
    if fw > 0:
        cv.vline(x + fw, y + 1, h - 2, r[-1])
    if ticks:
        for k in range(1, ticks):
            tx = x + 1 + (w - 2) * k // ticks
            cv.vline(tx, y + 1, h - 2, C["ink"])
    if trim:
        cv.frame(x - 1, y - 1, w + 2, h + 2, C["gold_dk"])
        cv.hline(x - 1, y - 1, w + 2, C["gold"])


def label_box(cv, x, y, s, c, font=FONT5x7, pad=2, border=C["iron"], dim=True):
    """Ground-item style label: darkened backing plate + coloured text."""
    w = text_width(s, font) + pad * 2 + 1
    h = font["h"] + pad * 2
    if dim:
        cv.remap(x, y, w, h, DARKEN2)
    cv.dither(x, y, w, h, C["ink"], 0.5)
    cv.frame(x, y, w, h, border)
    cv.text(x + pad, y + pad, s, c, font=font, shadow=C["ink"])
    return w, h


# darkening LUT (two steps down each colour's own family) — used for overlays
def _build_darken(steps):
    lut = list(range(len(PALETTE)))
    fam = [RAMPS["stone"], [0, 1, 8, 9], [0, 1, 8, 10, 11, 12], [0, 1, 13, 14, 15],
           [0, 1, 16, 17, 18, 19], [0, 1, 20, 21, 22, 23], [0, 1, 24, 25, 26, 27],
           [0, 1, 30, 31], [0, 21, 22, 23, 28, 29]]
    for f in fam:
        for k, c in enumerate(f):
            if c in (28, 29) or f is not fam[-1] or True:
                lut[c] = f[max(0, k - steps)]
    return lut


DARKEN1 = _build_darken(1)
DARKEN2 = _build_darken(2)
DARKEN3 = _build_darken(3)


# --------------------------------------------------------------------------
# ORB
# --------------------------------------------------------------------------
def orb(cv, cx, cy, r, fill, ramp="red", seed=0, frame_w=6):
    """Liquid globe with sphere shading, wavy surface, dithered bands, glass
    highlight and an iron/gold frame ring. (cx,cy) = centre, r = glass radius."""
    L = RAMPS[ramp]                           # [ink, abyss, dk, mid, base, lt]
    liquid = L[2:]                            # 4 tones dark->light
    R = r + frame_w
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    dx, dy = xx - cx + 0.5, yy - cy + 0.5
    d = np.sqrt(dx * dx + dy * dy)
    # --- frame ring (iron, shaded by angle; gold inner trim) ---
    ring = (d <= R) & (d > r + 1)
    ang = np.arctan2(dy, dx)
    lit = np.cos(ang + math.pi * 0.75)        # 1 at top-left
    b = bayer(cv.h, cv.w)
    t = (lit * 0.5 + 0.5) * 2.99 + (b - 0.5) * 0.9
    tone = np.clip(t.astype(int), 0, 2)
    iron = np.array([C["iron_dk"], C["iron"], C["iron_lt"]])
    cv.a[ring] = iron[tone[ring]]
    cv.a[ring & (np.abs(d - (r + 3)) < 0.75)] = C["gold"]
    cv.a[ring & (np.abs(d - (r + 3)) < 0.75) & (lit > 0.2)] = C["gold_lt"]
    cv.a[ring & (np.abs(d - (r + 3)) < 0.75) & (lit < -0.6)] = C["gold_dk"]
    cv.a[(d <= R + 1) & (d > R)] = C["ink"]
    cv.a[(d <= r + 1) & (d > r)] = C["ink"]
    # rivets on the ring
    for k in range(12):
        a = k * math.pi / 6 + math.pi / 12
        rx, ry = int(round(cx + math.cos(a) * (R - 1.5) - 0.5)), int(round(cy + math.sin(a) * (R - 1.5) - 0.5))
        rivet(cv, rx, ry)
    # --- glass interior ---
    inside = d <= r
    level_y = cy + r - 2 * r * fill
    wave = np.sin(xx * 0.55 + seed) * 0.8
    liq = inside & (yy >= level_y + wave)
    nx, ny = dx / r, dy / r
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    shade = (-0.45 * nx - 0.35 * ny + 0.82 * nz)          # lambert-ish from top-left
    swirl = np.sin(xx * 0.31 + yy * 0.47 + seed) * np.sin(yy * 0.23 - xx * 0.17) * 0.18
    s = np.clip(shade * 0.95 + swirl, 0, 1) * 3.2 + (b - 0.5) * 0.8
    st = np.clip(s.astype(int), 0, 3)
    lq = np.array(liquid)
    cv.a[liq] = lq[st[liq]]
    # surface: bright meniscus line + slightly lighter band below
    surf = inside & (yy >= level_y + wave) & (yy < level_y + wave + 1)
    cv.a[surf] = liquid[3]
    surf2 = inside & (yy >= level_y + wave + 1) & (yy < level_y + wave + 3) & (b < 0.5)
    cv.a[surf2] = liquid[2]
    # empty glass: near black with dim tint toward bottom of empty area
    empty = inside & ~liq
    cv.a[empty] = C["ink"]
    cv.a[empty & (b < 0.5 * np.clip(nz, 0, 1) * 0.6)] = L[1]
    cv.a[empty & (b < 0.12) & (nz > 0.6)] = L[2]
    # rim shadow inside glass
    cv.a[inside & (d > r - 1.2) & (lit < 0.3)] = C["ink"]
    # reflected light at bottom-right
    rim = inside & (d > r - 2.5) & (d <= r - 1.2) & (lit < -0.55) & (b < 0.6)
    cv.a[rim] = liquid[3]
    # glass highlight crescent top-left + specular dots
    cres = inside & (d > r - 5) & (d < r - 2.6) & (lit > 0.82)
    cv.a[cres & (b < 0.75)] = C["parchment"]
    cres2 = inside & (d > r - 6) & (d < r - 1.8) & (lit > 0.55) & ~cres
    cv.a[cres2 & (b < 0.30)] = C["parchment"]
    hx, hy = int(cx - r * 0.38), int(cy - r * 0.55)
    cv.rect(hx, hy, 3, 2, C["parchment"]); cv.px(hx + 3, hy + 1, C["parchment"])
    cv.px(hx - 1, hy + 2, C["parchment"])
    cv.px(int(cx + r * 0.42), int(cy - r * 0.42), C["parchment"])


# --------------------------------------------------------------------------
# ICONS
# --------------------------------------------------------------------------
def _icon_bg(cv, x, y, s, c_dark, c_mid, seed=0):
    cv.rect(x, y, s, s, C["abyss"])
    yy, xx = np.mgrid[0:s, 0:s]
    d = np.sqrt((xx - s / 2 + 0.5) ** 2 + (yy - s / 2 + 0.5) ** 2) / (s * 0.6)
    b = bayer(s, s, x, y)
    sub = cv.a[y:y + s, x:x + s]
    sub[(1 - d) * 0.9 > b] = c_dark
    sub[(1 - d) * 0.55 > b + 0.25] = c_mid


def icon_fireball(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["blood"], C["red_dk"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    cv.poly([P(1, 21), P(9, 8), P(16, 11), P(13, 15)], C["red"])
    cv.poly([P(3, 19), P(10, 9), P(15, 12)], C["red_lt"])
    cv.poly([P(6, 16), P(11, 10), P(14, 12)], C["ember"])
    cx, cy = x + 13.5 * f, y + 8.5 * f
    cv.disc(cx, cy, 6.2 * f, C["red_lt"])
    cv.disc(cx - 0.3, cy + 0.3, 4.6 * f, C["ember"])
    cv.disc(cx - 0.6, cy + 0.6, 3.0 * f, C["flame"])
    cv.disc(cx - 0.8, cy + 0.8, 1.2 * f, C["parchment"])
    for (a, b) in ((19, 3), (20, 9), (16, 2), (8, 4)):
        cv.px(int(x + a * f), int(y + b * f), C["flame"])


def icon_icebolt(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["navy"], C["blue_dk"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    cv.poly([P(2, 20), P(15, 4), P(20, 2), P(18, 7)], C["blue_dk"])
    cv.poly([P(3, 19), P(15, 5), P(19, 3), P(17, 6)], C["blue"])
    cv.poly([P(5, 17), P(15, 5), P(19, 3)], C["blue_lt"])
    cv.line(int(x + 14 * f), int(y + 6 * f), int(x + 19 * f), int(y + 3 * f), C["parchment"])
    for (a, b) in ((6, 6), (16, 15), (4, 11)):
        ax, ay = int(x + a * f), int(y + b * f)
        cv.px(ax, ay, C["parchment"])
        for dx_, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.px(ax + dx_, ay + dy_, C["blue_lt"])


def icon_bash(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["earth_dk"], C["gold_dk"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    # impact burst
    cx, cy = x + 14 * f, y + 7 * f
    pts = []
    for k in range(16):
        a = k * math.pi / 8
        rr = (8.5 if k % 2 == 0 else 3.5) * f
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    cv.poly(pts, C["ember"])
    cv.disc(cx, cy, 2.5 * f, C["flame"])
    # handle
    cv.poly([P(2, 19), P(4, 21), P(13, 11), P(11, 9)], C["earth"])
    cv.line(int(x + 3 * f), int(y + 19 * f), int(x + 11 * f), int(y + 10 * f), C["gold"])
    # flanged mace head
    cv.poly([P(9, 5), P(14, 3), P(18, 8), P(15, 13), P(10, 11)], C["iron"], outline=C["ink"])
    cv.poly([P(10, 6), P(14, 4), P(15, 7), P(11, 9)], C["iron_lt"])
    cv.px(int(x + 12 * f), int(y + 5 * f), C["parchment"])


def icon_holyshield(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["gold_dk"], C["gold"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    sh = [P(4, 3), P(18, 3), P(18, 11), P(11, 20), P(4, 11)]
    cv.poly(sh, C["gold_lt"], outline=C["ink"])
    cv.poly([P(6, 5), P(16, 5), P(16, 11), P(11, 17), P(6, 11)], C["blue_dk"])
    cv.poly([P(6, 5), P(11, 5), P(11, 17), P(6, 11)], C["blue"])
    cv.rect(int(x + 10 * f), int(y + 6 * f), max(2, int(2 * f)), int(10 * f), C["gold_hi"])
    cv.rect(int(x + 7 * f), int(y + 9 * f), int(8 * f), max(2, int(2 * f)), C["gold_hi"])
    cv.px(int(x + 5 * f), int(y + 4 * f), C["parchment"])


def icon_teleport(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["violet_dk"], C["violet_dk"])
    f = s / 22.0
    cx, cy = x + 11 * f, y + 11.5 * f
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    e = ((xx + 0.5 - cx) / (6.5 * f)) ** 2 + ((yy + 0.5 - cy) / (8.5 * f)) ** 2
    box = (xx >= x) & (xx < x + s) & (yy >= y) & (yy < y + s)
    cv.a[box & (e <= 1.0)] = C["violet"]
    cv.a[box & (e <= 0.62)] = C["blue_lt"]
    cv.a[box & (e <= 0.42)] = C["violet_dk"]
    cv.a[box & (e <= 0.42) & (bayer(cv.h, cv.w) < 0.3)] = C["violet"]
    cv.a[box & (e > 1.0) & (e <= 1.25)] = C["ink"]
    # traveller silhouette stepping through
    sx, sy = int(cx), int(cy - 4 * f)
    cv.rect(sx - 1, sy, 3, 3, C["parchment"])
    cv.rect(sx - 2, sy + 3, 5, int(5 * f), C["parchment"])
    cv.px(sx - 2, sy + 3 + int(5 * f), C["parchment"]); cv.px(sx + 2, sy + 3 + int(5 * f), C["parchment"])
    for (a_, b_) in ((3, 4), (18, 17), (17, 3), (4, 17), (19, 10)):
        px_, py_ = int(x + a_ * f), int(y + b_ * f)
        cv.px(px_, py_, C["parchment"])
        cv.px(px_ + 1, py_, C["violet"]); cv.px(px_ - 1, py_, C["violet"])
        cv.px(px_, py_ + 1, C["violet"]); cv.px(px_, py_ - 1, C["violet"])


def icon_whirlwind(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["iron_dk"], C["iron_dk"])
    f = s / 22.0
    cx, cy = x + 11 * f, y + 12 * f
    # wind arcs (3 bands, 2px thick, open spiral)
    for k_, (rr, c) in enumerate(((9.0, C["iron"]), (6.6, C["iron_lt"]), (4.2, C["parchment"]))):
        for j in range(90):
            a = j / 90 * math.pi * 1.25 + k_ * 2.1
            for dr in (0, 0.8):
                cv.px(int(cx + math.cos(a) * (rr + dr) * f), int(cy + math.sin(a) * (rr + dr) * f * 0.55), c)
    # spinning blade in the eye of the storm
    bx = int(cx)
    cv.rect(bx, int(y + 2 * f), 1, int(12 * f), C["parchment"])
    cv.rect(bx + 1, int(y + 3 * f), 1, int(11 * f), C["iron_lt"])
    cv.rect(bx - 2, int(y + 14 * f), 6, 1, C["gold_lt"])
    cv.rect(bx, int(y + 15 * f), 2, int(3 * f), C["earth"])
    cv.px(bx, int(y + 18 * f), C["gold_lt"]); cv.px(bx + 1, int(y + 18 * f), C["gold_lt"])


def icon_sword(cv, x, y, s=22):
    _icon_bg(cv, x, y, s, C["iron_dk"], C["iron"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    cv.poly([P(6, 14), P(17, 2), P(20, 2), P(20, 5), P(9, 16)], C["iron_lt"], outline=C["ink"])
    cv.line(int(x + 8 * f), int(y + 14 * f), int(x + 19 * f), int(y + 3 * f), C["parchment"])
    cv.poly([P(3, 12), P(5, 10), P(12, 17), P(10, 19)], C["gold_lt"], outline=C["ink"])
    cv.poly([P(4, 17), P(6, 15), P(8, 17), P(6, 19)], C["earth"], outline=C["ink"])
    cv.disc(x + 3.5 * f, y + 19.5 * f, 1.6 * f, C["gold_lt"])
    cv.px(int(x + 3 * f), int(y + 19 * f), C["gold_hi"])


SKILL_ICONS = {
    "fireball": icon_fireball, "icebolt": icon_icebolt, "bash": icon_bash,
    "holyshield": icon_holyshield, "teleport": icon_teleport,
    "whirlwind": icon_whirlwind, "sword": icon_sword,
}

# ---- small direct-palette menu icons (12x12) ------------------------------
_ML = {"k": C["ink"], "d": C["iron_dk"], "I": C["iron"], "j": C["iron_lt"], "g": C["gold"],
       "y": C["gold_lt"], "Y": C["gold_hi"], "w": C["parchment"], "b": C["bone"],
       "B": C["stone_lt"], "r": C["red"], "R": C["red_lt"], "e": C["earth"],
       "E": C["gold_dk"], "u": C["blue"], "U": C["blue_lt"], "x": C["red_dk"]}
MENU_ICONS = {
    "character": [
        "....kkkk....",
        "..kkjjIIkk..",
        ".kjjIIIIIdk.",
        ".kjIIIIIIdk.",
        "kjIIgyygIIdk",
        "kkkkkkkkkkkk",
        "kIIkIIIIkIdk",
        "kIIIIkkIIIdk",
        ".kIIkk.kIdk.",
        ".kIdk...kdk.",
        "..kk.....k..",
        "............"],
    "inventory": [
        "...kkkkk....",
        "...keyek....",
        "....kek.....",
        "..kkeeekk...",
        ".keyyeeeek..",
        "keyeeeeeeek.",
        "keyeekkeeek.",
        "keeekYgkeek.",
        "keeeekkeeEk.",
        "keeeeeeeeEk.",
        ".kEeeeeeEk..",
        "..kkkkkkk..."],
    "skills": [
        ".....kkk....",
        "....kYyyk...",
        "....kygEk...",
        ".....kEk....",
        "......k.....",
        "..kkkkkkkkk.",
        "..k.......k.",
        ".kkk.....kkk",
        "kRrxk...kUuk",
        "krrxk...kuuk",
        ".kkk.....kkk",
        "............"],
    "map": [
        ".kkkkkkkkkk.",
        "kbwwwwwwwwbk",
        ".kkkkkkkkkk.",
        ".kwbbwbbbbk.",
        ".kbbkbbbRbk.",
        ".kbkbbbbRRk.",
        ".kbbkkbbbbk.",
        ".kbbbbkbkbk.",
        ".kwbbbbbkbk.",
        ".kkkkkkkkkk.",
        "kbwwwwwwwwbk",
        ".kkkkkkkkkk."],
    "menu": [
        "............",
        ".kkkkkkkkkk.",
        "kYyyyyyyyygk",
        ".kkkkkkkkkk.",
        "............",
        ".kkkkkkkkkk.",
        "kYyyyyyyyygk",
        ".kkkkkkkkkk.",
        "............",
        ".kkkkkkkkkk.",
        "kYyyyyyyyygk",
        ".kkkkkkkkkk."],
}


def menu_button(cv, x, y, s, icon, key):
    """Stone/metal square button with pixel icon and key tag."""
    cv.rect(x, y, s, s, C["stone"])
    stone_fill(cv, x + 1, y + 1, s - 2, s - 2, seed=hash(icon) & 0xFF, base=4, brick=(s, s))
    bevel(cv, x, y, s, s, light=C["stone_lt"], dark=C["shadow"])
    cv.frame(x + 2, y + 2, s - 4, s - 4, C["iron_dk"])
    cv.rect(x + 3, y + 3, s - 6, s - 6, C["shadow"])
    rows = MENU_ICONS[icon]
    cv.stamp(rows, _ML, x + (s - 12) // 2, y + (s - 12) // 2 - 1)
    corner_studs(cv, x, y, s, s)
    w = text_width(key, FONT3x5) + 2
    key_label(cv, x + s - w + 1, y + s - 5, key, C["gold_hi"])


# ---- potions (12x15) ------------------------------------------------------
_POTION = [
    "....kkkk....",
    "....kEek....",
    "....kEek....",
    "...kkkkkk...",
    "....kgwk....",
    "....kg3k....",
    "...kk23kk...",
    "..kw23321k..",
    ".kw3322221k.",
    ".kw3222221k.",
    ".k32222211k.",
    ".k22222211k.",
    ".k12222111k.",
    "..k111111k..",
    "...kkkkkk...",
]


def potion(cv, x, y, kind="health"):
    r = {"health": RAMPS["red"], "mana": RAMPS["blue"],
         "rejuv": [0, 1, 30, 30, 31, 27]}[kind]
    lg = {"k": C["ink"], "E": C["gold"], "e": C["gold_dk"], "g": C["stone_lt"], "w": C["parchment"],
          "1": r[2], "2": r[3] if kind != "rejuv" else 31, "3": r[5] if kind != "health" else r[5]}
    if kind == "rejuv":
        lg.update({"1": 30, "2": 31, "3": 27})
    if kind == "health":
        lg.update({"1": C["red_dk"], "2": C["red"], "3": C["red_lt"]})
    if kind == "mana":
        lg.update({"1": C["blue_dk"], "2": C["blue"], "3": C["blue_lt"]})
    cv.stamp(_POTION, lg, x, y)


# --------------------------------------------------------------------------
# WINDOW WIDGETS (stage 2): windows, buttons, fields, tooltips, cursor
# --------------------------------------------------------------------------
def inset(cv, x, y, w, h, fill=C["abyss"], texture=True):
    """Sunken dark panel: ink rim, dark top/left inner edge, lit bottom/right."""
    cv.rect(x, y, w, h, fill)
    if texture:
        cv.dither(x + 1, y + 1, w - 2, h - 2, C["shadow"], 0.12)
    cv.frame(x, y, w, h, C["ink"])
    cv.hline(x + 1, y + h - 1, w - 1, C["stone"]); cv.vline(x + w - 1, y + 1, h - 1, C["stone"])
    cv.hline(x + 1, y + 1, w - 2, C["ink"])


def close_button(cv, x, y, s=13, hover=False):
    cv.rect(x, y, s, s, C["ink"])
    cv.rect(x + 1, y + 1, s - 2, s - 2, C["red_dk"] if hover else C["iron"])
    cv.hline(x + 1, y + 1, s - 2, C["red"] if hover else C["iron_lt"]); cv.vline(x + 1, y + 1, s - 2, C["red"] if hover else C["iron_lt"])
    cv.hline(x + 2, y + s - 2, s - 3, C["iron_dk"]); cv.vline(x + s - 2, y + 2, s - 3, C["iron_dk"])
    for i in range(s - 8):
        for c, o in ((C["ink"], 1), (C["red_lt"] if not hover else C["flame"], 0)):
            cv.px(x + 4 + i, y + 4 + i + o, c); cv.px(x + s - 5 - i, y + 4 + i + o, c)
    corner_studs(cv, x - 1, y - 1, s + 2, s + 2)


def title_plate(cv, cx, y, title, font=FONT5x7):
    tw = text_width(title, font)
    w, h = tw + 28, font["h"] + 7
    x = cx - w // 2
    cv.poly([(x, y + h // 2), (x + 6, y), (x + w - 7, y), (x + w - 1, y + h // 2), (x + w - 7, y + h - 1), (x + 6, y + h - 1)],
            C["shadow"], outline=C["ink"])
    cv.line(x + 1, y + h // 2, x + 6, y + 1, C["gold_lt"]); cv.hline(x + 6, y + 1, w - 13, C["gold_lt"])
    cv.line(x + w - 7, y + 1, x + w - 2, y + h // 2, C["gold"])
    cv.line(x + 1, y + h // 2, x + 6, y + h - 2, C["gold_dk"]); cv.hline(x + 6, y + h - 2, w - 13, C["gold_dk"])
    cv.line(x + w - 2, y + h // 2, x + w - 7, y + h - 2, C["gold_dk"])
    for dx in (3, w - 4):
        cv.px(x + dx, y + h // 2, C["red_lt"])
    cv.text_c(cx + 1, y + 4, title, C["gold_hi"], font=font, outline=C["ink"])
    return w, h


def window(cv, x, y, w, h, title=None, close=True, border=6, seed=11, close_hover=False):
    """Gothic window: carved stone border, worn gold trim, dark inner field,
    corner studs, title plate and close button. Returns inner rect (x,y,w,h)."""
    cv.rect(x, y, w, h, C["ink"])
    stone_fill(cv, x + 1, y + 1, w - 2, h - 2, seed=seed, base=3, brick=(20, 8))
    bevel(cv, x, y, w, h, light=C["stone_lt"], dark=C["shadow"])
    ix, iy, iw, ih = x + border, y + border, w - 2 * border, h - 2 * border
    gold_trim(cv, ix - 2, iy - 2, iw + 4, ih + 4)
    cv.rect(ix, iy, iw, ih, C["abyss"])
    cv.dither(ix, iy, iw, ih, C["shadow"], 0.18)
    # inner vignette: darker toward edges
    cv.dither(ix, iy, iw, 3, C["ink"], 0.5); cv.dither(ix, iy, 3, ih, C["ink"], 0.5)
    cv.dither(ix, iy + ih - 3, iw, 3, C["ink"], 0.3); cv.dither(ix + iw - 3, iy, 3, ih, C["ink"], 0.3)
    for (cx_, cy_) in ((x + 1, y + 1), (x + w - 8, y + 1), (x + 1, y + h - 8), (x + w - 8, y + h - 8)):
        cv.rect(cx_, cy_, 7, 7, C["ink"])
        cv.rect(cx_ + 1, cy_ + 1, 5, 5, C["gold"])
        cv.rect(cx_ + 1, cy_ + 1, 4, 1, C["gold_hi"]); cv.rect(cx_ + 1, cy_ + 1, 1, 4, C["gold_lt"])
        cv.rect(cx_ + 2, cy_ + 5, 4, 1, C["gold_dk"]); cv.rect(cx_ + 5, cy_ + 2, 1, 4, C["gold_dk"])
        cv.px(cx_ + 3, cy_ + 3, C["red_lt"])
    if title:
        title_plate(cv, x + w // 2, y - 1, title)
    if close:
        close_button(cv, x + w - border - 15, y + border + 2, hover=close_hover)
    return ix, iy, iw, ih


def section_title(cv, x, y, w, text, c=C["gold_lt"], font=FONT5x7):
    tw = text_width(text, font)
    cx = x + w // 2
    cv.text_c(cx + 1, y, text, c, font=font, outline=C["ink"])
    ly = y + font["h"] // 2
    for (a, b) in ((x, cx - tw // 2 - 4), (cx + tw // 2 + 4, x + w)):
        if b > a:
            cv.hline(a, ly, b - a, C["gold_dk"]); cv.hline(a, ly - 1, b - a, C["ink"])
            cv.px(a, ly, C["gold_lt"]); cv.px(b - 1, ly, C["gold_lt"])


def text_button(cv, x, y, w, h, label, state="normal", font=FONT5x7, seed=5):
    """Stone/iron button. state: normal | hover | pressed | disabled."""
    cv.rect(x, y, w, h, C["ink"])
    base = 4 if state == "hover" else 3
    stone_fill(cv, x + 1, y + 1, w - 2, h - 2, seed=seed, base=base, brick=(w, h))
    if state == "pressed":
        bevel(cv, x, y, w, h, light=C["stone"], dark=C["ink"], inset=True)
    else:
        bevel(cv, x, y, w, h, light=C["stone_lt"] if state != "hover" else C["bone"], dark=C["shadow"])
    trim = {"hover": C["gold_lt"], "disabled": C["iron"], "pressed": C["gold"]}.get(state, C["gold"])
    cv.frame(x + 2, y + 2, w - 4, h - 4, trim)
    if state == "hover":
        cv.hline(x + 3, y + 2, w - 6, C["gold_hi"])
        cv.dither(x + 3, y + h - 6, w - 6, 3, C["ember"], 0.25)
        cv.dither(x + 3, y + h - 4, w - 6, 1, C["flame"], 0.25)
    corner_studs(cv, x, y, w, h)
    tc = {"hover": C["gold_hi"], "disabled": C["stone_lt"], "pressed": C["gold_lt"]}.get(state, C["parchment"])
    off = 1 if state == "pressed" else 0
    cv.text_c(x + w // 2 + 1 + off, y + (h - font["h"]) // 2 + off, label, tc, font=font, outline=C["ink"])
    if state == "hover":   # flame pointers either side
        for sx, d in ((x - 5, 1), (x + w + 4, -1)):
            cy = y + h // 2
            for i in range(4):
                cv.vline(sx + i * d, cy - (3 - i), 2 * (3 - i) + 1, C["ember"] if i < 2 else C["flame"])
            cv.px(sx + 3 * d, cy, C["parchment"])


def plus_button(cv, x, y, s=11, active=True):
    cv.rect(x, y, s, s, C["ink"])
    cv.rect(x + 1, y + 1, s - 2, s - 2, C["red_dk"] if active else C["stone_dk"])
    cv.hline(x + 1, y + 1, s - 2, C["red"] if active else C["stone"]); cv.vline(x + 1, y + 1, s - 2, C["red"] if active else C["stone"])
    cv.frame(x, y, s, s, C["gold_lt"] if active else C["iron"])
    c = C["gold_hi"] if active else C["stone_lt"]
    m = s // 2
    cv.rect(x + 3, y + m, s - 6, 1, c); cv.rect(x + m, y + 3, 1, s - 6, c)
    cv.px(x + m + 1, y + m + 1, C["ink"])


def stat_field(cv, x, y, w, h, label, value, lc=C["bone"], vc=C["parchment"], font=FONT5x7, vfont=None):
    inset(cv, x, y, w, h)
    ty = y + (h - font["h"]) // 2
    cv.text(x + 4, ty, label, lc, font=font, shadow=C["ink"])
    vf = vfont or font
    cv.text_r(x + w - 4, y + (h - vf["h"]) // 2, value, vc, font=vf, shadow=C["ink"])


def tooltip(cv, x, y, lines, pad=5, gap=2, anchor="tl", min_w=0):
    """D2-style item tooltip: darkened see-through plate, centred lines.
    lines: list of (text, colour[, font]). Returns (x, y, w, h)."""
    ws = [text_width(t[0], t[2] if len(t) > 2 else FONT5x7) for t in lines]
    hs = [(t[2] if len(t) > 2 else FONT5x7)["h"] for t in lines]
    w = max(max(ws) + pad * 2 + 1, min_w)
    h = sum(hs) + gap * (len(lines) - 1) + pad * 2
    if anchor == "tr":
        x -= w
    elif anchor == "bl":
        y -= h
    elif anchor == "br":
        x -= w; y -= h
    cv.remap(x, y, w, h, DARKEN3)
    cv.dither(x, y, w, h, C["ink"], 0.6)
    cv.frame(x, y, w, h, C["iron"])
    cv.frame(x + 1, y + 1, w - 2, h - 2, C["ink"])
    for (px_, py_) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(px_, py_, C["gold_lt"])
    yy = y + pad
    for t, ww, hh in zip(lines, ws, hs):
        f = t[2] if len(t) > 2 else FONT5x7
        if t[0]:
            cv.text(x + (w - ww) // 2, yy, t[0], t[1], font=f, shadow=C["ink"])
        yy += hh + gap
    return x, y, w, h


_CURSOR = [
    "kk..........",
    "kGk.........",
    "kGYk........",
    "kGYYk.......",
    "kGYyyk......",
    "kGYyyyk.....",
    "kGyyyyyk....",
    "kGyyyyggk...",
    "kGyyyggggk..",
    "kGyygkkkkkk.",
    "kGygk.......",
    "kGgk........",
    "kgk.........",
    "kk..........",
]


def cursor(cv, x, y):
    """Gilded gauntlet-tip arrow cursor (hotspot = top-left)."""
    cv.stamp(_CURSOR, {"k": C["ink"], "G": C["gold_hi"], "Y": C["gold_lt"], "y": C["gold"],
                       "g": C["gold_dk"]}, x, y)


def coin_icon(cv, x, y):
    for (cx, cy) in ((3, 7), (6, 5), (2, 4), (5, 2)):
        cv.rect(x + cx - 2, y + cy, 6, 2, C["gold_dk"])
        cv.rect(x + cx - 2, y + cy - 1, 6, 2, C["gold_lt"])
        cv.px(x + cx - 1, y + cy - 1, C["gold_hi"])
        cv.px(x + cx + 3, y + cy, C["ink"])


# --------------------------------------------------------------------------
# PALETTE SWITCHING (themes) — mutates module state in place so that
# `from pixelkit import C` references stay valid.
# --------------------------------------------------------------------------
def use_palette(entries, ramps, aliases=None, families=None):
    global PALETTE, RGB, RAMPS, RAMP_NAMES, RAMP_ID, RAMP_LUT, RAMP_LEN, DARKEN1, DARKEN2, DARKEN3
    PALETTE[:] = entries
    C.clear()
    C.update({n: i for i, (n, _) in enumerate(entries)})
    for a, b in (aliases or {}).items():
        C[a] = C[b] if isinstance(b, str) else b
    RGB = np.array([[int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)] for _, h in entries], dtype=np.uint8)
    RAMPS = {k: [C[c] if isinstance(c, str) else c for c in v] for k, v in ramps.items()}
    RAMP_NAMES = list(RAMPS)
    RAMP_ID = {n: i for i, n in enumerate(RAMP_NAMES)}
    mx = max(len(r) for r in RAMPS.values())
    RAMP_LUT = np.zeros((len(RAMPS), mx), dtype=np.uint8)
    for n, r in RAMPS.items():
        RAMP_LUT[RAMP_ID[n], :len(r)] = r
        RAMP_LUT[RAMP_ID[n], len(r):] = r[-1]
    RAMP_LEN = np.array([len(RAMPS[n]) for n in RAMP_NAMES])
    if families:
        fam = [[C[c] if isinstance(c, str) else c for c in f] for f in families]
        def build(steps):
            lut = list(range(len(entries)))
            for f in fam:
                for i, c in enumerate(f):
                    lut[c] = f[max(0, i - steps)]
            return lut
        DARKEN1, DARKEN2, DARKEN3 = build(1), build(2), build(3)


def palette_png(path, cols=8, sw=32):
    rows = (len(PALETTE) + cols - 1) // cols
    cv = Canvas(cols * sw, rows * (sw + 10), fill=C["ink"])
    for i, (name, hx) in enumerate(PALETTE):
        x, y = (i % cols) * sw, (i // cols) * (sw + 10)
        cv.frame(x + 1, y + 1, sw - 2, sw - 2, 6)
        cv.rect(x + 2, y + 2, sw - 4, sw - 4, i)
        cv.text(x + 2, y + sw + 2, str(i), 7, font=FONT3x5, shadow=None)
    cv.save(path, scale=4)


# --------------------------------------------------------------------------
# MATCANVAS — draw material-letter sprites with primitives instead of typing
# --------------------------------------------------------------------------
class MatCanvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.a = np.full((h, w), ".", dtype="<U1")

    def _mask(self, drawfn):
        m = Image.new("L", (self.w, self.h), 0)
        drawfn(ImageDraw.Draw(m))
        return np.array(m, dtype=bool)

    def poly(self, pts, ch):
        self.a[self._mask(lambda d: d.polygon([(round(x), round(y)) for x, y in pts], fill=1))] = ch
        return self

    def ellipse(self, cx, cy, rx, ry, ch):
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        self.a[((xx - cx) / max(rx, 0.5)) ** 2 + ((yy - cy) / max(ry, 0.5)) ** 2 <= 1.0] = ch
        return self

    def line(self, x0, y0, x1, y1, ch, w=1):
        self.a[self._mask(lambda d: d.line([(round(x0), round(y0)), (round(x1), round(y1))], fill=1, width=w))] = ch
        return self

    def rect(self, x, y, w, h, ch):
        self.a[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = ch
        return self

    def px(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = ch
        return self

    def where(self, ch_from, ch_to, mask):
        self.a[(self.a == ch_from) & mask] = ch_to
        return self

    def rows(self):
        return ["".join(r) for r in self.a]


# --------------------------------------------------------------------------
# ORB LIQUID (frame-agnostic) — reusable by any theme
# --------------------------------------------------------------------------
def orb_liquid(cv, cx, cy, r, fill, tones, empty=(0, 1), glass=None, seed=0.0):
    """tones: 4 palette indices dark->light. empty: (base, tint) for empty glass.
    glass: highlight colour (defaults to the lightest neutral 7)."""
    glass = 7 if glass is None else glass
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    dx, dy = xx - cx + 0.5, yy - cy + 0.5
    d = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    lit = np.cos(ang + math.pi * 0.75)
    b = bayer(cv.h, cv.w)
    inside = d <= r
    level_y = cy + r - 2 * r * fill
    wave = np.sin(xx * 0.55 + seed) * 0.8
    liq = inside & (yy >= level_y + wave)
    nx, ny = dx / r, dy / r
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    shade = (-0.45 * nx - 0.35 * ny + 0.82 * nz)
    swirl = np.sin(xx * 0.31 + yy * 0.47 + seed) * np.sin(yy * 0.23 - xx * 0.17) * 0.18
    s = np.clip(shade * 0.95 + swirl, 0, 1) * 3.2 + (b - 0.5) * 0.8
    st = np.clip(s.astype(int), 0, 3)
    lq = np.array(tones)
    cv.a[liq] = lq[st[liq]]
    cv.a[inside & (yy >= level_y + wave) & (yy < level_y + wave + 1)] = tones[3]
    cv.a[inside & (yy >= level_y + wave + 1) & (yy < level_y + wave + 3) & (b < 0.5)] = tones[2]
    em = inside & ~liq
    cv.a[em] = empty[0]
    cv.a[em & (b < 0.3 * np.clip(nz, 0, 1))] = empty[1]
    cv.a[inside & (d > r - 1.2) & (lit < 0.3)] = empty[0]
    cv.a[inside & (d > r - 2.5) & (d <= r - 1.2) & (lit < -0.55) & (b < 0.6)] = tones[3]
    cres = inside & (d > r - 5) & (d < r - 2.6) & (lit > 0.82)
    cv.a[cres & (b < 0.75)] = glass
    cres2 = inside & (d > r - 6) & (d < r - 1.8) & (lit > 0.55) & ~cres
    cv.a[cres2 & (b < 0.30)] = glass
    hx, hy = int(cx - r * 0.38), int(cy - r * 0.55)
    cv.rect(hx, hy, 3, 2, glass); cv.px(hx + 3, hy + 1, glass); cv.px(hx - 1, hy + 2, glass)
    cv.px(int(cx + r * 0.42), int(cy - r * 0.42), glass)

"""
Theme «Русь / Гардарики» — palette v2 + carved-wood / forged-iron / bronze UI
widgets with Slavic ornament (плетёнка, верёвочный бордюр, громовник-розетка),
serpent-framed orbs, themed skill & menu icons.

Call theme_rus.activate() before drawing (switches pixelkit to palette v2).
Reuses generic pixelkit widgets through colour-name aliases.
"""
import json
import math
import numpy as np
import pixelkit as pk
from pixelkit import C, Canvas, FONT3x5
from fonts_ru import FONT_RU, FONT_USTAV

PALETTE_V2 = [
    ("ink", "#0d0b0a"), ("night", "#1a1c20"), ("slate_dk", "#2a2f34"), ("slate", "#3f474c"),
    ("slate_lt", "#5e6a70"), ("mist", "#8a9aa2"), ("birch", "#cbc4ae"), ("linen", "#f2ecd8"),
    ("wood_dk", "#2b1b10"), ("wood", "#4b2f1b"), ("wood_md", "#714829"), ("wood_lt", "#a8703f"),
    ("bronze_dk", "#5c3b14"), ("bronze", "#9a6826"), ("bronze_lt", "#d39a45"), ("bronze_hi", "#f2d48a"),
    ("pine_dk", "#0f1f1a"), ("pine", "#1c3a2b"), ("moss", "#3a5a31"), ("moss_lt", "#708440"),
    ("sea_dk", "#1b2b3c"), ("sea", "#34506a"), ("red_dk", "#4c0f10"), ("red", "#8f1d1a"),
    ("red_lt", "#d4432c"), ("blue_dk", "#16306f"), ("blue", "#2f5fc6"), ("blue_lt", "#8db6ee"),
    ("ember", "#e6862b"), ("flame", "#ffd65c"), ("nebyl_dk", "#1d5a40"), ("nebyl", "#8af27e"),
]
DESCR = {
    "ink": "outlines", "night": "deepest cool shadow", "slate_dk": "iron dark / shadow",
    "slate": "iron / stone", "slate_lt": "iron light", "mist": "northern sky, silver",
    "birch": "birch bark, bone", "linen": "text white, highlights",
    "wood_dk": "wood shadow", "wood": "wood", "wood_md": "wood mid", "wood_lt": "wood light / skin",
    "bronze_dk": "bronze dark", "bronze": "bronze", "bronze_lt": "bronze light", "bronze_hi": "bronze shine",
    "pine_dk": "forest dark", "pine": "spruce", "moss": "moss", "moss_lt": "dry grass",
    "sea_dk": "sea dark", "sea": "sea", "red_dk": "blood dark", "red": "red cloak / life",
    "red_lt": "red light", "blue_dk": "mana dark", "blue": "mana", "blue_lt": "mana light",
    "ember": "fire", "flame": "fire core", "nebyl_dk": "Небыль dark glow", "nebyl": "Небыль glow",
}
RAMPS_V2 = {
    "ink": ["ink"],
    "stone": ["ink", "night", "slate_dk", "slate", "slate_lt", "mist", "birch", "linen"],
    "iron": ["ink", "night", "slate_dk", "slate", "slate_lt", "mist", "linen"],
    "birch": ["ink", "slate_dk", "slate_lt", "mist", "birch", "linen"],
    "wood": ["ink", "wood_dk", "wood", "wood_md", "wood_lt", "birch"],
    "skin": ["ink", "wood_dk", "wood_md", "wood_lt", "bronze_lt", "bronze_hi"],
    "bronze": ["ink", "wood_dk", "bronze_dk", "bronze", "bronze_lt", "bronze_hi"],
    "grass": ["ink", "pine_dk", "pine", "moss", "moss_lt", "bronze_lt"],
    "earth": ["ink", "wood_dk", "wood", "wood_md", "wood_lt"],
    "pine": ["ink", "pine_dk", "pine", "moss", "moss_lt"],
    "sea": ["ink", "night", "sea_dk", "sea", "slate_lt", "mist", "birch"],
    "red": ["ink", "red_dk", "red", "red_lt", "ember"],
    "blue": ["ink", "sea_dk", "blue_dk", "blue", "blue_lt"],
    "fire": ["red", "red_lt", "ember", "flame", "linen"],
    "nebyl": ["ink", "pine_dk", "nebyl_dk", "nebyl", "linen"],
    "fur": ["ink", "night", "wood_dk", "slate_dk", "slate", "slate_lt", "mist"],
    "ghoul": ["ink", "slate_dk", "slate", "slate_lt", "mist", "birch"],
}
ALIASES = {  # v1 widget colour names -> v2 entries
    "abyss": "night", "shadow": "slate_dk", "stone_dk": "slate", "stone": "slate_lt",
    "stone_lt": "mist", "bone": "birch", "parchment": "linen", "earth_dk": "wood_dk",
    "earth": "wood", "moss_dk": "pine", "iron_dk": "slate_dk", "iron": "slate",
    "iron_lt": "mist", "gold_dk": "bronze_dk", "gold": "bronze", "gold_lt": "bronze_lt",
    "gold_hi": "bronze_hi", "blood": "red_dk", "navy": "sea_dk", "violet_dk": "nebyl_dk",
    "violet": "nebyl",
}
FAMILIES = [
    ["ink", "night", "slate_dk", "slate", "slate_lt", "mist", "birch", "linen"],
    ["ink", "wood_dk", "wood", "wood_md", "wood_lt"],
    ["ink", "wood_dk", "bronze_dk", "bronze", "bronze_lt", "bronze_hi"],
    ["ink", "pine_dk", "pine", "moss", "moss_lt"],
    ["ink", "night", "sea_dk", "sea"],
    ["ink", "red_dk", "red", "red_lt"],
    ["ink", "sea_dk", "blue_dk", "blue", "blue_lt"],
    ["red", "red_lt", "ember", "flame"],
    ["ink", "pine_dk", "nebyl_dk", "nebyl"],
]


def activate():
    pk.use_palette(PALETTE_V2, RAMPS_V2, ALIASES, FAMILIES)


def save_palette(png, js):
    pk.palette_png(png)
    with open(js, "w") as f:
        json.dump({"name": "gardariki_v2", "count": len(PALETTE_V2),
                   "colors": [{"index": i, "name": n, "hex": h, "use": DESCR[n]} for i, (n, h) in enumerate(PALETTE_V2)],
                   "ramps": RAMPS_V2}, f, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# MATERIAL FILLS & ORNAMENT
# --------------------------------------------------------------------------
def wood_planks(cv, x, y, w, h, seed=1, plank=8, vertical=False, tones=None, dark=False):
    """Carved plank surface: per-plank tone, streaky grain, seams, knots."""
    T = tones or [C["wood_dk"], C["wood"], C["wood_md"], C["wood_lt"]]
    for j in range(h):
        for i in range(w):
            a, b = (i, j) if not vertical else (j, i)
            row = b // plank
            lb = b % plank
            shift = int(pk.hash2(row, 3, seed) * 60)
            seg = (a + shift) // 71
            la = (a + shift) % 71
            t = pk.hash2(row, seg, seed)
            base = (1 if t < 0.55 else 2) - (1 if dark and t < 0.4 else 0)
            g = math.sin((a + shift) * 0.21 + row * 1.7 + math.sin((a + shift) * 0.05 + row) * 2.2 + lb * 0.9)
            c = base
            if g > 0.82:
                c = base - 1
            elif g < -0.92 and pk.hash2(i, j, seed + 5) < 0.5:
                c = base + 1
            if lb == 0:
                c = -1
            elif lb == 1:
                c = min(3, base + 1) if not dark else base
            elif lb == plank - 1:
                c = 0
            if la == 0:
                c = -1
            # knot
            kx, ky = int(pk.hash2(row, seg, seed + 9) * 60) + 4, plank // 2
            if pk.hash2(row, seg, seed + 4) < 0.35:
                dd = (la - kx) ** 2 + ((lb - ky) * 2) ** 2
                if dd <= 2:
                    c = 0
                elif dd <= 6:
                    c = min(3, base + 1)
            col = C["ink"] if c < 0 else T[max(0, min(3, c))]
            cv.px(x + i, y + j, col)


def rope(cv, x, y, w, light=None, mid=None, dark=None, vertical=False):
    """3-px twisted rope border (верёвочка)."""
    L = light or C["bronze_lt"]; M = mid or C["bronze"]; D = dark or C["bronze_dk"]
    pat = [[L, M, D, C["ink"]], [M, D, C["ink"], L], [D, C["ink"], L, M]]
    for i in range(w):
        for r in range(3):
            c = pat[r][(i + r) % 4]
            if vertical:
                cv.px(x + r, y + i, c)
            else:
                cv.px(x + i, y + r, c)


def interlace(cv, x, y, w, h=9, period=14, fg=None, bg=None):
    """Two-strand плетёнка band with over/under crossings."""
    hi, mid, lo = (fg or (C["bronze_hi"], C["bronze_lt"], C["bronze"]))
    cv.rect(x, y, w, h, bg if bg is not None else C["wood_dk"])
    amp = (h - 4) / 2.0
    mid_y = y + h / 2.0 - 0.5
    for i in range(w):
        ph = 2 * math.pi * i / period
        ya = mid_y + amp * math.sin(ph)
        yb = mid_y - amp * math.sin(ph)
        top_is_a = (int(i / (period / 2.0)) % 2) == 0
        order = (("b", yb), ("a", ya)) if top_is_a else (("a", ya), ("b", yb))
        for name, yy in order:
            yi = int(round(yy))
            cv.px(x + i, yi - 2, C["ink"]); cv.px(x + i, yi + 2, C["ink"])
            cv.px(x + i, yi - 1, hi); cv.px(x + i, yi, mid); cv.px(x + i, yi + 1, lo)
    cv.hline(x, y, w, C["ink"]); cv.hline(x, y + h - 1, w, C["ink"])


def rosette(cv, cx, cy, r, line=None, ring=True):
    """Six-petal громовник rosette (compass construction), engraved lines."""
    line = line if line is not None else C["bronze_lt"]
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    dO = np.hypot(xx - cx, yy - cy)
    m = np.zeros(dO.shape, bool)
    for k in range(6):
        a = k * math.pi / 3
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        d = np.hypot(xx - px, yy - py)
        m |= (np.abs(d - r) < 0.55) & (dO <= r)
    if ring:
        m |= np.abs(dO - r) < 0.6
    cv.a[m] = line


def bronze_corner(cv, x, y, sx=1, sy=1, n=5):
    for k in range(n):
        cv.px(x + k * sx, y, C["bronze_lt"] if k < n - 1 else C["bronze"])
        cv.px(x, y + k * sy, C["bronze_lt"] if k < n - 1 else C["bronze"])
    cv.px(x + sx, y + sy, C["bronze_hi"])
    cv.px(x + 2 * sx, y + sy, C["bronze"]); cv.px(x + sx, y + 2 * sy, C["bronze"])


def nail(cv, x, y):
    cv.px(x, y, C["mist"]); cv.px(x + 1, y, C["slate_lt"])
    cv.px(x, y + 1, C["slate_lt"]); cv.px(x + 1, y + 1, C["ink"])


def wood_slot(cv, x, y, w, h, active=False):
    """Recessed slot in a carved wooden frame with bronze corner fittings."""
    cv.frame(x, y, w, h, C["ink"])
    cv.frame(x + 1, y + 1, w - 2, h - 2, C["wood_md"])
    cv.hline(x + 1, y + 1, w - 2, C["wood_lt"]); cv.vline(x + 1, y + 1, h - 2, C["wood_lt"])
    cv.hline(x + 2, y + h - 2, w - 3, C["wood_dk"]); cv.vline(x + w - 2, y + 2, h - 3, C["wood_dk"])
    cv.rect(x + 2, y + 2, w - 4, h - 4, C["ink"])
    cv.rect(x + 3, y + 3, w - 6, h - 6, C["night"])
    cv.dither(x + 3, y + h // 2, w - 6, h // 2 - 3, C["slate_dk"], 0.25)
    if active:
        cv.frame(x, y, w, h, C["bronze_hi"])
        cv.frame(x + 1, y + 1, w - 2, h - 2, C["bronze_lt"])
    for (cx_, cy_, sx, sy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        bronze_corner(cv, cx_, cy_, sx, sy, 4)


def text_ru(cv, x, y, s, c, font=FONT_RU, outline=True, align="l"):
    w = pk.text_width(s, font)
    if align == "c":
        x -= w // 2
    elif align == "r":
        x -= w
    if outline:
        return cv.text(x, y, s, c, font=font, outline=C["ink"])
    return cv.text(x, y, s, c, font=font, shadow=C["ink"])


def label_ru(cv, x, y, s, c, align="c"):
    """Ground item label with darkened plate (centred on x)."""
    w = pk.text_width(s, FONT_RU) + 7
    h = 13
    if align == "c":
        x -= w // 2
    cv.remap(x, y, w, h, pk.DARKEN2)
    cv.dither(x, y, w, h, C["ink"], 0.5)
    cv.frame(x, y, w, h, C["wood_md"])
    for (px_, py_) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(px_, py_, C["bronze_lt"])
    cv.text(x + 4, y + 2, s, c, font=FONT_RU, shadow=C["ink"])


# --------------------------------------------------------------------------
# SERPENT ORB
# --------------------------------------------------------------------------
def serpent_head(face_right=True, eye="fire"):
    m = pk.MatCanvas(36, 28)
    m.poly([(2, 27), (9, 27), (12, 18), (16, 13), (12, 10), (6, 16)], "Z")        # neck
    m.ellipse(18, 10, 8, 5.5, "Z")                                               # skull
    m.poly([(20, 6), (33, 9), (34, 12), (22, 13)], "Z")                           # snout
    m.poly([(18, 14), (32, 16), (33, 19), (26, 19), (17, 17)], "z")               # lower jaw
    m.poly([(22, 13), (33, 13), (32, 15), (22, 15)], "k")                         # mouth gap
    for tx in (24, 27, 30):
        m.px(tx, 13, "y"); m.px(tx + 1, 15, "y")
    m.px(33, 8, "Z"); m.px(34, 7, "Z"); m.px(35, 8, "z")                         # curled nose
    for i, (sx, sy) in enumerate(((6, 13), (9, 8), (13, 4), (18, 3))):          # crest spines
        m.poly([(sx, sy + 3), (sx + 3, sy + 3), (sx - 1, sy - 3)], "q")
    m.poly([(4, 18), (10, 15), (9, 20)], "q")
    m.px(20, 8, "E"); m.px(21, 8, "E"); m.px(21, 9, "k")                         # eye
    m.line(14, 12, 21, 12, "z")                                                  # cheek ridge
    legend = {
        "Z": ("bronze", 3, True, False), "z": ("bronze", 2, False, False),
        "q": ("bronze", 4, True, False), "k": ("ink", 0, False, False),
        "y": ("birch", 5, False, False), "E": (eye, 3 if eye == "fire" else 4, False, True),
    }
    spr = pk.make_sprite(m.rows(), legend)
    return spr if face_right else pk.flip(spr)


def serpent_ring(cv, cx, cy, r, w=6, n=30):
    """Scaled serpent body forming the orb rim (bronze scales, lit top-left)."""
    R = r + w
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    dx, dy = xx - cx + 0.5, yy - cy + 0.5
    d = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    lit = np.cos(ang + math.pi * 0.75)
    band = (d > r + 1) & (d <= R)
    t = (d - r - 1) / (w - 1)                         # 0 inner .. 1 outer
    row = (t > 0.5).astype(int)
    a = (ang / (2 * math.pi) * n + row * 0.5) % 1.0   # position inside scale
    tr = (t * 2) % 1.0
    tone = 2 + (lit > 0.25).astype(int) + (lit > -0.35).astype(int) - 1      # 1..3
    edge = (a < 0.14) | (tr < 0.18)
    hi = (a > 0.2) & (a < 0.45) & (tr > 0.25) & (tr < 0.6)
    ramp = np.array([C["wood_dk"], C["bronze_dk"], C["bronze"], C["bronze_lt"], C["bronze_hi"]])
    lv = np.clip(tone - edge.astype(int) + hi.astype(int), 0, 4)
    cv.a[band] = ramp[lv[band]]
    cv.a[(d <= R + 1) & (d > R)] = C["ink"]
    cv.a[(d <= r + 1) & (d > r)] = C["ink"]


def orb_v2(cv, cx, cy, r, fill, kind="life", seed=0.0):
    tones = [C["red_dk"], C["red"], C["red_lt"], C["ember"]] if kind == "life" else \
            [C["blue_dk"], C["blue"], C["blue_lt"], C["linen"]]
    serpent_ring(cv, cx, cy, r)
    pk.orb_liquid(cv, cx, cy, r, fill, tones, empty=(C["ink"], C["night"]), glass=C["linen"], seed=seed)


# --------------------------------------------------------------------------
# ICONS (themed)
# --------------------------------------------------------------------------
def _bg(cv, x, y, s, a, b):
    pk._icon_bg(cv, x, y, s, a, b)


def icon_fire_serpent(cv, x, y, s=22):
    _bg(cv, x, y, s, C["red_dk"], C["red"])
    f = s / 22.0
    pts = []
    for k in range(40):
        t = k / 39.0
        px = x + (2 + t * 15) * f
        py = y + (18 - t * 12 + math.sin(t * 7.5) * 3.2) * f
        pts.append((px, py, t))
    for px, py, t in pts:
        rr = (0.8 + t * 1.6) * f
        c = C["red_lt"] if t < 0.35 else (C["ember"] if t < 0.75 else C["flame"])
        cv.disc(px, py, rr + 0.6, C["red_lt"] if t > 0.3 else C["red"])
        cv.disc(px, py, rr, c)
    hx, hy = pts[-1][0], pts[-1][1]
    cv.disc(hx + 1, hy - 0.5, 3.2 * f, C["flame"])
    cv.disc(hx + 1.5, hy - 1, 1.6 * f, C["linen"])
    cv.px(int(hx + 3 * f), int(hy - 1 * f), C["ink"])
    for (a, b) in ((19, 3), (4, 8), (16, 15)):
        cv.px(int(x + a * f), int(y + b * f), C["flame"])


def icon_frost(cv, x, y, s=22):
    _bg(cv, x, y, s, C["sea_dk"], C["blue_dk"])
    f = s / 22.0
    cx, cy = x + 11 * f, y + 11 * f
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        ex, ey = cx + math.cos(a) * 9 * f, cy + math.sin(a) * 9 * f
        cv.line(int(cx), int(cy), int(ex), int(ey), C["blue_lt"])
        for t in (0.5, 0.75):
            bx, by = cx + math.cos(a) * 9 * f * t, cy + math.sin(a) * 9 * f * t
            for da in (0.7, -0.7):
                cv.line(int(bx), int(by), int(bx + math.cos(a + da) * 3 * f), int(by + math.sin(a + da) * 3 * f), C["blue"])
        cv.px(int(ex), int(ey), C["linen"])
    cv.disc(cx, cy, 1.8 * f, C["linen"])


def icon_shield_bash(cv, x, y, s=22):
    _bg(cv, x, y, s, C["wood_dk"], C["bronze_dk"])
    f = s / 22.0
    cx, cy, R = x + 9.5 * f, y + 12 * f, 7.8 * f
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    d = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
    a = np.arctan2(yy + 0.5 - cy, xx + 0.5 - cx)
    m = d <= R
    sect = ((a / (math.pi / 4)).astype(int) + 8) % 2 == 0
    cv.a[m & sect] = C["red"]; cv.a[m & ~sect] = C["birch"]
    cv.a[m & (d > R - 1.3)] = C["bronze"]
    cv.a[(d <= R + 1) & (d > R)] = C["ink"]
    cv.disc(cx, cy, 2.2 * f, C["bronze_lt"]); cv.px(int(cx - 1), int(cy - 1), C["bronze_hi"])
    for k in range(5):           # impact streaks
        ang = -0.9 + k * 0.45
        sx, sy = x + 17 * f + math.cos(ang) * 2, y + 12 * f + math.sin(ang) * 6 * f
        cv.line(int(sx), int(sy), int(sx + math.cos(ang) * 3 * f), int(sy + math.sin(ang) * 3 * f), C["flame"])


def icon_obereg(cv, x, y, s=22):
    _bg(cv, x, y, s, C["bronze_dk"], C["bronze_dk"])
    f = s / 22.0
    cx, cy = x + 11 * f, y + 11 * f
    cv.disc(cx, cy, 9 * f, C["wood_dk"])
    rosette(cv, cx - 0.5, cy - 0.5, 7.5 * f, C["bronze_hi"])
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    ring = np.abs(np.hypot(xx - cx + 0.5, yy - cy + 0.5) - 9 * f) < 0.7
    box = (xx >= x) & (xx < x + s) & (yy >= y) & (yy < y + s)
    cv.a[ring & box] = C["bronze"]


def icon_perun(cv, x, y, s=22):
    _bg(cv, x, y, s, C["sea_dk"], C["slate_dk"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    cv.poly([P(13, 1), P(6, 11), P(10, 11), P(7, 21), P(16, 8), P(12, 8), P(16, 1)], C["flame"], outline=C["ink"])
    cv.line(int(x + 13 * f), int(y + 2 * f), int(x + 8 * f), int(y + 10 * f), C["linen"])
    for (a, b) in ((3, 4), (18, 14), (4, 17)):
        cv.px(int(x + a * f), int(y + b * f), C["blue_lt"])


def icon_axe(cv, x, y, s=22):
    _bg(cv, x, y, s, C["slate_dk"], C["slate_dk"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    for j in range(50):             # swing arc
        a = math.pi * (0.9 + j / 50 * 1.1)
        cv.px(int(x + 11 * f + math.cos(a) * 9 * f), int(y + 12 * f + math.sin(a) * 9 * f), C["mist"] if j % 3 else C["linen"])
    cv.line(int(x + 5 * f), int(y + 20 * f), int(x + 15 * f), int(y + 4 * f), C["wood_md"])
    cv.line(int(x + 6 * f), int(y + 20 * f), int(x + 16 * f), int(y + 4 * f), C["wood"])
    cv.poly([P(12, 4), P(19, 2), P(21, 9), P(17, 12), P(14, 8)], C["mist"], outline=C["ink"])   # bearded blade
    cv.line(int(x + 19 * f), int(y + 3 * f), int(x + 20 * f), int(y + 9 * f), C["linen"])


def icon_bogatyr(cv, x, y, s=22):
    """«Богатырская стать» (passive: +HP, +phys. damage): broad-shouldered
    bogatyr bust in a conical helm, red cloak, bronze up-chevrons."""
    _bg(cv, x, y, s, C["red_dk"], C["red_dk"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    cv.poly([P(2, 21), P(4, 14), P(8, 12), P(14, 12), P(18, 14), P(20, 21)], C["red"], outline=C["ink"])   # cloak/shoulders
    cv.poly([P(6, 21), P(7, 15), P(15, 15), P(16, 21)], C["slate_lt"], outline=C["ink"])                 # mail chest
    for yy in (16, 18, 20):
        for xx in range(7, 16, 2):
            cv.px(int(x + (xx + (yy // 2) % 2) * f), int(y + yy * f), C["slate"])
    cv.disc(x + 11 * f, y + 9.5 * f, 3.2 * f, C["wood_lt"])                                           # face
    cv.poly([P(7, 8), P(15, 8), P(11, 1)], C["mist"], outline=C["ink"])                                # helm
    cv.line(int(x + 11 * f), int(y + 2 * f), int(x + 13 * f), int(y + 7 * f), C["linen"])
    cv.rect(int(x + 7 * f), int(y + 7 * f), int(9 * f), max(1, int(1.5 * f)), C["bronze_lt"])
    cv.px(int(x + 11 * f), int(y + 9 * f), C["slate"])                                                 # nasal
    for (cx_, cy_) in ((3, 6), (19, 6)):                                                              # up-chevrons
        for k in range(3):
            cv.px(int(x + (cx_ - 2 + k) * f), int(y + (cy_ + 2 - (1 - abs(k - 1))) * f), C["bronze_hi"])
            cv.px(int(x + (cx_ - 2 + k) * f), int(y + (cy_ + 5 - (1 - abs(k - 1))) * f), C["bronze_lt"])


def icon_veshchee(cv, x, y, s=22):
    """«Вещее слово» (passive: Ярь regen, fire & cold damage): a bronze lunnitsa
    breathing out a spiral of runes, one fiery, one frosty."""
    _bg(cv, x, y, s, C["blue_dk"], C["sea_dk"])
    f = s / 22.0
    cx, cy = x + 7 * f, y + 13 * f
    for k in range(60):                                   # breath spiral
        t = k / 59
        a = t * 5.2 + 0.4
        r = (1.5 + t * 8.0) * f
        px_, py_ = cx + math.cos(a) * r * 1.1 + t * 5 * f, cy - math.sin(a) * r * 0.8 - t * 4 * f
        c = C["blue_lt"] if t < 0.5 else (C["mist"] if t < 0.75 else C["linen"])
        cv.px(int(px_), int(py_), c)
    # runes: fiery «ᚠ»-like and frosty «ᛁ»-like strokes
    for (ax, ay, col) in ((15, 4, C["flame"]), (18, 10, C["blue_lt"])):
        cv.line(int(x + ax * f), int(y + ay * f), int(x + ax * f), int(y + (ay + 6) * f), col)
        cv.line(int(x + ax * f), int(y + (ay + 1) * f), int(x + (ax + 2) * f), int(y + ay * f), col)
        cv.line(int(x + ax * f), int(y + (ay + 3) * f), int(x + (ax + 2) * f), int(y + (ay + 2) * f), col)
    # bronze lunnitsa (crescent) at the speaker's side
    yy, xx = np.mgrid[0:cv.h, 0:cv.w]
    d1 = np.hypot(xx + 0.5 - (x + 6 * f), yy + 0.5 - (y + 16 * f))
    d2 = np.hypot(xx + 0.5 - (x + 6 * f), yy + 0.5 - (y + 13.5 * f))
    box = (xx >= x) & (xx < x + s) & (yy >= y) & (yy < y + s)
    moon = (d1 <= 5 * f) & (d2 > 4.2 * f) & box
    cv.a[moon] = C["bronze_lt"]
    cv.a[moon & (yy > y + 18 * f)] = C["bronze"]
    cv.a[box & (d1 > 5 * f) & (d1 <= 5.9 * f) & (d2 > 4.2 * f)] = C["ink"]


def icon_ryvok(cv, x, y, s=22):
    """«Рывок» (dash, Space): a boot kicking off with speed streaks and dust."""
    _bg(cv, x, y, s, C["slate_dk"], C["slate"])
    f = s / 22.0
    P = lambda a, b: (x + a * f, y + b * f)
    for k, (a, b, ln) in enumerate(((2, 6, 8), (1, 10, 10), (3, 14, 7))):      # speed streaks
        cv.line(int(x + a * f), int(y + b * f), int(x + (a + ln) * f), int(y + b * f), C["mist"] if k != 1 else C["linen"])
    cv.poly([P(10, 3), P(15, 3), P(15, 12), P(20, 14), P(20, 18), P(9, 18), P(10, 12)], C["wood_md"], outline=C["ink"])   # boot
    cv.line(int(x + 11 * f), int(y + 5 * f), int(x + 14 * f), int(y + 5 * f), C["wood_lt"])
    cv.line(int(x + 11 * f), int(y + 8 * f), int(x + 14 * f), int(y + 8 * f), C["wood_lt"])
    cv.rect(int(x + 9 * f), int(y + 17 * f), int(12 * f), max(1, int(1.5 * f)), C["wood_dk"])                 # sole
    for (a, b) in ((5, 19), (3, 18), (7, 20), (2, 20)):                                                         # dust puffs
        cv.px(int(x + a * f), int(y + b * f), C["birch"])
    cv.line(int(x + 16 * f), int(y + 10 * f), int(x + 19 * f), int(y + 8 * f), C["bronze_lt"])            # motion accent


def icon_sword(cv, x, y, s=22):
    pk.icon_sword(cv, x, y, s)


ICONS = {"fire_serpent": icon_fire_serpent, "frost": icon_frost, "shield_bash": icon_shield_bash,
         "obereg": icon_obereg, "perun": icon_perun, "axe": icon_axe, "sword": icon_sword,
         "bogatyr": icon_bogatyr, "veshchee": icon_veshchee, "ryvok": icon_ryvok}

# 12x12 menu icons (legend chars -> v2 names)
MENU_LG = {"k": "ink", "d": "slate_dk", "I": "slate_lt", "j": "mist", "g": "bronze", "y": "bronze_lt",
           "Y": "bronze_hi", "w": "linen", "b": "birch", "r": "red", "R": "red_lt", "e": "wood_md",
           "E": "wood", "u": "blue", "U": "blue_lt", "x": "red_dk", "n": "nebyl"}
MENU_ICONS = {
    "character": [  # conical helm with nasal
        ".....kk.....",
        "....kjIk....",
        "...kjIIIk...",
        "..kjIIIIdk..",
        ".kjIIIIIIdk.",
        "kyyyyyyyyygk",
        "kIIkkIIkkIdk",
        "kIIk.kk.kIdk",
        "kIIk.kk.kIdk",
        ".kkk.kk.kkk.",
        ".....kk.....",
        "............"],
    "inventory": pk.MENU_ICONS["inventory"],
    "skills": [  # rosette / rune
        "....kkkk....",
        "..kkyyyykk..",
        ".kyk.kk.kyk.",
        ".ky.kYYk.yk.",
        "kyk.kYYk.kyk",
        "kykkYYYYkkyk",
        "kykkYYYYkkyk",
        "kyk.kYYk.kyk",
        ".ky.kYYk.yk.",
        ".kyk.kk.kyk.",
        "..kkyyyykk..",
        "....kkkk...."],
    "map": pk.MENU_ICONS["map"],
    "menu": pk.MENU_ICONS["menu"],
    "chronicle": [  # «Летопись»: open birch-bark book with a bookmark
        "............",
        ".kkkkk.kkkkk",
        "kbbbbbkbbbbk",
        "kbeebbkbeebk",
        "kbbbbbkbbbbk",
        "kbeeebkbeeek",
        "kbbbbbkbbbbk",
        "kbeebbkbbeek",
        "kbbbbbkbrbbk",
        ".kkkkkkkrkk.",
        "........R...",
        "............"],
}


def menu_button(cv, x, y, s, icon, key):
    wood_planks(cv, x, y, s, s, seed=len(icon) * 7, plank=s)
    cv.frame(x, y, s, s, C["ink"])
    cv.hline(x + 1, y + 1, s - 2, C["wood_lt"]); cv.vline(x + 1, y + 1, s - 2, C["wood_lt"])
    cv.hline(x + 1, y + s - 2, s - 2, C["wood_dk"]); cv.vline(x + s - 2, y + 1, s - 2, C["wood_dk"])
    cv.rect(x + 3, y + 3, s - 6, s - 6, C["night"])
    cv.frame(x + 2, y + 2, s - 4, s - 4, C["wood_dk"])
    lg = {k: C[v] for k, v in MENU_LG.items()}
    cv.stamp(MENU_ICONS[icon], lg, x + (s - 12) // 2, y + (s - 12) // 2 - 1)
    for (cx_, cy_, sx, sy) in ((x, y, 1, 1), (x + s - 1, y, -1, 1), (x, y + s - 1, 1, -1), (x + s - 1, y + s - 1, -1, -1)):
        bronze_corner(cv, cx_, cy_, sx, sy, 4)
    w = pk.text_width(key, FONT3x5) + 2
    pk.key_label(cv, x + s - w + 1, y + s - 5, key, C["bronze_hi"])


POTION_TONES = {
    "life": ("red_dk", "red", "red_lt"),
    "mana": ("blue_dk", "blue", "blue_lt"),
    "zhivaya": ("bronze", "bronze_lt", "bronze_hi"),   # живая вода (rejuvenation)
}


def potion(cv, x, y, kind):
    a, b, c = POTION_TONES[kind]
    lg = {"k": C["ink"], "E": C["wood_md"], "e": C["wood_dk"], "g": C["mist"], "w": C["linen"],
          "1": C[a], "2": C[b], "3": C[c]}
    cv.stamp(pk._POTION, lg, x, y)

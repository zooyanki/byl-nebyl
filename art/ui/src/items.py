"""Item icons for inventory / equipment (material-letter maps -> auto-shaded,
outlined sprites via pixelkit.make_sprite). Long items are generated from
shape functions so they scale to any cell size."""
import math
import numpy as np
import pixelkit as pk
from pixelkit import C
from sprites import MAT

IMAT = dict(MAT)
IMAT.update({
    "V": ("blue", 4, True, False), "v": ("blue", 3, False, False),
    "P": ("violet", 3, True, False), "p": ("violet", 2, False, False),
    "g": ("gold", 3, False, False), "N": ("bone", 6, True, False), "n": ("bone", 5, False, False),
    "l": ("earth", 2, False, False), "F": ("fire", 4, False, False), "f": ("fire", 3, False, False),
    "Z": ("gold", 5, True, False), "z": ("gold", 3, False, False),
    "Q": ("grass", 5, True, False), "q": ("grass", 4, False, False),
})


def grid(w, h, fn):
    return ["".join(fn(x, y) for x in range(w)) for y in range(h)]


# --------------------------------------------------------------------------
HELM = [
    "B......................B",
    "BB....................BB",
    ".BB.....HHHHHHHH.....BB.",
    ".BBB..HHHHHHHHHHHH..BBB.",
    "..BBBHHHHHHGHHHHHHHBBB..",
    "...BHHHHHHHGHHHHHHHaB...",
    "....HHHHHHHGHHHHHHHa....",
    "....HHHHHHHGHHHHHHHa....",
    "....HHHHHHHGHHHHHHHa....",
    "....DDDDDDDDDDDDDDDD....",
    "....HHHHHHHGHHHHHHHa....",
    "....HHDHDHHGHHDHDHHa....",
    "....HHHHHHHGHHHHHHHa....",
    "....HHDHDHHGHHDHDHHa....",
    "....HHHHHHHGHHHHHHaa....",
    ".....HHHHHHGHHHHHaa.....",
    ".....GGGGGGGGGGGGGG.....",
    "......GGGGGGGGGGGG......",
]

GLOVES = [
    "........AA.AA.......",
    ".......AHAAHAA......",
    ".......AHAAHAAA.....",
    ".......AHAAHAAAA....",
    "..AA...AAAAAAAAA....",
    "..AHA..AHAAHAAHA....",
    "...AHA.AAAAAAAAA....",
    "....AHAAAAAAAAAA....",
    ".....AAAAAAAAAAa....",
    "......AAAAAAAAa.....",
    "......GGGGGGGGG.....",
    "......LLLLLLLLL.....",
    "......LLLGLLLLL.....",
    "......LLLLLLLLL.....",
    "......LLLLLLGLL.....",
    "......GGGGGGGGG.....",
]

BOOTS = [
    "..AAAAA......AAAAA....",
    "..LLLLL......LLLLL....",
    "..LLLLL......LLLLL....",
    "..LGLLL......LGLLL....",
    "..LLLLL......LLLLL....",
    "..GGGGG......GGGGG....",
    "..LLLLL......LLLLL....",
    "..LLLLL......LLLLL....",
    "..LLLLLL.....LLLLLL...",
    "..LLLLLLLL...LLLLLLLL.",
    "..LLLLLLLLL..LLLLLLLLL",
    "..AAAAAAAAA..AAAAAAAAA",
]

BELT = [
    "LLLLLLLLLLLLLLLGGGGGGLLLLLLLLLLLLLLL",
    "LLLHLLLLLLLHLLLG....GLLLHLLLLLLLHLLL",
    "LLLLLLLLLLLLLLLG.GG.GLLLLLLLLLLLLLLL",
    "LLLHLLLLLLLHLLLG....GLLLHLLLLLLLHLLL",
    "lllllllllllllllGGGGGGlllllllllllllll",
    "..SSSSS......................SSSSS..",
    "..SGSSS......................SSSGS..",
    "..SSSSS......................SSSSS..",
]

GEM = [
    "...XXXX...",
    "..XWXXXX..",
    ".XWXXXXXX.",
    "XXXXXXXXXx",
    "XXXXXXXXxx",
    ".XXXXXXxx.",
    "..XXXXxx..",
    "...Xxxx...",
    "....xx....",
]

SCROLL = [
    ".NNNNNNNNNNNN.",
    "NNnNNNNNNNNnNN",
    ".NNNNNNNNNNNN.",
    "..NnnnNnnNNN..",
    "..NNNNNNNNNN..",
    "..NnnNNnnnNN..",
    "..NNNNNNNNNN..",
    "..NnnnNNnNNN..",
    "..NNNNNNNCCN..",
    ".NNNNNNNNCCNN.",
    "NNnNNNNNNNNnNN",
    ".NNNNNNNNNNNN.",
]

CHARM = [
    "..BBBBB..",
    ".BBBBBBB.",
    "BBDDBDDBB",
    "BBEDBEDBB",
    "BBBBDBBBb",
    ".BWBWBWb.",
    "..bbbbb..",
    "...GGG...",
    "..GOOOG..",
    "...GGG...",
]

ARMOR = (
    ["....GGGG..............GGGG...."] +
    ["..AAAAAAG............GAAAAAA.."] +
    [".AAAHHAAAG..........GAAAHHAAA."] +
    ["AAAHHAAAAAGGGGGGGGGGAAAAAHHAAA"] +
    ["AAHHAAAAAAAACCCCCCAAAAAAAAHHAA"] +
    ["AAAAAAAAAAAACCCCCCAAAAAAAAAAAA"] +
    ["aAAAA.AAAAAACCGGCCAAAAAA.AAAAa"] +
    [".aaa..AAAAAACGGGGCAAAAAA..aaa."] +
    ["......AAAAAACCGGCCAAAAAA......"] +
    ["......AAAAAACCGGCCAAAAAA......"] * 2 +
    ["......aAAAAACCCCCCAAAAAa......"] * 3 +
    ["......GGGGGGGGGGGGGGGGGG......"] +
    ["......LLLLLLLLGGLLLLLLLL......"] +
    ["......AaAaAaACCCCaAaAaAa......", "......aAaAaAaCCCCAaAaAaA......"] * 4 +
    [".....AaAaAaA.CCCC.AaAaAaA.....", ".....aAaAaAa.CCCC.aAaAaAa....."] +
    [".............cccc.............."]
)


def kite_shield(w=30, h=44, field="C", device="Y"):
    cx = (w - 1) / 2

    def fn(x, y):
        t = y / (h - 1)
        half = w / 2 if t < 0.45 else (w / 2) * max(0.0, 1 - (t - 0.45) / 0.55) ** 0.75
        top_cut = (t < 0.06 and abs(x - cx) > w / 2 - 3 + (0.06 - t) * 0)
        if abs(x - cx) > half - 0.01 or top_cut:
            return "."
        if abs(x - cx) > half - 2.5 or y < 2:
            return "G"
        # device: cross
        if (abs(x - cx) < 1.5 and 0.12 < t < 0.78) or (abs(y - h * 0.34) < 1.5 and abs(x - cx) < w * 0.28):
            return device
        return field if x < cx else field.lower() if field.lower() in IMAT else field
    return grid(w, h, fn)


def buckler(d=30):
    r = d / 2

    def fn(x, y):
        dd = math.hypot(x - r + 0.5, y - r + 0.5)
        if dd > r:
            return "."
        if dd > r - 3:
            return "A"
        if dd < 3.5:
            return "G"
        ang = math.atan2(y - r, x - r)
        if abs(dd - (r - 5)) < 0.8 and int((ang + 4) * 4) % 3 == 0:
            return "H"
        return "S" if int((x + y * 0.3) / 4) % 2 else "L"
    return grid(d, d, fn)


def sword(w=14, h=66):
    cx = w // 2

    def fn(x, y):
        dx = x - cx
        if y < h - 20:                      # blade with tip
            half = 2 if y > 5 else max(0, (y - 1) // 2)
            if -half <= dx < half + 1 and y >= 1:
                return "W" if dx == -half else ("H" if dx <= 0 else "T")
            return "."
        if h - 20 <= y < h - 17:            # crossguard
            return "G" if abs(dx) <= cx - (0 if y == h - 19 else 1) else "."
        if h - 17 <= y < h - 6:             # grip
            return ("L" if (y % 2) else "l") if -1 <= dx <= 1 else "."
        if y >= h - 6:                      # pommel
            return "G" if abs(dx) <= (2 if h - 5 <= y <= h - 2 else 1) else "."
        return "."
    return grid(w, h, fn)


def staff(w=30, h=86):
    """Diagonal fire staff: wooden shaft, gold claw head holding an ember orb."""
    x0, y0, x1, y1 = 4, h - 3, w - 9, 16
    ox, oy, orr = w - 9, 9, 6

    def fn(x, y):
        dd = math.hypot(x - ox, y - oy)
        if dd <= orr - 1.5:
            return "O" if dd < 1.6 else ("f" if dd < orr - 3 else "E")
        # claws around orb
        if orr - 1.5 < dd <= orr + 0.8:
            ang = math.degrees(math.atan2(y - oy, x - ox))
            if any(abs(ang - a) < 22 for a in (-150, -30, 90, 160, 20)):
                return "G"
        # shaft: distance to line
        vx, vy = x1 - x0, y1 - y0
        t = max(0, min(1, ((x - x0) * vx + (y - y0) * vy) / (vx * vx + vy * vy)))
        px, py = x0 + vx * t, y0 + vy * t
        d = math.hypot(x - px, y - py)
        if d < 1.6:
            if t > 0.86:
                return "G"
            return "G" if abs(t - 0.45) < 0.02 or abs(t - 0.62) < 0.02 else "S"
        return "."
    return grid(w, h, fn)


def ring(gem="R"):
    def fn(x, y):
        dd = math.hypot(x - 7, y - 9)
        if y <= 4 and abs(x - 7) <= 2 - (1 if y in (0, 4) else 0):
            return gem
        if 3.6 <= dd <= 5.8:
            return "G"
        return "."
    return grid(15, 16, fn)


def amulet(gem="V"):
    rows = []
    for y in range(18):
        r = ""
        for x in range(18):
            ch = "."
            # chain: V-shape
            if y < 10 and (abs(x - (2 + y * 0.7)) < 0.8 or abs(x - (15 - y * 0.7)) < 0.8) and (x + y) % 2 == 0:
                ch = "G"
            dd = math.hypot(x - 8.5, y - 12.5)
            if dd <= 4.6:
                ch = "G" if dd > 2.6 else gem
            if y == 17 and x in (8, 9):
                ch = "G"
            r += ch
        rows.append(r)
    return rows


def tome(w=18, h=34):
    def fn(x, y):
        if x >= w - 3 and 2 <= y < h - 2:
            return "N"
        if x < w - 2:
            if (x < 3 or y < 3 or y >= h - 3) and ((x + y) % 7 < 3):
                return "G"
            if abs(x - (w - 3) / 2) < 3.5 and abs(y - h / 2) < 4.5:
                return "R" if math.hypot(x - (w - 3) / 2, y - h / 2) < 3.2 else "G"
            return "c"
        return "."
    return grid(w, h, fn)


def stretch(rows, fx, fy):
    """Nearest-neighbour resample of a material map (keeps 1:1 pixel size after
    shading/outline, so enlarged items stay crisp and consistent)."""
    h, w = len(rows), max(len(r) for r in rows)
    rows = [r.ljust(w, ".") for r in rows]
    W2, H2 = int(round(w * fx)), int(round(h * fy))
    return ["".join(rows[min(h - 1, int(y / fy))][min(w - 1, int(x / fx))] for x in range(W2)) for y in range(H2)]


def _spr(rows, mat=None):
    return pk.make_sprite(rows, mat or IMAT)


def gem_sprite(kind):
    m = dict(IMAT)
    ramp = {"ruby": "red", "sapphire": "blue", "amethyst": "violet", "topaz": "gold"}[kind]
    top = {"violet": 3}.get(ramp, 4)
    m["X"] = (ramp, top, True, False)
    m["x"] = (ramp, top - 1, False, False)
    return _spr(GEM, m)


def build():
    S = {
        "helm": _spr(stretch(HELM, 1.5, 1.6)), "gloves": _spr(stretch(GLOVES, 1.6, 1.6)),
        "boots": _spr(stretch(BOOTS, 1.6, 1.5)), "belt": _spr(stretch(BELT, 1.15, 1.3)),
        "armor": _spr(stretch(ARMOR, 1.4, 2.4)), "scroll": _spr(SCROLL), "charm": _spr(CHARM),
        "kite": _spr(kite_shield(38, 70)), "buckler": _spr(buckler(36)), "sword": _spr(sword()),
        "staff": _spr(staff()), "ring_ruby": _spr(ring("R")), "ring_sapph": _spr(ring("V")),
        "amulet": _spr(amulet("V")), "tome": _spr(tome()),
    }
    for g in ("ruby", "sapphire", "amethyst", "topaz"):
        S["gem_" + g] = gem_sprite(g)
    return S


RARITY = {  # name colour, cell tint
    "normal": (C["parchment"], C["shadow"]),
    "magic": (C["blue_lt"], C["navy"]),
    "rare": (C["flame"], C["earth_dk"]),
    "unique": (C["gold_lt"], C["gold_dk"]),
    "quest": (C["ember"], C["blood"]),
}


def draw_item(cv, spr, x, y, w, h, rarity=None, tint=0.35):
    """Draw sprite centred inside the pixel rect (x,y,w,h) with rarity tint."""
    if rarity:
        cv.dither(x + 1, y + 1, w - 2, h - 2, RARITY[rarity][1], tint)
    if callable(spr):
        spr(cv, x, y, w, h)
        return
    idx = pk.sprite_to_index(spr)
    cv.blit(idx, x + (w - spr["w"]) // 2, y + (h - spr["h"]) // 2)


def potion_fn(kind):
    def f(cv, x, y, w, h):
        pk.potion(cv, x + (w - 12) // 2, y + (h - 15) // 2, kind)
    return f

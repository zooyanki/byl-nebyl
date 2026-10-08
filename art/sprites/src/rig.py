"""Shared 2-view humanoid rig for 46-px «Люди» (scale.md §2): 64x64 frame,
pivot (32,56), soles on the pivot row, 1-px ink outline (make_sprite).

Views (GDD §12.1.2: monsters 2 drawn + 2 mirrored):
  "se" - 3/4 front, facing down-right (mirror -> "sw")
  "ne" - 3/4 back,  facing up-right   (mirror -> "nw")
The character's RIGHT arm is the near arm in both views (screen-left in SE,
screen-right in NE); the LEFT arm is the far arm.

Local coordinates: x right, y down, origin = ground point between the soles
(material row 54 of the 62x62 MatCanvas; make_sprite adds the 1-px outline,
so the outline under the soles lands on frame row 56 = pivot row).
"""
import os
import sys
import math
import numpy as np

sys.path.insert(0, "/workspace/game/art/ui/src")
import gameplay_hud_v2 as _G          # noqa: F401  (activates palette v2)
import pixelkit as pk

GX, GY = 31, 54          # local origin in MatCanvas coords
MW = MH = 62             # MatCanvas size (frame 64 after the outline pad)
PIVOT = (32, 56)

# material legend: (ramp, base level, auto-shade, emissive[, pattern])
BASE = {
    "S": ("skin", 3, True, False), "s": ("skin", 2, False, False),
    "B": ("wood", 2, True, False), "b": ("wood", 1, False, False),          # dark beard / hair
    "G": ("birch", 4, True, False), "g": ("birch", 3, False, False),        # grey beard
    "k": ("ink", 0, False, False),                                           # eyes, mouth (not an outline)
    "L": ("wood", 2, True, False), "Z": ("bronze", 3, True, False), "z": ("bronze", 2, False, False),
    "W": ("birch", 3, True, False), "w": ("birch", 2, False, False),        # onuchi wraps
    "O": ("wood", 1, True, False), "o": ("wood", 1, False, False),          # shoes (o: far foot)
    "V": ("birch", 2, False, False),                                         # far-leg wraps (one step darker)
    "H": ("iron", 4, True, False), "h": ("iron", 3, False, False), "I": ("iron", 6, False, False),
    "X": ("wood", 3, True, False, "grain"), "x": ("wood", 2, False, False),  # haft / torch stick
    "R": ("wood", 1, False, False, "dither"),                                # pitch wrap of the torch
    "E": ("fire", 3, False, True), "e": ("fire", 4, False, True), "q": ("fire", 2, False, True),
    "Q": ("fire", 1, False, True), "r": ("fire", 0, False, True),
    "N": ("nebyl", 3, False, True), "n": ("nebyl", 2, False, True), "M": ("nebyl", 4, False, True),
    "Y": ("birch", 4, True, False), "y": ("birch", 5, False, False), "v": ("birch", 2, False, False),
    "U": ("red", 2, False, False), "u": ("red", 1, False, False),            # red trim / embroidery
    # character-scheme slots (overridden per character):
    "T": ("sea", 3, True, False), "t": ("sea", 2, False, False),            # tunic / robe
    "P": ("wood", 2, True, False), "p": ("wood", 1, False, False),          # trousers (p: far leg)
    "C": ("iron", 4, True, False), "c": ("iron", 3, False, False),          # cap / hood
    "F": ("fur", 5, True, False, "fur"), "f": ("fur", 4, False, False, "fur"), "j": ("fur", 3, False, False, "fur"),
    "A": ("wood", 2, True, False), "a": ("wood", 1, False, False),          # sleeves / bracers
}
FIRE_CH = set("EeqQr")
GLOW_CH = set("NnM")


def legend(**over):
    d = dict(BASE)
    d.update(over)
    return d


def rot(a, b, ang):
    t = math.radians(ang)
    return (a * math.cos(t) - b * math.sin(t), a * math.sin(t) + b * math.cos(t))


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


class Painter:
    """MatCanvas wrapper in local coordinates."""

    def __init__(self):
        self.m = pk.MatCanvas(MW, MH)

    @staticmethod
    def M(p):
        return (GX + p[0], GY + p[1])

    def poly(self, pts, ch):
        self.m.poly([self.M(p) for p in pts], ch)

    def line(self, p, q, ch, w=1):
        a, b = self.M(p), self.M(q)
        self.m.line(a[0], a[1], b[0], b[1], ch, w)

    def limb(self, p, q, ch, w=3):
        """Capsule: thick segment with rounded ends."""
        a, b = self.M(p), self.M(q)
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / n * (w / 2.0), dx / n * (w / 2.0)
        self.m.poly([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], ch)
        r = (w - 1) / 2.0
        for c in (a, b):
            self.m.ellipse(c[0], c[1], max(r, 0.5), max(r, 0.5), ch)

    def ellipse(self, c, rx, ry, ch, clip=None):
        cx, cy = self.M(c)
        yy, xx = np.mgrid[0:MH, 0:MW]
        msk = ((xx - cx) / max(rx, 0.5)) ** 2 + ((yy - cy) / max(ry, 0.5)) ** 2 <= 1.0
        if clip is not None:
            msk &= clip(xx - GX, yy - GY)
        self.m.a[msk] = ch

    def px(self, p, ch):
        x, y = self.M(p)
        self.m.px(int(round(x)), int(round(y)), ch)

    def shape(self, origin, ang, pts, ch, flip=1):
        """Polygon given in a rotated local frame (a lateral, b vertical)."""
        self.poly([add(origin, rot(a * flip, b, ang)) for a, b in pts], ch)


def ik(p, q, l1, l2, bend):
    """Knee / elbow position for a 2-bone chain from p to q; bend=+1 bends
    toward +x side of the segment's left normal, -1 the other way."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    d = math.hypot(dx, dy)
    d = min(d, l1 + l2 - 1e-3)
    if d < 1e-3:
        return p
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    ux, uy = dx / max(math.hypot(dx, dy), 1e-6), dy / max(math.hypot(dx, dy), 1e-6)
    mx, my = p[0] + ux * a, p[1] + uy * a
    nx, ny = -uy, ux
    return (mx + nx * h * bend, my + ny * h * bend)


# --------------------------------------------------------------------------
# finishing: sprite build with fire-aware outline
# --------------------------------------------------------------------------
def build(painter, leg):
    spr = pk.make_sprite(painter.m.rows(), leg)
    # outline pixels touching only fire become dark-red emissive (fire reads as light, not as a cut-out)
    ch = np.full(spr["mask"].shape, ".", dtype="<U1")
    ch[1:-1, 1:-1] = painter.m.a
    fire = np.isin(ch, list(FIRE_CH))
    glow = np.isin(ch, list(GLOW_CH))
    solid = (ch != ".") & ~fire & ~glow
    ink = pk.RAMP_ID["ink"]
    outl = spr["mask"] & (ch == ".")

    def nb(m):
        o = np.zeros_like(m)
        o[1:, :] |= m[:-1, :]; o[:-1, :] |= m[1:, :]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
        return o
    f_only = outl & nb(fire) & ~nb(solid) & ~nb(glow)
    g_only = outl & nb(glow) & ~nb(solid) & ~nb(fire)
    spr["ramp"][f_only] = pk.RAMP_ID["fire"]; spr["lvl"][f_only] = 0; spr["em"][f_only] = True
    spr["ramp"][g_only] = pk.RAMP_ID["nebyl"]; spr["lvl"][g_only] = 1; spr["em"][g_only] = True
    spr["pivot"] = PIVOT
    spr["chars"] = ch
    return spr


def to_index(spr):
    return pk.sprite_to_index(spr)


def visible_top(idx):
    rows = np.where((idx >= 0).any(1))[0]
    return int(rows.min()) if len(rows) else None


def height(idx, pivot_y=PIVOT[1]):
    t = visible_top(idx)
    return None if t is None else pivot_y - t + 1


# --------------------------------------------------------------------------
# flame (6-phase loop, always rising)
# --------------------------------------------------------------------------
def flame(P, base, phase, h=9, w=5, lean=0.0, scale=1.0):
    """Torch-head flame: base = local point of the flame root (top of the
    pitch wrap). phase 0..5. Drawn as stacked rows: ember skin, flame body,
    linen core; tongues flicker by phase."""
    if scale <= 0:
        return
    h = h * scale
    w = max(2.0, w * scale)
    ph = phase / 6.0 * 2 * math.pi
    hh = h * (1.0 + 0.12 * math.sin(ph) + 0.06 * math.sin(2 * ph + 1.0))
    rows = int(math.ceil(hh))
    for i in range(rows + 1):
        t = i / max(hh, 1)
        if t > 1:
            break
        half = (w / 2.0) * (1 - t) ** 0.75 * (1 + 0.15 * math.sin(ph * 2 + i * 0.9))
        off = lean * t * h * 0.35 + 0.9 * math.sin(ph + t * 3.2) * t
        y = base[1] - i
        x0, x1 = base[0] + off - half, base[0] + off + half
        P.line((x0, y), (x1, y), "q")
        if half > 0.9 and t < 0.75:
            P.line((x0 + 0.8, y), (x1 - 0.8, y), "E")
        if t < 0.35 and half > 1.3:
            P.line((x0 + 1.4, y), (x1 - 1.4, y), "e")
    # detached tongue / spark above, alternates by phase
    sx = base[0] + lean * h * 0.4 + (1 if phase % 3 == 0 else -1) * (phase % 2)
    sy = base[1] - rows - 1 - (phase % 3 == 1)
    P.px((sx, sy), "q" if phase % 2 else "E")

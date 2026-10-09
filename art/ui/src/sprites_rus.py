"""Characters & props for the Rus' theme, built with pixelkit.MatCanvas
primitives (material letters -> auto-shaded, outlined sprites)."""
import math
import numpy as np
import pixelkit as pk

MAT = {
    "K": ("ink", 0, False, False), "k": ("ink", 0, False, False),
    "H": ("iron", 4, True, False), "h": ("iron", 3, False, False),
    "Z": ("bronze", 3, True, False), "z": ("bronze", 2, False, False),
    "M": ("iron", 4, True, False, "mail"), "m": ("iron", 3, False, False, "mail"),
    "S": ("skin", 3, True, False), "s": ("skin", 2, False, False),
    "B": ("wood", 3, True, False, "fur"),
    "C": ("red", 2, True, False), "c": ("red", 1, False, False),
    "P": ("sea", 3, True, False), "W": ("birch", 4, True, False), "w": ("birch", 3, False, False),
    "O": ("wood", 2, True, False), "L": ("wood", 2, True, False),
    "D": ("red", 2, True, False), "d": ("birch", 4, True, False),
    "T": ("iron", 5, True, False), "G": ("wood", 2, False, False),
    "E": ("fire", 3, False, True), "e": ("fire", 4, False, True),
    "N": ("nebyl", 3, False, True), "n": ("nebyl", 2, False, True),
    "F": ("fur", 4, True, False, "fur"), "f": ("fur", 3, False, False, "fur"),
    "U": ("ghoul", 3, True, False), "u": ("ghoul", 2, False, False),
    "R": ("wood", 2, True, False, "dither"), "r": ("wood", 1, False, False),
    "X": ("wood", 3, True, False, "grain"), "x": ("wood", 2, False, False, "grain"),
    "V": ("pine", 3, True, False, "fur"), "v": ("pine", 2, False, False),
    "y": ("birch", 5, False, False), "Q": ("red", 1, False, False),
    "A": ("wood", 3, True, False), "Y": ("birch", 4, True, False),
}


def _shield(m, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:m.h, 0:m.w]
    d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    a = np.arctan2((yy - cy) / ry, (xx - cx) / rx)
    inside = d <= 1.0
    sect = (((a + math.pi) / (math.pi / 4)).astype(int) % 2) == 0
    m.a[inside & sect] = "D"
    m.a[inside & ~sect] = "d"
    m.a[inside & (d > 0.72)] = "Z"
    m.a[d <= 0.09] = "Z"


def hero_doll():
    """Druzhinnik, large portrait version (56 px) used as the doll in the
    «Витязь» window (scale.md §4.4: window doll is separate art). Faces right."""
    m = pk.MatCanvas(40, 58)
    ox = 3
    # cloak behind
    m.poly([(ox + 8, 19), (ox + 21, 18), (ox + 27, 30), (ox + 29, 49), (ox + 20, 52), (ox + 7, 51), (ox + 4, 34)], "C")
    m.poly([(ox + 5, 36), (ox + 9, 30), (ox + 9, 51), (ox + 6, 50)], "c")
    m.poly([(ox + 24, 34), (ox + 29, 49), (ox + 25, 50)], "c")
    # legs (stride: right leg forward)
    m.poly([(ox + 10, 38), (ox + 14, 38), (ox + 13, 50), (ox + 9, 50)], "P")
    m.poly([(ox + 16, 38), (ox + 20, 38), (ox + 24, 49), (ox + 20, 50)], "P")
    m.poly([(ox + 9, 45), (ox + 13, 45), (ox + 13, 51), (ox + 9, 51)], "W")
    m.poly([(ox + 21, 44), (ox + 24, 44), (ox + 25, 50), (ox + 21, 51)], "W")
    m.line(ox + 9, 47, ox + 13, 46, "w"); m.line(ox + 21, 47, ox + 24, 46, "w")
    m.poly([(ox + 8, 51), (ox + 13, 51), (ox + 14, 54), (ox + 7, 54)], "O")
    m.poly([(ox + 20, 51), (ox + 25, 50), (ox + 28, 53), (ox + 20, 54)], "O")
    # mail hauberk
    m.poly([(ox + 9, 18), (ox + 21, 18), (ox + 23, 32), (ox + 24, 40), (ox + 7, 40), (ox + 8, 32)], "M")
    m.poly([(ox + 7, 37), (ox + 24, 37), (ox + 24, 40), (ox + 7, 40)], "m")
    m.rect(ox + 8, 30, 16, 2, "L")
    m.rect(ox + 14, 30, 3, 2, "Z")
    m.line(ox + 18, 32, ox + 19, 37, "L")          # scabbard strap
    # head
    m.ellipse(ox + 15, 13.5, 3.6, 4.2, "S")
    m.poly([(ox + 11, 14), (ox + 19, 14), (ox + 18.5, 20), (ox + 15, 22.5), (ox + 11.5, 20)], "B")
    m.line(ox + 12, 15, ox + 18, 15, "B")
    m.px(ox + 13, 13, "k"); m.px(ox + 17, 13, "k")
    # aventail
    m.poly([(ox + 9, 10), (ox + 11, 10), (ox + 11, 18), (ox + 9, 18)], "M")
    m.poly([(ox + 19, 10), (ox + 21, 10), (ox + 21, 18), (ox + 19, 18)], "M")
    # conical helm + nasal
    m.poly([(ox + 9, 11), (ox + 21, 11), (ox + 15, 0)], "H")
    m.poly([(ox + 15, 1), (ox + 21, 11), (ox + 17, 11)], "h")
    m.rect(ox + 9, 10, 13, 2, "Z")
    m.rect(ox + 15, 11, 1, 4, "H")
    m.px(ox + 15, 0, "Z")
    # sword arm raised (screen right)
    m.line(ox + 21, 20, ox + 25, 15, "M", 3)
    m.line(ox + 25, 15, ox + 27, 11, "M", 3)
    m.ellipse(ox + 27.5, 10.5, 1.6, 1.6, "S")
    m.line(ox + 25, 8, ox + 30, 12, "Z")            # crossguard
    m.line(ox + 27, 11, ox + 25, 14, "G")
    m.px(ox + 24, 15, "Z")
    m.line(ox + 28, 9, ox + 36, 0, "T", 2)          # blade
    # round shield on the left arm, in front
    _shield(m, ox + 7, 29, 7.6, 9.2)
    return pk.make_sprite(m.rows(), MAT)


def upyr_v2b():
    """Упырь — hunched grave-ghoul, pale, red eyes, long clawed arms. Faces left."""
    m = pk.MatCanvas(34, 50)
    # shroud / rags body
    m.poly([(13, 16), (24, 14), (28, 30), (27, 44), (24, 41), (21, 46), (18, 42), (14, 46), (12, 41), (11, 30)], "R")
    m.poly([(22, 18), (27, 30), (26, 42), (23, 40)], "r")
    # bare ribcage through torn shroud
    m.poly([(13, 20), (19, 19), (19, 30), (13, 31)], "U")
    for yy in (22, 25, 28):
        m.line(13, yy, 18, yy - 1, "u")
    # head forward, hunched neck
    m.poly([(12, 13), (19, 12), (17, 19), (12, 19)], "U")
    m.ellipse(10, 12, 5.2, 5.8, "U")
    m.poly([(5, 13), (9, 13), (9, 18), (6, 17)], "U")              # jaw
    m.px(7, 11, "E"); m.px(10, 11, "E"); m.px(8, 11, "k")
    m.line(5, 15, 9, 15, "k"); m.px(6, 14, "y"); m.px(8, 16, "y")
    m.line(6, 16, 6, 19, "Q"); m.px(8, 17, "Q")
    m.line(11, 7, 14, 6, "u"); m.line(12, 9, 15, 8, "u")             # sparse hair
    # arms reaching to the left with claws
    m.line(14, 19, 7, 25, "U", 2); m.line(7, 25, 2, 28, "U", 2)
    for i in range(3):
        m.line(2, 28, -1 + i, 31 + i, "y")
    m.line(19, 20, 13, 28, "U", 2); m.line(13, 28, 8, 32, "U", 2)
    for i in range(3):
        m.line(8, 32, 4 + i, 35 + i // 2, "y")
    # legs
    m.line(15, 44, 14, 49, "U", 2); m.line(22, 44, 23, 49, "U", 2)
    m.line(12, 49, 15, 49, "u"); m.line(22, 49, 26, 49, "u")
    return pk.make_sprite(m.rows(), MAT)


def volkolak_v2b():
    """Волколак — wolf-headed man, hunched, amber eyes, claws. Faces left."""
    m = pk.MatCanvas(40, 56)
    # tail
    m.line(30, 32, 37, 44, "f", 3)
    # back leg
    m.poly([(24, 34), (30, 34), (31, 44), (28, 54), (25, 54), (27, 44)], "f")
    # torso hunched
    m.poly([(12, 18), (26, 12), (32, 22), (31, 34), (16, 37), (11, 28)], "F")
    m.poly([(18, 14), (26, 11), (30, 16), (22, 18)], "f")              # mane
    m.poly([(16, 33), (31, 31), (31, 37), (15, 38)], "R")              # torn trousers
    # front leg
    m.poly([(15, 36), (22, 36), (21, 44), (19, 54), (15, 54), (17, 44)], "F")
    m.line(13, 54, 20, 54, "y")
    # head + snout
    m.ellipse(10, 15, 6, 5.5, "F")
    m.poly([(6, 13), (0, 15), (0, 18), (2, 20), (8, 20)], "F")
    m.poly([(1, 18), (7, 18), (7, 21), (2, 21)], "f")                # lower jaw
    m.line(1, 18, 7, 18, "k"); m.px(2, 17, "y"); m.px(4, 19, "y"); m.px(6, 17, "y")
    m.px(0, 15, "k")
    m.poly([(10, 4), (14, 10), (9, 11)], "F"); m.poly([(6, 6), (9, 11), (5, 12)], "f")   # ears
    m.px(7, 13, "e"); m.px(8, 13, "e")
    # arms
    m.line(15, 20, 9, 28, "F", 3); m.line(9, 28, 5, 33, "F", 3)
    for i in range(3):
        m.line(5, 33, 2 + i, 37, "y")
    m.line(24, 20, 23, 30, "f", 3); m.line(23, 30, 20, 35, "f", 2)
    return pk.make_sprite(m.rows(), MAT)


def leshy_v2b():
    """Леший — tall bark-skinned forest spirit, moss beard, branch antlers,
    green Небыль eyes. Faces left. ~64 px."""
    m = pk.MatCanvas(40, 68)
    # antlers / branches
    for (a, b, c, d) in ((16, 10, 9, 1), (11, 5, 6, 4), (12, 6, 11, 0), (22, 10, 30, 1), (27, 5, 33, 4), (27, 5, 27, 0)):
        m.line(a, b, c, d, "A", 2 if (a, b) in ((16, 10), (22, 10)) else 1)
    # trunk body
    m.poly([(12, 20), (26, 20), (29, 40), (26, 60), (13, 60), (9, 40)], "X")
    m.poly([(22, 22), (29, 40), (26, 60), (22, 60)], "x")
    # head
    m.ellipse(19, 14, 6.5, 6.5, "X")
    m.px(16, 13, "N"); m.px(21, 13, "N"); m.px(16, 14, "n"); m.px(21, 14, "n")
    m.line(17, 18, 21, 18, "k")
    # long moss beard
    m.poly([(13, 16), (25, 16), (23, 26), (19, 35), (15, 27)], "V")
    m.poly([(19, 22), (23, 24), (19, 35)], "v")
    # moss on shoulders + fly agaric
    m.ellipse(12, 21, 3.5, 2, "V"); m.ellipse(27, 21, 3.5, 2, "V")
    m.ellipse(28, 18.5, 2.5, 1.5, "D"); m.px(27, 18, "y"); m.px(29, 19, "y"); m.rect(28, 20, 1, 1, "W")
    # arms (branches) reaching left
    m.line(12, 24, 5, 36, "X", 3)
    for (a, b) in ((0, 38), (2, 41), (5, 41)):
        m.line(5, 36, a, b, "A")
    m.line(27, 24, 31, 38, "X", 3)
    for (a, b) in ((29, 43), (32, 43), (35, 41)):
        m.line(31, 38, a, b, "A")
    # roots
    for (a, b) in ((10, 66), (17, 67), (24, 66), (30, 65)):
        m.line(19, 59, a, b, "x", 2)
    return pk.make_sprite(m.rows(), MAT)


def idol():
    """Идол у ворот (was «чур») / wooden idol of the капище: carved pillar with a stern face and cap."""
    m = pk.MatCanvas(18, 58)
    m.rect(4, 8, 10, 50, "X")
    m.poly([(3, 9), (15, 9), (13, 3), (9, 0), (5, 3)], "z")         # cap (bronze-stained)
    m.rect(3, 8, 12, 2, "Z")
    m.line(6, 15, 8, 15, "k"); m.line(10, 15, 12, 15, "k")            # brows/eyes
    m.px(6, 16, "E"); m.px(11, 16, "E")
    m.line(9, 16, 9, 21, "x")                                          # nose
    m.line(6, 24, 12, 24, "k")                                         # mouth
    m.poly([(5, 25), (13, 25), (12, 34), (6, 34)], "x")               # beard
    m.rect(4, 37, 10, 2, "Z")                                          # belt
    m.line(4, 28, 3, 40, "x"); m.line(14, 28, 15, 40, "x")             # arms
    m.rect(7, 42, 4, 3, "Z")                                           # horn/cup
    return pk.make_sprite(m.rows(), MAT)


def horse_head():
    """Конёк — carved horse head on the cabin ridge (faces right)."""
    m = pk.MatCanvas(14, 13)
    m.poly([(0, 12), (3, 4), (6, 1), (10, 1), (13, 4), (12, 6), (8, 5), (6, 12)], "X")
    m.px(9, 2, "k"); m.poly([(4, 1), (6, 3), (3, 4)], "x")
    return pk.make_sprite(m.rows(), MAT)


def dragon_prow():
    """Ладья stem head (змей), faces left."""
    m = pk.MatCanvas(30, 26)
    m.poly([(22, 25), (28, 25), (26, 14), (22, 8), (17, 6), (16, 11), (21, 14)], "X")  # stem
    m.ellipse(12, 7, 6.5, 4.5, "X")
    m.poly([(8, 5), (0, 7), (1, 10), (8, 10)], "X")
    m.poly([(1, 10), (8, 10), (8, 12), (2, 12)], "x")
    m.line(1, 10, 8, 10, "k")
    m.px(10, 5, "E"); m.px(3, 9, "y"); m.px(5, 10, "y")
    for sx in (13, 17, 21):
        m.poly([(sx, 4), (sx + 3, 4), (sx + 3, -1)], "A")
    m.line(19, 12, 25, 22, "Z")
    return pk.make_sprite(m.rows(), MAT)


# --------------------------------------------------------------------------
# WORLD-SCALE SPRITES (scale.md §2, frames with fixed pivots)
# --------------------------------------------------------------------------
class SMat:
    """Proxy around MatCanvas that scales/offsets the coordinates of the
    drawing primitives (re-rasterises at the new size instead of resampling
    pixels, so 1-px lines stay 1 px)."""

    def __init__(self, mc, s, src_foot, dst_foot):
        self.m, self.s = mc, s
        self.fx, self.fy = src_foot
        self.dx, self.dy = dst_foot
        self.w, self.h = mc.w, mc.h
        self.a = mc.a

    def X(self, x):
        return (x - self.fx) * self.s + self.dx

    def Y(self, y):
        return (y - self.fy) * self.s + self.dy

    def poly(self, pts, ch):
        self.m.poly([(self.X(x), self.Y(y)) for x, y in pts], ch)

    def ellipse(self, cx, cy, rx, ry, ch):
        self.m.ellipse(self.X(cx), self.Y(cy), rx * self.s, ry * self.s, ch)

    def line(self, x0, y0, x1, y1, ch, w=1):
        self.m.line(self.X(x0), self.Y(y0), self.X(x1), self.Y(y1), ch, max(1, int(round(w * self.s))))

    def rect(self, x, y, w, h, ch):
        x0, x1 = int(round(self.X(x))), int(round(self.X(x + w)))
        y0, y1 = int(round(self.Y(y))), int(round(self.Y(y + h)))
        self.m.rect(x0, y0, max(1, x1 - x0), max(1, y1 - y0), ch)

    def px(self, x, y, ch):
        self.m.px(int(self.X(x + 0.5)), int(self.Y(y + 0.5)), ch)


def _framed(draw, frame, pivot, s, src_foot, target_h=None):
    """Draw `draw(m)` into a frame (w, h) so that the source foot point lands
    on the pivot. MatCanvas is frame-2 (make_sprite adds the 1-px outline).
    The drawing is shifted so its lowest material row is pivot_y-2: the
    outline under the soles then sits exactly on the pivot row. If target_h
    is given, the scale is searched around `s` so the visible height
    (outline included) equals it."""
    fw, fh = frame

    def build(sc):
        mc = pk.MatCanvas(fw - 2, fh - 2)
        draw(SMat(mc, sc, src_foot, (pivot[0] - 1, pivot[1] - 2)))
        rows = np.where((mc.a != ".").any(1))[0]
        dy = (pivot[1] - 2) - rows.max()
        mc.a = np.roll(mc.a, dy, axis=0)
        return mc, rows.max() - rows.min() + 1 + 2
    mc, h = build(s)
    if target_h is not None and h != target_h:
        best = (abs(h - target_h), s)
        for k in range(1, 60):
            for sc in (s + k * 0.004, s - k * 0.004):
                _, hh = build(sc)
                if abs(hh - target_h) < best[0]:
                    best = (abs(hh - target_h), sc)
            if best[0] == 0:
                break
        mc, h = build(best[1])
    spr = pk.make_sprite(mc.rows(), MAT)
    spr["pivot"] = pivot
    return spr


def hero():
    """Дружинник-ведун at world scale: 44 px tall (outline included) in a
    64x64 frame, pivot (32,56), soles on the pivot row. Proportions per
    scale.md §2: helm 0-7 (spire 2), face 7-12, shoulders 13, belt 26,
    knees 35, soles 44; shield 13x15, blade 16 px. Faces right."""
    m = pk.MatCanvas(62, 62)
    cx, y0 = 31, 13                          # material top row (outline above it)
    X = lambda d: cx + d
    Y = lambda y: y0 + y
    # cloak behind (red accent, >30 px² visible)
    m.poly([(X(-6), Y(12)), (X(6), Y(12)), (X(9), Y(22)), (X(10), Y(37)), (X(3), Y(39)), (X(-7), Y(38)), (X(-8), Y(24))], "C")
    m.poly([(X(-8), Y(26)), (X(-6), Y(22)), (X(-5), Y(38)), (X(-7), Y(38))], "c")
    m.poly([(X(7), Y(26)), (X(10), Y(37)), (X(7), Y(38))], "c")
    # legs: stride, right (front) leg forward
    m.poly([(X(-4), Y(30)), (X(-1), Y(30)), (X(-1), Y(39)), (X(-4), Y(39))], "P")
    m.poly([(X(1), Y(30)), (X(4), Y(30)), (X(6), Y(38)), (X(3), Y(39))], "P")
    m.rect(X(-4), Y(34), 3, 5, "W"); m.line(X(-4), Y(36), X(-2), Y(35), "w")     # onuchi (wraps)
    m.poly([(X(3), Y(34)), (X(5), Y(34)), (X(6), Y(38)), (X(3), Y(39))], "W"); m.line(X(3), Y(36), X(5), Y(35), "w")
    m.rect(X(-5), Y(39), 5, 3, "O")                                          # boots
    m.poly([(X(2), Y(39)), (X(6), Y(38)), (X(8), Y(41)), (X(2), Y(41))], "O")
    # mail hauberk + skirt
    m.poly([(X(-6), Y(13)), (X(6), Y(13)), (X(6), Y(24)), (X(7), Y(30)), (X(-7), Y(30)), (X(-6), Y(24))], "M")
    m.rect(X(-7), Y(28), 15, 2, "m")
    m.rect(X(-6), Y(24), 13, 2, "L")                                        # belt
    m.rect(X(0), Y(24), 2, 2, "Z")                                          # buckle
    # head: face, beard, aventail
    m.ellipse(X(0.5), Y(9.5), 3.0, 3.0, "S")
    m.poly([(X(-2), Y(11)), (X(3), Y(11)), (X(3), Y(13)), (X(0), Y(14)), (X(-2), Y(13))], "B")
    m.px(X(-1), Y(9), "k"); m.px(X(2), Y(9), "k")                           # eyes
    m.rect(X(-4), Y(7), 2, 6, "M"); m.rect(X(3), Y(7), 2, 6, "M")          # aventail sides
    # conical helm with spire + bronze band + nasal
    m.poly([(X(-4), Y(7)), (X(5), Y(7)), (X(0.5), Y(1))], "H")
    m.poly([(X(0.5), Y(1)), (X(5), Y(7)), (X(2), Y(7))], "h")
    m.rect(X(0), Y(0), 1, 2, "Z")                                            # spire
    m.rect(X(-4), Y(6), 10, 2, "Z")                                          # brow band
    m.rect(X(0), Y(8), 1, 3, "H")                                            # nasal
    # sword arm raised (screen right), blade 16 px x 2 px
    m.line(X(6), Y(14), X(9), Y(10), "M", 2)
    m.line(X(9), Y(10), X(10), Y(6), "M", 2)
    m.ellipse(X(10.5), Y(5.5), 1.3, 1.3, "S")
    m.line(X(8), Y(4), X(13), Y(7), "Z")                                     # crossguard
    m.px(X(9), Y(8), "Z")                                                    # pommel
    m.line(X(11), Y(4), X(20), Y(-9), "T", 2)                                # blade
    # round shield 13x15 on the left arm, in front of the body (8 painted sectors = solar wheel)
    _shield(m, X(-6), Y(19), 6.5, 7.5)
    spr = pk.make_sprite(m.rows(), MAT)
    spr["pivot"] = (32, 56)
    return spr


def _upyr_draw(m):
    m.poly([(13, 16), (24, 14), (28, 30), (27, 44), (24, 41), (21, 46), (18, 42), (14, 46), (12, 41), (11, 30)], "R")
    m.poly([(22, 18), (27, 30), (26, 42), (23, 40)], "r")
    m.poly([(13, 20), (19, 19), (19, 30), (13, 31)], "U")
    for yy in (22, 26):
        m.line(13, yy, 18, yy - 1, "u")
    m.poly([(12, 13), (19, 12), (17, 19), (12, 19)], "U")
    m.ellipse(10, 12, 5.2, 5.8, "U")
    m.poly([(5, 13), (9, 13), (9, 18), (6, 17)], "U")
    m.px(7, 11, "E"); m.px(10, 11, "E")
    m.line(5, 15, 9, 15, "k"); m.px(6, 14, "y"); m.px(8, 16, "y")
    m.line(6, 16, 6, 19, "Q")
    m.line(11, 7, 14, 6, "u")
    m.line(14, 19, 7, 25, "U", 2); m.line(7, 25, 2, 28, "U", 2)
    for i in range(3):
        m.line(2, 28, -1 + i, 31 + i, "y")
    m.line(19, 20, 13, 28, "U", 2); m.line(13, 28, 8, 32, "U", 2)
    for i in range(3):
        m.line(8, 32, 4 + i, 35 + i // 2, "y")
    m.line(15, 44, 14, 49, "U", 2); m.line(22, 44, 23, 49, "U", 2)
    m.line(12, 49, 15, 49, "u"); m.line(22, 49, 26, 49, "u")


def upyr(s=0.87):
    """Упырь, hunched: 40 px (scale.md §2) in a 64x64 frame, pivot (32,56)."""
    return _framed(_upyr_draw, (64, 64), (32, 56), s, (18.5, 49), target_h=40)


def _volkolak_draw(m):
    m.line(30, 32, 37, 44, "f", 3)
    m.poly([(24, 34), (30, 34), (31, 44), (28, 54), (25, 54), (27, 44)], "f")
    m.poly([(12, 18), (26, 12), (32, 22), (31, 34), (16, 37), (11, 28)], "F")
    m.poly([(18, 14), (26, 11), (30, 16), (22, 18)], "f")
    m.poly([(16, 33), (31, 31), (31, 37), (15, 38)], "R")
    m.poly([(15, 36), (22, 36), (21, 44), (19, 54), (15, 54), (17, 44)], "F")
    m.line(13, 54, 20, 54, "y")
    m.ellipse(10, 15, 6, 5.5, "F")
    m.poly([(6, 13), (0, 15), (0, 18), (2, 20), (8, 20)], "F")
    m.poly([(1, 18), (7, 18), (7, 21), (2, 21)], "f")
    m.line(1, 18, 7, 18, "k"); m.px(2, 17, "y"); m.px(4, 19, "y"); m.px(6, 17, "y")
    m.px(0, 15, "k")
    m.poly([(10, 4), (14, 10), (9, 11)], "F"); m.poly([(6, 6), (9, 11), (5, 12)], "f")
    m.px(7, 13, "e"); m.px(8, 13, "e")
    m.line(15, 20, 9, 28, "F", 3); m.line(9, 28, 5, 33, "F", 3)
    for i in range(3):
        m.line(5, 33, 2 + i, 37, "y")
    m.line(24, 20, 23, 30, "f", 3); m.line(23, 30, 20, 35, "f", 2)


def volkolak(s=1.14):
    """Волколак (крупный): 60 px in a 96x96 frame, pivot (48,88)."""
    return _framed(_volkolak_draw, (96, 96), (48, 88), s, (21, 54), target_h=60)


def _leshy_draw(m):
    for (a, b, c, d) in ((16, 10, 9, 1), (11, 5, 6, 4), (12, 6, 11, 0), (22, 10, 30, 1), (27, 5, 33, 4), (27, 5, 27, 0)):
        m.line(a, b, c, d, "A", 2 if (a, b) in ((16, 10), (22, 10)) else 1)
    m.poly([(12, 20), (26, 20), (29, 40), (26, 60), (13, 60), (9, 40)], "X")
    m.poly([(22, 22), (29, 40), (26, 60), (22, 60)], "x")
    m.ellipse(19, 14, 6.5, 6.5, "X")
    m.px(16, 13, "N"); m.px(21, 13, "N"); m.px(16, 14, "n"); m.px(21, 14, "n")
    m.line(17, 18, 21, 18, "k")
    m.poly([(13, 16), (25, 16), (23, 26), (19, 35), (15, 27)], "V")
    m.poly([(19, 22), (23, 24), (19, 35)], "v")
    m.ellipse(12, 21, 3.5, 2, "V"); m.ellipse(27, 21, 3.5, 2, "V")
    m.ellipse(28, 18.5, 2.5, 1.5, "D"); m.px(27, 18, "y"); m.px(29, 19, "y"); m.rect(28, 20, 1, 1, "W")
    m.line(12, 24, 5, 36, "X", 3)
    for (a, b) in ((0, 38), (2, 41), (5, 41)):
        m.line(5, 36, a, b, "A")
    m.line(27, 24, 31, 38, "X", 3)
    for (a, b) in ((29, 43), (32, 43), (35, 41)):
        m.line(31, 38, a, b, "A")
    for (a, b) in ((10, 66), (17, 67), (24, 66), (30, 65)):
        m.line(19, 59, a, b, "x", 2)


def leshy(s=1.15):
    """Леший-элита («Матёрый»): 80 px with branch antlers, 96x96 frame,
    pivot (48,88), footprint 2x2."""
    return _framed(_leshy_draw, (96, 96), (48, 88), s, (19.5, 66), target_h=80)


def dragon_prow_big():
    """Змей on the bow stem of the 12-tile ладья: 32x40 frame, faces left
    (outboard). The bottom-right of the neck joins the stem post."""
    m = pk.MatCanvas(30, 38)
    # S-curved neck rising from the stem (bottom right) to the head (top left)
    for t in range(0, 41):
        u = t / 40
        x = 24 - 9 * u + 4 * math.sin(u * math.pi * 1.3)
        y = 37 - 27 * u
        w = 5.2 - 1.6 * u
        m.ellipse(x, y, w / 2, 1.2, "X")
    for t in range(0, 41, 2):                                   # shaded back of the neck
        u = t / 40
        x = 24 - 9 * u + 4 * math.sin(u * math.pi * 1.3) + 1.6
        y = 37 - 27 * u
        m.px(int(x), int(y), "x")
    # head with open jaws, facing left
    m.ellipse(12, 9, 6, 4.5, "X")
    m.poly([(8, 6), (0, 8), (0, 10), (8, 10)], "X")            # upper jaw
    m.poly([(1, 12), (8, 11), (9, 14), (3, 14)], "x")          # lower jaw
    m.poly([(1, 10), (8, 10), (8, 11), (1, 12)], "k")          # mouth gap
    m.px(2, 10, "y"); m.px(5, 10, "y"); m.px(3, 12, "y")       # teeth
    m.px(0, 7, "Z")                                            # curled snout tip
    m.px(10, 7, "E"); m.px(11, 7, "E")                         # ember eye
    for sx, sy in ((12, 4), (16, 5), (19, 9), (21, 14), (21, 19)):   # crest spines along the neck
        m.poly([(sx, sy), (sx + 3, sy + 1), (sx + 4, sy - 3)], "A")
    m.line(14, 13, 17, 26, "Z")                                # bronze binding on the neck
    m.line(18, 30, 26, 30, "Z")
    return pk.make_sprite(m.rows(), MAT)



def silver():
    m = pk.MatCanvas(14, 7)
    for (x, y) in ((1, 4), (4, 3), (7, 4), (10, 4), (5, 1), (8, 2), (3, 5), (9, 5)):
        m.ellipse(x + 1, y + 0.5, 1.6, 1, "Y")
    m.px(5, 1, "y"); m.px(8, 2, "y")
    return pk.make_sprite(m.rows(), MAT)


def sword_ground():
    m = pk.MatCanvas(22, 9)
    m.line(6, 6, 21, 0, "T", 2)
    m.line(3, 4, 7, 8, "Z")
    m.line(1, 8, 4, 7, "G")
    m.px(0, 8, "Z")
    return pk.make_sprite(m.rows(), MAT)


def shield_ground():
    m = pk.MatCanvas(14, 8)
    _shield(m, 7, 4, 6.5, 3.4)
    return pk.make_sprite(m.rows(), MAT)


def skull():
    m = pk.MatCanvas(6, 5)
    m.ellipse(2.5, 2, 2.5, 2, "Y"); m.px(1, 2, "k"); m.px(3, 2, "k")
    return pk.make_sprite(m.rows(), MAT)


def build():
    return {"hero": hero(), "hero_doll": hero_doll(), "upyr": upyr(), "volkolak": volkolak(), "leshy": leshy(),
            "idol": idol(), "horse": horse_head(), "prow": dragon_prow(), "prow_big": dragon_prow_big(), "silver": silver(),
            "sword": sword_ground(), "shield": shield_ground(), "skull": skull()}

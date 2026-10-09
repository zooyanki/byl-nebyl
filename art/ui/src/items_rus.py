"""Item icons for the «Гардарики» theme (inventory / equipment / tooltips).
Built with pixelkit.MatCanvas -> make_sprite (auto shading + ink outline).
Sizes are in pixels for a 24-px inventory cell (sprite = canvas + 2 outline)."""
import math
import numpy as np
import pixelkit as pk
from pixelkit import C, MatCanvas
from sprites_rus import MAT

IMAT = dict(MAT)
IMAT.update({
    "a": ("red", 3, True, False), "b": ("blue", 4, True, False), "g": ("bronze", 5, True, False),
    "j": ("nebyl", 3, True, True), "l": ("wood", 3, True, False), "o": ("wood", 4, True, False),
    "p": ("birch", 4, True, False, "grain"), "q": ("birch", 2, False, False),
    "t": ("iron", 5, True, False), "i": ("bronze", 4, True, False), "I": ("bronze", 3, False, False),
    "J": ("iron", 3, True, False, "mail"),
})


def _mk(m):
    return pk.make_sprite(m.rows(), IMAT)


def sword(h=68):
    """Каролингский меч: fullered blade, short guard, leather grip, lobed pommel."""
    m = MatCanvas(18, h)
    cx = 8
    bl = h - 22
    m.poly([(cx - 2, 4), (cx, 0), (cx + 2, 4), (cx + 2, bl), (cx - 2, bl)], "T")
    m.line(cx, 4, cx, bl - 2, "h")                         # fuller
    m.rect(cx - 2, 4, 1, bl - 4, "t")
    m.rect(cx - 7, bl, 15, 3, "Z")                         # crossguard
    m.rect(cx - 1, bl + 3, 3, 11, "l")                     # grip
    for k in range(bl + 4, bl + 14, 2):
        m.rect(cx - 1, k, 3, 1, "L")
    m.rect(cx - 5, bl + 14, 11, 2, "Z")                    # upper guard
    m.ellipse(cx, bl + 18, 2.4, 2.4, "Z"); m.ellipse(cx - 3.5, bl + 18.5, 1.8, 1.8, "Z"); m.ellipse(cx + 3.5, bl + 18.5, 1.8, 1.8, "Z")
    return _mk(m)


def axe(h=68):
    """Бородовидный топор: long haft, bearded head at the top."""
    m = MatCanvas(22, h)
    m.rect(9, 4, 3, h - 6, "X")
    m.rect(9, h - 6, 3, 4, "Z")
    m.poly([(11, 5), (16, 3), (20, 2), (21, 12), (20, 22), (16, 16), (12, 13)], "H")   # bearded blade
    m.line(20, 2, 21, 22, "t")
    m.poly([(5, 6), (9, 5), (9, 11), (5, 10)], "H")         # butt
    m.rect(8, 4, 5, 10, "h")
    m.line(9, 30, 11, 30, "Z"); m.line(9, 46, 11, 46, "Z")
    return _mk(m)


def kolchuga(w=44, h=66):
    """Кольчуга with short sleeves, bronze-rimmed neck and hem."""
    m = MatCanvas(w, h)
    m.poly([(10, 4), (16, 2), (28, 2), (34, 4), (43, 18), (36, 24), (34, 18), (34, 62), (10, 62), (10, 18), (8, 24), (1, 18)], "M")
    m.poly([(34, 18), (34, 62), (30, 62), (30, 20)], "m")
    m.poly([(16, 2), (28, 2), (25, 8), (19, 8)], "k")       # neck opening
    m.line(16, 2, 19, 8, "Z", 1); m.line(28, 2, 25, 8, "Z", 1); m.line(19, 8, 25, 8, "Z")
    m.rect(10, 60, 25, 3, "Z")                              # hem trim
    for k in range(10, 35, 4):
        m.px(k, 63, "Z")
    m.line(1, 18, 8, 24, "Z"); m.line(43, 18, 36, 24, "Z")  # sleeve trim
    m.rect(10, 36, 25, 3, "L"); m.rect(20, 36, 4, 3, "Z")   # belt
    return _mk(m)


def round_shield(d=44, kind="gromovnik"):
    """Round shield: red-painted planks with a birch-white rosette (six-petal
    rosette in a ring, GDD §12.1.1 A5: no crosses), iron rim, bronze boss.
    kind="plain" gives unpainted planks."""
    m = MatCanvas(d, d)
    r = d / 2 - 0.5
    yy, xx = np.mgrid[0:d, 0:d]
    dd = np.hypot(xx - r, yy - r)
    inside = dd <= r
    if kind == "gromovnik":
        m.a[inside] = "D"
        rho = r - 6.5                                        # rosette radius
        petals = np.zeros_like(inside)
        for k in range(6):
            t = k * math.pi / 3 + math.pi / 6
            c1 = (r + rho * math.cos(t - math.pi / 3), r + rho * math.sin(t - math.pi / 3))
            c2 = (r + rho * math.cos(t + math.pi / 3), r + rho * math.sin(t + math.pi / 3))
            petals |= (np.hypot(xx - c1[0], yy - c1[1]) <= rho) & (np.hypot(xx - c2[0], yy - c2[1]) <= rho)
        m.a[petals] = "d"
        m.a[inside & (np.abs(dd - (rho + 1.6)) < 0.75)] = "d"    # ring around the rosette
    else:
        m.a[inside] = "X"
    m.a[inside & (np.mod(xx, 7) == 0) & (dd < r - 3) & (m.a != "d")] = "c"     # plank seams
    m.a[inside & (dd > r - 2.2)] = "H"
    m.a[(dd <= 3.6)] = "Z"; m.a[(dd <= 1.6)] = "i"
    for k in range(8):
        a = k * math.pi / 4
        m.px(int(r + math.cos(a) * (r - 1)), int(r + math.sin(a) * (r - 1)), "t")
    return _mk(m)


def scramasax(h=54):
    """Скрамасакс: single-edged long knife, broken back, short guard, wooden grip."""
    m = MatCanvas(14, h)
    cx = 6
    bl = h - 16
    m.poly([(cx - 2, bl), (cx - 2, 8), (cx + 1, 0), (cx + 3, 10), (cx + 3, bl)], "T")
    m.line(cx + 1, 10, cx + 1, bl - 2, "h")
    m.rect(cx - 4, bl, 10, 2, "Z")
    m.rect(cx - 1, bl + 2, 4, 11, "X")
    for k in range(bl + 3, bl + 13, 3):
        m.rect(cx - 1, k, 4, 1, "Z")
    m.rect(cx - 2, bl + 13, 6, 2, "Z")
    return _mk(m)


def steganka(w=44, h=60):
    """Стёганка: quilted linen gambeson, wood-brown trim."""
    m = MatCanvas(w, h)
    m.poly([(10, 4), (16, 2), (28, 2), (34, 4), (43, 18), (36, 24), (34, 18), (34, h - 4), (10, h - 4), (10, 18), (8, 24), (1, 18)], "Y")
    m.poly([(34, 18), (34, h - 4), (30, h - 4), (30, 20)], "w")
    for x in range(13, 33, 4):                                   # quilting seams
        m.line(x, 9, x, h - 6, "q")
    for y in range(16, h - 6, 10):
        m.line(11, y, 33, y, "q")
    m.poly([(16, 2), (28, 2), (25, 8), (19, 8)], "k")
    m.line(16, 2, 19, 8, "L"); m.line(28, 2, 25, 8, "L"); m.line(19, 8, 25, 8, "L")
    m.line(22, 8, 22, h - 5, "L")                                # front opening
    m.rect(10, h - 6, 25, 2, "L")
    m.line(1, 18, 8, 24, "L"); m.line(43, 18, 36, 24, "L")
    return _mk(m)


def shapka(w=26, h=22):
    """Войлочная шапка: felt cap with a fur band."""
    m = MatCanvas(w, h)
    m.ellipse(12.5, 11, 9.5, 10, "D")
    m.poly([(13, 1), (18, 4), (21, 9), (22, 13), (14, 13)], "c")
    m.rect(1, 13, 24, 7, "F")
    m.rect(1, 18, 24, 2, "f")
    m.px(12, 1, "Z"); m.px(13, 1, "Z")
    return _mk(m)


def porshni():
    """Поршни: low leather shoes with lacing."""
    m = MatCanvas(24, 16)
    for ox in (0, 12):
        m.poly([(ox + 2, 4), (ox + 8, 4), (ox + 9, 9), (ox + 11, 11), (ox + 11, 14), (ox + 1, 14), (ox + 1, 8)], "l")
        m.rect(ox + 1, 13, 11, 2, "L")
        for y in (6, 9):
            m.line(ox + 3, y, ox + 7, y + 1, "q")
    return _mk(m)


def kushak(w=40):
    """Кушак: red woven sash with a knot and tassels."""
    m = MatCanvas(w, 14)
    m.rect(0, 3, w, 6, "D")
    m.rect(0, 8, w, 1, "c")
    for k in range(2, w, 5):
        m.px(k, 5, "d")
    m.ellipse(w - 9, 6, 3.5, 3.5, "D")
    m.line(w - 11, 9, w - 13, 13, "c"); m.line(w - 8, 9, w - 7, 13, "c")
    return _mk(m)


def beresta():
    """Береста (1x1, stacks to 20): small rolled strip of birch bark with a cord."""
    m = MatCanvas(18, 16)
    m.poly([(2, 4), (15, 2), (16, 12), (3, 14)], "p")
    m.ellipse(2.5, 9, 2.5, 5, "o"); m.ellipse(2.5, 9, 1, 3, "L")
    m.ellipse(15.5, 7, 2, 5, "o")
    for y in (6, 9):
        m.line(6, y, 12, y - 1, "q")
    m.line(9, 2, 9, 14, "C")
    return _mk(m)


def beresta_v2():
    """Береста возврата v2 (08.10, M1c): diagonal birch roll, bronze wire, burning ember rhomb, no red cord.
    Drawn in art/sprites/src/beresta.py (same drawing as art/sprites/item_beresta/item_beresta_icon.png)."""
    import os
    import sys
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sprites", "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    import beresta as _B
    return _B.icon_sprite()


def shelom(w=26, h=28):
    """Конический шелом с наносником и бармицей."""
    m = MatCanvas(w, h)
    m.poly([(3, 15), (5, 8), (9, 3), (13, 0), (17, 3), (21, 8), (23, 15)], "H")   # ogival cone
    m.poly([(13, 1), (17, 3), (21, 8), (23, 15), (16, 15)], "h")
    m.rect(2, 14, 23, 3, "Z")
    for k in range(4, 24, 4):
        m.px(k, 15, "g")
    m.px(13, 0, "Z")
    m.rect(12, 17, 3, 6, "H")                                   # nasal
    m.poly([(3, 17), (10, 17), (10, 20), (7, 25), (4, 24)], "M")  # aventail
    m.poly([(16, 17), (23, 17), (22, 24), (19, 25), (16, 20)], "m")
    m.line(13, 4, 13, 13, "Z")
    return _mk(m)


def grivna(d=20):
    """Витая гривна (twisted bronze torc) with knot terminals."""
    m = MatCanvas(d, d)
    c = (d - 1) / 2
    yy, xx = np.mgrid[0:d, 0:d]
    dd = np.hypot(xx - c, yy - c)
    ang = np.arctan2(yy - c, xx - c)
    ring = (dd >= c - 3) & (dd <= c) & ~((ang > 1.15) & (ang < 2.0))
    m.a[ring] = "Z"
    tw = ring & (np.mod((ang * 9 + dd * 0.9), 2) < 0.8)
    m.a[tw] = "i"
    for a in (1.05, 2.1):
        m.ellipse(c + math.cos(a) * (c - 1.5), c + math.sin(a) * (c - 1.5), 1.8, 1.8, "g")
    return _mk(m)


def obereg(kind="lunnitsa"):
    """Обереги: лунница (crescent pendant) or rosette disc on a cord."""
    m = MatCanvas(18, 18)
    if kind == "lunnitsa":
        yy, xx = np.mgrid[0:18, 0:18]
        outer = np.hypot(xx - 8.5, yy - 7) <= 8
        inner = np.hypot(xx - 8.5, yy - 2) <= 7.5
        m.a[outer & ~inner & (yy > 4)] = "Z"
        for x in (4, 8, 13):
            m.px(x, 15, "g")
        m.line(8, 0, 8, 6, "q"); m.ellipse(8.5, 6, 1.4, 1.2, "i")
    else:
        yy, xx = np.mgrid[0:18, 0:18]
        dd = np.hypot(xx - 8.5, yy - 10)
        m.a[dd <= 7] = "Z"
        for k in range(6):
            a = k * math.pi / 3
            m.line(8.5, 10, 8.5 + math.cos(a) * 6, 10 + math.sin(a) * 6, "i")
        m.a[dd <= 1.5] = "g"
        m.line(8, 0, 8, 3, "q")
    return _mk(m)


def ring(gem="a"):
    m = MatCanvas(14, 14)
    yy, xx = np.mgrid[0:14, 0:14]
    dd = np.hypot(xx - 6.5, yy - 8)
    m.a[(dd >= 3.2) & (dd <= 5.6)] = "Z"
    m.ellipse(6.5, 3, 2.6, 2.2, "Z"); m.ellipse(6.5, 3, 1.6, 1.4, gem)
    return _mk(m)


def rukavitsy():
    """Leather mittens with mail cuffs."""
    m = MatCanvas(22, 22)
    m.ellipse(7, 7, 5, 6.5, "l"); m.ellipse(1.8, 9, 1.8, 3, "o")          # mitten + thumb
    m.rect(2, 13, 10, 7, "M"); m.rect(2, 12, 10, 1, "Z")
    m.ellipse(16, 9, 5, 6.5, "l"); m.ellipse(21, 11, 1.6, 3, "o")
    m.rect(11, 15, 10, 7, "m"); m.rect(11, 14, 10, 1, "Z")
    m.line(5, 3, 8, 3, "o"); m.line(14, 5, 17, 5, "o")
    return _mk(m)


def poyas(w=40):
    """Наборный пояс: leather strap with bronze plaques and a buckle."""
    m = MatCanvas(w, 12)
    m.rect(0, 3, w, 6, "l")
    m.rect(0, 8, w, 1, "L")
    for k in range(3, w - 10, 6):
        m.rect(k, 4, 3, 4, "Z"); m.px(k + 1, 5, "g")
    m.rect(w - 9, 1, 8, 10, "Z"); m.rect(w - 7, 3, 4, 6, "k"); m.rect(w - 6, 3, 1, 6, "i")
    m.poly([(4, 9), (8, 9), (7, 12), (5, 12)], "Z")          # strap end
    return _mk(m)


def sapogi():
    """Leather boots."""
    m = MatCanvas(24, 24)
    for ox in (0, 12):
        m.poly([(ox + 2, 1), (ox + 8, 1), (ox + 8, 16), (ox + 11, 19), (ox + 11, 22), (ox + 1, 22), (ox + 2, 14)], "l")
        m.rect(ox + 2, 1, 7, 2, "o")
        m.rect(ox + 1, 21, 11, 2, "L")
        m.line(ox + 3, 6, ox + 7, 6, "L")
    return _mk(m)


def gramota():
    """Берестяная грамота: strip of birch bark with scratched letters (2x1)."""
    m = MatCanvas(44, 18)
    m.poly([(4, 3), (40, 1), (41, 15), (5, 17)], "p")
    m.ellipse(4, 10, 3.5, 7.5, "o"); m.ellipse(4, 10, 1.5, 5, "L")      # rolled ends show tan inner bark
    m.ellipse(40.5, 8, 3, 7.5, "o"); m.ellipse(40.5, 8, 1.2, 5, "L")
    for k in range(3):                                                  # scratched letters
        y = 6 + k * 4
        x = 10
        while x < 34:
            ln = 1 + (x * 7 + k * 3) % 3
            m.line(x, y + (x % 2), x + ln - 1, y + (x % 2), "q")
            if (x + k) % 3 == 0:
                m.line(x, y - 1, x, y + 1, "q")
            x += ln + 1
    for x in (14, 27):                                                  # lenticels
        m.line(x, 3, x + 3, 3, "k")
    return _mk(m)


def gem(kind):
    mat = {"ruby": "a", "sapphire": "b", "amber": "g", "nebyl": "j"}[kind]
    m = MatCanvas(12, 12)
    m.poly([(3, 0), (8, 0), (11, 4), (6, 11), (0, 4)], mat)
    m.line(0, 4, 11, 4, "y" if kind != "nebyl" else "j")
    m.px(3, 2, "y"); m.px(4, 1, "y")
    return _mk(m)


# ---- GDD v1.4 (A13) base renames: new icons; the older functions above are kept for v2a-v2d ----
def shelom_klep(w=26, h=26):
    """Клёпаный шелом (head_1, v1.4; was «Шелом-шишак»): the same ogival cone, built from
    riveted plates; no nasal (the nasal belongs to tier 2 «Шелом с наносником»)."""
    m = MatCanvas(w, h)
    m.poly([(3, 15), (5, 8), (9, 3), (13, 0), (17, 3), (21, 8), (23, 15)], "H")
    m.poly([(13, 1), (17, 3), (21, 8), (23, 15), (16, 15)], "h")
    m.rect(2, 14, 23, 3, "L")                                   # leather brow band
    for (x0, y0, x1, y1) in ((13, 1, 8, 14), (13, 1, 18, 14)):  # plate seams with rivets
        m.line(x0, y0, x1, y1, "Z")
    for (x, y) in ((11, 5), (10, 9), (9, 12), (15, 5), (16, 9), (17, 12)):
        m.px(x, y, "t")
    for k in range(4, 24, 4):
        m.px(k, 15, "t")                                        # rivets on the band
    m.px(13, 0, "Z")
    m.poly([(3, 17), (10, 17), (10, 20), (7, 24), (4, 23)], "M")  # aventail
    m.poly([(16, 17), (23, 17), (22, 23), (19, 24), (16, 20)], "m")
    return _mk(m)


def rukavitsy_kozh():
    """Кожаные рукавицы (gloves_1): plain leather mittens with leather cuffs."""
    m = MatCanvas(22, 22)
    m.ellipse(7, 7, 5, 6.5, "l"); m.ellipse(1.8, 9, 1.8, 3, "o")
    m.rect(2, 13, 10, 7, "L"); m.rect(2, 12, 10, 1, "o")
    m.ellipse(16, 9, 5, 6.5, "l"); m.ellipse(21, 11, 1.6, 3, "o")
    m.rect(11, 15, 10, 7, "L"); m.rect(11, 14, 10, 1, "o")
    m.line(5, 3, 8, 3, "o"); m.line(14, 5, 17, 5, "o")
    m.line(3, 16, 10, 16, "q"); m.line(12, 18, 19, 18, "q")    # stitching
    return _mk(m)


def rukavitsy_boevye():
    """Боевые рукавицы (gloves_2, v1.4; was «Кольчужные рукавицы»): leather gauntlets
    with riveted iron plates (бляхи) over the back of the hand and the cuff."""
    m = MatCanvas(22, 22)
    m.ellipse(7, 7, 5, 6.5, "l"); m.ellipse(1.8, 9, 1.8, 3, "o")
    m.rect(2, 12, 10, 8, "L")
    m.ellipse(16, 9, 5, 6.5, "l"); m.ellipse(21, 11, 1.6, 3, "o")
    m.rect(11, 14, 10, 8, "L")
    for (x, y) in ((4, 4), (8, 4), (4, 8), (8, 8)):              # plates on the left mitt
        m.rect(x, y, 3, 3, "H"); m.px(x + 1, y + 1, "t")
    for (x, y) in ((13, 6), (17, 6), (13, 10), (17, 10)):
        m.rect(x, y, 3, 3, "h"); m.px(x + 1, y + 1, "t")
    for x in (3, 7):                                             # cuff splints
        m.rect(x, 13, 3, 6, "H")
    for x in (12, 16):
        m.rect(x, 15, 3, 6, "h")
    return _mk(m)


def poyas_kozh(w=40):
    """Кожаный пояс (belt_1, v1.4; was «Кушак»): plain leather strap, iron buckle, hanging tongue."""
    m = MatCanvas(w, 14)
    m.rect(0, 3, w, 6, "l")
    m.rect(0, 8, w, 1, "L")
    m.line(0, 4, w - 1, 4, "o")
    m.rect(w - 12, 1, 7, 10, "H"); m.rect(w - 10, 3, 3, 6, "k"); m.rect(w - 9, 3, 1, 6, "h")   # iron buckle
    m.poly([(w - 6, 6), (w - 1, 6), (w - 1, 13), (w - 4, 13)], "l")                            # hanging tongue
    m.px(w - 3, 12, "t")                                                                       # iron tip
    for k in range(4, w - 14, 6):
        m.px(k, 6, "L")                                                                        # punched holes
    return _mk(m)


def doshchataya(w=44, h=66):
    """Дощатая броня (body_3, v1.4; was «Кольчуга с зерцалом»): mail shirt with a corselet
    of narrow iron plates (дощечки) laced over the chest and belly."""
    m = MatCanvas(w, h)
    m.poly([(10, 4), (16, 2), (28, 2), (34, 4), (43, 18), (36, 24), (34, 18), (34, 62), (10, 62), (10, 18), (8, 24), (1, 18)], "M")
    m.poly([(34, 18), (34, 62), (30, 62), (30, 20)], "m")
    m.poly([(16, 2), (28, 2), (25, 8), (19, 8)], "k")
    for r in range(5):                                           # rows of lamellae
        y = 12 + r * 8
        for c in range(6):
            x = 11 + c * 4
            m.rect(x, y, 3, 7, "H" if x < 28 else "h")
            m.px(x + 1, y + 1, "t")
        m.line(11, y + 7, 34, y + 7, "L")                        # lacing
    m.rect(10, 60, 25, 3, "Z")
    return _mk(m)


def build():
    return {
        "sword": sword(), "axe": axe(), "kolchuga": kolchuga(), "shield": round_shield(),
        "shield_sm": round_shield(36), "shelom": shelom(), "grivna": grivna(),
        "lunnitsa": obereg("lunnitsa"), "gromovnik": obereg("gromovnik"),
        "ring_ruby": ring("a"), "ring_amber": ring("g"), "rukavitsy": rukavitsy(),
        "poyas": poyas(), "sapogi": sapogi(), "gramota": gramota(),
        "gem_ruby": gem("ruby"), "gem_sapphire": gem("sapphire"), "gem_amber": gem("amber"),
        "gem_nebyl": gem("nebyl"), "sword_eq": sword(70), "kolchuga_eq": kolchuga(44, 60),
        "shield_small": round_shield(34), "scramasax": scramasax(), "steganka": steganka(),
        "shapka": shapka(), "porshni": porshni(), "kushak": kushak(), "beresta": beresta_v2(),   # v1: beresta() (red cord, read like the грамота)
        # v1.4 names (GDD §6.2, A13)
        "shelom_klep": shelom_klep(), "rukavitsy_kozh": rukavitsy_kozh(), "rukavitsy_boevye": rukavitsy_boevye(),
        "poyas_kozh": poyas_kozh(), "doshchataya": doshchataya(),
    }


RARITY = {  # name colour, cell tint
    "normal": ("linen", "slate_dk"),
    "magic": ("blue_lt", "blue_dk"),
    "rare": ("flame", "bronze_dk"),
    "unique": ("bronze_lt", "wood"),
    "nebyl": ("nebyl", "nebyl_dk"),
    "quest": ("ember", "red_dk"),
}


def draw_item(cv, spr, x, y, w, h, rarity=None, tint=0.3):
    if rarity:
        cv.dither(x + 1, y + 1, w - 2, h - 2, C[RARITY[rarity][1]], tint)
    if callable(spr):
        spr(cv, x, y, w, h)
        return
    idx = pk.sprite_to_index(spr)
    cv.blit(idx, x + (w - spr["w"]) // 2, y + (h - spr["h"]) // 2)

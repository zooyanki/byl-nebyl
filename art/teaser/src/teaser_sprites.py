"""Teaser sprites (scale.md §2): hero poses 44 px (64x64, pivot 32,56), upyr variants 40 px,
волколак leap (96x96, pivot 48,88), Чернояр-Лютоволк 104 standing / ~80 kneeling
(128x144, pivot 64,132), loot (prince's sword 24, staff ~30, pelt 36x10).
Hero handedness: faces right; sword in the right hand (screen-left/back side),
shield on the left arm (screen-right, toward the enemy)."""
import math
import numpy as np
import pixelkit as pk
import sprites_rus as SR
from sprites_rus import MAT, _shield, SMat

TM = dict(MAT)
TM.update({
    "b": ("fur", 3, True, False, "fur"),      # black wolf pelt (Лютоволк)
    "j": ("fur", 2, False, False, "fur"),     # pelt shadow
    "I": ("birch", 3, True, False),           # volkhv shirt (grey linen)
    "i": ("birch", 2, False, False),
    "g": ("bronze", 4, True, False),          # bright bronze (prince's hilt)
})


def _mk(m):
    return pk.make_sprite(m.rows(), TM)


def _framed(draw, frame, pivot, s, src_foot, target_h=None):
    """sprites_rus._framed with the teaser material table (TM)."""
    fw, fh = frame

    def build(sc):
        mc = pk.MatCanvas(fw - 2, fh - 2)
        draw(SMat(mc, sc, src_foot, (pivot[0] - 1, pivot[1] - 2)))
        rows = np.where((mc.a != ".").any(1))[0]
        mc.a = np.roll(mc.a, (pivot[1] - 2) - rows.max(), axis=0)
        return mc, rows.max() - rows.min() + 1 + 2
    mc, h = build(s)
    if target_h is not None and h != target_h:
        best = (abs(h - target_h), s)
        for k in range(1, 80):
            for sc in (s + k * 0.004, s - k * 0.004):
                _, hh = build(sc)
                if abs(hh - target_h) < best[0]:
                    best = (abs(hh - target_h), sc)
            if best[0] == 0:
                break
        mc, h = build(best[1])
    spr = _mk(mc)
    spr["pivot"] = pivot
    return spr


# --------------------------------------------------------------------------
# HERO
# --------------------------------------------------------------------------
POSES = {
    # sword arm: shoulder -> elbow -> hand; blade from hand to tip; shield centre; cloak polygon; stride
    "swing":  dict(elbow=(-9, 8), hand=(-6, 3), tip=(-12, -12), guard=1, shield=(6, 18), lean=0,
                   cloak=[(-6, 12), (5, 12), (5, 24), (0, 36), (-8, 39), (-15, 33), (-16, 24), (-11, 17)], stride=2),
    "guard":  dict(elbow=(-9, 19), hand=(-10, 25), tip=(-19, 38), guard=1, shield=(6, 11), lean=0,
                   cloak=[(-6, 12), (6, 12), (8, 24), (8, 37), (0, 39), (-8, 38), (-9, 24)], stride=3),
    "cast":   dict(elbow=(2, 17), hand=(10, 14), tip=(26, 16), guard=1, shield=(1, 19), lean=0,
                   cloak=[(-6, 12), (5, 12), (4, 24), (-1, 37), (-9, 39), (-14, 32), (-13, 22)], stride=2),
    "over":   dict(elbow=(-7, 5), hand=(-2, -1), tip=(-11, -13), guard=1, shield=(7, 25), lean=1,
                   cloak=[(-6, 12), (5, 12), (6, 25), (4, 36), (1, 39), (-2, 36), (-4, 40), (-7, 37), (-9, 40), (-10, 30), (-9, 20)],
                   stride=2, ragged=True),
    "idle":   dict(elbow=(-8, 20), hand=(-8, 25), tip=(-9, 41), guard=1, shield=(6, 20), lean=0,
                   cloak=[(-6, 12), (6, 12), (8, 24), (8, 37), (5, 39), (2, 37), (-1, 40), (-4, 37), (-7, 39), (-9, 30), (-8, 20)],
                   stride=1, ragged=True),
}


def hero_pose(pose):
    """Ратибор at world scale, 44 px from the helm spire to the soles
    (outline included), frame 64x64, pivot (32,56), soles on the pivot row."""
    p = POSES[pose]
    m = pk.MatCanvas(62, 62)
    cx, y0 = 31, 13
    lean = p["lean"]
    X = lambda d: cx + d
    Y = lambda y: y0 + y
    XU = lambda d, y: cx + d + (lean if y < 24 else 0)          # upper body leans forward
    # cloak behind everything
    m.poly([(XU(x, y), Y(y)) for x, y in p["cloak"]], "C")
    cl = p["cloak"]
    m.poly([(XU(cl[-1][0], cl[-1][1]), Y(cl[-1][1])), (XU(-6, 14), Y(14)), (XU(-6, 30), Y(30)), (XU(cl[-3][0], cl[-3][1]), Y(cl[-3][1]))], "c")
    # sword (behind the head when raised)
    sx, sy = 0, 0
    hx, hy = p["hand"]; tx, ty = p["tip"]
    raised = ty < hy
    def draw_sword():
        dx, dy = tx - hx, ty - hy
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        bx, by = hx + ux * 2, hy + uy * 2                     # blade starts just past the guard
        m.line(XU(bx, by), Y(by), XU(tx, ty), Y(ty), "T", 2)
        gx, gy = -uy * 3, ux * 3                               # crossguard perpendicular
        m.line(XU(hx + ux * 1.2 + gx, hy + uy * 1.2 + gy), Y(hy + uy * 1.2 + gy), XU(hx + ux * 1.2 - gx, hy + uy * 1.2 - gy), Y(hy + uy * 1.2 - gy), "Z")
        m.px(int(round(XU(hx - ux * 2, hy - uy * 2))), int(round(Y(hy - uy * 2))), "Z")    # pommel
    if raised:
        draw_sword()
    # legs
    st = p["stride"]
    m.poly([(X(-4), Y(30)), (X(-1), Y(30)), (X(-1 - st // 2), Y(39)), (X(-4 - st // 2), Y(39))], "P")      # back leg
    m.poly([(X(1), Y(30)), (X(4), Y(30)), (X(4 + st), Y(38)), (X(1 + st), Y(39))], "P")                 # front leg
    m.rect(X(-4 - st // 2), Y(34), 3, 5, "W"); m.line(X(-4 - st // 2), Y(36), X(-2 - st // 2), Y(35), "w")
    m.poly([(X(1 + st), Y(34)), (X(3 + st), Y(34)), (X(4 + st), Y(38)), (X(1 + st), Y(39))], "W"); m.line(X(1 + st), Y(36), X(3 + st), Y(35), "w")
    m.rect(X(-5 - st // 2), Y(39), 5, 3, "O")
    m.poly([(X(st), Y(39)), (X(4 + st), Y(38)), (X(6 + st), Y(41)), (X(st), Y(41))], "O")
    # hauberk, skirt, belt
    m.poly([(XU(-6, 13), Y(13)), (XU(6, 13), Y(13)), (X(6), Y(24)), (X(7), Y(30)), (X(-7), Y(30)), (X(-6), Y(24))], "M")
    m.rect(X(-7), Y(28), 15, 2, "m")
    m.rect(X(-6), Y(24), 13, 2, "L")
    m.rect(X(0), Y(24), 2, 2, "Z")
    # head (3/4 to the right): face, beard, aventail, conical helm with nasal
    m.ellipse(XU(1.5, 9), Y(9.5), 3.0, 3.0, "S")
    m.poly([(XU(-1, 11), Y(11)), (XU(4, 11), Y(11)), (XU(4, 13), Y(13)), (XU(1, 14), Y(14)), (XU(-1, 13), Y(13))], "B")
    m.px(int(XU(1, 9)), Y(9), "k"); m.px(int(XU(3, 9)), Y(9), "k")
    m.rect(XU(-4, 7), Y(7), 3, 6, "M"); m.rect(XU(4, 7), Y(7), 1, 5, "M")
    m.poly([(XU(-4, 7), Y(7)), (XU(5, 7), Y(7)), (XU(0.5, 1), Y(1))], "H")
    m.poly([(XU(0.5, 1), Y(1)), (XU(5, 7), Y(7)), (XU(2, 7), Y(7))], "h")
    m.rect(XU(0, 0), Y(0), 1, 2, "Z")
    m.rect(XU(-4, 6), Y(6), 10, 2, "Z")
    m.rect(XU(2, 8), Y(8), 1, 3, "H")
    # sword arm (right arm, screen-left side)
    ex, ey = p["elbow"]
    m.line(XU(-6, 14), Y(14), XU(ex, ey), Y(ey), "M", 2)
    m.line(XU(ex, ey), Y(ey), XU(hx, hy), Y(hy), "M", 2)
    m.ellipse(XU(hx, hy), Y(hy), 1.3, 1.3, "S")
    if not raised:
        draw_sword()
    # shield on the left arm (13x15, red/birch solar wheel), toward the enemy
    shx, shy = p["shield"]
    _shield(m, XU(shx, shy), Y(shy), 6.5, 7.5)
    spr = _mk(m)
    spr["pivot"] = (32, 56)
    # material coords of the blade tip, for effects (fire ball on the tip)
    spr["tip"] = (XU(tx, ty) + 1 - 32, Y(ty) + 1 - 56)
    return spr


# --------------------------------------------------------------------------
# UPYR variants (40 px, 64x64, pivot 32,56). Face left, toward the hero.
# --------------------------------------------------------------------------
def _upyr_lunge(m):
    """Lunge: torso pitched forward, both clawed arms thrust at the hero."""
    m.poly([(13, 16), (24, 14), (28, 30), (27, 44), (24, 41), (21, 46), (18, 42), (14, 46), (12, 41), (11, 30)], "R")
    m.poly([(22, 18), (27, 30), (26, 42), (23, 40)], "r")
    m.poly([(13, 20), (19, 19), (19, 30), (13, 31)], "U")
    for yy in (22, 26):
        m.line(13, yy, 18, yy - 1, "u")
    m.poly([(12, 13), (19, 12), (17, 19), (12, 19)], "U")
    m.ellipse(9, 13, 5.2, 5.8, "U")
    m.poly([(3, 14), (8, 14), (8, 19), (4, 18)], "U")
    m.px(6, 12, "E"); m.px(9, 12, "E")
    m.line(3, 16, 8, 16, "k"); m.px(4, 15, "y"); m.px(7, 17, "y")
    m.line(15, 18, 6, 21, "U", 2); m.line(6, 21, -2, 21, "U", 2)              # upper arm thrust forward
    for i in range(3):
        m.line(-2, 21, -6, 19 + i * 2, "y")
    m.line(19, 21, 11, 25, "U", 2); m.line(11, 25, 2, 27, "U", 2)
    for i in range(3):
        m.line(2, 27, -2, 25 + i * 2, "y")
    m.line(15, 44, 12, 49, "U", 2); m.line(22, 44, 25, 49, "U", 2)           # wide lunging stance
    m.line(10, 49, 13, 49, "u"); m.line(24, 49, 28, 49, "u")


def _upyr_shamble(m):
    """Shambling: hunched, arms hanging loose to the knees."""
    m.poly([(13, 16), (24, 14), (27, 30), (26, 44), (23, 41), (21, 46), (18, 42), (15, 46), (13, 41), (12, 30)], "R")
    m.poly([(22, 18), (26, 30), (25, 42), (22, 40)], "r")
    m.poly([(14, 20), (20, 19), (20, 30), (14, 31)], "U")
    for yy in (22, 26):
        m.line(14, yy, 19, yy - 1, "u")
    m.poly([(13, 13), (20, 12), (18, 19), (13, 19)], "U")
    m.ellipse(11, 13, 5.2, 5.8, "U")
    m.poly([(6, 14), (10, 14), (10, 19), (7, 18)], "U")
    m.px(8, 12, "E"); m.px(11, 12, "E")
    m.line(6, 16, 10, 16, "k"); m.px(7, 15, "y")
    m.line(14, 19, 11, 28, "U", 2); m.line(11, 28, 10, 37, "U", 2)            # hanging arms
    for i in range(3):
        m.line(10, 37, 8 + i, 40, "y")
    m.line(20, 20, 20, 29, "U", 2); m.line(20, 29, 18, 38, "U", 2)
    for i in range(3):
        m.line(18, 38, 16 + i, 41, "y")
    m.line(16, 44, 15, 49, "U", 2); m.line(22, 44, 23, 49, "U", 2)
    m.line(13, 49, 16, 49, "u"); m.line(22, 49, 26, 49, "u")


def upyr_lunge():
    return _framed(_upyr_lunge, (64, 64), (32, 56), 0.87, (18.5, 49), target_h=40)


def upyr_shamble():
    return _framed(_upyr_shamble, (64, 64), (32, 56), 0.87, (19, 49), target_h=40)


def _upyr_emerge(m):
    """Climbing out of the ground: head, shoulders and one clawed arm on the
    ground (frame 2 of 6); drawn as the full upper body, the scene clips it."""
    m.poly([(12, 18), (25, 16), (28, 32), (11, 33)], "R")
    m.poly([(14, 21), (21, 20), (21, 32), (14, 33)], "U")
    m.poly([(13, 14), (21, 13), (19, 20), (13, 20)], "U")
    m.ellipse(11, 12, 5.2, 5.8, "U")
    m.poly([(5, 13), (10, 13), (10, 18), (6, 17)], "U")
    m.px(8, 11, "E"); m.px(11, 11, "E")
    m.line(5, 15, 10, 15, "k"); m.px(6, 14, "y"); m.px(9, 16, "y")
    m.line(14, 20, 6, 26, "U", 2); m.line(6, 26, -2, 30, "U", 2)              # arm reaching onto the ground
    for i in range(3):
        m.line(-2, 30, -6 + i * 2, 33, "y")
    m.line(22, 21, 26, 30, "u", 2)


def upyr_emerge():
    # same scale as the 40-px upyr; visible part is cut by the ground line in the scene
    return _framed(_upyr_emerge, (64, 64), (32, 56), 0.87 * 1.0, (16, 49))


# --------------------------------------------------------------------------
# VOLKOLAK leap (scene 3)
# --------------------------------------------------------------------------
def _volk_leap(m):
    """Leap toward the hero (left): body stretched diagonally, forelegs and
    claws forward, jaws open, hind legs trailing up-right."""
    m.poly([(14, 18), (28, 10), (40, 8), (46, 14), (42, 24), (28, 30), (16, 30)], "F")      # stretched torso
    m.poly([(28, 10), (40, 8), (44, 12), (32, 16)], "f")                                       # back
    m.poly([(16, 26), (30, 26), (40, 22), (40, 27), (28, 32), (16, 31)], "R")                # belt / rags
    m.line(42, 16, 52, 6, "F", 3); m.line(52, 6, 58, 2, "f", 2)                               # hind legs trailing
    m.line(40, 22, 50, 22, "F", 3); m.line(50, 22, 56, 16, "f", 2)
    m.line(56, 16, 59, 15, "y"); m.line(58, 2, 61, 1, "y")
    m.ellipse(10, 20, 6, 5.5, "F")                                                             # head
    m.poly([(6, 18), (-2, 20), (-2, 23), (6, 22)], "F")                                       # upper jaw
    m.poly([(-1, 25), (6, 24), (7, 28), (1, 28)], "f")                                        # lower jaw (open)
    m.poly([(-1, 23), (6, 22), (6, 24), (-1, 25)], "k")
    m.px(0, 23, "y"); m.px(2, 23, "y"); m.px(1, 25, "y"); m.px(4, 24, "y")
    m.poly([(11, 10), (16, 15), (11, 16)], "F"); m.poly([(8, 12), (11, 16), (7, 17)], "f")   # ears flat back
    m.px(7, 18, "N"); m.px(8, 18, "N")                                                         # glowing eye
    m.line(18, 22, 8, 32, "F", 3); m.line(8, 32, 0, 36, "F", 3)                                # forelegs forward
    m.line(24, 24, 14, 34, "f", 3); m.line(14, 34, 6, 40, "f", 2)
    for i in range(3):
        m.line(0, 36, -4, 34 + i * 2, "y")
        m.line(6, 40, 2, 39 + i * 2, "y")


def volkolak_leap(s):
    return _framed(_volk_leap, (96, 96), (48, 88), s, (30, 40))


# --------------------------------------------------------------------------
# ЧЕРНОЯР-ВОЛКОДЛАК (boss, phase 2): 104 standing, kneeling ~80.
# Source units: ground at y=100; faces left (toward the hero).
# --------------------------------------------------------------------------
def _wolfdlak_kneel(m):
    # --- far side first: pelt cape flowing down the back (ragged hem)
    m.poly([(60, 26), (74, 30), (86, 46), (90, 66), (88, 80), (84, 76), (80, 84), (76, 78), (70, 84), (66, 72)], "j")
    # far leg: knee on the ground, shin lying back, clawed foot
    m.poly([(60, 62), (74, 62), (70, 97), (58, 98)], "j")
    m.poly([(58, 93), (86, 94), (90, 99), (58, 100)], "j")
    for k in range(3):
        m.line(88 + k, 99, 91 + k, 100, "y")
    # far arm pressed to the chest
    m.line(68, 36, 72, 54, "j", 6)
    # torso: barrel chest, leaning back
    m.poly([(38, 36), (66, 28), (78, 42), (76, 64), (52, 70), (40, 56)], "b")
    m.poly([(66, 28), (78, 42), (76, 64), (68, 66), (70, 40)], "j")
    # torn volkhv shirt: a grey strip down the chest with a red hem, belt with bronze plaques
    m.poly([(46, 42), (53, 40), (58, 62), (50, 64)], "I")
    m.line(53, 40, 58, 62, "i")
    m.line(49, 61, 58, 59, "D")
    m.poly([(42, 62), (74, 58), (75, 62), (43, 66)], "L")
    for x in (48, 56, 64, 70):
        m.px(x, 62 - (x - 42) // 8, "Z")
    # near leg: thigh forward, knee up, shin down, foot planted in front
    m.poly([(46, 60), (62, 64), (42, 76), (32, 72)], "b")
    m.poly([(30, 70), (42, 74), (40, 96), (31, 96)], "b")
    m.poly([(36, 72), (42, 74), (40, 96), (37, 96)], "j")
    m.poly([(24, 95), (42, 94), (43, 100), (22, 100)], "j")
    for k in range(4):
        m.line(21 + k * 2, 100, 19 + k * 2, 101, "y")
    # wounds: Небыль-green slashes across the chest fur
    m.line(58, 34, 68, 46, "N"); m.line(61, 33, 70, 43, "n")
    m.line(40, 46, 45, 52, "N")
    # far arm forearm + hand on the chest (over the shirt)
    m.line(72, 54, 56, 50, "b", 5)
    m.ellipse(54, 50, 3.5, 3.2, "b")
    for k in range(3):
        m.px(51, 47 + k * 2, "y")
    # thick neck + mane
    m.poly([(36, 34), (46, 18), (58, 18), (64, 30), (50, 38)], "b")
    m.poly([(52, 18), (58, 18), (64, 30), (58, 32)], "j")
    # amulets on a cord: two discs and a лунница
    m.line(38, 38, 60, 34, "G")
    m.ellipse(42, 38.5, 1.8, 1.8, "Z"); m.ellipse(56, 36, 1.8, 1.8, "Z")
    m.poly([(47, 37), (52, 36), (51, 40), (48, 40)], "Z")
    # head thrown back, howling up-left: skull, long muzzle, open jaws
    m.ellipse(46, 20, 8.5, 7.5, "b")
    m.poly([(42, 14), (24, 2), (21, 5), (36, 20)], "b")                      # upper jaw (long, up-left)
    m.poly([(24, 2), (21, 5), (23, 6), (26, 3)], "j")                        # nose
    m.poly([(40, 24), (26, 12), (25, 16), (36, 27)], "j")                    # lower jaw, open
    m.poly([(36, 20), (22, 6), (25.5, 12.5), (37, 24)], "Q")                 # mouth
    for (x, y) in ((24, 7), (27, 9), (30, 12), (26, 12), (29, 15)):
        m.px(x, y, "y")
    m.poly([(48, 12), (56, 2), (58, 14)], "b"); m.poly([(52, 9), (56, 4), (57, 12)], "j")    # ear laid back
    m.poly([(44, 12), (49, 5), (51, 13)], "j")                               # far ear
    m.px(39, 15, "N"); m.px(40, 15, "N"); m.px(40, 16, "n")                  # eye
    # near arm: long, down to a paw braced on the ground in front
    m.line(42, 38, 30, 60, "b", 6)
    m.line(30, 60, 20, 92, "b", 5)
    m.line(32, 60, 23, 92, "j", 2)
    m.ellipse(18, 95, 5, 3.5, "b")
    for k in range(4):
        m.line(13 + k * 2, 97, 12 + k * 2, 100, "y")


def rim_light(spr, side=1, ramp="nebyl", lvl=2, top=False):
    """Small emissive Небыль rim on the side facing the rift (side=+1: right)."""
    s = dict(spr)
    s["ramp"] = spr["ramp"].copy(); s["lvl"] = spr["lvl"].copy(); s["em"] = spr["em"].copy()
    ink = pk.RAMP_ID["ink"]
    body = spr["mask"] & (spr["ramp"] != ink)
    outl = spr["mask"] & (spr["ramp"] == ink)
    ext = ~spr["mask"]
    nb = np.roll(outl, -side, axis=1) & np.roll(ext, -2 * side, axis=1)
    if top:
        nb = nb | (np.roll(outl, 1, axis=0) & np.roll(np.roll(outl, -side, axis=1), 1, axis=0))
    rim = body & nb
    s["ramp"][rim] = pk.RAMP_ID[ramp]; s["lvl"][rim] = lvl; s["em"][rim] = True
    return s


def wolfdlak_kneel():
    return rim_light(_framed(_wolfdlak_kneel, (128, 144), (64, 132), 0.85, (54, 100), target_h=80))


# --------------------------------------------------------------------------
# LOOT (scale.md §3.4: sword 22-24 long, silver 14x7)
# --------------------------------------------------------------------------
def prince_sword():
    """Меч князя on the ground: 24 px, bronze hilt with a lobed pommel."""
    m = pk.MatCanvas(24, 10)
    m.line(7, 7, 23, 1, "T", 2)
    m.line(4, 4, 8, 9, "g")
    m.line(1, 9, 5, 8, "L")
    m.ellipse(0.8, 9, 1.2, 1.0, "g")
    return _mk(m)


def staff():
    """«Посох Чернояра»: ~30 px dark staff lying diagonally, carved wolf-head
    finial with a green Небыль stone."""
    m = pk.MatCanvas(30, 13)
    m.line(1, 12, 23, 4, "x", 2)
    for k in (6, 12, 18):
        m.px(k, 12 - int(k * 8 / 22), "Z")
    m.ellipse(25, 3.5, 3, 2.6, "X")
    m.poly([(26, 2), (30, 0), (29, 3)], "X")                                  # snout of the finial
    m.px(25, 2, "N")
    m.line(22, 1, 23, -1, "x")                                                # ear
    return _mk(m)


def pelt():
    """Empty black wolf pelt (~36x10) lying flat, head to the left."""
    m = pk.MatCanvas(36, 10)
    m.poly([(6, 3), (28, 1), (35, 4), (33, 8), (22, 9), (8, 9), (3, 7)], "b")
    m.poly([(14, 5), (26, 4), (32, 6), (24, 8), (12, 8)], "j")
    m.ellipse(4, 4.5, 3.5, 3, "b")
    m.poly([(0, 4), (2, 3), (2, 6), (0, 6)], "b")
    m.poly([(5, 1), (7, 0), (7, 3)], "b")
    m.line(29, 8, 34, 9, "j"); m.line(8, 9, 5, 10, "j")                       # empty paws
    m.px(3, 4, "k")
    return _mk(m)

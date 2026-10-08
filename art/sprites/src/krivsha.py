"""Б1 Кривша, Обгорелый страж (GDD v1.7 §5.4, §12.1.2; act1.md): бывший сторож капища,
убитый Чернояром и поднятый упырём. Сутулый, весь в огне, обгоревший тулуп, связка ключей
капища на поясе, горящие когти. scale.md §2: рост 96 (с огненным ореолом до 112), силуэт 44,
кадр 128x128, pivot (64,116), 2 вида (se, ne) + зеркало. Огненная фаза — вариант hot=True
(выше пламя на плечах до 112, раскалённые трещины, светлые глаза) + наземный ореол (fx).
Faces +x in both views (se: 3/4 front, ne: 3/4 back)."""
import math
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
from bigrig import Pn, build, rot, add, ik, tongue, TAU, over

W, H, PIV = 128, 128, (64, 116)

LEG = rig.legend(
    T=("wood", 2, True, False), t=("wood", 1, False, False),                    # burnt sheepskin coat (t: shadow side)
    A=("wood", 3, True, False), a=("wood", 2, False, False),                    # near sleeve (lit) / far sleeve
    c=("wood", 1, False, False), k=("ink", 0, False, False),                     # char patches / holes
    F=("stone", 2, True, False, "fur"), f=("stone", 1, False, False),          # sooty fleece (collar, cuffs, hem)
    S=("ghoul", 2, True, False), s=("ghoul", 1, False, False),                  # dead grey skin (s: far limbs)
    B=("ink", 0, False, False), b=("fur", 2, False, False),                     # burnt hair
    Y=("birch", 4, True, False), y=("birch", 3, False, False),                  # claws (bone)
    P=("wood", 1, True, False), p=("wood", 1, False, False),                    # leggings
    W=("stone", 2, True, False), w=("stone", 1, False, False),                  # foot wraps (ash)
    L=("wood", 1, False, False), Z=("bronze", 3, True, False), z=("bronze", 2, False, False),
    G=("nebyl", 1, False, False),                                               # trupnaya zelen' (dead green)
)

FIRE = set("qEeQr")


def P_(**kw):
    d = dict(pel=(-4.0, -44.0), tor=34.0, fn=(9.0, 0.0), ff=(-11.0, -1.0), lift_n=0.0, lift_f=0.0,
             hn=(27.0, -27.0), hf=(15.0, -31.0), claw_n=72.0, claw_f=80.0, head=(12.0, 6.0), head_ang=0.0,
             jaw=0, sway=0.0, keys=0.0, fire=1.0, eyes=1, crouch=0.0, flame_ph=0.0, extra_flames=())
    d.update(kw)
    return d


class Skel:
    def __init__(s, p):
        s.pel = p["pel"]
        s.tor = p["tor"]
        s.T = lambda a, b: add(s.pel, rot(a, b, s.tor))
        s.neck = s.T(0, -40)
        s.hc = add(s.neck, p["head"])
        s.sh_n = s.T(7, -33)
        s.sh_f = s.T(-3, -37)
        s.hip_n = add(s.pel, (3, 0))
        s.hip_f = add(s.pel, (-4, -1))
        s.fn = (p["fn"][0], p["fn"][1] - p["lift_n"])
        s.ff = (p["ff"][0], p["ff"][1] - p["lift_f"])
        s.kn = ik(s.hip_n, s.fn, 25, 25, -1)
        s.kf = ik(s.hip_f, s.ff, 25, 25, -1)
        s.hn, s.hf = p["hn"], p["hf"]
        s.en = ik(s.sh_n, s.hn, 21, 21, 1)
        s.ef = ik(s.sh_f, s.hf, 21, 21, 1)
        s.sh_nb = s.T(10, -33)                    # back view: near (right) shoulder on the front edge
        s.sh_fb = s.T(1, -38)
        s.en_b = ik(s.sh_nb, s.hn, 21, 21, 1)
        s.ef_b = ik(s.sh_fb, s.hf, 21, 21, 1)


def _claws(P, hand, ang, fire_tips, ph, far=False):
    for k, d in enumerate((-26, -9, 8, 24)):
        a = math.radians(ang + d)
        L = 12.0 if k in (1, 2) else 9.5
        tip = (hand[0] + math.cos(a) * L, hand[1] + math.sin(a) * L)
        mid = (hand[0] + math.cos(a) * L * 0.55, hand[1] + math.sin(a) * L * 0.55)
        P.line(hand, mid, "y" if far else "Y", 2)
        P.line(mid, tip, "y" if far else "Y", 1)
        if fire_tips:
            P.px(tip, "E" if (k + int(ph * 3)) % 2 else "e")
            P.px((tip[0], tip[1] - 1), "q")


def _arm(P, sh, el, hand, far, p, ph, claw_ang):
    sl = "a" if far else "A"
    if not far:                                   # inner ink contour so the arm reads over the coat
        P.limb(sh, el, "k", 13)
        P.limb(el, hand, "k", 11)
    P.limb(sh, el, sl, 11 if not far else 10)
    P.limb(el, hand, sl, 9 if not far else 8)
    cuff = add(el, ((hand[0] - el[0]) * 0.8, (hand[1] - el[1]) * 0.8))
    P.limb(cuff, add(cuff, ((hand[0] - el[0]) * 0.12, (hand[1] - el[1]) * 0.12)), "f" if far else "F", 8)
    P.ellipse(hand, 4.4, 4.0, "s" if far else "S")
    _claws(P, hand, claw_ang, p["fire"] > 0, ph, far)
    # smouldering sleeve
    m = add(sh, ((el[0] - sh[0]) * 0.5, (el[1] - sh[1]) * 0.5))
    P.px(m, "q"); P.px(add(m, (1, 1)), "q")


def _leg(P, hip, knee, foot, far):
    ch = "p" if far else "P"
    P.limb(hip, knee, ch, 10 if not far else 9)
    P.limb(knee, foot, ch, 8 if not far else 7)
    wr = add(knee, ((foot[0] - knee[0]) * 0.45, (foot[1] - knee[1]) * 0.45))
    P.limb(wr, add(foot, (0, -2)), "w" if far else "W", 8 if not far else 7)
    P.poly([add(foot, (-4, -3)), add(foot, (7, -3)), add(foot, (8, 0)), add(foot, (-4, 0))], "s" if far else "S")
    for k in range(3):                                    # toe claws
        P.px(add(foot, (8, -1 - k)), "y")


CRACKS = [[(4, -8), (8, -14), (6, -20)], [(-10, -12), (-6, -18), (-9, -26)], [(10, -26), (6, -31)],
          [(-14, -30), (-10, -34)], [(0, 4), (3, 10)], [(-8, 6), (-11, 12)], [(12, 2), (10, 8), (13, 12)]]
CRACKS_BACK = [[(-6, -10), (-2, -16), (-5, -22)], [(-16, -18), (-12, -26)], [(4, -24), (0, -32), (3, -38)],
               [(-12, -36), (-6, -40)], [(-4, 6), (-2, 12)], [(6, 4), (9, 11)]]


def _coat(P, S, p, view, ph):
    sw = p["sway"]
    T = lambda a, b: S.T(a, b)
    pel = S.pel
    # skirt (hangs vertically from the waist, ragged hem to the knees)
    hl = 24 - p["crouch"] * 6
    kr = max(0.0, p["tor"] - 45.0) * 1.15                    # lying down: the skirt follows the legs
    Rk = lambda a, b: add(pel, rot(a, b, kr))
    sk = [(-16, -4), (14, -4), (17 + sw, hl - 2), (12 + sw, hl + 2), (7 + sw, hl - 1), (2 + sw, hl + 3), (-4 + sw, hl),
          (-9 + sw, hl + 3), (-14 + sw, hl - 1), (-19 + sw, hl + 1)]
    P.poly([Rk(a, b) for a, b in sk], "T")
    P.poly([Rk(a, b) for a, b in [(6, -4), (14, -4), (17 + sw, hl - 2), (12 + sw, hl + 2), (8 + sw, hl)]], "t" if view == "se" else "T")
    for k in range(5):                                       # fleece showing on the ragged hem
        x = -16 + k * 7 + sw
        P.line(Rk(x, hl), Rk(x + 3, hl + 1), "F")
    # body of the coat (torso frame): belly forward (+a), big hump behind (-a)
    body = [(-14, 6), (12, 6), (14, -10), (17, -26), (14, -36), (6, -42), (-6, -46), (-17, -42), (-22, -30), (-18, -12)]
    P.poly([T(a, b) for a, b in body], "T")
    if view == "se":
        P.poly([T(a, b) for a, b in [(6, 6), (12, 6), (14, -10), (17, -26), (14, -36), (6, -40)]], "t")
        P.poly([T(a, b) for a, b in [(2, -38), (5, -38), (6, 6), (3, 6)]], "F")         # fleece-lined front edge
    else:
        P.poly([T(a, b) for a, b in [(-21, -28), (-17, -40), (-8, -44), (-6, -30), (-12, -12), (-20, -12)]], "t")
        P.line(T(-4, -42), T(-6, 4), "c")                                                 # back seam
    # char patches & holes (move with the body)
    for (a, b, rx, ry) in ((-12, -20, 4, 3), (8, -2, 3, 2), (-4, -34, 3, 2), (12, -18, 2, 3)):
        P.ellipse(T(a, b), rx, ry, "c")
    P.ellipse(T(-12, -20), 1.6, 1.2, "k")
    # belt
    P.line(T(-18, 0), T(15, 0), "L", 2)
    # glowing cracks
    hot = p["fire"] >= 2
    for k, cr in enumerate(CRACKS if view == "se" else CRACKS_BACK):
        pts = [T(a, b) if b < 2 else Rk(a + sw * 0.5, b) for a, b in cr]
        cold = p["fire"] < 0.35 and k % 3 != 0                # burnt out: most cracks go dark
        for q0, q1 in zip(pts, pts[1:]):
            P.line(q0, q1, "c" if cold else "E" if hot and k % 2 == 0 else "q")
        if not cold and (hot or (k + int(ph / TAU * 6)) % 3 == 0):
            P.px(pts[0], "E" if not hot else "e")


def _keys(P, S, p, view):
    sw = p["keys"]
    ring = S.T(9 if view == "se" else -2, 2)
    ring = add(ring, (0, 1))
    P.ellipse(ring, 2.4, 1.6, "z")
    P.ellipse(ring, 1.0, 0.6, "k")
    for k, (dx, ln) in enumerate(((-3, 9), (-1, 11), (1, 10), (3, 8))):
        a = math.radians(90 + dx * 5 + sw * 14)
        top = add(ring, (dx * 0.8, 1))
        end = (top[0] + math.cos(a) * ln, top[1] + math.sin(a) * ln)
        P.line(top, end, "Z")
        P.line((end[0] - 1, end[1]), (end[0] + 1, end[1]), "Z")              # bit
        P.px((end[0] + 1, end[1] - 2), "Z")


def _collar(P, S, p, view):
    n = S.neck
    P.ellipse(add(n, (-4, 3)), 11, 5.5, "F")
    P.ellipse(add(n, (-6, 5)), 8, 2.5, "f")
    for k in range(6):                                     # shaggy, singed edge
        a = (k / 6.0) * math.pi + math.pi
        P.px(add(n, (-4 + math.cos(a) * 11.5, 2 + math.sin(a) * 6)), "c" if k % 2 else "F")


def _head(P, S, p, view, ph):
    hc = S.hc
    ha = p["head_ang"]
    R = lambda a, b: add(hc, rot(a, b, ha))
    sh = lambda pts, ch: P.shape(hc, ha, pts, ch)
    if view == "se":
        P.ellipse(R(0, 0), 8.2, 8.6, "S")
        sh([(-1, 3), (7, 2), (8, 5), (5, 9), (0, 9), (-3, 6)], "S")                 # heavy jaw
        sh([(-6.5, -2), (-5, -6), (-1, -8), (4, -7), (6, -5), (2, -4), (-2, -3)], "B")   # scorched scalp
        P.px(R(-3, -8), "b"); P.px(R(1, -9), "b"); P.px(R(-5, -7), "b")
        P.ellipse(R(3.4, -1.0), 1.6, 1.3, "k"); P.ellipse(R(-0.6, -1.4), 1.4, 1.2, "k")
        eye = "e" if p["fire"] >= 2 else "E"
        if p["eyes"]:
            P.px(R(3.6, -1.2), eye); P.px(R(-0.4, -1.4), eye)
        P.line(R(1, 5 + p["jaw"]), R(7, 4 + p["jaw"] * 0.6), "k")                   # mouth
        if p["jaw"] >= 2:
            P.poly([R(1.5, 5), R(6.5, 4.2), R(6, 4 + p["jaw"]), R(2, 5 + p["jaw"])], "k")
            P.px(R(3, 5), "y"); P.px(R(5, 4.6), "y")
        P.line(R(-4, 2), R(-1, 6), "G")                                              # dead green rot
        P.px(R(5.8, 0.6), "s")                                                        # nose stub
    else:
        P.ellipse(R(0, 0), 6.4, 7.0, "S")
        sh([(-6.6, 1), (-6, -5), (-1, -8), (5, -6), (6.4, -2), (3, 2), (-2, 4)], "B")
        P.px(R(-2, -8), "b"); P.px(R(3, -7), "b"); P.px(R(-5, -4), "b")
        sh([(4, 2), (7, 3), (6, 7), (3, 7)], "S")                                   # jaw edge from behind


def _flames(P, S, p, view, ph):
    """Back / shoulder fire. fire 1 = normal (top <= 96), 2 = fire phase (crown to 112)."""
    f = p["fire"]
    if f <= 0:
        return
    hot = f >= 2
    sc = min(1.0, f)                            # < 1 while burning out (death)
    T = S.T
    spots = [(-14, -40, 10, 7, 0.3), (-6, -44, 12, 7, 2.1), (3, -43, 9, 6, 4.0), (-19, -30, 9, 6, 1.2),
             (10, -36, 7, 5, 5.0), (-20, -16, 7, 5, 3.3), (-10, -44, 9, 6, 5.5)]
    for k, (a, b, h, w, phi) in enumerate(spots):
        hh = sc * h * (0.78 + 0.22 * math.sin(ph + phi)) * (1.0 if not hot else 2.0 if k < 3 or k == 6 else 1.5)
        ww = w * (1.0 if not hot else 1.3)
        tongue(P, T(a, b + 2), hh, ww, ph + phi, lean=-0.35, chars=("q", "E", "e" if hot else "E"))
    for (a, b, h, phi) in p.get("extra_flames", ()):
        tongue(P, T(a, b), h * (0.8 + 0.2 * math.sin(ph + phi)), 4, ph + phi, lean=-0.2)
    if hot:                                     # embers lifting off the crown
        for j in range(4):
            tt = ((ph / TAU) + j * 0.25) % 1.0
            P.px(add(T(-8 + j * 5, -50), (math.sin(ph + j) * 2, -tt * 14)), "E" if tt < 0.5 else "q")


def draw(p, view, phase_ph):
    S = Skel(p)
    P = Pn(W, H, PIV)
    ph = phase_ph
    if view == "se":
        _arm(P, S.sh_f, S.ef, S.hf, True, p, ph, p["claw_f"])
        _leg(P, S.hip_f, S.kf, S.ff, True)
        _leg(P, S.hip_n, S.kn, S.fn, False)
        _coat(P, S, p, view, ph)
        _keys(P, S, p, view)
        _flames(P, S, p, view, ph)
        _collar(P, S, p, view)
        _head(P, S, p, view, ph)
        _arm(P, S.sh_n, S.en, S.hn, False, p, ph, p["claw_n"])
    else:
        _head(P, S, p, view, ph)
        _arm(P, S.sh_fb, S.ef_b, S.hf, True, p, ph, p["claw_f"])
        _leg(P, S.hip_n, S.kn, S.fn, True)
        _leg(P, S.hip_f, S.kf, S.ff, False)
        _coat(P, S, p, view, ph)
        _keys(P, S, p, view)
        _collar(P, S, p, view)
        _flames(P, S, p, view, ph)
        _arm(P, S.sh_nb, S.en_b, S.hn, False, p, ph, p["claw_n"])
    return build(P, LEG)


# --------------------------------------------------------------------------
# swipe trail (claw hit frame) and ground cracks
# --------------------------------------------------------------------------
def _swipe(P, c, r0, r1, a0, a1):
    """Fire crescent left by the claws: thick ember arc with a flame core, tapering at both ends."""
    n = 18
    pts = []
    for k in range(n + 1):
        t = k / n
        a = math.radians(a0 + (a1 - a0) * t)
        w = math.sin(math.pi * t)
        ro, ri = r1, r1 - (r1 - r0) * w
        pts.append(((c[0] + math.cos(a) * ro, c[1] + math.sin(a) * ro * 0.8), (c[0] + math.cos(a) * ri, c[1] + math.sin(a) * ri * 0.8), w))
    P.poly([q[0] for q in pts] + [q[1] for q in pts[::-1]], "q")
    for (o, i_, w) in pts:
        if w > 0.45:
            m = ((o[0] * 0.6 + i_[0] * 0.4), (o[1] * 0.6 + i_[1] * 0.4))
            P.px(m, "E")
        if w > 0.8:
            P.px(((o[0] * 0.75 + i_[0] * 0.25), (o[1] * 0.75 + i_[1] * 0.25)), "e")


# --------------------------------------------------------------------------
# animations (GDD §12.1.2: idle 4, ходьба 8, удар когтями 8, призыв 8, прыжок в огнище 8,
# выход с ореолом 6, урон 2, гибель 12). Each fn(i, hot) -> (pose, flame phase)
# --------------------------------------------------------------------------
def idle(i, hot=False):
    b = [0.0, 0.5, 1.0, 0.5][i]
    return P_(pel=(-4.0, -44.0 + b), tor=34.0 + 2 * b, hn=(27.0 - b, -27.0 + b * 1.5), hf=(15.0, -31.0 + b),
              keys=[0, 0.3, 0, -0.3][i], sway=[0, 0.5, 0, -0.5][i], fire=2 if hot else 1), i / 4 * TAU


def walk(i, hot=False):
    t = i / 8 * TAU
    sn, cs = math.sin(t), math.cos(t)
    bob = abs(sn) * 1.5
    return P_(pel=(-4.0 + 1.0 * sn, -44.0 + bob), tor=37.0 + 2.0 * abs(sn), fn=(2.0 + 10.0 * sn, 0.0), ff=(-4.0 - 10.0 * sn, -1.0),
              lift_n=max(0.0, 4.0 * cs), lift_f=max(0.0, -4.0 * cs),
              hn=(25.0 - 6.0 * sn, -28.0 + bob + abs(sn)), hf=(15.0 + 6.0 * sn, -32.0 + bob),
              keys=-0.8 * sn, sway=-1.5 * sn, fire=2 if hot else 1), i / 8 * 2 * TAU


CLAW = [  # near arm swings up and back behind the shoulder (telegraph 0.6 s = frames 0-5), strike on frame 6
    dict(hn=(20.0, -46.0), claw_n=0.0, tor=32.0),
    dict(hn=(2.0, -70.0), claw_n=-110.0, tor=28.0, pel=(-5.0, -45.0), jaw=1),
    dict(hn=(-12.0, -78.0), claw_n=-130.0, tor=26.0, pel=(-6.0, -45.0), jaw=1),
    dict(hn=(-17.0, -78.0), claw_n=-140.0, tor=25.0, pel=(-6.0, -45.0), jaw=2),
    dict(hn=(-18.0, -77.0), claw_n=-142.0, tor=25.0, pel=(-6.0, -45.0), jaw=2),
    dict(hn=(-15.0, -78.0), claw_n=-135.0, tor=26.0, pel=(-6.0, -45.0), jaw=2),
    dict(hn=(42.0, -18.0), claw_n=50.0, tor=46.0, pel=(-1.0, -42.0), fn=(15.0, 0.0), jaw=2, swipe=True),
    dict(hn=(34.0, -22.0), claw_n=70.0, tor=40.0, pel=(-2.0, -43.0), fn=(13.0, 0.0), jaw=1),
]
CLAW_HIT = 6


def claw(i, hot=False):
    d = dict(CLAW[i]); sw = d.pop("swipe", False)
    p = P_(**d, fire=2 if hot else 1)
    p["swipe"] = sw
    return p, i * 1.1


SUMMON = [
    dict(tor=26.0, hn=(20.0, -50.0), hf=(8.0, -54.0), claw_n=-30.0, claw_f=-40.0, jaw=1),
    dict(tor=16.0, pel=(-5.0, -45.0), hn=(18.0, -70.0), hf=(2.0, -72.0), claw_n=-70.0, claw_f=-80.0, jaw=2),
    dict(tor=12.0, pel=(-5.0, -45.0), hn=(20.0, -76.0), hf=(0.0, -78.0), claw_n=-80.0, claw_f=-90.0, jaw=3),
    dict(tor=14.0, pel=(-5.0, -45.0), hn=(22.0, -75.0), hf=(2.0, -77.0), claw_n=-75.0, claw_f=-85.0, jaw=3),
    dict(tor=50.0, pel=(-2.0, -38.0), hn=(36.0, -10.0), hf=(26.0, -12.0), claw_n=80.0, claw_f=85.0, jaw=2, fn=(12.0, 0.0)),
    dict(tor=58.0, pel=(-1.0, -34.0), hn=(38.0, -3.0), hf=(28.0, -4.0), claw_n=90.0, claw_f=95.0, jaw=2, fn=(12.0, 0.0), slam=True),
    dict(tor=48.0, pel=(-2.0, -38.0), hn=(34.0, -8.0), hf=(25.0, -10.0), claw_n=85.0, claw_f=90.0, jaw=1, fn=(11.0, 0.0), slam=True),
    dict(tor=38.0, pel=(-3.0, -43.0), hn=(28.0, -24.0), hf=(17.0, -28.0), claw_n=75.0, claw_f=80.0, fn=(10.0, 0.0)),
]
SUMMON_SPAWN = 5


def summon(i, hot=False):
    d = dict(SUMMON[i]); sl = d.pop("slam", False)
    p = P_(**d, fire=2 if hot else 1)
    p["slam"] = sl
    return p, i * 1.1


LEAP = [  # engine moves the sprite along the arc and adds the lift (0.6 s = frames 0-5); 6-7 loop inside the hearth
    dict(tor=50.0, pel=(-6.0, -36.0), hn=(14.0, -22.0), hf=(4.0, -24.0), claw_n=100.0, claw_f=110.0, jaw=2),
    dict(tor=56.0, pel=(-8.0, -32.0), hn=(0.0, -26.0), hf=(-8.0, -30.0), claw_n=140.0, claw_f=150.0, jaw=3),
    dict(tor=40.0, pel=(-2.0, -48.0), fn=(-10.0, 0.0), ff=(-20.0, -2.0), hn=(36.0, -52.0), hf=(28.0, -56.0), claw_n=-20.0, claw_f=-30.0, jaw=3),
    dict(tor=46.0, pel=(0.0, -46.0), fn=(10.0, -14.0), ff=(-6.0, -12.0), hn=(38.0, -48.0), hf=(30.0, -52.0), claw_n=0.0, claw_f=-10.0, jaw=3),
    dict(tor=40.0, pel=(0.0, -46.0), fn=(12.0, -8.0), ff=(-6.0, -6.0), hn=(34.0, -30.0), hf=(26.0, -36.0), claw_n=60.0, claw_f=60.0, jaw=2),
    dict(tor=58.0, pel=(-2.0, -32.0), fn=(12.0, 0.0), ff=(-12.0, -1.0), hn=(34.0, -4.0), hf=(24.0, -6.0), claw_n=90.0, claw_f=95.0, jaw=2),
    dict(tor=60.0, pel=(-2.0, -30.0), fn=(12.0, 0.0), ff=(-12.0, -1.0), hn=(30.0, -6.0), hf=(20.0, -8.0), claw_n=90.0, claw_f=95.0, jaw=1, fire=2,
         extra_flames=((0, -10, 18, 0.0), (-10, -20, 16, 2.0), (8, -30, 14, 4.0), (-16, -36, 16, 1.0))),
    dict(tor=60.0, pel=(-2.0, -31.0), fn=(12.0, 0.0), ff=(-12.0, -1.0), hn=(30.0, -7.0), hf=(20.0, -9.0), claw_n=90.0, claw_f=95.0, jaw=2, fire=2,
         extra_flames=((0, -10, 18, 3.1), (-10, -20, 16, 5.1), (8, -30, 14, 1.0), (-16, -36, 16, 4.1))),
]
LEAP_LOOP = (6, 7)


def leap(i, hot=False):
    d = dict(LEAP[i])
    d.setdefault("fire", 1)
    return P_(**d), (i * 1.1 if i < 6 else (i - 6) * math.pi)


EMERGE = [  # out of the hearth (fire phase) / out of the idol's flame (rise, normal phase)
    dict(tor=62.0, pel=(-2.0, -28.0), hn=(28.0, -4.0), hf=(18.0, -6.0), claw_n=90.0, claw_f=95.0, jaw=1,
         extra_flames=((0, -10, 22, 0.0), (-10, -20, 20, 2.0), (8, -30, 16, 4.0), (-16, -36, 18, 1.0))),
    dict(tor=48.0, pel=(-3.0, -36.0), hn=(32.0, -20.0), hf=(20.0, -22.0), claw_n=80.0, claw_f=85.0, jaw=2,
         extra_flames=((0, -10, 18, 1.0), (-10, -20, 16, 3.0), (-16, -36, 16, 2.0))),
    dict(tor=24.0, pel=(-5.0, -45.0), hn=(30.0, -60.0), hf=(6.0, -66.0), claw_n=-50.0, claw_f=-70.0, jaw=3,
         extra_flames=((-10, -20, 12, 4.0), (-16, -36, 12, 0.5))),
    dict(tor=20.0, pel=(-5.0, -45.0), hn=(34.0, -64.0), hf=(4.0, -70.0), claw_n=-60.0, claw_f=-80.0, jaw=3),
    dict(tor=30.0, pel=(-4.0, -44.0), hn=(30.0, -36.0), hf=(16.0, -40.0), claw_n=40.0, claw_f=50.0, jaw=1),
    dict(tor=34.0, pel=(-4.0, -44.0), hn=(27.0, -27.0), hf=(15.0, -31.0)),
]


def emerge(i, hot=False):
    return P_(**EMERGE[i], fire=2 if hot else 1), i * 1.3


HURT = [
    dict(tor=24.0, pel=(-7.0, -45.0), head=(9.0, 2.0), head_ang=-14.0, hn=(20.0, -36.0), hf=(8.0, -40.0), claw_n=40.0, claw_f=50.0, jaw=2, eyes=0),
    dict(tor=30.0, pel=(-5.0, -44.0), head=(11.0, 4.0), head_ang=-6.0, hn=(24.0, -30.0), hf=(12.0, -34.0), jaw=1),
]


def hurt(i, hot=False):
    return P_(**HURT[i], fire=2 if hot else 1), i * 2.0


DEATH = [
    dict(tor=20.0, pel=(-7.0, -45.0), head=(9.0, 1.0), head_ang=-20.0, hn=(22.0, -52.0), hf=(6.0, -56.0), claw_n=-30.0, claw_f=-40.0, jaw=3, f=1.0),
    dict(tor=16.0, pel=(-9.0, -45.0), head=(9.0, 1.0), head_ang=-24.0, hn=(24.0, -60.0), hf=(4.0, -64.0), claw_n=-50.0, claw_f=-60.0, jaw=3, f=1.0),
    dict(tor=34.0, pel=(-6.0, -36.0), fn=(14.0, 0.0), ff=(-12.0, -1.0), hn=(26.0, -30.0), hf=(14.0, -34.0), claw_n=60.0, claw_f=70.0, jaw=2, f=0.9),
    dict(tor=40.0, pel=(-4.0, -28.0), fn=(16.0, 0.0), ff=(-14.0, 0.0), hn=(30.0, -10.0), hf=(18.0, -12.0), claw_n=90.0, claw_f=90.0, jaw=2, f=0.85),
    dict(tor=52.0, pel=(-4.0, -26.0), fn=(16.0, 0.0), ff=(-14.0, 0.0), hn=(32.0, -4.0), hf=(20.0, -6.0), claw_n=90.0, claw_f=90.0, jaw=2, f=0.8, eyes=1),
    dict(tor=60.0, pel=(-4.0, -24.0), fn=(16.0, 0.0), ff=(-14.0, 0.0), hn=(34.0, -2.0), hf=(22.0, -3.0), claw_n=60.0, claw_f=60.0, jaw=1, f=0.7),
    dict(tor=72.0, pel=(-8.0, -18.0), fn=(8.0, 0.0), ff=(-22.0, 0.0), hn=(40.0, -2.0), hf=(28.0, -2.0), claw_n=20.0, claw_f=20.0, jaw=1, f=0.6),
    dict(tor=84.0, pel=(-12.0, -12.0), fn=(-2.0, 0.0), ff=(-30.0, 0.0), hn=(44.0, -2.0), hf=(30.0, -1.0), claw_n=0.0, claw_f=10.0, f=0.5, eyes=1),
    dict(tor=88.0, pel=(-14.0, -10.0), fn=(-6.0, 0.0), ff=(-34.0, 0.0), hn=(46.0, -1.0), hf=(32.0, 0.0), claw_n=0.0, claw_f=10.0, f=0.4, eyes=0),
    dict(tor=88.0, pel=(-14.0, -10.0), fn=(-6.0, 0.0), ff=(-34.0, 0.0), hn=(46.0, -1.0), hf=(32.0, 0.0), claw_n=0.0, claw_f=10.0, f=0.3, eyes=0),
    dict(tor=88.0, pel=(-14.0, -10.0), fn=(-6.0, 0.0), ff=(-34.0, 0.0), hn=(46.0, -1.0), hf=(32.0, 0.0), claw_n=0.0, claw_f=10.0, f=0.18, eyes=0),
    dict(tor=88.0, pel=(-14.0, -10.0), fn=(-6.0, 0.0), ff=(-34.0, 0.0), hn=(46.0, -1.0), hf=(32.0, 0.0), claw_n=0.0, claw_f=10.0, f=0.0, eyes=0),
]


def death(i, hot=False):
    d = dict(DEATH[i]); f = d.pop("f")
    p = P_(**d, fire=(2 if hot and f >= 1.0 else f))
    p["embers"] = max(0, 11 - i) if i >= 8 else 0
    return p, i * 1.2


ANIMS = [  # name, frames, fps, loop, fn
    ("idle", 4, 5, True, idle),
    ("walk", 8, 9, True, walk),
    ("claw", 8, 10, False, claw),
    ("summon", 8, 10, False, summon),
    ("leap", 8, 10, False, leap),
    ("emerge", 6, 8, False, emerge),
    ("hurt", 2, 8, False, hurt),
    ("death", 12, 10, False, death),
]
FIRE_VARIANT = ("idle", "walk", "claw", "summon", "emerge", "hurt", "death")   # leap happens before the fire phase


def frame(fn, i, view, hot=False):
    p, ph = fn(i, hot)
    idx = draw(p, view, ph)
    if p.get("swipe") or p.get("slam") or p.get("embers"):
        P = Pn(W, H, PIV)
        S = Skel(p)
        if p.get("swipe"):
            _swipe(P, S.sh_n, 24, 34, -75, 75)
        if p.get("slam"):
            for k, (dx, dy) in enumerate(((-6, 0), (4, 1), (12, -1), (-12, 2), (18, 1))):
                c = add(S.hn, (dx * 0.8, 3 + dy))
                P.line(c, add(c, (dx * 0.5, 2)), "q")
                P.px(add(c, (dx * 0.3, -3 - k % 3)), "E")
        if p.get("embers"):
            rng = np.random.RandomState(5)
            for k in range(p["embers"]):
                x, y = rng.uniform(-30, 40), rng.uniform(-14, -2)
                P.px((x, y), "q" if k % 3 else "E")
        over(idx, build(P, LEG))
    return idx

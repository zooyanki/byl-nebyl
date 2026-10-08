"""Упырь (GDD §5.2 E2, §12.1.2; act1: «мертвец, вставший из могилы. Медленный, но бьёт больно и ходит толпой»;
codex: «мертвец, которого Небыль подняла из могилы»). Обычный враг Залесья, М1–М2, и призыв Кривши — один спрайт.
scale.md §2: рост 40 (сутулый, распрямлённый 46), силуэт 22–24, кадр 64x64, pivot (32,56), 2 вида (se, ne) + зеркало.
Look (концепт sprites_rus.upyr, HUD-макеты): сутулый могильный мертвец — голова вынесена вперёд ниже горба,
серо-синяя трупная кожа (ghoul), рёбра, редкие волосы, провалы глаз с жёлтыми угольками, отвисшая челюсть с клыками,
длинные руки до колен с костяными когтями, бурый истлевший саван (через плечо и набедренная тряпка), пятна
трупной зелени (nebyl_dk), комья могильной земли. Кровь у рта — только red_dk (red — акцент героя, scale.md §4.4).
Faces +x in both views (se: 3/4 front, ne: 3/4 back)."""
import math
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
from bigrig import Pn, build, rot, add, ik, TAU, over

W, H, PIV = 64, 64, (32, 56)

LEG = rig.legend(
    S=("ghoul", 3, True, False), s=("ghoul", 2, False, False),          # dead skin (s: far limbs / shade)
    u=("ghoul", 1, False, False),                                        # ribs, sockets edge, spine
    R=("wood", 3, True, False), r=("wood", 2, False, False),             # rotten shroud, earth-stained (r: folds / far)
    Y=("birch", 4, True, False), y=("birch", 3, False, False),           # bone claws, fangs
    h=("stone", 1, False, False),                                        # sparse hair
    G=("nebyl", 2, False, False),                                        # trupnaya zelen' (rot), not glowing
    b=("red", 1, False, False),                                          # blood = red_dk only
    d=("earth", 2, False, False), D=("earth", 1, False, False),          # grave earth: lumps / dark soil
    g=("grass", 3, True, False),                                         # torn turf on the grave rim
    k=("ink", 0, False, False),
)
EARTH = set("dDg")


def P_(**kw):
    d = dict(pel=(-3.0, -17.0), tor=36.0, fn=(4.0, 0.0), ff=(-6.0, -0.5), lift_n=0.0, lift_f=0.0,
             hn=(12.0, -11.0), hf=(7.0, -13.0), claw_n=75.0, claw_f=80.0, head=(3.5, -3.4), head_ang=0.0,
             jaw=0, eyes=1, sway=0.0, sink=0.0, rise=None, wisp=None, dust=None)
    d.update(kw)
    return d


class Skel:
    def __init__(s, p):
        s.pel = p["pel"]
        s.tor = p["tor"]
        s.T = lambda a, b: add(s.pel, rot(a, b, s.tor))
        s.neck = s.T(1.0, -15.5)
        s.hc = add(s.neck, p["head"])
        s.sh_n = s.T(2.0, -13.0)
        s.sh_f = s.T(-1.5, -14.0)
        s.hip_n = add(s.pel, (1.0, 0.0))
        s.hip_f = add(s.pel, (-2.0, -0.5))
        s.fn = (p["fn"][0], p["fn"][1] - p["lift_n"])
        s.ff = (p["ff"][0], p["ff"][1] - p["lift_f"])
        s.kn = ik(s.hip_n, s.fn, 9.0, 9.0, -1)
        s.kf = ik(s.hip_f, s.ff, 9.0, 9.0, -1)
        s.hn, s.hf = p["hn"], p["hf"]
        s.en = ik(s.sh_n, s.hn, 9.0, 9.0, 1)
        s.ef = ik(s.sh_f, s.hf, 9.0, 9.0, 1)
        s.sh_nb = s.T(4.0, -13.0)                # back view: near (right) shoulder on the front edge
        s.sh_fb = s.T(0.0, -15.0)
        s.en_b = ik(s.sh_nb, s.hn, 9.0, 9.0, 1)
        s.ef_b = ik(s.sh_fb, s.hf, 9.0, 9.0, 1)


def _claws(P, hand, ang, far):
    for d in (-28, 0, 26):
        a = math.radians(ang + d)
        tip = (hand[0] + math.cos(a) * 4.2, hand[1] + math.sin(a) * 4.2)
        P.line(add(hand, (math.cos(a) * 1.4, math.sin(a) * 1.4)), tip, "y" if far else "Y")


def _arm(P, sh, el, hand, far, ang):
    ch = "s" if far else "S"
    P.limb(sh, el, ch, 3)
    P.limb(el, hand, ch, 2)
    P.ellipse(hand, 1.6, 1.4, ch)
    _claws(P, hand, ang, far)
    if not far:                                   # elbow knob + rot spot
        P.px(el, "u")


def _leg(P, hip, knee, foot, far):
    ch = "s" if far else "S"
    P.limb(hip, knee, ch, 3)
    P.limb(knee, foot, ch, 2)
    P.poly([add(foot, (-1.5, -1.6)), add(foot, (3.0, -1.4)), add(foot, (3.6, 0.0)), add(foot, (-1.5, 0.0))], ch)
    P.px(add(foot, (4.0, 0.0)), "y")                                  # toe claws
    P.px(add(foot, (2.5, -0.3)), "u" if not far else "s")


def _torso(P, S, p, view):
    T = S.T
    body = [(-4.0, 1.5), (3.5, 1.5), (4.0, -5.0), (5.0, -11.0), (3.5, -15.5), (-1.0, -17.0), (-5.5, -15.0),
            (-6.5, -9.0), (-5.0, -2.5)]
    P.poly([T(a, b) for a, b in body], "S")
    if view == "se":
        for b in (-7.0, -9.5, -12.0):                                 # ribs through the torn shroud
            P.line(T(0.5, b), T(4.2, b + 0.4), "u")
        P.line(T(1.0, -4.0), T(3.5, -3.6), "u")                       # sunken belly
        P.px(T(2.0, -14.0), "G"); P.px(T(3.0, -13.5), "G")            # rot
        # shroud over the far shoulder and the hump (hugs the back, tatters below the hips), strap across the chest
        P.poly([T(a, b) for a, b in [(-1.0, -17.4), (-6.0, -15.3), (-7.0, -9.0), (-6.4, -3.0), (-5.6, 1.0), (-6.6, 4.5),
                                      (-4.6, 3.0), (-3.6, 6.0), (-2.4, 2.5), (-2.0, -5.0), (0.0, -11.0), (2.0, -15.6)]], "R")
        P.poly([T(a, b) for a, b in [(1.5, -15.6), (3.2, -15.0), (-0.8, -4.0), (-2.4, -4.6)]], "R")
        P.line(T(-4.5, -13.0), T(-5.0, -4.0), "r")                    # fold
        P.line(T(-2.5, -9.0), T(-3.5, 2.0), "r")
        P.px(T(-4.0, -8.0), "k")                                      # moth hole
    else:
        P.poly([T(a, b) for a, b in [(3.5, -15.5), (-1.0, -17.6), (-6.5, -15.2), (-7.2, -8.0), (-6.2, -1.0), (-6.8, 4.5),
                                      (-4.8, 3.0), (-3.6, 6.0), (-2.2, 2.8), (-0.6, 5.0), (0.8, 1.5), (2.5, -2.0), (4.0, -9.0)]], "R")
        P.line(T(-5.5, -13.0), T(-6.0, 0.0), "r")                    # folds on the shade side
        P.line(T(-3.5, -10.0), T(-4.0, 2.0), "r")
        for k in range(3):                                            # spine knobs through a rent
            P.px(T(-1.5 - k * 0.2, -15.5 + k * 2.0), "S")
        P.ellipse(T(1.5, -7.0), 1.6, 2.0, "S")                       # torn hole: shoulder blade
        P.px(T(1.5, -7.5), "u")
        P.px(T(-3.0, -5.0), "G")


def _loin(P, S, p, view):
    """loin rag hanging from the waist (vertical, ragged hem above the knees)."""
    pel, sw = S.pel, p["sway"]
    kr = max(0.0, p["tor"] - 60.0)                                    # lying down: the rag follows the hips
    R = lambda a, b: add(pel, rot(a, b, kr))
    pts = [(-4.5, -2.0), (3.6, -1.5), (4.0 + sw, 3.0), (2.6 + sw, 5.5), (1.2 + sw, 3.6), (-0.4 + sw, 6.0),
           (-2.0 + sw, 3.6), (-3.6 + sw, 5.0), (-4.8 + sw, 2.4)]
    P.poly([R(a, b) for a, b in pts], "R")
    P.line(R(-4.5, -1.5), R(3.6, -1.0), "r")                          # knotted rope belt
    P.line(R(0.5, -0.5), R(0.0 + sw, 5.0), "r")                       # fold


def _head(P, S, p, view):
    hc, ha = S.hc, p["head_ang"]
    R = lambda a, b: add(hc, rot(a, b, ha))
    j = p["jaw"]
    if view == "se":
        P.ellipse(R(0.0, -0.6), 4.5, 4.7, "S")                        # skull
        P.poly([R(-1.5, 1.5), R(4.2, 1.0), R(4.8, 3.2 + j * 0.8), R(3.0, 4.6 + j), R(0.0, 4.4 + j * 0.6)], "S")  # long jaw
        P.line(R(-3.6, -2.2), R(-1.0, -4.6), "h"); P.line(R(-4.2, 0.0), R(-2.0, -3.6), "h")   # sparse hair
        P.px(R(0.5, -4.9), "h")
        P.ellipse(R(2.2, -1.0), 1.3, 1.1, "k")                        # sunken sockets
        P.ellipse(R(-0.8, -1.2), 1.0, 1.0, "k")
        if p["eyes"]:
            P.px(R(2.4, -1.2), "E" if p["eyes"] == 1 else "e")
            P.px(R(-0.7, -1.3), "E" if p["eyes"] == 1 else "e")
        P.px(R(4.2, 0.4), "k")                                        # nose hole
        P.px(R(-2.8, 1.5), "G"); P.px(R(-2.0, 2.4), "G")              # rot on the cheek
        if j >= 1:
            P.poly([R(0.8, 2.6), R(4.4, 2.0), R(4.2, 2.6 + j), R(1.2, 3.4 + j * 0.7)], "k")   # gaping mouth
            P.px(R(1.8, 2.7), "Y"); P.px(R(3.6, 2.3), "Y")            # fangs
            P.px(R(2.6, 3.4 + j), "b")                                # blood on the lip
        else:
            P.line(R(0.8, 2.8), R(4.4, 2.2), "k")
            P.px(R(2.0, 3.0), "Y"); P.px(R(3.6, 2.6), "Y")
            P.px(R(1.2, 3.8), "b")
    else:
        P.ellipse(R(0.0, -0.6), 4.3, 4.6, "S")
        P.line(R(-3.4, -2.5), R(0.5, -4.6), "h"); P.line(R(-3.8, 0.2), R(-0.5, -3.4), "h"); P.line(R(-1.5, 1.6), R(1.0, -2.0), "h")
        P.poly([R(2.0, 1.0), R(4.6, 1.2), R(4.4, 3.4 + j), R(2.2, 3.4)], "s")   # jaw edge from behind
        P.px(R(-2.5, 2.4), "G")
        P.px(R(2.8, -0.4), "u")                                       # ear nub


def _wisp(P, base, k):
    """Небыль leaves the body (death): a green wisp rising, k = 0..2."""
    if k is None:
        return
    x, y = base
    if k == 0:
        P.ellipse((x, y - 4.0), 2.0, 2.5, "n"); P.px((x, y - 4.5), "N")
        P.px((x + 1.0, y - 8.0), "n")
    elif k == 1:
        P.ellipse((x + 0.5, y - 11.0), 2.4, 3.2, "n"); P.ellipse((x + 0.5, y - 11.5), 1.0, 1.6, "N")
        P.px((x - 1.0, y - 7.0), "n"); P.px((x + 1.5, y - 16.0), "n"); P.px((x + 0.5, y - 15.0), "N")
    else:
        P.px((x + 1.0, y - 19.0), "n"); P.px((x + 1.5, y - 21.0), "N"); P.px((x, y - 23.0), "n")
        P.px((x + 2.0, y - 25.0), "n")


def _figure(p, view):
    S = Skel(p)
    P = Pn(W, H, PIV)
    if view == "se":
        _arm(P, S.sh_f, S.ef, S.hf, True, p["claw_f"])
        _leg(P, S.hip_f, S.kf, S.ff, True)
        _leg(P, S.hip_n, S.kn, S.fn, False)
        _torso(P, S, p, view)
        _loin(P, S, p, view)
        P.limb(S.T(1.0, -14.5), S.neck, "S", 3)                       # neck
        _head(P, S, p, view)
        _arm(P, S.sh_n, S.en, S.hn, False, p["claw_n"])
    else:
        _head(P, S, p, view)
        _arm(P, S.sh_fb, S.ef_b, S.hf, True, p["claw_f"])
        _leg(P, S.hip_n, S.kn, S.fn, True)
        _leg(P, S.hip_f, S.kf, S.ff, False)
        _torso(P, S, p, view)
        _loin(P, S, p, view)
        _arm(P, S.sh_nb, S.en_b, S.hn, False, p["claw_n"])
    if p["dust"]:                                                     # grave earth on him (rise)
        for (a, b) in p["dust"]:
            P.px(S.T(a, b), "d")
    _wisp(P, S.T(2.0, -8.0), p["wisp"])
    return P, S


# --------------------------------------------------------------------------
# rise from the grave: hole + earth mound composited around the clipped body
# --------------------------------------------------------------------------
def _grave(stage, back):
    """stage 0..5. back=True: rear rim + dark hole (behind the body); False: front lip + flying clods."""
    P = Pn(W, H, PIV)
    rx = [10.0, 12.0, 13.0, 13.0, 12.5, 0.0][stage]
    rng = np.random.RandomState(11 + stage)
    if stage <= 4:
        ry = 3.6
        if back:
            P.ellipse((0.0, -1.0), rx, ry + 0.6, "D")                 # rear rim of soil
            for k in range(4):                                        # turf flaps torn up on the far rim
                a = math.pi * (1.15 + 0.7 * k / 3)
                P.ellipse((math.cos(a) * (rx - 1.5), -1.0 + math.sin(a) * (ry + 0.4)), 1.6, 1.0, "g")
            P.ellipse((0.0, -0.3), rx - 3.5, ry - 1.6, "k")           # the hole
        else:
            P.ellipse((0.0, 0.4), rx, ry, "D", clip=lambda x, y: y >= 0.4)
            for k in range(5):                                        # soil lumps + turf on the near rim
                a = math.pi * (0.08 + 0.84 * k / 4)
                c = (math.cos(a) * (rx - 1.0), 0.6 + math.sin(a) * (ry - 0.6))
                P.ellipse(c, 1.5, 1.0, "g" if k % 2 == 0 else "D")
                P.px(add(c, (0.0, -0.6)), "d")
    if not back:
        n = [3, 6, 6, 5, 4, 5][stage]
        for k in range(n):                                            # clods thrown up / falling, cracks
            if stage == 5:
                x, y = rng.uniform(-11, 11), rng.uniform(-1.0, 2.0)
            else:
                x, y = rng.uniform(-12, 12), rng.uniform(-6 - stage * 3, -3)
            P.px((x, y), "d" if k % 2 else "D")
            if stage in (1, 2) and k % 3 == 0:
                P.px((x + 1, y), "d")
    return P.m.a.copy()


RISE = [  # (sink px, pose); frame 0: a hand breaks the ground, 5: stands, shakes the earth off
    (38.0, dict(tor=10.0, hn=(9.0, -44.0), hf=(-2.0, -30.0), claw_n=-80.0, claw_f=-90.0, jaw=0, eyes=0)),
    (27.0, dict(tor=14.0, hn=(10.0, -42.0), hf=(1.0, -43.0), claw_n=-70.0, claw_f=-85.0, head=(2.5, -3.5), jaw=1)),
    (17.0, dict(tor=40.0, hn=(15.0, -17.5), hf=(9.0, -18.0), claw_n=60.0, claw_f=65.0, jaw=2, eyes=2,
                dust=((-3.0, -16.0), (2.0, -15.0), (-5.0, -11.0)))),
    (9.0, dict(tor=50.0, hn=(15.0, -9.5), hf=(10.0, -10.0), claw_n=70.0, claw_f=80.0, jaw=1,
               dust=((-3.0, -16.0), (2.0, -15.0), (-6.0, -6.0), (1.0, -5.0)))),
    (3.0, dict(tor=44.0, pel=(-3.0, -14.0), fn=(7.0, -3.0), hn=(14.0, -5.0), hf=(9.0, -6.0), claw_n=80.0, jaw=1,
               dust=((-3.0, -16.0), (-6.0, -6.0), (1.0, -5.0)))),
    (0.0, dict(tor=32.0, hn=(11.0, -13.0), hf=(5.0, -14.0), jaw=2, sway=1.0, dust=((-3.0, -16.0),))),
]


def _rise_frame(i, view):
    sink, d = RISE[i]
    p = P_(**d)
    P, S = _figure(p, view)
    a = P.m.a
    s = int(round(sink))
    if s:
        a2 = np.full_like(a, ".")
        a2[s:, :] = a[:-s, :]
        a = a2
    h, w = a.shape
    yy = np.mgrid[0:h, 0:w][0] - P.gy
    a[(yy > 0) & (a != ".")] = "."                                    # below the ground: hidden
    back, front = _grave(i, True), _grave(i, False)
    out = back.copy()
    out[a != "."] = a[a != "."]
    out[front != "."] = front[front != "."]
    Q = Pn(W, H, PIV)
    Q.m.a = out
    return build(Q, LEG)


def draw(p, view, ph=0.0):
    P, S = _figure(p, view)
    return build(P, LEG)


# --------------------------------------------------------------------------
# animations (GDD §12.1.2: idle 4, ходьба 8, атака 6, урон 2, гибель 8, подъём из земли 6)
# --------------------------------------------------------------------------
def idle(i):
    b = [0.0, 0.5, 1.0, 0.5][i]
    return P_(pel=(-3.0, -17.0 + b), tor=36.0 + 1.5 * b, hn=(12.0 - 0.5 * b, -11.0 + b * 1.5), hf=(7.0, -13.0 + b),
              jaw=1 if i == 2 else 0, sway=[0, 0.5, 0, -0.5][i], head=(3.5, -3.4 + 0.5 * b)), i


def walk(i):          # slow shamble: dragging steps, arms swinging loose
    t = i / 8 * TAU
    sn, cs = math.sin(t), math.cos(t)
    bob = abs(sn) * 1.0
    return P_(pel=(-3.0 + 0.5 * sn, -17.0 + bob), tor=38.0 + 2.0 * abs(sn), fn=(1.0 + 6.0 * sn, 0.0), ff=(-4.0 - 6.0 * sn, -0.5),
              lift_n=max(0.0, 2.5 * cs), lift_f=max(0.0, -2.5 * cs),
              hn=(11.0 - 3.5 * sn, -10.0 + bob + abs(sn)), hf=(6.0 + 3.5 * sn, -12.0 + bob),
              claw_n=75.0 - 15 * sn, claw_f=80.0 + 15 * sn,
              sway=-1.0 * sn, head=(3.5, -3.4 + bob * 0.5), jaw=1 if i in (2, 6) else 0), i


ATTACK = [  # heavy two-handed overhead smash; hit on frame 3 (5 fps -> 0.6 s = hitAt)
    dict(tor=30.0, pel=(-4.0, -16.5), hn=(9.0, -18.0), hf=(4.0, -19.0), claw_n=20.0, claw_f=20.0, jaw=1),
    dict(tor=18.0, pel=(-5.0, -17.5), hn=(1.0, -39.0), hf=(-3.0, -38.0), claw_n=-90.0, claw_f=-100.0, jaw=2, eyes=2,
         head=(3.5, -2.5), head_ang=-6.0),
    dict(tor=10.0, pel=(-6.0, -18.0), hn=(-3.0, -43.0), hf=(-7.0, -42.0), claw_n=-115.0, claw_f=-125.0, jaw=3, eyes=2,
         head=(4.0, -2.0), head_ang=-10.0, ff=(-8.0, -0.5)),
    dict(tor=56.0, pel=(-1.0, -14.5), fn=(9.0, 0.0), hn=(19.0, -2.0), hf=(15.0, -2.5), claw_n=60.0, claw_f=60.0, jaw=3, eyes=2,
         head=(3.0, -2.0), head_ang=10.0, dust=None),
    dict(tor=58.0, pel=(-1.0, -14.0), fn=(9.0, 0.0), hn=(19.0, -1.5), hf=(15.0, -2.0), claw_n=70.0, claw_f=70.0, jaw=2,
         head=(3.0, -2.0), head_ang=10.0),
    dict(tor=44.0, pel=(-2.0, -16.0), fn=(7.0, 0.0), hn=(15.0, -7.0), hf=(10.0, -9.0), claw_n=75.0, claw_f=80.0, jaw=1),
]
ATTACK_HIT = 3
IMPACT = {3: 1.0, 4: 0.5}            # dirt / slash marks at the claws


def attack(i):
    return P_(**ATTACK[i]), i


HURT = [
    dict(tor=22.0, pel=(-5.0, -17.5), head=(2.0, -4.0), head_ang=-18.0, hn=(8.0, -17.0), hf=(3.0, -18.0), claw_n=30.0,
         claw_f=40.0, jaw=2, eyes=0),
    dict(tor=30.0, pel=(-4.0, -17.0), head=(3.0, -3.5), head_ang=-6.0, hn=(10.0, -13.0), hf=(5.0, -15.0), jaw=1),
]


def hurt(i):
    return P_(**HURT[i]), i


DEATH = [  # recoils, knees buckle, falls on its face; the Небыль leaves as a green wisp; the corpse stays
    dict(tor=18.0, pel=(-5.0, -17.5), head=(2.0, -4.0), head_ang=-22.0, hn=(9.0, -24.0), hf=(2.0, -26.0),
         claw_n=-30.0, claw_f=-40.0, jaw=3, eyes=2),
    dict(tor=30.0, pel=(-5.0, -13.0), fn=(6.0, 0.0), ff=(-9.0, 0.0), head=(3.0, -3.0), head_ang=-6.0,
         hn=(12.0, -8.0), hf=(6.0, -9.0), claw_n=60.0, claw_f=70.0, jaw=3, eyes=1),
    dict(tor=55.0, pel=(-6.0, -8.0), fn=(4.0, 0.0), ff=(-12.0, 0.0), head=(4.0, -1.5), head_ang=12.0,
         hn=(16.0, -1.5), hf=(11.0, -2.0), claw_n=80.0, claw_f=80.0, jaw=2, eyes=1),
    dict(tor=80.0, pel=(-9.0, -4.0), fn=(-2.0, 0.0), ff=(-18.0, 0.0), head=(4.5, 0.5), head_ang=30.0,
         hn=(18.0, -0.5), hf=(13.0, 0.0), claw_n=20.0, claw_f=20.0, jaw=1, eyes=0),
    dict(tor=88.0, pel=(-10.0, -3.0), fn=(-5.0, 0.0), ff=(-21.0, 0.0), head=(4.5, 1.5), head_ang=40.0,
         hn=(19.0, 0.0), hf=(14.0, 0.0), claw_n=10.0, claw_f=10.0, jaw=1, eyes=0, wisp=0),
    dict(tor=88.0, pel=(-10.0, -3.0), fn=(-5.0, 0.0), ff=(-21.0, 0.0), head=(4.5, 1.5), head_ang=40.0,
         hn=(19.0, 0.0), hf=(14.0, 0.0), claw_n=10.0, claw_f=10.0, jaw=1, eyes=0, wisp=1),
    dict(tor=88.0, pel=(-10.0, -3.0), fn=(-5.0, 0.0), ff=(-21.0, 0.0), head=(4.5, 1.5), head_ang=40.0,
         hn=(19.0, 0.0), hf=(14.0, 0.0), claw_n=10.0, claw_f=10.0, jaw=1, eyes=0, wisp=2),
    dict(tor=88.0, pel=(-10.0, -3.0), fn=(-5.0, 0.0), ff=(-21.0, 0.0), head=(4.5, 1.5), head_ang=40.0,
         hn=(19.0, 0.0), hf=(14.0, 0.0), claw_n=10.0, claw_f=10.0, jaw=1, eyes=0),
]


def death(i):
    return P_(**DEATH[i]), i


def rise(i):
    return None, i


ANIMS = [  # name, frames, fps, loop, fn
    ("idle", 4, 5, True, idle),
    ("walk", 8, 10, True, walk),
    ("attack", 6, 5, False, attack),
    ("hurt", 2, 8, False, hurt),
    ("death", 8, 10, False, death),
    ("rise", 6, 8, False, rise),
]


def _impact(p, k, view):
    """claw strike marks + dirt kicked up in front of the hands."""
    P = Pn(W, H, PIV)
    S = Skel(p)
    for j, (dx, dy) in enumerate(((-3.0, 1.0), (1.0, 1.5), (5.0, 1.0))):
        c = add(S.hn, (dx, dy))
        P.line(c, add(c, (2.0, 0.5)), "D")
    if k >= 1.0:
        for j, (dx, dy) in enumerate(((-4.0, -3.0), (0.0, -5.0), (4.0, -4.0), (7.0, -2.0), (-6.0, -1.0))):
            P.px(add(S.hn, (dx, dy)), "d" if j % 2 else "D")
    else:
        for j, (dx, dy) in enumerate(((-5.0, -1.0), (6.0, -1.0), (1.0, -2.0))):
            P.px(add(S.hn, (dx, dy)), "d")
    return build(P, LEG)


def _no_red(idx):
    """make_sprite fire-aware rims (red) -> red_dk: pure red stays the hero's accent (scale.md §4.4)."""
    idx[idx == C["red"]] = C["red_dk"]
    return idx


def frame(fn, i, view):
    if fn is rise:
        return _no_red(_rise_frame(i, view))
    p, _ = fn(i)
    idx = draw(p, view)
    if fn is attack and i in IMPACT:
        im = _impact(p, IMPACT[i], view)
        base = idx.copy()
        idx = im
        idx[base >= 0] = base[base >= 0]
    return _no_red(idx)


def body_height(view):
    """def.height check: idle + walk, no raised arms."""
    from bigrig import height
    hs = [height(frame(idle, i, view), PIV[1]) for i in range(4)] + [height(frame(walk, i, view), PIV[1]) for i in range(8)]
    return min(hs), max(hs)

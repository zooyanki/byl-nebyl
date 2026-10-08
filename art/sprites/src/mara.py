"""Мара Пепельная (GDD v1.7 §5.3, §12.1.2; act1: дух пожара, бродит по Залесью, поджигает
землю под собой). scale.md §2: рост 48 (языки пламени до 54), силуэт 22, кадр 64x64, pivot (32,56),
2 вида (se, ne) + зеркало. Парит над землёй (подол на 3-5 px выше строки pivot, тень — движок).
Пепельный саван, космы пламени вместо волос, тлеющие руки. Faces +x in both views."""
import math
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
from bigrig import Pn, build, rot, add, ik, tongue, TAU, over

W, H, PIV = 64, 64, (32, 56)

LEG = rig.legend(
    T=("stone", 4, True, False), t=("stone", 3, False, False), d=("stone", 2, False, False),   # ash shroud
    V=("stone", 5, True, False),                                                               # pale ash highlight
    S=("birch", 3, True, False), s=("birch", 2, False, False),                                 # ash-pale face
    A=("wood", 1, True, False), a=("ink", 0, False, False),                                    # charred forearms
    k=("ink", 0, False, False),
    N=("nebyl", 3, False, True), n=("nebyl", 2, False, True), M=("nebyl", 4, False, True),
)


def P_(**kw):
    d = dict(lift=2.5, lean=0.0, hn=(9.0, -26.0), hf=(-6.0, -27.0), hem=0.0, eyes=1, mouth=0, orb=0.0, orb_at=None,
             heal=0.0, collapse=0.0, hair=1.0, hair_back=0.0, view_ph=0.0)
    d.update(kw)
    return d


def _shroud(P, p, view, ph):
    L = p["lift"]; c = p["collapse"]
    lean = p["lean"]
    top_y = -33.5 - L + c * 24          # shoulders sink when collapsing
    hem_y = -L + c * (L - 1)
    sh = lambda x, y: (x + lean * (hem_y - y) * 0.022, y)    # lean: top shifts to +x
    hw_top, hw_hem = 6.5 - c * 3.5, 11.0 + c * 5          # collapsing: sags into a heap, not a box
    pts = [sh(-hw_top, top_y), sh(hw_top, top_y), sh(hw_top + 1.5 + c * 6, top_y + 8 - c * 3)]
    n = 7                                                     # tattered hem (ripples by phase)
    for k in range(n + 1):
        t = k / n
        x = hw_hem - 2 * hw_hem * t
        y = hem_y + (2.5 if k % 2 else -0.5) + 1.2 * math.sin(ph + k * 1.7) - p["hem"] * (1 - t) * 3
        pts.append(sh(x + p["hem"] * 2, y))
    pts.append(sh(-hw_top - 1.5 - c * 6, top_y + 8 - c * 3))
    P.poly(pts, "T")
    # shadow fold on the far side + folds
    if view == "se":
        P.poly([sh(-hw_top, top_y + 2), sh(-hw_top - 1.5, top_y + 8), sh(-hw_hem + p["hem"] * 2, hem_y), sh(-hw_hem + 4, hem_y), sh(-2, top_y + 6)], "t")
    else:
        P.poly([sh(1, top_y + 2), sh(hw_top + 1.5, top_y + 8), sh(hw_hem + p["hem"] * 2, hem_y), sh(hw_hem - 5, hem_y), sh(3, top_y + 8)], "t")
    for k, x in enumerate((-3.0, 2.0, 5.5)):
        P.line(sh(x * 0.6, top_y + 9), sh(x, hem_y - 2), "d" if k != 1 else "t")
    # smouldering hem: ember stitch along the bottom edge
    for k in range(int(hw_hem * 2) + 1):
        x = -hw_hem + k
        y = hem_y + 1.2 * math.sin(ph + k * 0.6) * 0.5
        if (k + int(ph * 2)) % 3 != 0:
            P.px(sh(x + p["hem"] * 2, y), "q" if k % 4 else "E")


def _hair(P, hc, p, ph, view):
    """космы пламени: 5 tongues streaming up (and back when gliding) from the scalp."""
    if p["hair"] <= 0:
        return
    back = p["hair_back"]
    for k, (dx, h, phi) in enumerate(((-4, 6.5, 0.0), (-1.8, 7.5, 1.9), (0.8, 6.5, 3.8), (3.0, 5, 1.1), (-6.2, 5.5, 5.0))):
        hh = h * 0.9 * p["hair"] * (0.82 + 0.18 * math.sin(ph + phi))
        base = add(hc, (dx - 1.0 - (1.5 if view == "ne" else 0), -3.5 + abs(dx) * 0.3))
        tongue(P, base, hh, 3.8 if k < 4 else 3.0, ph + phi, lean=-0.6 - back * 1.4)


def _head(P, hc, p, view):
    # ash hood (the shroud pulled over the head), face set forward in its shadow
    P.ellipse(add(hc, (-0.8, 0.0)), 4.8, 5.2, "T")
    P.poly([add(hc, (-5.4, 0)), add(hc, (-4.6, 5)), add(hc, (-7.0, 9)), add(hc, (-2, 7))], "T")         # hood falls on the back
    if view == "se":
        P.ellipse(add(hc, (1.4, 0.8)), 2.9, 3.8, "d")                          # shadow inside the hood
        P.ellipse(add(hc, (2.0, 1.2)), 2.2, 3.2, "S")                          # gaunt pale face
        if p["eyes"]:
            for ex in (1.0, 3.4):
                P.px(add(hc, (ex, 0.2)), "E" if p["eyes"] == 1 else "e")
        else:
            P.line(add(hc, (0.8, 0.4)), add(hc, (3.6, 0.4)), "d")
        P.line(add(hc, (1.6, 3.2)), add(hc, (3.0, 3.2 + min(1, p["mouth"]))), "k")
        if p["mouth"] >= 2:
            P.ellipse(add(hc, (2.4, 3.6)), 1.0, 1.1, "k")
        P.line(add(hc, (-2.6, -3.6)), add(hc, (2.4, -4.2)), "V")             # lit rim of the hood
    else:
        P.poly([add(hc, (-4.4, -2)), add(hc, (2.0, -4.6)), add(hc, (3.8, -1)), add(hc, (3.2, 4))], "t")
        P.px(add(hc, (4.0, 1.0)), "S")


def _arm(P, sh, hand, far, p, ph):
    el = ik(sh, hand, 9.0, 9.0, -1)
    P.limb(sh, el, "t" if far else "T", 4)                         # wide sleeve of the shroud
    cuff = add(el, ((hand[0] - el[0]) * 0.45, (hand[1] - el[1]) * 0.45))
    P.limb(el, cuff, "t" if far else "T", 4)
    P.poly([el, cuff, add(cuff, (-1.5, 5.0)), add(el, (-2.5, 4.0))], "t" if far else "d")   # hanging sleeve rag
    P.limb(cuff, hand, "a" if far else "A", 2)                     # charred, smouldering forearm
    P.px(hand, "E" if far else "e")                                 # glowing fingers
    P.px(add(hand, (1, 0)), "q"); P.px(add(hand, (0, 1)), "q")
    P.px(add(cuff, ((hand[0] - cuff[0]) * 0.5, (hand[1] - cuff[1]) * 0.5)), "q")


def _orb(P, c, r, ph):
    if r <= 0:
        return
    P.ellipse(c, r + 0.8, r + 0.8, "q")
    P.ellipse(c, r, r, "E")
    if r >= 1.6:
        P.ellipse((c[0] + 0.3, c[1] - 0.3), r * 0.5, r * 0.5, "e")
    for k in range(3):
        a = ph * 1.3 + k * 2.1
        P.px((c[0] + math.cos(a) * (r + 2.4), c[1] + math.sin(a) * (r + 1.8) - 1), "E" if k % 2 else "q")


def _heal(P, c, r, ph):
    if r <= 0:
        return
    for k in range(7):
        a = ph * 1.2 + k * TAU / 7
        P.px((c[0] + math.cos(a) * r * 2.4, c[1] + math.sin(a) * r * 1.1), "N" if k % 2 else "n")
    P.ellipse(c, r * 0.55, r * 0.55, "n")
    P.ellipse(c, r * 0.3, r * 0.3, "M")


def draw(p, view, ph):
    P = Pn(W, H, PIV)
    L, c, lean = p["lift"], p["collapse"], p["lean"]
    top_y = -33.5 - L + c * 24
    hem_y = -L
    shx = lambda y: lean * (hem_y - y) * 0.022
    hc = (1.0 + shx(top_y - 6) + (0.6 if view == "se" else 0), top_y - 6.0 + c * 4)
    sh_n = (shx(top_y) + 4.5, top_y + 1.5)
    sh_f = (shx(top_y) - 4.5, top_y + 1.0)
    if c < 0.75:
        _hair(P, hc, p, ph, view)
    if view == "se":
        if c < 0.6:
            _arm(P, sh_f, p["hf"], True, p, ph)
        _shroud(P, p, view, ph)
        if c < 0.75:
            _head(P, hc, p, view)
        if c < 0.6:
            _arm(P, sh_n, p["hn"], False, p, ph)
    else:
        if c < 0.6:
            _arm(P, sh_n, p["hn"], True, p, ph)
        _shroud(P, p, view, ph)
        if c < 0.75:
            _head(P, hc, p, view)
            _hair(P, hc, dict(p, hair=p["hair"] * 0.6), ph + 1.0, view)    # back view: hair over the crown
        if c < 0.6:
            _arm(P, sh_f, p["hf"], False, p, ph)
    if p["orb"]:
        _orb(P, p["orb_at"] or add(p["hn"], (2.5, -2.0)), p["orb"], ph)
    if p["heal"]:
        hx = (p["hn"][0] + p["hf"][0]) / 2; hy = (p["hn"][1] + p["hf"][1]) / 2
        _heal(P, (hx, hy - 2), p["heal"], ph)
    return build(P, LEG)


# --------------------------------------------------------------------------
# animations (GDD §12.1.2: парение 6, ведовство 6, урон 2, гибель 8; + glide 6, heal 6 for the prototype)
# --------------------------------------------------------------------------
def idle(i):
    t = i / 6 * TAU
    return P_(lift=2.5 + 1.0 * math.sin(t), hn=(9.0, -27.0 - 1.0 * math.sin(t)), hf=(-7.0, -28.0 - 1.0 * math.sin(t)),
              hem=0.0), t


def walk(i):          # glide: leans forward, hem and hair stream back
    t = i / 6 * TAU
    return P_(lift=3.0 + 1.0 * math.sin(t), lean=8.0, hn=(10.0, -31.0 - math.sin(t)), hf=(-8.0, -30.0 - math.sin(t)),
              hem=-1.5, hair_back=0.6), t


CAST = [
    dict(hn=(5.0, -36.0), orb=1.0),
    dict(hn=(2.0, -44.0), orb=2.0, mouth=1),
    dict(hn=(1.0, -46.0), orb=2.6, mouth=2, eyes=2),
    dict(hn=(13.0, -36.0), orb=0.0, mouth=2, eyes=2, lean=6.0, release=True),
    dict(hn=(12.0, -33.0), orb=0.0, mouth=1, lean=4.0),
    dict(hn=(9.0, -30.0)),
]
CAST_RELEASE = 3


def cast(i):
    d = dict(CAST[i]); rel = d.pop("release", False)
    p = P_(**d)
    if rel:
        p["orb"] = 2.2; p["orb_at"] = (19.0, -38.0)
    return p, i * 1.2


HEAL = [
    dict(hn=(7.0, -36.0), hf=(-6.0, -36.0), heal=1.5),
    dict(hn=(6.0, -41.0), hf=(-5.0, -41.0), heal=2.6, mouth=1),
    dict(hn=(5.0, -43.0), hf=(-4.0, -43.0), heal=3.4, mouth=2),
    dict(hn=(6.0, -42.0), hf=(-5.0, -42.0), heal=3.8, mouth=2),
    dict(hn=(8.0, -38.0), hf=(-6.0, -38.0), heal=2.0, mouth=1),
    dict(hn=(9.0, -31.0), hf=(-7.0, -31.0), heal=0.0),
]
HEAL_APPLY = 3


def heal(i):
    return P_(**HEAL[i]), i * 1.1


HURT = [dict(lean=-8.0, hn=(5.0, -33.0), hf=(-9.0, -33.0), eyes=0, mouth=2, hair=0.7, hem=1.0),
        dict(lean=-4.0, hn=(7.0, -30.0), hf=(-8.0, -30.0), mouth=1, hair=0.85)]


def hurt(i):
    return P_(**HURT[i]), i * 2.0


def death(i):
    c = [0.0, 0.0, 0.15, 0.3, 0.5, 0.7, 0.85, 1.0][i]
    return P_(lift=max(0.0, 3.0 - i * 0.6), collapse=c, hair=max(0.0, 1.0 - i * 0.22), eyes=0 if i >= 2 else 2, mouth=2 if i < 4 else 0,
              hn=(6.0 + i, -40.0 + i * 3), hf=(-6.0 - i, -40.0 + i * 3), lean=-6.0 if i < 2 else 0.0), i * 1.3


ANIMS = [
    ("idle", 6, 8, True, idle),
    ("walk", 6, 8, True, walk),
    ("cast", 6, 10, False, cast),
    ("heal", 6, 10, False, heal),
    ("hurt", 2, 8, False, hurt),
    ("death", 8, 10, False, death),
]


def frame(fn, i, view):
    p, ph = fn(i)
    idx = draw(p, view, ph)
    if fn is death and p["collapse"] >= 0.5:          # ash heap with dying embers
        P = Pn(W, H, PIV)
        k = p["collapse"]
        P.ellipse((0, -2), 9 + 3 * k, 3.4 + k, "T")
        P.ellipse((-1, -4), 6 + 2 * k, 2.4, "V")
        rng = np.random.RandomState(11)
        n = int(10 * (1.3 - k))
        for j in range(n):
            P.px((rng.uniform(-9, 9), rng.uniform(-5, -1)), "q" if j % 3 else "E")
        for j in range(3):                                   # last sparks rising
            P.px((rng.uniform(-6, 6), -8 - j * 4 - i), "q")
        heap = build(P, LEG)
        if k >= 1.0:
            idx = heap
        else:
            over(idx, heap)
    return idx

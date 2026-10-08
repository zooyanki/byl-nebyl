"""Згуба (GDD §12.1.2, былинный враг М2, P1) and its base «Волхв-прислужник»
(designed here: no sprite existed). Long robe, bone beads, wolf-skin hood
(ears count toward the 46-px height), staff with a horse skull (58 spec ->
57 max in a 64x64 frame with pivot y 56). Views se/ne (+ mirrors)."""
import math
from rig import Painter, build, legend, rot, add, flame
from human import Skel, leg, arm, pose as hpose

SCHEME = {
    "zguba": legend(
        T=("wood", 2, True, False), t=("wood", 1, False, False),            # dark homespun robe
        F=("fur", 4, True, False, "fur"), f=("fur", 3, False, False, "fur"), j=("fur", 2, False, False, "fur"),
        P=("stone", 2, True, False), p=("stone", 1, False, False)),
    "servant": legend(
        T=("birch", 3, True, False), t=("birch", 2, False, False),          # undyed linen robe
        F=("wood", 3, True, False), f=("wood", 2, False, False), j=("wood", 1, False, False),
        P=("stone", 2, True, False), p=("stone", 1, False, False)),
}

ROBE_CHEST = [(-5.4, -13.0), (4.6, -13.4), (5.4, -9.6), (4.8, -1.5), (-5.0, -1.2), (-6.0, -9.2)]


def P_(**kw):
    d = dict(fn=(0.0, 2.6), ff=(0.0, 2.4), hn=(0.0, 7.0, -25.0), hf=(1.0, 6.0, -21.0),
             staff=dict(ang=-91.0, below=25.0, above=23.0), neck=13.8, glow=0, eye=3)
    d.update(kw)
    return hpose(**d)


def staff(P, grip, st, view, kind, eye_lvl):
    ang = st["ang"]
    u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    A = lambda a, b=0.0: (grip[0] + u[0] * a - u[1] * b, grip[1] + u[1] * a + u[0] * b)
    butt, top = A(-st["below"]), A(st["above"])
    P.line(butt, top, "X", 2)
    for k in (-3.0, 6.0, 14.0):                                  # knots / bindings
        P.px(A(k, 0.6), "x")
    if kind != "zguba":                        # base servant: plain staff, 54 (top knob)
        P.ellipse(A(st["above"] - 3.0), 1.6, 1.6, "X")
        return top, None
    # horse skull on top, muzzle hanging forward-down (+x side)
    fs = 1.0 if view == "se" else 0.7
    sk = A(st["above"] + 2.5)
    pts = [(-2.2, -3.2), (1.8, -3.6), (4.0 * fs + 1.0, -1.6), (7.5 * fs + 1.0, 2.4), (7.8 * fs + 1.0, 4.0), (5.5 * fs + 1.0, 4.2),
           (1.6, 2.2), (-1.8, 1.8), (-2.8, -0.6)]
    P.poly([(sk[0] + a, sk[1] + b) for a, b in pts], "Y")
    P.line((sk[0] + 2.0, sk[1] + 2.0), (sk[0] + 7.0 * fs + 1.0, sk[1] + 3.8), "v")              # jaw line
    for k in range(3):
        P.px((sk[0] + 3.2 * fs + 1.0 + k * 1.5 * fs, sk[1] + 3.2 + k * 0.3), "y")               # teeth
    P.px((sk[0] + 7.4 * fs + 1.0, sk[1] + 2.6), "k")                                            # nostril
    eye = (sk[0] + 0.6, sk[1] - 1.0)
    P.ellipse(eye, 1.0, 0.9, "k")
    if eye_lvl:
        P.px(eye, "N" if eye_lvl >= 3 else "n")
        if eye_lvl >= 4:
            P.px((eye[0] - 1, eye[1]), "n"); P.px((eye[0], eye[1] - 1), "M")
    # red ribbons under the skull
    r0 = A(st["above"] - 2.0)
    P.line(r0, (r0[0] - 2.5, r0[1] + 4.5), "U"); P.line((r0[0] + 0.5, r0[1]), (r0[0] - 0.8, r0[1] + 6.0), "u")
    return top, eye


def hood(P, S, view, p):
    hc, ha = S.hc, S.head_ang
    R = lambda a, b: add(hc, rot(a, b, ha))
    sh = lambda pts, ch: P.shape(hc, ha, pts, ch)
    if view == "se":
        sh([(-5.0, -1.6), (-1.0, -4.6), (3.0, -4.4), (5.0, -2.4), (8.2, -1.6), (8.4, 0.0), (4.4, 0.4), (3.6, -0.6), (-1.4, -0.6),
            (-4.2, 3.0), (-5.6, 6.0)], "F")                                     # wolf head hood + snout over the brow
        sh([(3.0, -1.0), (8.2, -1.2), (8.2, 0.2), (4.4, 0.4)], "f")
        P.px(R(8.6, -0.8), "k")                                                 # wolf nose
        P.px(R(4.4, -2.2), "k")                                                 # wolf eye (dead)
        for e in ((-1.6, -3.8), (1.8, -4.2)):                                   # ears
            sh([(e[0] - 1.4, e[1] + 0.6), (e[0] + 0.2, e[1] - 2.8), (e[0] + 1.4, e[1] + 0.4)], "F")
        P.px(R(1.9, -5.4), "j")
    else:
        sh([(-4.6, -2.0), (-1.0, -4.6), (3.0, -4.4), (5.2, -2.0), (6.0, 0.0), (4.6, 1.2), (4.2, 4.0), (-4.4, 5.0), (-5.0, 1.0)], "F")
        sh([(1.0, -3.6), (5.0, -2.0), (5.6, 0.0), (2.0, 0.0)], "f")
        for e in ((-1.8, -3.8), (1.6, -4.2)):
            sh([(e[0] - 1.4, e[1] + 0.6), (e[0] + 0.2, e[1] - 2.8), (e[0] + 1.4, e[1] + 0.4)], "F")


def head(P, S, view, p, kind):
    hc, ha = S.hc, S.head_ang
    R = lambda a, b: add(hc, rot(a, b, ha))
    sh = lambda pts, ch: P.shape(hc, ha, pts, ch)
    if view == "se":
        P.ellipse(R(0.5, 0.4), 3.2, 3.8, "S")
        sh([(-1.2, 1.8), (1.4, 2.4), (3.8, 1.6), (3.6, 5.0), (2.2, 8.4), (0.6, 9.0), (-1.0, 6.0)], "G")   # long grey beard
        P.line(R(0.6, 5.0), R(1.2, 8.0), "g")
        P.line(R(1.4, 1.8), R(3.6, 1.4), "G")
        P.px(R(3.9, 0.4), "S"); P.px(R(4.2, 0.6), "S")
        if p.get("eyes") == "closed":
            P.line(R(1.6, -0.2), R(2.8, -0.2), "b")
        else:
            P.px(R(2.4, -0.3), "k")
        if p.get("mouth"):
            P.px(R(2.8, 2.6), "k"); P.px(R(2.8, 3.3), "k")
    else:
        P.ellipse(R(0.0, 0.2), 3.3, 3.7, "G")
        P.ellipse(R(2.6, 0.8), 1.2, 2.4, "S")
        sh([(1.6, 2.4), (3.6, 2.0), (3.4, 6.4), (1.8, 7.4)], "G")
    if kind == "zguba":
        hood(P, S, view, p)
    else:                                   # base servant: bare head, grey hair band
        clip = lambda xx, yy: yy <= (hc[1] - 0.8)
        P.ellipse(R(0.0, -1.0), 3.8, 3.4, "G", clip=clip)
        P.line(R(-3.4, -1.2), R(3.6, -1.4), "U")


def beads(P, S, view, kind):
    if kind != "zguba":
        return
    pts = []
    for k in range(9):
        t = k / 8.0
        a = -4.2 + 8.6 * t
        b = -12.4 + 3.6 * math.sin(math.pi * t)
        pts.append((a if view == "se" else -a, b))
    for k, (a, b) in enumerate(pts):
        P.px(add(S.pel, rot(a, b, S.tor)), "y" if k % 2 else "Y")
    # second, longer string with a small skull pendant
    for k in range(7):
        t = k / 6.0
        a = (-3.0 + 6.4 * t) * (1 if view == "se" else -1)
        b = -11.6 + 6.0 * math.sin(math.pi * t)
        P.px(add(S.pel, rot(a, b, S.tor)), "Y" if k % 2 else "v")
    if view == "se":
        c = add(S.pel, rot(0.4, -5.0, S.tor))
        P.ellipse(c, 1.2, 1.0, "y"); P.px((c[0] - 0.5, c[1]), "k"); P.px((c[0] + 0.7, c[1]), "k")


def robe(P, S, view, p, kind):
    flip = 1 if view == "se" else -1
    T = lambda pts, ch, f=flip: P.shape(S.pel, S.tor, pts, ch, flip=f)
    sw = p.get("sway", 0.0)
    hem = [(-5.2, -1.5), (5.0, -1.8), (7.2 + sw, 15.6), (4.0 + sw, 16.6), (0.0 + sw, 16.2), (-3.8 + sw, 17.0), (-7.6 + sw, 16.4)]
    T(hem, "T")
    P.shape(S.pel, S.tor, [(1.8 + sw * 0.5, -1.6), (5.0, -1.8), (7.2 + sw, 15.6), (4.0 + sw, 16.6), (2.6 + sw, 16.2)], "t")
    P.line(add(S.pel, rot(-7.4 * flip + sw, 16.2, S.tor)), add(S.pel, rot(7.0 * flip + sw, 15.4, S.tor)), "U")
    P.line(add(S.pel, rot(-7.2 * flip + sw, 15.0, S.tor)), add(S.pel, rot(6.8 * flip + sw, 14.2, S.tor)), "u")
    T(ROBE_CHEST, "T")
    P.shape(S.pel, S.tor, [(2.6, -13.2), (4.6, -13.4), (5.4, -9.6), (4.8, -1.5), (3.0, -1.5)], "t")
    if view == "se":                                   # embroidered front strip
        P.shape(S.pel, S.tor, [(0.0, -12.0), (1.4, -12.0), (1.6 + sw * 0.6, 15.6), (0.2 + sw * 0.6, 15.6)], "u")
        for b in range(-10, 15, 4):
            P.px(add(S.pel, rot(0.8 + sw * 0.6 * max(0, b) / 15, b, S.tor)), "U")
    T([(-5.2, -2.4), (5.0, -2.6), (5.0, -0.4), (-5.2, -0.2)], "L")
    if view == "se":
        P.shape(S.pel, S.tor, [(-4.6, -0.4), (-2.4, -0.4), (-2.2, 3.2), (-4.4, 3.4)], "L")            # pouch
        for (a, b) in ((3.0, 0.0), (3.6, 2.0), (3.2, 4.0)):                                           # hanging bones
            P.px(add(S.pel, rot(a, b, S.tor)), "Y")
    else:
        P.shape(S.pel, S.tor, [(2.2, -0.4), (4.4, -0.4), (4.4, 3.2), (2.4, 3.4)], "L")


def cape(P, S, view, p, kind):
    """Wolf pelt hanging from the hood down the back (Згуба) / short cloak (servant)."""
    if kind != "zguba":
        flip = 1 if view == "se" else -1
        P.shape(S.pel, S.tor, [(-6.6, -14.0), (6.0, -14.4), (6.8, -9.0), (-7.2, -8.6)], "F", flip=flip)
        return
    sw = p.get("sway", 0.0)
    if view == "se":     # back is screen-left: pelt visible as a band behind the near side
        pts = [(-3.0, -15.0), (-7.8, -12.0), (-8.6 + sw, 2.0), (-8.0 + sw, 10.0), (-9.2 + sw, 13.0), (-6.6 + sw, 12.0),
               (-5.0 + sw, 14.0), (-4.6, 4.0)]
    else:                # back view: the whole pelt over the back, legs dangling
        pts = [(-5.6, -16.0), (5.6, -16.0), (7.4, -10.0), (7.0 + sw, 6.0), (8.4 + sw, 11.0), (5.6 + sw, 9.0), (3.0 + sw, 12.5),
               (0.0 + sw, 9.6), (-3.0 + sw, 12.5), (-5.6 + sw, 9.0), (-8.2 + sw, 11.2), (-7.0 + sw, 6.0), (-7.4, -10.0)]
    P.shape(S.pel, S.tor, pts, "F")
    if view == "ne":
        P.shape(S.pel, S.tor, [(1.0, -14.0), (5.6, -15.0), (7.0, -10.0), (6.6 + sw, 6.0), (2.0 + sw, 6.0)], "f")
        P.shape(S.pel, S.tor, [(-0.6, -2.0), (0.6, -2.0), (0.4 + sw, 9.0), (-0.4 + sw, 9.0)], "j")   # spine line


def paws(P, S, view):
    """Pelt forelegs hanging over the shoulders in front (SE only)."""
    if view != "se":
        return
    for (a0, a1) in ((-4.6, -4.0), (3.6, 4.0)):
        p0 = add(S.pel, rot(a0, -13.0, S.tor)); p1 = add(S.pel, rot(a1, -6.0, S.tor))
        P.limb(p0, p1, "F", 2)
        P.px(add(p1, (0, 1)), "y"); P.px(add(p1, (1, 1)), "y")


def glow_ball(P, c, r, phase):
    """Небыль fire in the palm (ведовство / подъём)."""
    if r <= 0:
        return
    P.ellipse(c, r + 0.6, r + 0.6, "n")
    P.ellipse(c, r, r, "N")
    if r >= 1.5:
        P.ellipse((c[0] - 0.3, c[1] + 0.3), r * 0.45, r * 0.45, "M")
    for k in range(3):
        ang = phase * 1.1 + k * 2.1
        P.px((c[0] + math.cos(ang) * (r + 2.2), c[1] + math.sin(ang) * (r + 1.8) - 1), "N" if k % 2 else "n")


KIND_ADJ = {"zguba": dict(neck=-1.0, above=0.0), "servant": dict(neck=2.2, above=3.0)}


def draw(p, view, kind="zguba", phase=0):
    p = {k: (v[view] if isinstance(v, dict) and set(v) <= {"se", "ne"} else v) for k, v in p.items()}
    adj = KIND_ADJ[kind]
    p["neck"] = p["neck"] + adj["neck"]
    if isinstance(p["staff"], dict):
        p["staff"] = dict(p["staff"], above=p["staff"]["above"] + adj["above"])
    S = Skel(p, view)
    # neck length per character (old, slightly stooped)
    S.neck = S.T(0, -p["neck"]); S.hc = add(S.neck, rot(1.0 if view == "se" else 0.4, -4.4, S.head_ang))
    P = Painter()
    st = p["staff"]

    def staff_arm():
        if isinstance(st, dict):
            staff(P, S.hn, st, view, kind, p["eye"])
        arm(P, S.sh_n, S.en, S.hn, sleeve="T", cuff="t")

    if isinstance(st, tuple):                          # dropped staff ("ground", grip, ang)
        staff(P, st[1], dict(ang=st[2], below=25.0, above=22.0), view, kind, p["eye"])
    lying = abs(S.tor) > 60
    if view == "se":
        cape(P, S, view, p, kind)
    def far_arm():
        arm(P, S.sh_f, S.ef, S.hf, sleeve="T", cuff="t")
        if p.get("glow_far"):
            glow_ball(P, add(S.hf, p.get("glow_off", (0.0, -1.5))), p["glow_far"], phase)
    if not p.get("far_front"):
        far_arm()
    if p.get("near_behind"):
        staff_arm()
    leg(P, S.hip_f, S.kf, S.ff, view, far=True, wrap=False)
    leg(P, S.hip_n, S.kn, S.fn, view, wrap=False)
    robe(P, S, view, p, kind)
    beads(P, S, view, kind)
    if view == "ne":
        cape(P, S, view, p, kind)
    head(P, S, view, p, kind)
    paws(P, S, view) if kind == "zguba" else None
    if p.get("far_front"):
        far_arm()
    if not p.get("near_behind"):
        staff_arm()
    if p.get("glow_front"):
        glow_ball(P, p["glow_front"][0], p["glow_front"][1], phase)
    for (c, ch) in p.get("motes", ()):
        P.px(c, ch)
    spr = build(P, SCHEME[kind])
    return spr


# --------------------------------------------------------------------------
# animations (GDD §12.1.2: idle 4, ходьба 8, ведовство 6, подъём павших 6, урон 2, гибель 8)
# --------------------------------------------------------------------------
STAFF = dict(ang=-91.0, below=25.0, above=23.0)


def idle(i):
    b = [0, 0, 1, 1][i]
    return P_(pel=(0.0, -19.0 + b), hn=(0.0, 7.0, -25.0 + b), hf=(1.0, 6.0, -21.0 + b), sway=[0, 0.3, 0.3, 0][i],
              eye=[3, 3, 2, 3][i], staff=dict(STAFF, below=25.0 - b))


def walk(i):
    t = i / 8.0 * 2 * math.pi
    sn = math.sin(t)
    bob = round(abs(sn) * 0.9)
    return P_(pel=(0.4, -19.0 + bob), tor=3.0, fn=(3.0 * sn, 2.6), ff=(-3.0 * sn, 2.4),
              lift_n=max(0.0, 1.6 * math.cos(t)), lift_f=max(0.0, -1.6 * math.cos(t)),
              hn=(0.5 + 1.2 * sn, 7.0, -25.0 + bob), hf=(1.0 - 1.0 * sn, 6.0, -21.0 + bob),
              staff=dict(STAFF, ang=-91.0 + 4.0 * sn, below=25.0 - bob - abs(sn) * 1.0), sway=-1.0 * sn, eye=3)


FF = {"se": True, "ne": False}
CAST = [
    dict(tor=-3.0, hf=(3.0, 5.0, -33.0), glow_far=1.4, eye=3, far_front=FF),
    dict(tor=-5.0, hf=(1.0, 5.0, -37.0), glow_far=2.0, eye=4, far_front=FF),
    dict(tor=5.0, hf=(7.0, 2.0, -31.0), glow_far=2.6, eye=4, mouth=True, pel=(0.8, -19.0), far_front=FF),
    dict(tor=8.0, hf=(11.0, 1.0, -29.0), glow_far=0, eye=4, mouth=True, pel=(1.2, -18.8), fn=(1.6, 2.6), release=True, far_front=FF),
    dict(tor=5.0, hf=(8.0, 2.0, -26.0), glow_far=0.8, eye=3, pel=(1.0, -19.0), fn=(1.6, 2.6), far_front=FF),
    dict(tor=1.0, hf=(3.0, 5.0, -23.0), eye=3),
]
CAST_RELEASE = 3


def cast(i):
    d = dict(CAST[i]); d.pop("release", None)
    p = P_(**d)
    if CAST[i].get("release"):
        p["glow_burst"] = 3.4
    return p


def _ring(cx, cy, rx, ry, ch, step=0.35):
    pts = []
    t = 0.0
    while t < 2 * math.pi:
        pts.append(((cx + math.cos(t) * rx, cy + math.sin(t) * ry), ch))
        t += step
    return pts


def _motes(x0, x1, y0, h, k, seed):
    out = []
    for j in range(k):
        x = x0 + (x1 - x0) * ((j * 0.618 + seed * 0.37) % 1.0)
        y = y0 - h * ((j * 0.414 + seed * 0.23) % 1.0)
        out.append(((x, y), "N" if j % 3 == 0 else ("M" if j % 5 == 1 else "n")))
    return out


RAISE = [
    dict(tor=-2.0, hn=(1.0, 6.0, -23.0), staff=dict(STAFF, ang=-82.0, below=23.0), hf=(2.0, 5.0, -29.0), glow_far=1.4, eye=3, far_front=FF),
    dict(tor=-6.0, hn=(0.0, 6.0, -27.0), staff=dict(STAFF, ang=-86.0, below=21.0, above=20.0), hf=(2.0, 4.0, -39.0),
         glow_far=2.2, eye=4, mouth=True, far_front=FF),
    dict(tor=4.0, hn=(2.0, 6.0, -24.0), staff=dict(STAFF, ang=-91.0, below=25.0), hf=(5.0, 4.0, -38.0), glow_far=2.4, eye=4,
         mouth=True, ring=(5.0, 2.4), far_front=FF),
    dict(tor=3.0, hn=(2.0, 6.0, -24.0), staff=dict(STAFF, ang=-91.0, below=25.0), hf=(7.0, 3.0, -36.0), glow_far=2.0, eye=4,
         ring=(9.0, 4.0), rise=(1, 6.0), far_front=FF),
    dict(tor=2.0, hn=(2.0, 6.0, -24.0), staff=dict(STAFF, ang=-91.0, below=25.0), hf=(7.0, 3.0, -34.0), glow_far=1.6, eye=4,
         ring=(12.0, 5.2), rise=(2, 11.0), far_front=FF),
    dict(tor=0.0, hn=(1.0, 7.0, -25.0), hf=(3.0, 5.0, -24.0), glow_far=0.6, eye=3, rise=(3, 14.0)),
]


def raise_fallen(i):
    d = dict(RAISE[i]); ring = d.pop("ring", None); rise = d.pop("rise", None)
    p = P_(**d)
    p["ring"] = ring; p["rise"] = rise
    return p


HURT = [
    dict(pel=(-2.0, -18.6), tor=-10.0, head=-8.0, hf=(-1.0, 7.0, -29.0), hn=(-1.0, 7.0, -26.0), mouth=True, eyes="closed",
         staff=dict(STAFF, ang=-100.0)),
    dict(pel=(-1.0, -18.8), tor=-5.0, head=-4.0, hf=(0.0, 6.0, -24.0), hn=(-0.5, 7.0, -25.0), staff=dict(STAFF, ang=-95.0)),
]


def hurt(i):
    return P_(**HURT[i])


def death(i):
    G = ("ground", (-6.0, 3.5), 182.0)
    lie = dict(staff=G, eyes="closed", fn_abs=(13.0, 3.0), ff_abs=(10.0, -2.0))
    fr = [
        dict(pel=(-2.0, -18.5), tor=-12.0, head=-12.0, hf=(-1.0, 7.0, -31.0), hn=(-2.0, 8.0, -27.0), mouth=True, eyes="closed",
             staff=dict(STAFF, ang=-106.0), eye=3),
        dict(pel=(-3.0, -15.0), tor=-18.0, head=-12.0, hf=(0.0, 7.0, -26.0), hn=(-3.0, 8.0, -22.0), mouth=True, eyes="closed",
             staff=dict(STAFF, ang=-122.0, below=20.0), eye=2),
        dict(pel=(-3.5, -11.0), tor=-30.0, head=-10.0, hf=(2.0, 6.0, -16.0), hn=(-7.0, 6.0, -13.0), staff=G, eyes="closed", eye=2),
        dict(lie, pel=(-3.0, -8.5), tor=-44.0, head=-8.0, hn=(-14.0, -10.0), hf=(-19.0, -17.0), fn_abs=(8.0, 2.0), ff_abs=(5.0, -1.0), eye=1),
        dict(lie, pel=(-2.5, -6.5), tor=-58.0, head=-4.0, hn=(-17.0, -4.0), hf=(-21.0, -15.0), eye=1),
        dict(lie, pel=(-2.0, -5.5), tor=-64.0, head=-2.0, hn=(-16.0, -2.0), hf=(-22.0, -14.0), eye=0),
        dict(lie, pel=(-2.0, -5.0), tor=-63.0, head=0.0, hn=(-16.0, -1.5), hf=(-22.0, -13.0), eye=0),
        dict(lie, pel=(-2.0, -5.0), tor=-63.0, head=0.0, hn=(-16.0, -1.5), hf=(-22.0, -13.0), eye=0),
    ][i]
    return P_(**fr)


ANIMS = [
    ("idle", 4, 5, True, idle),
    ("walk", 8, 9, True, walk),
    ("cast", 6, 10, False, cast),
    ("raise_fallen", 6, 8, False, raise_fallen),
    ("hurt", 2, 8, False, hurt),
    ("death", 8, 10, False, death),
]


def frame(anim_fn, i, view, kind="zguba"):
    p = anim_fn(i)
    extra = []
    if p.get("glow_burst"):
        # burst in front of the casting hand: drawn via glow_front
        S = Skel({k: (v[view] if isinstance(v, dict) and set(v) <= {"se", "ne"} else v) for k, v in p.items()}, view)
        p["glow_front"] = ((S.hf[0] + 3.5, S.hf[1] - 1.5), p["glow_burst"])
    if p.get("ring"):
        rx, ry = p["ring"]
        Sx = 7.0 * (-1 if view == "se" else 1)       # staff butt x (near side)
        extra += _ring(Sx, 0.5, rx, ry, "n")
        extra += _ring(Sx, 0.5, rx * 0.7, ry * 0.7, "N", step=0.6)
    if p.get("rise"):
        k, h = p["rise"]
        extra += _motes(8.0, 20.0, 1.0, h, 5 + 2 * k, k)
    p["motes"] = extra
    return draw(p, view, kind, phase=i % 6)

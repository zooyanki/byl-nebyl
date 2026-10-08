"""Черноярец-топорщик (base, designed here: no sprite existed) and its
recolour «Черноярец-поджигатель» (+ torch in the left hand)."""
import math
from rig import Painter, build, legend, rot, add
from human import Skel, leg, arm, axe, torch, pose

# ---- colour schemes: the same letters, different ramps = a true recolour
SCHEME = {
    # v2 recolour (designer 08.10, scale.md §4.4): red is the hero's only accent, so the
    # черноярцы wear dark-grey / soot shirts; топорщик accent = steel, поджигатель = smouldering stripes.
    "axeman": legend(
        T=("stone", 2, True, False), t=("stone", 1, False, False),           # dark-grey (soot) shirt
        C=("iron", 4, True, False), c=("iron", 3, False, False),
        F=("fur", 5, True, False, "fur"), f=("fur", 4, False, False, "fur"), j=("fur", 3, False, False, "fur"),
        P=("wood", 2, True, False),
        U=("iron", 5, False, False), u=("iron", 4, False, False)),          # steel trim / studs
    "arsonist": legend(
        T=("stone", 3, True, False), t=("stone", 2, False, False),           # soot-grey shirt
        C=("wood", 2, True, False), c=("wood", 1, False, False),            # sooty brown felt cap
        F=("fur", 2, True, False, "fur"), f=("fur", 1, False, False, "fur"), j=("fur", 1, False, False, "fur"),  # scorched black pelt
        P=("wood", 1, True, False),                                          # dark-brown trousers
        U=("fire", 2, False, False), u=("bronze", 2, False, False)),        # ember-orange hem (not emissive)
}

CHEST = [(-5.6, -13.2), (4.6, -13.6), (5.6, -10.0), (5.0, -1.5), (-5.2, -1.2), (-6.2, -9.5)]
MANTLE = {
    "se": [(-7.0, -14.6), (-2.0, -15.6), (3.0, -15.4), (6.6, -14.2), (7.0, -11.0), (5.4, -9.6), (4.0, -11.0), (2.0, -8.8),
           (0.0, -10.6), (-2.2, -8.6), (-4.0, -10.4), (-6.0, -8.8), (-7.6, -10.5)],
    "ne": [(-7.0, -14.6), (-2.0, -15.8), (3.0, -15.6), (7.0, -14.0), (7.4, -8.0), (6.0, -4.5), (4.0, -6.5), (2.0, -4.0),
           (0.0, -6.0), (-2.0, -3.8), (-4.0, -6.0), (-6.0, -4.4), (-7.6, -8.0)],
}


def head(P, S, view, scheme, p):
    hc, ha = S.hc, S.head_ang
    H = lambda pts, ch: P.shape(hc, ha, pts, ch)
    R = lambda a, b: add(hc, rot(a, b, ha))
    if view == "se":
        P.ellipse(R(-1.6, -0.4), 2.4, 3.4, "B")
        P.ellipse(R(0.5, 0.2), 3.3, 3.9, "S")
        H([(-1.0, 2.2), (1.4, 2.8), (3.8, 2.0), (3.6, 3.8), (2.2, 5.2), (0.2, 5.4), (-1.2, 4.0)], "B")
        P.line(R(1.6, 1.8), R(3.6, 1.6), "B")                                # moustache
        P.px(R(3.9, 0.2), "S"); P.px(R(4.2, 0.4), "S")                       # nose
        P.px(R(-1.2, 0.4), "s"); P.px(R(-1.2, 1.4), "s")                     # ear
        if p.get("eyes") == "closed":
            P.line(R(1.6, -0.4), R(2.8, -0.4), "b")
        else:
            P.px(R(2.4, -0.6), "k")
        P.line(R(1.4, -1.7), R(3.2, -1.5), "b")
        if p.get("mouth"):
            P.px(R(3.0, 2.6), "k"); P.px(R(3.0, 3.4), "k")
        if scheme == "arsonist":
            P.px(R(-0.2, 1.0), "b")                                          # soot smear on the cheek
    else:
        P.ellipse(R(0.0, 0.0), 3.4, 3.8, "B")
        P.ellipse(R(2.5, 0.8), 1.3, 2.6, "S")
        P.px(R(1.6, 0.4), "s")
        H([(1.2, 2.6), (3.6, 2.0), (3.4, 4.6), (1.6, 5.4)], "B")
    clip = lambda xx, yy: yy <= (hc[1] - 1.4)
    P.ellipse(R(0.2, -1.6), 4.0, 3.6, "C", clip=clip)
    P.line(R(-3.8, -1.6), R(4.0, -1.8), "c")
    if view == "se":
        P.px(R(3.4, -3.0), "C")


def body(P, S, view, p, scheme):
    flip = 1 if view == "se" else -1
    T = lambda pts, ch, f=flip: P.shape(S.pel, S.tor, pts, ch, flip=f)
    sw = p.get("sway", 0.0)
    T([(-5.4, -1.5), (5.2, -1.8), (6.6 + sw, 6.6), (4.0 + sw, 7.2), (1.0 + sw, 6.6), (-1.5 + sw, 7.6), (-4.0 + sw, 6.6), (-6.8 + sw, 7.6)], "T")
    P.shape(S.pel, S.tor, [(1.5 + sw, -1.6), (5.2, -1.8), (6.6 + sw, 6.6), (4.0 + sw, 7.2), (2.5 + sw, 6.6)], "t")
    P.line(add(S.pel, rot(-6.6 * flip + sw, 7.4, S.tor)), add(S.pel, rot(6.4 * flip + sw, 6.6, S.tor)), "U")  # hem trim
    T(CHEST, "T")
    P.shape(S.pel, S.tor, [(2.6, -13.4), (4.8, -13.4), (5.6, -10.0), (5.0, -1.5), (3.0, -1.5)], "t")     # chest shade
    if view == "se":
        P.shape(S.pel, S.tor, [(0.2, -12.4), (1.4, -12.4), (1.4, -2.6), (0.2, -2.6)], "t")              # placket
        P.shape(S.pel, S.tor, [(0.4, -11.8), (1.2, -11.8), (1.2, -10.4), (0.4, -10.4)], "U")
    if scheme == "arsonist":
        for (a, b) in ((-3.0, -6.0), (2.0, 3.0), (-2.0, 4.0), (3.4, -8.0)):
            P.px(add(S.pel, rot(a * flip, b, S.tor)), "t")
        # smouldering ember stripes (патарина-like): two on the chest, three on the skirt
        L_ = lambda a, b0, b1, ch: P.line(add(S.pel, rot(a * flip, b0, S.tor)), add(S.pel, rot(a * flip, b1, S.tor)), ch)
        for a in (-3.0, 3.0):
            L_(a, -12.4, -3.0, "U" if a * flip < 0 else "u")
        for a in (-4.0, -0.4, 3.4):
            L_(a + sw, 0.4, 6.2, "U" if (a * flip) < 2 else "u")
    else:
        for a in (-3.6, -1.2, 3.6):                                                                    # steel belt studs
            P.px(add(S.pel, rot(a * flip, -1.4, S.tor)), "U")
    T([(-5.4, -2.4), (5.2, -2.6), (5.2, -0.4), (-5.4, -0.2)], "L")                                      # belt
    if view == "se":
        P.shape(S.pel, S.tor, [(1.0, -2.4), (2.6, -2.4), (2.6, -0.6), (1.0, -0.6)], "Z")
    else:
        P.shape(S.pel, S.tor, [(-4.4, -2.0), (-2.2, -2.0), (-2.2, 1.6), (-4.4, 1.6)], "L")             # pouch on the back
    T(MANTLE[view], "F")
    P.shape(S.pel, S.tor, [(2.0, -14.8), (6.6, -14.2), (7.0, -11.0), (5.4, -9.6), (4.0, -11.0), (2.4, -9.6)], "f")


def draw(p, view, scheme="arsonist", phase=0, with_torch=None):
    """One frame. p: pose dict (human.pose + extras):
       axe_ang (deg), axe_edge, axe=None/"hand"/("ground", pos, ang)
       torch: "hand"/None/("ground", pos, ang, flame_scale)/("fly",) ; torch_ang
       near_behind: draw the near arm + axe behind the body (wind-ups)."""
    p = {k: (v[view] if isinstance(v, dict) and set(v) <= {"se", "ne"} else v) for k, v in p.items()}
    S = Skel(p, view)
    P = Painter()
    if with_torch is None:
        with_torch = scheme == "arsonist"
    tstate = p.get("torch", "hand") if with_torch else None
    torch_root = None
    fx = 1 if view == "se" else -1

    def far_arm():
        nonlocal torch_root
        arm(P, S.sh_f, S.ef, S.hf, sleeve="T", cuff="L")
        if tstate == "hand":
            torch_root = torch(P, S.hf, p.get("torch_ang", -80), phase, lean=p.get("flame_lean", 0.0))
            P.ellipse(S.hf, 1.4, 1.4, "S")

    def near_arm():
        if p.get("axe", "hand") == "hand":
            if p.get("smear_from") is not None:          # swing trail: arc of the blade around the shoulder
                hx, hy = S.hn
                a1 = math.radians(p["axe_ang"])
                tip = (hx + math.cos(a1) * 13.5, hy + math.sin(a1) * 13.5)
                cx, cy = S.sh_n
                r = math.hypot(tip[0] - cx, tip[1] - cy)
                t1 = math.atan2(tip[1] - cy, tip[0] - cx)
                t0 = math.radians(p["smear_from"])
                if t1 - t0 > math.pi:
                    t1 -= 2 * math.pi
                t0 = max(t0, t1 - math.radians(75))
                n = 10
                pts = [(cx + math.cos(t0 + (t1 - t0) * k / n) * r, cy + math.sin(t0 + (t1 - t0) * k / n) * r) for k in range(n + 1)]
                for k in range(n):
                    P.line(pts[k], pts[k + 1], "I" if k > n // 3 else "h")
                    if k > n // 2:
                        q0 = (cx + (pts[k][0] - cx) * 0.86, cy + (pts[k][1] - cy) * 0.86)
                        q1 = (cx + (pts[k + 1][0] - cx) * 0.86, cy + (pts[k + 1][1] - cy) * 0.86)
                        P.line(q0, q1, "h")
            axe(P, S.hn, p.get("axe_ang", 100), edge=p.get("axe_edge", 1))
        arm(P, S.sh_n, S.en, S.hn, sleeve="T", cuff="L")

    # ground items first (under everything)
    if isinstance(p.get("axe"), tuple):
        _, pos, ang = p["axe"]
        axe(P, pos, ang, edge=1)
    if with_torch and isinstance(tstate, tuple) and tstate[0] == "ground":
        _, pos, ang, fs = tstate
        torch_root = torch(P, pos, ang, phase, lit=fs > 0, flame_scale=fs)
    lying = abs(S.tor) > 60
    if not lying:
        far_arm()
    leg(P, S.hip_f, S.kf, S.ff, view, far=True)
    leg(P, S.hip_n, S.kn, S.fn, view)
    if lying:
        far_arm()
    if p.get("near_behind"):
        near_arm()
    body(P, S, view, p, scheme)
    head(P, S, view, scheme, p)
    if not p.get("near_behind"):
        near_arm()
    spr = build(P, SCHEME[scheme])
    spr["torch_root"] = None if torch_root is None else (torch_root[0] + 32, torch_root[1] + 56)
    return spr

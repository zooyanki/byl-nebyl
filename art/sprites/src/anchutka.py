"""Анчутка (GDD §5.2 E1, §12.1.2; act1: «мелкий бес-поджигатель: быстрый, кидает угли и убегает»;
codex: «мелкий бес, что водится у печей и пожарищ»). Один спрайт для стай Залесья и свиты Мары.
scale.md §2: рост 24–28 (цель 26 = def.height прототипа), силуэт 16–18, кадр 32x40, pivot (16,34),
2 вида (se, ne) + зеркало, детали блоками от 2x2 (мелкий монстр, scale.md §5).
Look: сутулый лысый бес в саже — большая голова с острыми ушами и рожками-бугорками, длинные руки
почти до земли, короткие кривые ноги, хвост с тлеющей кисточкой. Кожа — сажа (slate / slate_dk),
брюхо и морда — зола (slate_lt / mist), глаза, пасть и трещинки — угли (ember / flame). Без red:
красный — акцент героя (scale.md §4.4). Faces +x in both views."""
import math
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
from bigrig import Pn, build, rot, add, ik, TAU, over

W, H, PIV = 32, 40, (16, 34)

LEG = rig.legend(
    K=("stone", 3, True, False), k2=None,
    D=("stone", 2, True, False),                    # far limbs / shade side (soot)
    J=("stone", 4, True, False), j=("stone", 5, False, False),   # ash belly / muzzle
    Y=("birch", 4, True, False), y=("birch", 3, False, False),   # horn nubs, claws (bone)
    k=("ink", 0, False, False),
)
del LEG["k2"]


def P_(**kw):
    d = dict(bob=0.0, lean=34.0, hn=(9.0, -1.0), hf=(4.0, -1.5), fn=(3.0, 0.0), ff=(-2.5, 0.0), tail=0.0,
             head=(0.0, 0.0), eyes=1, mouth=0, coal=None, coal_r=1.5, crouch=0.0, sink=0.0, ears=0.0)
    d.update(kw)
    return d


class Skel:
    """hunched: short legs, egg body leaning forward, big head pushed ahead of the chest."""
    def __init__(self, p):
        b = p["bob"] + p["crouch"]
        self.hip = (-1.0, -6.5 + b)
        lean = math.radians(p["lean"])
        self.chest = (self.hip[0] + 7.0 * math.sin(lean), self.hip[1] - 7.0 * math.cos(lean))
        hx, hy = p["head"]
        self.head = (self.chest[0] + 4.0 + hx, self.chest[1] - 4.0 + hy)
        self.sh_n = add(self.chest, (1.5, 0.5))
        self.sh_f = add(self.chest, (-1.0, -0.5))


def _leg(P, hip, foot, far):
    knee = ik(hip, foot, 3.6, 3.6, -1)
    knee = (knee[0] + 1.0, knee[1])
    ch = "D" if far else "K"
    P.limb(hip, knee, ch, 3)
    P.limb(knee, foot, ch, 2)
    P.line(foot, add(foot, (2.0, 0)), "y" if far else "Y")          # clawed toes


def _arm(P, sh, hand, far):
    """long thin arm (reaches the ground at rest), big hand with 2 bone claws."""
    el = ik(sh, hand, 5.5, 5.5, 1)
    ch = "D" if far else "K"
    fo = "D" if far else "J"                                        # near forearm / hand dusted with ash
    P.limb(sh, el, ch, 2)
    P.limb(el, hand, fo, 2)
    P.ellipse(hand, 1.5, 1.2, fo)
    for k in (-1, 1):
        P.line(add(hand, (0.8, 0.3)), add(hand, (2.2, 0.8 + k * 0.9)), "y" if far else "Y")


def _tail(P, hip, p, view):
    """thin tail curling low behind, smouldering tuft at the tip."""
    s = p["tail"]
    pts = [add(hip, (-2.0, 1.0)), add(hip, (-5.0, 3.5)), add(hip, (-8.5, 3.0 + s * 0.5)), add(hip, (-10.5, 0.5 + s)),
           add(hip, (-10.0 + s * 0.5, -1.5 + s))]
    for a, b in zip(pts, pts[1:]):
        P.line(a, b, "D", 1)
    tip = pts[-1]
    P.ellipse(add(tip, (0.0, -0.8)), 1.1, 1.3, "q")                # smouldering tuft
    P.px(add(tip, (0.0, -1.4)), "E")


def _body(P, S, p, view):
    mid = ((S.hip[0] + S.chest[0]) / 2, (S.hip[1] + S.chest[1]) / 2)
    P.ellipse(mid, 4.0, 4.4, "D")
    P.ellipse(add(S.chest, (0.3, 0.5)), 3.8, 3.0, "D")
    if view == "se":
        P.ellipse(add(mid, (1.8, 1.6)), 2.0, 2.6, "J")              # ash belly
        P.px(add(mid, (2.2, 1.0)), "q")                             # smouldering cracks
        P.px(add(mid, (1.4, 3.0)), "q")
    else:
        for k in range(3):                                          # spine knobs
            P.px(add(S.chest, (-1.8 - k * 1.2, 0.6 + k * 1.8)), "K")


def _head(P, S, p, view):
    c = S.head
    e = p["ears"]
    # long pointed ears swept back (one big, the far one peeks over the crown)
    P.poly([add(c, (-1.0, -4.5)), add(c, (-4.5 - e * 0.5, -8.5 - e * 0.5)), add(c, (-3.5, -3.0))], "D")
    P.poly([add(c, (-2.0, -3.5)), add(c, (-10.0 - e, -4.5 - e * 0.6)), add(c, (-8.0 - e, -2.5 - e * 0.3)), add(c, (-2.5, 1.0))], "K")
    P.line(add(c, (-3.5, -1.5)), add(c, (-8.0 - e, -3.6 - e * 0.5)), "D")       # inner ear shade
    P.ellipse(c, 5.6, 4.6, "K")                                     # big bald head
    P.ellipse(add(c, (0.5, -1.0)), 5.0, 3.8, "K")
    # horn nubs (bone, 2x2 blocks)
    for hx in (0.0, 3.0):
        P.px(add(c, (hx, -4.6)), "Y"); P.px(add(c, (hx + 1, -4.6)), "Y"); P.px(add(c, (hx + 0.5, -5.6)), "y")
    if view == "se":
        P.ellipse(add(c, (3.0, 1.8)), 2.8, 2.0, "J")                # ash muzzle
        P.px(add(c, (5.6, 1.2)), "j")                               # snout tip
        col = {0: "k", 1: "E", 2: "e"}[p["eyes"]]
        P.line(add(c, (0.6, -1.0)), add(c, (1.4, -1.0)), col, 2)   # 2x2 ember eyes
        P.line(add(c, (3.4, -1.2)), add(c, (3.9, -1.2)), col, 2)
        if p["mouth"]:
            P.line(add(c, (1.5, 2.8)), add(c, (5.0, 2.6)), "k", 1)
            P.line(add(c, (2.0, 3.6)), add(c, (4.5, 3.4)), "q" if p["mouth"] >= 2 else "k")   # ember gullet
        else:
            P.line(add(c, (1.5, 3.0)), add(c, (5.0, 2.4)), "k")     # grin
        P.px(add(c, (3.0, 3.6)), "Y")                               # fang
    else:
        P.ellipse(add(c, (-1.0, 0.5)), 3.0, 2.5, "D")               # back of the skull in shade


def draw(p, view, ph):
    P = Pn(W, H, PIV)
    S = Skel(p)
    sink = p["sink"]
    if view == "se":
        _tail(P, S.hip, p, view)
        _arm(P, S.sh_f, p["hf"], True)
        _leg(P, S.hip, p["ff"], True)
        _body(P, S, p, view)
        _leg(P, add(S.hip, (1.0, 0.5)), p["fn"], False)
        _head(P, S, p, view)
        _arm(P, S.sh_n, p["hn"], False)
    else:
        _arm(P, S.sh_n, p["hn"], True)
        _leg(P, add(S.hip, (1.0, 0.5)), p["fn"], True)
        _head(P, S, p, view)
        _body(P, S, p, view)
        _leg(P, S.hip, p["ff"], False)
        _arm(P, S.sh_f, p["hf"], False)
        _tail(P, S.hip, p, view)
    if p["coal"] is not None:
        c = p["coal"]
        P.ellipse(c, p["coal_r"] + 0.6, p["coal_r"] + 0.4, "q")
        P.ellipse(c, p["coal_r"], p["coal_r"] * 0.8, "E")
        P.px(add(c, (0.3, -0.3)), "e")
    if sink > 0:                                                    # death: soot crumbles from the top
        P.keep(set("KDJjYykqEe"), lambda x, y: y > -30 + sink)
    return build(P, LEG)


# --------------------------------------------------------------------------
# animations (GDD §12.1.2: idle 4, бег 6, бросок угля 5, урон 2, гибель 6)
# --------------------------------------------------------------------------
def idle(i):
    t = i / 4 * TAU
    b = 0.5 * math.sin(t)
    return P_(bob=b, hn=(9.0, -1.0), hf=(4.0, -1.5), tail=1.0 * math.sin(t + 1.0), ears=0.5 * math.sin(t),
              head=(0.0, b * 0.5)), t


def walk(i):          # бег: low fast scuttle, knuckles on the ground like an ape
    t = i / 6 * TAU
    s = math.sin(t)
    hop = abs(math.cos(t)) * 1.5
    return P_(bob=-hop, lean=44.0, fn=(3.5 + 3.5 * s, -max(0, -math.cos(t)) * 2.0), ff=(-2.5 - 3.5 * s, -max(0, math.cos(t)) * 2.0),
              hn=(11.0 - 3.5 * s, -0.5 - max(0, s) * 2.5), hf=(6.0 + 3.5 * s, -1.0 - max(0, -s) * 2.5),
              tail=1.5 * math.sin(t + 1.5), ears=1.2, head=(0.5, 1.0)), t


THROW = [  # pulls a coal out of its smouldering belly, winds back over the head, flings it on frame 3
    dict(lean=22.0, hn=(5.0, -6.0), coal=(5.5, -7.0), coal_r=1.0),
    dict(lean=12.0, hn=(-2.0, -17.0), hf=(5.0, -2.0), coal=(-2.0, -18.5), coal_r=1.5, mouth=1, crouch=0.5),
    dict(lean=6.0, hn=(-5.0, -18.0), hf=(6.0, -2.0), coal=(-5.5, -19.5), coal_r=1.7, mouth=1, eyes=2, crouch=0.8),
    dict(lean=40.0, hn=(11.0, -8.0), hf=(4.0, -2.0), coal=(13.0, -10.0), coal_r=1.6, mouth=2, eyes=2, crouch=-0.3),
    dict(lean=38.0, hn=(11.0, -3.0), mouth=1),
]
THROW_RELEASE = 3
THROW_SPAWN = (13.0, -10.0)          # coal position on the release frame, relative to the pivot (SE)


def coal_throw(i):
    return P_(**THROW[i]), i * 1.3


HURT = [dict(lean=18.0, head=(-1.5, 0.0), hn=(6.0, -7.0), hf=(1.0, -7.0), eyes=0, mouth=2, ears=1.0),
        dict(lean=28.0, head=(-0.5, 0.5), hn=(8.0, -3.0), hf=(3.0, -3.0), mouth=1, ears=0.8)]


def hurt(i):
    return P_(**HURT[i]), i * 2.0


DEATH = [  # squeals, topples back, crumbles into a soot heap with dying embers
    dict(lean=10.0, head=(-1.5, 0.5), hn=(5.0, -12.0), hf=(-2.0, -12.0), mouth=2, eyes=2, ears=1.0),
    dict(lean=-10.0, crouch=1.5, head=(-2.0, 1.0), hn=(3.0, -7.0), hf=(-5.0, -8.0), mouth=2, eyes=0),
    dict(lean=-30.0, crouch=3.0, head=(-2.5, 2.5), hn=(4.0, -2.0), hf=(-7.0, -3.0), mouth=1, eyes=0, sink=8),
    dict(lean=-30.0, crouch=3.0, head=(-2.5, 2.5), hn=(4.0, -2.0), hf=(-7.0, -3.0), eyes=0, sink=16),
    dict(lean=-30.0, crouch=3.0, head=(-2.5, 2.5), hn=(4.0, -2.0), hf=(-7.0, -3.0), eyes=0, sink=24),
    dict(lean=-30.0, crouch=3.0, head=(-2.5, 2.5), hn=(4.0, -2.0), hf=(-7.0, -3.0), eyes=0, sink=34),
]


def death(i):
    return P_(**DEATH[i]), i * 1.4


ANIMS = [  # name, frames, fps, loop, fn
    ("idle", 4, 6, True, idle),
    ("walk", 6, 12, True, walk),
    ("coal_throw", 5, 7, False, coal_throw),
    ("hurt", 2, 8, False, hurt),
    ("death", 6, 10, False, death),
]


def _heap(i):
    """soot heap with embers (death frames 2-5)."""
    P = Pn(W, H, PIV)
    r = [0, 0, 4.0, 5.5, 6.5, 6.5][i]
    if r <= 0:
        return None
    P.ellipse((0.0, -1.0), r, min(2.5, r * 0.45), "D")
    P.ellipse((-0.5, -1.6), r * 0.6, 1.3, "K")
    rng = np.random.RandomState(7)
    n = [0, 0, 5, 4, 3, 2][i]
    for k in range(n):
        x, y = rng.uniform(-r + 1, r - 1), rng.uniform(-2.5, -0.5)
        P.px((x, y), "q" if k % 2 else "E")
    if i >= 3:                                                      # soot puff rising
        for k in range(3):
            P.px((-2.0 + k * 2.0, -6.0 - (i - 3) * 2.5 - k), "D")
    return build(P, LEG)


def _no_red(idx):
    """fire-aware outline rims (red) -> red_dk: pure red stays the hero's accent (scale.md §4.4)."""
    idx[idx == C["red"]] = C["red_dk"]
    return idx


def frame(fn, i, view):
    return _no_red(_frame(fn, i, view))


def _frame(fn, i, view):
    p, ph = fn(i)
    idx = draw(p, view, ph)
    if fn is death:
        h = _heap(i)
        if h is not None:
            m = h >= 0
            base = idx.copy()
            idx = h.copy()
            idx[base >= 0] = base[base >= 0]                        # body (what is left of it) over the heap
    return idx


# --------------------------------------------------------------------------
# fx: угли анчутки (GDD §12.1.5: 3 frames) — the thrown coal in flight
# --------------------------------------------------------------------------
CO_W, CO_H, CO_PIV = 12, 12, (6, 6)


def coal_fx():
    out = []
    for i in range(3):
        f = np.full((CO_H, CO_W), -1, np.int16)
        yy, xx = np.mgrid[0:CO_H, 0:CO_W]
        e = ((xx + 0.5 - 6) / 2.4) ** 2 + ((yy + 0.5 - 6) / 2.1) ** 2
        f[e <= 1] = C["ember"]
        f[((xx + 0.5 - 6.3 + 0.3 * (i - 1)) / 1.3) ** 2 + ((yy + 0.5 - 5.6) / 1.1) ** 2 <= 1] = C["flame"]
        f[(e <= 1) & (e > 0.6) & (((xx + yy + i) % 3) == 0)] = C["slate_dk"]       # charred crust
        for (dx, dy) in [((-3, -2), (-4, 1)), ((-4, -1), (-3, 2)), ((-3, 1), (-4, -2))][i]:
            pass
        sp = [[(2, 4), (1, 7)], [(1, 5), (2, 8)], [(2, 6), (0, 4)]][i]           # trailing sparks (behind, -x)
        for k, (x, y) in enumerate(sp):
            f[y, x] = C["flame"] if k == 0 else C["ember"]
        out.append(f)
    return out

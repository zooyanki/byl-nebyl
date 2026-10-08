"""Humanoid skeleton + part drawing for the 46-px people (топорщик /
поджигатель / прислужник / Згуба). See rig.py for coordinates and views."""
import math
from rig import Painter, ik, rot, add, flame

D_FWD = {"se": (1.0, 0.45), "ne": (1.0, -0.45)}

DEFAULT = dict(
    pel=(0.0, -19.0), tor=0.0, head=0.0,
    # feet: (fwd, side) on the ground; side > 0 = toward that leg's own side
    fn=(0.0, 3.2), ff=(0.0, 3.0),
    lift_n=0.0, lift_f=0.0,
    # hands: (fwd, side, y); fwd = +x (facing), side > 0 = outward on the arm's own side
    hn=(0.0, 6.6, -20.0), hf=(0.0, 6.4, -21.0),
    bend_n=None, bend_f=None,
    sway=0.0, mouth=False, eyes="open",
)


def pose(**kw):
    p = dict(DEFAULT)
    p.update(kw)
    return p


class Skel:
    """Joint positions for one frame and one view."""

    def __init__(self, p, view):
        self.p, self.view = p, view
        s = 1 if view == "se" else -1          # x sign of the NEAR side (se: near side is screen-left -> -1)
        self.near_sgn = -1 if view == "se" else 1
        self.pel = p["pel"]
        self.tor = p["tor"]
        T = lambda a, b: add(self.pel, rot(a, b, self.tor))
        ns = self.near_sgn
        self.T = T
        self.neck = T(0, -14.6)
        self.sh_n = T(5.2 * ns, -12.2)
        self.sh_f = T(-4.6 * ns, -12.8)
        self.hip_n = T(2.2 * ns, 0.4)
        self.hip_f = T(-2.2 * ns, -0.4)
        ha = self.tor + p["head"]
        self.head_ang = ha
        self.hc = add(self.neck, rot(1.0 if view == "se" else 0.4, -4.4, ha))
        dy = D_FWD[view][1]
        def foot(fs, sgn, base):
            f, sd = fs[0], fs[1]
            return (f + sd * sgn, base + f * dy)
        fn = p["fn_abs"] if p.get("fn_abs") else foot(p["fn"], ns, 0.0)
        ff = p["ff_abs"] if p.get("ff_abs") else foot(p["ff"], -ns, -1.0)
        self.fn = (fn[0], fn[1] - p["lift_n"])
        self.ff = (ff[0], ff[1] - p["lift_f"])
        self.kn = ik(self.hip_n, (self.fn[0], self.fn[1] - 1.5), 9.6, 9.0, self._kbend(self.hip_n, self.fn))
        self.kf = ik(self.hip_f, (self.ff[0], self.ff[1] - 1.5), 9.6, 9.0, self._kbend(self.hip_f, self.ff))
        def hand(h, sgn):
            if len(h) == 2:                    # absolute local (x, y) - used for ground/lying poses
                return h
            f, sd, y = h
            return (f + sd * sgn, y + f * dy * 0.5)
        self.hn, self.hf = hand(p["hn"], ns), hand(p["hf"], -ns)
        bn = p["bend_n"] if p["bend_n"] is not None else self._ebend(self.sh_n, self.hn)
        bf = p["bend_f"] if p["bend_f"] is not None else self._ebend(self.sh_f, self.hf)
        self.en = ik(self.sh_n, self.hn, 6.6, 6.4, bn)
        self.ef = ik(self.sh_f, self.hf, 6.6, 6.4, bf)

    @staticmethod
    def _kbend(h, f):
        # knees bend forward (+x screen): pick the IK side whose knee lies at larger x
        k1 = ik(h, f, 9.6, 9.0, 1); k2 = ik(h, f, 9.6, 9.0, -1)
        return 1 if k1[0] >= k2[0] else -1

    @staticmethod
    def _ebend(s, hnd):
        # elbows bend backward/outward: the side with smaller x (behind), or lower when reaching up
        k1 = ik(s, hnd, 6.6, 6.4, 1); k2 = ik(s, hnd, 6.6, 6.4, -1)
        return 1 if k1[0] <= k2[0] else -1


# --------------------------------------------------------------------------
# parts
# --------------------------------------------------------------------------
def leg(P, hip, knee, foot, view, boot="O", wrap=True, trouser="P", far=False):
    if far:
        boot, trouser, wch, wl = "o", "p", "V", "v"
    else:
        wch, wl = "W", "w"
    P.limb(hip, knee, trouser, 4)
    P.limb(knee, (foot[0], foot[1] - 1.5), trouser, 3)
    if wrap:                                       # onuchi: wrapped lower shin only
        a0 = (knee[0] + (foot[0] - knee[0]) * 0.3, knee[1] + (foot[1] - 1.5 - knee[1]) * 0.3)
        P.limb(a0, (foot[0], foot[1] - 1.5), wch, 3)
        for t in (0.5, 0.8):
            a = (knee[0] + (foot[0] - knee[0]) * t, knee[1] + (foot[1] - 1.5 - knee[1]) * t)
            P.line((a[0] - 1.2, a[1] + 0.6), (a[0] + 1.2, a[1] - 0.6), wl)
    fx = 1.0
    toe = 3.2 if view == "se" else 2.4
    toe_x = 1.0 if view == "se" else -1.0
    P.poly([(foot[0] - 1.6, foot[1] - 2.2), (foot[0] + 0.8, foot[1] - 2.2), (foot[0] + 0.8 + toe * toe_x, foot[1] - 0.8),
            (foot[0] + 0.8 + toe * toe_x, foot[1]), (foot[0] - 1.6, foot[1])], boot)


def arm(P, sh, el, hand, sleeve="A", cuff="L", w=3, fist=True):
    P.limb(sh, el, sleeve, w)
    P.limb(el, hand, cuff, max(2, w - 1))
    if fist:
        P.ellipse(hand, 1.4, 1.4, "S")


def axe(P, grip, ang, edge=1, scale=1.0):
    """Bearded axe (секира): haft 16 px (3 behind the grip), iron head with a
    long beard; edge=+1 puts the blade on the left normal of the haft."""
    L = 13.0 * scale
    u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    v = (-u[1] * edge, u[0] * edge)
    A = lambda a, b: (grip[0] + u[0] * a + v[0] * b, grip[1] + u[1] * a + v[1] * b)
    P.line(A(-3, 0), A(L + 1, 0), "X", 2)
    head = [A(L - 1.6, 0.4), A(L + 1.6, 0.4), A(L + 3.0, 3.2), A(L + 2.2, 7.6), A(L - 2.0, 8.2), A(L - 3.2, 6.6), A(L - 1.2, 2.6)]
    P.poly(head, "H")
    P.line(A(L + 2.8, 3.4), A(L + 1.6, 7.6), "I")             # bright cutting edge
    P.line(A(L - 1.6, 1.2), A(L - 1.2, 5.0), "h")
    P.px(A(L + 1.0, -0.8), "x")                                # haft end above the head
    return A(L + 2.0, 5.5)


def torch(P, grip, ang, phase, lit=True, flame_scale=1.0, lean=0.0):
    """Torch: 12-px stick (4 below the grip), 3x4 pitch wrap, 6-phase flame.
    Returns the local point of the flame root."""
    u = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    A = lambda a: (grip[0] + u[0] * a, grip[1] + u[1] * a)
    P.line(A(-4), A(7), "x", 2)
    top = A(9)
    n = (-u[1], u[0])
    P.poly([(A(6.5)[0] + n[0] * 1.8, A(6.5)[1] + n[1] * 1.8), (A(10)[0] + n[0] * 1.8, A(10)[1] + n[1] * 1.8),
            (A(10)[0] - n[0] * 1.8, A(10)[1] - n[1] * 1.8), (A(6.5)[0] - n[0] * 1.8, A(6.5)[1] - n[1] * 1.8)], "R")
    root = A(10.2)
    if lit:
        P.px(A(8), "q")
        flame(P, (root[0], root[1] + 0.5), phase, h=9, w=5.2, lean=lean, scale=flame_scale)
    return root

"""H21 (GDD v1.14 §12.1.8, P0): Ратибор — блок щитом. 5 drawn views (S, SE, E, NE, N) + 3 mirrored (SW, W, NW),
64×64, pivot (32, 56), height 44 (spire to soles, outline included), palette_v2, alpha 0/255.
Look = the canon hero (teaser concept v2 / sprites_rus MAT): conical helm with bronze rim and nasal, mail hauberk,
red cloak, sea-blue trousers, birch onuchi, brown boots, sword in the RIGHT hand, small round shield on the LEFT arm —
the existing shield pattern (sprites_rus._shield: 8 alternating sectors red/birch, bronze rim and umbo) is reused
as is (critic's symbol review pending, not redesigned).
Animations: raise 2, hold 2 (loop), walk 6 (loop, ×0.5 speed), hit 3 (blocked), break 4 = 17 frames per view.
A small 2.5D rig: body parts are 3D points (f forward, r character's right, z up) projected per view angle phi
(S 0°, SE 45°, E 90°, NE 135°, N 180°) and painted back to front."""
import os
import sys
import math
import json
import numpy as np
import rig                                  # noqa: F401  (palette v2)
import pixelkit as pk
sys.path.insert(0, "/workspace/game/art/ui/src")
from sprites_rus import MAT
import export as X

OUT = os.path.join(X.ROOT, "hero")
GX, GY = 31, 54
PIVOT = (32, 56)
TILT = 0.4
VIEWS = [("s", 0), ("se", 45), ("e", 90), ("ne", 135), ("n", 180)]
MIRROR = {"se": "sw", "e": "w", "ne": "nw"}
PROTO_DIR = {"s": [0], "se": [7, 1], "e": [6, 2], "ne": [5, 3], "n": [4]}
from pixelkit import C as C_
LEG = dict(MAT)
LEG.update({"L": ("wood", 2, True, False), "l": ("wood", 3, False, False)})   # shield back boards


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


class View:
    def __init__(self, phi, pose):
        self.cs, self.sn = math.cos(math.radians(phi)), math.sin(math.radians(phi))
        self.p = pose

    def T(self, f, r, z, body=True):
        """pose transform: lean of the upper body about the hips, recoil shift, bob."""
        p = self.p
        if body and z > 11:
            dz = z - 11
            a = math.radians(p.get("lean", 0.0))
            f, z = f + dz * math.sin(a), 11 + dz * math.cos(a)
            z += p.get("bob", 0.0)
        return f + p.get("bodyf", 0.0), r, z

    def P(self, f, r, z, body=True):
        f, r, z = self.T(f, r, z, body)
        x = f * self.sn - r * self.cs
        d = f * self.cs + r * self.sn
        return GX + x, GY - z + TILT * d, d

    def d(self, f, r, z=0, body=True):
        return self.P(f, r, z, body)[2]


def shield_pixels(V, C, yaw, tilt, rx=6.5, ry=7.5):
    """forward-map the shield disc; returns {(x, y): ch}. Front: sprites_rus._shield pattern; back: boards + rim."""
    a, t = math.radians(yaw), math.radians(tilt)
    n = (math.cos(a), -math.sin(a))
    u = (math.sin(a), math.cos(a))
    v = (-math.sin(t) * n[0], -math.sin(t) * n[1], math.cos(t))
    front = (n[0] * V.cs + n[1] * V.sn) >= 0
    out = {}
    for A in np.arange(-rx, rx + 0.01, 0.2):
        for B in np.arange(-ry, ry + 0.01, 0.2):
            dd = (A / rx) ** 2 + (B / ry) ** 2
            if dd > 1.0:
                continue
            f = C[0] + A * u[0] + B * v[0]
            r = C[1] + A * u[1] + B * v[1]
            z = C[2] + B * v[2]
            x, y, _ = V.P(f, r, z)
            if front:
                ang = math.atan2(-B / ry, A / rx)
                ch = "D" if (int((ang + math.pi) / (math.pi / 4)) % 2) == 0 else "d"
                if dd > 0.72 or dd <= 0.09:
                    ch = "Z"
            else:
                ch = "Z" if dd > 0.72 else ("l" if int((A + rx) / 2.2) % 2 else "L")
            out[(int(round(x)), int(round(y)))] = ch
    # edge-on guard: keep at least a 2-px bronze rim strip
    xs = [k[0] for k in out]
    if xs and max(xs) - min(xs) < 2:
        for (x, y) in list(out):
            out[(x + 1, y)] = "Z"
    return out


def draw(view, phi, p):
    V = View(phi, p)
    m = pk.MatCanvas(62, 62)
    items = []                                  # (depth, fn)

    def add(dep, fn):
        items.append((dep, len(items), fn))

    def L3(a, b, ch, w=1, body=True):
        pa, pb = V.P(*a, body=body), V.P(*b, body=body)
        add((pa[2] + pb[2]) / 2, lambda: m.line(pa[0], pa[1], pb[0], pb[1], ch, w))

    # ---- legs
    for side, (ff, lift) in (("L", p["feetL"]), ("R", p["feetR"])):
        r = -2.6 if side == "L" else 2.6
        hip = (0.0, r, 11.0)
        foot = (ff, r, lift)
        knee = ((ff * 0.55) + 0.8, r, 5.8 + lift * 0.6)
        def leg(hip=hip, foot=foot, knee=knee):
            a, b, c = V.P(*hip), V.P(*knee, body=False), V.P(foot[0], foot[1], foot[2] + 2, body=False)
            m.line(a[0], a[1], b[0], b[1], "P", 3)
            m.line(b[0], b[1], c[0], c[1], "P", 3)
            w0 = (b[0] * 0.5 + c[0] * 0.5, b[1] * 0.5 + c[1] * 0.5)
            m.line(w0[0], w0[1], c[0], c[1], "W", 3)
            m.px(int(round((w0[0] + c[0]) / 2)), int(round((w0[1] + c[1]) / 2)), "w")
            h, t = V.P(foot[0] - 1.2, foot[1], foot[2] + 1.0, body=False), V.P(foot[0] + 2.2, foot[1], foot[2] + 0.8, body=False)
            m.line(h[0], h[1], t[0], t[1], "O", 3)
        add(V.d(ff, r, 4, body=False) - 0.3, leg)
    # ---- cloak (red), hanging behind the shoulders; inside face darker
    sway = p.get("cloak", 0.0)
    cl = [(-3.4, -6.0, 27.5), (-3.4, 6.0, 27.5), (-4.4 - sway, 8.0, 4.0), (-4.4 - sway, -8.0, 4.0)]
    outer = (-V.cs) >= -0.05
    pts = [V.P(*q)[:2] for q in cl]
    add(V.d(-3.8, 0, 15) - 0.5, lambda pts=pts: m.poly(pts, "C" if outer else "c"))
    # ---- hauberk (mail), hem band, belt
    def ring(z, w, dep=3.6):
        return [V.P(f, r, z)[:2] for f in (-dep, dep) for r in (-w, w)]
    torso = hull(ring(28, 6.0) + ring(25, 6.2) + ring(17, 5.4) + ring(11, 6.4, 3.9))
    add(V.d(0, 0, 17), lambda: m.poly(torso, "M"))
    hem = hull(ring(11, 6.4, 3.9) + ring(12.8, 6.2, 3.8))
    add(V.d(0, 0, 17) + 0.01, lambda: m.poly(hem, "m"))
    belt = hull(ring(16.0, 5.6, 3.65) + ring(17.6, 5.6, 3.65))
    add(V.d(0, 0, 17) + 0.02, lambda: m.poly(belt, "L"))
    if V.cs > 0.2:
        bx, by, bd = V.P(3.7, 0.6, 16.8)
        add(bd + 0.03, lambda: m.rect(int(round(bx)) - 1, int(round(by)), 2, 2, "Z"))
    # ---- sword arm (right) and the lowered sword, pointing down-back
    sh, el, hd = (0.0, 6.2, 27.0), (-1.4, 7.4, 21.0), p.get("swordhand", (-2.4, 7.2, 16.0))
    L3(sh, el, "M", 3); L3(el, hd, "M", 2)
    hx, hy, hdd = V.P(*hd)
    add(hdd + 0.05, lambda: m.ellipse(hx, hy, 1.3, 1.3, "S"))
    bd_ = p.get("blade", (-0.45, 0.12, -0.89))
    n_ = math.sqrt(sum(c * c for c in bd_))
    bdv = tuple(c / n_ for c in bd_)
    b0 = tuple(hd[i] + bdv[i] * 2.0 for i in range(3))
    b1 = tuple(hd[i] + bdv[i] * 16.0 for i in range(3))
    L3(b0, b1, "T", 2)
    g0 = (hd[0] + bdv[0] * 1.2, hd[1] - 2.4, hd[2] + bdv[2] * 1.2)
    g1 = (hd[0] + bdv[0] * 1.2, hd[1] + 2.4, hd[2] + bdv[2] * 1.2)
    L3(g0, g1, "Z", 1)
    pm = V.P(hd[0] - bdv[0] * 2.0, hd[1], hd[2] - bdv[2] * 2.0)
    add(pm[2], lambda: m.px(int(round(pm[0])), int(round(pm[1])), "Z"))
    # ---- head: coif, face, beard, eyes, helm with bronze rim, nasal, spire
    H = (0.6, 0.0, 31.6)
    co = V.P(0.3, 0.0, 29.6)
    add(V.d(*H) - 0.2, lambda: m.ellipse(co[0], co[1], 3.4, 2.2, "M"))
    hp = V.P(*H)
    add(V.d(*H), lambda: m.ellipse(hp[0], hp[1], 2.9, 2.9, "M"))
    if V.cs > -0.25:
        fc = V.P(H[0] + 1.4, 0.0, H[2] - 0.3)
        add(V.d(*H) + 0.1, lambda: m.ellipse(fc[0], fc[1], 2.4 if abs(V.sn) < 0.8 else 1.8, 2.4, "S"))
        bq = [V.P(H[0] + 2.0, -1.9, H[2] - 2.0)[:2], V.P(H[0] + 2.0, 1.9, H[2] - 2.0)[:2],
              V.P(H[0] + 2.4, 1.2, H[2] - 3.6)[:2], V.P(H[0] + 2.6, 0.0, H[2] - 4.4)[:2], V.P(H[0] + 2.4, -1.2, H[2] - 3.6)[:2]]
        add(V.d(*H) + 0.2, lambda bq=bq: m.poly(hull(bq) if len(set(bq)) > 2 else bq, "B"))
        for er in (-1.25, 1.25):
            ex, ey, ed = V.P(H[0] + 2.7, er, H[2] + 0.3)
            if ed - V.d(*H) > 0.9:
                add(V.d(*H) + 0.3, lambda ex=ex, ey=ey: m.px(int(round(ex)), int(round(ey)), "k"))
    base = [V.P(H[0] - 0.1 + 3.5 * math.cos(k * math.pi / 8), 3.5 * math.sin(k * math.pi / 8), H[2] + 2.0)[:2] for k in range(16)]
    apex = V.P(H[0] - 0.1, 0.0, 39.8)[:2]
    helm = hull(base + [apex])
    add(V.d(*H) + 0.4, lambda: m.poly(helm, "H"))
    rim = hull([V.P(H[0] - 0.1 + 3.7 * math.cos(k * math.pi / 8), 3.7 * math.sin(k * math.pi / 8), zz)[:2] for k in range(16) for zz in (H[2] + 1.6, H[2] + 2.6)])
    add(V.d(*H) + 0.41, lambda: m.poly(rim, "Z"))
    sp = V.P(H[0] - 0.1, 0.0, 40.8)
    add(V.d(*H) + 0.42, lambda: m.px(int(round(sp[0])), int(round(sp[1])), "Z"))
    if V.cs > 0.3:
        n0, n1 = V.P(H[0] + 3.4, 0.0, H[2] + 1.6), V.P(H[0] + 3.3, 0.0, H[2] - 0.8)
        add(V.d(*H) + 0.43, lambda: m.line(n0[0], n0[1], n1[0], n1[1], "H"))
    # ---- shield arm (left) and the shield
    C = p["shield"]
    yaw, tilt = p.get("yaw", -20.0) - 22.0 * max(0.0, V.sn) * max(0.0, 1 - abs(V.cs) * 1.2), p.get("tilt", 0.0)
    a = math.radians(yaw)
    hand = (C[0] - 1.6 * math.cos(a), C[1] + 1.6 * math.sin(a), C[2] - 0.5)
    shL = (0.0, -6.2, 27.0)
    elb = ((shL[0] + hand[0]) / 2 - 0.5, min(shL[1], hand[1]) - 1.8, (shL[2] + hand[2]) / 2 - 3.0)
    L3(shL, elb, "M", 3); L3(elb, hand, "M", 2)
    spx = shield_pixels(V, C, yaw, tilt)
    def put_shield():
        for (x, y), ch in spx.items():
            if 0 <= x < 62 and 0 <= y < 62:
                m.a[y, x] = ch
    add(V.d(*C) + 0.5, put_shield)
    for dep, _, fn in sorted(items, key=lambda t: (t[0], t[1])):
        fn()
    # v1.14 P1 (дизайнер 10.10): в видах ne/n щит закрыт корпусом — выводим край щита сбоку (сторона левой руки,
    # экранно слева): дуга 2–3 px — наружный ряд бронзовой кромки «Z» + дерево изнанки «L», блик bronze_hi сверху.
    sliver = []
    if V.cs < -0.3:
        vis = sum(1 for (x, y), ch in spx.items() if 0 <= x < 62 and 0 <= y < 62 and m.a[y, x] == ch)
        scx, scy, _ = V.P(*C)
        ry = 6.0 * max(0.55, math.cos(math.radians(tilt)))
        y0, y1 = int(round(scy - ry)), int(round(scy + ry))
        occ = [np.nonzero(m.a[y] != ".")[0] for y in range(max(0, y0), min(62, y1 + 1))]
        lx = min([o.min() for o in occ if len(o)] or [int(round(scx)) - 4])
        sx = [x for (x, y) in spx]
        if vis < 10 or (sx and min(sx) >= lx - 1):
            for y in range(max(0, y0), min(62, y1 + 1)):
                t = (y - scy) / ry
                if abs(t) > 1:
                    continue
                o = int(round(1.4 * math.sqrt(max(0.0, 1 - t * t))))          # дуга: в середине на 1 px дальше
                xo = lx - 1 - o
                for x in range(xo, lx):
                    if 0 <= x < 62 and (m.a[y, x] == "." or x == xo):
                        m.a[y, x] = "Z" if x == xo else "L"
                sliver.append((int(xo), int(y)))
    spr = pk.make_sprite(m.rows(), LEG)
    idx = pk.sprite_to_index(spr)
    if sliver:                                                                   # блик на верхней трети кромки
        top = min(y for _, y in sliver)
        for (x, y) in sliver:
            if y - top <= 2:
                idx[y + 1, x + 1] = C_["bronze_hi"]
            elif y - top <= 4:
                idx[y + 1, x + 1] = C_["bronze_lt"]
    # anchors (frame px): shield centre and the rim point toward the enemy (front-top)
    cx, cy, _ = V.P(*C)
    # точка контакта = верхне-правая точка кромки (экранно; враг справа в видах s/se/e/ne; для зеркал x → 63 − x)
    if sliver:                                   # ne/n: контакт = верх выведенной кромки
        rx_, ry_ = min(sliver, key=lambda q: q[1])
    elif spx:
        rx_, ry_ = max(spx.keys(), key=lambda q: q[0] - 0.6 * q[1])
    else:
        ff = (C[0] + 0.9 * math.cos(a), C[1] - 0.9 * math.sin(a), C[2] + 6.8)
        rx_, ry_, _ = V.P(*ff)
    return idx, dict(shield_center=[round(cx + 1, 1), round(cy + 1, 1)], shield_rim=[round(rx_ + 1, 1), round(ry_ + 1, 1)])


# ---------------------------------------------------------------- poses
HOLD = (5.2, -1.4, 24.0)


def poses():
    still = dict(feetL=(0.6, 0.0), feetR=(-0.6, 0.0))
    A = {}
    A["raise"] = [dict(still, shield=(3.0, -5.4, 18.0), yaw=38, tilt=6, swordhand=(-2.2, 7.2, 14.0)),
                  dict(still, shield=(4.4, -2.8, 22.0), yaw=-6, tilt=3)]
    A["hold"] = [dict(still, shield=HOLD), dict(still, shield=(5.0, -1.4, 23.5), bob=-0.6, cloak=0.3)]
    A["walk"] = []
    for i in range(6):
        ph = i / 6 * 2 * math.pi
        s = 2.4 * math.sin(ph)
        A["walk"].append(dict(feetL=(s, max(0.0, math.cos(ph)) * 1.2), feetR=(-s, max(0.0, -math.cos(ph)) * 1.2),
                              shield=(HOLD[0], HOLD[1], HOLD[2] - 0.6 * abs(math.sin(ph))), bob=-0.7 * abs(math.sin(ph)),
                              cloak=0.6 * abs(math.cos(ph))))
    A["hit"] = [dict(still, shield=(4.0, -1.0, 24.3), yaw=-14, tilt=14, bodyf=-0.4),
                dict(still, shield=(3.8, -1.2, 23.7), yaw=-18, tilt=8, bodyf=-1.0, lean=-4, cloak=0.6),
                dict(still, shield=(4.6, -1.4, 23.9), yaw=-20, tilt=3, bodyf=-0.6, lean=-1)]
    A["break"] = [dict(still, shield=(3.4, -6.4, 22.5), yaw=58, tilt=18, bodyf=-0.6, lean=-5, cloak=0.8),
                  dict(feetL=(0.2, 0.0), feetR=(-1.6, 0.0), shield=(1.2, -8.6, 18.5), yaw=82, tilt=24, bodyf=-1.4, lean=-9,
                       cloak=1.2, swordhand=(-2.0, 7.8, 15.0)),
                  dict(still, shield=(1.6, -7.6, 15.5), yaw=74, tilt=10, bodyf=-0.8, lean=-3, cloak=0.6),
                  dict(still, shield=(1.4, -6.8, 13.1), yaw=70, tilt=4, bodyf=-0.3)]
    return A


ANIMS = [  # name, fps, loop, events, notes
    ("raise", 13, False, {"block_active_after_last_frame": True, "raised": 1},
     "0,15 с (§4.7): щит от бедра к груди, меч опущен назад. Опускание = эти кадры в обратном порядке."),
    ("hold", 4, True, {"block_active": [0, 1]}, "цикл; кромка щита на уровне подбородка, закрывает лицо наполовину"),
    ("walk", 8, True, {"block_active": [0, 1, 2, 3, 4, 5], "footstep": [0, 3]}, "шаг со щитом (скорость × 0,5), цикл 0,75 с"),
    ("hit", 12, False, {"block_active": [0, 1, 2], "hit": 0, "sparks": 0, "recoil_px": 1},
     "принятый удар: щит дрогнул, отдача в плечо, сдвиг на 1 px назад; искры H23 — в кадре 0 у anchors.shield_rim"),
    ("break", 13, False, {"block_active": [], "break": 0, "sparks": 0, "shield_down": 3},
     "пробитие: щит отбит в сторону, герой качнулся, затем опускает щит; блок снят с кадра 0; 13 fps: 4 кадра ≈ 0,3 с = оглушение §4.7"),
]


def run():
    A = poses()
    manifest = dict(character="Ратибор (герой) — блок щитом, H21", folder="hero", frame_size=[64, 64], pivot=list(PIVOT),
                    directions=dict(drawn=["s", "se", "e", "ne", "n"], mirrored={"sw": "se", "w": "e", "nw": "ne"},
                                    prototype_dirs={"0": "s", "7": "se", "6": "e", "5": "ne", "4": "n", "1": "se + mirror",
                                                    "2": "e + mirror", "3": "ne + mirror"},
                                    rule="GDD §12.1.2 / scale.md §4.1: hero 5 drawn + 3 mirrored; mirror = flip around x = 32, pivot stays (32, 56)"),
                    animations={}, heights={}, total_frames=0)
    rows, labels = {}, []
    for name, fps, loop, ev, notes in ANIMS:
        manifest["animations"]["hero_block_" + name] = dict(frames=len(A[name]), fps=fps, loop=loop, events=ev, notes=notes,
                                                            files={v: "hero_block_%s_%s.png" % (name, v) for v, _ in VIEWS})
        for v, phi in VIEWS:
            frames, anchors = [], []
            for pose in A[name]:
                idx, an = draw(v, phi, pose)
                assert not (idx[0] >= 0).any() and not (idx[:, 0] >= 0).any() and not (idx[:, -1] >= 0).any(), (name, v)
                frames.append(idx); anchors.append(an)
            hs = [int(PIVOT[1] - np.where((f >= 0).any(1))[0].min() + 1) for f in frames]
            manifest["heights"]["%s_%s" % (name, v)] = hs
            manifest["total_frames"] += len(frames)
            X.save_sheet(frames, OUT, "hero_block_%s_%s" % (name, v), dict(
                character="Ратибор (герой)", animation="block_" + name, direction=v, mirror_for=MIRROR.get(v),
                mirror_rule="flip horizontally around x = 32.0; pivot stays (32, 56)" if v in MIRROR else None,
                prototype_dirs=PROTO_DIR[v], pivot=list(PIVOT), fps=fps, loop=loop, events=ev,
                visible_height_px=hs, height_rule="pivot row (soles) to the top visible pixel, outline included",
                anchors=dict(shield_center=[a["shield_center"] for a in anchors], shield_rim=[a["shield_rim"] for a in anchors]),
                notes=notes))
            rows.setdefault(v, []).extend(frames)
    with open(os.path.join(OUT, "hero_block.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    # previews: one row per view (17 frames), GIF per animation
    X.preview([rows[v] for v, _ in VIEWS], [v.upper() for v, _ in VIEWS], os.path.join(OUT, "preview"), "hero_block_all", 8, True,
              PIVOT, shadow_w=18, title="Ратибор — блок: подъём 2 · держит 2 · шаг 6 · удар 3 · пробит 4")
    i = 0
    for name, fps, loop, ev, notes in ANIMS:
        n = len(A[name])
        X.preview([rows[v][i:i + n] for v, _ in VIEWS], [v.upper() for v, _ in VIEWS], os.path.join(OUT, "preview"),
                  "hero_block_" + name, fps, loop, PIVOT, shadow_w=18, title="block " + name)
        i += n
    return manifest["total_frames"], sorted(set(h for hs in manifest["heights"].values() for h in hs))


if __name__ == "__main__":
    print(run())

"""Капище Перуна (М1) objects: огнище (3 around the idol) and идол Перуна.
scale.md §3.3: огнище 2x2, «как крада»: кладка дров 24, пламя до 72; пламя «осквернённое»
(зелёное, nebyl) / «освящённое» (тёплое). Идол Перуна 2x2, 104 x 24, в М1 горит: пламя до 136;
после боя — дымящийся. GDD §8.4 / §12.1.3 / §12.1.5: освящение огнища 6, удержание 3 с.
Palette v2 only; functions return palette-index frames (-1 transparent)."""
import math
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
import effects_rest as R
from effects_rest import fire_field, sparks, _solid, _over, _glyph_mask, SMALL, TAU

# --------------------------------------------------------------------------
# огнище: frame 64x120, pivot (32,108) — same cell as the крада
# --------------------------------------------------------------------------
OG_W, OG_H, OG_PIV = 64, 120, (32, 108)
OG_FLAME = 52                         # above the crib top (24) -> 72 from the ground (+ licks)
OG_STONES = [(k + 0.5) / 8 * TAU for k in range(8)]
OG_GLYPH = ["plus", "x", "up", "bar", "x", "plus", "bar", "up"]
GREEN = {C["red"]: C["pine_dk"], C["red_lt"]: C["nebyl_dk"], C["ember"]: C["nebyl"], C["flame"]: C["nebyl"], C["linen"]: C["linen"]}


def _green(fl, i):
    """Warm fire_field -> Небыль green (outer nebyl_dk, body nebyl, a little linen at the core)."""
    out = fl.copy()
    b = pk.bayer(*fl.shape)
    for a, g in GREEN.items():
        out[fl == a] = g
    out[(fl == C["ember"]) & (b < 0.35)] = C["nebyl_dk"]
    return out


def _hearth_base(state, i):
    """state: desecrated | consecrated. Returns (index frame, rune masks in frame coords, stone order)."""
    cx, cy = OG_PIV[0] - 1, OG_PIV[1] - 1
    mc = pk.MatCanvas(OG_W - 2, OG_H - 2)
    pos = []

    def stones(front):
        for k, a in enumerate(OG_STONES):
            if (math.sin(a) > 0) != front:
                continue
            x, y = int(round(cx + math.cos(a) * 21)), int(round(cy + math.sin(a) * 10.5))
            mc.rect(x - 3, y - 6, 7, 8, "K"); mc.rect(x - 2, y - 7, 5, 1, "K")
            mc.rect(x - 2, y - 7, 4, 1, "D")
            mc.rect(x + 2, y - 5, 1, 7, "d")
            pos.append((k, x, y))
    stones(False)
    mc.ellipse(cx, cy, 15, 7, "a")                                           # ash bed
    b = pk.bayer(OG_H - 2, OG_W - 2)
    bed = mc.a == "a"
    mc.a[bed & (b < 0.2 + 0.05 * math.sin(R._ph(i)))] = "q"
    a_ = 0.38
    P0 = lambda du, dv, z: (cx + (du - dv) * 16, cy + (du + dv) * 8 - z)
    mc.poly([P0(-a_, a_, 0), P0(a_, a_, 0), P0(a_, -a_, 0), P0(a_, -a_, 24), P0(-a_, -a_, 24), P0(-a_, a_, 24)], "x")
    vol = mc.a == "x"
    mc.a[vol & (b < 0.24 + 0.05 * math.sin(R._ph(i) + 1.0))] = "q"
    mc.poly([P0(-a_, a_, 24), P0(a_, a_, 24), P0(a_, -a_, 24), P0(-a_, -a_, 24)], "E")
    for k in range(6):
        z = 4 * k + 1
        logs = (((-a_ - 0.2, -a_), (a_ + 0.2, -a_)), ((-a_ - 0.2, a_), (a_ + 0.2, a_))) if k % 2 == 0 else \
               (((-a_, -a_ - 0.2), (-a_, a_ + 0.2)), ((a_, -a_ - 0.2), (a_, a_ + 0.2)))
        for (p, q) in logs:
            (x0, y0), (x1, y1) = P0(*p, z), P0(*q, z)
            for dd, ch in ((0, "x"), (1, "X"), (2, "X")):
                mc.line(int(round(x0)), int(round(y0)) - dd, int(round(x1)), int(round(y1)) - dd, ch)
            for (ex, ey) in ((x0, y0), (x1, y1)):
                mc.rect(int(round(ex)) - 1, int(round(ey)) - 2, 2, 2, "J")
    stones(True)
    fr = _solid(mc)
    masks = []
    order = []
    for (k, x, y) in pos:
        masks.append(_glyph_mask(fr.shape, OG_GLYPH[k], x, y - 4, SMALL))   # MatCanvas -> frame +1
        order.append(k)
    if state == "desecrated":                     # soot on the stones, the crib glows green, ash bed green embers
        sb = pk.bayer(OG_H, OG_W)
        stone = np.isin(fr, [C["slate"], C["slate_lt"], C["mist"]])
        fr[stone & (sb < 0.45)] = C["slate_dk"]
        fr[fr == C["ember"]] = C["nebyl_dk"]
        fr[(fr == C["flame"])] = C["nebyl"]
        fr[(fr == C["red"]) | (fr == C["red_lt"])] = C["pine_dk"]
    return fr, masks, order


def _runes(fr, masks, order, mode, i, lit_upto=None):
    """mode: desecrated (dead green glints) | consecrated (bronze smoulder) | flash (bronze_hi)."""
    ph = R._ph(i)
    for j, (m, k) in enumerate(zip(masks, order)):
        if lit_upto is not None:                               # progress overlay: clockwise from the front stone
            if (k - 2) % 8 < lit_upto:
                fr[m] = C["bronze_hi"]
            continue
        if mode == "desecrated":
            fr[m] = C["pine_dk"]
            if (k + i) % 4 == 0:
                fr[m] = C["nebyl_dk"]
        elif mode == "consecrated":
            w = math.sin(ph + k * 1.7)
            fr[m] = C["bronze"] if w > -0.3 else C["bronze_dk"]
            if w > 0.8:
                fr[m] = C["bronze_lt"]
        else:
            fr[m] = C["bronze_hi"]
    return fr


def _flame(fr, i, kind, scale=1.0, n=6):
    top_y = OG_PIV[1] - 24
    if scale <= 0.02:
        return fr
    fl = fire_field(fr.shape, OG_PIV[0] - 0.5, top_y + 2, 11.5 * (0.6 + 0.4 * scale), OG_FLAME * scale, i, bright=0.0, n=n,
                    seed=2.0 if kind == "green" else 0.0)
    fl[(fr >= 0) & (np.arange(OG_H)[:, None] > top_y + 1)] = -1
    if kind == "green":
        fl = _green(fl, i)
    return _over(fr, fl)


def ognishche(state):
    frames = []
    for i in range(6):
        if state == "desecrated":
            fr, masks, order = _hearth_base("desecrated", i)
            _runes(fr, masks, order, "desecrated", i)
            _flame(fr, i, "green")
            em = [(30, OG_PIV[1] - 24 - 34, 30, 1.5, 0.1), (36, OG_PIV[1] - 24 - 28, 26, 1.0, 0.55), (27, OG_PIV[1] - 24 - 20, 22, 1.2, 0.8)]
            _over(fr, sparks(fr.shape, em, i, cols=("pine_dk", "nebyl_dk", "nebyl")))
        else:
            fr, masks, order = _hearth_base("consecrated", i)
            _runes(fr, masks, order, "consecrated", i)
            _flame(fr, i, "warm")
            em = [(30, OG_PIV[1] - 24 - 30, 30, 1.5, 0.0), (36, OG_PIV[1] - 24 - 24, 26, 1.0, 0.45)]
            _over(fr, sparks(fr.shape, em, i))
        frames.append(fr)
    return frames


def consecrate():
    """6-frame one-shot transition: green shrinks, flash of bronze_hi / linen, warm flame grows.
    The last frame equals consecrated frame 0 (no pop when the loop starts)."""
    frames = []
    for i in range(6):
        if i <= 1:
            fr, masks, order = _hearth_base("desecrated", i)
            _runes(fr, masks, order, "flash", i)
            _flame(fr, i, "green", scale=[0.7, 0.35][i])
        elif i == 2:
            fr, masks, order = _hearth_base("consecrated", 0)
            _runes(fr, masks, order, "flash", i)
            _flame(fr, 0, "warm", scale=0.25)
        else:
            fr, masks, order = _hearth_base("consecrated", 0 if i == 5 else i)
            _runes(fr, masks, order, "consecrated" if i == 5 else "flash", 0 if i == 5 else i)
            _flame(fr, 0 if i == 5 else i, "warm", scale=[0.55, 0.85, 1.0][i - 3])
        cx, top = OG_PIV[0], OG_PIV[1] - 24
        if 1 <= i <= 3:                                  # burst: ring of bronze_hi / linen motes flying out and up
            rng = np.random.RandomState(4)
            r = [0, 8, 16, 24][i]
            for k in range(14):
                a = k / 14 * TAU + rng.uniform(-0.2, 0.2)
                x = int(round(cx + math.cos(a) * r)); y = int(round(top - 4 + math.sin(a) * r * 0.5 - i * 4 - rng.uniform(0, 6)))
                if 0 <= x < OG_W and 0 <= y < OG_H:
                    fr[y, x] = C["linen"] if (k + i) % 3 == 0 else C["bronze_hi"]
        if i == 2:                                        # white-hot core
            yy, xx = np.mgrid[0:OG_H, 0:OG_W]
            core = ((xx - cx + 0.5) / 7.0) ** 2 + ((yy - top + 4) / 5.0) ** 2 <= 1
            fr[core] = C["flame"]
            fr[((xx - cx + 0.5) / 4.0) ** 2 + ((yy - top + 4) / 3.0) ** 2 <= 1] = C["linen"]
        frames.append(fr)
    return frames


PROGRESS_STEPS = 12
RING_RX, RING_RY = 31.0, 14.0
PR_W, PR_H, PR_PIV = 72, 124, (36, 108)        # wider / taller than the hearth cell so the ground ring fits
PR_PAD = (PR_PIV[0] - OG_PIV[0], PR_H - OG_H - (PR_PIV[1] - OG_PIV[1]))   # (left/right, bottom) padding


def progress():
    """12-frame overlay indexed by hold progress (frame = min(11, floor(p * 12))), drawn over the desecrated
    hearth: a ground ring of bronze fills clockwise from the front, the stone резы light one by one,
    a warm core grows at the flame root and warm motes rise."""
    base, masks, order = _hearth_base("desecrated", 0)
    padx, padb = PR_PAD
    masks = [np.pad(m, ((0, padb), (padx, padx))) for m in masks]
    frames = []
    H, Wd = PR_H, PR_W
    cx, cy = PR_PIV[0] - 0.5, PR_PIV[1]
    yy, xx = np.mgrid[0:H, 0:Wd]
    for s in range(PROGRESS_STEPS):
        p = (s + 1) / PROGRESS_STEPS
        fr = np.full((H, Wd), -1, np.int16)
        # ring track + fill
        n = 96
        for k in range(n):
            t = k / n
            a = math.pi / 2 - t * TAU                  # start at the front point, go clockwise on screen
            x = int(round(cx + math.cos(a) * RING_RX)); y = int(round(cy + math.sin(a) * RING_RY))
            if not (0 <= x < Wd and 0 <= y < H):
                continue
            if t <= p:
                fr[y, x] = C["bronze_hi"] if k % 3 else C["bronze_lt"]
                if y + 1 < H and k % 2 == 0:
                    fr[y + 1, x] = C["bronze"]
            elif k % 4 == 0:
                fr[y, x] = C["slate_dk"]
        # head of the fill: a bright spark
        a = math.pi / 2 - p * TAU
        hx, hy = int(round(cx + math.cos(a) * RING_RX)), int(round(cy + math.sin(a) * RING_RY))
        for (dx, dy) in ((0, 0), (1, 0), (-1, 0), (0, -1), (0, 1)):
            if 0 <= hx + dx < Wd and 0 <= hy + dy < H:
                fr[hy + dy, hx + dx] = C["linen"] if (dx, dy) == (0, 0) else C["flame"]
        # резы light in order
        _runes(fr, masks, order, None, 0, lit_upto=int(p * 8 + 1e-6))
        # warm core at the flame root (fights the green)
        top = PR_PIV[1] - 24
        r = 2.0 + 6.0 * p
        core = ((xx - cx) / r) ** 2 + ((yy - top + 1) / (r * 0.55)) ** 2 <= 1
        fr[core] = C["ember"]
        fr[((xx - cx) / (r * 0.6)) ** 2 + ((yy - top + 1) / (r * 0.35)) ** 2 <= 1] = C["flame"]
        # rising warm motes
        rng = np.random.RandomState(9)
        for k in range(int(3 + 10 * p)):
            mx = int(round(cx + rng.uniform(-10, 10))); my = int(round(top - rng.uniform(4, 30 + 20 * p)))
            if 0 <= my < H:
                fr[my, mx] = C["bronze_hi"] if k % 3 else C["flame"]
        frames.append(fr)
    return frames


# --------------------------------------------------------------------------
# идол Перуна: frame 80x160, pivot (40,148). 104 x 24; burning flame to 136; extinguish 8; smoking 6
# --------------------------------------------------------------------------
ID_W, ID_H, ID_PIV = 80, 160, (40, 148)
ID_LEG = rig.legend(
    K=("stone", 3, True, False), k=("ink", 0, False, False), a=("stone", 1, False, False), D=("stone", 4, True, False), d=("stone", 2, False, False),
    X=("wood", 3, True, False, "grain"), x=("wood", 2, False, False), J=("wood", 4, False, False), c=("wood", 1, False, False),
    O=("ink", 0, False, False),                                                 # charred black
    H=("iron", 5, True, False), h=("iron", 4, False, False),                    # silver head
    Z=("bronze", 4, True, False), z=("bronze", 3, False, False),                # gold moustache / thunder wheel
    E=("fire", 3, False, True), e=("fire", 4, False, True), q=("fire", 2, False, True), Q=("fire", 1, False, True), r=("fire", 0, False, True),
)
THUNDER = ["..#.#..", ".#.#.#.", "#..#..#", ".#####.", "#..#..#", ".#.#.#.", "..#.#.."]


def _idol_body(char_level):
    """char_level 0 = fresh wood, 1 = burning (upper half charred, ember cracks), 2 = burnt out."""
    P = rig.Painter.__new__(rig.Painter)
    mc = pk.MatCanvas(ID_W - 2, ID_H - 2)
    cx, gy = ID_PIV[0] - 1, ID_PIV[1] - 1
    # stone plinth (2x2 footprint, low)
    mc.poly([(cx - 22, gy), (cx, gy - 11), (cx + 22, gy), (cx, gy + 11)], "d")
    mc.poly([(cx - 22, gy - 3), (cx, gy - 14), (cx + 22, gy - 3), (cx, gy + 8)], "K")
    mc.poly([(cx - 22, gy - 3), (cx, gy + 8), (cx, gy + 11), (cx - 22, gy)], "a")
    mc.poly([(cx + 22, gy - 3), (cx, gy + 8), (cx, gy + 11), (cx + 22, gy)], "d")
    # pillar: 24 wide, top of the helm at 104 (incl. outline)
    top = gy - 102
    base = gy - 4
    mc.rect(cx - 12, top + 22, 24, base - top - 22, "X")
    mc.rect(cx + 5, top + 22, 7, base - top - 22, "x")                             # shaded side
    for yy in (base - 6, top + 52, top + 74):                                       # carved bands
        mc.rect(cx - 12, yy, 24, 2, "c")
    # head: silver, helm-cap (spire), face with gold moustache
    mc.ellipse(cx, top + 15, 10, 9, "H")
    mc.poly([(cx - 10, top + 12), (cx, top + 2), (cx + 10, top + 12)], "H")
    mc.rect(cx - 1, top, 2, 3, "Z")                                                   # spire
    mc.rect(cx - 11, top + 11, 22, 2, "Z")                                            # brow band
    mc.rect(cx + 4, top + 6, 6, 16, "h")
    mc.rect(cx - 5, top + 14, 3, 2, "k"); mc.rect(cx + 2, top + 14, 3, 2, "k")        # eyes
    mc.rect(cx - 1, top + 15, 2, 4, "h")                                              # nose
    mc.poly([(cx - 9, top + 22), (cx - 1, top + 19), (cx + 1, top + 19), (cx + 9, top + 22), (cx + 8, top + 24), (cx, top + 21), (cx - 8, top + 24)], "Z")   # gold moustache (lightning)
    mc.rect(cx - 12, top + 24, 24, 3, "c")                                            # neck groove
    # thunder wheel on the chest + arms carved along the sides, hands on the belt
    for r_, row in enumerate(THUNDER):
        for c_, ch in enumerate(row):
            if ch == "#":
                mc.px(cx - 3 + c_, top + 33 + r_, "Z")
    mc.rect(cx - 12, top + 28, 3, 24, "c"); mc.rect(cx + 9, top + 28, 3, 24, "c")
    mc.rect(cx - 9, top + 50, 18, 2, "Z")                                             # belt
    mc.line(cx - 10, top + 46, cx - 5, top + 50, "c"); mc.line(cx + 10, top + 46, cx + 5, top + 50, "c")
    # the crack («Идол треснул сам»)
    pts = [(cx + 1, top + 27), (cx - 1, top + 40), (cx + 2, top + 55), (cx, top + 70), (cx + 2, top + 84)]
    for (a, b), (c2, d2) in zip(pts, pts[1:]):
        mc.line(a, b, c2, d2, "k")
    if char_level >= 1:
        yy, xx = np.mgrid[0:ID_H - 2, 0:ID_W - 2]
        bb = pk.bayer(ID_H - 2, ID_W - 2)
        wood = np.isin(mc.a, ["X", "x", "c"])
        lim = top + (64 if char_level == 1 else 96)
        charred = wood & (yy < lim) & (bb < np.clip((lim - yy) / 34.0, 0, 1) * 0.75)
        mc.a[charred] = "O"
        mc.a[wood & (yy < lim - 20) & ~charred & (bb < 0.6)] = "c"
        if char_level == 2:
            mc.a[np.isin(mc.a, ["H"])] = "h"                                          # tarnished silver
            mc.a[np.isin(mc.a, ["Z"])] = "z"
    return mc, top


def _idol_frame(char_level, i, embers, n=6):
    mc, top = _idol_body(char_level)
    cx, gy = ID_PIV[0] - 1, ID_PIV[1] - 1
    if embers > 0:                                        # ember cracks / spots on the charred wood
        rng = np.random.RandomState(21)
        for k in range(int(26 * embers)):
            x = int(cx + rng.uniform(-11, 11)); y = int(top + rng.uniform(26, 92))
            if mc.a[y, x] in ("O", "c") and (k + i) % 3 != 0:
                mc.a[y, x] = "q" if (k + i) % 4 else "E"
        pts = [(cx + 1, top + 27), (cx - 1, top + 40), (cx + 2, top + 55), (cx, top + 70)]
        for (a, b), (c2, d2) in zip(pts, pts[1:]):
            mc.line(a, b, c2, d2, "q" if (embers >= 0.5 or i % 2) else "c")
    spr = pk.make_sprite(mc.rows(), ID_LEG)
    ch = np.full(spr["mask"].shape, ".", dtype="<U1"); ch[1:-1, 1:-1] = mc.a
    fire = np.isin(ch, list(rig.FIRE_CH)); solid = (ch != ".") & ~fire
    outl = spr["mask"] & (ch == ".")
    nb = lambda m: (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1))
    f_only = outl & nb(fire) & ~nb(solid)
    spr["ramp"][f_only] = pk.RAMP_ID["fire"]; spr["lvl"][f_only] = 0
    return pk.sprite_to_index(spr), top + 1


ID_FLAME_TOP = 136


def _idol_fire(fr, i, scale, top, n=6):
    """Blaze BEHIND the carved pillar (rises around and above it to 136 at scale 1), plus tongues licking
    up the charred sides in front. The idol's silhouette, face and gold moustache stay readable."""
    if scale <= 0.03:
        return fr
    body = fr >= 0
    base_y = top + 70
    height = (base_y - (ID_PIV[1] - ID_FLAME_TOP)) * 0.86 * scale
    fl = fire_field(fr.shape, ID_PIV[0] - 0.5, base_y, 30 * (0.5 + 0.5 * scale), height, i, bright=0.2, n=n, seed=0.7)
    fl[body] = -1                                            # behind the pillar
    _over(fr, fl)
    crown_base = top + 8                                     # the crown of the head burns: tall column to 136
    crown = fire_field(fr.shape, ID_PIV[0] - 0.5, crown_base, 11 * (0.5 + 0.5 * scale),
                       (crown_base - (ID_PIV[1] - ID_FLAME_TOP)) * 0.88 * scale, i, bright=0.4, n=n, seed=1.9)
    crown[body & (np.arange(ID_H)[:, None] > top + 3)] = -1
    _over(fr, crown)
    yy, xx = np.mgrid[0:ID_H, 0:ID_W]
    for (dx, by, h, s, w) in ((-11, top + 88, 26, 1.3, 4.5), (11, top + 80, 30, 3.1, 4.5), (-10, top + 58, 20, 4.4, 3.5),
                              (10, top + 50, 16, 5.2, 3.0), (2, top + 74, 14, 2.2, 3.0)):
        side = fire_field(fr.shape, ID_PIV[0] + dx, by, w, h * scale, i, n=n, seed=s)
        _over(fr, side)
    return fr


def _smoke(fr, i, amount, top, n=6):
    """Loopable smoke from the charred top: puffs rise ~50 px and drift right (dithered slate_dk / slate / mist)."""
    if amount <= 0:
        return fr
    H, Wd = fr.shape
    yy, xx = np.mgrid[0:H, 0:Wd]
    b = pk.bayer(H, Wd)
    for j in range(5):
        t = ((i / n) + j / 5.0) % 1.0
        cy = top + 2 - t * 46
        cx = ID_PIV[0] + 2.5 * math.sin(TAU * (t + j * 0.3)) + t * 9
        r = (3.5 + 6.5 * t) * (0.6 + 0.4 * amount)
        a = (1.0 - 0.8 * t) * amount
        blob = ((xx - cx) / max(r, 0.5)) ** 2 + ((yy - cy) / max(r * 0.75, 0.5)) ** 2 <= 1
        free = fr < 0
        fr[blob & free & (b < 0.9 * a + 0.1)] = C["slate_dk"]
        fr[blob & free & (b < 0.5 * a)] = C["slate"]
        fr[blob & free & (b < 0.12 * a) & (yy < cy)] = C["mist"]
    return fr


def idol(state):
    frames = []
    if state == "burning":
        for i in range(6):
            fr, top = _idol_frame(1, i, 1.0)
            _idol_fire(fr, i, 1.0, top)
            rng = np.random.RandomState(13)
            em = [(ID_PIV[0] + rng.uniform(-12, 12), ID_PIV[1] - 110 - rng.uniform(0, 14), rng.uniform(20, 30), rng.uniform(1, 2.5), k / 8.0)
                  for k in range(8)]
            _over(fr, sparks(fr.shape, em, i))
            frames.append(fr)
    elif state == "extinguish":                           # 8 frames, one-shot: flames die, smoke builds
        for i in range(8):
            sc = max(0.0, 1.0 - i / 5.0)
            fr, top = _idol_frame(1 if i < 4 else 2, i % 6, max(0.35, 1.0 - i * 0.1))
            _idol_fire(fr, i % 6, sc, top)
            _smoke(fr, i % 6, min(1.0, i / 5.0), top)
            frames.append(fr)
    else:                                                  # smoking: 6-frame loop
        for i in range(6):
            fr, top = _idol_frame(2, i, 0.35)
            _smoke(fr, i, 1.0, top)
            frames.append(fr)
    return frames

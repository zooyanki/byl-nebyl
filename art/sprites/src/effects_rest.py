"""Rest in safe zones (GDD v1.7 §4.5, §12.1.5): костёр, Путевой камень, костёр М3,
warm sparks over the hero, and the carved ring that marks the zone border.
Palette v2 only; every function returns palette-index frames (-1 = transparent).

Sizes (scale.md §3.3, §3.4, §1):
  костёр    2x2 tiles, stone ring r 20x10 (stones 6x4), log crib 24, flame to 72 (48 above
           the wood); rest flare to 86 (ritual pillar 96 stays reserved)      frame 64x120, pivot (32,108)
  Путевой камень 1x1, 24x40, carved насечки                                         frame 32x56,  pivot (16,48)
  костёр М3 (у поваленного идола) 1x1: firewood 8, flame 20-24 (rest 30),
           ring of 8 stones with насечки («работает как Путевой камень», GDD §8.4)   frame 48x56,  pivot (24,46)
  hero sparks: overlay in the hero's own 64x64 frame                          frame 64x64,  pivot (32,56)
  zone ring: groove pieces (8 tangent directions) + 4 rune pieces, placed by
           arc length on the 2:1 ellipse (rx = R*22.63, ry = R*11.31 px).
"""
import math
import numpy as np
import rig                      # palette v2
import pixelkit as pk
from pixelkit import C

TAU = math.tau
PX_PER_TILE_X = 16 * math.sqrt(2)          # 22.63 px per tile (metre) horizontally, scale.md §1
PX_PER_TILE_Y = 8 * math.sqrt(2)           # 11.31 px vertically

LEG = rig.legend(
    K=("stone", 3, True, False), k=("ink", 0, False, False), a=("stone", 1, False, False),
    X=("wood", 2, True, False, "grain"), x=("wood", 1, False, False), J=("wood", 4, False, False),
    D=("stone", 4, True, False), d=("stone", 2, False, False),
    E=("fire", 3, False, True), e=("fire", 4, False, True), q=("fire", 2, False, True),
    Q=("fire", 1, False, True), r=("fire", 0, False, True),
)


def _solid(mc):
    """MatCanvas (frame-2) -> index array with ink outline (fire-aware like effects.py)."""
    spr = pk.make_sprite(mc.rows(), LEG)
    ch = np.full(spr["mask"].shape, ".", dtype="<U1"); ch[1:-1, 1:-1] = mc.a
    fire = np.isin(ch, list(rig.FIRE_CH))
    solid = (ch != ".") & ~fire
    outl = spr["mask"] & (ch == ".")
    nb = lambda m: (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1))
    f_only = outl & nb(fire) & ~nb(solid)
    spr["ramp"][f_only] = pk.RAMP_ID["fire"]; spr["lvl"][f_only] = 0
    return pk.sprite_to_index(spr)


def _over(dst, src):
    m = src >= 0
    dst[m] = src[m]
    return dst


def _ph(i, n=6):
    return TAU * i / n


# --------------------------------------------------------------------------
# fire field (shared by костёр and костёр): tongues, loop of 6
# --------------------------------------------------------------------------
TONGUES = ((-0.62, 0.55, 0.3), (-0.3, 0.86, 2.1), (0.0, 1.0, 4.0), (0.32, 0.8, 1.2), (0.62, 0.5, 5.0))


def fire_field(shape, cx, base_y, hw, height, i, bright=0.0, n=6, seed=0.0):
    """Returns colour-index array (-1 transparent) of a flame standing on (cx, base_y).
    hw: half width at the base, height: tallest tongue (px). bright 0..1 (rest = hotter core).
    Uses only integer multiples of the loop phase, so frame n == frame 0."""
    H, W = shape
    out = np.full(shape, -1, np.int16)
    val = np.zeros(shape)
    yy, xx = np.mgrid[0:H, 0:W]
    ph = _ph(i, n)
    for k, (ox, rel, phi) in enumerate(TONGUES):
        hk = height * rel * (0.80 + 0.20 * math.sin(ph + phi + seed))
        wk = hw * (0.40 if k in (0, 4) else 0.48) * (1.0 + 0.08 * math.sin(2 * ph + phi))
        t = (base_y - yy + 0.5) / max(hk, 1)
        ok = (t >= 0) & (t <= 1)
        t = np.clip(t, 0, 1)
        sway = 2.4 * math.sin(ph + phi * 1.3 + seed) * t ** 1.3 + 1.3 * np.sin(2 * ph + phi + t * 5) * t
        xc = cx + ox * hw * (1 - 0.35 * t) + sway * (hw / 10.0)
        half = wk * (1 - t) ** 0.72 + 0.35
        d = np.abs(xx + 0.5 - xc) / np.maximum(half, 0.01)
        v = np.where(ok & (d <= 1), (1 - d) * (1 - 0.55 * t) + 0.25 * (1 - t), 0)
        val = np.maximum(val, v)
    # detached licks above the tallest tongue (2 per frame, rising). Designer fix 08.10: a lick is a
    # spark in ember/flame with no red rim (pure red is the hero's accent, scale.md §4.4)
    lick = np.zeros(shape, bool)
    for j in range(2):
        tt = ((i / n) + j * 0.5) % 1.0
        ly = int(round(base_y - height * (0.86 + 0.28 * tt)))
        lx = int(round(cx + (j - 0.5) * hw * 0.6 + math.sin(ph + j) * 1.5))
        if 0 <= ly < H and 0 <= lx < W and val[ly, lx] < 0.04:
            lick[ly, lx] = True
            if ly + 1 < H and tt < 0.5 and val[ly + 1, lx] < 0.04:
                lick[ly + 1, lx] = True
    m = val > 0.04
    th_linen, th_flame, th_ember = 0.86 - 0.1 * bright, 0.58 - 0.1 * bright, 0.32 - 0.08 * bright
    low = yy > base_y - height * (0.28 + 0.12 * bright)             # white-hot core only near the wood
    out[m] = C["red_lt"]
    out[m & (val > th_ember)] = C["ember"]
    out[m & (val > th_flame)] = C["flame"]
    out[m & (val > th_linen) & low] = C["linen"]
    # dark-red rim (fire ramp lvl 0) for definition, as on the other fires
    nb = np.zeros(shape, bool)
    for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb |= np.roll(np.roll(m, dy, 0), dx, 1)
    rim = nb & ~m & (yy < base_y)
    out[rim] = C["red"]
    lk = lick & ~m & ~rim
    out[lk] = C["ember"]
    out[lk & np.roll(lk, -1, 0)] = C["flame"]          # 2-px lick: hot head, ember tail
    return out


def sparks(shape, emitters, i, n=6, cols=("ember", "flame", "linen")):
    """emitters: list of (x0, y0, rise_px, sway_px, offset 0..1). A spark rises rise_px per loop."""
    out = np.full(shape, -1, np.int16)
    H, W = shape
    for (x0, y0, rise, sway, off) in emitters:
        t = ((i / n) + off) % 1.0
        x = int(round(x0 + sway * math.sin(TAU * (t + off * 3))))
        y = int(round(y0 - rise * t))
        c = cols[0] if t > 0.66 else (cols[1] if t > 0.25 else cols[2])
        if 0 <= y < H and 0 <= x < W:
            out[y, x] = C[c]
            if t < 0.25 and y + 1 < H:
                out[y + 1, x] = C[cols[1]]          # short trail while hot
    return out


# --------------------------------------------------------------------------
# 1. костёр
# --------------------------------------------------------------------------
KR_W, KR_H, KR_PIV = 64, 120, (32, 108)
KR_FLAME = {"idle": 55, "rest": 68}          # above the wood (top of the crib at 24): 72 / 86 from the ground


def _krada_base(state, i):
    cx, cy = KR_PIV[0] - 1, KR_PIV[1] - 1          # material coords (make_sprite pads 1 px)
    mc = pk.MatCanvas(KR_W - 2, KR_H - 2)

    def stones(front):
        for k in range(16):
            a = (k + 0.5) / 16 * TAU
            if (math.sin(a) > 0) != front:
                continue
            x, y = int(round(cx + math.cos(a) * 20)), int(round(cy + math.sin(a) * 10))
            mc.rect(x - 3, y - 2, 6, 4, "K"); mc.rect(x - 2, y - 2, 4, 1, "D")
    stones(False)
    mc.ellipse(cx, cy, 15, 7, "a")                                            # ash bed
    b = pk.bayer(KR_H - 2, KR_W - 2)
    bed = mc.a == "a"
    glow = 0.18 if state == "idle" else 0.32
    mc.a[bed & (b < glow * (0.8 + 0.2 * math.sin(_ph(i))))] = "q"
    a_ = 0.40
    P0 = lambda du, dv, z: (cx + (du - dv) * 16, cy + (du + dv) * 8 - z)
    mc.poly([P0(-a_, a_, 0), P0(a_, a_, 0), P0(a_, -a_, 0), P0(a_, -a_, 24), P0(-a_, -a_, 24), P0(-a_, a_, 24)], "x")
    vol = mc.a == "x"
    hot = 0.22 if state == "idle" else 0.36
    flick = 0.06 * math.sin(_ph(i) + 1.0)
    mc.a[vol & (b < hot + flick)] = "q"
    mc.a[vol & (b < 0.05 + (0.07 if state == "rest" else 0))] = "E"
    mc.poly([P0(-a_, a_, 24), P0(a_, a_, 24), P0(a_, -a_, 24), P0(-a_, -a_, 24)], "E")
    ov = 0.2
    for k in range(6):
        z = 4 * k + 1
        logs = (((-a_ - ov, -a_), (a_ + ov, -a_)), ((-a_ - ov, a_), (a_ + ov, a_))) if k % 2 == 0 else \
               (((-a_, -a_ - ov), (-a_, a_ + ov)), ((a_, -a_ - ov), (a_, a_ + ov)))
        for (p, q) in logs:
            (x0, y0), (x1, y1) = P0(*p, z), P0(*q, z)
            for dd, ch in ((0, "x"), (1, "X"), (2, "X")):
                mc.line(int(round(x0)), int(round(y0)) - dd, int(round(x1)), int(round(y1)) - dd, ch)
            for (ex, ey) in ((x0, y0), (x1, y1)):
                mc.rect(int(round(ex)) - 1, int(round(ey)) - 2, 2, 2, "J")   # sawn ends
    stones(True)
    base = _solid(mc)
    if state == "rest":                    # fire-lit stone tops (warm bounce light), dithered
        bb = pk.bayer(KR_H, KR_W)
        yy, xx = np.mgrid[0:KR_H, 0:KR_W]
        near = ((xx - KR_PIV[0]) / 24.0) ** 2 + ((yy - KR_PIV[1]) / 12.0) ** 2 <= 1
        lightc = np.isin(base, [C["slate_lt"], C["mist"]]) & near & (yy < KR_PIV[1] + 4) & (bb < 0.5)
        base[lightc] = C["bronze_lt"]
    return base


def krada(state):
    frames = []
    for i in range(6):
        fr = _krada_base(state, i)
        top_y = KR_PIV[1] - 24                                      # crib top (frame coords)
        fl = fire_field(fr.shape, KR_PIV[0] - 0.5, top_y + 2, 11.5 if state == "idle" else 13.5,
                        KR_FLAME[state], i, bright=0.0 if state == "idle" else 0.8)
        fl[(fr >= 0) & (np.arange(KR_H)[:, None] > top_y + 1)] = -1   # keep the logs in front of the flame base
        _over(fr, fl)
        if state == "idle":
            em = [(30, top_y - 30, 30, 1.5, 0.0), (36, top_y - 24, 26, 1.0, 0.45)]
        else:
            rng = np.random.RandomState(7)
            em = [(KR_PIV[0] + rng.uniform(-10, 10), top_y - rng.uniform(20, 46), rng.uniform(34, 52),
                   rng.uniform(1.0, 3.0), k / 14.0) for k in range(14)]
        _over(fr, sparks(fr.shape, em, i))
        frames.append(fr)
    return frames


# --------------------------------------------------------------------------
# 2. Путевой камень (насечки smoulder bronze; rest: bronze_hi + halo + rising motes)
# --------------------------------------------------------------------------
CH_W, CH_H, CH_PIV = 32, 56, (16, 48)
GLYPHS = {   # rename_map §5 (09.10): plain notches on the waystone — no runes, no signs (was «стрела», «ромб с крестом», «древо»)
    "cut2": [".......", ".#####.", ".......", ".#####.", ".......", ".......", "......."],          # two long cuts
    "tally": [".......", "#.#.#.#", "#.#.#.#", "#.#.#.#", ".......", ".......", "......."],         # four short notches
    "cut1": [".......", "#######", ".......", ".......", ".......", ".......", "......."],          # one long cut
}
# 3x3 notches on the stones of the костёр М3 and the огнища (were «plus», «x», «up», «bar»)
SMALL = {"n1": ["...", "###", "..."], "n2": ["###", "...", "###"], "n3": ["#.#", "#.#", "#.#"], "n4": ["#.#", "#.#", "..."]}


def _stone_static():
    mc = pk.MatCanvas(CH_W - 2, CH_H - 2)
    cx, gy = CH_PIV[0] - 1, CH_PIV[1] - 1
    mc.ellipse(cx, gy + 1, 12, 3, "d")                             # set into the ground
    mc.poly([(cx - 11, gy + 1), (cx - 10, gy - 22), (cx - 9, gy - 31), (cx + 9, gy - 31), (cx + 10, gy - 22), (cx + 11, gy + 1)], "K")
    mc.ellipse(cx, gy - 31, 9, 7, "K")                             # rounded top: 40 px with the outline
    mc.poly([(cx + 6, gy - 34), (cx + 10, gy - 22), (cx + 11, gy + 1), (cx + 7, gy + 1)], "d")   # shaded side
    mc.rect(cx - 9, gy - 2, 3, 2, "a"); mc.px(cx + 4, gy - 12, "a"); mc.px(cx - 6, gy - 26, "a")   # pits
    for (x, y) in ((cx - 12, gy + 1), (cx + 12, gy + 2)):         # two pebbles at the foot
        mc.rect(x - 1, y - 1, 3, 2, "K")
    return _solid(mc)


def _glyph_mask(shape, name, x0, y0, table=GLYPHS):
    m = np.zeros(shape, bool)
    for r, row in enumerate(table[name]):
        for c, ch in enumerate(row):
            if ch == "#":
                m[y0 + r, x0 + c] = True
    return m


def _rune_paint(fr, masks, state, i, solid):
    """masks: list of bool arrays (one per glyph). idle: bronze_dk/bronze smoulder wave;
    rest: bronze_hi + linen sparks, bronze_lt/bronze halo on the stone around the cuts."""
    ph = _ph(i)
    H, W = fr.shape
    yy, xx = np.mgrid[0:H, 0:W]
    for g, m in enumerate(masks):
        if state == "idle":
            wave = np.sin(ph + g * 2.1 + yy * 0.7)
            fr[m] = C["bronze_dk"]
            fr[m & (wave > -0.2)] = C["bronze"]
            fr[m & (wave > 0.85)] = C["bronze_lt"]
        else:
            halo = np.zeros_like(m)
            for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                halo |= np.roll(np.roll(m, dy, 0), dx, 1)
            halo &= ~m & solid
            b = pk.bayer(H, W)
            fr[halo & (b < 0.55 + 0.25 * math.sin(ph + g))] = C["bronze"]
            fr[halo & (b < 0.2)] = C["bronze_lt"]
            wave = np.sin(ph + g * 2.1 + yy * 0.7)
            fr[m] = C["bronze_hi"]
            fr[m & (wave > 0.9)] = C["linen"]
    return fr


def churov(state):
    base = _stone_static()
    solid = base >= 0
    gx = CH_PIV[0] - 4
    masks = [_glyph_mask(base.shape, n, gx, y) for n, y in (("cut2", 13), ("tally", 22), ("cut1", 31))]
    frames = []
    for i in range(6):
        fr = _rune_paint(base.copy(), masks, state, i, solid)
        if state == "rest":
            rng = np.random.RandomState(3)
            em = [(CH_PIV[0] + rng.uniform(-9, 9), CH_PIV[1] - rng.uniform(26, 38), rng.uniform(10, 16),
                   rng.uniform(0.5, 1.5), k / 6.0) for k in range(6)]
            sp = sparks(fr.shape, em, i, cols=("bronze", "bronze_lt", "bronze_hi"))
            sp[solid & (sp >= 0)] = -1                                 # motes only in the air
            _over(fr, sp)
        frames.append(fr)
    return frames


# --------------------------------------------------------------------------
# 3. костёр М3: small fire in a ring of 6 rune stones
# --------------------------------------------------------------------------
CF_W, CF_H, CF_PIV = 48, 56, (24, 46)
CF_FLAME = {"idle": 21, "rest": 25}           # above the firewood top (8): 23 / 30 from the ground
CF_STONES = [k / 8 * TAU for k in range(8)]
CF_GLYPH = ["n1", "n2", "n3", "n4", "n1", "n2", "n3", "n4"]


def _campfire_base(state, i):
    cx, cy = CF_PIV[0] - 1, CF_PIV[1] - 1
    mc = pk.MatCanvas(CF_W - 2, CF_H - 2)
    pos = []

    def stones(front):
        for k, a in enumerate(CF_STONES):
            if (math.sin(a) > 0) != front:
                continue
            x, y = int(round(cx + math.cos(a) * 18)), int(round(cy + math.sin(a) * 9))
            mc.rect(x - 2, y - 3, 5, 5, "K"); mc.rect(x - 1, y - 4, 3, 1, "K"); mc.px(x - 1, y - 4, "D")
            pos.append((k, x, y))
    stones(False)
    mc.ellipse(cx, cy, 8, 4, "a")
    b = pk.bayer(CF_H - 2, CF_W - 2)
    bed = mc.a == "a"
    mc.a[bed & (b < (0.12 if state == "idle" else 0.22))] = "q"
    # «шалашик»: 5 sticks leaning together, 8 px high
    for (dx0, dy0) in ((-6, 1), (-3, 3), (3, 3), (6, 1), (0, -2)):
        mc.line(cx + dx0, cy + dy0, cx, cy - 7, "X", 1)
        mc.px(cx + dx0, cy + dy0, "J")
    mc.rect(cx - 1, cy - 2, 3, 2, "q")
    mc.px(cx, cy - 2, "E" if state == "rest" else "q")
    stones(True)
    return _solid(mc), pos


def campfire(state):
    frames = []
    for i in range(6):
        fr, pos = _campfire_base(state, i)
        solid = fr >= 0
        masks = [_glyph_mask(fr.shape, CF_GLYPH[k], x, y - 2, SMALL) for (k, x, y) in pos]   # MatCanvas -> frame +1
        _rune_paint(fr, masks, state, i, solid)
        top_y = CF_PIV[1] - 8
        fl = fire_field(fr.shape, CF_PIV[0] - 0.5, top_y + 2, 5.5 if state == "idle" else 6.5,
                        CF_FLAME[state], i, bright=0.0 if state == "idle" else 0.8, seed=1.0)
        fl[solid & (np.arange(CF_H)[:, None] > top_y + 1)] = -1
        _over(fr, fl)
        if state == "rest":
            rng = np.random.RandomState(11)
            em = [(CF_PIV[0] + rng.uniform(-5, 5), top_y - rng.uniform(12, 22), rng.uniform(14, 22),
                   rng.uniform(0.5, 2.0), k / 7.0) for k in range(7)]
            _over(fr, sparks(fr.shape, em, i))
        else:
            _over(fr, sparks(fr.shape, [(CF_PIV[0], top_y - 14, 12, 1.0, 0.2)], i))
        frames.append(fr)
    return frames


# --------------------------------------------------------------------------
# 4. warm sparks over the hero while Жизнь rises (no red: hero accent)
# --------------------------------------------------------------------------
HS_W, HS_H, HS_PIV = 64, 64, (32, 56)
WARM = ("bronze", "bronze_lt", "bronze_hi", "flame", "linen")
NO_RED = {C["red"], C["red_lt"], C["red_dk"], C["ember"]}


def hero_sparks():
    rng = np.random.RandomState(5)
    parts = []
    for k in range(16):                     # around the silhouette edges and above the helm, so they read
        side = -1 if k % 2 else 1
        x = HS_PIV[0] + side * rng.uniform(4, 15) if k % 5 else HS_PIV[0] + rng.uniform(-4, 4)
        y = HS_PIV[1] - (rng.uniform(14, 38) if k % 5 else rng.uniform(40, 44))
        parts.append((x, y, rng.uniform(12, 18), k % 4, rng.uniform(0, TAU), k % 2 == 0))
    frames = []
    for i in range(4):
        fr = np.full((HS_H, HS_W), -1, np.int16)
        for (x0, y0, rise, off, phi, star) in parts:
            age = (i + off) % 4                                  # 0..3, loops in 4 frames
            t = age / 4.0
            x = int(round(x0 + 1.2 * math.sin(phi + TAU * t)))
            y = int(round(y0 - rise * t))
            c = ("linen", "bronze_hi", "bronze_lt", "bronze")[age]
            if star and age == 1:                              # 1-px twinkle cross on some
                for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    fr[y + dy, x + dx] = C["bronze_lt"]
                fr[y, x] = C["linen"]
            else:
                fr[y, x] = C[c]
                if age <= 1:
                    fr[y + 1, x] = C["flame"] if age == 0 else C["bronze_lt"]
                    fr[y + 2, x] = C["bronze"]
        assert not (set(np.unique(fr).tolist()) & NO_RED)
        frames.append(fr)
    return frames


# --------------------------------------------------------------------------
# 5. zone ring: groove pieces (8 tangent directions) + rune pieces; placement by radius
# --------------------------------------------------------------------------
GR_W, GR_H, GR_PIV = 16, 12, (8, 6)
RU_W, RU_H, RU_PIV = 12, 8, (6, 4)
RING_COL = {"dim": ("night", "slate_dk"), "lit": ("bronze_dk", "bronze")}
RUNES_G = [  # rename_map §5: «кольцо насечек» — groups of short notches across the groove (squashed 2:1); no runes
    [".........", "..#.#.#..", "..#.#.#..", ".........", "........."],
    [".........", "...#.#...", "...#.#...", ".........", "........."],
    [".........", ".#.#.#.#.", ".#.#.#.#.", ".........", "........."],
    [".........", "..#...#..", "..#...#..", ".........", "........."],
]
SPACING_PX = 12.0          # arc length between pieces
RUNE_EVERY = 4             # every 4th piece (k % 4 == 2) is a rune


def groove_pieces(state):
    c0, c1 = (C[n] for n in RING_COL[state])
    out = []
    for b in range(8):
        ang = math.radians(b * 22.5)
        fr = np.full((GR_H, GR_W), -1, np.int16)
        u = (math.cos(ang), -math.sin(ang))                 # screen y down: bucket angle counter-clockwise
        for s in np.linspace(-3.5, 3.5, 29):
            x, y = GR_PIV[0] - 0.5 + u[0] * s, GR_PIV[1] - 0.5 + u[1] * s
            fr[int(round(y)), int(round(x))] = c0
        for s in (-2.0, 2.0):                                 # two notches across the groove (насечки)
            x, y = GR_PIV[0] - 0.5 + u[0] * s, GR_PIV[1] - 0.5 + u[1] * s
            n_ = (-u[1], u[0])
            xx, yy = int(round(x + n_[0] * 1.2)), int(round(y + n_[1] * 1.2))
            if fr[yy, xx] < 0:
                fr[yy, xx] = c1
        out.append(fr)
    return out


def rune_pieces(state):
    c0, c1 = (C[n] for n in RING_COL[state])
    out = []
    for g in RUNES_G:
        fr = np.full((RU_H, RU_W), -1, np.int16)
        for r, row in enumerate(g):
            for c, ch in enumerate(row):
                if ch == "#":
                    fr[r + 1, c + 1] = c0
        fr[RU_PIV[1], RU_PIV[0] - 1] = c1 if fr[RU_PIV[1], RU_PIV[0] - 1] >= 0 else fr[RU_PIV[1], RU_PIV[0] - 1]
        out.append(fr)
    return out


def ring_layout(radius_tiles, spacing=SPACING_PX):
    """Places pieces along the 2:1 ellipse of a ground circle of `radius_tiles`.
    Returns list of dicts {dx, dy, piece, index} relative to the zone centre (screen px)."""
    rx, ry = radius_tiles * PX_PER_TILE_X, radius_tiles * PX_PER_TILE_Y
    th = np.linspace(0, TAU, 4097)
    pts = np.stack([rx * np.cos(th), ry * np.sin(th)], 1)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    per = s[-1]
    n = int(round(per / spacing))
    out = []
    for k in range(n):
        t = np.interp(k * per / n, s, th)
        x, y = rx * math.cos(t), ry * math.sin(t)
        tx, ty = -rx * math.sin(t), ry * math.cos(t)
        ang = math.degrees(math.atan2(-ty, tx)) % 180.0       # counter-clockwise, screen y down
        b = int(round(ang / 22.5)) % 8
        if k % RUNE_EVERY == 2:
            out.append(dict(dx=int(round(x)), dy=int(round(y)), piece="rune", index=(k // RUNE_EVERY) % len(RUNES_G)))
        else:
            out.append(dict(dx=int(round(x)), dy=int(round(y)), piece="groove", index=b))
    return out, per


def assemble_ring(radius_tiles, state, canvas_wh=None, centre=None, layout=None):
    lay, _ = ring_layout(radius_tiles) if layout is None else (layout, 0)
    rx, ry = radius_tiles * PX_PER_TILE_X, radius_tiles * PX_PER_TILE_Y
    W, H = canvas_wh or (int(2 * rx) + 24, int(2 * ry) + 24)
    cx, cy = centre or (W // 2, H // 2)
    out = np.full((H, W), -1, np.int16)
    gp, rp = groove_pieces(state), rune_pieces(state)
    for p in lay:
        spr, piv = (gp[p["index"]], GR_PIV) if p["piece"] == "groove" else (rp[p["index"]], RU_PIV)
        x0, y0 = cx + p["dx"] - piv[0], cy + p["dy"] - piv[1]
        h, w = spr.shape
        ys, xs = slice(max(0, y0), min(H, y0 + h)), slice(max(0, x0), min(W, x0 + w))
        sub = spr[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]
        m = sub >= 0
        out[ys, xs][m] = sub[m]
    return out

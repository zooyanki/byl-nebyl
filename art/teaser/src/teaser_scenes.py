"""Teaser scenes (worlds without HUD)."""
from teaser_world import *          # noqa
from teaser_world import _r


# ==========================================================================
# SCENE 1 — «Огонь на капище» (teaser §2.2)
# ==========================================================================
S1 = dict(idol=(232, 150), krada=(196, 214), hearth2=(440, 120), upyr1=(360, 190), upyr2=(404, 166),
          upyr3=(432, 220))
PAL_C = (320, 550, 896, 448)          # round palisade: screen centre, rx, ry (circle R≈39.6 tiles)


def pal_base(x):
    cx, cy, rx, ry = PAL_C
    return cy - ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))


def ground_shrine(lit, rng):
    b = BAY
    n = noise(26, 3) * 0.65 + noise(6, 4) * 0.35
    n2 = noise(34, 9)
    lit.put(np.ones((H, W), bool), "earth", np.clip(np.floor(1.7 + n * 2.0 + (b - 0.5) * 0.9).astype(int), 1, 3))
    ash = (noise(11, 21) * 0.7 + n2 * 0.3 > 0.6) & (b < 0.55)
    lit.put(ash, "stone", np.clip(np.floor(1.5 + n * 1.6).astype(int), 1, 3))
    # moss and dry grass at the edges of the trampled shrine floor
    d = np.hypot((XX - 290) / 300, (YY - 190) / 135)
    edge = d + (n2 - 0.5) * 0.4 > 0.88
    lit.put(edge, "grass", np.clip(np.floor(1.4 + n * 2 + (b - 0.5) * 0.9).astype(int), 1, 3))
    lit.put(edge & (noise(14, 12) > 0.6), "pine", np.clip(np.floor(1.5 + n * 2).astype(int), 1, 2))
    g = rid("grass")
    for _ in range(420):                      # dry grass tufts
        x, y = int(rng.integers(2, W - 2)), int(rng.integers(4, H - 2))
        if lit.ramp[y, x] != g:
            continue
        hgt = int(rng.integers(2, 5))
        straw = rng.random() < 0.5
        for k in range(hgt):
            if straw:
                lit.ramp[y - k, x] = rid("bronze"); lit.lvl[y - k, x] = 2 if k < hgt - 1 else 3
            else:
                lit.lvl[y - k, x] = 3 if k < hgt - 1 else 4
        lit.ramp[y - 1, x - 1] = rid("bronze") if straw else g; lit.lvl[y - 1, x - 1] = 2
    for _ in range(50):                       # pebbles
        x, y = int(rng.integers(4, W - 4)), int(rng.integers(110, H - 4))
        lit.put(_r(x, y, 3, 2), "stone", 3); lit.put(_r(x, y, 2, 1), "stone", 4); lit.put(_r(x, y + 2, 3, 1), "ink", 0)


def palisade_round(lit, rng):
    """Частокол капища 80 px (scale.md §3.1 logs: 5 px, tips 4-6, bindings
    at 24/64) on a large circle around the shrine: in the 2:1 projection the
    back arc of a ring R≈40 tiles runs along the top of the frame."""
    logs = []
    for x in range(-6, W + 6, 5):
        logs.append((x, int(round(pal_base(x + 2.5)))))
    logs.sort(key=lambda t: t[1])
    tops = []
    for (x, y) in logs:
        h = int(79 + rng.integers(-4, 5))
        tip = int(rng.integers(4, 7))
        tops.append((x + 2, y - h - 1, h + 1))
        burnt = 150 <= x <= 300 and rng.random() < 0.45
        for i, l in enumerate((4, 3, 3, 2, 1)):
            top = y - h + int(round(abs(i - 2) / 2 * tip))
            lit.put(_r(x + i, top, 1, y - top), "wood", l)
        lit.put(_r(x + 2, y - h - 1, 1, 1), "wood", 4)
        lit.put(_r(x, y - h + tip, 5, 1), "wood", 1)
        for _ in range(2):
            ky = y - int(rng.integers(8, h - 10))
            lit.put(_r(x + 1 + int(rng.integers(0, 2)), ky, 2, 1), "wood", 1)
        for bz in (24, 64):
            lit.put(_r(x, y - bz, 5, 2), "wood", 1)
            lit.put(_r(x, y - bz - 1, 5, 1), "bronze", 2)
        if burnt:                               # scorched tips near the burning idol
            ch = int(rng.integers(10, 24))
            lit.put(_r(x, y - h - 1, 5, ch), "wood", 0)
            lit.put(_r(x + 1, y - h + ch - 2, 3, 1), "red", 2, em=True)
            if rng.random() < 0.5:
                lit.put(_r(x + 2, y - h + int(rng.integers(2, ch)), 1, 1), "fire", 1, em=True)
        lit.put(_r(x - 1, y - 1, 7, 2), "earth", 1)         # dark soil at the foot
    MEASURE_PAL = [t[2] for t in tops]
    MEAS["palisade"] = dict(h_mean=float(np.mean(MEASURE_PAL)), h_min=min(MEASURE_PAL), h_max=max(MEASURE_PAL),
                            top_centre=min(t[1] for t in tops if 300 <= t[0] <= 340),
                            top_x100=[t[1] for t in tops if 98 <= t[0] <= 104][0],
                            base_centre=int(pal_base(320)), base_x440=int(pal_base(440)))


def forest_behind(lit, rng):
    for k, x in enumerate(range(-30, W + 40, 21)):
        base = int(pal_base(x)) - int(rng.integers(6, 30))
        h = int(rng.integers(140, 191))
        G.spruce(lit, x + int(rng.integers(-6, 7)), base, h, seed=100 + k, dark=2)


def fence_ring(lit, rng, front):
    """Ограда вокруг идола: posts 20 px on a ring Ø8 tiles, ditch -8 outside;
    open toward the hero and the крада. front=True draws the near arc."""
    cx, cy = S1["idol"]
    R = 4.0
    rx, ry = R * 16 * math.sqrt(2), R * 8 * math.sqrt(2)
    if not front:                                   # ditch (ров): dark band outside the posts
        d = np.hypot((XX - cx) / (rx + 6), (YY - cy) / (ry + 3))
        band = (d > 0.93) & (d < 1.07)
        gap = (XX > cx + 20) & (YY > cy - 14)
        band = (d > 0.97) & (d < 1.06)
        lit.put(band & ~gap, "earth", 1)
        lit.put(band & ~gap & (BAY < 0.2), "ink", 0)
        lip = (d >= 1.06) & (d < 1.11) & ~gap
        lit.put(lip & (YY >= cy), "earth", 3)
    posts = []
    for k in range(36):
        a = k / 36 * math.tau
        x, y = cx + math.cos(a) * rx, cy + math.sin(a) * ry
        is_front = math.sin(a) > 0
        if is_front != front:
            continue
        if x > cx + 18 and y > cy - 16:             # opening toward the hero / upyrs
            continue
        if front and x > cx - 40 and y > cy + 30:   # opening toward the крада
            continue
        posts.append((int(x), int(y)))
    posts.sort(key=lambda p: p[1])
    for i, (x, y) in enumerate(posts):
        hh = 20 + int(rng.integers(-1, 2))
        lit.put(_r(x - 1, y - hh + 2, 3, hh - 2), "wood", 2)
        lit.put(_r(x - 1, y - hh + 2, 1, hh - 2), "wood", 3)
        lit.put(_r(x, y - hh + 1, 1, 1), "wood", 3)
        lit.put(_r(x - 2, y - hh + 2, 1, hh - 2), "ink", 0); lit.put(_r(x + 2, y - hh + 2, 1, hh - 2), "ink", 0)
        lit.put(_r(x - 1, y - hh, 1, 1), "ink", 0); lit.put(_r(x + 1, y - hh, 1, 1), "ink", 0)
        lit.put(_r(x - 1, y - 9, 3, 1), "bronze", 1)
        if i % 7 == 3:                              # animal skull on a post (обережный череп)
            lit.put(_r(x - 2, y - hh - 3, 5, 3), "stone", 6); lit.put(_r(x - 1, y - hh - 2, 1, 1), "ink", 0)
            lit.put(_r(x + 1, y - hh - 2, 1, 1), "ink", 0)
        MEAS.setdefault("fence_posts", []).append(hh)


def perun_burning(lit, rng):
    cx, cy = S1["idol"]
    # 2x2 stone platform (4 px high)
    P0 = lambda du, dv, z: (cx + (du - dv) * 16, cy + (du + dv) * 8 - z)
    top = poly_mask([P0(-1, -1, 4), P0(1, -1, 4), P0(1, 1, 4), P0(-1, 1, 4)])
    side = poly_mask([P0(-1, 1, 4), P0(1, 1, 4), P0(1, -1, 4), P0(1, -1, 0), P0(1, 1, 0), P0(-1, 1, 0)])
    lit.put(side, "stone", 2); lit.put(side & (XX > cx), "stone", 1)
    lit.put(top, "stone", 3); lit.put(top & (BAY < 0.25), "stone", 4)
    lit.put(top & (noise(5, 77) > 0.6), "stone", 1)              # soot
    for (x0, y0, x1, y1) in ((cx - 32, cy - 4, cx, cy + 12), (cx, cy + 12, cx + 32, cy - 4)):
        lit.put(line_mask(x0, y0, x1, y1), "ink", 0)
    spr = charred(perun_idol(), (0.5, 1.0), seed=3)
    b = place_m(lit, "perun_idol", spr, (cx, cy))
    # fire: a ragged mass around the base climbing the trunk sides; the carved
    # face and the gold moustache stay readable between the tongues
    face = (XX >= cx - 7) & (XX <= cx + 7) & (YY >= cy - 104) & (YY <= cy - 64)
    env = np.clip(1 - np.abs((XX - cx) / 15.0) ** 1.6, 0, 1)
    env = np.where(np.abs(XX - cx) > 5, env * 1.0, env * 0.62)       # lower in the middle: sides burn higher
    noise_fire(lit, cx, cy - 2, 15, 70, seed=41, env=env, avoid=face)
    noise_fire(lit, cx + 10, cy - 50, 5, 34, seed=43, avoid=face)        # tongue up the right side
    noise_fire(lit, cx - 10, cy - 44, 4, 24, seed=44, avoid=face)        # and the left
    G.flame(lit, cx + 11, cy - 80, 1, 10, seed=16)
    G.flame(lit, cx - 3, cy - 104, 1, 6, seed=17)                         # flame on the cap spire
    # embers rising from the idol and drifting right
    for _ in range(46):
        t = rng.uniform(0, 1)
        x = cx + rng.normal(0, 7) + t * 70 * rng.uniform(0.4, 1.1)
        y = cy - 60 - t * 100 + rng.normal(0, 6)
        if y > 2:
            put_px(lit, x, y, "fire", int(rng.integers(1, 4)), em=True)
    return b


def debris_shrine(lit, rng):
    S = SR.build()
    kx, ky = S1["krada"]
    for (x, y) in ((kx + 30, ky + 8), (kx - 34, ky - 6), (262, 196), (470, 140)):
        G.place(lit, S["skull"], (x, y))
    for (x0, y0, x1, y1, emb) in ((150, 232, 170, 226, True), (226, 236, 246, 246, False), (262, 166, 276, 176, True),
                                  (300, 222, 324, 220, False), (470, 196, 488, 204, True), (128, 196, 140, 186, False)):
        lit.put(line_mask(x0, y0, x1, y1, 2), "wood", 0)
        lit.put(line_mask(x0, y0, x1, y1, 1), "wood", 1)
        if emb:
            lit.put(_r(x1 - 1, y1 - 1, 2, 2), "fire", 1, em=True)
    for _ in range(70):                     # embers on the ground near the fires
        cx, cy = (S1["krada"] if rng.random() < 0.55 else S1["idol"])
        x, y = cx + rng.normal(0, 30), cy + abs(rng.normal(0, 14)) + 4
        put_px(lit, x, y, "fire", int(rng.integers(0, 2)), em=True)


def emerge_mound(lit, rng, x, y):
    """Broken earth around the upyr climbing out (clods, dark pit)."""
    pit = ((XX - x) / 13) ** 2 + ((YY - y) / 5) ** 2 <= 1
    lit.put(pit, "ink", 0)
    lit.put(pit & (YY > y + 1) & (BAY < 0.5), "earth", 1)
    for _ in range(16):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(11, 20)
        cx, cy = x + math.cos(a) * rr, y + math.sin(a) * rr * 0.45 + 1
        sz = int(rng.integers(2, 4))
        lit.put(_r(cx, cy, sz, 2), "earth", 3); lit.put(_r(cx, cy, sz, 1), "earth", 4)
        lit.put(_r(cx, cy + 2, sz, 1), "ink", 0)
    for (dx, dy) in ((-8, -10), (7, -13), (12, -6), (-12, -4)):       # flying clods
        lit.put(_r(x + dx, y + dy, 2, 2), "earth", 3); lit.put(_r(x + dx, y + dy + 2, 2, 1), "ink", 0)


def front_rim(lit, x, y):
    """Front lip of the pit drawn over the upyr's waist."""
    lip = (((XX - x) / 14) ** 2 + ((YY - y) / 5.5) ** 2 <= 1) & (YY >= y + 1)
    lit.put(lip, "earth", 2)
    lit.put(lip & (YY == y + 1), "earth", 3)
    lit.put(lip & (BAY < 0.2), "earth", 4)


def scene1():
    rng = np.random.default_rng(101)
    lit = pk.Lit(W, H)
    ground_shrine(lit, rng)
    forest_behind(lit, rng)
    palisade_round(lit, rng)
    # foreground-left dark spruce under the tracker area (background mass)
    fence_ring(lit, rng, front=False)
    smoke_plume(lit, S1["idol"][0] + 2, S1["idol"][1] - 96, 0, 6, 34, 90, seed=5, lvl=(2, 3))
    perun_burning(lit, rng)
    fence_ring(lit, rng, front=True)
    G.FIRE = S1["krada"]
    G.krada(lit)
    kx, ky = S1["krada"]
    noise_fire(lit, kx, ky - 23, 11, 46, seed=61, ymin=ky - 72, hot=1.1)
    MEAS["krada_flame_top"] = int(np.where((lit.ramp == rid("fire")) & lit.em & (np.abs(XX - S1["krada"][0]) <= 9)
                                           & (YY < S1["krada"][1]) & (YY > 100))[0].min())
    dead_hearth(lit, *S1["hearth2"], rng)
    smoke(lit, S1["hearth2"][0] - 1, S1["hearth2"][1] - 6, 80, 40, seed=3)
    smoke(lit, S1["hearth2"][0] + 4, S1["hearth2"][1] - 4, 60, 30, seed=7)
    debris_shrine(lit, rng)
    # characters
    ux, uy = S1["upyr3"]
    emerge_mound(lit, rng, ux, uy)
    hero = TS.hero_pose("swing")
    u1, u2 = TS.upyr_lunge(), TS.upyr_shamble()
    shadow(lit, *S1["upyr2"], 9, 3)
    place_m(lit, "upyr2", u2, S1["upyr2"])
    shadow(lit, *HERO, 9, 3.5)
    place_m(lit, "hero", hero, HERO)
    shadow(lit, S1["upyr1"][0] - 2, S1["upyr1"][1], 10, 3)
    place_m(lit, "upyr1", u1, S1["upyr1"], outline_ramp=("red", 3))
    place_m(lit, "upyr3", TS.upyr_emerge(), (ux, uy + 2))
    front_rim(lit, ux, uy)
    # visible part of upyr 3 above the ground lip
    m = sprite_mask_at(TS.upyr_emerge(), (ux, uy + 2))
    rows = np.where(m.any(1))[0]
    MEAS["upyr3_visible"] = int(uy + 1 - rows.min())
    # spruces along the left edge (under the tracker / orb: background only) and right
    for k, (x, base, h) in enumerate(((44, 150, 150), (8, 232, 170), (74, 312, 142), (30, 352, 160), (596, 214, 148))):
        G.spruce(lit, x, base, h, seed=500 + k, dark=1)
        MEAS.setdefault("spruces", []).append(h)
    # sacrificial stone with a soot-black top and a toppled bowl
    sx, sy = 272, 262
    lit.put(_r(sx - 10, sy - 6, 21, 7), "stone", 3); lit.put(_r(sx - 10, sy - 7, 20, 2), "stone", 5)
    lit.put(_r(sx - 4, sy - 7, 8, 1), "stone", 1); lit.put(_r(sx - 11, sy + 1, 23, 1), "ink", 0)
    lit.put(_r(sx + 12, sy - 1, 5, 3), "wood", 3); lit.put(_r(sx + 12, sy - 1, 5, 1), "wood", 4)
    for k in range(6):
        put_px(lit, sx + 17 + k, sy + 1 + (k % 2), "bronze", 3)          # spilled grain
    # foreground spruce at the right edge (220-240), cut by the frame as specified
    G.spruce(lit, 634, 352, 232, seed=77, wk=0.2, trunk=6)
    MEAS["spruce_fg"] = 232
    # lights: крада + burning idol; night ambient
    ix, iy = S1["idol"]; kx, ky = S1["krada"]
    src = [(kx, ky - 36, 200, 0.95), (ix, iy - 60, 210, 0.9), (ix, iy - 20, 130, 0.5), (HERO[0], HERO[1] - 22, 90, 0.25),
           (440, 116, 50, 0.18), (470, 150, 230, 0.34), (330, 250, 200, 0.18),
           (60, 250, 150, 0.22), (580, 270, 170, 0.22), (560, 40, 200, 0.2)]
    L = pk.light_field(W, H, src, ambient=0.36, depth=3.6, ysquash=1.4, gamma=0.9)
    a = lit.flatten(L)
    tint(a, kx, ky - 30, 92, 0.62, G.WARM)
    tint(a, ix, iy - 50, 115, 0.55, G.WARM)
    return a, lit, L


# ==========================================================================
# SCENES 2-3 — «Разлом в Чёрном бору» (teaser §3.2, §4.2): one shared world
# ==========================================================================
S2 = dict(rift=(452, 172), volk=(446, 176), idol=(530, 128), fallen=(180, 238), leap=(414, 168))


def ground_forest(lit, rng, seed=0):
    b = BAY
    n = noise(24, 31 + seed) * 0.6 + noise(7, 32 + seed) * 0.4
    lit.put(np.ones((H, W), bool), "grass", np.clip(np.floor(1.3 + n * 2.0 + (b - 0.5) * 0.9).astype(int), 1, 3))
    dark = noise(18, 33 + seed) > 0.56
    lit.put(dark, "pine", np.clip(np.floor(1.2 + n * 1.8 + (b - 0.5) * 0.9).astype(int), 1, 2))
    frost = (noise(6, 34 + seed) * 0.6 + noise(17, 35 + seed) * 0.4 > 0.66)
    lit.put(frost & (b < 0.5), "stone", 4)
    lit.put(frost & (b < 0.15), "stone", 5)
    for _ in range(420):                     # needles and twigs
        x, y = int(rng.integers(0, W - 3)), int(rng.integers(0, H))
        lit.put(_r(x, y, int(rng.integers(1, 4)), 1), "wood", 1)
    for _ in range(260):                     # moss tufts
        x, y = int(rng.integers(1, W - 2)), int(rng.integers(2, H))
        lit.put(_r(x, y - 1, 1, 2), "grass", 3); lit.put(_r(x + 1, y, 1, 1), "grass", 2)
    for _ in range(46):                      # stones with frost caps
        x, y = int(rng.integers(4, W - 6)), int(rng.integers(40, H - 4))
        w = int(rng.integers(3, 6))
        lit.put(_r(x, y, w, 2), "stone", 2); lit.put(_r(x, y - 1, w - 1, 1), "stone", 5); lit.put(_r(x, y + 2, w, 1), "ink", 0)


def forest_frame(lit, rng, variant=2):
    """Trees only around the edges and along the top; nearly black."""
    back = [(18, 60, 176), (60, 78, 160), (104, 52, 186), (150, 70, 170), (262, 58, 182), (300, 84, 158),
            (356, 62, 176), (398, 80, 164), (512, 66, 172), (566, 58, 188), (612, 78, 166)]
    if variant == 4:
        back = [(18, 60, 176), (64, 80, 160), (580, 60, 186), (622, 80, 168)]
    for k, (x, base, h) in enumerate(back):
        pine(lit, x, base, h, seed=200 + k, trunk=7 if k % 2 else 6, dark=1)
        MEAS.setdefault("pines", []).append(h)
    side = [(36, 150, 140), (90, 118, 128), (14, 212, 156), (60, 262, 150), (24, 330, 160),
            (606, 150, 150), (628, 236, 160), (590, 300, 146), (636, 352, 158)]
    if variant == 4:
        side = [(36, 150, 140), (14, 212, 156), (40, 300, 150), (612, 150, 152), (630, 250, 160), (600, 330, 146)]
    for k, (x, base, h) in enumerate(side):
        G.spruce(lit, x, base, h, seed=300 + k, dark=2, wk=0.18)
        MEAS.setdefault("spruces", []).append(h)
    if variant != 4:
        pine(lit, 548, 352, 184, seed=260, trunk=8, dark=1)
        MEAS["pines"].append(184)


def chur_black(lit, feet):
    spr = recolor(SR.idol(), ("wood", "bronze", "fire"), ("fur", "fur", "nebyl"))
    # carved runes glowing Небыль green
    ys, xs = np.where(spr["mask"] & (spr["ramp"] == rid("fur")))
    rng = np.random.default_rng(5)
    for i in rng.choice(len(ys), 7, replace=False):
        if 22 < ys[i] < 50:
            spr["ramp"][ys[i], xs[i]] = rid("nebyl"); spr["lvl"][ys[i], xs[i]] = 3; spr["em"][ys[i], xs[i]] = True
    for y in (40, 46):
        for x in range(6, 13, 2):
            if spr["mask"][y, x]:
                spr["ramp"][y, x] = rid("nebyl"); spr["lvl"][y, x] = 2; spr["em"][y, x] = True
    shadow(lit, feet[0], feet[1], 8, 3)
    return place_m(lit, "chur_idol", spr, feet)


def forest_world():
    """Shared Чёрный бор world for scenes 2 and 3 (no characters)."""
    rng = np.random.default_rng(202)
    lit = pk.Lit(W, H)
    ground_forest(lit, rng)
    forest_frame(lit, rng)
    inverted_pine(lit, 214, 104, 92, seed=9)
    MEAS["inverted_pine"] = 92
    rx, ry = S2["rift"]
    # corrupted ground around the rift
    dd = np.hypot(XX - rx, (YY - ry) * 2.0)
    corrupt = (dd < 70) & (BAY < np.clip(1 - dd / 70, 0, 1) * 0.7)
    lit.put(corrupt & (lit.ramp == rid("grass")), "nebyl", 1)
    lit.put(corrupt & (lit.ramp == rid("stone")), "stone", 2)
    ground_crack(lit, [(rx - 64, ry + 22), (rx - 44, ry + 12), (rx - 26, ry + 10), (rx - 10, ry + 3), (rx + 2, ry),
                       (rx + 18, ry - 5), (rx + 34, ry - 12), (rx + 52, ry - 16), (rx + 66, ry - 24)],
                 branches=((rx - 26, ry + 10, rx - 32, ry + 20), (rx + 18, ry - 5, rx + 26, ry + 6),
                           (rx - 44, ry + 12, rx - 52, ry + 6)))
    chur_black(lit, S2["idol"])
    fx, fy = S2["fallen"]
    stump(lit, fx + 34, fy - 4, seed=2)
    MEAS["fallen_idol_1"] = fallen_idol(lit, fx, fy, k=1, seed=4)
    snap_before_rift = snapshot(lit)
    tear = rift_tear(lit, rx, ry, th=89, hw=13, seed=1, stars=4)
    trows = np.where(tear["inside"] & (tear["dx"] <= tear["half"] + 0.5))[0]
    MEAS["rift_s23"] = dict(top=int(trows.min()), bottom=int(trows.max()), h=int(trows.max() - trows.min() + 1))
    return lit, rng, tear


def forest_lights(extra=()):
    rx, ry = S2["rift"]
    src = [(rx, ry - 44, 190, 0.8), (HERO[0], HERO[1] - 22, 120, 0.3), (200, 40, 260, 0.3),
           (S2["idol"][0], S2["idol"][1] - 30, 60, 0.3), (330, 220, 220, 0.2)] + list(extra)
    return pk.light_field(W, H, src, ambient=0.4, depth=3.6, ysquash=1.4, gamma=0.9)


def nebyl_eyes(spr):
    s = dict(spr)
    for k in ("ramp", "lvl", "em"):
        s[k] = spr[k].copy()
    e = spr["mask"] & ((spr["ramp"] == rid("fire")) | (spr["ramp"] == rid("nebyl")) & ~spr["em"])
    e = spr["mask"] & (spr["ramp"] == rid("fire"))
    s["ramp"][e] = rid("nebyl"); s["lvl"][e] = 3; s["em"][e] = True
    return s


CHAR = {}


def volk_out_of_rift(lit, tear):
    """Волколак half out of the tear: everything right of the tear's left
    lip is swallowed by the dark (dissolves into motes at the cut)."""
    snap = snapshot(lit)
    spr = TS.rim_light(SR.volkolak(), side=1)          # Небыль rim on the contour (GDD §5)
    vx, vy = S2["volk"]
    spr = nebyl_eyes(spr)
    place_m(lit, "volkolak_s2", spr, (vx, vy))
    m = sprite_mask_at(spr, (vx, vy))
    cut = np.where(YY <= tear["ty"], tear["cx"] - tear["half"] * 0.15, tear["tx"] - 1)
    hide = m & (XX > cut)
    restore(lit, snap, hide)
    band = m & ~hide & (XX > cut - 3) & (YY < tear["ty"])
    motes = band & (BAY < 0.5)
    lit.ramp[motes] = rid("nebyl"); lit.lvl[motes] = 3; lit.em[motes] = True
    for k in range(10):                               # motes peeling off toward the tear
        ys, xs = np.where(band)
        if len(xs):
            i = (k * 37) % len(xs)
            put_px(lit, xs[i] + 2 + k % 3, ys[i] - 1, "nebyl", 4 if k % 3 == 0 else 3, em=True)
    vis = m & ~hide
    CHAR["volk"] = vis
    rows, cols = np.where(vis.any(1))[0], np.where(vis.any(0))[0]
    MEAS["volkolak_s2_visible"] = dict(top=int(rows.min()), bottom=int(rows.max()), left=int(cols.min()),
                                       right=int(cols.max()))


def scene2():
    lit, rng, tear = forest_world()
    snow_up(lit, rng, 42, (0, 0, W, 300))
    volk_out_of_rift(lit, tear)
    shadow(lit, *HERO, 9, 3.5)
    hero = TS.hero_pose("guard")
    place_m(lit, "hero_s2", hero, HERO)
    prot = CHAR["volk"] | sprite_mask_at(hero, HERO)
    L = forest_lights()
    a = lit.flatten(L)
    rx, ry = S2["rift"]
    tint_p(a, rx, ry - 40, 80, 0.75, G.EERIE, prot, 0.25)
    tint_p(a, rx, ry - 30, 150, 0.35, G.EERIE, prot, 0.25)
    return a, lit, L


def fire_clump(lit, cx, cy, rng):
    """Огненный змей being born on the sword tip: a coiled clump 11 px with a
    tiny serpent head pointing right, red_lt rim, 5 sparks."""
    d = np.hypot(XX - cx, (YY - cy) * 1.05)
    ang = np.arctan2(YY - cy, XX - cx)
    clump = d <= 5.6
    lit.put(clump, "fire", 1, em=True)                       # red_lt rim
    lit.put(d <= 4.4, "fire", 2, em=True)                    # ember
    spiral = (d <= 4.4) & (np.mod(ang + d * 1.1, math.tau) < 1.6)
    lit.put(spiral, "fire", 3, em=True)                      # flame coil
    lit.put(d <= 1.6, "fire", 4, em=True)                    # white-hot core
    # serpent head poking out to the right, eye
    lit.put(_r(cx + 5, cy - 2, 3, 3), "fire", 2, em=True); lit.put(_r(cx + 8, cy - 1, 2, 2), "fire", 1, em=True)
    put_px(lit, cx + 6, cy - 1, "red", 0, em=True)
    # tail flick to the upper-left
    for k, (dx, dy) in enumerate(((-5, -4), (-6, -5), (-7, -5), (-8, -6))):
        put_px(lit, cx + dx, cy + dy, "fire", 2 if k < 2 else 1, em=True)
    for (dx, dy) in ((-9, 3), (3, -9), (10, -6), (8, 6), (-3, 8)):
        put_px(lit, cx + dx, cy + dy, "fire", int(rng.integers(2, 5)), em=True)
    MEAS["fire_clump"] = dict(centre=(cx, cy), size=int(2 * 5.6))


def scene3():
    lit, rng, tear = forest_world()
    snow_up(lit, rng, 42, (0, 0, W, 300))                    # same rng sequence -> same snow as scene 2
    lx, ly = S2["leap"]
    shadow(lit, lx, ly + 10, 16, 3.5, -2)
    spr = TS.rim_light(TS.volkolak_leap(1.07), side=1)
    place_m(lit, "volkolak_s3", nebyl_eyes(spr), (lx, ly))
    shadow(lit, *HERO, 9, 3.5)
    hero = TS.hero_pose("cast")
    place_m(lit, "hero_s3", hero, HERO)
    tx, ty = HERO[0] + hero["tip"][0], HERO[1] + hero["tip"][1]
    fire_clump(lit, tx + 1, ty, rng)
    prot = sprite_mask_at(spr, (lx, ly)) | sprite_mask_at(hero, HERO)
    L = forest_lights(extra=[(tx, ty, 48, 0.6)])
    a = lit.flatten(L)
    rx, ry = S2["rift"]
    tint_p(a, rx, ry - 40, 80, 0.75, G.EERIE, prot, 0.25)
    tint_p(a, rx, ry - 30, 150, 0.35, G.EERIE, prot, 0.25)
    tint(a, tx, ty, 30, 0.6, G.WARM)
    return a, lit, L

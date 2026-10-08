"""Shared world-building helpers for the teaser frames (teaser.md §1–5)."""
import os
import sys
import math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/workspace/game/art/ui/src")
sys.path.insert(0, HERE)
import numpy as np
import gameplay_hud_v2 as G          # activates palette v2
import pixelkit as pk
import sprites_rus as SR
import teaser_sprites as TS
from pixelkit import C, Canvas

W, H = 640, 360
HERO = (320, 178)
P, proj, inv_proj, _r, poly_mask, rid = G.P, G.proj, G.inv_proj, G._r, G.poly_mask, G.rid
YY, XX = np.mgrid[0:H, 0:W]
BAY = pk.bayer(H, W)
MEAS = {}


def noise(cell, seed):
    return pk.value_noise(H, W, cell, seed=seed)


def put_px(lit, x, y, ramp, lvl, em=False):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < W and 0 <= y < H:
        lit.ramp[y, x] = rid(ramp); lit.lvl[y, x] = lvl; lit.em[y, x] = em


def line_mask(x0, y0, x1, y1, w=1):
    c = Canvas(W, H)
    for k in range(w):
        c.line(int(round(x0)), int(round(y0)) + k, int(round(x1)), int(round(y1)) + k, 1)
    return c.a == 1


def sprite_box(spr, feet):
    """Screen bbox of a sprite placed by G.place (x0, y0, x1, y1, inclusive)."""
    rows = np.where(spr["mask"].any(1))[0]; cols = np.where(spr["mask"].any(0))[0]
    if "pivot" in spr:
        ox, oy = feet[0] - spr["pivot"][0], feet[1] - spr["pivot"][1]
    else:
        ox, oy = feet[0] - spr["w"] // 2, feet[1] - spr["h"] + 1
    return (ox + cols.min(), oy + rows.min(), ox + cols.max(), oy + rows.max())


def place_m(lit, name, spr, feet, outline_ramp=None, remap=None):
    G.place(lit, spr, feet, outline_ramp, remap)
    b = sprite_box(spr, feet)
    MEAS[name] = dict(box=b, h=b[3] - b[1] + 1, w=b[2] - b[0] + 1)
    return b


def sprite_mask_at(spr, feet):
    m = np.zeros((H, W), bool)
    if "pivot" in spr:
        ox, oy = feet[0] - spr["pivot"][0], feet[1] - spr["pivot"][1]
    else:
        ox, oy = feet[0] - spr["w"] // 2, feet[1] - spr["h"] + 1
    h, w = spr["mask"].shape
    x0, y0, x1, y1 = max(0, ox), max(0, oy), min(W, ox + w), min(H, oy + h)
    m[y0:y1, x0:x1] = spr["mask"][y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    return m


def snapshot(lit):
    return (lit.ramp.copy(), lit.lvl.copy(), lit.em.copy())


def restore(lit, snap, mask):
    lit.ramp[mask] = snap[0][mask]; lit.lvl[mask] = snap[1][mask]; lit.em[mask] = snap[2][mask]


def recolor(spr, ramp_from=None, ramp_to=None, outline=None, em_outline=False):
    s = dict(spr)
    for k in ("ramp", "lvl", "em"):
        s[k] = spr[k].copy()
    if ramp_from:
        for a, b in zip(ramp_from, ramp_to):
            s["ramp"][spr["ramp"] == rid(a)] = rid(b)
    if outline:
        o = spr["mask"] & (spr["ramp"] == rid("ink"))
        s["ramp"][o] = rid(outline[0]); s["lvl"][o] = outline[1]
        if em_outline:
            s["em"][o] = True
    return s


def rot_sprite(spr, k):
    s = dict(spr)
    for key in ("ramp", "lvl", "em", "mask"):
        s[key] = np.rot90(spr[key], k).copy()
    s["h"], s["w"] = s["mask"].shape
    s.pop("pivot", None)
    return s


# --------------------------------------------------------------------------
# props
# --------------------------------------------------------------------------
TS.TM.update({"o": ("stone", 4, True, False), "q": ("stone", 2, False, False),
              "t": ("iron", 5, True, False), "J": ("wood", 1, False, False, "grain")})


def perun_idol():
    """Идол Перуна (teaser §2.2): 104 x 24 with the outline, carved face with a
    silver head-cap and a gold moustache (летопись: «глава сребрена, ус злат»),
    arms holding a horn, belt, громовник on the lower trunk, stone plinth."""
    m = pk.MatCanvas(24, 102)
    # plinth of stones (24 wide)
    m.poly([(0, 95), (23, 95), (23, 101), (0, 101)], "o")
    for x in (0, 6, 12, 18):
        m.line(x, 95, x, 101, "q")
    m.line(0, 98, 23, 98, "q")
    # trunk
    m.rect(4, 12, 16, 84, "X")
    m.rect(15, 12, 5, 84, "x")
    # silver head-cap (шелом) with a spire
    m.poly([(3, 15), (20, 15), (18, 7), (13, 2), (11.5, 0), (10, 2), (5, 7)], "t")
    m.line(3, 15, 20, 15, "h"); m.line(4, 14, 19, 14, "Z")
    # face
    m.line(6, 19, 10, 18, "k"); m.line(13, 18, 17, 19, "k")       # brows
    m.px(8, 20, "E"); m.px(15, 20, "E")                             # eyes (embers in the sockets)
    m.line(11, 19, 11, 25, "x"); m.line(12, 19, 12, 25, "J")       # nose
    # gold moustache, long and drooping
    m.poly([(11.5, 26), (5, 27), (3, 33), (6, 29), (11.5, 28)], "Z")
    m.poly([(11.5, 26), (18, 27), (20, 33), (17, 29), (11.5, 28)], "Z")
    m.line(9, 30, 14, 30, "k")                                      # mouth
    m.poly([(7, 31), (16, 31), (14, 40), (9, 40)], "x")             # beard
    for y in (33, 36):
        m.line(9, y, 14, y, "J")
    # arms carved in relief, hands holding a horn (рог) at the chest
    m.line(4, 42, 4, 56, "J"); m.line(5, 56, 11, 54, "J")
    m.line(19, 42, 19, 56, "J"); m.line(18, 56, 13, 54, "J")
    m.poly([(9, 46), (14, 46), (15, 53), (11, 56), (8, 52)], "Z")   # horn
    m.line(10, 47, 13, 47, "z")
    m.rect(4, 60, 16, 3, "Z")                                       # belt
    for x in (6, 10, 14, 18):
        m.px(x, 61, "g")
    # sword in relief hanging from the belt
    m.line(15, 63, 15, 80, "J"); m.line(13, 64, 17, 64, "J")
    # громовник (six-petal rosette) on the lower trunk
    for k in range(6):
        a = k / 6 * math.tau
        m.line(10, 74, 10 + math.cos(a) * 3.5, 74 + math.sin(a) * 3.5, "Z")
    m.px(10, 74, "g")
    # notches at the base of the trunk
    for y in (86, 90):
        m.line(4, y, 19, y, "J")
    return pk.make_sprite(m.rows(), TS.TM)


def charred(spr, frac_rows=(0.45, 1.0), seed=0):
    """Char the lower part of a wooden sprite: darker wood + ember cracks."""
    s = dict(spr)
    for k in ("ramp", "lvl", "em"):
        s[k] = spr[k].copy()
    h = spr["mask"].shape[0]
    rng = np.random.default_rng(seed)
    yy = np.arange(h)[:, None] * np.ones((1, spr["mask"].shape[1]), int)
    xx = np.ones((h, 1), int) * np.arange(spr["mask"].shape[1])[None, :]
    rel = yy / h
    wood = spr["mask"] & (spr["ramp"] == rid("wood"))
    zone = wood & (rel > frac_rows[0]) & (rel < frac_rows[1])
    s["lvl"][zone] = np.maximum(0, s["lvl"][zone] - 1)
    deep = zone & (pk.bayer(h, spr["mask"].shape[1]) < (rel - frac_rows[0]) * 1.4)
    s["lvl"][deep] = np.maximum(0, s["lvl"][deep] - 1)
    cracks = zone & (pk.hash2(xx // 2, yy // 3, seed) < 0.12)
    s["ramp"][cracks] = rid("fire"); s["lvl"][cracks] = rng.integers(0, 3, cracks.sum()); s["em"][cracks] = True
    return s


def stone_ring(lit, cx, cy, front, rx=17, ry=8.5, n=16, lvl=3):
    for k in range(n):
        a = k / n * math.tau
        if (math.sin(a) > 0) != front:
            continue
        x, y = int(cx + math.cos(a) * rx), int(cy + math.sin(a) * ry)
        lit.put(_r(x - 3, y - 2, 6, 4), "stone", lvl)
        lit.put(_r(x - 3, y - 2, 5, 1), "stone", lvl + 2)
        lit.put(_r(x - 2, y - 1, 3, 1), "stone", lvl + 1)
        lit.put(_r(x - 3, y + 2, 6, 1), "ink", 0)


def dead_hearth(lit, cx, cy, rng):
    """Погасшее огнище: stone ring, collapsed charred logs, a few dying embers."""
    stone_ring(lit, cx, cy, False, lvl=2)
    inside = ((XX - cx) / 14) ** 2 + ((YY - cy) / 7) ** 2 <= 1
    lit.put(inside, "stone", 1); lit.put(inside & (BAY < 0.3), "ink", 0)
    for (a, b, c, d) in ((-10, 2, 8, -4), (-6, -5, 9, 3), (-11, -2, 4, -10), (2, 4, 12, -6), (-3, 3, 3, -14)):
        m = line_mask(cx + a, cy + b, cx + c, cy + d, 3)
        lit.put(m, "wood", 0)
        lit.put(line_mask(cx + a, cy + b, cx + c, cy + d, 1), "wood", 1)
    for _ in range(9):
        x, y = cx + int(rng.integers(-9, 10)), cy + int(rng.integers(-5, 4))
        put_px(lit, x, y, "red", int(rng.integers(1, 3)), em=True)
    put_px(lit, cx - 2, cy - 1, "fire", 1, em=True); put_px(lit, cx + 3, cy - 3, "fire", 0, em=True)
    stone_ring(lit, cx, cy, True, lvl=2)


def smoke(lit, x0, y0, length, drift, seed, lvl=(3, 4)):
    """Thin grey smoke column drifting right; dithered, not emissive."""
    rng = np.random.default_rng(seed)
    for k in range(length):
        t = k / length
        x = x0 + drift * t ** 1.4 + math.sin(k * 0.21 + seed) * (1.5 + 3 * t)
        w = 1 + int(t * 5)
        for dx in range(-w // 2, w - w // 2):
            xx, yy = int(x + dx), y0 - k
            if 0 <= xx < W and 0 <= yy < H and BAY[yy, xx] < 0.62 - t * 0.45:
                lit.ramp[yy, xx] = rid("stone"); lit.lvl[yy, xx] = lvl[0] if rng.random() < 0.6 else lvl[1]
                lit.em[yy, xx] = False


def pine(lit, x, base, h, seed=0, trunk=7, dark=1, bare=0.56):
    """Сосна (scale.md: 150-190): long bare trunk (bare share of h), flat
    irregular crown of needle clumps; nearly black in the Чёрный бор."""
    rng = np.random.default_rng(seed)
    top = base - h
    cb = base - int(h * bare)                  # crown bottom
    tx = int(x - trunk // 2)
    lit.put(_r(tx, top + 8, trunk, base - top - 8), "fur", 2)
    lit.put(_r(tx, top + 8, 2, base - top - 8), "fur", 3)
    lit.put(_r(tx + trunk - 2, top + 8, 2, base - top - 8), "fur", 1)
    for _ in range(int(h / 9)):                 # bark plates
        yy = int(rng.integers(cb, base - 2))
        lit.put(_r(tx + int(rng.integers(1, trunk - 2)), yy, 2, 2), "fur", 1)
    lit.put(_r(tx - 1, top + 8, 1, base - top - 8), "ink", 0)
    lit.put(_r(tx + trunk, top + 8, 1, base - top - 8), "ink", 0)
    lit.put(_r(tx - 2, base - 2, trunk + 4, 2), "fur", 1)      # root flare
    m = np.zeros((H, W), bool)
    lv = np.zeros((H, W), np.int16)
    for _ in range(int(h / 7)):
        cy = rng.uniform(top + 4, cb)
        rel = (cy - top) / max(1, cb - top)
        cx = x + rng.uniform(-1, 1) * (8 + rel * h * 0.14)
        rx, ry = rng.uniform(6, 11) * (0.6 + rel * 0.6), rng.uniform(3, 5)
        d = ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2
        blob = (d <= 1) & ((d < 0.55) | (BAY < 0.6))
        l = np.where(YY < cy - ry * 0.3, 2, 1)
        m |= blob; lv = np.where(blob, l, lv)
        # branch to the trunk
        lit.put(line_mask(x, cy + 3, cx, cy, 1), "fur", 1)
    lit.put(m, "pine", np.clip(lv - (dark - 1), 0, 3))
    edge = m & ~(np.roll(m, 1, 1) & np.roll(m, -1, 1) & np.roll(m, 1, 0) & np.roll(m, -1, 0))
    lit.put(edge & (BAY < 0.7), "ink", 0)
    return top, base


def inverted_pine(lit, x, base, h, seed=0, trunk=6):
    """Сосна корнями вверх (act1): the crown is buried, branches splay on the
    ground, the trunk goes up and ends in a fan of roots."""
    rng = np.random.default_rng(seed)
    top = base - h
    tx = int(x - trunk // 2)
    lit.put(_r(tx, top + 10, trunk, h - 10), "fur", 2)
    lit.put(_r(tx, top + 10, 2, h - 10), "fur", 3)
    lit.put(_r(tx - 1, top + 10, 1, h - 10), "ink", 0); lit.put(_r(tx + trunk, top + 10, 1, h - 10), "ink", 0)
    # roots fanning out at the top
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.33 + rng.uniform(-0.1, 0.1)
        ln = rng.uniform(14, 26)
        x0, y0 = x + rng.uniform(-2, 2), top + 12
        mx, my = x0 + math.cos(a) * ln * 0.5, y0 + math.sin(a) * ln * 0.5 + 2
        x1, y1 = x0 + math.cos(a) * ln, y0 + math.sin(a) * ln * 0.75
        w = 2 if abs(k - 4) < 3 else 1
        lit.put(line_mask(x0, y0, mx, my, w), "fur", 2); lit.put(line_mask(mx, my, x1, y1, 1), "fur", 2)
        lit.put(line_mask(mx, my - 1, x1, y1 - 1, 1), "ink", 0)
        if rng.random() < 0.6:
            lit.put(line_mask(x1, y1, x1 + rng.uniform(-5, 5), y1 + rng.uniform(-6, -2), 1), "fur", 1)
    lit.put(_r(x - 6, top + 9, 13, 4), "earth", 1)                 # clod of soil still in the roots
    lit.put(_r(x - 4, top + 8, 9, 1), "earth", 2)
    # buried crown: flattened needle mass splayed on the ground
    m = np.zeros((H, W), bool)
    for _ in range(14):
        cx, cy = x + rng.uniform(-18, 18), base - rng.uniform(0, 7)
        d = ((XX - cx) / rng.uniform(5, 9)) ** 2 + ((YY - cy) / rng.uniform(2.5, 4)) ** 2
        m |= (d <= 1) & ((d < 0.5) | (BAY < 0.6))
    lit.put(m, "pine", 1)
    lit.put(m & (YY < base - 4) & (BAY < 0.3), "pine", 2)
    edge = m & ~(np.roll(m, 1, 1) & np.roll(m, -1, 1) & np.roll(m, 1, 0))
    lit.put(edge, "ink", 0)


def fallen_idol(lit, cx, cy, k=1, seed=0, flip=False):
    """Поваленный чур-идол: the idol sprite lying (rotated), blackened, no glow,
    split in two with chips, plus the splintered stump."""
    spr = recolor(SR.idol(), ("wood", "bronze", "fire"), ("fur", "fur", "fur"))
    s = rot_sprite(spr, k)
    if flip:
        for key in ("ramp", "lvl", "em", "mask"):
            s[key] = s[key][::-1, :].copy()
    # split: remove a 2-px gap at ~40% of the length
    gx = int(s["w"] * (0.42 if k == 1 else 0.58))
    for key in ("mask",):
        s[key][:, gx:gx + 2] = False
    G.place(lit, s, (cx, cy))
    rng = np.random.default_rng(seed)
    for _ in range(6):
        x, y = cx - s["w"] // 2 + gx + int(rng.integers(-5, 6)), cy + int(rng.integers(-2, 3))
        lit.put(_r(x, y, 2, 1), "fur", 3)
    return sprite_box(s, (cx, cy))


def stump(lit, x, base, seed=0):
    """Splintered stump of a felled idol (8-10 px)."""
    rng = np.random.default_rng(seed)
    lit.put(_r(x - 4, base - 9, 9, 9), "fur", 2)
    lit.put(_r(x - 4, base - 9, 2, 9), "fur", 3)
    for i in range(9):
        hh = int(rng.integers(0, 4))
        lit.put(_r(x - 4 + i, base - 10 - hh, 1, hh + 1), "fur", 3 if i % 2 else 2)
    lit.put(_r(x - 5, base - 13, 1, 13), "ink", 0); lit.put(_r(x + 5, base - 13, 1, 13), "ink", 0)
    lit.put(_r(x - 5, base, 11, 1), "ink", 0)


# --------------------------------------------------------------------------
# rift (custom: dark inside with stars, Небыль rim) — scale.md §3.4: 88 px
# --------------------------------------------------------------------------
def rift_tear(lit, tx, ty, th=89, hw=12, seed=0, stars=4, halo=5):
    rng = np.random.default_rng(seed)
    t = (ty - YY) / th
    inside = (t >= 0) & (t <= (th - 1) / th)
    half = np.sin(np.clip(t, 0, 1) * math.pi) ** 0.75 * hw
    wob = np.sin(YY * 0.55 + seed) * 1.4 + np.sin(YY * 0.21 + 1 + seed) * 2.0
    cxl = tx + wob * (1 - np.abs(t - 0.5))
    dx = np.abs(XX - cxl)
    lit.put(inside & (dx <= half + halo) & (BAY < 0.45 * (1 - np.abs(t - 0.5))), "nebyl", 2, em=True)
    lit.put(inside & (dx <= half + 1.5), "nebyl", 2, em=True)
    lit.put(inside & (dx <= half + 0.5), "nebyl", 3, em=True)
    core = inside & (dx <= half - 1.0)
    lit.put(core, "nebyl", 1, em=True)                     # pine_dk fringe
    deep = inside & (dx <= half - 2.2)
    lit.put(deep, "ink", 0, em=True)
    lit.put(deep & (dx > half - 3.2) & (BAY < 0.35), "nebyl", 1, em=True)
    # stars inside
    pts = np.argwhere(inside & (dx <= half - 3.5))
    if len(pts):
        idx = rng.choice(len(pts), size=min(stars, len(pts)), replace=False)
        for j, i in enumerate(idx):
            y, x = pts[i]
            put_px(lit, x, y, "nebyl", 4, em=True)
            if j == 0:
                for (ax, ay) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if deep[y + ay, x + ax]:
                        put_px(lit, x + ax, y + ay, "stone", 4, em=True)
    # sparks around the rim
    for _ in range(26):
        yy = int(ty - rng.uniform(4, th - 6))
        side = rng.choice([-1, 1])
        hh = math.sin((ty - yy) / th * math.pi) ** 0.75 * hw
        x = int(tx + side * (hh + rng.uniform(2, 10)))
        put_px(lit, x, yy, "nebyl", int(rng.integers(2, 5)), em=True)
    return dict(inside=inside, half=half, cx=cxl, dx=dx, tx=tx, ty=ty, th=th)


def ground_crack(lit, pts, branches=(), glow="nebyl"):
    c = Canvas(W, H)
    for (a, b), (d, e) in zip(pts, pts[1:]):
        c.line(int(a), int(b), int(d), int(e), 1)
        c.line(int(a), int(b) + 1, int(d), int(e) + 1, 2)
        c.line(int(a) + 1, int(b) - 1, int(d) + 1, int(e) - 1, 3)
    for (a, b, d, e) in branches:
        c.line(int(a), int(b), int(d), int(e), 3)
    lit.put(c.a == 3, "ink", 0)
    lit.put(c.a == 2, glow, 2, em=True)
    lit.put(c.a == 1, glow, 3, em=True)


def snow_up(lit, rng, n, box, avoid=None):
    """Snowflakes 1x1 / 2x1 (birch/linen) drifting UP: a faint trail below."""
    x0, y0, x1, y1 = box
    k = 0
    while k < n:
        x, y = int(rng.integers(x0, x1)), int(rng.integers(y0, y1))
        if avoid is not None and avoid[y, x]:
            continue
        w = 2 if rng.random() < 0.35 else 1
        lit.put(_r(x, y, w, 1), "stone", 7 if rng.random() < 0.5 else 6, em=True)
        if rng.random() < 0.6:
            lit.put(_r(x, y + 2, 1, 1), "stone", 4, em=True)
        k += 1


def snow_into(lit, rng, n, target, box, rmax=230):
    """Snow sucked into the rift: flakes with short streaks pointing at it."""
    x0, y0, x1, y1 = box
    k = 0
    while k < n:
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        d = math.hypot(target[0] - x, target[1] - y)
        if d > rmax or d < 30:
            continue
        ux, uy = (target[0] - x) / d, (target[1] - y) / d
        put_px(lit, x, y, "stone", 7, em=True)
        ln = 2 + int((1 - d / rmax) * 4)
        for j in range(1, ln):
            put_px(lit, x - ux * j, y - uy * j, "stone", 5 if j == 1 else 4, em=True)
        k += 1


def shadow(lit, cx, cy, rx, ry, d=-2):
    G.shadow(lit, cx, cy, rx, ry, d)


def tint(a, cx, cy, r, s, mapping):
    G.tint(a, cx, cy, r, s, mapping)


def noise_fire(lit, cx, by, w, h, seed=0, env=None, avoid=None, hot=1.0, ymin=0):
    """Ragged fire mass: vertically stretched value noise over an envelope;
    levels red -> red_lt -> ember -> flame -> parchment by intensity."""
    nb = pk.value_noise(H * 2, W, 4, seed=seed)
    nb2 = pk.value_noise(H * 2, W, 2, seed=seed + 1)
    yi = np.clip((YY // 3) + 40, 0, 2 * H - 1)
    n = nb[yi, XX] * 0.7 + nb2[np.clip(YY // 2 + 90, 0, 2 * H - 1), XX] * 0.3
    rx = (XX - cx) / w
    ry = (by - YY) / h
    e = np.clip(1 - np.abs(rx) ** 1.6, 0, 1) if env is None else env
    field = e * (1.1 - ry) + (n - 0.5) * 0.9
    m = (ry >= 0) & (ry <= 1.3) & (field > 0.28) & (np.abs(rx) <= 1.2)
    m &= YY >= ymin
    if avoid is not None:
        m &= ~avoid
    lv = np.clip(np.floor((field - 0.28) * 6.5 * hot + BAY * 0.9 - 0.2).astype(int), 0, 4)
    lit.ramp[m] = rid("fire"); lit.lvl[m] = lv[m]; lit.em[m] = True
    return m


def smoke_plume(lit, cx, by, top, w0, w1, drift, seed=0, lvl=(1, 2)):
    """Dense dark smoke column (not emissive): dithered noise blob widening up."""
    nb = pk.value_noise(H, W, 7, seed=seed)
    t = np.clip((by - YY) / max(1, by - top), 0, 1)
    cxl = cx + drift * t ** 1.5 + np.sin(YY * 0.09 + seed) * 4 * t
    hw = w0 + (w1 - w0) * t
    d = np.abs(XX - cxl) / hw
    dens = (1 - d) * 0.9 + (nb - 0.5) * 0.8 - t * 0.25
    m = (YY <= by) & (YY >= top) & (dens > 0.15) & (BAY < np.clip(dens + 0.2, 0, 0.85)) & ~lit.em
    lit.ramp[m] = rid("stone"); lit.lvl[m] = np.where(nb[m] > 0.55, lvl[1], lvl[0]); lit.em[m] = False
    return m


def tint_p(a, cx, cy, r, strength, mapping, protect=None, k=0.3):
    """G.tint with reduced strength on `protect` (characters keep their colours)."""
    d = np.sqrt((XX - cx) ** 2 + ((YY - cy) * 1.5) ** 2) / r
    w = np.clip(1 - d, 0, 1) * strength
    if protect is not None:
        w = np.where(protect, w * k, w)
    lut = np.arange(len(pk.PALETTE), dtype=np.uint8)
    for kk, v in mapping.items():
        lut[C[kk]] = C[v]
    m = BAY < w
    a[m] = lut[a[m]]

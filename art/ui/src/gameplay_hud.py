"""
Gameplay HUD mockup generator — gothic pixel ARPG (Act I).

Native 640x360, exported x3 NEAREST -> 1920x1080.
Run:  python3 gameplay_hud.py            (writes into ../ )

Structure
  build_world()   -> Lit buffers (iso ground, ruins, props, characters)
  lights()        -> banded light field
  draw_*()        -> HUD pieces (each takes Canvas + layout args, reusable)
  main()          -> composition + export
Reusable primitives live in pixelkit.py (palette, Canvas, fonts, widgets,
icons) and sprites.py (material-letter sprite maps).
"""
import os
import math
import numpy as np
from PIL import Image

import pixelkit as pk
from pixelkit import C, Canvas, FONT3x5, FONT5x7
import sprites as SP

W, H = 640, 360
SCALE = 3
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# iso projection: tile 32x16, tile (12,12) under the player's feet
OX, OY = 320, -2


def P(u, v):
    return (OX + (u - v) * 16, OY + (u + v) * 8)


# --------------------------------------------------------------------------
# WORLD
# --------------------------------------------------------------------------
PLAYER_FEET = (320, 192)
CAMPFIRE = (214, 226)
TORCH = (299, 22)
FIREBALL = (382, 158)
SKEL1 = (420, 170)
SKEL2 = (458, 210)
FALLEN = (396, 250)
BRAZIER = (552, 268)


def ground(lit):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    X = (xx + 0.5 - OX) / 16.0
    Y = (yy + 0.5 - OY) / 8.0
    u, v = (X + Y) / 2, (Y - X) / 2
    iu, iv = np.floor(u).astype(int), np.floor(v).astype(int)
    fu, fv = u - iu, v - iv
    b = pk.bayer(H, W)

    # --- grass / earth base ---
    n = pk.value_noise(H, W, 28, seed=3) * 0.7 + pk.value_noise(H, W, 7, seed=4) * 0.3
    n2 = pk.value_noise(H, W, 40, seed=9)
    glev = np.floor(2.4 + n * 2.4 + (b - 0.5) * 0.9).astype(int)
    lit.put(np.ones((H, W), bool), "grass", np.clip(glev, 2, 5))
    # dirt path from camp to bottom-left and toward right
    path = (np.abs((v - 17.5) - (u - 10.5) * 0.15) < 1.4 + n2 * 1.2) & (u < 12) | \
           (np.abs(u - 13 - (v - 12) * 0.1) < 1.1 + n2) & (v > 12)
    earth = path | (n2 < 0.28)
    elev = np.floor(2.5 + n * 2.0 + (b - 0.5) * 0.9).astype(int)
    lit.put(earth, "earth", np.clip(elev, 2, 4))

    # --- flagstone plaza + ruin interior ---
    tu, tv = iu.copy(), iv.copy()
    th = pk.hash2(tu.astype(np.int64), tv.astype(np.int64), 11)
    dplaza = np.maximum(np.abs(tu + 0.5 - 11.0), np.abs(tv + 0.5 - 11.5)) + th * 2.6
    interior = (u < 3.3) & (v < 4.3) & (u > -5) & (v > -5)
    plaza = ((dplaza < 8.0) & (u > 3.9) & (v > 4.9)) | interior
    plaza &= ~((th > 0.93) & ~interior)       # a few missing slabs
    # slabs: some tiles split in two or four
    split = pk.hash2(tu.astype(np.int64), tv.astype(np.int64), 21)
    su = np.where(split > 0.62, (fu * 2) % 1, fu)
    sv = np.where(split > 0.88, (fv * 2) % 1, fv)
    sid = (tu * 4 + (fu * 2).astype(int) * (split > 0.62)) * 1000 + tv * 4 + (fv * 2).astype(int) * (split > 0.88)
    tone = pk.hash2(sid.astype(np.int64), 7, 5)
    base = 4 + (tone > 0.86).astype(int) - (tone < 0.22).astype(int)
    base = np.where(interior, base - 1, base)
    ssz_u = np.where(split > 0.62, 32.0, 16.0)
    ssz_v = np.where(split > 0.88, 32.0, 16.0)
    mortar = (su * ssz_u < 1.0) | (sv * ssz_v < 1.0)
    hi = ((su * ssz_u < 2.0) | (sv * ssz_v < 2.0)) & ~mortar
    lo = (su > 1 - 1.0 / ssz_u) | (sv > 1 - 1.0 / ssz_v)
    grit = (pk.value_noise(H, W, 3, seed=8) > 0.8) & (b < 0.5)
    slev = base + hi.astype(int) - lo.astype(int) - grit.astype(int)
    slev = np.where(mortar, 2, slev)
    lit.put(plaza, "stone", np.clip(slev, 1, 6))
    # moss creeping between slabs at plaza border
    creep = plaza & ~interior & (dplaza > 6.0) & mortar & (b < 0.6)
    lit.put(creep, "grass", 4)
    return u, v


def cracks(lit, rng):
    for _ in range(26):
        x, y = rng.integers(130, 520), rng.integers(80, 300)
        if lit.ramp[y, x] != pk.RAMP_ID["stone"]:
            continue
        for _k in range(rng.integers(4, 9)):
            if 0 <= x < W and 0 <= y < H and lit.ramp[y, x] == pk.RAMP_ID["stone"]:
                lit.lvl[y, x] = 2
            x += rng.choice([-1, 1]); y += rng.choice([0, 1])


def tufts(lit, rng):
    g = pk.RAMP_ID["grass"]
    for _ in range(520):
        x, y = int(rng.integers(2, W - 2)), int(rng.integers(4, H - 2))
        if lit.ramp[y, x] != g:
            continue
        hgt = int(rng.integers(2, 4))
        for k in range(hgt):
            lit.lvl[y - k, x] = 5 if k == hgt - 1 else 4
            lit.ramp[y - k, x] = g
        lit.lvl[y - 1, x - 1] = 4; lit.ramp[y - 1, x - 1] = g
        if rng.random() < 0.6:
            lit.lvl[y - 2, x + 1] = 5; lit.ramp[y - 2, x + 1] = g
        lit.lvl[y + 1, x] = 2


def iso_box(lit, u0, v0, u1, v1, h, ramp="stone", seed=0, top_lvl=5, brick=True, z=0):
    """Iso block on tiles [u0,u1]x[v0,v1], h px tall, raised z px above ground."""
    cv = Canvas(W, H)
    pts = {k: (P(*k)[0], P(*k)[1] - z) for k in [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]}
    up = lambda p: (p[0], p[1] - h)
    a, bq, c, d = pts[(u0, v0)], pts[(u1, v0)], pts[(u1, v1)], pts[(u0, v1)]
    left = cv.mask_poly([d, c, up(c), up(d)])
    right = cv.mask_poly([c, bq, up(bq), up(c)])
    top = cv.mask_poly([up(a), up(bq), up(c), up(d)])
    yy, xx = np.mgrid[0:H, 0:W]
    bb = pk.bayer(H, W)
    for mask, base, (sx, sy, slope) in ((left, 4, (d[0], d[1], 0.5)), (right, 3, (c[0], c[1], -0.5))):
        gy = sy + (xx - sx) * slope
        z = gy - yy
        row = np.floor(z / 5).astype(int)
        lv = np.full((H, W), base)
        if brick:
            bid = (np.floor((xx + row * 5) / 10)).astype(int)
            tone = pk.hash2(bid.astype(np.int64), row.astype(np.int64), seed)
            lv = lv + (tone > 0.75) - (tone < 0.2)
            joint = ((xx + row * 5) % 10 == 0)
            mort = (np.mod(z, 5) < 1) | joint
            lv = np.where(mort, base - 2, lv)
            lv = np.where((np.mod(z, 5) >= 4) & ~mort & (bb < 0.5), lv + 1, lv)
        lit.put(mask, ramp, np.clip(lv, 1, 6))
    lit.put(top, ramp, top_lvl)
    # edges: front vertical corner + top rim highlights
    m = Canvas(W, H)
    m.line(int(c[0]), int(c[1]) - 1, int(c[0]), int(c[1] - h), 1)
    lit.put(m.a == 1, ramp, 5)
    m = Canvas(W, H)
    m.line(int(up(d)[0]), int(up(d)[1]), int(up(c)[0]), int(up(c)[1]), 1)
    m.line(int(up(c)[0]), int(up(c)[1]), int(up(bq)[0]), int(up(bq)[1]), 1)
    lit.put(m.a == 1, ramp, 6)


def walls(lit):
    boxes = []
    ha = [40, 54, 34, 48, 40, 22, 30, 0, 0, 12, 32, 46, 26, 14]
    for k, h in enumerate(ha):
        if h:
            boxes.append((1 + k, 4.3, 2 + k, 5.0, h))
    hb = [58, 36, 48, 26, 32, 14, 0, 0, 10, 22, 8, 4]
    for k, h in enumerate(hb):
        if h:
            boxes.append((3.3, 5 + k, 4.0, 6 + k, h))
    boxes.append((3.0, 4.0, 4.4, 5.4, 74))           # corner pillar
    boxes.append((19.6, 4.2, 20.8, 5.4, 58))         # lone column (right)
    # rubble
    rng = np.random.default_rng(5)
    for (cu, cv_) in ((8.6, 5.6), (9.5, 6.0), (4.6, 11.3), (5.0, 12.2), (14.5, 5.6), (21.2, 6.2), (4.8, 6.4)):
        s = rng.uniform(0.35, 0.6)
        boxes.append((cu, cv_, cu + s, cv_ + s * 0.8, int(rng.integers(3, 7))))
    boxes.sort(key=lambda b: b[0] + b[1] + b[2] + b[3])
    for i, (u0, v0, u1, v1, h) in enumerate(boxes):
        iso_box(lit, u0, v0, u1, v1, h, seed=i)


def shadow(lit, cx, cy, rx, ry, d=-2):
    yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    lit.shade(m & ~lit.em, d)


def place(lit, spr, feet, dx=0):
    """Place sprite so its bottom-centre sits on feet=(x,y)."""
    x = feet[0] - spr["w"] // 2 + dx
    y = feet[1] - spr["h"] + 1
    lit.sprite(spr, x, y)


def flame(lit, cx, by, w, h, seed=0):
    rng = np.random.default_rng(seed)
    fr = pk.RAMP_ID["fire"]
    for dx in range(-w, w + 1):
        t = abs(dx) / (w + 0.5)
        hh = int(h * (1 - t) ** 0.8 * rng.uniform(0.7, 1.1))
        for k in range(hh + 1):
            y = by - k
            rel = k / max(1, h)
            core = (1 - t) * (1 - rel)
            lvl = int(np.clip(core * 6.2 + rng.uniform(-0.6, 0.6), 0, 5))
            if 0 <= y < H:
                lit.ramp[y, cx + dx] = fr; lit.lvl[y, cx + dx] = lvl; lit.em[y, cx + dx] = True
            if k == hh and hh > 1 and rng.random() < 0.5 and y - 1 >= 0:
                lit.ramp[y - 1, cx + dx] = fr; lit.lvl[y - 1, cx + dx] = 0; lit.em[y - 1, cx + dx] = True
    for _ in range(6):   # sparks
        sx, sy = cx + int(rng.integers(-w - 2, w + 3)), by - h - int(rng.integers(2, 12))
        if 0 <= sy < H:
            lit.ramp[sy, sx] = fr; lit.lvl[sy, sx] = int(rng.integers(2, 5)); lit.em[sy, sx] = True


def campfire(lit, S):
    cx, cy = CAMPFIRE
    # stone ring
    for k in range(10):
        a = k / 10 * math.tau
        x, y = int(cx + math.cos(a) * 10), int(cy + math.sin(a) * 5)
        lit.put(_rect(x - 1, y - 1, 3, 2), "stone", 4)
        lit.put(_rect(x - 1, y - 1, 2, 1), "stone", 5)
        lit.put(_rect(x - 1, y + 1, 3, 1), "stone", 1)
    place(lit, S["logs"], (cx, cy + 3))
    # embers bed
    for dx in range(-5, 6):
        lit.ramp[cy, cx + dx] = pk.RAMP_ID["fire"]; lit.lvl[cy, cx + dx] = 2 + (dx % 3 == 0); lit.em[cy, cx + dx] = True
    flame(lit, cx, cy, 5, 16, seed=2)


def _rect(x, y, w, h):
    m = np.zeros((H, W), bool)
    m[max(y, 0):max(y + h, 0), max(x, 0):max(x + w, 0)] = True
    return m


def torch(lit):
    x, y = TORCH
    lit.put(_rect(x - 2, y + 3, 5, 2), "iron", 3)
    lit.put(_rect(x - 1, y + 5, 3, 3), "iron", 2)
    lit.put(_rect(x - 1, y + 1, 3, 2), "wood", 3)
    flame(lit, x, y, 2, 8, seed=5)


def fireball(lit):
    x, y = FIREBALL
    fr = pk.RAMP_ID["fire"]
    # trail back toward player (down-left)
    for k in range(26):
        tx, ty = x - k * 2.0, y + k * 0.45
        r = max(0.6, 3.6 - k * 0.13)
        lvl = max(0, 4 - k // 5)
        m = ((np.arange(W)[None, :] - tx) ** 2 + ((np.arange(H)[:, None] - ty) * 1.3) ** 2) <= r * r
        m &= (pk.bayer(H, W) < max(0.25, 1 - k / 26)) if k > 6 else m
        lit.ramp[m] = fr; lit.lvl[m] = np.maximum(lit.lvl[m] * lit.em[m], lvl); lit.em[m] = True
    for r, l in ((5.2, 2), (4.0, 3), (2.6, 4), (1.2, 5)):
        m = ((np.arange(W)[None, :] - x) ** 2 + (np.arange(H)[:, None] - y) ** 2) <= r * r
        lit.ramp[m] = fr; lit.lvl[m] = l; lit.em[m] = True


def dead_tree(lit, x, y, seed=1):
    rng = np.random.default_rng(seed)
    cv = Canvas(W, H)

    def br(x0, y0, ang, ln, wdt):
        if ln < 3:
            return
        x1, y1 = x0 + math.cos(ang) * ln, y0 - math.sin(ang) * ln
        for o in range(wdt):
            cv.line(int(x0) + o, int(y0), int(x1) + o, int(y1), 1 if o < wdt - 1 or wdt == 1 else 2)
        br(x1, y1, ang + rng.uniform(0.25, 0.6), ln * rng.uniform(0.55, 0.75), max(1, wdt - 1))
        br(x1, y1, ang - rng.uniform(0.25, 0.6), ln * rng.uniform(0.55, 0.75), max(1, wdt - 1))
    br(x, y, math.pi / 2 + 0.08, 34, 4)
    lit.put(cv.a == 1, "wood", 2)
    lit.put(cv.a == 2, "wood", 3)


def blood(lit, x, y, rng, n=14):
    for _ in range(n):
        dx, dy = rng.normal(0, 4), rng.normal(0, 2)
        xx, yy = int(x + dx), int(y + dy)
        if 0 <= xx < W and 0 <= yy < H:
            lit.ramp[yy, xx] = pk.RAMP_ID["red"]; lit.lvl[yy, xx] = int(rng.integers(2, 4))
            lit.em[yy, xx] = False


def build_world(S, target_outline=True):
    lit = pk.Lit(W, H)
    ground(lit)
    rng = np.random.default_rng(7)
    cracks(lit, rng)
    tufts(lit, rng)
    blood(lit, FALLEN[0] - 18, FALLEN[1] + 6, rng)
    blood(lit, 352, 214, rng, 8)
    walls(lit)
    iso_box(lit, 2.8, 3.8, 4.6, 5.6, 5, seed=7, top_lvl=6, brick=False, z=74)      # capitals
    iso_box(lit, 19.45, 4.05, 20.95, 5.55, 4, seed=8, top_lvl=6, brick=False, z=58)
    torch(lit)
    # props (back to front)
    dead_tree(lit, 116, 206, seed=4)
    props = [
        ("tombstone", (36, 214)), ("cross", (78, 232)), ("tombstone", (112, 258)),
        ("cross", (30, 282)), ("tombstone", (590, 286)), ("cross", (604, 240)), ("tombstone", (512, 290)),
        ("bones", (360, 132)), ("skull", (282, 140)), ("bones", (180, 250)),
        ("skull", (452, 268)), ("bones", (520, 196)),
    ]
    for name, f in props:
        place(lit, S[name], f)
    # ground items
    place(lit, S["sword"], (250, 272))
    place(lit, S["goldpile"], (298, 252))
    campfire(lit, S)
    place(lit, S["brazier"], BRAZIER)
    flame(lit, BRAZIER[0], BRAZIER[1] - 11, 4, 10, seed=9)
    # characters with shadows, sorted by y
    chars = [("skeleton", SKEL1, True, True), ("skeleton", SKEL2, False, False),
             ("player", PLAYER_FEET, False, False), ("fallen", FALLEN, False, True)]
    for name, f, tgt, fl in sorted(chars, key=lambda c: c[1][1]):
        spr = S[name] if not fl else pk.flip(S[name])
        shadow(lit, f[0], f[1] - 1, spr["w"] * 0.42, 3.2, -2)
        if tgt and target_outline:
            spr = dict(spr); spr["ramp"] = spr["ramp"].copy(); spr["lvl"] = spr["lvl"].copy()
            o = spr["ramp"] == pk.RAMP_ID["ink"]
            spr["ramp"][o] = pk.RAMP_ID["red"]; spr["lvl"][o] = 4
        place(lit, spr, f)
    fireball(lit)
    return lit


def lights():
    return pk.light_field(W, H, [
        (PLAYER_FEET[0], PLAYER_FEET[1] - 12, 230, 0.75),
        (CAMPFIRE[0], CAMPFIRE[1] - 6, 165, 0.95),
        (TORCH[0], TORCH[1] + 6, 95, 0.7),
        (FIREBALL[0], FIREBALL[1], 70, 0.5),
        (BRAZIER[0], BRAZIER[1] - 14, 110, 0.75),
    ], ambient=0.26, depth=4.2, ysquash=1.45, gamma=0.85)


def warm_tint(a, cx, cy, r, strength):
    """Dithered warm cast of firelight: shift neutrals toward earth/gold."""
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.5) ** 2) / r
    w = np.clip(1 - d, 0, 1) * strength
    lut = np.arange(len(pk.PALETTE), dtype=np.uint8)
    lut[C["shadow"]] = C["earth_dk"]; lut[C["stone_dk"]] = C["earth"]
    lut[C["stone"]] = C["gold_dk"]; lut[C["stone_lt"]] = C["gold"]; lut[C["bone"]] = C["gold_lt"]
    lut[C["moss"]] = C["gold"]; lut[C["moss_lt"]] = C["gold_lt"]
    m = pk.bayer(H, W) < w
    a[m] = lut[a[m]]


# --------------------------------------------------------------------------
# HUD
# --------------------------------------------------------------------------
PANEL_Y = 318


def draw_orb_housing(cv, left=True):
    x0 = 0 if left else W - 86
    pts = [(0, 298), (64, 298), (86, 318), (86, 360), (0, 360)]
    if not left:
        pts = [(W - 1 - x, y) for x, y in pts]
    m = cv.mask_poly(pts)
    tmp = Canvas(W, H)
    pk.stone_fill(tmp, x0, 296, 86, 64, seed=3 if left else 4, base=3, brick=(14, 7))
    cv.a[m] = tmp.a[m]
    # trim along the outline
    p = [(int(x), int(y)) for x, y in pts]
    for i in range(len(p) - 1):
        (xa, ya), (xb, yb) = p[i], p[i + 1]
        if ya == 360 and yb == 360:
            continue
        cv.line(xa, ya - 1, xb, yb - 1, C["ink"])
        cv.line(xa, ya, xb, yb, C["gold_lt"])
        cv.line(xa, ya + 1, xb, yb + 1, C["gold_dk"])


def draw_panel(cv):
    y = PANEL_Y
    pk.stone_fill(cv, 0, y, W, H - y, seed=2, base=3, brick=(18, 7))
    cv.hline(0, y - 2, W, C["ink"])
    cv.hline(0, y - 1, W, C["gold_lt"])
    cv.dither(0, y - 1, W, 1, C["gold"], 0.35)
    cv.hline(0, y, W, C["gold_dk"])
    cv.hline(0, y + 1, W, C["ink"])
    for x in range(100, W - 100, 40):
        pk.rivet(cv, x, y + 2)


def draw_xp(cv, ratio=0.62):
    x, y, w = 96, 322, W - 192
    pk.bar(cv, x, y, w, 5, ratio, ramp="gold", ticks=10)
    # little level tags at the ends
    pk.key_label(cv, x - 13, y - 1, "14", C["gold_hi"])
    pk.key_label(cv, x + w + 2, y - 1, "15", C["stone_lt"])


def draw_skill_slot(cv, x, y, s, icon, key=None, active=False, cooldown=None, mouse=None):
    pk.slot(cv, x, y, s, s, active=active)
    isz = s - 6
    pk.SKILL_ICONS[icon](cv, x + 3, y + 3, isz)
    if cooldown is not None:
        ch = int(isz * cooldown[0])
        cv.remap(x + 3, y + 3, isz, ch, pk.DARKEN3)
        cv.dither(x + 3, y + 3, isz, ch, C["ink"], 0.5)
        cv.hline(x + 3, y + 3 + ch, isz, C["gold"])             # sweep edge
        cv.text_c(x + s // 2 + 1, y + 3 + max(1, (ch - 7) // 2) + 1, cooldown[1], C["gold_hi"], outline=C["ink"])
    if key:
        pk.key_label(cv, x + 2, y + 2, key, C["gold_hi"] if active else C["parchment"])
    if mouse:
        # tiny mouse glyph with highlighted button
        mx, my = x + s - 8, y + s - 10
        cv.rect(mx, my, 7, 9, C["ink"])
        cv.rect(mx + 1, my + 1, 5, 7, C["stone_lt"])
        cv.vline(mx + 3, my + 1, 3, C["ink"]); cv.hline(mx + 1, my + 4, 5, C["ink"])
        if mouse == "L":
            cv.rect(mx + 1, my + 1, 2, 3, C["red_lt"])
        else:
            cv.rect(mx + 4, my + 1, 2, 3, C["red_lt"])
        cv.px(mx + 1, my + 7, C["bone"]); cv.px(mx + 5, my + 7, C["bone"])


def draw_belt(cv, x, y, kinds):
    n = len(kinds)
    s, g = 24, 2
    w = n * s + (n - 1) * g + 6
    # leather strap + iron frame with gold trim
    cv.rect(x, y, w, s + 6, C["ink"])
    cv.rect(x + 1, y + 1, w - 2, s + 4, C["earth_dk"])
    cv.hline(x + 1, y + (s + 6) // 2 - 2, w - 2, C["earth"])
    cv.hline(x + 1, y + (s + 6) // 2 + 2, w - 2, C["earth"])
    pk.gold_trim(cv, x, y, w, s + 6)
    for i, k in enumerate(kinds):
        sx = x + 3 + i * (s + g)
        pk.slot(cv, sx, y + 3, s, s)
        pk.potion(cv, sx + 6, y + 3 + 5, k)
        pk.key_label(cv, sx + s - 6, y + 3 + s - 7, str(i + 1), C["gold_hi"])
    # buckle in the middle top
    bx = x + w // 2 - 4
    cv.rect(bx, y - 4, 9, 6, C["ink"])
    cv.rect(bx + 1, y - 3, 7, 4, C["gold_lt"])
    cv.rect(bx + 3, y - 2, 3, 2, C["ink"])
    cv.px(bx + 1, y - 3, C["gold_hi"])
    return w


def draw_level_badge(cv, x, y, lvl="14"):
    pts = [(x, y), (x + 26, y), (x + 26, y + 18), (x + 13, y + 28), (x, y + 18)]
    cv.poly(pts, C["stone_dk"], outline=C["ink"])
    cv.poly([(x + 2, y + 2), (x + 24, y + 2), (x + 24, y + 17), (x + 13, y + 25), (x + 2, y + 17)], C["red_dk"], outline=C["gold_lt"])
    cv.dither(x + 3, y + 3, 21, 6, C["red"], 0.5)
    cv.text_c(x + 14, y + 4, "LV", C["gold_lt"], font=FONT3x5, shadow=C["ink"])
    cv.text_c(x + 14, y + 11, lvl, C["parchment"], shadow=C["ink"])


def draw_gold(cv, x, y, amount="1284"):
    # coin stack icon + amount on a small plaque
    cv.rect(x, y, 40, 26, C["ink"])
    cv.rect(x + 1, y + 1, 38, 24, C["shadow"])
    pk.bevel(cv, x, y, 40, 26, light=C["stone"], dark=C["ink"], inset=True)
    for k, (cx, cy) in enumerate(((10, 15), (14, 12), (8, 11), (12, 8))):
        cv.rect(x + cx - 3, y + cy, 7, 3, C["gold_dk"])
        cv.rect(x + cx - 3, y + cy - 1, 7, 2, C["gold_lt"])
        cv.px(x + cx - 2, y + cy - 1, C["gold_hi"])
    cv.text(x + 20, y + 5, "G", C["gold_lt"], font=FONT3x5, shadow=None)
    cv.text_r(x + 37, y + 15, amount, C["gold_hi"], font=FONT3x5, shadow=C["ink"])


def draw_orb(cv, S, left=True, fill=0.7, value="312/446"):
    cx = 40 if left else W - 40
    cy = 322
    pk.orb(cv, cx, cy, 27, fill, ramp="red" if left else "blue", seed=1.3 if left else 4.1)
    garg = S["gargoyle_red"] if left else S["gargoyle_blue"]
    g = pk.sprite_to_index(garg)
    cv.blit(g, cx - garg["w"] // 2, cy - 27 - 6 - 11)
    cv.text_c(cx + 1, cy + 9, value, C["parchment"], font=FONT3x5, outline=C["ink"])
    lab = "LIFE" if left else "MANA"
    cv.text_c(cx + 1, cy + 2, lab, C["bone"], font=FONT3x5, outline=C["ink"])


def draw_bottom_hud(cv, S):
    draw_panel(cv)
    draw_orb_housing(cv, True)
    draw_orb_housing(cv, False)
    draw_xp(cv)
    by = 328
    s_big, s_sm = 32, 26
    belt_w = 4 * 24 + 3 * 2 + 6
    total = s_big + 6 + 3 * s_sm + 4 + 10 + belt_w + 10 + 3 * s_sm + 4 + 6 + s_big
    x = W // 2 - total // 2
    draw_skill_slot(cv, x, by, s_big, "sword", mouse="L"); x += s_big + 6
    for i, (ic, kw) in enumerate((("fireball", dict(active=True)), ("icebolt", {}), ("bash", {}))):
        draw_skill_slot(cv, x, by + 3, s_sm, ic, key="F%d" % (i + 1), **kw); x += s_sm + 2
    x += 8
    draw_belt(cv, x, by + 1, ["health", "health", "mana", "rejuv"]); x += belt_w + 10
    for i, (ic, kw) in enumerate((("holyshield", {}), ("teleport", dict(cooldown=(0.55, "3"))), ("whirlwind", {}))):
        draw_skill_slot(cv, x, by + 3, s_sm, ic, key="F%d" % (i + 4), **kw); x += s_sm + 2
    x += 4
    draw_skill_slot(cv, x, by, s_big, "fireball", mouse="R", active=True)
    draw_level_badge(cv, 98, 330)
    draw_gold(cv, W - 98 - 40 + 2, 331)
    draw_orb(cv, S, True, 0.70, "312/446")
    draw_orb(cv, S, False, 0.85, "198/233")


def draw_minimap(cv, lit, light, x, y, w, h):
    # semi-transparent: darken the world under it two bands
    region = np.zeros((H, W), bool); region[y:y + h, x:x + w] = True
    dark = lit.flatten(light, extra=np.where(region, -2.2, 0))
    cv.a[region] = dark[region]
    cv.dither(x, y, w, h, C["ink"], 0.25)
    cx, cy = x + w // 2, y + h // 2 + 6

    def M(u, v):
        return (int(cx + (u - 12) * 3 - (v - 12) * 3), int(cy + (u - 12) * 1.5 + (v - 12) * 1.5))

    def seg(a, b, c=C["bone"]):
        p, q = M(*a), M(*b)
        cv.line(*p, *q, c)
    clip = Canvas(W, H, fill=255)
    saved = cv.a.copy()
    # walls of the ruin (with the gaps)
    seg((1, 4.5), (8, 4.5)); seg((10, 4.5), (15, 4.5))
    seg((3.5, 5), (3.5, 11)); seg((3.5, 13), (3.5, 17))
    seg((20, 4.5), (20.6, 4.5), C["parchment"])
    # plaza outline (dotted)
    for (a, b) in (((4.5, 5), (18, 5)), ((18, 5), (18, 18)), ((18, 18), (4.5, 18))):
        p, q = M(*a), M(*b)
        n = max(abs(q[0] - p[0]), abs(q[1] - p[1]))
        for k in range(0, n, 3):
            cv.px(p[0] + (q[0] - p[0]) * k // n, p[1] + (q[1] - p[1]) * k // n, C["stone_lt"])
    # far structures: crypt to the north-east, cliff edge, river
    seg((22, -6), (30, -6)); seg((30, -6), (30, 2)); seg((22, -6), (22, -1)); seg((22, 1), (22, 2)); seg((22, 2), (30, 2))
    seg((-6, 20), (2, 24), C["stone_lt"]); seg((2, 24), (6, 30), C["stone_lt"]); seg((6, 30), (16, 32), C["stone_lt"])
    for k in range(-8, 40, 2):
        p = M(k, 28 - k * 0.25)
        cv.px(*p, C["blue"])
        cv.px(p[0] + 1, p[1], C["blue_dk"])
    seg((26, 10), (34, 10)); seg((26, 10), (26, 16)); seg((26, 16), (31, 16))
    # restore outside region (lines may spill)
    cv.a[~region] = saved[~region]
    # enemies
    for (ex, ey) in ((5, -3), (8, 0), (4, 6), (-12, 30), (-16, 26)):
        cv.px(cx + ex, cy + ey, C["red_lt"])
    # waypoint (blue diamond) + campfire
    wx, wy = M(8, 18)
    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
        cv.px(wx + dx, wy + dy, C["blue_lt"])
    cv.px(wx, wy, C["parchment"])
    fx, fy = M(10.7, 17.3)
    cv.px(fx, fy, C["ember"]); cv.px(fx, fy - 1, C["flame"])
    # quest marker on crypt entrance
    qx, qy = M(26, -2)
    cv.poly([(qx, qy - 6), (qx + 4, qy - 2), (qx, qy + 2), (qx - 4, qy - 2)], C["gold_lt"], outline=C["ink"])
    cv.vline(qx, qy - 4, 3, C["ink"]); cv.px(qx, qy, C["ink"])
    # player cross
    cv.rect(cx - 2, cy, 5, 1, C["parchment"]); cv.rect(cx, cy - 2, 1, 5, C["parchment"])
    cv.px(cx, cy, C["red_lt"])
    # corner brackets
    for (bx, by, sx, sy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        for k in range(7):
            cv.px(bx + k * sx, by, C["gold_lt"] if k < 5 else C["gold"]); cv.px(bx, by + k * sy, C["gold_lt"] if k < 5 else C["gold"])
        cv.px(bx + sx, by + sy, C["gold_dk"])
    for k in range(10, w - 10, 4):
        cv.px(x + k, y, C["iron"]); cv.px(x + k, y + h - 1, C["iron"])
    for k in range(10, h - 10, 4):
        cv.px(x, y + k, C["iron"]); cv.px(x + w - 1, y + k, C["iron"])


def draw_zone(cv, rx, y):
    cv.text_r(rx, y, "THE ASHEN MOOR", C["gold_lt"], outline=C["ink"])
    cv.text_r(rx, y + 10, "ACT I - MISSION 1 OF 3", C["bone"], font=FONT3x5, outline=C["ink"])


def draw_menu_buttons(cv, x, y):
    s, g = 22, 4
    for i, (ic, key) in enumerate((("character", "C"), ("inventory", "I"), ("skills", "T"), ("map", "M"), ("menu", "ESC"))):
        pk.menu_button(cv, x + i * (s + g), y, s, ic, key)


def draw_target(cv, cx, y, name="BONE WARRIOR", ratio=0.58, sub="UNDEAD - CHAMPION"):
    w = 176
    x = cx - w // 2
    cv.rect(x, y, w, 17, C["ink"])
    pk.stone_fill(cv, x + 1, y + 1, w - 2, 15, seed=6, base=3, brick=(22, 15))
    pk.gold_trim(cv, x + 1, y + 1, w - 2, 15)
    pk.bar(cv, x + 4, y + 4, w - 8, 9, ratio, ramp="red", trim=False)
    cv.text_c(cx + 1, y + 5, name, C["parchment"], outline=C["ink"])
    # skull caps on the ends
    for sx in (x - 6, x + w - 3):
        cv.rect(sx, y + 3, 9, 11, C["ink"])
        cv.rect(sx + 1, y + 4, 7, 6, C["bone"])
        cv.rect(sx + 2, y + 10, 5, 3, C["bone"])
        cv.hline(sx + 1, y + 4, 7, C["parchment"])
        cv.px(sx + 2, y + 6, C["ink"]); cv.px(sx + 3, y + 6, C["ink"]); cv.px(sx + 5, y + 6, C["ink"]); cv.px(sx + 6, y + 6, C["ink"])
        cv.px(sx + 2, y + 7, C["red_lt"]); cv.px(sx + 6, y + 7, C["red_lt"])
        cv.px(sx + 4, y + 8, C["ink"]); cv.px(sx + 3, y + 11, C["ink"]); cv.px(sx + 5, y + 11, C["ink"])
    cv.text_c(cx + 1, y + 20, sub, C["gold_lt"], font=FONT3x5, outline=C["ink"])


def draw_quest(cv, x, y):
    lines = [("THE BURNING CAIRN", C["gold_lt"], FONT5x7),
             ("- SLAY THE BONE WARDEN", C["parchment"], FONT3x5),
             ("- RELIGHT BEACONS  1/3", C["bone"], FONT3x5)]
    cv.remap(x - 3, y - 3, 128, 34, pk.DARKEN2)
    cv.dither(x - 3, y - 3, 128, 34, C["ink"], 0.5)
    cv.vline(x - 3, y - 3, 34, C["gold"])
    cv.text(x + 1, y, "QUEST", C["red_lt"], font=FONT3x5, outline=C["ink"])
    yy = y + 8
    for s, c, f in lines:
        cv.text(x + 1, yy, s, c, font=f, outline=C["ink"])
        yy += f["h"] + 3


def draw_item_labels(cv):
    t = "ETCHED BLADE"
    tw = pk.text_width(t) + 5
    pk.label_box(cv, 250 - tw // 2, 252, t, C["blue_lt"])
    t2 = "86 GOLD"
    tw2 = pk.text_width(t2) + 5
    pk.label_box(cv, 298 - tw2 // 2, 233, t2, C["gold_hi"])


# --------------------------------------------------------------------------
def build_sprites():
    S = SP.build()
    mat_r = dict(SP.MAT); mat_b = dict(SP.MAT)
    mat_b["E"] = ("blue", 5, False, True)
    S["gargoyle_red"] = pk.make_sprite(SP.GARGOYLE, mat_r)
    S["gargoyle_blue"] = pk.make_sprite(SP.GARGOYLE, mat_b)
    return S


_CACHE = {}


def render_world():
    """Lit, tinted world layer + ground item labels (no HUD). Cached."""
    if "world" not in _CACHE:
        S = build_sprites()
        lit = build_world(S)
        L = lights()
        cv = Canvas(W, H)
        cv.a[:] = lit.flatten(L)
        warm_tint(cv.a, CAMPFIRE[0], CAMPFIRE[1] - 4, 75, 0.55)
        warm_tint(cv.a, TORCH[0], TORCH[1] + 6, 40, 0.45)
        warm_tint(cv.a, FIREBALL[0], FIREBALL[1], 30, 0.5)
        warm_tint(cv.a, BRAZIER[0], BRAZIER[1] - 8, 45, 0.45)
        draw_item_labels(cv)
        _CACHE["world"] = (cv.a.copy(), lit, L, S)
    a, lit, L, S = _CACHE["world"]
    return a.copy(), lit, L, S


def compose(shift=0, parts=("minimap", "zone", "buttons", "target", "quest", "bottom"), dim=0):
    """Gameplay screen as a Canvas. shift: horizontal camera offset in px
    (positive moves the world right, used when a side window is open).
    parts: which HUD pieces to draw. dim: darken world by n bands."""
    a, lit, L, S = render_world()
    cv = Canvas(W, H, fill=C["ink"])
    if shift > 0:
        cv.a[:, shift:] = a[:, :W - shift]
    elif shift < 0:
        cv.a[:, :W + shift] = a[:, -shift:]
    else:
        cv.a[:] = a
    if dim:
        cv.remap(0, 0, W, H, {1: pk.DARKEN1, 2: pk.DARKEN2, 3: pk.DARKEN3}[dim])
    if "minimap" in parts:
        draw_minimap(cv, lit, L, 506, 24, 128, 84)
    if "zone" in parts:
        draw_zone(cv, 633, 4)
    if "buttons" in parts:
        draw_menu_buttons(cv, 506, 112)
    if "target" in parts:
        draw_target(cv, W // 2, 4)
    if "quest" in parts:
        draw_quest(cv, 8, 8)
    if "bottom" in parts:
        draw_bottom_hud(cv, S)
    return cv


def export(cv, name):
    """Save native + x3 and verify size/palette."""
    os.makedirs(OUT, exist_ok=True)
    cv.save(os.path.join(OUT, name + "_native.png"))
    big = cv.save(os.path.join(OUT, name + "_1920x1080.png"), scale=SCALE)
    assert big.size == (1920, 1080)
    cols = {tuple(c) for c in np.array(big).reshape(-1, 3)}
    assert cols <= {tuple(c) for c in pk.RGB}, "off-palette colour!"
    print(name, "ok,", len(cols), "colours used")


def main():
    cv = compose()
    export(cv, "mockup_gameplay_hud")
    pk.save_palette(os.path.join(OUT, "palette.png"), os.path.join(OUT, "palette.json"))


if __name__ == "__main__":
    main()

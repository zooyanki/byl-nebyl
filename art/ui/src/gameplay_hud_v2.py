"""
Gameplay HUD mockup v2 — theme «Гардарики» (Northern Rus', XI c., Быль/Небыль).

Native 640x360 -> x3 NEAREST -> 1920x1080. Same HUD layout as v1.
Run:  python3 gameplay_hud_v2.py   (writes ../mockup_gameplay_hud_v2_*.png,
      ../palette_v2.png/.json; v1 files are not touched)

Modules: pixelkit (canvas, lighting, MatCanvas), theme_rus (palette v2,
wood/bronze widgets, ornament, icons), fonts_ru (FONT_RU, FONT_USTAV),
sprites_rus (characters & props).
"""
import os
import math
import numpy as np

import pixelkit as pk
import theme_rus as T
T.activate()
from pixelkit import C, Canvas, FONT3x5, FONT5x7
from fonts_ru import FONT_RU, FONT_USTAV
import sprites_rus as SR
import ui_rus as U

W, H = 640, 360
SCALE = 3
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OX, OY = 320, 13


def P(u, v):
    return (OX + (u - v) * 16, OY + (u + v) * 8)


# Scale standard: /workspace/game/design/scale.md (hero 44 px, door 56, wall 68 ...).
# Camera: hero soles at (320, 178) -> body centre at the centre of the 640x314 field.
PLAYER = (320, 178)
FIRE = (252, 230)          # крада centre (2x2 tiles)
IDOL = (212, 214)          # чур (sprite unchanged, 60 px)
RIFT = (492, 208)          # разлом Небыли
UPYR = (404, 168)
VOLK = (532, 246)
LESHY = (578, 224)
SHORE0, SHORE_K = 142, 0.5  # shoreline parallel to the u axis (ship keel)


def rid(n):
    return pk.RAMP_ID[n]


def water_mask():
    yy, xx = np.mgrid[0:H, 0:W]
    n = pk.value_noise(H, W, 9, seed=31)
    return yy > SHORE0 + SHORE_K * xx + (n - 0.5) * 8


# --------------------------------------------------------------------------
# GROUND
# --------------------------------------------------------------------------
def ground(lit):
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    X = (xx + 0.5 - OX) / 16.0
    Y = (yy + 0.5 - OY) / 8.0
    u, v = (X + Y) / 2, (Y - X) / 2
    b = pk.bayer(H, W)
    n = pk.value_noise(H, W, 26, seed=3) * 0.65 + pk.value_noise(H, W, 6, seed=4) * 0.35
    n2 = pk.value_noise(H, W, 34, seed=9)
    glev = np.floor(2.3 + n * 2.3 + (b - 0.5) * 0.9).astype(int)
    lit.put(np.ones((H, W), bool), "grass", np.clip(glev, 2, 4))
    # trampled clearing + path from the gate to the fire
    d = np.hypot(u - 11.0, (v - 11.6) * 1.1)
    clear = d < 5.4 + n2 * 2.8
    path = (np.abs((u - 10.5) - (v - 2.25) * 0.05) < 1.0 + n2 * 0.9) & (v < 12) & (v > 2)      # from the gate
    path |= (np.abs((v - 15.0) - (u - 9) * -0.9) < 0.8 + n2 * 0.7) & (u < 11) & (u > 4)       # down to the shore
    earth = clear | path
    elev = np.floor(2.2 + n * 1.9 + (b - 0.5) * 0.9).astype(int)
    lit.put(earth, "earth", np.clip(elev, 1, 3))
    # grass creeping into the earth edges
    edge = earth & (n2 + n * 0.3 > 0.78) & (b < 0.5)
    lit.put(edge, "grass", 3)
    # moss patches
    moss = ~earth & (pk.value_noise(H, W, 14, seed=12) > 0.68)
    lit.put(moss, "pine", np.clip(np.floor(2 + n * 2 + b * 0.8).astype(int), 2, 3))
    # water + shore
    wm = water_mask()
    shore = wm & ~np.roll(wm, -3, axis=0)
    lit.put(np.roll(wm, -4, axis=0) & ~wm, "earth", 3)        # wet sand
    ripple = (np.sin(xx * 0.35 + yy * 1.7) + np.sin(xx * 0.11 - yy * 0.9)) > 1.35
    deep = np.clip((yy - (SHORE0 + SHORE_K * xx)) / 60, 0, 1)
    wl = np.floor(3.4 - deep * 1.6 + (b - 0.5) * 0.8).astype(int)
    wl = np.where(ripple, wl + 1, wl)
    lit.put(wm, "sea", np.clip(wl, 1, 5))
    lit.put(shore & (b < 0.6), "birch", 3)
    return wm


def scatter(lit, rng, wm):
    g, e = rid("grass"), rid("earth")
    for _ in range(700):                         # grass tufts
        x, y = int(rng.integers(2, W - 2)), int(rng.integers(4, H - 2))
        if lit.ramp[y, x] != g or wm[y, x]:
            continue
        hgt = int(rng.integers(2, 4))
        for k in range(hgt):
            lit.lvl[y - k, x] = 4 if k == hgt - 1 else 3
        lit.ramp[y - 1, x - 1] = g; lit.lvl[y - 1, x - 1] = 4
        if rng.random() < 0.5:
            lit.ramp[y - 2, x + 1] = g; lit.lvl[y - 2, x + 1] = 5
        lit.lvl[y + 1, x] = 1
    for _ in range(260):                         # fallen birch leaves
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        if wm[y, x]:
            continue
        lit.ramp[y, x] = g; lit.lvl[y, x] = 5
    for _ in range(40):                          # pebbles
        x, y = int(rng.integers(4, W - 4)), int(rng.integers(20, H - 4))
        if wm[y, x]:
            continue
        lit.put(_r(x, y, 3, 2), "stone", 4); lit.put(_r(x, y, 2, 1), "stone", 5); lit.put(_r(x, y + 2, 3, 1), "stone", 1)


def _r(x, y, w, h):
    x, y, w, h = int(round(x)), int(round(y)), int(w), int(h)
    m = np.zeros((H, W), bool)
    m[max(y, 0):max(y + h, 0), max(x, 0):max(x + w, 0)] = True
    return m


# --------------------------------------------------------------------------
# VEGETATION
# --------------------------------------------------------------------------
def spruce(lit, x, base, h, seed=0, dark=0, wk=0.19, trunk=5):
    """Spruce: tiered crown (total width ~0.38 h, scale.md: ель 150 px -> 50-64 wide),
    trunk `trunk` px wide, outline only on the outer silhouette."""
    rng = np.random.default_rng(seed)
    m = np.zeros((H, W), bool)
    lv = np.zeros((H, W), np.int16)
    top = base - h
    tier = max(7, int(h / 13)) + int(rng.integers(0, 3))
    skirt = max(5, int(h * 0.06))               # bare trunk under the lowest branches
    for y in range(max(0, top), min(H, base - skirt)):
        rel = (y - top) / max(1, h - skirt)
        hw = 1 + rel * h * wk
        ph = ((y - top) % tier) / tier
        hw *= 0.55 + 0.45 * ph
        hw += rng.uniform(-1.0, 1.0)
        for xx in range(int(x - hw), int(x + hw) + 1):
            if 0 <= xx < W:
                m[y, xx] = True
                t = (xx - (x - hw)) / max(1, 2 * hw)
                l = 3 if t < 0.3 else (2 if t < 0.72 else 1)
                if ph > 0.82:
                    l -= 1
                if ph < 0.25 and t < 0.6 and rng.random() < 0.5:
                    l += 1
                lv[y, xx] = max(1, min(4, l - dark))
    tx = int(x - trunk // 2)
    lit.put(_r(tx, base - skirt - 2, trunk, skirt + 2), "wood", 2)
    lit.put(_r(tx, base - skirt - 2, 1, skirt + 2), "wood", 3)
    lit.put(_r(tx + trunk - 1, base - skirt - 2, 1, skirt + 2), "wood", 1)
    edge = m & ~(np.roll(m, 1, 1) & np.roll(m, -1, 1) & np.roll(m, 1, 0))
    lit.put(m, "pine", lv)
    lit.put(edge & (lv <= 1), "ink", 0)
    return (top, base)


def birch(lit, x, base, h, seed=0, lean=0.0):
    """White-barked birch (trunk 4 px, black lenticels) with a golden autumn
    crown ~50-60 px wide (scale.md §3.2: берёза 96-128)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    bay = pk.bayer(H, W)
    k_ = h / 60.0
    for _ in range(9):
        k = int(rng.integers(int(h * 0.45), int(h * 0.9)))
        sx = int(x + lean * k); sy = base - k
        d = int(rng.choice([-1, 1])); ln = int(rng.integers(6, 14))
        cv = Canvas(W, H)
        cv.line(sx + 1, sy, sx + 1 + d * ln, sy - ln // 2 - 3, 1)
        lit.put(cv.a == 1, "birch", 2)
    for y in range(base - int(h * 0.92), base):
        k = base - y
        cx = int(round(x + lean * k))
        thin = k > h * 0.72
        cols = ((0, 5), (1, 4), (2, 3)) if thin else ((0, 5), (1, 4), (2, 4), (3, 3))
        for dx, l in cols:
            lit.put(_r(cx + dx, y, 1, 1), "birch", l)
        lit.put(_r(cx - 1, y, 1, 1), "ink", 0); lit.put(_r(cx + len(cols), y, 1, 1), "ink", 0)
        if rng.random() < 0.16:
            lit.put(_r(cx + int(rng.integers(0, 3)), y, 2, 1), "ink", 0)
    crown = np.zeros((H, W), bool)
    lvl = np.zeros((H, W), np.int16)
    for _ in range(46):
        k = rng.uniform(h * 0.42, h * 1.0)
        cx = x + 2 + lean * k + rng.uniform(-1, 1) * h * 0.16 * (1.15 - k / h)
        cy = base - k
        r = rng.uniform(4.5, 7.5) * min(k_, 1.45)
        d = np.hypot(xx - cx, (yy - cy) * 1.25) / r
        blob = (d <= 1) & ((d < 0.6) | (bay < 0.5)) & ~((d < 0.5) & (bay > 0.8))
        crown |= blob
        l = np.where((xx - cx) + (yy - cy) < -r * 0.3, 5, 4)
        l = np.where((xx - cx) + (yy - cy) > r * 0.5, 3, l)
        lvl = np.where(blob, l, lvl)
    gold = pk.value_noise(H, W, 9, seed=seed + 50) > 0.45
    lit.put(crown & gold, "bronze", np.clip(lvl, 2, 5))
    lit.put(crown & ~gold, "grass", np.clip(lvl, 3, 5))
    lit.put(_r(x - 3, base - 1, 9, 1), "earth", 1)


# --------------------------------------------------------------------------
# STRUCTURES
# --------------------------------------------------------------------------
def poly_mask(pts):
    return Canvas(W, H).mask_poly(pts)


def log_face(lit, mask, gy0, gx0, slope, base=3, log=4):
    yy, xx = np.mgrid[0:H, 0:W]
    gy = gy0 + (xx - gx0) * slope
    z = gy - yy
    r = np.mod(z, log)
    lv = np.full((H, W), base)
    lv = np.where(r >= log - 1, base + 1, lv)
    lv = np.where(r < 1, base - 2, lv)
    grain = (pk.hash2(xx // 4, (z // log).astype(np.int64), 3) < 0.25) & (r >= 1) & (r < log - 1)
    lv = np.where(grain, lv - 1, lv)
    lit.put(mask, "wood", np.clip(lv, 1, 5))


def proj(u, v, z=0.0):
    """Iso projection with height (z in screen px)."""
    return (OX + (u - v) * 16, OY + (u + v) * 8 - z)


def _area(pts):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a += x0 * y1 - x1 * y0
    return a / 2


def facing(pts):
    """True if a world polygon listed counter-clockwise seen from outside
    faces the camera (screen winding check)."""
    return _area(pts) < 0


def plane_uv(p0, du, dt):
    """Per-pixel (a, b) coordinates of the screen-space parallelogram
    p0 + a*du + b*dt (used to texture roof slopes along their own axes)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    det = du[0] * dt[1] - du[1] * dt[0]
    rx, ry = xx - p0[0], yy - p0[1]
    a = (rx * dt[1] - ry * dt[0]) / det
    b = (du[0] * ry - du[1] * rx) / det
    return a, b


CABIN = dict(u0=2.0, u1=6.0, v0=8.5, v1=12.5, hh=68, rise=44, ov=0.3, og=0.3)


def cabin(lit, S):
    """Сруб 4x4 tiles in true 2:1 iso (scale.md §3.1): log walls along the tile
    axes, 17 courses of 4 px (окладной венец 4 + этаж 64 = 68), gable end
    facing +u, ridge along u, plank roof rising 44 px (охлупень 112, конёк
    +12). Door opening 1.5 tiles x 56 px above a 4-px threshold log, window
    12x12 at 28-44. Light from the upper left: +v wall lit, +u gable in shade."""
    k = CABIN
    u0, u1, v0, v1, hh = k["u0"], k["u1"], k["v0"], k["v1"], k["hh"]
    vm = (v0 + v1) / 2
    zr = hh + k["rise"]
    slope = k["rise"] / (v1 - vm)                 # px of height per tile
    ov, og = k["ov"], k["og"]
    ze = hh - ov * slope
    walls = [
        ([(u0, v1), (u1, v1)], 3, 0.5),        # +v face (front-left, lit)
        ([(u1, v1), (u1, v0)], 2, -0.5),       # +u face (front-right, gable end)
        ([(u1, v0), (u0, v0)], 2, 0.5),
        ([(u0, v0), (u0, v1)], 2, -0.5),
    ]
    for (a, b), tone, sl in walls:
        pts = [proj(*a), proj(*b), proj(*b, hh - 1), proj(*a, hh - 1)]     # 68 rows incl. both edges
        if not facing(pts):
            continue
        log_face(lit, poly_mask(pts), pts[0][1], pts[0][0], sl, base=tone)
        MEASURE.setdefault("walls", []).append(pts)
    # ---- gable triangle on the +u end ---------------------------------------------------
    g = [proj(u1, v1, hh), proj(u1, v0, hh), proj(u1, vm, zr)]
    if facing([proj(u1, v1, 0), proj(u1, v0, 0), g[1], g[0]]):
        log_face(lit, poly_mask(g), proj(u1, v1)[1], proj(u1, v1)[0], -0.5, base=2)
        # carved «полотенце» board hanging under the ridge
        tx, ty = proj(u1 + og, vm, zr)
        lit.put(_r(tx - 2, ty + 3, 4, 16), "wood", 4); lit.put(_r(tx - 2, ty + 19, 4, 1), "wood", 2)
        for j in range(4):
            lit.put(_r(tx - 1, ty + 6 + j * 3, 2, 1), "wood", 2)
        lit.put(_r(tx - 1, ty + 20, 2, 3), "wood", 4)
    # ---- small волоковое window on the gable-end wall (8x5 at 36-44) --------------------
    def gpar(va, vb, za, zb, u=u1):
        return [proj(u, va, za), proj(u, vb, za), proj(u, vb, zb), proj(u, va, zb)]
    lit.put(poly_mask(gpar(vm + 0.38, vm - 0.38, 34, 46)), "wood", 1)
    lit.put(poly_mask(gpar(vm + 0.25, vm - 0.25, 36, 41)), "fire", 1, em=True)
    # ---- door + window on the lit +v wall -----------------------------------------------
    def wpar(ua, ub, za, zb, v=v1):
        return [proj(ua, v, za), proj(ub, v, za), proj(ub, v, zb), proj(ua, v, zb)]
    da, db = u0 + 0.8, u0 + 0.8 + 23 / 16          # 1.5 tiles = 24 px columns (inclusive raster)
    lit.put(poly_mask(wpar(da - 0.13, db + 0.13, 2, 62)), "wood", 4)            # наличник +2 px
    lit.put(poly_mask(wpar(da - 0.13, db + 0.13, 60, 62)), "wood", 5)
    lit.put(poly_mask(wpar(da, db, 4, 59.5)), "ink", 0)                           # opening 56 px (rows 4..59)
    MEASURE["door"] = wpar(da, db, 4, 59.5)
    lit.put(poly_mask(wpar(da, da + 0.45, 4, 59)), "wood", 1)                   # door leaf, opened inward
    lit.put(poly_mask(wpar(da + 0.06, da + 0.4, 6, 57)), "wood", 2)
    for zz in (14, 46):
        lit.put(poly_mask(wpar(da + 0.06, da + 0.4, zz, zz + 2)), "iron", 2)   # iron straps
    lit.put(poly_mask(wpar(da + 0.6, db - 0.1, 4, 6)), "fire", 0, em=True)      # warm light on the floor
    lit.put(poly_mask(wpar(da - 0.2, db + 0.2, 0, 4)), "wood", 4)               # threshold log (окладной венец)
    lit.put(poly_mask(wpar(da - 0.2, db + 0.2, 0, 1)), "wood", 2)
    # window 12x12 at 28-44 with shutters and a carved «кокошник» above
    wa, wb = u0 + 2.9, u0 + 2.9 + 11 / 16          # glass 12x12 (z 30..41), frame +2 -> 28..44
    lit.put(poly_mask(wpar(wa - 0.13, wb + 0.13, 28, 43)), "wood", 4)
    lit.put(poly_mask(wpar(wa, wb, 30, 41.5)), "fire", 2, em=True)
    MEASURE["window"] = wpar(wa, wb, 30, 41.5)
    lit.put(poly_mask(wpar((wa + wb) / 2 - 0.03, (wa + wb) / 2 + 0.03, 30, 41)), "wood", 2)
    lit.put(poly_mask(wpar(wa, wb, 35, 36)), "wood", 2)
    lit.put(poly_mask(wpar(wa - 0.5, wa - 0.13, 28, 43)), "wood", 3)          # shutters
    lit.put(poly_mask(wpar(wb + 0.13, wb + 0.5, 28, 43)), "wood", 3)
    for (sa, sb) in ((wa - 0.5, wa - 0.13), (wb + 0.13, wb + 0.5)):
        lit.put(poly_mask(wpar(sa + 0.06, sb - 0.06, 30, 32)), "wood", 1)
        lit.put(poly_mask(wpar(sa + 0.06, sb - 0.06, 40, 42)), "wood", 1)
    cx, cy = proj((wa + wb) / 2, v1, 45)
    lit.put(poly_mask([(cx - 10, cy + 1), (cx + 10, cy + 6), (cx + 1, cy - 5)]), "wood", 4)
    lit.put(poly_mask([(cx - 5, cy + 1), (cx + 5, cy + 4), (cx + 1, cy - 1)]), "wood", 2)
    # ---- protruding log ends at the three visible corners (Ø4, every other course) ------
    for z in range(0, hh, 4):
        for (cu, cv_, du_, dv_) in ((u1, v1, 0.22, 0), (u1, v1, 0, 0.22), (u0, v1, -0.22, 0), (u1, v0, 0, -0.22)):
            if ((z // 4) % 2 == 0) == (du_ != 0):
                x, y = proj(cu + du_, cv_ + dv_, z + 2)
                lit.put(_r(x - 2, y - 2, 4, 4), "wood", 4); lit.put(_r(x - 1, y - 1, 2, 2), "wood", 3)
                lit.put(_r(x - 2, y + 2, 4, 1), "wood", 1)
    # ---- roof: back slope (only if it faces the camera), then front slope ---------------
    def slope_face(vr, ve, tone, seed):
        r_a, r_b = proj(u0 - og, vr, zr), proj(u1 + og, vr, zr)
        e_a, e_b = proj(u0 - og, ve, ze), proj(u1 + og, ve, ze)
        pts = [e_a, e_b, r_b, r_a]
        if not facing(pts if ve > vr else pts[::-1]):
            return None
        m = poly_mask(pts)
        a, b = plane_uv(r_a, (r_b[0] - r_a[0], r_b[1] - r_a[1]), (e_a[0] - r_a[0], e_a[1] - r_a[1]))
        nplank = 30
        pi = np.floor(a * nplank)
        fr = a * nplank - pi
        lv = np.full((H, W), tone)
        lv = np.where(pk.hash2(pi.astype(np.int64) + 50, np.zeros_like(pi, dtype=np.int64), seed) < 0.3, tone - 1, lv)
        lv = np.where(fr < 0.2, tone - 2, lv)                  # seams between тёс planks
        lv = np.where(fr > 0.8, tone + 1, lv)
        lv = np.where((np.mod(b * 5, 1) < 0.08) & (b > 0.1), tone - 1, lv)   # plank joints across the slope
        lv = np.where(b > 0.93, tone - 2, lv)                 # eave shadow line
        lv = np.where(b < 0.04, tone + 1, lv)
        lit.put(m, "wood", np.clip(lv, 1, 5))
        return pts
    slope_face(vm, v0 - ov, 2, 11)
    slope_face(vm, v1 + ov, 3, 12)
    c2 = Canvas(W, H)
    ea, eb = proj(u0 - og, v1 + ov, ze), proj(u1 + og, v1 + ov, ze)
    rb = proj(u1 + og, vm, zr)
    bb = proj(u1 + og, v0 - ov, ze)
    for d in (1, 2):
        c2.line(int(ea[0]), int(ea[1]) + d, int(eb[0]), int(eb[1]) + d, 1)
    for d in (0, 1, 2):
        c2.line(int(eb[0]) + d, int(eb[1]), int(rb[0]) + d, int(rb[1]), 2)
        c2.line(int(rb[0]) + d, int(rb[1]), int(bb[0]) + d, int(bb[1]), 2)
    lit.put(c2.a == 1, "wood", 1)
    lit.put(c2.a == 2, "wood", 4)
    # ridge log (охлупень, 4 px) with конёк at the gable end
    c3 = Canvas(W, H)
    ra = proj(u0 - og, vm, zr)
    for d, val in ((-2, 2), (-1, 2), (0, 1), (1, 3)):
        c3.line(int(ra[0]), int(ra[1]) + d, int(rb[0]), int(rb[1]) + d, val)
    lit.put(c3.a == 2, "wood", 4); lit.put(c3.a == 1, "wood", 3); lit.put(c3.a == 3, "wood", 1)
    hs = S["horse"]
    lit.sprite(hs, int(rb[0]) - 4, int(rb[1]) - 1 - hs["h"] + 3)    # top of конёк = ridge + 12
    # ground contact shadow (light from upper left -> shadow to the +u side)
    base = poly_mask([proj(u0, v1 + 0.35), proj(u1 + 0.45, v1 + 0.35), proj(u1 + 0.45, v0), proj(u1, v0), proj(u1, v1), proj(u0, v1)])
    lit.shade(base & ~lit.em & (lit.ramp != rid("wood")), -1)


def cabin_window_light():
    k = CABIN
    return proj(k["u0"] + 3.2, k["v1"] + 0.8, 30)


PAL = dict(v=2.25, u0=-3.0, u1=26.0, gate=(9.4, 11.6))


def palisade(lit, rng, v=None, u0=None, u1=None, gate=None):
    """Тын (scale.md §3.1): logs 80±4 px, 5 px wide, step 0.31 tile, sharpened
    tips 4-6 px, binding at 24 and 64. Gate: posts 96, opening 72 under the
    lintel (lintel at 84-90 with a bronze rosette), torches at 48."""
    v = PAL["v"] if v is None else v
    u0 = PAL["u0"] if u0 is None else u0
    u1 = PAL["u1"] if u1 is None else u1
    gate = PAL["gate"] if gate is None else gate
    torches = []
    u = u0
    while u < u1:
        if gate[0] - 0.2 <= u <= gate[1]:
            u = gate[1] + 0.25
            continue
        x, y = P(u, v)
        x, y = int(x), int(y)
        h = int(79 + rng.integers(-4, 5))         # +1 px tip -> 76..84 visible
        tip = int(rng.integers(4, 7))
        MEASURE.setdefault("pal", []).append((x + 2, y, h + 1))
        for i, l in enumerate((4, 3, 3, 2, 1)):
            top = y - h + int(round(abs(i - 2) / 2 * tip))
            lit.put(_r(x + i, top, 1, y - top), "wood", l)
        lit.put(_r(x + 2, y - h - 1, 1, 1), "wood", 4)
        lit.put(_r(x, y - h + tip, 5, 1), "wood", 1)
        # bark knots
        for _ in range(2):
            ky = y - int(rng.integers(8, h - 10))
            lit.put(_r(x + 1 + int(rng.integers(0, 2)), ky, 2, 1), "wood", 1)
        for bz in (24, 64):          # binding beams / rope
            lit.put(_r(x, y - bz, 5, 2), "wood", 1)
            lit.put(_r(x, y - bz - 1, 5, 1), "bronze", 2)
        u += 0.31
    # gate posts (96) + lintel (84-90)
    for gu in gate:
        x, y = P(gu, v)
        x, y = int(x), int(y)
        for i, l in enumerate((4, 4, 3, 3, 2, 1, 1)):
            lit.put(_r(x - 1 + i, y - 93, 1, 93), "wood", l)
        lit.put(_r(x - 2, y - 96, 10, 3), "wood", 3)          # cap: post top at 96
        lit.put(_r(x - 2, y - 94, 10, 1), "wood", 1)
        for bz in (24, 64):
            lit.put(_r(x - 1, y - bz, 7, 1), "bronze", 2)
        torches.append((x + 2, y - 48))
    (xa, ya), (xb, yb) = P(gate[0], v), P(gate[1], v)
    c = Canvas(W, H)
    for k in range(7):               # lintel beam, top at 90, bottom at 84
        c.line(int(xa) - 4, int(ya) - 90 + k, int(xb) + 9, int(yb) - 90 + k, 1 + (k == 0) + 2 * (k >= 5))
    lit.put(c.a == 1, "wood", 3); lit.put(c.a == 2, "wood", 4); lit.put(c.a == 3, "wood", 1)
    # lower crossbar at 72-75 (clear opening 72) + carved balusters up to the lintel
    c = Canvas(W, H)
    for k in range(4):
        c.line(int(xa) + 5, int(ya) - 76 + k, int(xb) - 1, int(yb) - 76 + k, 1 if k else 2)   # bottom row at 73 -> opening 72
    lit.put(c.a == 1, "wood", 2); lit.put(c.a == 2, "wood", 4)
    n = 7
    for j in range(1, n):
        t = j / n
        bx_, by_ = xa + 5 + (xb - 6 - xa - 5) * t, ya + (yb - ya) * t
        lit.put(_r(bx_, by_ - 84, 2, 8), "wood", 3)
        lit.put(_r(bx_ + 1, by_ - 84, 1, 8), "wood", 1)
    # rosette plaque on the lintel
    mx, my = int((xa + xb) / 2 + 2), int((ya + yb) / 2 - 87)
    rc = Canvas(W, H)
    T.rosette(rc, mx, my, 5, 1)
    yy, xx = np.mgrid[0:H, 0:W]
    lit.put(np.hypot(xx - mx, yy - my) <= 6.5, "bronze", 2)
    lit.put(rc.a == 1, "bronze", 4)
    lit.put((np.hypot(xx - mx, yy - my) > 6.5) & (np.hypot(xx - mx, yy - my) <= 7.4), "ink", 0)
    for (tx, ty) in torches:
        lit.put(_r(tx - 2, ty, 5, 2), "iron", 3)
        lit.put(_r(tx, ty - 4, 1, 4), "wood", 2)
        flame(lit, tx, ty - 4, 2, 9, seed=tx)
    return torches


def flame(lit, cx, by, w, h, seed=0, clip=False):
    rng = np.random.default_rng(seed)
    fr = rid("fire")
    for dx in range(-w, w + 1):
        t = abs(dx) / (w + 0.5)
        hh = int(h * (1 - t) ** 0.8 * rng.uniform(0.7, 1.1))
        if clip:
            hh = h if dx == 0 else min(hh, h - 1)
        for k in range(hh + 1):
            y = by - k
            rel = k / max(1, h)
            core = (1 - t) * (1 - rel)
            lvl = int(np.clip(core * 5.2 + rng.uniform(-0.6, 0.6), 0, 4))
            if 0 <= y < H and 0 <= cx + dx < W:
                lit.ramp[y, cx + dx] = fr; lit.lvl[y, cx + dx] = lvl; lit.em[y, cx + dx] = True
    for _ in range(int(w * 2)):
        sx, sy = cx + int(rng.integers(-w - 2, w + 3)), by - h - int(rng.integers(2, 14))
        if clip:
            sy = by - int(rng.integers(int(h * 0.55), h))
            sx = cx + int(rng.integers(-w - 3, w + 4))
        if 0 <= sy < H and 0 <= sx < W:
            lit.ramp[sy, sx] = fr; lit.lvl[sy, sx] = int(rng.integers(1, 4)); lit.em[sy, sx] = True


def krada(lit):
    """Крада (scale.md §3.3): stone ring Ø2.5 tiles on a 2x2 footprint
    (stones 6x4), log crib 24 px, flame 48 above the wood (72 from the ground)."""
    cx, cy = FIRE
    # stone ring: back half first, front half after the crib
    def stones(front):
        for k in range(16):
            a = k / 16 * math.tau
            if (math.sin(a) > 0) != front:
                continue
            x, y = int(cx + math.cos(a) * 17), int(cy + math.sin(a) * 8.5)
            lit.put(_r(x - 3, y - 2, 6, 4), "stone", 3)
            lit.put(_r(x - 3, y - 2, 5, 1), "stone", 5)
            lit.put(_r(x - 2, y - 1, 3, 1), "stone", 4)
            lit.put(_r(x - 3, y + 2, 6, 1), "ink", 0)
    stones(False)
    # ashes / embers on the ground inside the ring
    yy, xx = np.mgrid[0:H, 0:W]
    inside = ((xx - cx) / 14) ** 2 + ((yy - cy) / 7) ** 2 <= 1
    lit.put(inside & (pk.bayer(H, W) < 0.55), "stone", 1)
    lit.put(inside & (pk.bayer(H, W) < 0.12), "fire", 0, em=True)
    # log crib (колодец из брёвен), 6 courses of 4 px = 24 px; fire glows through the gaps
    a = 0.40                                  # half side in tiles (crib inside the 2x2 stone ring)
    P0 = lambda du, dv, z: (cx + (du - dv) * 16, cy + (du + dv) * 8 - z)
    vol = poly_mask([P0(-a, a, 0), P0(a, a, 0), P0(a, -a, 0), P0(a, -a, 24), P0(-a, -a, 24), P0(-a, a, 24)])
    lit.put(vol, "wood", 0)
    lit.put(vol & (pk.bayer(H, W) < 0.45), "fire", 0, em=True)
    lit.put(vol & (pk.bayer(H, W) < 0.12), "fire", 2, em=True)
    top = poly_mask([P0(-a, a, 24), P0(a, a, 24), P0(a, -a, 24), P0(-a, -a, 24)])
    lit.put(top, "fire", 2, em=True)

    def log(p, q, z):
        c = Canvas(W, H)
        (x0, y0), (x1, y1) = P0(*p, z), P0(*q, z)
        for d, val in ((0, 1), (1, 2), (2, 3)):
            c.line(int(x0), int(y0) - d, int(x1), int(y1) - d, val)
        lit.put(c.a == 3, "wood", 3); lit.put(c.a == 2, "wood", 2); lit.put(c.a == 1, "wood", 1)
        lit.put((c.a == 3) & (pk.bayer(H, W) < 0.3), "fire", 1, em=True)     # embers on the charred top
        for (ex, ey) in ((x0, y0), (x1, y1)):           # sawn log ends
            lit.put(_r(ex - 1, ey - 2, 3, 2), "wood", 4)
    ov = 0.2
    for k in range(6):
        z = 4 * k + 1
        if k % 2 == 0:   # logs along u (back one at -v, front one at +v)
            log((-a - ov, -a), (a + ov, -a), z); log((-a - ov, a), (a + ov, a), z)
        else:            # logs along v
            log((-a, -a - ov), (-a, a + ov), z); log((a, -a - ov), (a, a + ov), z)
    flame(lit, cx, cy - 24, 9, 48, seed=2, clip=True)
    flame(lit, cx - 6, cy - 23, 4, 28, seed=5, clip=True)
    flame(lit, cx + 6, cy - 23, 4, 32, seed=6, clip=True)
    stones(True)


SHIP = dict(uc=9.19, vs=21.44, L=12.0, B=1.25, zg=28, sheer=40)


def ship(lit, S):
    """Ладья (scale.md §3.3): 12 tiles along the u axis, beam 2.5 tiles, side
    28 px at midships, ends ~68 (sheer 40), змей head on the bow stem up to 84,
    mast 150 with the yard at 132, striped sail 4 tiles x 72 (z 60-132) set
    across the hull, 13 shields Ø14 on the near gunwale. Bow up-left."""
    k = SHIP
    uc, vs, L, B = k["uc"], k["vs"], k["L"], k["B"]
    ua = uc - L / 2
    N = 72
    ss = np.linspace(0, 1, N + 1)

    def beam(s):
        return B * max(0.0, math.sin(math.pi * s)) ** 0.7

    def zg(s):
        return k["zg"] + k["sheer"] * abs(2 * s - 1) ** 3

    def U(s):
        return ua + L * s
    near = [proj(U(s), vs + beam(s), zg(s)) for s in ss]
    far = [proj(U(s), vs - beam(s), zg(s)) for s in ss]

    def beam_w(s):
        return B * 0.8 * max(0.0, math.sin(math.pi * (0.1 + 0.8 * s))) ** 0.7
    wl = [proj(U(0.1 + 0.8 * s), vs + beam_w(s), 0) for s in ss]
    # interior first: far inner side + floor
    inner = poly_mask(far + near[::-1])
    lit.put(inner, "wood", 1)
    for i in range(N):
        q = [far[i], far[i + 1], proj(U(ss[i + 1]), vs - beam(ss[i + 1]) * 0.55, zg(ss[i + 1]) - 16),
             proj(U(ss[i]), vs - beam(ss[i]) * 0.55, zg(ss[i]) - 16)]
        lit.put(poly_mask(q) & inner, "wood", 2)
    c = Canvas(W, H)
    for j in range(1, 4):                   # strake lines on the far inner side
        pts = [proj(U(s), vs - beam(s) * (1 - 0.15 * j), zg(s) - 4 * j) for s in ss]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            c.line(int(x0), int(y0), int(x1), int(y1), 2)
    for s in np.linspace(0.16, 0.84, 11):   # thwarts (rowing benches)
        a, b = proj(U(s), vs - beam(s) * 0.92, zg(s) - 8), proj(U(s), vs + beam(s) * 0.92, zg(s) - 8)
        c.line(int(a[0]), int(a[1]), int(b[0]), int(b[1]), 1)
        c.line(int(a[0]), int(a[1]) + 1, int(b[0]), int(b[1]) + 1, 3)
    lit.put((c.a == 2) & inner, "wood", 1)
    lit.put((c.a == 1) & inner, "wood", 4)
    lit.put((c.a == 3) & inner, "wood", 2)
    # chest / cargo in the hold
    for s, col in ((0.3, "red"), (0.62, "wood")):
        x, y = proj(U(s), vs, zg(s) - 12)
        lit.put(_r(x - 4, y - 3, 8, 5), col, 2); lit.put(_r(x - 4, y - 3, 8, 1), col, 3)
    # near hull side: 7 clinker strakes from the waterline up to the gunwale
    nst = 7

    def pt(idx, t):
        return (wl[idx][0] + (near[idx][0] - wl[idx][0]) * t, wl[idx][1] + (near[idx][1] - wl[idx][1]) * t)
    for i in range(N):
        for j in range(nst):
            t0, t1 = j / nst, (j + 1) / nst
            q = [pt(i, t0), pt(i + 1, t0), pt(i + 1, t1), pt(i, t1)]
            lit.put(poly_mask(q), "wood", 3 if j >= 3 else 2)
    c = Canvas(W, H)
    for j in range(1, nst + 1):
        t = j / nst
        pts = [pt(i, t) for i in range(N + 1)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            c.line(int(x0), int(y0), int(x1), int(y1), 1 if j < nst else 2)
            if j < nst:
                c.line(int(x0), int(y0) - 1, int(x1), int(y1) - 1, 3)
    lit.put(c.a == 3, "wood", 4)
    lit.put(c.a == 1, "wood", 1)
    lit.put(c.a == 2, "wood", 4)
    # rivet dots along the strakes
    for j in range(1, nst):
        for i in range(2, N - 1, 3):
            x, y = pt(i, j / nst)
            lit.put(_r(x, y + 1, 1, 1), "bronze", 2)
    # waterline foam + reflection
    b = pk.bayer(H, W)
    c = Canvas(W, H)
    for (x0, y0), (x1, y1) in zip(wl, wl[1:]):
        c.line(int(x0), int(y0) + 1, int(x1), int(y1) + 1, 1)
        for d in (3, 5, 7):
            c.line(int(x0), int(y0) + d, int(x1), int(y1) + d, 2)
    lit.put((c.a == 1) & (b < 0.75), "birch", 4)
    lit.put((c.a == 2) & (b < 0.4), "wood", 1)
    # oars resting in the water (2 tiles), between the shields
    c = Canvas(W, H)
    for s in np.linspace(0.2, 0.8, 6):
        x0, y0 = proj(U(s + 0.02), vs + beam(s), zg(s) - 10)
        x1, y1 = proj(U(s + 0.06), vs + beam(s) + 2.0, 0)
        c.line(int(x0), int(y0), int(x1), int(y1), 1)
        c.line(int(x1) - 2, int(y1), int(x1) + 1, int(y1) + 1, 2)
    lit.put(c.a == 1, "wood", 3); lit.put(c.a == 2, "wood", 4)
    # shields hung on the near gunwale: Ø14 (scale.md: same as the hero's), 13 per side
    yy, xx = np.mgrid[0:H, 0:W]
    for n, s in enumerate(np.linspace(0.13, 0.87, 13)):
        x, y = proj(U(s), vs + beam(s) + 0.08, zg(s) - 7)
        r = 6.6
        d = np.hypot((xx - x) * 0.95, (yy - y))
        a = np.arctan2(yy - y, xx - x)
        m = d <= r
        sect = (((a + math.pi) / (math.pi / 4)).astype(int) % 2) == 0
        col = ("red", "birch") if n % 3 != 2 else ("blue", "birch")
        lit.put(m & sect, col[0], 2); lit.put(m & ~sect, col[1], 4)
        lit.put(m & (d > r - 1.2), "bronze", 3); lit.put(d <= 1.6, "bronze", 5)
        lit.put((d > r) & (d <= r + 0.9), "ink", 0)
    # gunwale rail (2 px)
    c = Canvas(W, H)
    for (x0, y0), (x1, y1) in zip(near, near[1:]):
        c.line(int(x0), int(y0), int(x1), int(y1), 1)
        c.line(int(x0), int(y0) + 1, int(x1), int(y1) + 1, 3)
    for (x0, y0), (x1, y1) in zip(far, far[1:]):
        c.line(int(x0), int(y0), int(x1), int(y1), 2)
    lit.put(c.a == 1, "wood", 4); lit.put(c.a == 3, "wood", 2); lit.put(c.a == 2, "wood", 3)
    # stern post: rises to 64 then curls back inboard (top ~80)
    c = Canvas(W, H)
    pts = [proj(U(1.0 + 0.004 * t), vs, zg(1.0) - 6 + t * 1.4) for t in range(9)]
    cx_, cy_ = pts[-1]
    for t in range(1, 24):
        ang = t / 23 * 4.0
        rr = 7.0 * (1 - t / 34)
        pts.append((cx_ - rr + math.cos(ang) * rr, cy_ - math.sin(ang) * rr))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for d in (0, 1):
            c.line(int(x0) + d, int(y0), int(x1) + d, int(y1), 1)
        c.line(int(x0) + 2, int(y0), int(x1) + 2, int(y1), 2)
    lit.put(c.a == 2, "wood", 2); lit.put(c.a == 1, "wood", 4)
    # bow: змей head; its neck emerges from the stem, head top at 84 above the water
    bx, by_ = proj(U(0.0), vs, 0)
    pr = S["prow_big"]
    lit.sprite(pr, int(bx) - 25, int(by_) - 85)
    # mast (150 above the water) + yard at 132 + sail 4 tiles x 72 (z 60-132)
    mx, my = proj(uc, vs, 0)
    mtop = my - 150
    lit.put(_r(int(mx) - 1, int(mtop), 3, int(my - 20 - mtop)), "wood", 3)
    lit.put(_r(int(mx) + 1, int(mtop), 1, int(my - 20 - mtop)), "wood", 1)
    lit.put(_r(int(mx) - 1, int(mtop), 1, int(my - 20 - mtop)), "wood", 4)
    sw = 2.0
    za, zb = 60, 132
    corners = [proj(uc + 0.05, vs + sw, za), proj(uc + 0.05, vs - sw, za), proj(uc, vs - sw, zb), proj(uc, vs + sw, zb)]
    sail = poly_mask(corners)
    a_, b_ = plane_uv(corners[3], (corners[2][0] - corners[3][0], corners[2][1] - corners[3][1]),
                      (corners[0][0] - corners[3][0], corners[0][1] - corners[3][1]))
    stripe = np.mod(np.floor(a_ * 9), 2) == 0
    tone = np.where(a_ < 0.5, 3, 2)
    tone = np.where(b_ > 0.88, tone - 1, tone)
    tone = np.where((b_ > 0.3) & (b_ < 0.36), tone - 1, tone)          # reef seam
    lit.put(sail & stripe, "red", tone); lit.put(sail & ~stripe, "birch", tone + 1)
    edge = sail & ~(np.roll(sail, 1, 0) & np.roll(sail, -1, 0) & np.roll(sail, 1, 1) & np.roll(sail, -1, 1))
    lit.put(edge, "ink", 0)
    c = Canvas(W, H)
    ya, yb = proj(uc, vs + sw + 0.2, zb + 1), proj(uc, vs - sw - 0.2, zb + 1)
    for d in (0, 1, 2):
        c.line(int(ya[0]), int(ya[1]) - d, int(yb[0]), int(yb[1]) - d, 1)          # yard
    for s_, side in ((0.06, 1), (0.94, 1), (0.3, -1), (0.7, -1), (0.36, 1), (0.64, 1)):  # shrouds / stays
        gx, gy = proj(U(s_), vs + side * beam(s_), zg(s_))
        c.line(int(mx), int(mtop) + 3, int(gx), int(gy), 2)
    for side in (1, -1):                    # sheets from the lower sail corners
        sx, sy = proj(uc + 0.05, vs + side * sw, za)
        gx, gy = proj(uc + side * 1.6, vs + side * beam(0.5 + side * 0.13), zg(0.5))
        c.line(int(sx), int(sy), int(gx), int(gy), 2)
    lit.put((c.a == 2) & ~sail, "wood", 1); lit.put(c.a == 1, "wood", 3)
    lit.put(_r(int(mx) - 2, int(mtop), 5, 3), "bronze", 4)              # vane (флюгер) at the mast top
    lit.put(_r(int(mx) + 2, int(mtop) + 1, 5, 3), "bronze", 3)


def rift(lit, rng):
    """Crack of Небыль (scale.md §3.4): ground fissure within ~5 tiles, vertical
    tear 88 px (2 hero heights), motes + corrupted ground."""
    cx, cy = RIFT
    pts = [(cx - 46, cy + 16), (cx - 26, cy + 8), (cx - 13, cy + 10), (cx, cy), (cx + 15, cy - 4), (cx + 29, cy - 12), (cx + 44, cy - 15)]
    c = Canvas(W, H)
    for (a, b), (d, e) in zip(pts, pts[1:]):
        c.line(a, b, d, e, 1)
        c.line(a, b + 1, d, e + 1, 2)
        c.line(a + 1, b - 1, d + 1, e - 1, 3)
    for (a, b, d, e) in ((cx - 13, cy + 10, cx - 20, cy + 22), (cx + 15, cy - 4, cx + 22, cy + 9), (cx, cy, cx - 7, cy - 9),
                         (cx - 26, cy + 8, cx - 34, cy + 2)):
        c.line(a, b, d, e, 3)
    yy, xx = np.mgrid[0:H, 0:W]
    dd = np.hypot(xx - cx, (yy - cy) * 2.0)
    corrupt = (dd < 60) & (pk.bayer(H, W) < np.clip(1 - dd / 60, 0, 1) * 0.8) & ~lit.em
    lit.put(corrupt & (lit.ramp == rid("grass")), "nebyl", 1)
    lit.put(corrupt & (lit.ramp == rid("earth")), "stone", 2)
    lit.put(c.a == 3, "nebyl", 2, em=True)
    lit.put(c.a == 2, "nebyl", 3, em=True)
    lit.put(c.a == 1, "nebyl", 4, em=True)
    # vertical tear in the air: 88 px from the ground
    tx, ty, th = cx + 2, cy, 89
    t = (ty - yy) / th
    inside = (t >= 0) & (t <= (th - 1) / th)
    half = np.sin(np.clip(t, 0, 1) * math.pi) ** 0.8 * 11
    wob = np.sin(yy * 0.6) * 1.6 + np.sin(yy * 0.23 + 1) * 2.2
    dx_ = np.abs(xx - tx - wob * (1 - np.abs(t - 0.5)))
    halo = inside & (dx_ <= half + 5) & (pk.bayer(H, W) < 0.5)
    lit.put(halo, "nebyl", 2, em=True)
    lit.put(inside & (dx_ <= half + 1), "nebyl", 2, em=True)
    lit.put(inside & (dx_ <= half), "nebyl", 3, em=True)
    lit.put(inside & (dx_ <= half * 0.45), "nebyl", 4, em=True)
    lit.put(inside & (dx_ <= half * 0.45) & (np.mod(yy, 5) == 0), "nebyl", 3, em=True)
    lit.put(inside & (dx_ <= half * 0.15), "ink", 0)
    for _ in range(90):
        x = int(cx + rng.normal(0, 20)); y = int(cy - abs(rng.normal(0, 18)) - 2)
        lit.put(_r(x, y, 1, 1), "nebyl", int(rng.integers(2, 5)), em=True)
    for _ in range(8):   # wisps
        x = int(cx + rng.normal(0, 18)); y0 = int(cy + rng.normal(0, 4))
        for k in range(int(rng.integers(8, 20))):
            if 0 <= y0 - k < H and 0 <= x < W and pk.bayer(H, W)[y0 - k, x] < 0.6:
                lit.put(_r(x + int(math.sin(k * 0.6) * 1.5), y0 - k, 1, 1), "nebyl", 2, em=True)


def swing(lit):
    """Sword trail: radius 20, centre 26 px above the soles (scale.md §5.1)."""
    cx, cy = PLAYER[0] + 5, PLAYER[1] - 26
    for j in range(80):
        a = -1.25 + j / 80 * 1.9
        for rr, l in ((20, 3), (21, 5), (22, 4), (23, 3)):
            if j < 12 and rr == 23:
                continue
            x, y = int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr * 0.8)
            if (j > 50 or rr != 20) and pk.bayer(H, W)[y, x] < 0.25 + j / 80:
                lit.put(_r(x, y, 1, 1), "birch", l, em=True)


def shadow(lit, cx, cy, rx, ry, d=-2):
    yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
    lit.shade(m & ~lit.em, d)


def place(lit, spr, feet, outline_ramp=None, remap=None):
    """Place a sprite by its pivot (characters: frame pivot, soles on the
    pivot row). Props without a pivot: bottom-centre on `feet`."""
    if outline_ramp or remap:
        spr = dict(spr); spr["ramp"] = spr["ramp"].copy(); spr["lvl"] = spr["lvl"].copy()
        if remap:
            for a, b in remap.items():
                spr["ramp"][spr["ramp"] == rid(a)] = rid(b)
        if outline_ramp:
            o = spr["ramp"] == rid("ink")
            spr["ramp"][o] = rid(outline_ramp[0]); spr["lvl"][o] = outline_ramp[1]
    if "pivot" in spr:
        lit.sprite(spr, feet[0] - spr["pivot"][0], feet[1] - spr["pivot"][1])
    else:
        lit.sprite(spr, feet[0] - spr["w"] // 2, feet[1] - spr["h"] + 1)


def silhouette_w(spr):
    cols = np.where(spr["mask"].any(0))[0]
    return cols.max() - cols.min() + 1


# positions of everything the measuring script reports
MEASURE = {}

SWORD_G, SILVER_G, SHIELD_G = (316, 262), (372, 276), (392, 232)
ELITE = {"upyr": False}
COLD = {"ghoul": "sea", "wood": "fur"}      # «Матёрый» cold tint (GDD §5.3)


def build_world():
    S = SR.build()
    lit = pk.Lit(W, H)
    rng = np.random.default_rng(7)
    wm = ground(lit)
    scatter(lit, rng, wm)
    # forest beyond the palisade: spruces 140-190 (tops peek above the 80-px тын)
    for k, u in enumerate(np.arange(-2, 30, 1.6)):
        x, y = P(u, -0.2 - (k % 3) * 0.7)
        h = int(rng.integers(140, 191))
        spruce(lit, int(x + rng.integers(-5, 6)), int(y), h, seed=k, dark=1)
    torches = palisade(lit, rng)
    # left forest 130-170 (crowns run off the top edge / under the quest tracker)
    for (x, y, h, s) in ((110, 96, 134, 44), (40, 112, 150, 41), (80, 136, 142, 42), (12, 134, 168, 43)):
        spruce(lit, x, y, h, seed=s)
        MEASURE.setdefault("spruce_left", []).append(h)
    birch(lit, 60, 162, 112, seed=3, lean=0.04)
    birch(lit, 38, 150, 102, seed=4, lean=-0.05)
    MEASURE["birch"] = [112, 102]
    cabin(lit, S)
    birch(lit, 306, 112, 120, seed=5, lean=0.03)
    MEASURE["birch"].append(120)
    ship(lit, S)
    krada(lit)
    shadow(lit, IDOL[0], IDOL[1], 9, 3)
    place(lit, S["idol"], IDOL)
    rift(lit, rng)
    # ground items, debris (loot sprites unchanged, scale.md §3.4)
    place(lit, S["sword"], SWORD_G)
    place(lit, S["silver"], SILVER_G)
    place(lit, S["shield"], SHIELD_G)
    for (x, y) in ((436, 214), (470, 236), (556, 264), (452, 180)):
        place(lit, S["skull"], (x, y))
    # characters sorted by pivot y; shadows: ellipse 0.8 x silhouette width, 6-7 px tall
    chars = [("upyr", UPYR, ("red", 3)), ("hero", PLAYER, None), ("leshy", LESHY, None), ("volkolak", VOLK, None)]
    for name, f, ol in sorted(chars, key=lambda c: c[1][1]):
        spr = S[name]
        sw = 18 if name == "hero" else silhouette_w(spr) * 0.8
        shadow(lit, f[0], f[1], sw / 2, 3.5 if name != "upyr" else 3, -2)
        remap = COLD if ((ELITE["upyr"] and name == "upyr") or name == "leshy") else None
        place(lit, spr, f, ol, remap=remap)
    swing(lit)
    # foreground right spruce 220-260 (cut by the frame edge, as intended)
    spruce(lit, 640, 334, 244, seed=77, wk=0.2, trunk=6)
    MEASURE["spruce_fg"] = 244
    return lit, torches, S


def lights(torches):
    src = [(PLAYER[0], PLAYER[1] - 20, 230, 0.6), (FIRE[0], FIRE[1] - 36, 190, 0.95),
           (RIFT[0], RIFT[1] - 40, 160, 0.85), (cabin_window_light()[0], cabin_window_light()[1], 60, 0.45),
           (60, 200, 200, 0.28), (590, 210, 200, 0.3), (330, 40, 260, 0.2)]
    for (x, y) in torches:
        src.append((x, y, 90, 0.6))
    return pk.light_field(W, H, src, ambient=0.46, depth=3.4, ysquash=1.4, gamma=0.85)


def tint(a, cx, cy, r, strength, mapping):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.5) ** 2) / r
    w = np.clip(1 - d, 0, 1) * strength
    lut = np.arange(len(pk.PALETTE), dtype=np.uint8)
    for k, v in mapping.items():
        lut[C[k]] = C[v]
    m = pk.bayer(H, W) < w
    a[m] = lut[a[m]]


WARM = {"slate_dk": "wood_dk", "slate": "wood", "slate_lt": "wood_md", "mist": "wood_lt", "birch": "bronze_lt",
        "moss": "bronze", "moss_lt": "bronze_lt", "pine": "wood", "sea": "wood_md", "sea_dk": "wood"}
EERIE = {"slate_dk": "pine_dk", "slate": "nebyl_dk", "slate_lt": "nebyl_dk", "mist": "nebyl", "wood": "pine",
         "wood_md": "moss", "wood_lt": "moss_lt", "moss": "nebyl_dk", "moss_lt": "nebyl", "birch": "nebyl",
         "red": "nebyl_dk"}


_CACHE = {}


def render_world():
    if "w" not in _CACHE:
        lit, torches, S = build_world()
        L = lights(torches)
        a = lit.flatten(L)
        tint(a, FIRE[0], FIRE[1] - 24, 100, 0.6, WARM)
        for (x, y) in torches:
            tint(a, x, y, 36, 0.5, WARM)
        tint(a, RIFT[0], RIFT[1] - 36, 105, 0.5, EERIE)
        cv = Canvas(W, H); cv.a[:] = a
        T.label_ru(cv, SWORD_G[0], SWORD_G[1] - 22, "Калёный меч сокола", C["blue_lt"])
        T.label_ru(cv, SILVER_G[0], SILVER_G[1] - 20, "86 сер.", C["birch"])          # GDD v1.4 §10.1, A13
        _CACHE["w"] = (cv.a.copy(), lit, L, S)
    a, lit, L, S = _CACHE["w"]
    return a.copy(), lit, L, S


# --------------------------------------------------------------------------
# HUD
# --------------------------------------------------------------------------
PANEL_Y = 318

# Hero state in mission 1 (GDD §12.1.1 A3, §3.3, §3.5): level 4, XP 1 700 of 1 120 -> 2 250.
HUD = dict(level=4, life=(95, 102), yar=(50, 58), silver=284, xp=(1700, 1120, 2250), free_points=5)


def draw_panel(cv):
    T.wood_planks(cv, 0, PANEL_Y, W, H - PANEL_Y, seed=2, plank=7, dark=True)
    cv.hline(0, PANEL_Y - 4, W, C["ink"])
    T.rope(cv, 0, PANEL_Y - 3, W)
    cv.hline(0, PANEL_Y, W, C["ink"])
    for x in range(100, W - 100, 36):
        T.nail(cv, x, PANEL_Y + 2)


def draw_housing(cv, left=True):
    pts = [(0, 294), (62, 294), (88, 316), (88, 360), (0, 360)]
    if not left:
        pts = [(W - 1 - x, y) for x, y in pts]
    m = cv.mask_poly(pts)
    tmp = Canvas(W, H)
    T.wood_planks(tmp, 0 if left else W - 89, 292, 89, 68, seed=5 if left else 6, plank=68, vertical=True, dark=True)
    T.wood_planks(tmp, 0 if left else W - 89, 292, 89, 68, seed=5 if left else 6, plank=10, vertical=True, dark=True)
    cv.a[m] = tmp.a[m]
    p = [(int(x), int(y)) for x, y in pts]
    for i in range(len(p) - 1):
        (xa, ya), (xb, yb) = p[i], p[i + 1]
        if ya == 360 and yb == 360:
            continue
        cv.line(xa, ya - 1, xb, yb - 1, C["ink"])
        cv.line(xa, ya, xb, yb, C["bronze_lt"])
        cv.line(xa, ya + 1, xb, yb + 1, C["bronze"])
        cv.line(xa, ya + 2, xb, yb + 2, C["ink"])
    # carved interlace strip under the housing top edge
    x0 = 2 if left else W - 62
    T.interlace(cv, x0, 297, 60, 9, period=12)


def draw_orb(cv, S, left=True, fill=0.7, value="312/446"):
    cx, cy, r = (40 if left else W - 40), 322, 27
    T.orb_v2(cv, cx, cy, r, fill, "life" if left else "mana", seed=1.3 if left else 4.1)
    head = T.serpent_head(face_right=left, eye="fire" if left else "blue")
    idx = pk.sprite_to_index(head)
    hx = cx - 14 if left else cx - head["w"] + 14
    cv.blit(idx, hx, cy - r - 6 - 22)
    # tail tip curling on the other side of the ring
    tx = cx + 22 if left else cx - 22
    for k, (dx, dy) in enumerate(((0, 0), (1, -1), (2, -2), (2, -3), (1, -4))):
        xx = tx + (dx if left else -dx)
        cv.px(xx, cy - 22 + dy, C["bronze_lt"] if k % 2 else C["bronze"])
        cv.px(xx + (1 if left else -1), cy - 22 + dy, C["ink"])
    T.text_ru(cv, cx + 1, cy + 1, "Жизнь" if left else "Ярь", C["birch"], align="c")
    T.text_ru(cv, cx + 1, cy + 10, value, C["linen"], align="c")


def draw_xp(cv, ratio=None):
    x, y, w = 96, 322, W - 192
    xp, a, b = HUD["xp"]
    ratio = (xp - a) / (b - a) if ratio is None else ratio
    pk.bar(cv, x, y, w, 5, ratio, ramp="bronze", ticks=10)
    pk.key_label(cv, x - 9, y - 1, str(HUD["level"]), C["bronze_hi"])
    pk.key_label(cv, x + w + 2, y - 1, str(HUD["level"] + 1), C["mist"])


def mouse_glyph(cv, mx, my, which):
    cv.rect(mx, my, 7, 9, C["ink"])
    cv.rect(mx + 1, my + 1, 5, 7, C["mist"])
    cv.vline(mx + 3, my + 1, 3, C["ink"]); cv.hline(mx + 1, my + 4, 5, C["ink"])
    cv.rect(mx + 1 if which == "L" else mx + 4, my + 1, 2, 3, C["red_lt"])


def space_label(cv, x, y, c):
    """Hotkey tag for the Space bar: «⎵» glyph on an ink plate."""
    cv.rect(x, y, 9, 7, C["ink"])
    cv.hline(x + 1, y + 4, 7, c); cv.vline(x + 1, y + 2, 2, c); cv.vline(x + 7, y + 2, 2, c)


def skill_slot(cv, x, y, s, icon, key=None, active=False, cooldown=None, mouse=None, space=False):
    T.wood_slot(cv, x, y, s, s, active=active)
    isz = s - 6
    if icon is None:                      # empty slot: skill not learned yet (lvl 4, tier 2 opens at 6)
        cv.rect(x + 3, y + 3, isz, isz, C["night"])
        cv.dither(x + 3, y + 3, isz, isz, C["wood_dk"], 0.4)
        T.rosette(cv, x + s // 2 - 0.5, y + s // 2 - 0.5, isz * 0.32, C["wood"])
    else:
        T.ICONS[icon](cv, x + 3, y + 3, isz)
    if cooldown is not None:
        ch = int(isz * cooldown[0])
        cv.remap(x + 3, y + 3, isz, ch, pk.DARKEN3)
        cv.dither(x + 3, y + 3, isz, ch, C["ink"], 0.5)
        cv.hline(x + 3, y + 3 + ch, isz, C["bronze"])
        cv.text_c(x + s // 2 + 1, y + 3 + max(1, (ch - 7) // 2) + 1, cooldown[1], C["bronze_hi"], outline=C["ink"])
    if space:
        space_label(cv, x + 2, y + 2, C["linen"])
    elif key:
        pk.key_label(cv, x + 2, y + 2, key, C["bronze_hi"] if active else (C["linen"] if icon else C["slate_lt"]))
    if mouse:
        mouse_glyph(cv, x + s - 8, y + s - 10, mouse)


def draw_belt(cv, x, y, kinds):
    s, g = 24, 2
    w = len(kinds) * s + (len(kinds) - 1) * g + 6
    cv.rect(x, y, w, s + 6, C["ink"])
    cv.rect(x + 1, y + 1, w - 2, s + 4, C["wood_dk"])
    for yy in (y + 2, y + s + 3):
        for xx in range(x + 2, x + w - 2, 3):
            cv.px(xx, yy, C["wood_md"])
    cv.frame(x, y, w, s + 6, C["bronze"])
    cv.hline(x + 1, y, w - 2, C["bronze_lt"])
    for i, k in enumerate(kinds):
        sx = x + 3 + i * (s + g)
        T.wood_slot(cv, sx, y + 3, s, s)
        T.potion(cv, sx + 6, y + 8, k)
        pk.key_label(cv, sx + s - 6, y + s - 4, str(i + 1), C["bronze_hi"])
    bx = x + w // 2 - 5
    cv.rect(bx, y - 5, 11, 7, C["ink"])
    cv.rect(bx + 1, y - 4, 9, 5, C["bronze_lt"])
    cv.rect(bx + 3, y - 3, 5, 3, C["ink"])
    cv.px(bx + 1, y - 4, C["bronze_hi"])
    return w


def draw_level(cv, cx, cy, lvl=None, plus=None):
    lvl = str(HUD["level"]) if lvl is None else lvl
    plus = HUD["free_points"] > 0 if plus is None else plus
    cv.disc(cx, cy, 14, C["ink"])
    cv.disc(cx, cy, 13, C["bronze"])
    cv.disc(cx - 0.5, cy - 0.5, 11, C["bronze_dk"])
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - cx + 0.5, yy - cy + 0.5)
    ang = np.arctan2(yy - cy, xx - cx)
    rim = (d > 11) & (d <= 13)
    cv.a[rim & ((np.floor(ang * 6) % 2) == 0)] = C["bronze_lt"]
    cv.a[(d > 10) & (d <= 11)] = C["ink"]
    cv.disc(cx - 0.5, cy - 0.5, 10, C["wood_dk"])
    T.text_ru(cv, cx + 1, cy - 10, "ур.", C["bronze_lt"], align="c", outline=False)
    T.text_ru(cv, cx + 1, cy - 1, lvl, C["bronze_hi"], align="c")
    if plus:          # free attribute points (GDD §10: «+» при свободных очках)
        px_, py_ = cx + 9, cy - 13
        cv.disc(px_, py_, 4.5, C["ink"]); cv.disc(px_ - 0.5, py_ - 0.5, 3.6, C["red"])
        cv.rect(px_ - 2, py_ - 1, 4, 1, C["linen"]); cv.rect(px_ - 1, py_ - 2, 1, 4, C["linen"])


def draw_silver(cv, x, y, w=46, amount=None):
    amount = str(HUD["silver"]) if amount is None else amount
    cv.rect(x, y, w, 26, C["ink"])
    cv.rect(x + 1, y + 1, w - 2, 24, C["wood_dk"])
    cv.frame(x + 1, y + 1, w - 2, 24, C["wood"])
    for (a, b) in ((5, 16), (9, 14), (4, 12), (8, 10)):
        cv.rect(x + a, y + b, 6, 2, C["slate_lt"]); cv.rect(x + a, y + b - 1, 6, 1, C["birch"])
        cv.px(x + a + 1, y + b - 1, C["linen"])
    T.text_ru(cv, x + w - 4, y + 3, "Серебро:", C["mist"], align="r", outline=False)   # «Серебро: 284» (§10.1, A3)
    T.text_ru(cv, x + w - 4, y + 14, amount, C["linen"], align="r")


# Skill bar layout (GDD §3.6, §10; designer 08.10: Рывок on its own small slot «Пробел», CD 4 s).
# level 4: only tier-1 skills learned (Огненный змей on ПКМ/F1, Сшибка on F2); F3-F6 empty sockets.
SKILLBAR = dict(lmb=("sword", False), rmb=("fire_serpent", True),
                f=(("fire_serpent", True), ("shield_bash", False), None, None, None, None),
                belt=("life", "life", "mana", "zhivaya"), dash=(0.85, "4"), xp=None)


def dash_slot(cv, x, y, s=18, cd=None):
    """Рывок (GDD §10, §12.1.1 A4): small 18x18 slot right of ПКМ, 16x16 icon,
    «Пробел» caption under it; cooldown = clock sector (remaining share cd[0],
    seconds cd[1]). Designer 08.10: separate slot, not in F1-F6, CD 4 s."""
    cv.rect(x, y, s, s, C["ink"])
    isz = s - 2
    T.ICONS["ryvok"](cv, x + 1, y + 1, isz)
    if cd is not None and cd[0] > 0:
        yy, xx = np.mgrid[0:H, 0:W]
        cx, cy = x + s / 2 - 0.5, y + s / 2 - 0.5
        ang = (np.arctan2(xx - cx, -(yy - cy)) % (2 * math.pi)) / (2 * math.pi)     # 0 at 12 o'clock, clockwise
        box = (xx >= x + 1) & (xx < x + 1 + isz) & (yy >= y + 1) & (yy < y + 1 + isz)
        pie = box & (ang >= 1 - cd[0])
        cv.a[pie] = np.asarray(pk.DARKEN1, dtype=np.uint8)[cv.a[pie]]
        a1 = (1 - cd[0]) * 2 * math.pi
        for r in np.arange(0, isz / 2, 0.5):
            cv.px(int(round(cx)), int(round(cy - r)), C["bronze_lt"])
            cv.px(int(round(cx + math.sin(a1) * r)), int(round(cy - math.cos(a1) * r)), C["bronze_lt"])
        T.text_ru(cv, x + s - 5, y + s - 10, cd[1], C["bronze_hi"], align="c")
    cv.frame(x, y, s, s, C["bronze"])
    for (px_, py_) in ((x, y), (x + s - 1, y), (x, y + s - 1), (x + s - 1, y + s - 1)):
        cv.px(px_, py_, C["bronze_lt"])
    T.text_ru(cv, x + s // 2 + 1, y + s + 1, "Пробел", C["mist"], align="c", outline=False)


def draw_bottom(cv, S, sb=None, xp_ratio=None):
    sb = SKILLBAR if sb is None else sb
    draw_panel(cv)
    draw_housing(cv, True); draw_housing(cv, False)
    draw_xp(cv, xp_ratio if xp_ratio is not None else sb.get("xp"))
    by = 328
    s_big, s_sm, s_dash = 32, 22, 18
    belt_w = 4 * 24 + 3 * 2 + 6
    total = s_big + 4 + 3 * s_sm + 4 + 6 + belt_w + 6 + 3 * s_sm + 4 + 4 + s_big + 3 + 36
    x = 127
    assert x + total + 3 + 44 <= 551, total
    skill_slot(cv, x, by, s_big, sb["lmb"][0], mouse="L", active=sb["lmb"][1]); x += s_big + 4
    fs = list(sb["f"])
    for i in range(3):
        ic = fs[i]
        skill_slot(cv, x, by + 5, s_sm, ic[0] if ic else None, key="F%d" % (i + 1), active=bool(ic and ic[1]),
                   cooldown=ic[2] if ic and len(ic) > 2 else None)
        x += s_sm + 2
    x += 4
    draw_belt(cv, x, by + 1, list(sb["belt"])); x += belt_w + 6
    for i in range(3, 6):
        ic = fs[i]
        skill_slot(cv, x, by + 5, s_sm, ic[0] if ic else None, key="F%d" % (i + 1), active=bool(ic and ic[1]),
                   cooldown=ic[2] if ic and len(ic) > 2 else None)
        x += s_sm + 2
    x += 2
    skill_slot(cv, x, by, s_big, sb["rmb"][0], mouse="R", active=sb["rmb"][1])
    x += s_big + 3
    dash_slot(cv, x + 9, by + 2, s_dash, sb.get("dash")); x += 36 + 3      # 36-px column: «Пробел» is 35 px
    draw_level(cv, 112, 343)
    draw_silver(cv, x, 331, w=50)          # v1.4: «Серебро:» label needs 43 px
    (l, lm), (m, mm) = HUD["life"], HUD["yar"]
    draw_orb(cv, S, True, l / lm, "%d/%d" % (l, lm))
    draw_orb(cv, S, False, m / mm, "%d/%d" % (m, mm))


def inv_proj(x, y):
    X, Y = (x - OX) / 16.0, (y - OY) / 8.0
    return (X + Y) / 2, (Y - X) / 2


def draw_minimap(cv, lit, L, x, y, w, h):
    region = np.zeros((H, W), bool); region[y:y + h, x:x + w] = True
    dark = lit.flatten(L, extra=np.where(region, -2.4, 0))
    cv.a[region] = dark[region]
    cv.dither(x, y, w, h, C["ink"], 0.3)
    saved = cv.a.copy()
    cx, cy = x + w // 2, y + h // 2 + 6
    hu, hv = inv_proj(*PLAYER)                       # minimap centred on the hero
    k = 2.2

    def M(u, v):
        return (int(cx + (u - hu) * k - (v - hv) * k), int(cy + (u - hu) * k / 2 + (v - hv) * k / 2))

    def seg(a, b, c, dotted=False):
        p, q = M(*a), M(*b)
        n = max(abs(q[0] - p[0]), abs(q[1] - p[1]), 1)
        for t in range(n + 1):
            if not dotted or t % 2 == 0:
                cv.px(p[0] + (q[0] - p[0]) * t // n, p[1] + (q[1] - p[1]) * t // n, c)
    # water: map every minimap pixel back to the world and test the shoreline
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    a_ = ((xx - cx) / k + (yy - cy) * 2 / k) / 2
    b_ = ((yy - cy) * 2 / k - (xx - cx) / k) / 2
    wu, wv = a_ + hu, b_ + hv
    sx, sy = proj(wu, wv)
    water = region & (sy > SHORE0 + SHORE_K * sx + 6)
    cv.a[water & ((xx + yy) % 2 == 0)] = C["sea_dk"]
    forest = region & (wv < 1.2)
    cv.a[forest & ((xx * 7 + yy * 13) % 9 == 0)] = C["pine"]
    pv = PAL["v"]
    seg((-6, pv), (PAL["gate"][0], pv), C["bronze_lt"], True); seg((PAL["gate"][1], pv), (30, pv), C["bronze_lt"], True)
    kc = CABIN
    for (a, b) in (((kc["u0"], kc["v0"]), (kc["u1"], kc["v0"])), ((kc["u1"], kc["v0"]), (kc["u1"], kc["v1"])),
                   ((kc["u1"], kc["v1"]), (kc["u0"], kc["v1"])), ((kc["u0"], kc["v1"]), (kc["u0"], kc["v0"]))):
        seg(a, b, C["birch"])
    sp = SHIP                                        # ladya outline
    seg((sp["uc"] - 6, sp["vs"]), (sp["uc"] + 6, sp["vs"]), C["wood_lt"])
    seg((10.5, pv), (10.6, 10), C["wood_lt"], True)
    ru, rv = inv_proj(*RIFT)
    rx, ry = M(ru, rv)
    cv.line(rx - 4, ry + 2, rx + 4, ry - 2, C["nebyl"])
    for (eu, ev) in (inv_proj(*UPYR), inv_proj(*VOLK), inv_proj(*LESHY)):
        ex, ey = M(eu, ev)
        cv.px(ex, ey, C["red_lt"])
    cv.a[~region] = saved[~region]
    # quest marker: the крада on the капище (rosette)
    qx, qy = M(*inv_proj(*FIRE))
    cv.disc(qx, qy, 3.5, C["ink"]); cv.disc(qx, qy, 2.6, C["bronze_lt"]); cv.px(qx, qy, C["ink"])
    # Чуров камень (waystone) far up the path
    wx, wy = M(14.5, -1.0)
    if y + 3 < wy < y + h - 3:
        cv.rect(wx - 1, wy - 2, 3, 4, C["blue_lt"]); cv.px(wx, wy - 3, C["linen"])
    # player arrow
    cv.rect(cx - 2, cy, 5, 1, C["linen"]); cv.rect(cx, cy - 2, 1, 5, C["linen"]); cv.px(cx, cy, C["red_lt"])
    for (bx, by_, sx_, sy_) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        T.bronze_corner(cv, bx, by_, sx_, sy_, 7)
    for t in range(10, w - 10, 4):
        cv.px(x + t, y, C["wood_md"]); cv.px(x + t, y + h - 1, C["wood_md"])
    for t in range(10, h - 10, 4):
        cv.px(x, y + t, C["wood_md"]); cv.px(x + w - 1, y + t, C["wood_md"])


def draw_zone(cv):
    w = pk.text_width("Капище Перуна", FONT_RU) + 10
    cv.remap(W - w, 0, w, 24, pk.DARKEN2)
    cv.dither(W - w, 0, w, 24, C["ink"], 0.3)
    for k in range(0, w, 4):
        cv.px(W - w + k, 23, C["bronze"] if k % 8 else C["bronze_lt"])
    T.text_ru(cv, 633, 3, "Капище Перуна", C["bronze_lt"], align="r")
    T.text_ru(cv, 633, 13, "Акт I · Миссия 1 из 3", C["mist"], align="r")


MENU_BUTTONS = (("character", "C", "Витязь"), ("inventory", "I", "Котомка"), ("skills", "T", "Навыки"),
                ("map", "M", "Карта"), ("chronicle", "J", "Летопись"), ("menu", "ESC", "Меню"))


def draw_buttons(cv, x, y, hover=None):
    """C Витязь · I Котомка · T Навыки · M Карта · J Летопись · ESC Меню (GDD §10, A8)."""
    s, g = 20, 2
    for i, (ic, key, _) in enumerate(MENU_BUTTONS):
        T.menu_button(cv, x + i * (s + g), y, s, ic, key)
        if hover == i:
            cv.frame(x + i * (s + g), y, s, s, C["bronze_hi"])
    return s, g


def button_tip(cv, bx, by, s, label, key, align="c"):
    """Russian hint under a HUD button: «Летопись (J)»."""
    txt = "%s (%s)" % (label, key if key != "ESC" else "Esc")
    w = pk.text_width(txt, FONT_RU) + 8
    x = bx + s // 2 - w // 2 if align == "c" else (bx + s - w if align == "r" else bx)
    y = by + s + 3
    cv.remap(x, y, w, 13, pk.DARKEN3)
    cv.dither(x, y, w, 13, C["ink"], 0.5)
    cv.frame(x, y, w, 13, C["wood_md"])
    for (px_, py_) in ((x, y), (x + w - 1, y), (x, y + 12), (x + w - 1, y + 12)):
        cv.px(px_, py_, C["bronze_lt"])
    T.text_ru(cv, x + 4, y + 3, txt, C["linen"], outline=False)


def draw_target(cv, cx, y, name="Упырь", ratio=0.58, sub="Нечисть · Небыль", elite=None):
    """Target plate: name, «Семейство · Мир», and for elites a third line
    («Матёрый» / «Вожак» + modifiers), GDD §5, §10, A4."""
    w = 180
    x = cx - w // 2
    cv.rect(x, y, w, 19, C["ink"])
    T.wood_planks(cv, x + 1, y + 1, w - 2, 17, seed=8, plank=17, dark=True)
    T.rope(cv, x + 1, y + 1, w - 2)
    T.rope(cv, x + 1, y + 15, w - 2)
    pk.bar(cv, x + 6, y + 4, w - 12, 11, ratio, ramp="red", trim=False)
    T.text_ru(cv, cx + 1, y + 5, name, C["blue_lt"] if elite else C["linen"], align="c")
    for ex in (x - 6, x + w - 7):
        cv.disc(ex + 6.5, y + 9.5, 7.5, C["ink"])
        cv.disc(ex + 6.5, y + 9.5, 6.5, C["bronze_dk"])
        T.rosette(cv, ex + 6, y + 9, 5, C["bronze_lt"])
    T.text_ru(cv, cx + 1, y + 21, sub, C["nebyl"], align="c")
    if elite:
        tw = pk.text_width(elite, FONT_RU)
        cv.remap(cx - tw // 2 - 4, y + 31, tw + 8, 11, pk.DARKEN2)
        T.text_ru(cv, cx + 1, y + 32, elite, C["blue_lt"], align="c")
        for sx_ in (cx - tw // 2 - 9, cx + tw // 2 + 4):          # small frost stars = cold tint
            cv.px(sx_ + 2, y + 33, C["blue_lt"]); cv.px(sx_ + 2, y + 37, C["blue_lt"])
            cv.px(sx_, y + 35, C["blue_lt"]); cv.px(sx_ + 4, y + 35, C["blue_lt"]); cv.px(sx_ + 2, y + 35, C["linen"])


QUEST = dict(title="ОГОНЬ НА КАПИЩЕ", act="Задание · Акт I",
             goals=(("— Спаси выживших", "3/3", "slate_lt", True),       # GDD v1.3 A2, act1 v1.1 §8.2: done, fades
                    ("— Отбей огнища у упырей", "2/3", "linen"),          # the burning крада counts as one огнище
                    ("— Одолей Крившу", "", "slate_lt")))                  # grey: not active yet (designer 08.10)


def draw_quest(cv, x, y):
    """Quest tracker in a carved wooden frame, ustav title with a буквица."""
    first, rest = QUEST["title"][0], QUEST["title"][1:]
    tw = pk.text_width(rest, FONT_USTAV)
    gw = max(pk.text_width(q[0], FONT_RU) + (pk.text_width(q[1], FONT_RU) + 8 if q[1] else 0) + (10 if len(q) > 3 else 0)
             for q in QUEST["goals"])
    w, h = max(186, 26 + 4 + tw + 6 + 14 + 4, gw + 16), 80
    ix, iy, iw, ih = U.carved_frame(cv, x, y, w, h, fill="dim")
    bw, bh = U.bukvitsa(cv, ix + 1, iy + 1, first)
    tx = ix + bw + 4
    T.text_ru(cv, tx, iy + 2, QUEST["act"], C["mist"])
    T.text_ru(cv, tx, iy + 15 - FONT_USTAV.get("top", 0), rest, C["bronze_hi"], font=FONT_USTAV)
    oy = iy + bh + 3
    for i, q in enumerate(QUEST["goals"]):
        g, n, col = q[:3]
        T.text_ru(cv, ix + 3, oy + 10 * i, g, C[col])
        rx = ix + iw - 3
        if len(q) > 3 and q[3]:                      # done: tick at the right edge
            tick(cv, rx - 7, oy + 10 * i + 1, C["bronze_lt"])
            rx -= 10
        if n:
            T.text_ru(cv, rx, oy + 10 * i, n, C[col], align="r")


def tick(cv, x, y, c):
    pts = ((6, 0), (5, 1), (4, 2), (0, 2), (3, 3), (1, 3), (2, 4))
    for (dx, dy) in pts:
        for (ox, oy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            cv.px(x + dx + ox, y + dy + oy, C["ink"])
    for (dx, dy) in pts:
        cv.px(x + dx, y + dy, c)


def compose(parts=("minimap", "zone", "buttons", "target", "quest", "bottom"), elite=False):
    a, lit, L, S = render_world()
    cv = Canvas(W, H); cv.a[:] = a
    if "minimap" in parts:
        draw_minimap(cv, lit, L, 506, 26, 128, 84)
    if "zone" in parts:
        draw_zone(cv)
    if "buttons" in parts:
        draw_buttons(cv, 505, 114)
    if "target" in parts:
        draw_target(cv, W // 2, 3, elite="Матёрый" if elite else None, ratio=0.74 if elite else 0.58)
    if "quest" in parts:
        draw_quest(cv, 3, 3)
    if "bottom" in parts:
        draw_bottom(cv, S)
    return cv


def export(cv, name):
    cv.save(os.path.join(OUT, name + "_native.png"))
    big = cv.save(os.path.join(OUT, name + "_1920x1080.png"), scale=SCALE)
    assert big.size == (1920, 1080)
    cols = {tuple(c) for c in np.array(big).reshape(-1, 3)}
    assert cols <= {tuple(c) for c in pk.RGB}, "off-palette colour!"
    print(name, "ok,", len(cols), "of", len(pk.PALETTE), "colours used")


def icon_sheet():
    """A6: the 9 skill icons 22x22 (6 existing + 3 new) with Russian names, for review."""
    names = (("sword", "Удар оружием"), ("shield_bash", "Сшибка"), ("fire_serpent", "Огненный змей"),
             ("obereg", "Чур-оберег"), ("bogatyr", "Богатырская стать"), ("frost", "Дыхание Морозко"),
             ("veshchee", "Вещее слово"), ("axe", "Круговая сеча"), ("perun", "Перунов скок"), ("ryvok", "Рывок"))
    cv = Canvas(320, 180, C["night"])
    U.carved_frame(cv, 0, 0, 320, 180, fill="dim")
    T.text_ru(cv, 160, 8, "Иконки навыков · 22 на 22", C["bronze_lt"], align="c")
    for i, (ic, nm) in enumerate(names):
        col, row = i % 2, i // 2
        x, y = 14 + col * 152, 24 + row * 30
        T.wood_slot(cv, x, y, 28, 28)
        T.ICONS[ic](cv, x + 3, y + 3, 22)
        new = ic in ("bogatyr", "veshchee", "ryvok")
        T.text_ru(cv, x + 34, y + (4 if new else 9), nm, C["flame"] if new else C["linen"], outline=False)
        if new:
            T.text_ru(cv, x + 34, y + 15, "новая иконка", C["bronze_lt"], outline=False)
    return cv


def buttons_sheet():
    """A8: HUD menu buttons with their Russian hints (shown on hover in the game)."""
    cv = Canvas(320, 120, C["night"])
    U.carved_frame(cv, 0, 0, 320, 120, fill="dim")
    T.text_ru(cv, 160, 8, "Кнопки HUD · подсказки при наведении", C["bronze_lt"], align="c")
    s, g = 20, 27
    x0 = 160 - (6 * s + 5 * g) // 2
    for i, (ic, key, lab) in enumerate(MENU_BUTTONS):
        bx = x0 + i * (s + g)
        by = 26 if i % 2 == 0 else 62
        T.menu_button(cv, bx, by, s, ic, key)
        button_tip(cv, bx, by, s, lab, key)
    return cv


def main():
    cv = compose()
    export(cv, "mockup_gameplay_hud_v2")
    # A4: same frame, hovered upyr is an elite «Матёрый» (cold tint + third plate line)
    ELITE["upyr"] = True
    _CACHE.clear()
    export(compose(elite=True), "mockup_gameplay_hud_v2_elite")
    ELITE["upyr"] = False
    _CACHE.clear()
    export_sheet(icon_sheet(), "skill_icons_v2")
    export_sheet(buttons_sheet(), "hud_buttons_v2")
    T.save_palette(os.path.join(OUT, "palette_v2.png"), os.path.join(OUT, "palette_v2.json"))


def export_sheet(cv, name):
    p = os.path.join(OUT, name + "_x3.png")
    big = cv.save(p, scale=SCALE)
    cols = {tuple(c) for c in np.array(big).reshape(-1, 3)}
    assert cols <= {tuple(c) for c in pk.RGB}, "off-palette colour!"
    print(name, "ok")


if __name__ == "__main__":
    main()

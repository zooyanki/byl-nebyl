"""Mission 1 milestone (b) ability effects (palette v2, index frames, -1 = transparent).

  fx_krivsha_fire_trail  4 loop  40x28  pivot (20,16)  r 0.6 tile ground fire left behind by Кривша
  fx_krivsha_aura        6 loop  80x48  pivot (40,26)  fire-phase ring r 1.5 tile, ground decal under the boss
  fx_krivsha_summon      8 once  48x56  pivot (24,44)  ground cracks + nebyl wisps where an упырь rises (0.8 s)
  fx_krivsha_leap_burst  8       64x120 pivot (32,108) flare of the огнище when Кривша lands in it (0-3 impact, 4-7 loop)
  fx_mara_ash_trail      4 loop  40x28  pivot (20,16)  r 0.6 tile smouldering ash left behind by Мара
  fx_mara_bolt           4 loop  24x16  pivot (12,8)   fire bolt in flight (faces +x; flip for -x)
  fx_mara_bolt_hit       5 once  32x32  pivot (16,24)  burst where the bolt lands
Ellipse radii on the 2:1 ground: rx = r*22.63, ry = r*11.31 px (scale.md §1)."""
import math
import numpy as np
import rig                       # palette v2
import pixelkit as pk
from pixelkit import C
from effects_rest import fire_field, sparks, _over, PX_PER_TILE_X, PX_PER_TILE_Y

TAU = math.tau


def _grid(H, W):
    return np.mgrid[0:H, 0:W]


def _ell(H, W, cx, cy, rx, ry):
    yy, xx = _grid(H, W)
    return ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2


def _hash(a, b, c=0):
    return (math.sin(a * 12.9898 + b * 78.233 + c * 37.719) * 43758.5453) % 1.0


def _small_tongue(out, x, base, h, i_ph):
    """Tiny 1-2 px wide flame tongue (ember body, flame core, red_lt tip)."""
    H, W = out.shape
    h = int(round(h))
    for k in range(h):
        y = base - k
        if not (0 <= y < H and 0 <= x < W):
            continue
        t = k / max(h, 1)
        out[y, x] = C["flame"] if t < 0.45 else (C["ember"] if t < 0.85 else C["red_lt"])
        if t < 0.35 and x + 1 < W:
            out[y, x + 1] = C["ember"]


# --------------------------------------------------------------------------
# trails (r 0.6 tile): Кривша — burning ground; Мара — ash with smouldering specks
# --------------------------------------------------------------------------
TR_W, TR_H, TR_PIV, TR_R = 40, 28, (20, 16), 0.6


def trail(kind, n=4):
    rx, ry = TR_R * PX_PER_TILE_X, TR_R * PX_PER_TILE_Y           # 13.6 x 6.8
    cx, cy = TR_PIV[0], TR_PIV[1]
    yy, xx = _grid(TR_H, TR_W)
    b = pk.bayer(TR_H, TR_W)
    e = _ell(TR_H, TR_W, cx, cy, rx, ry)
    # ragged edge: radius modulated by angle
    ang = np.arctan2((yy + 0.5 - cy) * 2, xx + 0.5 - cx)
    rag = 1 + 0.12 * np.sin(ang * 5 + 1.3) + 0.07 * np.sin(ang * 9)
    e = e / rag ** 2
    frames = []
    for i in range(n):
        ph = TAU * i / n
        out = np.full((TR_H, TR_W), -1, np.int16)
        if kind == "fire":
            out[(e <= 1.0) & (b < 0.55)] = C["ink"]
            out[(e <= 0.75)] = C["ink"]
            glow = 0.5 + 0.5 * np.sin(ph + xx * 0.7 - yy * 1.3)
            out[(e <= 0.55) & (b < 0.35 + 0.3 * glow)] = C["red"]
            out[(e <= 0.35) & (b < 0.3 + 0.3 * glow)] = C["ember"]
            for k, (dx, dy, hw, h) in enumerate(((-6, -1, 4.5, 11), (5, -2, 4.0, 9), (0, 2, 5.0, 13), (-10, 2, 3.0, 6),
                                                  (10, 1, 3.0, 7))):
                _over(out, fire_field(out.shape, cx + dx, cy + dy, hw, h, i, n=n, seed=k * 1.7))
            _over(out, sparks(out.shape, [(cx - 6, cy - 6, 8, 1, 0.1), (cx + 5, cy - 8, 8, 1, 0.6)], i, n=n))
        else:  # ash
            out[(e <= 1.0) & (b < 0.5)] = C["slate_dk"]
            out[(e <= 0.7)] = C["slate_dk"]
            out[(e <= 0.7) & (b < 0.35)] = C["slate"]
            out[(e <= 0.3) & (b < 0.25)] = C["mist"]
            out[(e <= 1.0) & (e > 0.82) & (b < 0.3)] = C["ink"]                # charred rim
            for k in range(13):                                          # smouldering specks blink
                a = _hash(k, 4) * TAU
                rr = math.sqrt(_hash(k, 5)) * 0.85
                x = int(round(cx + math.cos(a) * rx * rr)); y = int(round(cy + math.sin(a) * ry * rr))
                on = math.sin(ph + k * 2.3) > -0.2
                if on and 0 <= y < TR_H and 0 <= x < TR_W:
                    out[y, x] = C["ember"] if math.sin(ph + k * 2.3) > 0.6 else C["red_dk"]
            for k in range(2):                                          # thin smoke wisp rising
                t = ((i / n) + k * 0.5) % 1.0
                x = int(round(cx - 3 + k * 7 + math.sin(TAU * t + k) * 1.5)); y = int(round(cy - 3 - t * 12))
                if 0 <= y < TR_H:
                    out[y, x] = C["slate"] if t < 0.6 else C["slate_dk"]
        frames.append(out)
    return frames


# --------------------------------------------------------------------------
# fire-phase aura r 1.5 tile (ground ring, drawn under the boss)
# --------------------------------------------------------------------------
AU_W, AU_H, AU_PIV, AU_R = 80, 48, (40, 26), 1.5


def aura(n=6):
    rx, ry = AU_R * PX_PER_TILE_X, AU_R * PX_PER_TILE_Y           # 33.9 x 17.0
    cx, cy = AU_PIV[0], AU_PIV[1]
    yy, xx = _grid(AU_H, AU_W)
    b = pk.bayer(AU_H, AU_W)
    e = _ell(AU_H, AU_W, cx, cy, rx, ry)
    ang = np.arctan2((yy + 0.5 - cy) * 2, xx + 0.5 - cx)
    frames = []
    for i in range(n):
        ph = TAU * i / n
        out = np.full((AU_H, AU_W), -1, np.int16)
        wave = 0.5 + 0.5 * np.sin(ang * 6 - ph)                       # heat crawling around the ring
        inner = (e <= 1.0) & (e > 0.0)
        out[inner & (b < 0.10 + 0.10 * wave) & (e > 0.35)] = C["red_dk"]          # faint heat inside
        band = (e <= 1.0) & (e >= 0.80)
        out[band] = C["red"]
        out[band & (b < 0.45 + 0.4 * wave)] = C["ember"]
        out[(e <= 0.97) & (e >= 0.88) & (wave > 0.55)] = C["flame"]
        for k in range(14):                                           # tongues standing on the ring
            a = TAU * k / 14 + 0.2
            x = int(round(cx + math.cos(a) * rx * 0.96)); base = int(round(cy + math.sin(a) * ry * 0.96))
            h = 3 + 4 * (0.5 + 0.5 * math.sin(ph * (1 if k % 2 else 2) + k * 1.7))
            if math.sin(a) < 0:
                h *= 0.8                                              # back half lower (reads as a flat ring)
            _small_tongue(out, x, base, h, ph)
        frames.append(out)
    return frames


# --------------------------------------------------------------------------
# summon: ground cracks open, ember breath, nebyl wisps (8 frames @10 = upyr riseTime 0.8 s)
# --------------------------------------------------------------------------
SU_W, SU_H, SU_PIV = 48, 56, (24, 44)
SU_CRACKS = [[(0, 0), (-5, -1), (-9, 1), (-14, 0)], [(0, 0), (4, 1), (9, 0), (15, 2)], [(0, 0), (-2, 3), (-6, 5)],
             [(0, 0), (3, -3), (6, -4)], [(0, 0), (2, 4), (5, 6)]]
SU_OPEN = [0.25, 0.6, 1.0, 1.0, 1.0, 0.85, 0.5, 0.2]
SU_WISP = [0.0, 0.0, 0.35, 0.8, 1.0, 0.8, 0.45, 0.15]


def summon(n=8):
    cx, cy = SU_PIV
    frames = []
    for i in range(n):
        out = np.full((SU_H, SU_W), -1, np.int16)
        op = SU_OPEN[i]
        e = _ell(SU_H, SU_W, cx, cy, 13 * op + 2, 6 * op + 1)
        b = pk.bayer(SU_H, SU_W)
        out[(e <= 1) & (b < 0.5 * op)] = C["ink"]
        for c in SU_CRACKS:                                           # cracks grow along their polyline
            pts = [(cx + x, cy + y) for (x, y) in c]
            seg = len(pts) - 1
            upto = op * seg
            for s in range(seg):
                if s >= upto:
                    break
                (x0, y0), (x1, y1) = pts[s], pts[s + 1]
                fr_ = min(1.0, upto - s)
                steps = int(max(abs(x1 - x0), abs(y1 - y0)) * fr_) + 1
                for k in range(steps + 1):
                    t = k / max(steps, 1) * fr_
                    x = int(round(x0 + (x1 - x0) * t)); y = int(round(y0 + (y1 - y0) * t))
                    if 0 <= y < SU_H and 0 <= x < SU_W:
                        out[y, x] = C["ember"] if (s == 0 and op > 0.6) else C["red"]
                        if y - 1 >= 0 and out[y - 1, x] < 0:
                            out[y - 1, x] = C["ink"]
        if 2 <= i <= 4:                                               # ember breath from the centre
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.5
                d = (i - 1) * 3 + k % 2
                x = int(round(cx + math.cos(a) * d * 1.2)); y = int(round(cy - 2 + math.sin(a) * d))
                if 0 <= y < SU_H and 0 <= x < SU_W:
                    out[y, x] = C["flame"] if i == 2 else C["ember"]
        w = SU_WISP[i]
        if w > 0:                                                     # nebyl wisps (the dead rise)
            for k in range(4):
                t = min(1.0, (i - 2) / 5.0 + k * 0.08)
                x0 = cx + (k - 1.5) * 5
                for s in range(int(6 + 18 * w)):
                    y = int(round(cy - 2 - s))
                    x = int(round(x0 + 2.0 * math.sin(s * 0.45 + k * 1.7 + i * 0.8)))
                    if 0 <= y < SU_H and 0 <= x < SU_W:
                        top = s > (6 + 18 * w) * 0.6
                        if (s + k) % 3 == 0 and top:
                            continue
                        out[y, x] = C["nebyl"] if (s + i) % 4 else C["nebyl_dk"]
                        if s < 5 and x + 1 < SU_W:
                            out[y, x + 1] = C["nebyl_dk"]
        frames.append(out)
    return frames


# --------------------------------------------------------------------------
# leap burst: overlay on the огнище cell (64x120, pivot 32,108)
# --------------------------------------------------------------------------
LB_W, LB_H, LB_PIV = 64, 120, (32, 108)
LB_IMPACT = [(1.0, 0.9, 20), (0.85, 0.7, 26), (0.7, 0.5, 30), (0.6, 0.4, 30)]   # (height factor, bright, ring)


def leap_burst():
    cx, base = LB_PIV[0] - 0.5, LB_PIV[1] - 24          # stands on the log crib like the hearth flame
    frames = []
    for i in range(8):
        if i < 4:
            hf, br, ring = LB_IMPACT[i]
            fl = fire_field((LB_H, LB_W), cx, base, 18, 80 * hf, i, bright=br, n=4, seed=0.4)
            # ground shock ring of embers
            out = np.full((LB_H, LB_W), -1, np.int16)
            e = _ell(LB_H, LB_W, cx + 0.5, LB_PIV[1] - 0.5, ring, ring * 0.5)
            bb = pk.bayer(LB_H, LB_W)
            band = (e <= 1.0) & (e >= 0.78)
            out[band & (bb < [0.9, 0.7, 0.45, 0.25][i])] = C["ember"]
            out[band & (e >= 0.9) & (bb < [0.6, 0.35, 0.15, 0.0][i])] = C["flame"]
            _over(out, fl)
            em = [(cx + (k - 4) * 4, base - 30 - (k % 3) * 8, 30 + i * 6, 3, k * 0.11) for k in range(9)]
            _over(out, sparks(out.shape, em, i, n=8))
        else:                                                         # loop while he is inside (4 frames)
            j = i - 4
            out = fire_field((LB_H, LB_W), cx, base, 16, 66, j, bright=0.6, n=4, seed=0.4)
            em = [(cx + (k - 2) * 5, base - 50, 26, 2, k * 0.25) for k in range(5)]
            _over(out, sparks(out.shape, em, j, n=4))
        frames.append(out)
    return frames


# --------------------------------------------------------------------------
# Мара's fire bolt + hit
# --------------------------------------------------------------------------
BO_W, BO_H, BO_PIV = 24, 16, (12, 8)
BH_W, BH_H, BH_PIV = 32, 32, (16, 24)


def bolt(n=4):
    frames = []
    yy, xx = _grid(BO_H, BO_W)
    for i in range(n):
        ph = TAU * i / n
        out = np.full((BO_H, BO_W), -1, np.int16)
        cx, cy = 15.0, 8.0
        tail = (xx < cx) & (np.abs(yy + 0.5 - cy - 0.6 * np.sin(ph + xx * 0.6)) < (xx - 3) / (cx - 3) * 3.2)
        out[tail & (xx >= 3)] = C["red_lt"]
        out[tail & (xx >= 8) & (np.abs(yy + 0.5 - cy) < 1.6)] = C["ember"]
        e = _ell(BO_H, BO_W, cx, cy, 4.2, 4.0)
        out[e <= 1] = C["ember"]
        out[_ell(BO_H, BO_W, cx + 0.5, cy - 0.3, 2.7, 2.5) <= 1] = C["flame"]
        out[_ell(BO_H, BO_W, cx + 0.8, cy - 0.5, 1.3, 1.2) <= 1] = C["linen"]
        for k in range(3):                                            # trailing specks
            x = int(round(2 + k * 2 + (i + k) % 2)); y = int(round(cy + 3 * math.sin(ph + k * 2.1)))
            if 0 <= y < BO_H:
                out[y, x] = C["ember"] if k else C["red_lt"]
        frames.append(out)
    return frames


def bolt_hit(n=5):
    frames = []
    cx, cy = BH_PIV
    for i in range(n):
        out = np.full((BH_H, BH_W), -1, np.int16)
        r = [3, 6, 8, 9, 9][i]
        e = _ell(BH_H, BH_W, cx, cy - 4, r, r * 0.8)
        if i < 3:
            out[e <= 1] = C["ember"]
            out[e <= 0.5] = C["flame"]
            if i == 0:
                out[e <= 0.3] = C["linen"]
        else:
            b = pk.bayer(BH_H, BH_W)
            out[(e <= 1) & (e > 0.55) & (b < (0.6 if i == 3 else 0.3))] = C["slate"]
        for k in range(8):
            a = TAU * k / 8 + 0.3
            d = r + 2 + i
            x = int(round(cx + math.cos(a) * d)); y = int(round(cy - 4 + math.sin(a) * d * 0.8))
            if 0 <= y < BH_H and 0 <= x < BH_W and i < 4:
                out[y, x] = C["flame"] if i < 2 else C["ember"]
        ge = _ell(BH_H, BH_W, cx, cy, 9 - i, 3.5 - i * 0.5)       # scorch on the ground
        if i >= 1:
            out[(ge <= 1) & (out < 0)] = C["ink"] if i < 4 else -1
        frames.append(out)
    return frames


# --------------------------------------------------------------------------
# «огнище питает Крившу» (GDD v1.8 §5.4): fire-phase start, +15% HP while he leaves the огнище.
# Two layers in Кривша's own cell (128x128, pivot 64,116; mirror together with him):
#   fx_krivsha_feed_back  — parts behind his body (draw BEFORE the boss)
#   fx_krivsha_feed       — parts in front + chest glow + heal flash (draw AFTER the boss)
# plus fx_krivsha_feed_source on the огнище cell (64x120, pivot 32,108): the desecrated green flame
# surges and is drawn off. Green (огнище's nebyl) flows up three spiral strands, turns into his warm
# fire at the chest, flash on the heal frame. No red / red_lt (hero accent).
# --------------------------------------------------------------------------
FE_W, FE_H, FE_PIV = 128, 128, (64, 116)
FE_CHEST = (6.0, -60.0)                 # relative to the pivot; chest of krivsha_fire_emerge frames 2-5
FE_N, FE_FPS, FE_HEAL = 8, 10, 6
FE_HEAD = [0.22, 0.45, 0.72, 1.0, 1.0, 1.0, 1.0, 1.0]
FE_TAIL = [0.0, 0.0, 0.0, 0.12, 0.42, 0.78, 1.0, 1.0]
FE_GLOW = [0.0, 0.0, 0.0, 3.0, 4.5, 6.0, 8.0, 0.0]
FE_PILLAR = [0.3, 0.6, 0.85, 0.95, 0.7, 0.4, 0.0, 0.0]


def _disc(out, x, y, r, col):
    H, W = out.shape
    for yy in range(int(math.floor(y - r)), int(math.ceil(y + r)) + 1):
        for xx in range(int(math.floor(x - r)), int(math.ceil(x + r)) + 1):
            if 0 <= yy < H and 0 <= xx < W and (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= r * r:
                out[yy, xx] = col


def _strand_col(s):
    """colour along the strand: green at the ground -> warm at the chest."""
    if s < 0.38:
        return C["nebyl_dk"], C["nebyl"]
    if s < 0.55:
        return C["nebyl"], C["linen"]
    return C["ember"], C["flame"]


def feed():
    """returns (back_frames, front_frames) in Кривша's cell."""
    cx, gy = FE_PIV[0], FE_PIV[1]
    tx, ty = cx + FE_CHEST[0], gy + FE_CHEST[1]
    back, front = [], []
    for i in range(FE_N):
        b = np.full((FE_H, FE_W), -1, np.int16)
        f = np.full((FE_H, FE_W), -1, np.int16)
        head, tail = FE_HEAD[i], FE_TAIL[i]
        # ground ring of green tongues around his feet (the огнище's fire rising out of the ground), frames 0-4
        if i <= 4:
            k_ring = [0.6, 1.0, 1.0, 0.7, 0.35][i]
            for k in range(12):
                a = TAU * k / 12 + 0.15
                x = int(round(cx + math.cos(a) * 18)); base = int(round(gy + math.sin(a) * 9))
                h = (4 + 5 * (0.5 + 0.5 * math.sin(i * 1.9 + k * 2.3))) * k_ring
                dst = f if math.sin(a) >= 0 else b
                for t in range(int(round(h))):
                    y = base - t
                    if 0 <= y < FE_H:
                        dst[y, x] = C["nebyl"] if t < h * 0.6 else C["nebyl_dk"]
                        if t < h * 0.3 and x + 1 < FE_W:
                            dst[y, x + 1] = C["nebyl_dk"]
        # three spiral strands from the ring to the chest
        # pillar of the огнище's fire behind him (back layer): green rising, turns warm as it is absorbed
        ph_ = FE_PILLAR[i]
        if ph_ > 0:
            Rr, Hh = 36.0, 120.0 * ph_
            yy, xx = _grid(FE_H, FE_W)
            bb = pk.bayer(FE_H, FE_W)
            dx = (xx + 0.5 - cx) / Rr
            prof = np.zeros_like(dx)
            for k, (ok, rel) in enumerate(((-0.92, 0.62), (-0.55, 0.85), (0.0, 1.0), (0.55, 0.88), (0.9, 0.66))):
                sway = 0.06 * math.sin(i * 1.3 + k * 2.1)
                rk = rel * (0.85 + 0.15 * math.sin(i * 1.9 + k * 1.4))
                prof = np.maximum(prof, rk * np.clip(1 - np.abs(dx - ok - sway) / 0.3, 0, 1) ** 0.75)
            hgt = Hh * prof
            up = gy - yy                                               # height above the ground
            body = (up >= -2) & (up <= hgt) & (np.abs(dx) <= 1.25)
            frac = np.where(hgt > 0, up / np.maximum(hgt, 1), 1)
            body &= ~((frac > 0.8) & (bb > (1 - frac) * 4.0))       # slightly dithered tips
            edge = body & ~(np.roll(body, 1, 0) & np.roll(body, -1, 0) & np.roll(body, 1, 1) & np.roll(body, -1, 1))
            warm = i >= 4
            b[body] = C["flame"] if warm else C["nebyl"]
            b[body & (frac < 0.3) & (np.abs(dx) < 0.6)] = C["linen"] if not warm else C["flame"]
            b[body & (frac > 0.62)] = C["ember"] if warm else C["nebyl_dk"]        # darker tips: depth
            b[edge] = C["ember"] if warm else C["pine_dk"]
        for j in range(4):
            a0 = TAU * j / 4 + 0.5
            for st in range(90):
                s = st / 89.0
                if s < tail or s > head:
                    continue
                ang = a0 + s * math.pi * 1.4 + i * 0.25
                R = 18 * (1 - s) ** 0.8
                x = cx + (tx - cx) * s ** 1.5 + math.cos(ang) * R
                y = gy + (ty - gy) * s + math.sin(ang) * R * 0.5
                dst = f if (math.sin(ang) >= 0 or s > 0.85) else b
                edge, core = _strand_col(s)
                r = 2.6 - 1.2 * s
                if abs(s - head) < 0.06 and head < 1.0:
                    edge, core, r = C["flame"], C["linen"], 2.8     # bright leading head
                _disc(dst, x, y, r, edge)
                _disc(dst, x, y, max(0.6, r - 1.1), core)
        # chest glow
        g = FE_GLOW[i]
        if g > 0:
            e = _ell(FE_H, FE_W, tx + 0.5, ty + 0.5, g, g * 0.85)
            if i < FE_HEAL:
                f[e <= 1] = C["ember"]
                f[e <= 0.55] = C["flame"]
                f[e <= 0.2] = C["linen"]
            else:                                                     # heal flash: bright ring + rays
                f[(e <= 1) & (e >= 0.55)] = C["flame"]
                f[e <= 0.55] = C["linen"]
                ring = _ell(FE_H, FE_W, tx + 0.5, ty + 0.5, 19, 15)
                f[(ring <= 1.0) & (ring >= 0.8)] = C["flame"]
                f[(ring <= 0.93) & (ring >= 0.86)] = C["linen"]
                for k in range(8):
                    a = TAU * k / 8 + 0.4
                    for d in range(22, 28):
                        x = int(round(tx + math.cos(a) * d)); y = int(round(ty + math.sin(a) * d * 0.8))
                        if 0 <= y < FE_H and 0 <= x < FE_W:
                            f[y, x] = C["linen"] if d < 24 else C["flame"]
        if i == 7:                                                    # fade: dithered ring + rising embers
            bb = pk.bayer(FE_H, FE_W)
            ring = _ell(FE_H, FE_W, tx + 0.5, ty + 0.5, 26, 20)
            f[(ring <= 1.0) & (ring >= 0.82) & (bb < 0.45)] = C["ember"]
            em = [(tx + (k - 3) * 6, ty + 6 - (k % 3) * 5, 0, 0, 0) for k in range(7)]
            for (x, y, _, _, _) in em:
                x, y = int(round(x)), int(round(y - 8))
                if 0 <= y < FE_H and 0 <= x < FE_W:
                    f[y, x] = C["flame"]
                    if y + 1 < FE_H:
                        f[y + 1, x] = C["ember"]
        back.append(b)
        front.append(f)
    return back, front


FS_W, FS_H, FS_PIV = 64, 120, (32, 108)
FS_SURGE = [0.55, 1.0, 1.15, 0.9, 0.55, 0.3, 0.15, 0.0]


def feed_source():
    """Over the desecrated огнище: its green flame surges up thin and is drawn off (motes leave upward)."""
    import kapishche as KP
    cx, base = FS_PIV[0] - 0.5, FS_PIV[1] - 24
    frames = []
    for i in range(FE_N):
        out = np.full((FS_H, FS_W), -1, np.int16)
        s = FS_SURGE[i]
        if s > 0:
            fl = fire_field((FS_H, FS_W), cx, base, 9 + 3 * s, 70 * s, i, bright=0.5, n=FE_N, seed=2.3)
            fl = KP._green(fl, i)
            _over(out, fl)
        if 1 <= i <= 6:                                               # motes drawn off the flame
            for k in range(8):
                t = ((i - 1) / 6.0 + k / 8.0) % 1.0
                x = int(round(cx + (k - 3.5) * 2.5 * (1 - t) + math.sin(k + i) * 1.5))
                y = int(round(base - 30 - t * 40))
                if 0 <= y < FS_H and 0 <= x < FS_W:
                    out[y, x] = C["nebyl"] if t < 0.6 else C["nebyl_dk"]
        frames.append(out)
    return frames

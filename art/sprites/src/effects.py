"""Effects (GDD §12.1.5): поджигатель — полёт факела 4, горящая земля Ø 2
тайла 6 (цикл); шрам на месте Разлома 6 (цикл). Palette v2 only.
Each function returns a list of palette-index frames (-1 = transparent)."""
import math
import numpy as np
import rig                      # palette v2 + helpers
import pixelkit as pk
from pixelkit import C

FIRE = [C["red"], C["red_lt"], C["ember"], C["flame"], C["linen"]]


def _sprite_from(mc, leg):
    spr = pk.make_sprite(mc.rows(), leg)
    ch = np.full(spr["mask"].shape, ".", dtype="<U1"); ch[1:-1, 1:-1] = mc.a
    fire = np.isin(ch, list(rig.FIRE_CH))
    solid = (ch != ".") & ~fire
    outl = spr["mask"] & (ch == ".")
    nb = lambda m: (np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1))
    f_only = outl & nb(fire) & ~nb(solid)
    spr["ramp"][f_only] = pk.RAMP_ID["fire"]; spr["lvl"][f_only] = 0
    return pk.sprite_to_index(spr)


# --------------------------------------------------------------------------
# 1. torch flight: 4 frames, 32x32, pivot (16,16) = torch centre; travels to +x (mirror for -x)
# --------------------------------------------------------------------------
def torch_flight():
    frames = []
    for i in range(4):
        mc = pk.MatCanvas(30, 30)
        cx, cy = 14.5, 15.0
        ang = math.radians(-90 + i * 90 + 25)              # spins clockwise 90 deg per frame
        u = (math.cos(ang), math.sin(ang))
        A = lambda a: (cx + u[0] * a, cy + u[1] * a)
        a0, a1 = A(-6), A(4)
        mc.line(round(a0[0]), round(a0[1]), round(a1[0]), round(a1[1]), "x", 2)
        n = (-u[1], u[0])
        w0, w1 = A(3.5), A(7)
        mc.poly([(w0[0] + n[0] * 1.8, w0[1] + n[1] * 1.8), (w1[0] + n[0] * 1.8, w1[1] + n[1] * 1.8),
                 (w1[0] - n[0] * 1.8, w1[1] - n[1] * 1.8), (w0[0] - n[0] * 1.8, w0[1] - n[1] * 1.8)], "R")
        hx, hy = A(5.5)
        # flame: rises and streams back (to -x) because the torch flies to +x
        for k in range(9):
            t = k / 8.0
            px_ = hx - t * 9.0 - (1.2 if (i + k) % 2 else 0)
            py_ = hy - t * 4.5 + math.sin(i * 1.7 + k) * 0.8
            r = 2.8 * (1 - t) + 0.6
            mc.ellipse(px_, py_, r, r * 0.85, "q")
            if r > 1.4:
                mc.ellipse(px_ + 0.4, py_, r * 0.62, r * 0.55, "E")
        mc.ellipse(hx, hy, 1.6, 1.4, "e")
        for k in range(3):                                  # sparks left behind
            sx = hx - 10 - k * 3 - (i % 2); sy = hy - 2 + ((i + k) % 3) - k
            mc.px(int(round(sx)), int(round(sy)), "q" if k % 2 else "E")
        frames.append(_sprite_from(mc, rig.BASE))
    return frames


# --------------------------------------------------------------------------
# 2. burning ground: 64x40, ellipse 64x32 (2 tiles) centred at (32,24); flames <= 16 px; 6-frame loop
# --------------------------------------------------------------------------
def burning_ground():
    W, H, cx, cy, rx, ry = 64, 40, 31.5, 24.0, 31.5, 15.5
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    b = pk.bayer(H, W)
    noise = pk.value_noise(H, W, 5, seed=4)
    base = np.full((H, W), -1, np.int16)
    # scorched decal: dithered soft edge, darker centre
    inside = d <= 1.0
    edge = (d > 0.78) & inside
    base[inside] = C["wood_dk"]
    base[inside & (d < 0.8) & (noise > 0.45)] = C["night"]
    base[inside & (d < 0.55)] = C["night"]
    base[inside & (d < 0.55) & (noise > 0.6)] = C["ink"]
    base[edge & (b > (1.0 - d) / 0.22)] = -1                # dithered rim
    # flame bases (u, v in ellipse units), tallest at the back-centre; heights in px
    tongues = [(-0.55, -0.25, 9), (-0.2, -0.45, 14), (0.25, -0.4, 16), (0.6, -0.2, 10), (-0.75, 0.15, 7),
               (-0.3, 0.1, 11), (0.15, 0.05, 13), (0.5, 0.25, 9), (-0.1, 0.5, 8), (0.75, 0.35, 6), (-0.5, 0.55, 6)]
    frames = []
    global BG_FLAME_MAX
    BG_FLAME_MAX = 0
    for f in range(6):
        a = base.copy()
        ph = f / 6.0 * 2 * math.pi
        # glowing cracks / embers on the ground, pulsing
        glow = inside & (d < 0.9) & (np.abs(np.sin(xx * 0.55 + yy * 1.3 + noise * 6)) < 0.18)
        a[glow] = C["red"]
        hot = glow & (np.sin(ph + xx * 0.3 - yy * 0.5) > 0.35)
        a[hot] = C["red_lt"]
        a[inside & (d < 0.75) & (noise > 0.78)] = C["ember"] if f % 2 else C["red_lt"]
        # flame tongues, back to front
        for k, (u, v, h) in sorted(enumerate(tongues), key=lambda t: t[1][1]):
            bx, by = cx + u * rx, cy + v * ry
            hh = h * (0.82 + 0.18 * math.sin(ph * (1 + (k % 2)) + k * 1.9))
            w = 2.2 + h * 0.18
            for r in range(int(math.ceil(hh)) + 1):
                t = r / max(hh, 1)
                if t > 1:
                    break
                half = w * (1 - t) ** 0.8 * (1 + 0.2 * math.sin(ph * 2 + r * 0.8 + k))
                off = 1.1 * math.sin(ph + k * 2.3 + t * 3.0) * t
                y = int(round(by - r))
                if y < 0:
                    continue
                BG_FLAME_MAX = max(BG_FLAME_MAX, int(round(by)) - y + 1)
                x0, x1 = int(round(bx + off - half)), int(round(bx + off + half))
                for x in range(max(0, x0), min(W, x1 + 1)):
                    dx = abs(x - (bx + off)) / max(half, 0.5)
                    if t > 0.7 or dx > 0.7:
                        c = FIRE[1] if t < 0.85 else FIRE[0]
                    elif t > 0.4 or dx > 0.35:
                        c = FIRE[2]
                    else:
                        c = FIRE[3] if t > 0.15 else FIRE[4]
                    a[y, x] = c
        # sparks rising
        for k in range(7):
            sx = cx + rx * 0.8 * math.sin(k * 2.4 + 0.3)
            sy = cy - 6 - ((f * 3 + k * 5) % 18)
            sx += math.sin(f + k) * 1.5
            if 0 <= sy < H and 0 <= sx < W:
                a[int(sy), int(sx)] = C["flame"] if k % 2 else C["ember"]
        frames.append(a)
    return frames


# --------------------------------------------------------------------------
# 3. rift scar: 96x112, pivot (48,104); glowing line 88 tall, 2-4 px wide; 6-frame loop
# --------------------------------------------------------------------------
SCAR_W = set()


def rift_scar():
    W, H, px_, py_ = 96, 112, 48, 104
    top = py_ - 88 + 1
    rows = np.arange(top, py_ + 1)
    # jagged centre line (fixed over the loop), width 2-4 (widest in the middle)
    rng = np.random.default_rng(7)
    jag = np.cumsum(rng.choice([-1, 0, 0, 1], size=len(rows))).astype(float)
    jag -= np.linspace(jag[0], jag[-1], len(rows))
    jag = np.clip(jag, -4, 4)
    t = (rows - top) / (py_ - top)
    width = 2 + 2 * np.sin(np.pi * t) ** 1.5                 # 2 at the tips, 4 in the middle
    yy, xx = np.mgrid[0:H, 0:W]
    b = pk.bayer(H, W)
    frames = []
    for f in range(6):
        ph = f / 6.0 * 2 * math.pi
        a = np.full((H, W), -1, np.int16)
        pulse = 0.5 + 0.5 * math.sin(ph)
        halo_w = 3.0 + 2.0 * pulse
        for j, y in enumerate(rows):
            c = px_ + jag[j]
            w = width[j]
            # halo (dithered nebyl_dk, then pine_dk), shimmering along the line
            sh = 0.5 + 0.5 * math.sin(ph * 2 - j * 0.35)
            for x in range(int(c - w / 2 - halo_w - 2), int(c + w / 2 + halo_w + 3)):
                dist = max(0.0, abs(x + 0.5 - c) - w / 2)
                if dist <= 0:
                    continue
                k = dist / (halo_w + 1.5 * sh)
                if k < 0.55 and b[y, x] < 0.85 - k:
                    a[y, x] = C["nebyl_dk"]
                elif k < 1.0 and b[y, x] < 0.45 - 0.3 * k:
                    a[y, x] = C["pine_dk"]
            # core: nebyl edges, linen/nebyl centre flickering
            nw = int(round(w))
            SCAR_W.add(nw)
            x0 = int(round(c - nw / 2.0))
            for x in range(x0, x0 + nw):
                a[y, x] = C["nebyl"]
            hot = (math.sin(ph * 3 + j * 0.7) > 0.2) and (nw >= 3)
            if hot:
                a[y, x0 + nw // 2] = C["linen"]
        # drifting motes around the scar
        for k in range(10):
            my = top + ((k * 19 + f * 3) % 88)
            mx = px_ + jag[int(my - top)] + (6 + (k % 4) * 2) * (1 if k % 2 else -1) + math.sin(ph + k) * 1.5
            if 0 <= int(mx) < W:
                a[int(my), int(mx)] = C["nebyl"] if (k + f) % 3 else C["linen"]
        # ground spot under the scar
        for x in range(px_ - 6, px_ + 7):
            if b[py_ + 1, x] < 0.6 - abs(x - px_) / 12:
                a[py_ + 1, x] = C["nebyl_dk"]
        frames.append(a)
    return frames

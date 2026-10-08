"""Main menu, theme «Гардарики» (v2): northern night over Ladoga, longships,
Небыль aurora, ustav logo (placeholder title), carved buttons.
python3 main_menu_v2.py -> ../mockup_main_menu_v2_{native,1920x1080}.png"""
import math
import numpy as np
import pixelkit as pk
import screens_common_v2 as SC
from pixelkit import C, Canvas, FONT3x5
from fonts_ru import FONT_RU, FONT_USTAV
import theme_rus as T
import ui_rus as U

W, H = SC.W, SC.H
HZ = 214          # horizon (water line)


def sky(cv):
    yy, xx = np.mgrid[0:H, 0:W]
    b = pk.bayer(H, W)
    t = yy / HZ
    cv.a[:] = C["ink"]
    cv.a[(t > 0.12) & (b < (t - 0.12) * 1.6)] = C["night"]
    cv.a[(t > 0.55) & (b < (t - 0.55) * 1.8)] = C["sea_dk"]
    cv.a[(t > 0.85) & (b < (t - 0.85) * 2.2)] = C["slate_dk"]
    # aurora (Небыль curtains): sine ribbons with vertical rays fading upward
    n = pk.value_noise(H, W, 12, seed=8)
    for (y0, amp, ph, k, col_hi, col_lo, dens) in ((60, 10, 3.1, 0.012, "blue", "blue_dk", 0.5),
                                                  (96, 22, 0.0, 0.014, "nebyl", "nebyl_dk", 1.0), (138, 14, 1.7, 0.021, "nebyl_dk", "pine", 0.8)):
        base = y0 + amp * np.sin(xx * k + ph) + 6 * np.sin(xx * k * 3.1 + ph * 2)
        up = base - yy                      # pixels above the lower edge
        ray = 0.55 + 0.45 * np.sin(xx * 0.9 + np.sin(xx * 0.13) * 3)
        inten = np.where((up >= 0) & (up < 70), np.clip(1 - up / 70, 0, 1) ** 1.3 * ray, 0) * dens * (0.6 + n * 0.7)
        inten = np.where((xx > 150) & (xx < 640), inten, inten * np.clip((xx - 40) / 110, 0, 1))
        cv.a[(b < inten) & (up < 8)] = C[col_hi]
        cv.a[(b < inten * 0.8) & (up >= 8)] = C[col_lo]
        cv.a[(np.abs(up) < 0.6) & (b < dens) & (inten > 0.05)] = C[col_hi]
    # stars
    rng = np.random.default_rng(3)
    for _ in range(140):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, HZ - 40))
        if cv.a[y, x] in (C["ink"], C["night"]):
            cv.px(x, y, C["mist"] if rng.random() < 0.7 else C["linen"])
    for (x, y) in ((560, 30), (96, 22), (420, 16)):
        cv.px(x, y, C["linen"]); cv.px(x - 1, y, C["mist"]); cv.px(x + 1, y, C["mist"]); cv.px(x, y - 1, C["mist"]); cv.px(x, y + 1, C["mist"])
    # moon
    mx, my = 548, 70
    cv.disc(mx, my, 13, C["birch"]); cv.disc(mx + 4, my - 3, 11, C["sea_dk"]) if False else None
    d = np.hypot(xx - mx, yy - my)
    cv.a[(d < 16) & (d >= 13) & (b < 0.25)] = C["slate"]
    cv.a[(d < 13)] = C["birch"]
    cv.a[(d < 13) & (np.hypot(xx - mx - 3, yy - my + 2) < 3)] = C["mist"]
    cv.a[(d < 13) & (np.hypot(xx - mx + 4, yy - my - 4) < 2)] = C["mist"]
    cv.a[(d < 12) & (xx < mx - 6) & (b < 0.5)] = C["linen"]


def treeline(cv, y0, col, seed, hmin=8, hmax=22, step=5, dark_band=None):
    rng = np.random.default_rng(seed)
    x = -4
    while x < W + 4:
        h = int(rng.integers(hmin, hmax))
        for k in range(h):
            w = int(k * 0.42) + 1
            cv.hline(x - w // 2, y0 - h + k, w, col)
        x += int(rng.integers(step - 2, step + 3))
    cv.rect(0, y0, W, 4, col)


def fortress(cv, cx, base):
    """Ладожская крепость on the promontory: earth bank, log walls, tent-roof towers."""
    ink, d1, d2 = C["ink"], C["night"], C["slate_dk"]
    cv.poly([(cx - 150, base + 6), (cx - 110, base - 10), (cx + 90, base - 12), (cx + 140, base + 6)], d1)
    wall_y = base - 12
    cv.rect(cx - 104, wall_y - 18, 190, 18, d2)
    for x in range(cx - 104, cx + 86, 3):               # stake tops
        cv.px(x, wall_y - 19, d2); cv.px(x + 1, wall_y - 20, d2)
    for x in range(cx - 104, cx + 86, 3):
        cv.vline(x + 2, wall_y - 18, 18, d1)
        cv.px(x, wall_y - 19, C["slate"])
    for (tx, th, tw) in ((cx - 104, 34, 16), (cx - 36, 44, 20), (cx + 30, 38, 18), (cx + 80, 30, 14)):
        cv.rect(tx - tw // 2, wall_y - th, tw, th, d2)
        cv.vline(tx + tw // 2 - 1, wall_y - th, th, d1)
        cv.poly([(tx - tw // 2 - 3, wall_y - th + 1), (tx + tw // 2 + 2, wall_y - th + 1), (tx, wall_y - th - tw - 6)], d1, outline=None)
        cv.line(tx, wall_y - th - tw - 6, tx - tw // 2 - 3, wall_y - th + 1, C["slate"])   # moonlit roof edge
        cv.vline(tx, wall_y - th - tw - 11, 5, d2)
        for wy in range(wall_y - th + 6, wall_y - 6, 9):
            cv.rect(tx - 1, wy, 2, 3, C["ember"])
    # lit windows / torches along the wall
    for x in (cx - 80, cx - 60, cx + 4, cx + 52):
        cv.px(x, wall_y - 9, C["flame"]); cv.px(x, wall_y - 8, C["ember"])
    # houses inside (roof tops above wall)
    for (hx, hw) in ((cx - 76, 14), (cx - 8, 18), (cx + 52, 12)):
        cv.poly([(hx, wall_y - 18), (hx + hw, wall_y - 18), (hx + hw // 2, wall_y - 26)], d2)
        cv.line(hx + hw // 2, wall_y - 26, hx, wall_y - 18, C["slate"])


def longship(cv, x, y, s=1.0, sail=True, far=False):
    """Side-view silhouette of a ладья on the water (far ships are flat)."""
    body = C["slate_dk"] if far else C["night"]
    L = int(70 * s)
    for i in range(L):
        t = i / (L - 1)
        top = y - int(4 * s) - int(10 * s * abs(2 * t - 1) ** 3)
        bot = y + int(3 * s * math.sin(math.pi * t))
        cv.vline(x + i, top, bot - top + 1, body)
        if not far and i % 7 == 3 and 0.15 < t < 0.85:
            cv.disc(x + i, top + 2, 2.2 * s, C["wood"])
            cv.px(x + i, top + 2, C["bronze"])
    if not far:                                   # moonlit gunwale + waterline
        for i in range(L):
            t = i / (L - 1)
            top = y - int(4 * s) - int(10 * s * abs(2 * t - 1) ** 3)
            cv.px(x + i, top - 1, C["slate_lt"] if i % 7 else C["mist"])
            cv.px(x + i, y + int(3 * s * math.sin(math.pi * t)) + 1, C["slate"] if i % 2 else C["sea"])
    # stems
    for (sx, d) in ((x, -1), (x + L - 1, 1)):
        for k in range(int(10 * s)):
            cv.px(sx + d * (k // 4), y - int(14 * s) - k, body)
    if not far:
        cv.disc(x - 3, y - int(25 * s), 2.5 * s, body); cv.px(x - 5, y - int(25 * s), C["ember"])
    mx = x + L // 2
    cv.vline(mx, y - int(48 * s), int(46 * s), C["slate_dk"] if far else C["slate"])
    if sail:
        sw, sh = int(30 * s), int(24 * s)
        sx0, sy0 = mx - sw // 2, y - int(46 * s)
        for i in range(sw):
            bel = int(2 * s * math.sin(math.pi * i / max(1, sw - 1)))
            c = (C["red_dk"] if far else C["red"]) if (i // max(2, int(4 * s))) % 2 == 0 else (C["slate_dk"] if far else C["slate_lt"])
            cv.vline(sx0 + i, sy0 + bel, sh, c)
        if not far:
            cv.dither(sx0 + sw // 2, sy0, sw - sw // 2, sh, C["night"], 0.3)
            cv.hline(sx0, sy0 + sh, sw, C["slate_dk"])
        cv.hline(sx0 - 2, sy0, sw + 4, body)


def water(cv):
    yy, xx = np.mgrid[0:H, 0:W]
    b = pk.bayer(H, W)
    wm = yy >= HZ
    cv.a[wm] = C["ink"]
    t = (yy - HZ) / (H - HZ)
    cv.a[wm & (b < 0.55 - t * 0.5)] = C["sea_dk"]
    ripple = np.sin(xx * 0.08 + yy * 0.9) + np.sin(xx * 0.31 - yy * 0.5) > 1.1
    cv.a[wm & ripple & (b < 0.6 - t * 0.4)] = C["sea"]
    # aurora reflection
    refl = wm & (np.sin(xx * 0.05 + 1.0) > 0.2) & (np.mod(yy, 3) == 0) & (b < 0.3 - t * 0.25)
    cv.a[refl] = C["nebyl_dk"]
    # moon path
    nn = pk.value_noise(H, W, 5, seed=21)
    path = wm & (np.abs(xx - 548 + (yy - HZ) * 0.15) < 3 + (yy - HZ) * 0.22) & ripple & (nn > 0.35)
    cv.a[path] = C["slate_lt"]
    cv.a[path & (b < 0.35)] = C["mist"]
    cv.a[path & (b < 0.08)] = C["birch"]


def logo(cv, cy):
    """Placeholder title in ustav capitals scaled x3 with bronze bevel."""
    text = "БЫЛЬ И НЕБЫЛЬ"
    g = FONT_USTAV["glyphs"]
    sc = 3
    chars = [ch for ch in text]
    widths = [g[ch].shape[1] for ch in chars]
    total = (sum(widths) + 2 * (len(chars) - 1)) * sc
    x0 = W // 2 - total // 2
    m = np.zeros((14 * sc, total), bool)
    x = 0
    for ch, w in zip(chars, widths):
        m[:, x:x + w * sc] |= np.kron(g[ch], np.ones((sc, sc), bool))
        x += (w + 2) * sc
    hgt = m.shape[0]
    y0 = cy - hgt // 2
    # glow behind «НЕБЫЛЬ»
    b = pk.bayer(H, W)
    yy, xx = np.mgrid[0:H, 0:W]
    nx = x0 + int(total * 0.62)
    d = np.hypot((xx - nx) / 1.9, (yy - cy) * 1.0)
    cv.a[(d < 40) & (b < np.clip(1 - d / 40, 0, 1) * 0.5)] = C["nebyl_dk"]
    sub = cv.a[y0 - 2:y0 + hgt + 2, x0 - 2:x0 + total + 2]
    big = np.zeros(sub.shape, bool); big[2:-2, 2:-2] = m
    ol = np.zeros_like(big)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            if abs(dx) + abs(dy) <= 3:
                ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    sub[ol & ~big] = C["ink"]
    rows = np.arange(sub.shape[0])[:, None] * np.ones((1, sub.shape[1]), int)
    rel = (rows - 2) / max(1, hgt)
    sub[big] = C["bronze"]
    sub[big & (rel < 0.62)] = C["bronze_lt"]
    sub[big & (rel < 0.28)] = C["bronze_hi"]
    top_edge = big & ~np.roll(big, 1, 0)
    sub[top_edge] = C["linen"]
    bot_edge = big & ~np.roll(big, -1, 0)
    sub[bot_edge] = C["bronze_dk"]
    right_edge = big & ~np.roll(big, -1, 1)
    sub[right_edge & ~top_edge] = C["bronze_dk"]
    # the «НЕБЫЛЬ» half tinted with Небыль green highlights
    nb_start = 2 + (sum(widths[:7]) + 2 * 7) * sc
    seg = big.copy(); seg[:, :nb_start] = False
    sub[seg & (rel >= 0.62)] = C["nebyl_dk"]
    sub[seg & (rel < 0.62) & (rel >= 0.28)] = C["moss_lt"]
    sub[seg & (rel < 0.28)] = C["nebyl"]
    sub[seg & top_edge] = C["linen"]
    return x0, y0, total, hgt


def main():
    cv = Canvas(W, H)
    sky(cv)
    treeline(cv, HZ - 2, C["pine_dk"], 4, 4, 12, 4)                 # far forest shore
    fortress(cv, 150, HZ - 4)
    water(cv)
    longship(cv, 300, HZ + 12, 0.55, far=True)
    longship(cv, 470, HZ + 8, 0.42, far=True)
    longship(cv, 430, HZ + 62, 1.25)
    # foreground spruces framing the scene
    rng = np.random.default_rng(9)
    for (x, base, h) in ((12, 360, 200), (52, 360, 140), (618, 360, 210), (584, 360, 130)):
        tier = 11
        for k in range(h):
            ph = (k % tier) / tier
            w = int(k * 0.32 * (0.45 + 0.55 * ph)) + 1 + int(rng.integers(0, 2))
            cv.hline(x - w // 2, base - h + k, w, C["ink"])
            if ph > 0.85 and w > 6:          # moonlit branch tips
                cv.px(x + w // 2 - 1, base - h + k, C["night"])
    cv.rect(0, 336, W, 24, C["ink"])
    # logo + subtitle
    lx, ly, lw, lh = logo(cv, 54)
    T.text_ru(cv, W // 2 + 1, 14, "ГАРДАРИКИ", C["bronze_lt"], font=FONT_USTAV, align="c")
    tw = pk.text_width("ГАРДАРИКИ", FONT_USTAV)
    for sx in (W // 2 - tw // 2 - 50, W // 2 + tw // 2 + 8):
        T.interlace(cv, sx, 16, 42, 7, period=10, bg=C["ink"])
    sw_ = pk.text_width("рабочее название · макет", FONT_RU) + 10
    cv.remap(W // 2 - sw_ // 2, ly + lh, sw_, 12, pk.DARKEN3)
    T.text_ru(cv, W // 2 + 1, ly + lh + 2, "рабочее название · макет", C["mist"], align="c")
    # menu panel + buttons
    bw, bh, gap = 160, 21, 6
    labels = ["НОВАЯ ИГРА", "ПРОДОЛЖИТЬ", "НАСТРОЙКИ", "СОЗДАТЕЛИ", "ВЫХОД"]
    ph = len(labels) * (bh + gap) - gap + 30
    px, py = W // 2 - (bw + 30) // 2, 128
    U.carved_frame(cv, px, py, bw + 30, ph, fill="dim")
    for i, lab in enumerate(labels):
        st = "hover" if i == 1 else "normal"
        U.button(cv, W // 2 - bw // 2, py + 15 + i * (bh + gap), bw, bh, lab, state=st, font=FONT_USTAV, seed=11 + i)
    U.cursor(cv, W // 2 + 52, py + 15 + (bh + gap) + 12)
    # corner texts
    T.text_ru(cv, W - 5, H - 13, "Сборка 0.1.7 · пре-альфа", C["slate_lt"], align="r", outline=False)
    T.text_ru(cv, 5, H - 13, "Макет интерфейса · 2026", C["slate"], outline=False)
    SC.export(cv, "mockup_main_menu_v2")


if __name__ == "__main__":
    main()

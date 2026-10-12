"""Портреты для окна диалога (GDD v1.13 §10.4, §12.1.7 H7/H19): 64×64, лицо и плечи, свет слева сверху,
фон night/slate_dk, без текста; рамку рисует код. Palette v2 only, alpha 0/255 (opaque square).
python3 portraits_v2.py  →  /workspace/game/art/ui/portraits/portrait_<id>.png (+ _x3 preview, contact sheet)."""
import os
import json
import numpy as np
import pixelkit as pk
import theme_rus as T

T.activate()
C = pk.C
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "portraits"))
N = 64
YY, XX = np.mgrid[0:N, 0:N].astype(float)
LIGHT = np.array([-0.55, -0.6, 0.58])
LIGHT /= np.linalg.norm(LIGHT)
RAMP = {
    "skin": ["wood_dk", "wood_md", "wood_lt", "bronze_lt", "bronze_hi"],
    "skin_boy": ["wood_md", "wood_lt", "bronze_lt", "bronze_hi", "bronze_hi"],
    "hairdk": ["ink", "wood_dk", "wood", "wood_md", "wood_lt"],
    "hairbr": ["wood_dk", "wood", "wood_md", "wood_lt", "bronze_lt"],
    "hairfair": ["wood", "wood_md", "wood_lt", "bronze_lt", "bronze_hi"],
    "grey": ["slate_dk", "slate", "slate_lt", "mist", "birch"],
    "white": ["slate", "slate_lt", "mist", "birch", "linen"],
    "iron": ["night", "slate_dk", "slate", "slate_lt", "mist"],
    "bronze": ["wood_dk", "bronze_dk", "bronze", "bronze_lt", "bronze_hi"],
    "red": ["ink", "red_dk", "red", "red", "red_lt"],
    "leather": ["ink", "wood_dk", "wood", "wood_md", "wood_lt"],
    "linen": ["slate", "slate_lt", "mist", "birch", "linen"],
    "moss": ["pine_dk", "pine", "moss", "moss_lt", "moss_lt"],
    "sea": ["night", "sea_dk", "sea", "slate_lt", "mist"],
    "black": ["ink", "ink", "night", "slate_dk", "slate"],
    "fur": ["ink", "wood_dk", "wood", "wood_md", "wood_lt"],
}


class Pic:
    def __init__(self, bg="night"):
        self.a = np.full((N, N), C["night"], np.int16)
        # background: night with a soft slate_dk glow upper-left (dithered)
        g = np.hypot(XX - 14, YY - 10) / 50.0
        d = pk.bayer(N, N) if hasattr(pk, "bayer") else np.zeros((N, N))
        self.a[(g + d * 0.25) < 0.62] = C["slate_dk"]

    def shade(self, m, ramp, cx, cy, rx, ry, bias=0.0, flat=0.0, noise=0.0, seed=0):
        """sphere-ish shading of mask m by ellipse normal; ramp from RAMP; bias shifts the light level."""
        nx = np.clip((XX - cx) / rx, -1, 1)
        ny = np.clip((YY - cy) / ry, -1, 1)
        nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0.05, 1))
        l = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) * (1 - flat) + flat * 0.6 + bias
        if noise:
            l = l + (pk.hash2(XX.astype(np.int64), YY.astype(np.int64), seed) - 0.5) * noise
        r = RAMP[ramp]
        bay = pk.bayer(N, N)
        lv = np.clip(np.floor((l + 0.15) / 1.15 * len(r) + (bay - 0.5) * 0.55).astype(int), 0, len(r) - 1)
        cols = np.array([C[n] for n in r], np.int16)
        self.a[m] = cols[lv[m]]

    def part(self, m, ramp, cx, cy, rx, ry, outline=True, keep=None, **kw):
        if outline:
            g = m.copy()
            g[1:, :] |= m[:-1, :]; g[:-1, :] |= m[1:, :]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
            ring = g & ~m
            if keep is not None:
                ring &= ~keep
            self.a[ring] = C["ink"]
        self.shade(m, ramp, cx, cy, rx, ry, **kw)

    def px(self, x, y, c):
        if 0 <= x < N and 0 <= y < N:
            self.a[int(y), int(x)] = C[c] if isinstance(c, str) else c

    def rows(self, x0, y0, rows, pal):
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch in pal:
                    self.px(x0 + i, y0 + j, pal[ch])

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        im = pk.Canvas(N, N)
        im.a[:] = self.a
        im.save(os.path.join(OUT, name + ".png"))
        im.save(os.path.join(OUT, "preview", name + "_x3.png"), scale=3) if os.path.isdir(os.path.join(OUT, "preview")) else None
        return self.a


def ell(cx, cy, rx, ry):
    return ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2 <= 1.0


def poly(pts):
    from PIL import Image, ImageDraw
    im = Image.new("L", (N, N), 0)
    ImageDraw.Draw(im).polygon(pts, fill=1)
    return np.array(im, bool)


# ---------------------------------------------------------------- shared face
def face(P, cx=32, cy=29, rx=13, ry=16, skin="skin", jaw=1.0, age=0, eyes="calm", brow="dk", mouth="set", nose=1):
    head = ell(cx, cy, rx, ry) & (YY < cy + ry * jaw)
    P.part(head, skin, cx - 3, cy - 4, rx + 4, ry + 4, bias=0.12)
    for sx in (-1, 1):
        e = ell(cx + sx * (rx + 0.3), cy + 1, 2.4, 4) & ~head
        P.part(e, skin, cx + sx * rx - 1, cy, 3, 4, bias=0.05 if sx < 0 else -0.15)
    # cheek / jaw shadow on the right (away from the light), cheekbone light on the left
    sh = ell(cx + rx * 0.62, cy + ry * 0.25, rx * 0.35, ry * 0.5) & head
    P.a[sh & (P.a == C["wood_lt"])] = C["wood_md"]
    ey = int(round(cy))
    dx = int(round(rx * 0.42))
    bc = {"dk": "wood_dk", "grey": "slate_lt", "fair": "wood_md", "white": "mist"}[brow]
    for sx in (-1, 1):
        ex = cx + sx * dx - (1 if sx < 0 else 0)          # left eye x..x+2
        x0 = ex - 1
        # socket shadow + upper lid
        for k in range(4):
            P.px(x0 + k, ey - 1, "wood_md")
        lid = "wood_dk"
        for k in range(3):
            P.px(x0 + k + (1 if sx < 0 else 0), ey - 1, lid)
        # eye white + iris (iris towards the nose a bit → looking at the reader)
        white = "birch" if eyes != "tired" else "mist"
        P.px(x0 + 1, ey, white); P.px(x0 + 2, ey, white)
        ir = x0 + (2 if sx < 0 else 1)
        P.px(ir, ey, "ink")
        if eyes == "wide":
            P.px(x0 + 1, ey + 1, white); P.px(x0 + 2, ey + 1, white); P.px(ir, ey + 1, "wood_dk")
            for k in range(3):
                P.px(x0 + k + (1 if sx < 0 else 0), ey - 2, lid)
        # brows
        by = ey - 3 - (1 if eyes == "wide" else 0)
        for k in range(4):
            tilt = 0
            if eyes == "stern":
                tilt = (1 if k >= 2 else 0) if sx < 0 else (1 if k <= 1 else 0)
            if eyes == "tired":
                tilt = (1 if k <= 0 else 0) if sx < 0 else (1 if k >= 3 else 0)
            P.px(x0 - (1 if sx < 0 else 0) + k, by + tilt, bc)
        if eyes == "tired" or age >= 2:
            P.px(x0 + 1, ey + 2, "wood_md"); P.px(x0 + 2, ey + 2, "wood_md")
    nl = int(round(ry * 0.36))
    if nose:
        for k in range(nl):
            P.px(cx + 1, ey + 1 + k, "wood_md")
            if k % 2 == 0:
                P.px(cx - 1, ey + 1 + k, "bronze_lt")
        P.px(cx - 2, ey + nl, "wood_md"); P.px(cx - 1, ey + nl + 1, "wood_md"); P.px(cx, ey + nl + 1, "wood_md")
        P.px(cx + 1, ey + nl + 1, "wood_dk"); P.px(cx + 2, ey + nl, "wood_dk")
    my = ey + nl + 4
    if mouth == "set":
        for k in range(-3, 3):
            P.px(cx + k, my, "wood_dk")
        P.px(cx - 1, my + 1, "wood_md")
    elif mouth == "open":
        for k in range(-1, 2):
            P.px(cx + k, my, "ink"); P.px(cx + k, my + 1, "wood_dk")
        P.px(cx - 2, my, "wood_dk"); P.px(cx + 2, my, "wood_dk")
    elif mouth == "soft":
        for k in range(-3, 3):
            P.px(cx + k, my, "wood_md" if abs(k + 0.5) > 2 else "wood_dk")
        P.px(cx - 1, my + 1, "wood_md"); P.px(cx, my + 1, "wood_md"); P.px(cx - 1, my + 2, "bronze_lt")
    if age >= 2:
        P.px(cx - 5, my - 2, "wood_md"); P.px(cx - 5, my - 1, "wood_md"); P.px(cx + 4, my - 2, "wood_md")
        for k in range(4):
            P.px(cx - 3 + k, ey - 7, "wood_md")
    return head, ey, my


def shoulders(P, ramp, cx=32, top=48, w=27, seed=0, **kw):
    m = ell(cx, top + 18, w, 20) & (YY >= top - 2)
    P.part(m, ramp, cx - 8, top + 4, w, 18, **kw)
    return m


def beard(P, ramp, cx, top, bot, w, my, seed=1, moust=True):
    pts = [(cx - w, top), (cx - w + 1, top + (bot - top) * 0.55), (cx - w // 2, bot - 1), (cx, bot + 1),
           (cx + w // 2, bot - 1), (cx + w - 1, top + (bot - top) * 0.55), (cx + w, top)]
    m = poly(pts) & ~ell(cx, my, 3.2, 1.6)
    P.part(m, ramp, cx - 3, top + 2, w + 2, (bot - top), noise=0.35, seed=seed, keep=ell(cx, (top + bot) / 2 - 8, w + 3, 18))
    # strands
    for i in range(-w + 2, w - 1, 2):
        for j in range(int(top + 3 + (i * 7) % 3), int(bot - 1), 3):
            if m[j, cx + i] and pk.hash2(i, j, seed) < 0.5:
                P.px(cx + i, j, RAMP[ramp][1])
    if moust:
        for k in range(-4, 5):
            P.px(cx + k, my - 1 - (1 if abs(k) < 2 else 0), RAMP[ramp][2 if k < 0 else 1])
        P.px(cx - 5, my, RAMP[ramp][1]); P.px(cx + 5, my, RAMP[ramp][0])
    for k in range(-1, 2):
        P.px(cx + k, my, "ink")
    return m


# ---------------------------------------------------------------- characters
def ratibor():
    """Герой: шлем-шишак с наносником и бронзовым ободом, тёмно-русая борода, кольчуга, красный плащ (акцент героя)."""
    P = Pic()
    shoulders(P, "red", w=31, top=49)
    mail = ell(32, 70, 19, 21) & (YY >= 47)
    P.part(mail, "iron", 26, 52, 20, 14, noise=0.45, seed=3)
    for y in range(49, 64, 2):
        for x in range(13, 52):
            if mail[y, x] and (x + (y // 2)) % 3 == 0:
                P.px(x, y, "slate_dk")
    P.part(ell(45, 52, 3, 3), "bronze", 44, 51, 3, 3)            # round brooch of the cloak (plain)
    head, ey, my = face(P, cx=32, cy=31, rx=12.5, ry=15, eyes="stern", brow="dk", mouth="set")
    beard(P, "hairbr", 32, ey + 6, 54, 12, my, seed=2)
    hel = (poly([(32, 4), (19, 24), (45, 24)]) | ell(32, 24, 13.5, 4.5)) & (YY <= 25)
    P.part(hel, "iron", 25, 12, 13, 13)
    band = (YY >= 22) & (YY <= 25) & ell(32, 24, 13.6, 4.7)
    P.shade(band, "bronze", 26, 23, 13, 4)
    for x in range(21, 45, 4):
        P.px(x, 23, "bronze_dk")
    for y in range(26, ey + 6):                                      # nasal
        P.px(31, y, "slate_lt"); P.px(32, y, "slate")
    P.px(31, ey + 6, "slate"); P.px(32, ey + 6, "slate_dk")
    for y in range(8, 22, 2):                                       # rib highlight
        P.px(30 - (y - 8) // 3, y, "mist")
    return P


def strands(P, m, palette, seed, light_x=None, gap=3, dark="ink"):
    """fill mask m with vertical hair strands: per-column tone (lighter to the left), thin dark partings,
    ragged lower ends — no even arcs."""
    ys, xs = np.nonzero(m)
    if not len(xs):
        return
    x0, x1 = xs.min(), xs.max()
    lx = light_x if light_x is not None else x0
    for x in range(x0, x1 + 1):
        col = np.nonzero(m[:, x])[0]
        if not len(col):
            continue
        top, bot = col.min(), col.max()
        cut = int(pk.hash2(x, 3, seed) * 3)                        # ragged ends
        lvl = 1.0 - (x - lx) / max(1, (x1 - x0)) * 0.9 + (pk.hash2(x, 7, seed) - 0.5) * 0.9
        k = int(np.clip(round(lvl * (len(palette) - 1) * 0.75), 0, len(palette) - 1))
        for y in range(top, bot + 1 - cut):
            if not m[y, x]:
                continue
            c = palette[k]
            if (x + seed) % gap == 0 and pk.hash2(x, y // 4, seed + 1) < 0.6:
                c = palette[max(0, k - 2)]
            if (y - top) % 9 == 8 and pk.hash2(x, y, seed + 2) < 0.4:
                c = palette[min(len(palette) - 1, k + 1)]
            P.px(x, y, c)
        for y in range(bot + 1 - cut, bot + 1):
            if m[y, x]:
                P.px(x, y, P.a[y, x - 1] if False else int(P.a[y, x]))  # leave background (ragged tip)


def vyshata():
    """Вышата, посадник (v1.13.2 правка сценариста): лицо шире и короче, седая борода короткая и широкая, густые усы,
    шапка с широким пушистым меховым околышем, уши и виски под мехом (без «наушников»). Кафтан цвета моря, бронзовые пуговицы."""
    P = Pic()
    shoulders(P, "sea", w=31, top=49)
    fur = ell(32, 52, 17, 4.5) & (YY >= 48)
    P.part(fur, "fur", 28, 50, 16, 4, noise=0.6, seed=7)
    for y in range(56, 64, 3):
        P.px(32, y, "bronze_lt"); P.px(33, y, "bronze")
    head, ey, my = face(P, cx=32, cy=32, rx=13.8, ry=14.2, eyes="tired", brow="white", mouth="set", age=2, jaw=0.92)
    # side locks hidden under the fur band (writer's fix: no grey arcs over the ears)
    # short broad beard: square-cut, wide at the jaw
    top, bot, w = ey + 6, 51, 14
    pts = [(32 - w, top - 1), (32 - w, top + 7), (32 - w + 3, bot - 1), (32 - 4, bot + 1), (32 + 4, bot + 1),
           (32 + w - 3, bot - 1), (32 + w, top + 7), (32 + w, top - 1)]
    bm = poly(pts) & ~ell(32, my, 3.2, 1.6)
    P.part(bm, "white", 29, top + 2, w + 2, bot - top, noise=0.35, seed=5, keep=ell(32, top - 6, w + 3, 12))
    for i in range(-w + 2, w - 1, 2):
        for j in range(top + 3 + (i * 7) % 3, bot - 1, 3):
            if bm[j, 32 + i] and pk.hash2(i, j, 5) < 0.5:
                P.px(32 + i, j, "slate_lt")
    # heavy moustache drooping past the mouth corners, darker underside
    for k in range(-6, 7):
        yk = my - 2 + (1 if abs(k) >= 4 else 0) + (1 if abs(k) >= 6 else 0)
        P.px(32 + k, yk, "linen" if k < -1 else ("birch" if k < 3 else "mist"))
        P.px(32 + k, yk - 1, "birch" if k < 0 else "mist") if abs(k) < 5 else None
        P.px(32 + k, yk + 1, "slate_lt") if abs(k) >= 2 else None
    P.px(25, my + 2, "mist"); P.px(39, my + 2, "slate_lt")
    for k in range(-1, 2):
        P.px(32 + k, my, "ink")
    # cap (sea cloth) and a thick fur band: tall, pile texture, covers ears and temples
    cap = ell(32, 16, 12.5, 10) & (YY <= 20)
    P.part(cap, "sea", 27, 10, 13, 10)
    brim = ell(32, 21.5, 16.5, 5.6)
    for x in range(14, 51, 2):                                      # tufted silhouette
        brim |= ell(x + (pk.hash2(x, 1, 9) - 0.5) * 1.5, 16.5 + abs(x - 32) * 0.12, 1.4, 1.6) & (YY >= 15)
        brim |= ell(x, 26.6 - abs(x - 32) * 0.08, 1.3, 1.3)
    P.part(brim, "fur", 26, 18, 16, 6, noise=0.9, seed=9)
    for x in range(15, 50):
        for y in range(16, 28):
            if brim[y, x] and pk.hash2(x, y, 21) < 0.18:
                P.px(x, y, "wood_lt" if x < 32 else "wood_dk")
            elif brim[y, x] and (x + 2 * y) % 5 == 0:
                P.px(x, y, "wood_dk" if x > 26 else "wood")
    return P


def milusha():
    """Милуша, знахарка: зрелая, спокойная; льняной платок с зелёной каймой, тёмная коса, пучок трав. Без красного."""
    P = Pic()
    shoulders(P, "moss", w=29, top=50)
    col = poly([(26, 49), (38, 49), (35, 56), (29, 56)])
    P.part(col, "linen", 30, 50, 6, 5)
    for k in range(4):
        P.px(30 + k, 52 + (k % 2), "moss")                          # stitched collar edge (plain)
    head, ey, my = face(P, cx=32, cy=32, rx=11.5, ry=14, eyes="calm", brow="dk", mouth="soft")
    scarf = (ell(32, 30, 15.5, 19) & ~ell(32, 34, 11, 13.5)) & (YY <= 50)
    scarf |= ell(32, 21, 14.5, 10) & (YY <= 23)
    P.part(scarf, "linen", 25, 20, 15, 18, bias=-0.05)
    border = (ell(32, 34, 12.2, 14.6) & ~ell(32, 34, 11, 13.5)) & (YY <= 46)
    P.a[border] = C["moss"]
    for j in range(10):                                             # braid
        P.px(17 + (j % 2), 46 + j, "wood_dk" if j % 2 else "wood")
        P.px(18 - (j % 2), 46 + j, "wood")
    for k, (x, y) in enumerate(((44, 50), (45, 48), (46, 47), (47, 49), (45, 51), (47, 46), (48, 48), (46, 45))):
        P.px(x, y, ("moss_lt", "moss", "birch")[k % 3])
    P.px(45, 53, "wood"); P.px(45, 54, "wood_md"); P.px(46, 52, "wood")
    return P


def tverdyata():
    """Твердята, кузнец: кряжистый, лысеющий, чёрная окладистая борода, ремешок на лбу; (v1.13.2) кожаный фартук с
    нагрудником и лямками через плечи, ворот рубахи в саже, пятна сажи на рубахе и щеке, прожжённые точки на фартуке."""
    P = Pic()
    shoulders(P, "linen", w=32, top=48, bias=-0.3)
    # soot on the shirt: dithered dark patches on the shoulders
    shirt = ell(32, 66, 32, 20) & (YY >= 46)
    for (x, y, r) in ((14, 56, 4), (48, 54, 5), (22, 50, 3), (44, 60, 4)):
        m = ell(x, y, r, r * 0.7) & shirt
        P.a[m & (pk.bayer(N, N) < 0.55)] = C["slate_dk"]
    apron = poly([(18, 52), (46, 52), (48, 64), (16, 64)])
    P.part(apron, "leather", 24, 54, 16, 12, bias=0.38)
    for y in range(51, 64):                                          # stitched edge
        if y % 2:
            P.px(20 + (y - 50) // 7, y, "wood_md"); P.px(44 - (y - 50) // 7, y, "wood_dk")
    for x in range(20, 45, 2):
        P.px(x, 51, "wood_md")
    for (x, y) in ((24, 58), (39, 61), (28, 62), (36, 56)):           # burn marks
        P.px(x, y, "ink")
    for x0, d in ((18, 1), (46, -1)):                                 # straps from the shoulders to the bib corners
        for y in range(46, 53):
            xx = x0 - d * (52 - y)
            P.px(xx, y, "wood_dk"); P.px(xx + d, y, "wood_md"); P.px(xx + 2 * d, y, "wood")
    head, ey, my = face(P, cx=32, cy=31, rx=13.5, ry=15, eyes="stern", brow="dk", mouth="set")
    # sooty open shirt collar visible at the beard sides
    for sx in (-1, 1):
        for k in range(5):
            P.px(32 + sx * (15 + k // 2), 45 + k, "ink"); P.px(32 + sx * (16 + k // 2), 45 + k, "slate_dk")
            P.px(32 + sx * (17 + k // 2), 45 + k, "slate")
    beard(P, "hairdk", 32, ey + 5, 56, 14, my, seed=11)
    for sx in (-1, 1):
        h = ell(32 + sx * 12, 27, 3, 7) & head
        P.shade(h, "hairdk", 32 + sx * 12, 25, 3, 7)
    band = (YY >= 21) & (YY <= 22) & head
    P.a[band] = C["wood_dk"]
    for (x, y) in ((25, 36), (26, 37), (27, 36), (39, 24), (40, 25), (24, 37), (38, 25)):
        P.px(x, y, "wood_md")
    return P


def mal():
    """Мал, мальчик из сгоревшего Залесья: лет десяти, вихры, сажа на щеке, испуганный взгляд, рубаха в саже."""
    P = Pic()
    shoulders(P, "linen", w=24, top=53, bias=0.15)
    for (x, y) in ((22, 58), (25, 60), (38, 57), (41, 61), (30, 62), (35, 63)):
        P.px(x, y, "slate"); P.px(x + 1, y, "slate_lt")
    P.px(32, 54, "wood_md"); P.px(32, 55, "wood_md"); P.px(32, 56, "wood_md")
    head, ey, my = face(P, cx=32, cy=35, rx=12, ry=13.5, skin="skin_boy", eyes="wide", brow="fair", mouth="open", nose=0)
    P.px(32, ey + 3, "wood_lt"); P.px(33, ey + 4, "wood_md"); P.px(31, ey + 4, "wood_lt")
    hair = ell(32, 27, 14, 9.5) & (YY <= 30)
    for (x, y) in ((20, 28), (21, 32), (44, 28), (45, 31), (25, 19), (31, 17), (37, 18), (41, 21)):
        hair |= ell(x, y, 2.3, 2.3)
    hair &= ~(ell(32, 38, 10.5, 9.5))
    P.part(hair, "hairfair", 27, 22, 14, 9, noise=0.4, seed=13)
    for (x, y) in ((23, 39), (24, 40), (25, 39), (24, 38), (40, 33)):
        P.px(x, y, "wood_md")
    return P


def priest():
    """Поп Иоанн (H19; v1.13.2 правка сценариста): узкое длинное лицо, длинные волосы с проседью до плеч прядями,
    борода длинная узкая клином, чёрная скуфья, тёмный подрясник, маленький медный крест. Спокойный усталый взгляд,
    тёплый отсвет огня справа. Без нимба, книги и благословляющего жеста."""
    P = Pic()
    shoulders(P, "black", w=28, top=50)
    HAIR = ["ink", "wood_dk", "slate_dk", "slate", "slate_lt", "mist"]
    cx, cy, rx, ry = 32, 28, 11, 16
    # long hair behind the face, down to the shoulders, falling in strands
    hair = (ell(cx, cy + 4, 15.5, 22) & (YY >= cy - 6) & (YY <= 53)) & ~ell(cx, 58, 7, 9)
    hair &= ~((YY > 44) & (np.abs(XX - cx) < 6))
    P.part(hair, "grey", cx - 4, cy, 15, 20, noise=0.3, seed=31)
    strands(P, hair, HAIR, seed=31, gap=3)
    head, ey, my = face(P, cx=cx, cy=cy, rx=rx, ry=ry, eyes="tired", brow="grey", mouth="set", age=2)
    rim = head & ~ell(cx - 1.4, cy, rx, ry) & (YY > cy - 6)
    P.a[rim] = C["ember"]
    # strands over the temples/cheeks edge (break the face outline, hide the ears)
    over = (ell(cx - rx - 0.6, cy + 3, 1.8, 8) | ell(cx + rx + 0.6, cy + 3, 1.8, 8)) & (YY >= cy - 5)
    strands(P, over, HAIR, seed=37, gap=2)
    # long narrow wedge beard (клином), grey-streaked dark
    top, tip = my - 1, 57
    pts = [(cx - 8, top - 3), (cx - 8, top + 4), (cx - 4, tip - 6), (cx, tip), (cx + 4, tip - 6), (cx + 8, top + 4), (cx + 8, top - 3),
           (cx + 5, top - 1), (cx - 5, top - 1)]
    bm = poly(pts) & ~ell(cx, my, 2.8, 1.5)
    P.part(bm, "grey", cx - 3, top + 4, 10, tip - top, noise=0.3, seed=17, keep=ell(cx, top - 6, 12, 8))
    strands(P, bm, HAIR[1:], seed=19, gap=2)
    for k in range(-4, 5):                                            # thin moustache into the beard
        P.px(cx + k, my - 1 - (1 if abs(k) < 2 else 0), "slate" if k < 0 else "slate_dk")
    for k in range(-1, 2):
        P.px(cx + k, my, "ink")
    # скуфья: low rounded black cap, a dull fold line
    cap = ell(cx, cy - 10, 12.5, 7.5) & (YY <= cy - 8)
    P.part(cap, "black", cx - 5, cy - 15, 12, 7, bias=0.2)
    for x in range(cx - 10, cx + 11):
        if cap[cy - 9, x]:
            P.px(x, cy - 9, "slate_dk" if x < cx else "night")
    # small copper cross below the beard tip
    for y in range(58, 64):
        P.px(cx, y, "bronze_lt")
    for x in range(cx - 2, cx + 3):
        P.px(x, 60, "bronze_lt")
    P.px(cx + 1, 59, "bronze"); P.px(cx + 1, 62, "bronze")
    P.px(cx, 57, "bronze_dk")
    return P


PORTRAITS = [("portrait_ratibor", ratibor, "Ратибор (герой)"), ("portrait_vyshata", vyshata, "Вышата"),
             ("portrait_milusha", milusha, "Милуша (speaker id vedana)"), ("portrait_tverdyata", tverdyata, "Твердята"),
             ("portrait_mal", mal, "Мал"), ("portrait_priest", priest, "Поп Иоанн (H19, speaker id priest)")]


def main():
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    sheet = pk.Canvas(len(PORTRAITS) * 70 + 4, 70, fill=C["ink"])
    meta = {}
    for i, (name, fn, title) in enumerate(PORTRAITS):
        P = fn()
        a = P.save(name)
        sheet.a[3:67, 3 + i * 70:67 + i * 70] = a
        used = sorted({pk.PALETTE[int(v)][0] for v in np.unique(a)})
        meta[name] = dict(title=title, size=[64, 64], colours=used, red_used=[c for c in used if c.startswith("red")])
        with open(os.path.join(OUT, name + ".json"), "w") as f:
            json.dump(dict(image=name + ".png", size=[64, 64], who=title, draw_at="(130, 234) inside a 68×68 code-drawn frame at (128, 232), GDD §10.4",
                           light="top-left", background="night / slate_dk, opaque", palette="palette_v2", alpha="opaque (255)"),
                      f, ensure_ascii=False, indent=1)
    sheet.save(os.path.join(OUT, "preview", "portraits_v2_sheet_x3.png"), scale=3)
    return meta


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=0))

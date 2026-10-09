"""Act I map screen, theme «Гардарики» (v2): birch-bark chart of the Ladoga
region with mission markers and an info panel.
python3 act_map_v2.py -> ../mockup_act_map_v2_{native,1920x1080}.png"""
import math
import numpy as np
import pixelkit as pk
import screens_common_v2 as SC
from pixelkit import C, Canvas
from fonts_ru import FONT_RU, FONT_USTAV
import theme_rus as T
import ui_rus as U
import gameplay_hud_v2 as G

W, H = SC.W, SC.H
MX, MY, MW, MH = 20, 34, 404, 306          # bark map rect
LADOGA = (226, 176)
M1 = (124, 196)      # Огонь на капище (active: level-4 state, designer 08.10)
M2 = (306, 252)      # Сопки Волхова (locked)
M3 = (112, 296)      # Разлом в Чёрном бору (locked)
SEL = 1

MISSIONS = [          # names per act1.md (same as the teaser); recommended levels per GDD §8.1 / designer
    ("Огонь на капище", "current", "1–6"),
    ("Сопки Волхова", "locked", "7–11"),
    ("Разлом в Чёрном бору", "locked", "11–16"),
]


def river_x(y):
    """Volkhov centre line (flows north into the lake)."""
    return 252 + 26 * math.sin((y - 140) / 38.0) + (y - 140) * 0.18


def shore_y(x):
    return 118 + 14 * math.sin(x / 47.0) + 8 * math.sin(x / 17.0 + 1) + (x - 220) ** 2 / 2600.0 * (-1 if x > 220 else 0.6) + 10


def bark(cv, x, y, w, h):
    yy, xx = np.mgrid[0:H, 0:W]
    inside = (xx >= x) & (xx < x + w) & (yy >= y) & (yy < y + h)
    n = pk.value_noise(H, W, 18, seed=41)
    n2 = pk.value_noise(H, W, 5, seed=42)
    b = pk.bayer(H, W)
    # torn edge
    ex = np.minimum(np.minimum(xx - x, x + w - 1 - xx), np.minimum(yy - y, y + h - 1 - yy))
    edge_noise = pk.value_noise(H, W, 6, seed=44) * 5
    body = inside & (ex > edge_noise)
    curl = inside & ~body & (ex > edge_noise - 3)
    band = np.sin(yy * 0.55 + n * 5.0)                       # horizontal bark bands
    base = np.full((H, W), C["birch"])
    base = np.where((band > 0.55) & (b < (band - 0.55) * 2.2), C["linen"], base)
    base = np.where((band < -0.8) & (n2 > 0.55) & (b < 0.3), C["mist"], base)
    cv.a[body] = base[body]
    stre = body & (np.sin(yy * 1.9 + n2 * 4) > 0.96) & (b < 0.4)
    cv.a[stre] = C["mist"]
    cv.a[curl] = np.where(b < 0.5, C["wood_lt"], C["wood_md"])[curl]
    rng = np.random.default_rng(5)
    for _ in range(170):             # lenticels
        lx, ly = int(rng.integers(x + 6, x + w - 14)), int(rng.integers(y + 5, y + h - 5))
        ln = int(rng.integers(2, 9))
        cv.hline(lx, ly, ln, C["slate_lt"] if rng.random() < 0.6 else C["slate"])
        if rng.random() < 0.3:
            cv.hline(lx + 1, ly + 1, max(1, ln - 2), C["mist"])
    # outline of the bark sheet
    full = body | curl
    o = full & ~(np.roll(full, 1, 0) & np.roll(full, -1, 0) & np.roll(full, 1, 1) & np.roll(full, -1, 1))
    cv.a[o] = C["wood_dk"]
    return body


def spruce_glyph(cv, x, y, c, s=1):
    for k in range(5 + s):
        cv.hline(x - k // 2, y + k, 1 + (k // 2) * 2, c)
    cv.px(x, y + 5 + s, c)


def birch_glyph(cv, x, y, c):
    cv.vline(x, y + 2, 5, c)
    cv.px(x - 1, y + 1, c); cv.px(x + 1, y + 1, c); cv.px(x, y, c); cv.px(x - 1, y + 3, c); cv.px(x + 1, y + 2, c)


def draw_map(cv):
    body = bark(cv, MX, MY, MW, MH)
    yy, xx = np.mgrid[0:H, 0:W]
    b = pk.bayer(H, W)
    ink, ink2 = C["wood_dk"], C["wood"]
    # ---- lake Нево (Ладожское озеро) -------------------------------------------
    sy = np.array([shore_y(x) for x in range(W)])
    lake = body & (yy < sy[xx])
    cv.a[lake & (b < 0.5)] = C["mist"]
    cv.a[lake & (b < 0.12)] = C["sea"]
    waves = lake & (np.mod(yy + (np.sin(xx * 0.25) * 1.5).astype(int), 6) == 0) & (np.mod(xx // 3 + yy, 4) != 0)
    cv.a[waves] = C["sea"]
    shore = lake & ~np.roll(lake, -1, 0) | (lake & ~np.roll(lake, 1, 1)) & (yy > MY + 8)
    shore = body & (np.abs(yy - sy[xx]) < 1.0)
    cv.a[shore] = C["sea_dk"]
    cv.a[body & (np.abs(yy - sy[xx] - 2.5) < 0.5) & (np.mod(xx, 3) == 0)] = C["sea"]   # coastal hatch
    # ---- Volkhov river -------------------------------------------------------------
    for y in range(int(shore_y(250)) - 2, MY + MH):
        cx = river_x(y)
        wdt = 2.2 + (y - 140) * 0.008
        for x in range(int(cx - wdt - 1), int(cx + wdt + 2)):
            if not body[y, x]:
                continue
            d = abs(x - cx)
            if d <= wdt - 1:
                cv.px(x, y, C["sea"] if (x + y) % 3 else C["mist"])
            elif d <= wdt:
                cv.px(x, y, C["sea_dk"])
    # tributary
    for t in range(0, 70):
        x, y = int(river_x(210) - t * 1.1), int(210 + math.sin(t / 9) * 4 + t * 0.4)
        cv.px(x, y, C["sea_dk"])
    # ---- forests ---------------------------------------------------------------------
    rng = np.random.default_rng(12)
    for _ in range(260):
        x, y = int(rng.integers(MX + 8, MX + MW - 10)), int(rng.integers(MY + 8, MY + MH - 12))
        if y < shore_y(x) + 8 or abs(x - river_x(y)) < 9:
            continue
        if math.hypot(x - LADOGA[0], y - LADOGA[1]) < 22 or math.hypot(x - M2[0], y - M2[1]) < 18:
            continue
        if math.hypot(x - M1[0], y - M1[1]) < 12:
            continue
        dark = math.hypot(x - M3[0], (y - M3[1]) * 1.3) < 52
        if dark or rng.random() < 0.72:
            spruce_glyph(cv, x, y, C["ink"] if dark else ink, 1 if dark else 0)
        else:
            birch_glyph(cv, x, y, ink2)
    # ---- Небыль stain over Чёрный бор ---------------------------------------------
    d3 = np.hypot(xx - M3[0], (yy - M3[1]) * 1.3)
    stain = body & (d3 < 40) & (b < np.clip(1 - d3 / 40, 0, 1) * 0.55)
    cv.a[stain & (cv.a != C["ink"])] = C["nebyl_dk"]
    crack = Canvas(W, H)
    pts = [(M3[0] - 22, M3[1] + 8), (M3[0] - 10, M3[1] + 2), (M3[0] - 2, M3[1] + 6), (M3[0] + 8, M3[1] - 2), (M3[0] + 22, M3[1] - 6)]
    for (a, bb), (c, d) in zip(pts, pts[1:]):
        crack.line(a, bb, c, d, 1)
    cv.a[crack.a == 1] = C["nebyl"]
    # ---- sopki (burial mounds) near mission 2 --------------------------------------
    for (dx, dy, r) in ((-14, -6, 5), (10, -10, 6), (2, 8, 4), (16, 6, 4)):
        x0, y0 = M2[0] + dx, M2[1] + dy
        for k in range(-r, r + 1):
            hgt = int((1 - (k / r) ** 2) * r * 0.7)
            cv.vline(x0 + k, y0 - hgt, 1, ink)
        cv.hline(x0 - r, y0 + 1, 2 * r + 1, ink2)
    # ---- route ------------------------------------------------------------------------
    route = [LADOGA, (180, 186), M1, (190, 228), (262, 246), M2, (240, 290), (170, 304), M3]
    seg_done = 1
    k = 0
    for i, ((a, bb), (c, d)) in enumerate(zip(route, route[1:])):
        n = int(max(abs(c - a), abs(d - bb)))
        for t in range(n):
            x = int(a + (c - a) * t / n); y = int(bb + (d - bb) * t / n)
            k += 1
            if i < seg_done:          # walked: solid red dashes
                if k % 6 < 4:
                    cv.px(x, y, C["red"]); cv.px(x + 1, y, C["red"]); cv.px(x, y + 1, C["red_dk"]); cv.px(x + 1, y + 1, C["red_dk"])
            elif i < 2:               # to the current mission: dashes
                if k % 6 < 3:
                    cv.px(x, y, C["red_lt"]); cv.px(x + 1, y, C["red_lt"]); cv.px(x, y + 1, C["red_dk"]); cv.px(x + 1, y + 1, C["red_dk"])
            else:                     # locked: faint dots
                if k % 4 == 0:
                    cv.px(x, y, C["slate"]); cv.px(x + 1, y, C["slate"])
    # ---- compass rose ---------------------------------------------------------------
    cx, cy = MX + MW - 34, MY + 30
    cv.disc(cx, cy, 13, C["linen"])
    T.rosette(cv, cx, cy, 11, C["wood"])
    for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        for k in range(14, 18):
            cv.px(int(cx + dx * k), int(cy + dy * k), C["wood_dk"])
    T.text_ru(cv, cx + 1, cy - 27, "С", C["red"], align="c", outline=False)
    # ---- boat on the lake --------------------------------------------------------------
    bx, by_ = 120, 92
    cv.hline(bx, by_, 14, ink); cv.hline(bx + 1, by_ + 1, 12, ink); cv.px(bx - 1, by_ - 1, ink); cv.px(bx + 14, by_ - 1, ink)
    cv.vline(bx + 7, by_ - 8, 8, ink)
    cv.rect(bx + 3, by_ - 7, 9, 5, C["red"]); cv.vline(bx + 5, by_ - 7, 5, C["linen"]); cv.vline(bx + 9, by_ - 7, 5, C["linen"])


def town(cv, x, y):
    """Ладога: palisade ring with houses, drawn in ink + bronze highlights."""
    cv.disc(x, y, 12, C["linen"])
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - x, (yy - y) * 1.2)
    ring = (d > 9) & (d < 11.5)
    cv.a[ring] = C["wood_dk"]
    cv.a[ring & (np.mod(xx, 2) == 0)] = C["wood"]
    for (dx, dy) in ((-4, -2), (3, -3), (-1, 3), (5, 2)):
        cv.rect(x + dx - 2, y + dy - 1, 4, 3, C["wood_md"])
        cv.px(x + dx - 2, y + dy - 2, C["wood_dk"]); cv.px(x + dx - 1, y + dy - 3, C["wood_dk"]); cv.px(x + dx, y + dy - 3, C["wood_dk"]); cv.px(x + dx + 1, y + dy - 2, C["wood_dk"])
    cv.rect(x - 1, y - 14, 3, 5, C["wood_dk"]); cv.px(x, y - 15, C["red"])     # tower


def marker(cv, x, y, state, selected=False, num="1"):
    if selected:      # glowing rings
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.hypot(xx - x, yy - y)
        b = pk.bayer(H, W)
        cv.a[(d < 17) & (d > 10) & (b < np.clip((17 - d) / 7, 0, 1) * 0.6)] = C["ember"]
        cv.a[np.abs(d - 13.5) < 0.6] = C["red_lt"]
    if state == "locked":
        cv.disc(x, y, 8, C["ink"]); cv.disc(x, y, 7, C["slate"]); cv.disc(x - 0.5, y - 0.5, 5.5, C["slate_dk"])
        cv.rect(x - 3, y - 1, 7, 5, C["slate_lt"]); cv.frame(x - 2, y - 5, 5, 5, C["slate_lt"])   # padlock
        cv.px(x, y + 1, C["ink"]); cv.px(x, y + 2, C["ink"])
        for (dx, dy) in ((6, -7), (7, -6), (8, -8), (9, -7)):
            cv.px(x + dx, y + dy, C["nebyl"])
    else:
        rim = C["bronze_hi"] if selected else C["bronze"]
        cv.disc(x, y, 8, C["ink"]); cv.disc(x, y, 7, rim); cv.disc(x - 0.5, y - 0.5, 5.5, C["red"] if state == "current" else C["bronze_dk"])
        if state == "done":
            for (dx, dy) in ((-3, 0), (-2, 1), (-1, 2), (0, 1), (1, 0), (2, -1), (3, -2)):
                cv.px(x + dx, y + dy, C["linen"]); cv.px(x + dx, y + dy + 1, C["ink"])
        else:
            T.text_ru(cv, x + 1, y - 4, num, C["linen"], align="c", outline=False)


def map_label(cv, x, y, text, c, bg=True):
    w = pk.text_width(text, FONT_RU) + 6
    if bg:
        cv.rect(x - w // 2, y - 1, w, 11, C["linen"])
        cv.frame(x - w // 2, y - 1, w, 11, C["wood_lt"])
    T.text_ru(cv, x + 1, y + 1, text, c, align="c", outline=False)


def info_panel(cv, x, y, w, h):
    U.recess(cv, x, y, w, h, fill=C["night"])
    cx = x + w // 2
    T.text_ru(cv, cx + 1, y + 6, "Миссия 1 из 3 · идёт", C["mist"], align="c", outline=False)
    T.text_ru(cv, cx + 1, y + 16, "ОГОНЬ НА КАПИЩЕ", C["bronze_hi"], font=FONT_USTAV, align="c")
    U.divider(cv, x + 6, y + 33, w - 12)
    text = ("В ночь твоего прибытия запылало капище Перуна. Жрец не вернулся, "
            "а из леса выходят те, кому положено лежать в земле.")
    ty = y + 45
    for ln in U.wrap(text, w - 14):
        T.text_ru(cv, x + 7, ty, ln, C["birch"], outline=False)
        ty += 10
    ty += 4
    U.section_title(cv, x + 4, ty, w - 8, "Цели")
    ty += 13
    # level-4 state, act1 v1.1 / GDD v1.3 A2: same 3 lines as the HUD tracker
    for ln, n, c, done in (("— Спаси выживших", "3/3", C["slate_lt"], True), ("— Отбей огнища у упырей", "2/3", C["linen"], False),
                           ("— Одолей Крившу", "", C["slate_lt"], False)):
        T.text_ru(cv, x + 7, ty, ln, c, outline=False)
        rx = x + w - 8
        if done:
            G.tick(cv, rx - 7, ty + 1, C["bronze_lt"]); rx -= 10
        if n:
            T.text_ru(cv, rx, ty, n, c, align="r", outline=False)
        ty += 10
    ty += 4
    U.section_title(cv, x + 4, ty, w - 8, "Награда")
    ty += 13
    U.silver_icon(cv, x + 8, ty)
    T.text_ru(cv, x + 22, ty + 1, "Серебро: +300 · «Удаль I»", C["linen"], outline=False)   # GDD v1.4 §10.1
    T.text_ru(cv, x + 7, ty + 12, "Амулет «Громовой знак»", C["bronze_lt"], outline=False)
    T.text_ru(cv, x + 7, ty + 24, "Сложность: ", C["mist"], outline=False)
    T.text_ru(cv, x + 7 + pk.text_width("Сложность: ", FONT_RU), ty + 24, "уровень 1–6", C["flame"], outline=False)
    # missions list
    ly = ty + 40
    U.section_title(cv, x + 4, ly, w - 8, "Акт I")
    ly += 13
    for i, (name, st, lv) in enumerate(MISSIONS):
        yy = ly + i * 13
        if st == "current":
            cv.rect(x + 4, yy - 2, w - 8, 12, C["bronze_dk"])
            cv.frame(x + 4, yy - 2, w - 8, 12, C["bronze_lt"])
        icon_c = {"done": C["moss_lt"], "current": C["flame"], "locked": C["slate"]}[st]
        cv.rect(x + 8, yy + 1, 5, 5, icon_c); cv.frame(x + 7, yy, 7, 7, C["ink"])
        col = {"done": C["mist"], "current": C["bronze_hi"], "locked": C["slate_lt"]}[st]
        T.text_ru(cv, x + 18, yy, name, col, outline=False)
        T.text_ru(cv, x + w - 9, yy, lv, col, align="r", outline=False)
    # buttons
    U.button(cv, x + 8, y + h - 24, w - 16, 18, "Продолжить", state="hover")


M2_GOALS = (("— Осмотри сопки", "0/5"), ("— Собери обережные камни", "0/3"), ("— Найди вход в курган", ""),
            ("— Узнай, кто будит мёртвых", ""), ("— Одолей Курганного князя", ""))      # act1 v1.1, GDD v1.3 A6
# GDD v1.4 §8.1 / act1_texts §1.1: HUD zone «Сопки»; parts announced on entry
M2_ZONE = (("Зона «Сопки»: Берег Волхова,", "mist"), ("Разрытый курган,", "mist"), ("Каменные врата", "mist"))


def m2_card(cv, x, y):
    """Hover card of the locked mission 2 (GDD §12.1.1 A6: level 7-11, goals verbatim)."""
    w = 4 + max(pk.text_width(g, FONT_RU) + (pk.text_width(n, FONT_RU) + 8 if n else 0) for g, n in M2_GOALS) + 8
    w = max(w, pk.text_width("Закрыто · после миссии 1", FONT_RU) + 14,
            max(pk.text_width(t, FONT_RU) for t, _ in M2_ZONE) + 14)
    h = 34 + 14 + len(M2_GOALS) * 10 + 5 + 8 + len(M2_ZONE) * 10
    cv.rect(x, y, w, h, C["night"])
    cv.frame(x, y, w, h, C["wood_md"]); cv.frame(x - 1, y - 1, w + 2, h + 2, C["ink"])
    for (px_, py_) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(px_, py_, C["bronze_lt"])
    T.text_ru(cv, x + 6, y + 4, "2 · Сопки Волхова", C["bronze_lt"])
    T.text_ru(cv, x + 6, y + 14, "Закрыто · после миссии 1", C["slate_lt"], outline=False)
    T.text_ru(cv, x + 6, y + 24, "Сложность: ", C["mist"], outline=False)
    T.text_ru(cv, x + 6 + pk.text_width("Сложность: ", FONT_RU), y + 24, "уровень 7–11", C["flame"], outline=False)
    U.divider(cv, x + 4, y + 36, w - 8)
    ty = y + 43
    for g, n in M2_GOALS:
        T.text_ru(cv, x + 6, ty, g, C["mist"], outline=False)
        if n:
            T.text_ru(cv, x + w - 6, ty, n, C["mist"], align="r", outline=False)
        ty += 10
    U.divider(cv, x + 4, ty + 1, w - 8)
    ty += 8
    for t, c in M2_ZONE:
        T.text_ru(cv, x + 6, ty, t, C["slate_lt"], outline=False)
        ty += 10
    return (x, y, w, h)


def main():
    cv, S = SC.scene(shift=0, dim=3, hud=False)
    cv.remap(0, 0, W, H, pk.DARKEN2)
    ix, iy, iw, ih = U.window(cv, 4, 10, 632, 344, title="АКТ I · ЛАДОГА", fill="planks")
    # ornament frame around the bark chart
    fx, fy, fw, fh = MX - 8, MY - 8, MW + 16, MH + 16
    cv.rect(fx, fy, fw, fh, C["ink"])
    T.interlace(cv, fx, fy, fw, 9, period=14)
    T.interlace(cv, fx, fy + fh - 9, fw, 9, period=14)
    T.rope(cv, fx, fy + 9, fh - 18, vertical=True)
    T.rope(cv, fx + fw - 3, fy + 9, fh - 18, vertical=True)
    for (cx_, cy_) in ((fx - 2, fy - 2), (fx + fw - 7, fy - 2), (fx - 2, fy + fh - 7), (fx + fw - 7, fy + fh - 7)):
        U.corner_plate(cv, cx_, cy_, 9)
    draw_map(cv)
    # labels on the chart
    T.text_ru(cv, 150, 56, "НЕВО-ОЗЕРО", C["sea"], font=FONT_USTAV, align="c", outline=False)
    T.text_ru(cv, 150, 72, "(Ладожское)", C["sea"], align="c", outline=False)
    town(cv, *LADOGA)
    map_label(cv, LADOGA[0], LADOGA[1] + 15, "Ладога", C["wood_dk"])
    T.text_ru(cv, 290, 196, "р. Волхов", C["sea_dk"], outline=False)
    T.text_ru(cv, 70, 322, "Чёрный бор", C["ink"], outline=False)
    marker(cv, *M1, "current", selected=True, num="1")
    marker(cv, *M2, "locked")
    marker(cv, *M3, "locked")
    map_label(cv, M1[0], M1[1] + 17, "1 · Огонь на капище", C["red"])
    map_label(cv, M2[0] + 4, M2[1] + 11, "2 · Сопки Волхова", C["slate"])
    map_label(cv, M3[0] + 14, M3[1] - 24, "3 · Разлом в Чёрном бору", C["slate"])
    info_panel(cv, 434, 30, 192, 316)
    # cursor hovers the locked M2 -> its card (M1 stays selected in the panel)
    card = m2_card(cv, 249, 100)          # v1.4: taller (zone line)
    assert card[0] + card[2] <= 424 and card[1] + card[3] < M2[1] - 9, card
    U.cursor(cv, M2[0] + 3, M2[1] + 2)
    SC.export(cv, "mockup_act_map_v2")


if __name__ == "__main__":
    main()

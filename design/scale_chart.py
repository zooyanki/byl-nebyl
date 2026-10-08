"""Линейка масштаба (стандарт /workspace/game/design/scale.md).
Все размеры в нативных px (640x360), экспорт x3 NEAREST.
Запуск: python3 scale_chart.py  -> scale_chart.png (x3) и scale_chart_native.png
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "art", "ui", "src"))
import theme_rus as T
T.activate()
import pixelkit as pk
from pixelkit import C, Canvas
from fonts_ru import FONT_RU

W, H = 1060, 690
cv = Canvas(W, H, C["night"])
HERO, DOOR = 44, 56


def tw(s):
    return pk.text_width(s, FONT_RU)


def label(cx, y, lines, col=C["birch"]):
    for i, s in enumerate(lines):
        cv.text(cx - tw(s) // 2, y + i * 10, s, col, font=FONT_RU, shadow=C["ink"])


def box(x, base, w, h, fill, edge=C["ink"]):
    cv.rect(x, base - h, w, h, fill)
    cv.frame(x, base - h, w, h, edge)


def tri(pts, fill):
    cv.poly(pts, fill, outline=C["ink"])


def panel(y0, y1, title, base, maxh):
    cv.rect(0, y0, W, y1 - y0, C["slate_dk"])
    cv.hline(0, y0, W, C["bronze"])
    cv.text(6, y0 + 3, title, C["bronze_lt"], font=FONT_RU)
    # ruler + grid every 16 px (1 высота тайла)
    for h in range(0, maxh + 1, 16):
        y = base - h
        for x in range(30, W - 4, 4):
            cv.px(x, y, C["slate"])
        cv.text(4, y - 4, str(h), C["mist"], font=FONT_RU, shadow=None)
    for h, s, c in ((HERO, "герой 44", C["red_lt"]), (DOOR, "дверь 56", C["bronze_hi"])):
        y = base - h
        for x in range(30, W - 4, 2):
            cv.px(x, y, c)
        cv.text(W - tw(s) - 4, y - 10, s, c, font=FONT_RU)
    cv.hline(30, base, W - 34, C["earth"])


def hum(x, base, w, h, fill, head=True):
    """Простой силуэт: корпус-прямоугольник + голова."""
    hd = max(5, round(h / 6.3))
    if head:
        box(x, base, w, h - hd, fill)
        hw = max(4, round(w * 0.45))
        box(x + (w - hw) // 2, base - h + hd, hw, hd + 1, fill)
    else:
        box(x, base, w, h, fill)


def diamond(cx, base, c):
    pts = [(cx - 16, base), (cx, base - 8), (cx + 16, base), (cx, base + 8)]
    for (a, b), (d, e) in zip(pts, pts[1:] + pts[:1]):
        cv.line(a, b, d, e, c)


def items(base, specs, x0=40, gap=6):
    x = x0
    for sp in specs:
        name, h, w, draw, slot = sp
        sw = max(slot, w + 8)
        cx = x + sw // 2
        draw(cx - w // 2, base, w, h)
        num = sp[1] if isinstance(sp[1], str) else str(h)
        top = base - (h if isinstance(h, int) else int(h.split("/")[-1]))
        cv.text(cx - tw(num) // 2, top - 11, num, C["bronze_hi"], font=FONT_RU)
        label(cx, base + 10, name)
        x += sw + gap
    return x


def H_(v):
    return v if isinstance(v, int) else int(v.split("/")[-1])


def F(fill, head=True):
    return lambda x, b, w, h: hum(x, b, w, H_(h), fill, head)


# ---------------------------------------------------------------- panel A
cv.text(6, 4, "Линейка масштаба · нативные px (640х360), показано х3 без сглаживания · тайл 32х16 · 1 тайл = 1 м по земле · 1 м высоты = 24 px · стандарт: scale.md",
        C["birch"], font=FONT_RU)
A0, AB = 18, 176
panel(A0, A0 + 196, "Персонажи и монстры: видимый рост от ступней до макушки", AB, 128)


def wolf(x, b, w, h):
    box(x, b, w, 20, C["moss"]); box(x, b - 14, 10, 12, C["moss"])


specs_a = [
    (["Ратибор"], 44, 22, F(C["red"]), 50),
    (["Мал"], 28, 14, F(C["linen"]), 44),
    (["NPC", "взрослый"], 44, 20, F(C["linen"]), 50),
    (["Навь"], 24, 14, F(C["moss"]), 44),
    (["Анчутка"], 26, 18, F(C["moss"]), 50),
    (["Кикимора"], 36, 20, F(C["moss"]), 52),
    (["Упырь"], 40, 24, F(C["stone_lt"]), 46),
    (["Мертвяк"], 44, 26, F(C["stone_lt"]), 50),
    (["Черно-", "ярец"], 46, 22, F(C["linen"]), 46),
    (["Чернояр", "(ф. 1)"], 46, 22, F(C["linen"]), 50),
    (["Волколак"], 60, 34, F(C["bronze"]), 54),
    (["Леший"], 80, 36, F(C["bronze"]), 52),
    (["Кривша"], 96, 44, F(C["blue"]), 56),
    (["Курганный", "князь"], 100, 44, F(C["blue"]), 58),
    (["Волко-", "длак"], 104, 48, F(C["blue"]), 60),
]
print("A end", items(AB, specs_a))
diamond(40 + 25, AB, C["bronze_lt"])
# category legend
lx = 40
for s, c in (("герой", C["red"]), ("NPC", C["linen"]), ("мелкие", C["moss"]), ("обычные", C["stone_lt"]),
             ("крупные", C["bronze"]), ("боссы", C["blue"])):
    cv.rect(lx + 330, A0 + 4, 7, 7, c); cv.frame(lx + 330, A0 + 4, 7, 7, C["ink"])
    cv.text(lx + 340, A0 + 3, s, C["birch"], font=FONT_RU); lx += tw(s) + 20

# ---------------------------------------------------------------- panel B1
B0, BB = A0 + 200, A0 + 200 + 136
panel(B0, B0 + 160, "Окружение: малое и среднее (дверь = 1,27 роста героя)", BB, 112)


def door(x, b, w, h):
    box(x - 2, b, w + 4, h + 2, C["wood_lt"]); box(x, b, w, h, C["ink"], C["wood"])


def chest(x, b, w, h):
    box(x, b, w, h, C["wood_md"]); cv.hline(x + 1, b - h + 5, w - 2, C["bronze"])


def barrel(x, b, w, h):
    box(x, b, w, h, C["wood_md"])
    for k in (5, h - 6):
        cv.hline(x + 1, b - k, w - 2, C["iron"])


def bush(x, b, w, h):
    cv.disc(x + w // 2, b - h // 2, h // 2, C["pine"])
    cv.rect(x, b - h // 2, w, h // 2, C["pine"]); cv.hline(x, b, w, C["ink"])


def fence(x, b, w, h):
    for i in range(0, w, 6):
        box(x + i, b, 5, h - 3, C["wood"]); tri([(x + i, b - h + 3), (x + i + 4, b - h + 3), (x + i + 2, b - h)], C["wood"])


def gate(x, b, w, h):  # проём 72, столбы 96
    box(x, b, 6, 96, C["wood_md"]); box(x + w - 6, b, 6, 96, C["wood_md"])
    box(x - 2, b - 84, w + 4, 6, C["wood_lt"])
    cv.rect(x + 6, b - 72, w - 12, 72, C["ink"])


def idol(x, b, w, h):
    box(x, b, w, h - 6, C["wood_md"]); tri([(x, b - h + 6), (x + w - 1, b - h + 6), (x + w // 2, b - h)], C["bronze"])


def kurgan(x, b, w, h):
    import numpy as np
    for i in range(w):
        t = (i - w / 2) / (w / 2)
        hh = int(h * (1 - t * t) ** 0.6)
        cv.rect(x + i, b - hh, 1, hh, C["moss"])
        cv.px(x + i, b - hh, C["ink"])


def krada(x, b, w, h):
    box(x, b, w, 24, C["wood"])
    tri([(x + 6, b - 24), (x + w - 6, b - 24), (x + w // 2, b - h)], C["flame"])
    tri([(x + 12, b - 24), (x + w - 12, b - 24), (x + w // 2, b - h + 16)], C["gold_lt"])


def bridge(x, b, w, h):
    box(x, b - 24, w, 8, C["wood_md"])  # настил на высоте 24 над водой
    cv.rect(x, b - 23, w, 23, C["sea"])
    for i in range(0, w, 12):
        box(x + i, b - 32, 3, 24, C["wood"])
    box(x, b - 53, w, 3, C["wood_lt"])
    box(x + 4, b, 6, 24, C["wood_dk"]); box(x + w - 10, b, 6, 24, C["wood_dk"])


specs_b1 = [
    (["Герой"], 44, 22, F(C["red"]), 44),
    (["Дверь", "сруба"], 56, 24, door, 44),
    (["Сундук"], 16, 22, chest, 40),
    (["Бочка"], 24, 18, barrel, 40),
    (["Куст"], 24, 28, bush, 40),
    (["Плетень"], 28, 30, fence, 44),
    (["Частокол"], 80, 30, fence, 48),
    (["Ворота", "72/96"], "72/96", 44, gate, 56),
    (["Чур"], 64, 14, idol, 40),
    (["Идол", "Перуна"], 104, 24, idol, 50),
    (["Курган", "малый 6х6 т."], 40, 110, kurgan, 110),
    (["Крада", "дрова 24"], 72, 40, krada, 56),
    (["Мост", "перила 24"], 56, 72, bridge, 80),
]
print("B1 end", items(BB, specs_b1))

# ---------------------------------------------------------------- panel B2
C0, CB = B0 + 164, B0 + 164 + 268
panel(C0, H, "Окружение: крупное (кровли, деревья, ладья)", CB, 240)


def srub(x, b, w, h):  # стена 68, конёк 112, конёк-голова 124
    box(x, b, w, 68, C["wood"])
    for k in range(4, 68, 4):
        cv.hline(x + 1, b - k, w - 2, C["wood_dk"])
    tri([(x - 6, b - 68), (x + w + 5, b - 68), (x + w // 2, b - 112)], C["wood_md"])
    box(x + w // 2 - 2, b - 112, 5, 12, C["wood_lt"])
    box(x + 12, b - 4, 24, 56, C["ink"], C["wood_lt"])   # дверь
    hum(x + w - 30, b, 22, 44, C["red"])                 # герой у стены


def terem(x, b, w, h):
    box(x, b, w, 24, C["stone"])
    box(x, b - 24, w, 64, C["wood"]); box(x - 6, b - 88, w + 12, 4, C["wood_lt"])  # гульбище
    box(x + 8, b - 88, w - 16, 64, C["wood"])
    tri([(x + 4, b - 152), (x + w - 5, b - 152), (x + w // 2, b - 192)], C["wood_md"])
    box(x + w // 2 - 12, b - 24, 24, 56, C["ink"], C["wood_lt"])
    hum(x - 26, b, 22, 44, C["red"])


def tree(x, b, w, h, col=C["pine"], trunk=6, bare=0.0):
    tb = int(h * bare)
    box(x + w // 2 - trunk // 2, b, trunk, max(10, tb + 6), C["wood_dk"])
    top, bot = b - h, b - max(10, tb)
    tiers = 4 if bare < 0.3 else 2
    for i in range(tiers):
        ya = top + (bot - top) * i // tiers
        yb = top + (bot - top) * (i + 1) // tiers + 4
        hw = (w // 2) * (i + 2) // (tiers + 1)
        tri([(x + w // 2 - hw, yb), (x + w // 2 + hw, yb), (x + w // 2, ya)], col)


def birch(x, b, w, h):
    box(x + w // 2 - 2, b, 4, h - 30, C["birch"])
    cv.disc(x + w // 2, b - h + 28, 26, C["gold"]); cv.disc(x + w // 2, b - h + 28, 26, C["gold"])


def ship(x, b, w, h):  # длина 192, борт 28, штевни 84, мачта 150
    wl = b - 4
    cv.rect(x - 4, wl, w + 8, 4, C["sea"])
    tri([(x + 10, wl), (x + w - 10, wl), (x + w, wl - 28), (x, wl - 28)], C["wood"])
    box(x, wl - 28, 8, 56, C["wood_md"]); box(x - 8, wl - 72, 14, 12, C["wood_md"])  # нос + голова змея (84)
    box(x + w - 8, wl - 28, 8, 48, C["wood_md"])
    for i in range(14):
        cv.disc(x + 20 + i * 11, wl - 21, 6, C["red"] if i % 2 else C["birch"])
    mx = x + w // 2
    box(mx - 1, wl - 28, 3, 150 - 28, C["wood_dk"])
    box(mx - 32, wl - 60, 64, 72, C["red"])
    for k in range(0, 64, 9):
        cv.rect(mx - 31 + k, wl - 131, 4, 70, C["birch"])
    hum(x + 40, wl - 28 + 0, 22, 44, C["red"])  # герой на палубе (условно)


specs_b2 = [
    (["Герой"], 44, 22, F(C["red"]), 40),
    (["Сруб 4х4 т.", "стена 68, конёк 112"], 124, 104, srub, 128),
    (["Терем 5х5 т.", "до шатра 192"], 192, 116, terem, 160),
    (["Берёза"], 112, 56, birch, 64),
    (["Ель"], 150, 60, tree, 66),
    (["Сосна"], 180, 56, lambda x, b, w, h: tree(x, b, w, h, C["pine_dk"], 8, 0.55), 64),
    (["Вековая", "ель"], 240, 90, lambda x, b, w, h: tree(x, b, w, h, C["pine_dk"], 12), 96),
    (["Ладья 12 тайлов: борт 28,", "штевень 84, мачта 150"], 150, 192, ship, 210),
]
print("B2 end", items(CB, specs_b2))

big = cv.save(os.path.join(HERE, "scale_chart.png"), scale=3)
cv.save(os.path.join(HERE, "scale_chart_native.png"))
print("ok", big.size)

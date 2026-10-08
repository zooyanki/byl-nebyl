"""Inventory screen, theme «Гардарики» (v2).
python3 inventory_v2.py -> ../mockup_inventory_v2_{native,1920x1080}.png"""
import pixelkit as pk
import screens_common_v2 as SC
from pixelkit import C, Canvas, FONT3x5
from fonts_ru import FONT_RU, FONT_USTAV
import theme_rus as T
import ui_rus as U
import items_rus as IR

CELL = 24
WX, WY, WW, WH = 322, 8, 314, 284


def cell_rect(gx0, gy0, c, r, w=1, h=1):
    return gx0 + c * CELL, gy0 + r * CELL, w * CELL, h * CELL


def silhouette(cv, cx, top):
    """Faint carved druzhinnik figure behind the equipment slots."""
    m = pk.MatCanvas(96, 132)
    m.poly([(48, 0), (58, 14), (38, 14)], "k")                       # helm cone
    m.ellipse(48, 20, 9, 10, "k")                                    # head
    m.poly([(26, 32), (70, 32), (78, 44), (74, 98), (22, 98), (18, 44)], "k")   # torso + mail
    m.poly([(18, 36), (8, 70), (4, 92), (14, 94), (24, 60)], "k")    # right arm (screen left)
    m.poly([(78, 36), (88, 70), (92, 92), (82, 94), (72, 60)], "k")
    m.poly([(28, 96), (46, 96), (44, 130), (30, 130)], "k")          # legs
    m.poly([(50, 96), (68, 96), (66, 130), (52, 130)], "k")
    msk = m.a == "k"
    x0 = cx - 48
    sub = cv.a[top:top + 132, x0:x0 + 96]
    import numpy as np
    edge = msk & ~(np.roll(msk, 1, 0) & np.roll(msk, -1, 0) & np.roll(msk, 1, 1) & np.roll(msk, -1, 1))
    sub[msk] = C["wood_dk"]
    sub[edge] = C["wood"]
    b = pk.bayer(132, 96)
    sub[msk & ~edge & (b < 0.18)] = C["wood"]


def equip_slot(cv, S, x, y, w, h, item=None, rarity=None, label=None):
    T.wood_slot(cv, x, y, w, h)
    if item:
        IR.draw_item(cv, S[item], x, y, w, h, rarity, tint=0.35)
    elif label:
        T.text_ru(cv, x + w // 2 + 1, y + h // 2 - 4, label, C["slate"], align="c", outline=False)


def grid(cv, gx, gy, cols=10, rows=4):
    cv.rect(gx - 3, gy - 3, cols * CELL + 6, rows * CELL + 6, C["ink"])
    cv.frame(gx - 2, gy - 2, cols * CELL + 4, rows * CELL + 4, C["bronze_dk"])
    cv.hline(gx - 2, gy - 2, cols * CELL + 4, C["bronze"])
    for r in range(rows):
        for c in range(cols):
            x, y = gx + c * CELL, gy + r * CELL
            cv.rect(x, y, CELL, CELL, C["night"])
            cv.dither(x + 1, y + 1, CELL - 2, CELL - 2, C["wood_dk"], 0.35)
            cv.frame(x, y, CELL, CELL, C["ink"])
            cv.hline(x + 1, y + CELL - 1, CELL - 1, C["wood"]); cv.vline(x + CELL - 1, y + 1, CELL - 1, C["wood"])
            cv.px(x + 1, y + 1, C["wood_dk"])


def place(cv, S, gx, gy, item, c, r, w, h, rarity=None, hover=False):
    x, y, ww, hh = cell_rect(gx, gy, c, r, w, h)
    if hover:
        cv.dither(x + 1, y + 1, ww - 1, hh - 1, C["bronze"], 0.45)
        cv.frame(x, y, ww + 1, hh + 1, C["bronze_lt"])
    elif rarity:
        cv.dither(x + 1, y + 1, ww - 1, hh - 1, C[IR.RARITY[rarity][1]], 0.4)
    if callable(item):
        item(cv, x, y, ww, hh)
    else:
        IR.draw_item(cv, S[item], x, y, ww + 1, hh + 1)
    return x, y, ww, hh


def potion(kind):
    def f(cv, x, y, w, h):
        T.potion(cv, x + (w - 12) // 2 + 1, y + (h - 15) // 2 + 1, kind)
    return f


def stack(n):
    def f(cv, x, y, w, h, _n=n):
        pk.key_label(cv, x + w - 8, y + h - 6, str(_n), C["linen"])
    return f


def main():
    """Котомка (I) for the level-4 hero of mission 1 (GDD §6, §10, §12.1.1 A5):
    no weapon-set tabs, no gems/sockets, no durability, no attribute requirement.
    Worn gear (GDD v1.4 §6.2 стартовый комплект + A5/A13) matches the «Витязь» window:
    Защита 31 = короткая кольчуга 10 + клёпаный шелом 4 + малый щит 5 + кожаные рукавицы 3 +
    поршни 2 + кожаный пояс 2 + ⌊22/4⌋ 5; перстень «…живота» +10 к жизни (T1 max, ilvl <= 6);
    гривна «Ярая … Сварога»: +8 к Яри, +10% сопр. огню (both T1)."""
    cv, HS = SC.scene(shift=-205)
    S = IR.build()
    ix, iy, iw, ih = U.window(cv, WX, WY, WW, WH, title="КОТОМКА")
    cx = WX + WW // 2
    # ---- equipment (кукла, 10 slots) ---------------------------------------------
    top = iy + 12
    silhouette(cv, cx, top + 2)
    ey = top + 12
    equip_slot(cv, S, cx - 16, ey - 10, 32, 32, "shelom_klep", "normal")               # клёпаный шелом (простой)
    equip_slot(cv, S, cx + 22, ey - 2, 24, 24, "grivna", "magic")                      # гривна
    equip_slot(cv, S, cx - 25, ey + 26, 50, 66, "kolchuga_eq", "normal")               # короткая кольчуга (простая)
    equip_slot(cv, S, ix + 8, ey, 46, 76, "scramasax", "magic")                        # десница: скрамасакс
    equip_slot(cv, S, ix + iw - 54, ey, 46, 76, "shield_small", "normal")              # шуйца: малый щит
    by = ey + 88
    equip_slot(cv, S, ix + 12, by - 4, 32, 30, "rukavitsy_kozh", "normal")             # кожаные рукавицы
    equip_slot(cv, S, cx - 49, by, 22, 22, "ring_ruby", "magic")                       # перстень
    equip_slot(cv, S, cx - 25, by + 1, 50, 20, "poyas_kozh", "normal")                 # кожаный пояс (v1.4, было «кушак»)
    equip_slot(cv, S, cx + 27, by, 22, 22, None, label="")                             # перстень (пусто)
    cv.disc(cx + 38, by + 12, 4.5, C["slate_dk"]); cv.disc(cx + 38, by + 12, 2.5, C["night"])
    equip_slot(cv, S, ix + iw - 44, by - 4, 32, 30, "porshni", "normal")               # поршни
    for (x, s) in ((ix + 31, "Десница"), (ix + iw - 31, "Шуйца")):
        T.text_ru(cv, x, ey + 77, s, C["wood_lt"], align="c", outline=False)
    # ---- divider + bag grid 10x4 -----------------------------------------------
    dy = by + 27
    U.section_title(cv, ix + 6, dy, iw - 12, "Поклажа")
    gx = ix + (iw - 10 * CELL) // 2
    gy = dy + 12
    grid(cv, gx, gy)
    used = 0
    for (it, c, r, w, h, rar, hov) in (
            ("sword", 0, 0, 1, 3, "magic", True),          # Калёный меч сокола (база «Меч дружинника», треб. ур. 6)
            ("axe", 1, 0, 1, 3, "normal", False),          # Топорик
            ("shield", 2, 0, 2, 2, "normal", False),       # Круглый щит (треб. ур. 5)
            ("rukavitsy_kozh", 2, 2, 2, 2, "magic", False),  # кожаные (боевые треб. 8 > ilvl)
            (potion("life"), 4, 0, 1, 1, None, False),
            (potion("life"), 5, 0, 1, 1, None, False),
            (potion("mana"), 4, 1, 1, 1, None, False),
            (potion("zhivaya"), 5, 1, 1, 1, None, False),
            ("beresta", 6, 0, 1, 1, None, False),
            ("ring_amber", 6, 1, 1, 1, "magic", False),
            ("lunnitsa", 7, 0, 1, 1, "magic", False),
            ("gromovnik", 7, 1, 1, 1, "rare", False)):
        place(cv, S, gx, gy, it, c, r, w, h, rar, hover=hov)
        used += w * h
    assert used == 22, used
    bx, by2, bw, bh = cell_rect(gx, gy, 6, 0)
    pk.key_label(cv, bx + bw - 7, by2 + bh - 7, "3", C["linen"])     # стопка бересты
    # ---- footer: places + silver ----------------------------------------------------
    fy = gy + 4 * CELL + 5
    U.recess(cv, ix + iw - 92, fy, 86, 13)
    U.silver_icon(cv, ix + iw - 89, fy + 2)
    T.text_ru(cv, ix + iw - 9, fy + 3, "284", C["linen"], align="r", outline=False)
    T.text_ru(cv, ix + iw - 98, fy + 3, "Серебро:", C["birch"], align="r", outline=False)
    T.text_ru(cv, ix + 6, fy + 3, "Места: %d/40" % used, C["mist"], outline=False)
    # ---- tooltip for the hovered sword (GDD §12.1.1 A5 example) -----------------
    sx, sy, _, _ = cell_rect(gx, gy, 0, 0)
    curx, cury = sx + 14, sy + 30
    lines = [
        # GDD v1.4: short name + suffix (§6.2), rarity line «… вещь» (§6.3, A13), affixes at T1 (ilvl <= 6):
        # Урон = 4–11 × 1,20 (Калёный +20%) = 4–13
        ("Калёный меч сокола", C["blue_lt"]),
        ("Заговорённая вещь", C["blue"]),
        ("Меч дружинника", C["birch"]),
        ("Урон: 4–13", C["linen"]),
        ("Требуется уровень: 6", C["red_lt"]),
        ("+20% к урону", C["blue_lt"]),
        ("+10% к скорости атаки", C["blue_lt"]),
        ("Снарядить можно с 6-го уровня", C["mist"]),
    ]
    U.tooltip(cv, WX - 3, cury - 40, lines, anchor="tr", sep_after=(2, 4, 6))
    U.cursor(cv, curx, cury)
    SC.export(cv, "mockup_inventory_v2")


if __name__ == "__main__":
    main()

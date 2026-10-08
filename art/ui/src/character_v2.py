"""Character screen, theme «Гардарики» (v2).
python3 character_v2.py -> ../mockup_character_v2_{native,1920x1080}.png"""
import math
import pixelkit as pk
import screens_common_v2 as SC
from pixelkit import C
from fonts_ru import FONT_RU, FONT_USTAV
import theme_rus as T
import ui_rus as U

WX, WY, WW, WH = 4, 8, 314, 284


def field(cv, x, y, w, label, value, lc=None, vc=None, h=13):
    U.recess(cv, x, y, w, h)
    T.text_ru(cv, x + 4, y + 3, label, C["birch"] if lc is None else lc, outline=False)
    T.text_ru(cv, x + w - 4, y + 3, value, C["linen"] if vc is None else vc, align="r", outline=False)


def res_icon(cv, x, y, kind):
    if kind == "fire":
        for (dx, dy, c) in ((3, 0, "flame"), (2, 1, "ember"), (3, 1, "flame"), (4, 2, "ember"), (1, 3, "red_lt"), (2, 2, "ember"),
                            (2, 3, "flame"), (3, 3, "flame"), (4, 3, "ember"), (1, 4, "red_lt"), (2, 4, "ember"), (3, 4, "flame"),
                            (4, 4, "ember"), (5, 4, "red_lt"), (1, 5, "red"), (2, 5, "red_lt"), (3, 5, "ember"), (4, 5, "red_lt"), (5, 5, "red")):
            cv.px(x + dx, y + dy, C[c])
    elif kind == "cold":
        cx, cy = x + 3, y + 3
        for k in range(-3, 4):
            cv.px(cx + k, cy, C["blue_lt"]); cv.px(cx, cy + k, C["blue_lt"])
        for k in (-2, 2):
            cv.px(cx + k, cy + k, C["blue"]); cv.px(cx + k, cy - k, C["blue"])
        cv.px(cx, cy, C["linen"])
    elif kind == "bolt":
        for (dx, dy) in ((4, 0), (3, 1), (2, 2), (3, 3), (4, 3), (3, 4), (2, 5), (1, 6)):
            cv.px(x + dx, y + dy, C["flame"])
        cv.px(x + 2, y + 3, C["linen"])
    elif kind == "poison":
        for (dx, dy) in ((3, 0), (3, 1), (2, 2), (4, 2), (1, 3), (5, 3), (1, 4), (5, 4), (2, 5), (3, 5), (4, 5)):
            cv.px(x + dx, y + dy, C["nebyl"])
        cv.px(x + 3, y + 3, C["moss_lt"]); cv.px(x + 2, y + 4, C["moss"]); cv.px(x + 3, y + 4, C["nebyl_dk"]); cv.px(x + 4, y + 4, C["moss"])
        cv.px(x + 2, y + 3, C["linen"])


def portrait(cv, S, x, y, w, h):
    U.recess(cv, x, y, w, h, fill=C["wood_dk"])
    # warm hearth glow behind the hero
    cx, cy = x + w // 2, y + h - 18
    for r, d, c in ((26, 0.25, "wood"), (20, 0.35, "wood_md"), (13, 0.25, "bronze_dk")):
        import numpy as np
        yy, xx = np.mgrid[0:cv.h, 0:cv.w]
        m = (np.hypot(xx - cx, (yy - cy) * 1.2) < r) & (pk.bayer(cv.h, cv.w) < d)
        m &= (xx > x) & (xx < x + w - 1) & (yy > y) & (yy < y + h - 1)
        cv.a[m] = C[c]
    hero = S["hero_doll"]          # portrait art (scale.md §4.4), not the 44-px game sprite
    cv.blit(pk.sprite_to_index(hero), x + (w - hero["w"]) // 2, y + h - hero["h"] - 2)
    cv.frame(x - 1, y - 1, w + 2, h + 2, C["bronze"])
    for (cx_, cy_, sx, sy) in ((x - 1, y - 1, 1, 1), (x + w, y - 1, -1, 1), (x - 1, y + h, 1, -1), (x + w, y + h, -1, -1)):
        T.bronze_corner(cv, cx_, cy_, sx, sy, 5)


# Level-4 hero in mission 1 (GDD §3.2–3.5, §6.2, scale/teaser numbers; mana = «Ярь», STR = «Сила»):
# GDD v1.4 gear (inventory_v2 doll): клёпаный шелом, короткая кольчуга, скрамасакс, малый щит,
#   кожаные рукавицы, поршни, кожаный пояс; affixes T1 only (ilvl <= 6 in mission 1).
#   attributes: start 20/20/25/15, +15 points over 3 level-ups, 12 spent (+3/+2/+5/+2), 3 free (HUD «+»)
#   Жизнь  = 20 + 2·30 + 4·3 + 10 (перстень «…живота», T1 max) = 102
#   Ярь    = 10 + 2·17 + 2·3 + 8 (оберег)                 = 58
#   Меткость = 5·22 + 5·4                                 = 130
#   Защита = короткая кольчуга 10 + клёпаный шелом 4 + малый щит 5 + кожаные рукавицы 3 + поршни 2
#            + кожаный пояс 2 + ⌊22/4⌋ 5 = 31
#   Удачный удар = 5% + 0,1%·22 + меч 10%                 = 17%
#   Урон ЛКМ: скрамасакс 2–7 × (1 + 23/100 + 15% ED)      = 2–9
#   Урон ПКМ: Огненный змей ранг 2 9–15 × (1 + 17/100)    = 10–17
#   Шанс попасть по упырю ур. 4 (DEF 8+6·4=32): 2·130/162 · 4/8 = 80%
#   Опыт 1 700: ур. 4 с 1 120, ур. 5 с 2 250 -> 51%
STATS = dict(level=4, xp="1 700", next="2 250", ratio=(1700 - 1120) / (2250 - 1120),
             attrs=(("Сила", "23"), ("Ловкость", "22"), ("Живучесть", "30"), ("Дух", "17")), free=3,
             derived=(("Урон ЛКМ", "2–9", None), ("Урон ПКМ", "10–17", C["ember"]), ("Меткость", "130", None),
                      ("Шанс попасть", "80%", None), ("Защита", "31", None), ("Удачный удар", "17%", None),
                      ("Жизнь", "95 / 102", C["red_lt"]), ("Ярь", "50 / 58", C["blue_lt"])),
             res=(("fire", "Огню", "10%", C["ember"]), ("cold", "Холоду", "0%", C["blue_lt"]),
                  ("poison", "Порче", "0%", C["nebyl"])))


def main():
    cv, S = SC.scene(shift=160)
    st = STATS
    ix, iy, iw, ih = U.window(cv, WX, WY, WW, WH, title="ВИТЯЗЬ")
    # ---- header: portrait, name, class, level, experience -----------------------
    top = iy + 13
    portrait(cv, S, ix + 6, top, 54, 68)
    hx = ix + 70
    T.text_ru(cv, hx, top - 1 - FONT_USTAV["top"] + 1, "РАТИБОР", C["bronze_hi"], font=FONT_USTAV)
    T.text_ru(cv, hx, top + 15, "Дружинник · Княжья дружина", C["birch"], outline=False)
    # level medallion
    lx, ly = ix + iw - 30, top + 15
    cv.disc(lx, ly, 13, C["ink"]); cv.disc(lx, ly, 12, C["bronze"]); cv.disc(lx - 0.5, ly - 0.5, 10, C["wood_dk"])
    T.rosette(cv, lx - 0.5, ly - 0.5, 10, C["bronze_dk"])
    cv.disc(lx - 0.5, ly - 0.5, 6.5, C["wood_dk"])
    T.text_ru(cv, lx + 1, ly - 4, str(st["level"]), C["bronze_hi"], align="c")
    T.text_ru(cv, lx + 1, ly + 15, "Уровень", C["bronze_lt"], align="c", outline=False)
    field(cv, hx, top + 28, 150, "Опыт", st["xp"])
    field(cv, hx, top + 43, 150, "До уровня %d" % (st["level"] + 1), st["next"], lc=C["mist"], vc=C["mist"])
    pk.bar(cv, hx, top + 60, 150, 5, st["ratio"], ramp="bronze", ticks=10)
    T.text_ru(cv, ix + iw - 6, top + 58, "%d%%" % round(st["ratio"] * 100), C["bronze_lt"], align="r", outline=False)
    # ---- attributes --------------------------------------------------------------
    sy = top + 78
    colw = (iw - 18) // 2
    lx0, rx0 = ix + 6, ix + 12 + colw
    U.section_title(cv, lx0, sy, colw, "Свойства")
    U.section_title(cv, rx0, sy, colw, "Показатели")
    ry = sy + 13
    for k, (lab, val) in enumerate(st["attrs"]):
        y = ry + k * 17
        field(cv, lx0, y, colw - 18, lab, val, vc=C["bronze_hi"])
        U.plus_button(cv, lx0 + colw - 12, y + 1, 11, active=True)
    # unspent points
    py = ry + 4 * 17 + 2
    cv.rect(lx0, py, colw, 15, C["ink"])
    cv.rect(lx0 + 1, py + 1, colw - 2, 13, C["red_dk"])
    cv.dither(lx0 + 2, py + 2, colw - 4, 11, C["red"], 0.3)
    cv.frame(lx0 + 1, py + 1, colw - 2, 13, C["ember"])
    T.text_ru(cv, lx0 + 5, py + 4, "Свободных очков", C["flame"], outline=False)
    T.text_ru(cv, lx0 + colw - 6, py + 4, str(st["free"]), C["linen"], align="r")
    for k, (lab, val, vc) in enumerate(st["derived"]):
        y = ry + k * 15
        field(cv, rx0, y, colw, lab, val, vc=vc)
    # ---- resistances (left column, under the points) -----------------------------
    rsy = py + 21
    U.section_title(cv, lx0, rsy, colw, "Сопротивления")
    for k, (kind, lab, val, col) in enumerate(st["res"]):
        y = rsy + 13 + k * 15
        U.recess(cv, lx0, y, colw, 13)
        res_icon(cv, lx0 + 3, y + 3, kind)
        T.text_ru(cv, lx0 + 13, y + 3, lab, col, outline=False)
        T.text_ru(cv, lx0 + colw - 4, y + 3, val, C["linen"], align="r", outline=False)
    # ---- hint --------------------------------------------------------------------
    hy = max(rsy + 13 + 3 * 15, ry + 8 * 15) + 6
    T.text_ru(cv, ix + iw // 2, hy, "Жми [+], чтобы вложить свободные очки", C["mist"], align="c", outline=False)
    # hover tooltip on the "+" next to Сила
    bx, by_ = lx0 + colw - 12, ry + 1
    cv.frame(bx - 1, by_ - 1, 13, 13, C["flame"])            # hovered "+"
    cv.rect(bx + 3, by_ + 5, 5, 1, C["linen"]); cv.rect(bx + 5, by_ + 3, 1, 5, C["linen"])
    U.cursor(cv, bx + 6, by_ + 6)
    SC.export(cv, "mockup_character_v2")


if __name__ == "__main__":
    main()

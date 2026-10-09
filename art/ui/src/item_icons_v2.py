"""Base-item icon review sheet for GDD v1.4 (A13): renamed bases + the level-4 doll set.
python3 item_icons_v2.py -> ../item_icons_v2_x3.png (native 342x292 x3, palette v2 only)."""
import os
import numpy as np
import gameplay_hud_v2 as G          # activates palette v2
import pixelkit as pk
from pixelkit import C, Canvas
from fonts_ru import FONT_RU
import theme_rus as T
import ui_rus as U
import items_rus as IR

W, H = 342, 292

# GDD v1.4 §6.2: 6 types x 3 bases + 4 types x 2 + перстень 1 = 27 («28» in v1.1-v1.3 was a counting error)
BASES = (
    ("Меч", ("Скрамасакс", "Меч дружинника", "Меч-каролинг")),
    ("Топор", ("Топорик", "Секира", "Бородовидная секира")),
    ("Посох", ("Посох странника", "Резной посох", "Посох волхва")),
    ("Тело", ("Короткая кольчуга", "Кольчуга", "Дощатая броня")),
    ("Голова", ("Клёпаный шелом", "Шелом с наносником", "Шелом с полумаской")),
    ("Щит", ("Малый щит", "Круглый щит", "Каплевидный щит")),
    ("Рукавицы", ("Кожаные рукавицы", "Боевые рукавицы")),
    ("Ноги", ("Поршни", "Сапоги")),
    ("Пояс", ("Кожаный пояс", "Наборный пояс")),
    ("Шея", ("Оберег-подвеска", "Гривна")),
    ("Перстень", ("Перстень",)),
)
assert sum(len(b) for _, b in BASES) == 27
RENAMED = {"Дощатая броня", "Клёпаный шелом", "Шелом с полумаской", "Боевые рукавицы", "Кожаный пояс"}

# (sprite key, cell w x h in 24-px cells, caption, note)
ICONS = (
    ("shelom_klep", 2, 2, "Клёпаный шелом", "новое имя"),
    ("kolchuga_eq", 2, 3, "Короткая кольчуга", ""),
    ("doshchataya", 2, 3, "Дощатая броня", "новое имя"),
    ("rukavitsy_kozh", 2, 2, "Кожаные рукавицы", ""),
    ("rukavitsy_boevye", 2, 2, "Боевые рукавицы", "новое имя"),
    ("poyas_kozh", 2, 1, "Кожаный пояс", "новое имя"),
)


def main():
    cv = Canvas(W, H)
    cv.a[:] = C["night"]
    cv.dither(0, 0, W, H, C["wood_dk"], 0.25)
    S = IR.build()
    T.text_ru(cv, W // 2, 3, "Базы предметов · GDD 1.4 · всего 27", C["bronze_lt"], align="c")
    # ---- icons on 24-px cells -------------------------------------------------------
    x, y0 = 6, 18
    for key, cw, ch, cap, note in ICONS:
        w, h = cw * 24, ch * 24
        y = y0
        T.wood_slot(cv, x, y, w, h)
        IR.draw_item(cv, S[key], x, y, w, h, "normal", tint=0.3)
        T.text_ru(cv, x + w // 2 + 1, y + h + 3, cap.split()[0], C["linen"], align="c", outline=False)
        T.text_ru(cv, x + w // 2 + 1, y + h + 12, " ".join(cap.split()[1:]), C["linen"], align="c", outline=False)
        if note:
            T.text_ru(cv, x + w // 2 + 1, y + h + 21, note, C["flame"], align="c", outline=False)
        x += w + 6
    # ---- 27 bases list ----------------------------------------------------------------
    ly = 130
    U.section_title(cv, 4, ly - 2, W - 8, "Список баз · раздел 6.2")
    cols = ((4, BASES[:4]), (122, BASES[4:8]), (238, BASES[8:]))
    for (cx0, group) in cols:
        yy = ly + 12
        for typ, names in group:
            T.text_ru(cv, cx0, yy, typ, C["bronze_lt"], outline=False)
            yy += 9
            for nm in names:
                T.text_ru(cv, cx0 + 3, yy, nm, C["flame"] if nm in RENAMED else C["mist"], outline=False)
                yy += 9
            if yy > H - 12:
                break
    cv.save(os.path.join(G.OUT, "item_icons_v2_x3.png"), scale=3)
    big = np.array(cv.save(os.path.join(G.OUT, "item_icons_v2_native.png")))
    cols_ = {tuple(c) for c in big.reshape(-1, 3)}
    assert cols_ <= {tuple(c) for c in pk.RGB}, "off-palette colour!"
    print("item_icons_v2 ok")


if __name__ == "__main__":
    main()

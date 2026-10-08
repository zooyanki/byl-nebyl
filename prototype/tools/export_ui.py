"""Экспорт UI-ассетов из исходников художника (только чтение art/ui/src) в prototype/assets.
Запуск из папки prototype:  python3 tools/export_ui.py
Создаёт:
  assets/items.png + src/data/ui_atlas.js  — иконки предметов (items_rus.build), зелья, кукла героя
  assets/win_inventory.png                 — статичный фон окна «Котомка» (inventory_v2.py)
  assets/win_character.png                 — статичный фон окна «Витязь» (character_v2.py)
  assets/hud_buttons.png                   — кнопки C/I/T/M/J/ESC (gameplay_hud_v2.draw_buttons)
  assets/win_skills.png                    — фон окна «Навыки» (рамка ui_rus.window, слоты theme_rus.wood_slot)
  assets/hud_quest.png                     — рамка трекера задания с буквицей (gameplay_hud_v2.draw_quest без текста)
  иконки навыков theme_rus.ICONS (16/20/26 px) — в общий атлас items.png под ключами sk_<иконка>_<размер>
Прозрачность определяется рендером на двух разных фонах."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "art", "ui", "src"))
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image
import gameplay_hud_v2 as G            # активирует палитру v2
import pixelkit as pk
from pixelkit import C, Canvas
from fonts_ru import FONT_RU, FONT_USTAV
import theme_rus as T
import ui_rus as U
import items_rus as IR
import sprites_rus as SR
import inventory_v2 as INV
import character_v2 as CH

OUT = os.path.join(HERE, "..", "assets")
DATA = os.path.join(HERE, "..", "src", "data")
os.makedirs(OUT, exist_ok=True)
W, H = 640, 360
BG = (C["pine_dk"], C["red"])


def render(fn):
    """fn(cv) рисует; возвращает RGBA (H,W,4) с прозрачностью там, где результат зависит от фона."""
    res = []
    for bg in BG:
        cv = Canvas(W, H, fill=bg)
        fn(cv)
        res.append(cv.a.copy())
    a, b = res
    rgb = pk.RGB[a]
    alpha = np.where(a == b, 255, 0).astype(np.uint8)
    return np.dstack([rgb, alpha])


def crop_save(rgba, name):
    ys, xs = np.nonzero(rgba[:, :, 3])
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    Image.fromarray(rgba[y0:y1, x0:x1], "RGBA").save(os.path.join(OUT, name))
    return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}


meta = {}

# ---------------- окно «Котомка» -------------------------------------------------
def inv_bg(cv):
    WX, WY, WW, WH = INV.WX, INV.WY, INV.WW, INV.WH
    ix, iy, iw, ih = U.window(cv, WX, WY, WW, WH, title="КОТОМКА")
    cx = WX + WW // 2
    top = iy + 12
    INV.silhouette(cv, cx, top + 2)
    ey = top + 12
    by = ey + 88
    for (x, y, w, h) in INV_SLOTS(ix, iw, cx, ey, by):
        T.wood_slot(cv, x, y, w, h)
    cv.disc(cx + 38, by + 12, 4.5, C["slate_dk"]); cv.disc(cx + 38, by + 12, 2.5, C["night"])
    for (x, s) in ((ix + 31, "Десница"), (ix + iw - 31, "Шуйца")):
        T.text_ru(cv, x, ey + 77, s, C["wood_lt"], align="c", outline=False)
    dy = by + 27
    U.section_title(cv, ix + 6, dy, iw - 12, "Поклажа")
    gx = ix + (iw - 10 * INV.CELL) // 2
    gy = dy + 12
    INV.grid(cv, gx, gy)
    fy = gy + 4 * INV.CELL + 5
    U.recess(cv, ix + iw - 92, fy, 86, 13)
    U.silver_icon(cv, ix + iw - 89, fy + 2)
    T.text_ru(cv, ix + iw - 98, fy + 3, "Серебро:", C["birch"], align="r", outline=False)
    meta["inventory_layout"] = {"ix": ix, "iy": iy, "iw": iw, "ih": ih, "gx": gx, "gy": gy, "cell": INV.CELL, "fy": fy,
                                "close": [WX + WW - 22, WY + 9, 13], "win": [WX, WY, WW, WH]}


def INV_SLOTS(ix, iw, cx, ey, by):
    return [
        (cx - 16, ey - 10, 32, 32),     # head
        (cx + 22, ey - 2, 24, 24),      # neck
        (cx - 25, ey + 26, 50, 66),     # body
        (ix + 8, ey, 46, 76),           # rhand
        (ix + iw - 54, ey, 46, 76),     # lhand
        (ix + 12, by - 4, 32, 30),      # gloves
        (cx - 49, by, 22, 22),          # ring1
        (cx - 25, by + 1, 50, 20),      # belt
        (cx + 27, by, 22, 22),          # ring2
        (ix + iw - 44, by - 4, 32, 30), # feet
    ]


rgba = render(inv_bg)
meta["win_inventory"] = crop_save(rgba, "win_inventory.png")
L = meta["inventory_layout"]
ix, iw, cx = L["ix"], L["iw"], INV.WX + INV.WW // 2
ey = L["iy"] + 24
names = ["head", "neck", "body", "rhand", "lhand", "gloves", "ring1", "belt", "ring2", "feet"]
L["slots"] = {n: list(r) for n, r in zip(names, INV_SLOTS(ix, iw, cx, ey, ey + 88))}


# ---------------- окно «Витязь» ---------------------------------------------------
def char_bg(cv):
    WX, WY, WW, WH = CH.WX, CH.WY, CH.WW, CH.WH
    ix, iy, iw, ih = U.window(cv, WX, WY, WW, WH, title="ВИТЯЗЬ")
    top = iy + 13
    S = {"hero_doll": SR.hero_doll()}
    CH.portrait(cv, S, ix + 6, top, 54, 68)
    hx = ix + 70
    T.text_ru(cv, hx, top - 1 - FONT_USTAV["top"] + 1, "РАТИБОР", C["bronze_hi"], font=FONT_USTAV)
    T.text_ru(cv, hx, top + 15, "Дружинник-ведун · Ладога", C["birch"], outline=False)
    lx, ly = ix + iw - 30, top + 15
    cv.disc(lx, ly, 13, C["ink"]); cv.disc(lx, ly, 12, C["bronze"]); cv.disc(lx - 0.5, ly - 0.5, 10, C["wood_dk"])
    T.rosette(cv, lx - 0.5, ly - 0.5, 10, C["bronze_dk"])
    cv.disc(lx - 0.5, ly - 0.5, 6.5, C["wood_dk"])
    T.text_ru(cv, lx + 1, ly + 15, "Уровень", C["bronze_lt"], align="c", outline=False)
    U.recess(cv, hx, top + 28, 150, 13)
    U.recess(cv, hx, top + 43, 150, 13)
    sy = top + 78
    colw = (iw - 18) // 2
    lx0, rx0 = ix + 6, ix + 12 + colw
    U.section_title(cv, lx0, sy, colw, "Свойства")
    U.section_title(cv, rx0, sy, colw, "Показатели")
    ry = sy + 13
    for k in range(4):
        U.recess(cv, lx0, ry + k * 17, colw - 18, 13)
    py = ry + 4 * 17 + 2
    for k in range(8):
        U.recess(cv, rx0, ry + k * 15, colw, 13)
    rsy = py + 21
    U.section_title(cv, lx0, rsy, colw, "Сопротивления")
    for k, kind in enumerate(("fire", "cold", "poison")):
        y = rsy + 13 + k * 15
        U.recess(cv, lx0, y, colw, 13)
        CH.res_icon(cv, lx0 + 3, y + 3, kind)
    hy = max(rsy + 13 + 3 * 15, ry + 8 * 15) + 6
    meta["character_layout"] = {"ix": ix, "iy": iy, "iw": iw, "top": top, "hx": hx, "lvl": [lx, ly], "colw": colw,
                                "lx0": lx0, "rx0": rx0, "ry": ry, "py": py, "rsy": rsy, "hy": hy,
                                "close": [WX + WW - 22, WY + 9, 13], "win": [WX, WY, WW, WH]}


rgba = render(char_bg)
meta["win_character"] = crop_save(rgba, "win_character.png")


# ---------------- кнопки HUD -------------------------------------------------------
def buttons(cv):
    G.draw_buttons(cv, 505, 114)


rgba = render(buttons)
meta["hud_buttons"] = crop_save(rgba, "hud_buttons.png")
meta["hud_buttons"]["keys"] = [k for (_, k, _) in G.MENU_BUTTONS]
meta["hud_buttons"]["labels"] = [l for (_, _, l) in G.MENU_BUTTONS]


# ---------------- окно «Навыки» (T) ----------------------------------------------
# Две ветки столбцами (GDD §10: «2 вкладки» — в прототипе обе видны сразу), тиры I/II/III, у навыка: слот с иконкой,
# имя, «Ранг N/10», кнопка «+». Раскладку читает src/ui/skills_window.js из ui_atlas.js (skills_layout).
SK_TREE = {"ratnoe": [["sshibka"], ["chur", "stat"], ["secha"]], "vedovstvo": [["zmey"], ["morozko", "veshchee"], ["skok"]]}
def skills_bg(cv):
    WX, WY, WW, WH = INV.WX, INV.WY, INV.WW, INV.WH
    ix, iy, iw, ih = U.window(cv, WX, WY, WW, WH, title="НАВЫКИ")
    colw = (iw - 18) // 2
    cols = {"ratnoe": ix + 6, "vedovstvo": ix + 12 + colw}
    lay = {"ix": ix, "iy": iy, "iw": iw, "ih": ih, "colw": colw, "close": [WX + WW - 22, WY + 9, 13], "win": [WX, WY, WW, WH],
           "cols": {}, "slots": {}, "plus": {}, "tiers": []}
    top = iy + 12
    for b, x0 in cols.items():
        U.section_title(cv, x0, top, colw, {"ratnoe": "Ратное дело", "vedovstvo": "Ведовство"}[b])
        lay["cols"][b] = [x0, top]
        y = top + 14
        for t, row in enumerate(SK_TREE[b]):
            if b == "ratnoe":
                lay["tiers"].append(y)
            y += 11
            for sid in row:
                T.wood_slot(cv, x0, y, 28, 28)
                U.recess(cv, x0 + 31, y + 1, colw - 31, 26)
                lay["slots"][sid] = [x0, y, 28, 28]
                lay["plus"][sid] = [x0 + colw - 14, y + 8, 11, 11]
                y += 31
            y += 2
    fy = iy + ih - 34
    U.recess(cv, ix + 6, fy, iw - 12, 13)
    lay["points"] = [ix + 6, fy, iw - 12, 13]
    lay["hint"] = [ix + 6, fy + 16]
    meta["skills_layout"] = lay


rgba = render(skills_bg)
meta["win_skills"] = crop_save(rgba, "win_skills.png")


# ---------------- трекер задания (макет HUD v2: gameplay_hud_v2.draw_quest) -------------
# Рамка ui_rus.carved_frame и буквица ui_rus.bukvitsa рисуются как у художника; текст (заголовок уставом, цели)
# игра пишет сама из data/ru.json. Ширина считается по формуле draw_quest для самой длинной цели М1 (act1.md v1.1).
QUEST_TITLE = "ОГОНЬ НА КАПИЩЕ"
QUEST_GOALS = ("— Доберись до капища", "— Спаси выживших", "— Отбей огнища у упырей", "— Одолей Крившу", "— Найди поджигателя")
def quest_frame(cv):
    first, rest = QUEST_TITLE[0], QUEST_TITLE[1:]
    tw = pk.text_width(rest, FONT_USTAV)
    gw = max(pk.text_width(g, FONT_RU) + pk.text_width("0/3", FONT_RU) + 8 + 10 for g in QUEST_GOALS)
    w, h = max(186, 26 + 4 + tw + 6 + 14 + 4, gw + 16), 80
    ix, iy, iw, ih = U.carved_frame(cv, 3, 3, w, h, fill="dim")
    bw, bh = U.bukvitsa(cv, ix + 1, iy + 1, first)
    meta["quest_layout"] = {"frame": [3, 3, w, h], "inner": [ix, iy, iw, ih], "buk": [bw, bh], "title": QUEST_TITLE}


rgba = render(quest_frame)
meta["hud_quest"] = crop_save(rgba, "hud_quest.png")


# ---------------- атлас иконок -----------------------------------------------------
S = IR.build()
icons = {}
for k, spr in S.items():
    idx = pk.sprite_to_index(spr)
    rgba = np.zeros((spr["h"], spr["w"], 4), np.uint8)
    m = idx >= 0
    rgba[m, :3] = pk.RGB[idx[m]]
    rgba[m, 3] = 255
    icons[k] = rgba
for kind in ("life", "mana", "zhivaya"):
    def f(cv, _k=kind):
        T.potion(cv, 2, 2, _k)
    r = render(f)
    ys, xs = np.nonzero(r[:, :, 3])
    icons["potion_" + kind] = r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
for key, fn in T.ICONS.items():
    for sz in (16, 20, 26):
        def f(cv, _fn=fn, _s=sz):
            _fn(cv, 2, 2, _s)
        r = render(f)
        icons["sk_%s_%d" % (key, sz)] = r[2:2 + sz, 2:2 + sz]
doll = SR.hero_doll()
idx = pk.sprite_to_index(doll)
rgba = np.zeros((doll["h"], doll["w"], 4), np.uint8)
m = idx >= 0
rgba[m, :3] = pk.RGB[idx[m]]; rgba[m, 3] = 255
icons["hero_doll"] = rgba

# упаковка в полосы
pad = 1
order = sorted(icons, key=lambda k: -icons[k].shape[0])
AW = 512
x = y = rowh = 0
rects = {}
for k in order:
    h, w = icons[k].shape[:2]
    if x + w > AW:
        x = 0; y += rowh + pad; rowh = 0
    rects[k] = [x, y, w, h]
    x += w + pad; rowh = max(rowh, h)
AH = y + rowh
atlas = np.zeros((AH, AW, 4), np.uint8)
for k, (x, y, w, h) in rects.items():
    atlas[y:y + h, x:x + w] = icons[k]
Image.fromarray(atlas, "RGBA").save(os.path.join(OUT, "items.png"))
meta["icons"] = rects

with open(os.path.join(DATA, "ui_atlas.js"), "w", encoding="utf-8") as fh:
    fh.write("// Generated by tools/export_ui.py from art/ui/src (inventory_v2, character_v2, items_rus). Do not edit.\n")
    fh.write("export const UI_ATLAS = " + json.dumps(meta, ensure_ascii=False, default=int) + ";\n")
print("ok:", {k: v for k, v in meta.items() if k.startswith("win") or k == "hud_buttons"}, "icons", len(rects), "atlas", AW, AH)
print("skills_layout:", meta["skills_layout"]["slots"], meta["skills_layout"]["points"])

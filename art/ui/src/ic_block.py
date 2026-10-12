"""H22 (GDD v1.14 §12.1.8): иконка щита ic_block 16×16 для HUD-слота 18×18 (509;342).
Два кадра в полосе 32×16: 0 normal (щит героя анфас: 8 секторов красный/береста, бронзовая кромка, умбон),
1 broken (трещина через поле, погнутая кромка справа сверху). Рисунок щита = sprites_rus._shield (не меняется).
Фон — как у иконок навыков v2 (pixelkit._icon_bg, slate). Запуск: python3 ic_block.py"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image
import gameplay_hud_v2 as G          # палитра v2
import pixelkit as pk
from pixelkit import C, Canvas

OUT = os.path.join(HERE, "..", "hud")
S = 16


def shield_icon(cv, x0, y0, broken=False):
    pk._icon_bg(cv, x0, y0, S, C["slate_dk"], C["slate"])
    cx = cy = 7.5
    R = 7.0
    for y in range(S):
        for x in range(S):
            dx, dy = x - cx, y - cy
            if broken and x >= 10 and y <= 5:          # погнутая кромка: край вмят внутрь на 1 px
                dx, dy = dx * 1.18, dy * 1.18
            d = math.hypot(dx, dy) / R
            if d > 1.08:
                continue
            a = math.atan2(dy, dx)
            lit = (-dx - dy) / (R * 1.41)               # свет сверху-слева
            if d > 0.99:
                c = "ink"
            elif d > 0.84:
                c = "bronze_hi" if lit > 0.5 else ("bronze_lt" if lit > -0.2 else ("bronze" if lit > -0.65 else "bronze_dk"))
            elif d <= 0.17:
                c = "bronze_hi" if (dx < 0 and dy < 0) else "bronze_lt"
            elif d <= 0.32:
                c = "bronze_dk"
            else:
                sect = int((a + math.pi) / (math.pi / 4)) % 2 == 0
                if sect:
                    c = "red_lt" if lit > 0.55 else ("red" if lit > -0.45 else "red_dk")
                else:
                    c = "linen" if lit > 0.45 else "birch"
            cv.a[y0 + y, x0 + x] = C[c]
    if broken:
        # вмятина кромки сверху-справа: контур уходит внутрь, бронза смята (тёмная складка)
        for (x, y, c) in ((10, 1, "ink"), (11, 2, "ink"), (12, 2, "ink"), (13, 3, "ink"), (13, 4, "ink"),
                          (10, 2, "bronze_dk"), (11, 3, "bronze_dk"), (12, 3, "bronze"), (12, 4, "bronze_dk"),
                          (11, 1, None), (12, 1, None), (13, 2, None), (14, 3, None), (14, 4, None)):
            cv.a[y0 + y, x0 + x] = C[c] if c else cv.a[y0 + 0, x0 + 0]
        # трещина через всё поле (от вмятины к нижнему левому краю), 1 px, с изломом и сколом-бликом
        crack = [(11, 4), (10, 5), (10, 6), (9, 7), (8, 7), (7, 8), (7, 9), (6, 10), (5, 11), (5, 12), (4, 13)]
        for (x, y) in crack:
            cv.a[y0 + y, x0 + x] = C["ink"]
        for (x, y) in ((11, 6), (10, 7), (9, 8), (8, 9), (7, 10), (6, 11)):     # раскол 2 px в середине
            cv.a[y0 + y, x0 + x] = C["ink"]
        for (x, y) in ((12, 5), (11, 7), (9, 9), (7, 11)):                     # светлые сколы вдоль раскола
            cv.a[y0 + y, x0 + x] = C["linen"]
        for (x, y) in ((9, 5), (8, 6), (6, 8), (5, 9)):                        # тень смещённой половины
            cv.a[y0 + y, x0 + x] = C["red_dk"] if cv.a[y0 + y, x0 + x] in (C["red"], C["red_lt"]) else C["wood_lt"]


def build():
    cv = Canvas(S * 2, S, fill=C["ink"])
    shield_icon(cv, 0, 0, False)
    shield_icon(cv, S, 0, True)
    rgb = pk.RGB[cv.a]
    rgba = np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)])
    return rgba


def main():
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    rgba = build()
    pal = json.load(open(os.path.join(HERE, "..", "palette_v2.json")))
    hexes = {c["hex"].lower().lstrip("#") if isinstance(c, dict) else None for c in pal["colors"]}
    used = {"%02x%02x%02x" % tuple(p) for p in rgba[:, :, :3].reshape(-1, 3)}
    assert used <= hexes, used - hexes
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, "ic_block.png"))
    meta = {"name": "ic_block", "frame_size": [16, 16], "frame_count": 2,
            "frames": {"normal": 0, "broken": 1},
            "states_prototype": {"ready": "normal", "raised": "normal (+ обводка bronze_hi кодом, как сейчас)",
                                 "broken": "broken (+ cooldownSector кодом, как сейчас)",
                                 "none": "normal с затемнением (rect slate_dk alpha 0.6, как у навыков без Яри) — отдельного кадра нет"},
            "slot": {"x": 509, "y": 342, "s": 18, "icon_at": [510, 343]},
            "palette": "palette_v2", "alpha": "0/255 (иконка непрозрачна целиком)",
            "source": "art/ui/src/ic_block.py; рисунок щита = sprites_rus._shield",
            "gdd": "v1.14 §12.1.8 H22"}
    json.dump(meta, open(os.path.join(OUT, "ic_block.json"), "w"), ensure_ascii=False, indent=1)
    # превью ×3 и ×8 в рамке слота 18×18
    pv = Image.new("RGBA", (2 * 22 + 2, 22), (22, 24, 28, 255))
    for i in range(2):
        slot = Image.new("RGBA", (18, 18), tuple(pk.RGB[C["ink"]]) + (255,))
        slot.paste(Image.fromarray(rgba[:, i * 16:(i + 1) * 16], "RGBA"), (1, 1))
        pv.paste(slot, (2 + i * 22, 2))
    pv.resize((pv.width * 3, pv.height * 3), Image.NEAREST).save(os.path.join(OUT, "preview", "ic_block_x3.png"))
    pv.resize((pv.width * 8, pv.height * 8), Image.NEAREST).save(os.path.join(OUT, "preview", "ic_block_x8.png"))
    print("ok", sorted(used))


if __name__ == "__main__":
    main()

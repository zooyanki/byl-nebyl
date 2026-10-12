"""H23 (GDD v1.14 §12.1.8): искры блока fx_block_sparks — 16×16, 3 кадра, bronze_hi → bronze → прозрачно.
Одно направление: веер искр летит ВПРАВО от точки удара о кромку (pivot (4,8)). Для удара слева — зеркалить
по x (pivot станет (11,8)); для произвольного угла — поворот кодом не нужен: берите зеркало по стороне атакующего.
Запуск: python3 fx_block_sparks.py"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import numpy as np
import rig  # noqa: F401  (палитра v2)
from pixelkit import C
from export import save_sheet, preview, mirror, ROOT

W = H = 16
PIV = (4, 8)
# лучи: угол (град, 0 = вправо, + вниз), длина кадра 0, длина кадра 1
RAYS = [(-62, 4, 7), (-28, 5, 9), (0, 5, 9), (24, 4, 8), (55, 3, 6), (-95, 2, 4), (88, 2, 4)]


def frame(i):
    a = np.full((H, W), -1, np.int16)
    px, py = PIV

    def put(x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            a[y, x] = C[c]
    if i == 0:                       # вспышка: ядро bronze_hi + короткие лучи
        for dx, dy in ((0, 0), (1, 0), (0, -1), (0, 1), (-1, 0), (1, -1), (1, 1)):
            put(px + dx, py + dy, "bronze_hi")
        for ang, l0, _ in RAYS:
            t = math.radians(ang)
            for s in range(2, l0 + 1):
                put(px + s * math.cos(t), py + s * math.sin(t), "bronze_hi" if s < l0 else "bronze_lt")
    elif i == 1:                     # разлёт: оторвавшиеся штрихи bronze (2 px) с bronze_lt головой
        for k, (ang, l0, l1) in enumerate(RAYS):
            t = math.radians(ang + (4 if k % 2 else -3))
            for s in (l1 - 2, l1 - 1):
                put(px + s * math.cos(t), py + s * math.sin(t) + (0.3 if s == l1 - 1 else 0), "bronze")
            put(px + l1 * math.cos(t), py + l1 * math.sin(t) + 0.5, "bronze_lt")
    else:                            # гаснет: редкие точки bronze_dk на концах, почти прозрачно
        for k, (ang, l0, l1) in enumerate(RAYS[:5]):
            if k % 2 == 0:
                t = math.radians(ang)
                put(px + (l1 + 0.3) * math.cos(t), py + (l1 + 0.3) * math.sin(t) + 0.6, "bronze_dk")
    return a


def main():
    fr = [frame(i) for i in range(3)]
    for f in fr:   # не касаемся краёв, кроме допустимого
        assert (f[:, 0] < 0).all() and (f[:, -1] < 0).all() and (f[0] < 0).all() and (f[-1] < 0).all()
    out = os.path.join(ROOT, "fx_block_sparks")
    save_sheet(fr, out, "fx_block_sparks", dict(
        effect="Искры блока (H23, GDD v1.14 §12.1.8)",
        draw="поверх героя, pivot = точка удара на кромке щита (anchors.shield_rim из hero_block_*.json); веер летит вправо",
        pivot=list(PIV), fps=20, loop=False,
        mirror="атакующий слева от щита (экранно) → зеркалить по x, pivot (11,8)",
        colors="кадр 0 bronze_hi/bronze_lt, кадр 1 bronze/bronze_lt, кадр 2 bronze_dk (затухание)",
        events={"spawn": "на событии hit (кадр 0 hero_block_hit) — 1 шт.; на break — 2 шт. (второй зеркальный)"}))
    preview([fr, [mirror(f) for f in fr]], ["вправо", "зеркало"], os.path.join(out, "preview"), "fx_block_sparks",
            fps=20, loop=False, pivot=PIV, title="Искры блока x3")
    print("ok")


if __name__ == "__main__":
    main()

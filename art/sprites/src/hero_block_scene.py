"""Ревью-сцена H21+H23 (GDD v1.14 §12.1.8): Ратибор (вид se) принимает тяжёлый удар упыря (attack ne, зеркало → nw).
Кадры: hold → замах упыря (0-2) → удар (3) = hero_block_hit 0 + искры 0 у anchors.shield_rim → hit 1-2 + искры 1-2 → hold.
Плюс отдельная полоса «пробит» (break 0-3 + 2 пачки искр). Пишет hero/review/: native PNG, ×3 PNG, GIF ×3.
Запуск: python3 hero_block_scene.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image
import rig  # noqa
import pixelkit as pk
from pixelkit import C
from export import ROOT

OUT = os.path.join(ROOT, "hero", "review")
W, H = 168, 100


def strip(path):
    im = np.array(Image.open(path).convert("RGBA"))
    n = im.shape[1] // 64
    return [im[:, i * 64:(i + 1) * 64] for i in range(n)]


def J(path):
    return json.load(open(path))


HB = os.path.join(ROOT, "hero")
hero = {a: strip(f"{HB}/hero_block_{a}_se.png") for a in ("hold", "hit", "break")}
anc = {a: J(f"{HB}/hero_block_{a}_se.json")["anchors"]["shield_rim"] for a in ("hit", "break")}
up = [f[:, ::-1] for f in strip(os.path.join(ROOT, "upyr", "upyr_attack_ne.png"))]   # ne → nw
up_idle = [f[:, ::-1] for f in strip(os.path.join(ROOT, "upyr", "upyr_idle_ne.png"))]
sp = strip(os.path.join(ROOT, "fx_block_sparks", "fx_block_sparks.png")) if False else None
spim = np.array(Image.open(os.path.join(ROOT, "fx_block_sparks", "fx_block_sparks.png")).convert("RGBA"))
spark = [spim[:, i * 16:(i + 1) * 16] for i in range(3)]

HERO_PIV = (62, 60)            # экранная точка ног героя
UP_PIV = (62 + 26, 60 + 13)    # упырь ~1.3 тайла на юго-восток, лицом к герою (nw)


def ground():
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = pk.RGB[C["pine_dk"]]; g[..., 3] = 255
    yy, xx = np.mgrid[0:H, 0:W]
    # изометрическая сетка тайлов 32×16 (тонко, moss), для масштаба
    u = ((xx - HERO_PIV[0]) / 32.0 + (yy - HERO_PIV[1]) / 16.0)
    v = ((yy - HERO_PIV[1]) / 16.0 - (xx - HERO_PIV[0]) / 32.0)
    line = (np.abs(u - np.round(u)) < 0.035) | (np.abs(v - np.round(v)) < 0.035)
    g[line, :3] = pk.RGB[C["pine"]]
    return g


def shadow(img, piv, w):
    yy, xx = np.mgrid[0:H, 0:W]
    e = ((xx - piv[0] + 0.5) / (w / 2)) ** 2 + ((yy - piv[1]) / 3.0) ** 2 <= 1
    img[e, :3] = pk.RGB[C["night"]]


def blit(img, spr, x, y):
    h, w = spr.shape[:2]
    for j in range(h):
        yy = y + j
        if not 0 <= yy < H:
            continue
        for i in range(w):
            xx = x + i
            if 0 <= xx < W and spr[j, i, 3] == 255:
                img[yy, xx] = spr[j, i]


def compose(hfr, ufr, sparks=()):
    img = ground()
    shadow(img, HERO_PIV, 16); shadow(img, UP_PIV, 18)
    blit(img, hfr, HERO_PIV[0] - 32, HERO_PIV[1] - 56)          # герой дальше от камеры — рисуется первым
    blit(img, ufr, UP_PIV[0] - 32, UP_PIV[1] - 56)
    for (s, ax, ay, flip) in sparks:                              # FX поверх всего
        fr = s[:, ::-1] if flip else s
        px = 11 if flip else 4
        blit(img, fr, int(round(HERO_PIV[0] - 32 + ax - 1)) - px, int(round(HERO_PIV[1] - 56 + ay - 1)) - 8)
    return img


def seq_block():
    hr = lambda a, i: (anc[a][i][0], anc[a][i][1])
    f = []
    f.append((compose(hero["hold"][0], up_idle[0]), 400))
    for i in range(3):
        f.append((compose(hero["hold"][i % 2], up[i]), 200))
    ax, ay = hr("hit", 0)
    f.append((compose(hero["hit"][0], up[3], [(spark[0], ax, ay, False)]), 120))
    ax, ay = hr("hit", 1)
    f.append((compose(hero["hit"][1], up[4], [(spark[1], ax, ay, False)]), 90))
    ax, ay = hr("hit", 2)
    f.append((compose(hero["hit"][2], up[4], [(spark[2], ax, ay, False)]), 90))
    f.append((compose(hero["hold"][0], up[5]), 500))
    return f


def seq_break():
    f = [(compose(hero["hold"][0], up[2]), 300)]
    for i in range(4):
        ax, ay = anc["break"][i]
        sk = [(spark[i], ax, ay, False), (spark[i], ax, ay - 3, True)] if i < 3 else []
        f.append((compose(hero["break"][i], up[3 if i == 0 else (4 if i < 3 else 5)], sk), 125 if i < 3 else 600))
    return f


def save(frames, name):
    os.makedirs(OUT, exist_ok=True)
    ims = [Image.fromarray(a, "RGBA").convert("RGB") for a, _ in frames]
    big = [im.resize((W * 3, H * 3), Image.NEAREST) for im in ims]
    big[0].save(os.path.join(OUT, name + ".gif"), save_all=True, append_images=big[1:],
                duration=[d for _, d in frames], loop=0)
    # контакт-лист: все кадры в ряд, native и ×3
    sheet = Image.new("RGB", (len(ims) * (W + 2), H), tuple(pk.RGB[C["ink"]]))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * (W + 2), 0))
    sheet.save(os.path.join(OUT, name + "_native.png"))
    sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(os.path.join(OUT, name + "_x3.png"))


def seq_back(view, upos):
    """Вид сзади (ne/n): упырь впереди героя (дальше от камеры, рисуется первым), лицом к герою (se → зеркало sw);
    искры от выведенной кромки щита — веер влево (зеркало)."""
    hv = {a: strip(f"{HB}/hero_block_{a}_{view}.png") for a in ("hold", "hit")}
    ah = J(f"{HB}/hero_block_hit_{view}.json")["anchors"]["shield_rim"]
    us = [f[:, ::-1] for f in strip(os.path.join(ROOT, "upyr", "upyr_attack_se.png"))]
    up_p = (HERO_PIV[0] + upos[0], HERO_PIV[1] + upos[1])

    def comp(hfr, ufr, sk=()):
        img = ground(); shadow(img, up_p, 18); shadow(img, HERO_PIV, 16)
        blit(img, ufr, up_p[0] - 32, up_p[1] - 56)
        blit(img, hfr, HERO_PIV[0] - 32, HERO_PIV[1] - 56)
        for (sfr, ax, ay) in sk:
            blit(img, sfr[:, ::-1], int(round(HERO_PIV[0] - 32 + ax - 1)) - 11, int(round(HERO_PIV[1] - 56 + ay - 1)) - 8)
        return img
    f = [(comp(hv["hold"][0], us[0]), 400)]
    for i in (1, 2):
        f.append((comp(hv["hold"][i % 2], us[i]), 200))
    for i in range(3):
        f.append((comp(hv["hit"][i], us[3 if i == 0 else 4], [(spark[i], *ah[i])]), 120 if i == 0 else 90))
    f.append((comp(hv["hold"][0], us[5]), 500))
    return f


if __name__ == "__main__":
    save(seq_back("ne", (14, -18)), "review_hero_block_back_ne_vs_upyr")
    save(seq_back("n", (-4, -20)), "review_hero_block_back_n_vs_upyr")
    save(seq_block(), "review_hero_block_vs_upyr")
    save(seq_break(), "review_hero_guard_break_vs_upyr")
    # ключевой кадр (момент блока) отдельно ×3
    k = seq_block()[4][0]
    Image.fromarray(k, "RGBA").resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(OUT, "review_block_key_x3.png"))
    print("ok", OUT)

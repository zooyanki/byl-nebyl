"""Схема раскладки сверху (тайлы, ×3) по настоящей карте генератора прототипа (с патчем декора):
  node dump_map.mjs /tmp/_ov_decor.json (через check_layout.py) -> ../zalesye_mara_decor_plan_x3.png"""
import json, math, os, subprocess, sys
import numpy as np
sys.path.insert(0, '/workspace/game/art/sprites/src')
import rig  # noqa: F401  palette v2
import pixelkit as pk
from pixelkit import C
from fonts_ru import FONT_RU

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, '..', 'zalesye_mara_decor.json')))
json.dump({"clearR": L["clearR"], "ash": L["ash"]}, open('/tmp/_ov_decor.json', 'w'))
d = json.loads(subprocess.check_output(['node', os.path.join(HERE, 'dump_map.mjs'), '/tmp/_ov_decor.json']))
W = d['W']
X0, X1, Y0, Y1 = 34, 66, 5, 28
T = 10                                       # px на тайл (схема), потом ×3
M_L, M_T = 4, 16
cv = pk.Canvas(M_L + (X1 - X0) * T + 4, M_T + (Y1 - Y0) * T + 30, fill=C["night"])
GC = {0: C["moss"], 1: C["wood"], 2: C["sea_dk"], 3: C["pine_dk"], 4: C["slate"]}
for y in range(Y0, Y1):
    for x in range(X0, X1):
        g = d['ground'][y * W + x]
        cv.rect(M_L + (x - X0) * T, M_T + (y - Y0) * T, T, T, GC[g])
        if g == 4 and (x + y) % 2 == 0:
            cv.rect(M_L + (x - X0) * T, M_T + (y - Y0) * T, T, T, C["slate_dk"])
def P(x, y): return int(round(M_L + (x - X0) * T)), int(round(M_T + (y - Y0) * T))
# сетка
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1):
        if x % 2 == 0: cv.px(P(x, y)[0], P(x, y)[1], C["night"])
# пропы: деревья — тёмные точки, камень/сарай — футпринт
for p in d['props']:
    fx, fy, fw, fh = p['fp']
    if not (X0 - 2 <= fx < X1 and Y0 - 2 <= fy < Y1): continue
    if p['type'] == 'tree':
        a, b = P(p['x'] + 0.5, p['y'] + 0.5); cv.rect(a - 2, b - 2, 4, 4, C["pine"]); cv.px(a, b, C["ink"])
    elif p['type'] in ('rock', 'izba'):
        a, b = P(fx, fy); cv.rect(a, b, int(fw * T), int(fh * T), C["slate_lt"] if p['type'] == 'rock' else C["wood_md"])
# круги: обход Огнеи r 6, поляна r 8.9
cx, cy = 56.5, 16.5
for R, col, step in ((6.0, C["bronze"], 3), (L['clearR'], C["mist"], 2)):
    for k in range(0, 720, step):
        a = math.radians(k / 2)
        x, y = P(cx + math.cos(a) * R, cy + math.sin(a) * R)
        cv.px(int(x), int(y), col)
# горловина (рамка x 36–49, y 17–19 по тайлам: 36..50 × 17..20)
a0, b0 = P(36, 17); a1, b1 = P(50, 20)
for x in range(a0, a1 + 1, 2): cv.px(x, b0, C["bronze_lt"]); cv.px(x, b1, C["bronze_lt"])
for y in range(b0, b1 + 1, 2): cv.px(a0, y, C["bronze_lt"]); cv.px(a1, y, C["bronze_lt"])
# декор
for i, (x, y) in enumerate(L['ash']):
    a, b = P(x + 0.5, y + 0.5)
    cv.rect(int(a) - 2, int(b) - 1, 5, 3, C["mist"]); cv.rect(int(a) - 1, int(b) - 2, 3, 5, C["mist"]); cv.px(int(a), int(b), C["slate_dk"])
for x, y, v in L['stumps']:
    a, b = P(x + 0.5, y + 0.5)
    cv.rect(int(a) - 2, int(b) - 2, 5, 5, C["ink"]); cv.rect(int(a) - 1, int(b) - 1, 3, 3, (C["wood_md"], C["wood_lt"], C["wood"])[v])
# Огнея (точка спавна — первая точка круга) и точка предупреждения
for (x, y, col) in ((62.5, 16.5, C["nebyl"]), (39.5, 18.0, C["bronze_hi"])):
    a, b = P(x, y); cv.rect(int(a) - 1, int(b) - 3, 3, 7, col); cv.rect(int(a) - 3, int(b) - 1, 7, 3, col)
cv.text(M_L, 3, 'Тупик Огнеи: пни ' + str(len(L['stumps'])) + ', пепел ' + str(len(L['ash'])) + ' (горловина 10 + край ' + str(len(L['ash']) - 10) + ')', C["linen"], font=FONT_RU)
ly = M_T + (Y1 - Y0) * T + 4
items = [(C["mist"], 'пепел'), (C["wood_md"], 'пень'), (C["nebyl"], 'Огнея'), (C["bronze_hi"], 'реплика'), (C["bronze"], 'обход r6'), (C["mist"], 'поляна r' + ('%g' % L['clearR']).replace('.', ','))]
x = M_L
for col, s in items:
    cv.rect(x, ly + 2, 5, 5, col); cv.text(x + 7, ly, s, C["mist"], font=FONT_RU); x += 9 + pk.text_width(s, FONT_RU) + 6
cv.text(M_L, ly + 12, 'x ' + str(X0) + '–' + str(X1) + ', y ' + str(Y0) + '–' + str(Y1) + ' · клетка = 1 тайл · рамка — горловина', C["slate_lt"], font=FONT_RU)
out = os.path.join(HERE, '..', 'zalesye_mara_decor_plan_x3.png')
cv.save(out, scale=3)
print(out)

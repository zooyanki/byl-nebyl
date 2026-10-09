"""Раскладка декора тупика Огнеи (Залесье, GDD v1.11 §… «Тупик Огнеи», заказ художнику п.(1)-(2)).
Пишет ../zalesye_mara_decor.json в формате landmarks.maraDen прототипа (data/zones/zalesye.json).
Координаты — как в прототипе: точка (x, y) пропа 'ash' рисуется в центре (x+0.5, y+0.5) (props.js ashPile), так же
будет и 'stump'. Раскладка детерминирована (seed), проверки — check_layout.py."""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'zalesye_mara_decor.json')
C = (56.5, 16.5)            # центр круга обхода Огнеи = центр поляны (bosses.json mara.route.center, maraDen.center)
CLEAR_R = 8.9               # поляна (GDD v1.11, решение дизайнера 09.10: 8,9 — без зубцов в 1 тайл)
SAFE_R = CLEAR_R - 0.25         # декор ставится так, чтобы работал и при 8.9 (без однотайловых зубцов на (56,7), (56,25), (65,16))
GAP = (143.0, 196.0)
VARIANTS = [0, 2, 1, 0, 2, 0, 1, 2, 0, 1, 2, 0, 2]   # 0 срез, 1 обломанный ствол (высокий, ~1/4), 2 широкий        # градусы (x вправо, y вниз): здесь горловина входит в поляну — проход читается, декора нет

# --- горловина: 8 пятен пепла, x 36–49, y 17–19, шаг сокращается к Огнее (3.6 → 1.0 тайла)
THROAT = [(36, 18.5), (37.5, 17.5), (38, 17), (38, 19), (41.5, 18.5), (43.5, 17.5), (45, 18.5), (46, 17.5), (47, 19), (48, 18)]
# вариант B — дословно по заказу в GDD («у (39,5; 18) — самое густое»): 5 нынешних + 3


def snap(v):
    """визуальный центр на сетке ½ тайла => точка данных (центр − 0.5) тоже кратна ½: футпринт 0×0 не помечает сабтайл.
    (map.js markRect: при нецелом x·2 или y·2 даже пустой футпринт блокирует ½ тайла — так сейчас у (38,2; 18,8) и (36,8; 18,2).)"""
    return round(v * 2) / 2 + (0.0 if True else 0)


def in_den(x, y, R=CLEAR_R):
    tx, ty = math.floor(x), math.floor(y)
    if x == tx:                                    # точка на границе тайлов — проверяем оба соседних
        tx2 = tx - 1
    else:
        tx2 = tx
    if y == ty:
        ty2 = ty - 1
    else:
        ty2 = ty
    return all(math.hypot(a + 0.5 - C[0], b + 0.5 - C[1]) <= R - 0.25 for a in {tx, tx2} for b in {ty, ty2})


def ring(seed=11):
    """Кромка поляны: группы «пень + пепел» на r 7.1–8.6 (визуальные центры), неровно, с пустыми промежутками."""
    rng = np.random.default_rng(seed)
    # центры групп (угол, радиус) — руками, чтобы были и разрывы, и сгущения; потом шум
    groups = [(205, 8.1, 'S'), (222, 7.5, 'SA'), (246, 8.4, 'S'), (262, 7.3, 'AS'),          # север/северо-запад
              (290, 8.2, 'SSA'), (318, 7.6, 'A'), (338, 8.3, 'SA'),                           # северо-восток
              (6, 7.4, 'S'), (24, 8.4, 'AS'), (47, 7.8, 'S'),                                 # восток / юго-восток
              (66, 8.2, 'SA'), (88, 7.3, 'S'), (104, 8.5, 'AA'), (121, 7.6, 'S')]              # юг / юго-запад
    stumps, ash, used = [], [], []
    for ang, r, kinds in groups:
        for k, kind in enumerate(kinds):
            for _ in range(50):
                a = math.radians(ang + rng.uniform(-6, 6) + k * rng.choice((-9, 9)))
                rr = r + rng.uniform(-0.35, 0.35) + (0.6 if kind == 'A' and k else 0) * rng.choice((-1, 1))
                rr = min(8.6, max(7.1, rr))
                x, y = C[0] + math.cos(a) * rr, C[1] + math.sin(a) * rr
                deg = math.degrees(math.atan2(y - C[1], x - C[0])) % 360
                x, y = snap(x), snap(y)
                deg = math.degrees(math.atan2(y - C[1], x - C[0])) % 360
                if GAP[0] <= deg <= GAP[1] or not in_den(x, y, SAFE_R + 0.25):
                    continue
                if all(math.hypot(x - u, y - v) >= (1.25 if kind == 'S' else 1.0) for u, v in used):
                    break
            used.append((x, y))
            if kind == 'S':
                stumps.append((x - 0.5, y - 0.5, VARIANTS[len(stumps) % len(VARIANTS)]))
            else:
                ash.append((x - 0.5, y - 0.5))
    return stumps, ash


def main():
    stumps, edge_ash = ring()
    # снаги (вариант 1, высокий) — не больше трети и не у самого входа
    data = {
        "_about": "Декор тупика Огнеи (GDD v1.11, заказ художнику: горелые пни и пепел по краю поляны r 9, пепел в горловине 5 → 8). "
                  "Вставлять в data/zones/zalesye.json → landmarks.maraDen (поля ниже заменяют/дополняют существующие). "
                  "Точка (x, y) рисуется в центре (x+0.5, y+0.5), как нынешний 'ash'. Весь декор без коллизии (fp 0×0).",
        "clearR": CLEAR_R,
        "ash": [list(p) for p in THROAT] + [list(p) for p in edge_ash],
        "_ash": "ash[0..9] — горловина (x 36–49, y 17–19, чаще к Огнее; [1] и [3] — у свободного западного края камня 2×2 (39–41; 17,5–19,5), в радиусе реплики r 2 от (39,5; 18); шаг 2 → 3.5 (камень 2×2 на x 39–41) → 2 → 1.5 → 1); ash[10..] — пепел по краю поляны. "
                "Рисуется существующим пропом 'ash' (props.js ashPile), код не нужен.",
        "stumps": [list(p) for p in stumps],
        "_stumps": "[x, y, вариант]: горелый пень, спрайт assets/fx/prop_stump_burnt.png (24×22, опора (12,18), кадр = вариант: "
                   "0 срез, 1 обломанный ствол, 2 широкий с корнями). Нужен проп 'stump' без коллизии — см. INTEGRATION_zalesye_decor.md.",
    }
    with open(OUT, 'w') as f:
        txt = json.dumps(data, ensure_ascii=False, indent=1)
        import re
        txt = re.sub(r'\[\s+([-\d.,\s]+?)\s+\]', lambda mm: '[' + re.sub(r'\s+', ' ', mm.group(1)) + ']', txt)
        f.write(txt + '\n')
    print(len(THROAT), 'throat ash;', len(edge_ash), 'edge ash;', len(stumps), 'stumps')
    print('stump variants', [s[2] for s in stumps])


if __name__ == '__main__':
    main()

"""Применяет раскладку декора к КОПИИ прототипа (python3 apply_to_copy.py /path/to/prototype_copy) — для превью и
для получения точного патча (../zalesye_mara_decor.patch). Сам прототип этим скриптом не трогать: патч ставит разработчик."""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.abspath(os.path.join(HERE, '..', '..'))
P = sys.argv[1]
L = json.load(open(os.path.join(HERE, '..', 'zalesye_mara_decor.json')))


def edit(path, old, new):
    fp = os.path.join(P, path)
    s = open(fp).read()
    if new in s or (new.replace(old, '') and new.replace(old, '').strip() in s):
        print('  already in', path); return          # код уже поставлен разработчиком
    assert s.count(old) == 1, (path, old[:60])
    open(fp, 'w').write(s.replace(old, new))


# 1) data: landmarks.maraDen
fp = os.path.join(P, 'data/zones/zalesye.json')
z = json.load(open(fp))
den = z['landmarks']['maraDen']
DECOR = ("GDD v1.11 (заказ художнику): ash[0..9] — горловина x 36–49, y 17–19, чаще к Огнее, [1] и [3] — у свободного края камня, "
         "в r 2 реплики у (39,5; 18); ash[10..] и stumps — край поляны r 8,9. Весь декор без коллизии; координаты кратны ½ "
         "(иначе пустой fp помечает сабтайл, map.js markRect). Раскладка: art/layout/zalesye_mara_decor.json")
nd = {}
for k, v in den.items():
    v = {'ash': L['ash'], 'clearR': L['clearR'], 'stumps': L['stumps'], '_decor': DECOR}.get(k, v)
    nd[k] = v
    if k == 'ash' and 'stumps' not in den:
        nd['stumps'] = L['stumps']
        nd['_decor'] = DECOR
z['landmarks']['maraDen'] = nd
open(fp, 'w').write(json.dumps(z, ensure_ascii=False, indent=1))

# 2) map.js: пни как пропы без коллизии
edit('src/world/map.js',
     "  for (const [x, y] of den.ash || []) if (m.groundAt(Math.floor(x), Math.floor(y)) !== T_WATER) m.ground[Math.floor(y) * W + Math.floor(x)] = T_ASH;\n",
     "  for (const [x, y] of den.ash || []) if (m.groundAt(Math.floor(x), Math.floor(y)) !== T_WATER) m.ground[Math.floor(y) * W + Math.floor(x)] = T_ASH;\n"
     "  // GDD v1.11: горелые пни по краю поляны — декор без коллизии (спрайт prop_stump_burnt, кадр = вариант)\n"
     "  for (const [x, y, v] of den.stumps || []) m.addProp('stump', x, y, 1, { fp: [x + 0.5, y + 0.5, 0, 0], variant: v | 0 });\n")

# 3) rest_fx.js: лист спрайта
edit('src/render/rest_fx.js',
     "  item_beresta: '../items/item_beresta_ground',",
     "  stump: 'prop_stump_burnt',                                                                                                         // горелый пень (декор тупика Огнеи, GDD v1.11)\n"
     "  item_beresta: '../items/item_beresta_ground',")

# 4) props.js: отрисовка (статичный кадр, без запекания: лист может догрузиться позже)
edit('src/render/props.js',
     "import { drawRestSource } from './rest_fx.js';",
     "import { drawRestSource, drawFxFrame } from './rest_fx.js';")
edit('src/render/props.js',
     "  if (p.type === 'relic') return relic(ctx, p, toS, time);\n",
     "  if (p.type === 'relic') return relic(ctx, p, toS, time);\n"
     "  if (p.type === 'stump') { const [x, y] = toS(p.x + 0.5, p.y + 0.5); if (!drawFxFrame(ctx, 'stump', p.variant || 0, x, y, { flip: p.seed > 0.5 })) ashPile(ctx, p, toS); return; }   // горелый пень (GDD v1.11); без спрайта — кучка пепла\n")
edit('src/render/props.js',
     "anvil: 16 }[p.type] || 40;",
     "anvil: 16, stump: 18 }[p.type] || 40;")

# 5) asset
for ext in ('png', 'json'):
    shutil.copy(os.path.join(ART, 'sprites/prop_stump_burnt/prop_stump_burnt.' + ext), os.path.join(P, 'assets/fx/prop_stump_burnt.' + ext))
print('applied to', P)

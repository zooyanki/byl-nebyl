"""Проверка раскладки на настоящем генераторе карты прототипа (node, только чтение): все точки на проходимом пепелище,
вне футпринтов пропов, проходимость не меняется от декора, горловина и вход в поляну свободны."""
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, '..', 'zalesye_mara_decor.json')))
ov = {"clearR": L["clearR"], "ash": L["ash"]}
json.dump(ov, open('/tmp/_ov_decor.json', 'w'))
json.dump({"clearR": L["clearR"], "ash": []}, open('/tmp/_ov_clear.json', 'w'))
run = lambda a: json.loads(subprocess.check_output(['node', os.path.join(HERE, 'dump_map.mjs')] + a))
base, deco, cur = run(['/tmp/_ov_clear.json']), run(['/tmp/_ov_decor.json']), run([])
W = deco['W']
ok = True
def tile(x, y): return deco['ground'][int(y) * W + int(x)]
def walk(d, x, y): return d['walk'][int(y * 2)][int(x * 2)]
blocking = [p for p in deco['props'] if p['fp'] and p['fp'][2] > 0]
def in_fp(x, y):
    return [p['type'] for p in blocking if p['fp'][0] <= x < p['fp'][0] + p['fp'][2] and p['fp'][1] <= y < p['fp'][1] + p['fp'][3]]
pts = [('ash', i, a[0] + 0.5, a[1] + 0.5) for i, a in enumerate(L['ash'])] + [('stump', i, s[0] + 0.5, s[1] + 0.5) for i, s in enumerate(L['stumps'])]
C = (56.5, 16.5)
for kind, i, x, y in pts:
    r = math.hypot(x - C[0], y - C[1]); ang = math.degrees(math.atan2(y - C[1], x - C[0])) % 360
    issues = []
    if walk(deco, x, y) == '#': issues.append('blocked')
    f = in_fp(x, y)
    if f: issues.append('inside ' + ','.join(f))
    if kind == 'stump' and tile(x, y) != 4: issues.append('not ash ground')
    near = min(math.hypot(x - u, y - v) for k2, j, u, v in pts if (k2, j) != (kind, i))
    print(f'{kind:5} {i:2}  centre ({x:5.1f},{y:5.1f})  r {r:4.1f}  ang {ang:5.1f}  nearest {near:3.1f}  {" ".join(issues) or "ok"}')
    if issues and not (kind == 'ash' and i < 10 and issues == ['not ash ground']): ok = ok and not issues
same = base['walk'] == deco['walk']
print('walkability identical with/without decor (clearR %.1f):' % L['clearR'], same)
diff = sum(a != b for ra, rb in zip(cur['walk'], base['walk']) for a, b in zip(ra, rb))
print('half-tiles changed vs current prototype data (old ash -> new decor): %d' % diff)
json.dump({"ash": []}, open('/tmp/_ov_noash.json', 'w'))
noash = run(['/tmp/_ov_noash.json'])
blk = [(x / 2, y / 2) for y, (ra, rb) in enumerate(zip(cur['walk'], noash['walk'])) for x, (a, b) in enumerate(zip(ra, rb)) if a == '#' and b != '#']
cut = [(x / 2, y / 2) for y, (ra, rb) in enumerate(zip(cur['walk'], noash['walk'])) for x, (a, b) in enumerate(zip(ra, rb)) if a == ',' and b == '.']
cur_ash = [p for p in cur['props'] if p['type'] == 'ash']
bad = [[p['x'], p['y']] for p in cur_ash if (p['fp'][0] * 2) % 1 and (p['fp'][1] * 2) % 1]
print('CURRENT prototype ash (%d): off-grid points %s -> invisible ½-tile blockers at %s; half-tiles cut off from reach: %s' % (len(cur_ash), bad, blk, cut))
n_ash = sum(1 for p in deco['props'] if p['type'] == 'ash')
print('ash props in generated map:', n_ash)
sys.exit(0 if ok and same else 1)

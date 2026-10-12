"""m1j (GDD v1.13 D3, §9.3 B-35): пул гибели с Крившей — 9 зёрен × 30 боёв × 3 сценария (бот checks_v18 FIGHT, эталонный герой 6 ур.).
python tools/run_krivsha_pool.py --url http://127.0.0.1:8043/index.html?seed=7 [--runs 30] → tools/krivsha_pool_m1j.json"""
import argparse, asyncio, json, os, sys
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from checks_v18 import FIGHT
from checks_m1b import SEEDED
SEEDS = [20261008, 1, 7, 11, 23, 42, 100, 2026, 31337]      # те же 9 зёрен, что в M1d / GDD v1.13 §9.3
SCEN = [('noPhase_kit10', {'hearths': 0, 'kit': {'life1': 10, 'zhivaya': 1, 'yar1': 3}}),
        ('phase1_belt15', {'hearths': 1, 'kit': {'life1': 15, 'zhivaya': 1, 'yar1': 0}}),
        ('phase3_belt15', {'hearths': 3, 'kit': {'life1': 15, 'zhivaya': 1, 'yar1': 0}})]
async def main(a):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--autoplay-policy=no-user-gesture-required'])
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(a.url); await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=60000)
        if a.block: print('block policy', await pg.evaluate(open(os.path.join(HERE, 'block_policy.js'), encoding='utf-8').read()))   # m1l: справочно с блоком (GDD v1.14 §4.7)
        await pg.evaluate(FIGHT)
        out = {}
        for name, o in [x for x in SCEN if not a.scen or x[0] == a.scen]:
            per = []
            for sd in SEEDS:
                r = await pg.evaluate('''(async () => { const g = __game; __P__ const keep = g.hero; const r = await __fight(__O__); g.hero = keep; Math.random = rnd0; return r; })()'''
                                      .replace('__P__', SEEDED).replace('__O__', json.dumps({**o, 'runs': a.runs, 'seed': sd})))
                per.append({'seed': sd, 'deaths': r['deaths'], 'won': r['won'], 'mean': r['mean']})
            tot = sum(x['deaths'] for x in per); n = a.runs * len(SEEDS)
            ts = [x['mean'] for x in per if x['mean']]
            out[name] = {'deaths': tot, 'fights': n, 'per30': round(tot * 30 / n, 2), 'bySeed': [x['deaths'] for x in per], 'meanT': round(sum(ts) / len(ts), 1) if ts else None}
            print(name, json.dumps(out[name]), flush=True)
        await br.close()
    print('errors', errs[:3])
    OUTF = a.out or (os.path.join(HERE, 'krivsha_pool_m1j.json') if not a.scen else '/tmp/krivsha_pool_' + a.scen + '.json'); d = json.load(open(OUTF)) if os.path.exists(OUTF) else {}
    d.update(out); json.dump(d, open(OUTF, 'w'), ensure_ascii=False, indent=1)
ap = argparse.ArgumentParser(); ap.add_argument('--url', default='http://127.0.0.1:8043/index.html?seed=7'); ap.add_argument('--runs', type=int, default=30); ap.add_argument('--scen', default=''); ap.add_argument('--out', default='')   # m1l: свой файл замера
ap.add_argument('--block', type=int, default=0)
asyncio.run(main(ap.parse_args()))

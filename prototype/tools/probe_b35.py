"""B-35: воспроизводимость замера «Кривша без фазы, запас 10+1+3». Запуск: probe_b35.py [--runs 30] [--reps 3] [--throttle 4] [--noclick]"""
import argparse, asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from playwright.async_api import async_playwright
from checks_v18 import FIGHT
from checks_m1b import SEEDED

async def main(a):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--autoplay-policy=no-user-gesture-required'])
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        if a.throttle > 1:
            cdp = await pg.context.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate', {'rate': a.throttle})
        await pg.goto(a.url); await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=30000)
        if not a.noclick:
            await pg.mouse.click(960, 300); await pg.wait_for_timeout(300)
        await pg.evaluate(FIGHT)
        o = {'hearths': a.hearths, 'kit': json.loads(a.kit), 'runs': a.runs}
        if a.seed: o['seed'] = a.seed
        for rep in range(a.reps):
            r = await pg.evaluate('''(async () => { const g = __game; __P__ const keep = g.hero; const r = await __fight(__O__); g.hero = keep; Math.random = rnd0; return r; })()'''
                                  .replace('__P__', SEEDED).replace('__O__', json.dumps(o)))
            print(f"rep{rep} deaths={r['deaths']}/{r['runs']} mean={r['mean']} sig={r.get('sig','')}", flush=True)
        await br.close()

ap = argparse.ArgumentParser()
ap.add_argument('--url', default='http://127.0.0.1:8031/index.html?seed=7')
ap.add_argument('--runs', type=int, default=30); ap.add_argument('--reps', type=int, default=3)
ap.add_argument('--throttle', type=float, default=1); ap.add_argument('--noclick', action='store_true'); ap.add_argument('--seed', type=int, default=0); ap.add_argument('--hearths', type=int, default=0); ap.add_argument('--kit', default='{"life1": 10, "zhivaya": 1, "yar1": 3}')
asyncio.run(main(ap.parse_args()))

"""Замер зачистки Залесья эталонным ботом GDD v1.9 (tools/bot_zalesye_clear.js). python tools/run_bot_zalesye.py --seed 7 [--runs 30] [--throttle 4]
Результат дописывается в tools/bot_zalesye_m1d.json (ключ seed[_throttle])."""
import argparse, asyncio, json, os
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'bot_zalesye_m1d.json')
async def main(a):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--autoplay-policy=no-user-gesture-required'])
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        if a.throttle > 1:
            cdp = await pg.context.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate', {'rate': a.throttle})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(a.url); await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=60000)
        await pg.mouse.click(960, 300); await pg.wait_for_timeout(300)
        await pg.evaluate(f'window.__N = {a.runs}; window.__SEED = {a.seed}; window.__CAP = {a.cap};')
        r = await pg.evaluate(open(os.path.join(HERE, 'bot_zalesye_clear.js')).read())
        await br.close()
    det = r.pop('det'); print(json.dumps(r, ensure_ascii=False)); print('errors', errs[:3])
    d = json.load(open(OUT)) if os.path.exists(OUT) else {}
    d[str(a.seed) + ('_throttle%g' % a.throttle if a.throttle > 1 else '')] = {**r, 'det': det}
    json.dump(d, open(OUT, 'w'), ensure_ascii=False, indent=1)
ap = argparse.ArgumentParser(); ap.add_argument('--url', default='http://127.0.0.1:8031/index.html?seed=7')
ap.add_argument('--seed', type=int, default=7); ap.add_argument('--runs', type=int, default=30); ap.add_argument('--cap', type=int, default=400); ap.add_argument('--throttle', type=float, default=1)
asyncio.run(main(ap.parse_args()))

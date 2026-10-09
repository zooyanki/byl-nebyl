"""Справочный замер Огнеи Пепельной (id mara) по правилам GDD v1.12.1 §9.3 — бот дизайнера tools/bot_mara_ref_v1121.js.
python3 tools/run_bot_mara_v1121.py --url URL [--seed 7] [--runs 30] [--lvl 4] [--pot 6] [--rule v1121|petr] [--flee 0|1] [--out FILE]
Правила §9.3: без отхода (--flee 0, по умолчанию; у бота дизайнера теперь тоже __FLEE 0 по умолчанию, 1 — вариант с отходом). Результат дописывается в tools/bot_mara_m1h.json
(ключ {rule}_lvl{L}_pot{P}_seed{S}[_flee])."""
import argparse, asyncio, json, os
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
async def main(a):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--autoplay-policy=no-user-gesture-required'])
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(a.url); await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=60000)
        await pg.mouse.click(960, 300); await pg.wait_for_timeout(300)
        await pg.evaluate(f"window.__N = {a.runs}; window.__SEED = {a.seed}; window.__LVL = {a.lvl}; window.__POT = {a.pot}; window.__RULE = '{a.rule}'; window.__FLEE = {a.flee};")
        r = await pg.evaluate(open(os.path.join(HERE, 'bot_mara_ref_v1121.js'), encoding='utf-8').read())
        await br.close()
    print(json.dumps(r, ensure_ascii=False)); print('errors', errs[:3])
    out = a.out or os.path.join(HERE, 'bot_mara_m1h.json')
    d = json.load(open(out)) if os.path.exists(out) else {}
    d[f'{a.rule}_lvl{a.lvl}_pot{a.pot}_seed{a.seed}' + ('_flee' if a.flee else '')] = r
    json.dump(d, open(out, 'w'), ensure_ascii=False, indent=1)
ap = argparse.ArgumentParser(); ap.add_argument('--url', default='http://127.0.0.1:8039/index.html?seed=7')
ap.add_argument('--seed', type=int, default=7); ap.add_argument('--runs', type=int, default=30); ap.add_argument('--lvl', type=int, default=4)
ap.add_argument('--pot', type=int, default=6); ap.add_argument('--rule', default='v1121'); ap.add_argument('--flee', type=int, default=0)
ap.add_argument('--out', default='')
asyncio.run(main(ap.parse_args()))

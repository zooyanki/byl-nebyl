# Профиль кадра: update / мир (renderer.render и его шаги) / слой интерфейса; запуск: prof_opt.py firefox kapishche
import asyncio, json, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from perf_v2light import SCEN
from playwright.async_api import async_playwright
WRAP = '''(() => { const g = __game, T = window.__T = {}; const w = (o, k, name) => { const f = o[k]; o[k] = function (...a) { const t = performance.now(); try { return f.apply(this, a); } finally { T[name] = (T[name] || 0) + performance.now() - t; } }; };
  w(g, 'update', 'update'); w(g, 'render', 'render'); g._prof = T;
  const R = Object.getPrototypeOf(g.renderer); for (const k of Object.getOwnPropertyNames(R)) if (k !== 'constructor' && k !== 'render' && typeof R[k] === 'function') w(g.renderer, k, 'w.' + k);
  w(g.renderer.light, 'draw', 'L.draw'); for (const k of ['drawMist', 'drawUnder', 'drawOver']) w(g.renderer.atmo, k, 'A.' + k);
  window.__F0 = g.frames; window.__t0 = performance.now(); })()'''
async def main(bn, scs):
    async with async_playwright() as p:
        bt = getattr(p, bn); br = await (bt.launch(executable_path='/usr/bin/google-chrome') if bn == 'chromium' else bt.launch())
        for sc in scs.split(','):
            pg = await br.new_page(viewport={'width': 1920, 'height': 1080}); await pg.add_init_script("window.__dlgAuto = true;")
            await pg.goto('http://127.0.0.1:8047/index.html?seed=7'); await pg.wait_for_function('window.__game && __game.time > 0.5', timeout=90000)
            await pg.mouse.move(1270, 10)
            await pg.evaluate("(() => { const g = __game; g.state = 'play'; g.ui.closeAll(); g.dlgWin = null; g.settings.lightQ = 'high'; })()")
            await pg.evaluate(SCEN[sc]); await pg.wait_for_timeout(1500); await pg.evaluate(WRAP); await pg.wait_for_timeout(8000)
            r = await pg.evaluate("(() => { const n = __game.frames - __F0, el = performance.now() - __t0; const o = { fps: +(n / el * 1000).toFixed(1) }; for (const [k, v] of Object.entries(__T).sort((a, b) => b[1] - a[1])) if (v / n > 0.05) o[k] = +(v / n).toFixed(2); return o; })()")
            print(bn, sc, json.dumps(r), flush=True); await pg.close()
        await br.close()
asyncio.run(main(sys.argv[1], sys.argv[2]))

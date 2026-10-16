"""v2light: замер FPS и времени отрисовки (ms/кадр) — Ладога ночью, бой в Залесье со «змеем», Капище; Firefox и Chromium, 1920×1080 (v2art: 960×540 ×2; было 1280×720 — --vw/--vh).
  python3 tools/perf_v2light.py [--url http://127.0.0.1:8047/index.html?seed=7] [--sec 20] [--browsers firefox,chromium] [--quality high]
Результат — tools/perf_v2light_<quality>.json. FPS — по интервалам requestAnimationFrame (средний и «1% low» = FPS по 99-му перцентилю
интервала), время отрисовки — game.renderTimes (Game.render целиком: мир, свет, атмосфера, HUD)."""
import argparse, asyncio, json, os
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))

SCEN = {
    'ladoga': '''(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.invuln = 1e9;
        const pts = [[h.x + 6, h.y - 4], [h.x + 10, h.y + 2], [h.x + 2, h.y + 6], [h.x - 3, h.y + 1], [h.x, h.y]]; let i = 0;
        window.__perfDrv = setInterval(() => { const p = pts[i++ % pts.length]; h.moveTo(g.map, p[0], p[1]); }, 2500); })()''',
    'zalesye': '''(() => { const g = __game; g.enterZone('zalesye', 'krada'); const h = g.hero; h.invuln = 1e9; h.x = 30; h.y = 24; g.updateCamera();
        g.enemies = g.enemies.filter(e => !e.special);
        for (let i = 0; i < 8; i++) { const e = g.spawnTest(i % 2 ? 'anchutka' : 'upyr', h.x + 3 + (i % 4), h.y - 2 + Math.floor(i / 4) * 3, 1); e.hp = e.maxHp = 1e6; }
        let k = 0; window.__perfDrv = setInterval(() => { const a = k++ * 0.7; h.yar = h.maxYar;
          g.combat.castProjectile(h, 'zmey', h.x + Math.cos(a) * 6, h.y + Math.sin(a) * 6); }, 450); })()''',
    'kapishche': '''(() => { const g = __game; g.enterZone('kapishche', 'start'); const h = g.hero; h.invuln = 1e9;
        const x0 = h.x, y0 = h.y, pts = [[x0 + 5, y0 - 3], [x0 + 8, y0 + 3], [x0 + 2, y0 + 5], [x0, y0]]; let i = 0;
        window.__perfDrv = setInterval(() => { const p = pts[i++ % pts.length]; h.moveTo(g.map, p[0], p[1]); }, 2500); })()''',
}
MEASURE = '''((sec) => new Promise((res) => { const g = __game, iv = []; let last = performance.now(); const r0 = g.renderTimes.length, l0 = (g.lightTimes || []).length; const t0 = last;
    const tick = (now) => { iv.push(now - last); last = now; if (now - t0 < sec * 1000) requestAnimationFrame(tick); else {
      clearInterval(window.__perfDrv); const rt = g.renderTimes.slice(r0).sort((a, b) => a - b), s = iv.slice(5).sort((a, b) => a - b);
      const lt = (g.lightTimes || []).slice(l0), lavg = lt.length ? lt.reduce((a, b) => a + b, 0) / lt.length : 0; const avg = s.reduce((a, b) => a + b, 0) / s.length, p99 = s[Math.floor(s.length * 0.99)], ra = rt.reduce((a, b) => a + b, 0) / rt.length;
      res({ frames: s.length, fps: +(1000 / avg).toFixed(1), low1: +(1000 / p99).toFixed(1), renderAvg: +ra.toFixed(2), renderP95: +rt[Math.floor(rt.length * 0.95)].toFixed(2),
        renderP99: +rt[Math.floor(rt.length * 0.99)].toFixed(2), lightAvg: +lavg.toFixed(2), lights: g.lightInfo && g.lightInfo.lights, sparks: g.atmoInfo && g.atmoInfo.sparks,
        canvas: [g.canvas.width, g.canvas.height, g.canvas.style.width, g.canvas.style.height] }); } };
    requestAnimationFrame(tick); }))'''


async def run(a):
    out = {}
    async with async_playwright() as p:
        for bname in a.browsers.split(','):
            bt = getattr(p, bname)
            br = await (bt.launch(executable_path=a.chrome) if bname == 'chromium' and a.chrome else bt.launch())
            for sc, js in SCEN.items():
                if a.scen and sc not in a.scen.split(','): continue
                pg = await br.new_page(viewport={'width': a.vw, 'height': a.vh})
                await pg.add_init_script("window.__dlgAuto = true;")
                await pg.goto(a.url)
                await pg.wait_for_function('window.__game && __game.time > 0.5', timeout=90000)
                await pg.mouse.move(1270, 10)
                await pg.evaluate(f"(() => {{ const g = __game; g.state = 'play'; g.ui.closeAll(); g.dlgWin = null; g.settings.lightQ = '{a.quality}'; g.lightOff = {'true' if a.off else 'false'}; }})()")
                await pg.evaluate(js)
                await pg.wait_for_timeout(1500)
                r = await pg.evaluate(MEASURE, a.sec)
                out[f'{bname}/{sc}'] = r
                print(bname, sc, json.dumps(r, ensure_ascii=False), flush=True)
                await pg.close()
            await br.close()
    json.dump(out, open(os.path.join(HERE, f'perf_{a.tag}_{a.quality}{"_off" if a.off else ""}.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8047/index.html?seed=7')
    ap.add_argument('--sec', type=float, default=20)
    ap.add_argument('--browsers', default='firefox,chromium')
    ap.add_argument('--chrome', default='/usr/bin/google-chrome')
    ap.add_argument('--quality', default='high')
    ap.add_argument('--vw', type=int, default=1920)
    ap.add_argument('--vh', type=int, default=1080)
    ap.add_argument('--tag', default='v2art', help='имя файла результата: tools/perf_<tag>_<quality>.json')
    ap.add_argument('--scen', default='')
    ap.add_argument('--off', action='store_true', help='свет и атмосфера выключены (game.lightOff) — база для сравнения')
    asyncio.run(run(ap.parse_args()))

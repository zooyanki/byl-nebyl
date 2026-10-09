"""Превью раскладки в самом прототипе (копия с патчем, headless Chrome через Playwright):
  python3 apply_to_copy.py /tmp/zdecor/b && (cd /tmp/zdecor/b && python3 -m http.server 8771 --bind 127.0.0.1 &)
  /workspace/.venv-pw/bin/python preview_ingame.py [url] [out.png]
Камера на (50,75; 17,75) — видны горловина, сарай и вся поляна; HUD и нечисть убраны (кроме Огнеи — для масштаба).
Кадр 1920×1080 = родные 640×360 ×3; сохраняется игровое поле 640×314 ×3."""
import asyncio, sys
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8771/index.html'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/zdecor/ingame'
CAM = (50.75, 17.75)


async def main():
    errs = []
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome')
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        pg.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errs.append(f'pageerror: {e}'))
        await pg.goto(URL)
        await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=20000)
        G = pg.evaluate
        info = await G('''(() => { const g = __game; if (g.zone.id !== "zalesye") { g.ui.closeAll(); g.enterZone("zalesye", "start"); }
          const keep = g.enemies.filter(e => e.kind === 'mara'); g.enemies = keep;
          for (const e of keep) { e.stagger = 1e9; e.moving = false; e.path = null; }
          const h = g.hero; h.x = %f; h.y = %f; h.path = null; h.cmd = null; h.moving = false; g.updateCamera();
          const st = g.map.props.filter(p => p.type === 'stump').length, ash = g.map.props.filter(p => p.type === 'ash').length;
          return { st, ash, mara: keep.map(e => [e.x.toFixed(1), e.y.toFixed(1)]), fx: Object.keys((window.FX || {}).sheets || {}).length }; })()''' % CAM)
        print('props:', info)
        await pg.wait_for_timeout(1500)
        await G('(() => { const h = __game.hero; h.x = %f; h.y = %f; h.path = null; h.cmd = null; __game.updateCamera(); })()' % CAM)
        # без HUD: только мир (render() игры подменяется в странице; файлы не меняются)
        await G('(() => { const g = __game; g.render = function () { const c = this.ctx; c.setTransform(1, 0, 0, 1, 0, 0); c.imageSmoothingEnabled = false; this.renderer.render(c, this); }; })()')
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=OUT + '_game.png', clip={'x': 0, 'y': 0, 'width': 1920, 'height': 942})
        # режим разбора: деревья, стоящие перед декором (x+y ≥ 58, восточнее x 34), полупрозрачны
        n = await G('''(() => { let n = 0; for (const p of __game.map.props) {
            if (p.type !== 'tree' || p.x < 34 || p.x + p.y < 58 || !p._spr || p._faded) continue;
            const s = p._spr, c = document.createElement('canvas'); c.width = s.c.width; c.height = s.c.height;
            const x = c.getContext('2d'); x.globalAlpha = 0.08; x.drawImage(s.c, 0, 0);
            p._spr = { c, ox: s.ox, oy: s.oy, mask: s.mask, W: s.W, H: s.H }; p._faded = true; n++; } return n; })()''')
        print('faded trees', n)
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=OUT + '_review.png', clip={'x': 0, 'y': 0, 'width': 1920, 'height': 942})
        await br.close()
    print('\n'.join(errs) or 'console clean')


asyncio.run(main())

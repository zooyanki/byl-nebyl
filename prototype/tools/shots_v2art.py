"""v2art: снимки 1920×1080 (холст 960×540 ×2) — Ладога (пристань, ладья, избы v2, окна), бой с упырём (герой v2 в атаке),
лес тропы (деревья v2), посад (тын v2), пауза. python3 tools/shots_v2art.py [--url ...] [--out DIR]"""
import argparse, asyncio, os
from playwright.async_api import async_playwright
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PREP = "(() => { const g = __game; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.dlgAuto = true; g.dlgWin = null; g.notice = null; g.notices = []; g.lightOff = false; g.settings.lightQ = 'high'; g.ctrlHintSeen = true; })()"
SCEN = {
    'ladoga': "(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.x = 30.5; h.y = 38.5; h.dir = 7; h.invuln = 1e9; g.updateCamera(); g.log.lines = []; })()",
    'fight': """(() => { const g = __game; g.enterZone('zalesye', 'krada'); const h = g.hero; h.invuln = 1e9; g.enemies = g.enemies.filter(e => !e.special);
        for (const e of g.enemies) { e.x += 40; }
        const e1 = g.spawnTest('upyr', h.x + 1.3, h.y + 0.2, 1); e1.hp = e1.maxHp = 1e6; const e2 = g.spawnTest('upyr', h.x - 0.4, h.y + 1.5, 1); e2.hp = e2.maxHp = 1e6;
        g.updateCamera(); g.log.lines = []; window.__e1 = e1; })()""",
    'forest': "(() => { const g = __game; g.enterZone('trail', 'from_zalesye'); const h = g.hero; h.invuln = 1e9; g.enemies = []; g.updateCamera(); g.log.lines = []; })()",
    'palisade': "(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.x = 9; h.y = 20; h.invuln = 1e9; g.updateCamera(); g.log.lines = []; })()",
}


async def main(a):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path=a.chrome)
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        pg.on('console', lambda m: print('console', m.type, m.text) if m.type in ('error', 'warning') else None)
        await pg.add_init_script('window.__dlgAuto = true;')
        await pg.goto(a.url)
        await pg.wait_for_function('window.__game && __game.time > 0.5', timeout=90000)
        await pg.mouse.move(1900, 20)
        for name in (a.only.split(',') if a.only else SCEN):
            await pg.evaluate(PREP)
            await pg.evaluate(SCEN[name])
            await pg.wait_for_timeout(1200)
            if name == 'fight':
                for _ in range(6):
                    await pg.evaluate("(() => { const g = __game, h = g.hero, e = window.__e1; if (!h.action) h.attack ? h.attack(e, g) : null; })()")
                    await pg.wait_for_timeout(120)
                await pg.evaluate("(() => { const g = __game, h = g.hero, e = window.__e1; g.hoverEnemy = e; g.lastTarget = e; e.lastHitT = 0.5; })()")
                await pg.wait_for_timeout(130)
            await pg.screenshot(path=os.path.join(a.out, f'screenshot_v2art_{name}.png'))
            print('shot', name, await pg.evaluate("(() => { const g = __game; return { zone: g.zone.id, v2: Object.keys((window.__v2c = 1, {})).length }; })()"))
        if not a.only or 'pause' in a.only:
            await pg.evaluate(PREP); await pg.evaluate(SCEN['ladoga']); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
            await pg.screenshot(path=os.path.join(a.out, 'screenshot_v2art_pause.png'))
        await br.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8047/index.html?seed=7')
    ap.add_argument('--chrome', default='/usr/bin/google-chrome')
    ap.add_argument('--out', default=ROOT)
    ap.add_argument('--only', default='')
    asyncio.run(main(ap.parse_args()))

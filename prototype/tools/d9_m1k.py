"""m1k v1.13.3 D9: доля укороченных + заменённых деревьев (сиды 7/11/3), проходимость (m.sub) и обзор как при старых
treeRules v1.13.2, снимки до/после: screenshot_m1k_d9_{zalesye,trail}_{before,after}.png.
  python3 tools/d9_m1k.py [--url http://127.0.0.1:8047/index.html?seed=7] [--no-shots]"""
from pathlib import Path
import argparse, asyncio, json
from playwright.async_api import async_playwright

ROOT = str(Path(__file__).resolve().parent.parent) + '/'   # B-39: корень прототипа от расположения файла
OLD = {'pathClear': 1.5, 'frontClear': 3, 'frontMaxH': {'fir': 96, 'birch': 112}, 'rings': ['hutDoor', 'pack'], 'maxRemovedPct': 25}

STATS = '''(async (OLD) => { const g = __game, M = await import('/src/world/map.js'), CFG = g.dbg.CFG, out = {};
  for (const zid of ['zalesye', 'trail']) for (const seed of [7, 11, 3]) {
    const Z = CFG.zones[zid], m = M.generateMap(seed, Z), m0 = M.generateMap(seed, { ...Z, treeRules: OLD }), st = m.treeStats;
    const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
    out[zid + '_' + seed] = { total: st.total, removed: st.removed, shortened: st.shortened, by: st.by, pctTouched: st.pctTouched,
      oldTouched: m0.treeStats.pctTouched, walkSame: same(m.sub, m0.sub), opaqueSame: same(m.opaque, m0.opaque) };
  }
  return out; })'''


async def main(a):
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path=a.chrome)
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        await pg.goto(a.url)
        await pg.wait_for_function('() => window.__game && __game.time > 0.3')
        out = await pg.evaluate(STATS, OLD)
        print(json.dumps(out, ensure_ascii=False))
        if not a.no_shots:
            for zid, entry in (('zalesye', 'krada'), ('trail', 'from_zalesye')):
                spot = None
                for tag, rules in (('after', None), ('before', OLD)):
                    spot = await pg.evaluate('''([zid, entry, rules, spot]) => { const g = __game, Z = g.dbg.CFG.zones[zid], keep = Z.treeRules;
                        if (rules) Z.treeRules = rules; g.dlgAuto = false; g.ui.closeAll(); delete g.zoneStates[zid]; g.enterZone(zid, entry);
                        Z.treeRules = keep; g.enemies = []; const h = g.hero; h.invuln = 1e9; h.stop && h.stop(); g.notices = []; g.noticeQ = [];
                        if (!spot) { // точка на пути (ломаная m.treePath), перед которой (+x/+y, ≤ 8 тайлов) больше всего укороченных деревьев
                          const T = g.map.props.filter(p => p.type === 'tree' && p.hMax), P = g.map.treePath; let best = -1;
                          for (let i = 0; i + 1 < P.length; i++) for (let k = 0; k <= 1; k += 0.1) { const x = P[i][0] + (P[i + 1][0] - P[i][0]) * k, y = P[i][1] + (P[i + 1][1] - P[i][1]) * k;
                            if (!g.map.isReachableAt(x, y)) continue;
                            const n = T.filter(p => { const dx = p.x - x, dy = p.y - y; return dx + dy > 0 && Math.hypot(dx, dy) < 8; }).length; if (n > best) { best = n; spot = [x, y]; } } }
                        h.x = spot[0]; h.y = spot[1]; g.updateCamera && g.updateCamera(); return spot; }''', [zid, entry, rules, spot])
                    await pg.wait_for_timeout(700)
                    await pg.evaluate('() => { __game.enemies = []; }')
                    await pg.wait_for_timeout(200)
                    await pg.screenshot(path=f'{ROOT}screenshot_m1k_d9_{zid}_{tag}.png')
                print(zid, 'точка', spot)
            await pg.evaluate("() => { const g = __game; delete g.zoneStates.zalesye; delete g.zoneStates.trail; }")
        await br.close()

ap = argparse.ArgumentParser()
ap.add_argument('--url', default='http://127.0.0.1:8047/index.html?seed=7')
ap.add_argument('--chrome', default='/usr/bin/google-chrome')
ap.add_argument('--no-shots', action='store_true')
asyncio.run(main(ap.parse_args()))

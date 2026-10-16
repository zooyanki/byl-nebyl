# Веха v2light: живой свет (буфер света, факелы, окна, «Огненный змей», виньетка), атмосфера (туман над водой, дым, искры,
# светлячки), переключатель «Качество света», «Ярь» → «Удаль» везде, где видит игрок, бюджет кадра.
from pathlib import Path
import json, os, re, subprocess, sys

ROOT = str(Path(__file__).resolve().parent.parent) + '/'
SHOTS = {k: ROOT + f'screenshot_v2light_{k}.png' for k in ('final', 'ladoga_before', 'ladoga_night', 'zmey_light', 'river_fog', 'forest_fireflies', 'kapishche')}

PREP = '''(() => { const g = __game; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.dlgAuto = true; g.dlgWin = null; g.notice = null; g.notices = [];
  g.lightOff = false; g.settings.lightQ = 'high'; g.simHold = false; })()'''
# средняя яркость (0..255) прямоугольника / кольца на холсте 640×360
LUM = '''(() => { window.__rd = (cv, x0, y0, w, h) => { const t = window.__rdc || (window.__rdc = document.createElement('canvas')); t.width = w; t.height = h;
    const x = t.getContext('2d', { willReadFrequently: true }); x.clearRect(0, 0, w, h); x.drawImage(cv, x0, y0, w, h, 0, 0, w, h); return x.getImageData(0, 0, w, h).data; };
  window.__lum = (x0, y0, w, h, cx, cy, r0, r1) => { const d = __rd(__game.canvas, x0, y0, w, h); let s = 0, n = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { if (cx != null) { const q = Math.hypot(x0 + x - cx, y0 + y - cy); if (q < r0 || q > r1) continue; }
    const i = (y * w + x) * 4; s += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; n++; } return n ? s / n : 0; }; })()'''
TP = '''(([x, y]) => { const h = __game.hero; h.x = x; h.y = y; h.path = null; h.cmd = null; h.action = null; h.moving = false; h.kb = null; __game.updateCamera(); })'''


async def run_v2light(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха v2light', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.3', timeout=90000)   # ≈1000 листов v2: 30 с не всегда хватало
    await pg.mouse.move(1910, 10)
    await wait(150)
    await G(PREP)
    await G(LUM)
    thr = max(1.0, float(getattr(a, 'throttle', 1) or 1))

    # ================= 1. свет: проход есть, буфер пониженного разрешения, факелы и окна в Ладоге
    await G("(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.x += 6; h.y -= 4; h.invuln = 1e9; g.updateCamera(); })()")
    await wait(400)
    s = await G('''(async () => { const g = __game, L = await import('/src/render/light.js'), C = await import('/src/config.js'), R = g.renderer;
        const S = g.dbg.CFG.stats; g.render(); const li = g.lightInfo;
        return { li, buf: R.light.dark && [R.light.dark.width, R.light.dark.height], view: [C.VIEW_W, C.VIEW_H], cfg: !!(S.light && S.atmo),
          k: S.light.bufScale, src: (await (await fetch('/src/render/world.js')).text()) }; })()''')
    src = s.pop('src')
    li = s['li']
    check('v2light 1 проход света: буфер темноты/тепла ½ кадра, растяжка со сглаживанием — мягкий градиент (stats.light.bufScale.high, smooth), блоки light/atmo в stats.json, свет до подписей, HUD после мира',
          s['cfg'] and s['buf'] == [s['view'][0] * s['k']['high'], s['view'][1] * s['k']['high']] and li.get('lights', 0) > 0
          and src.find('this.renderLight(ctx, game, toS)') < src.find('this.renderLabels(uc, game, toU)'), {'buf': s['buf'], 'lights': li.get('lights')})
    check('v2light 1 Ладога ночью: свет у факелов (огни зоны и torch_A/B ворот) и у окон/дверей изб', li.get('torches', 0) >= 2 and li.get('windows', 0) >= 1,
          {k: li.get(k) for k in ('torches', 'windows', 'lights', 'culled')})
    # окно: яркость у точки окна выше, чем при снятом свете окон (тот же кадр, время стоит — g.render() синхронно)
    s = await G('''(() => { const g = __game, R = g.renderer; g.render();
        const P = g.map.props.filter(p => p._litF === R._frameNo && (p._lights || []).some(l => l[2] === 'window'));
        let best = null; for (const p of P) { const [bx, by] = g.toS(p.x, p.y); for (const l of p._lights) if (l[2] === 'window') { const x = bx + l[0], y = by + l[1];
          if (x > 30 && x < 930 && y > 30 && y < 480 && (!best || Math.abs(x - 480) < Math.abs(best.x - 480))) best = { p, x, y }; } }
        if (!best) return { none: true };
        const on = __lum(best.x - 12, best.y - 12, 24, 24); const keep = best.p._lights; best.p._lights = []; g.render();
        const off = __lum(best.x - 12, best.y - 12, 24, 24); best.p._lights = keep; g.render(); return { on: +on.toFixed(1), off: +off.toFixed(1), at: [best.x, best.y] }; })()''')
    check('v2light 1 окно светит: яркость у окна выше, чем без его света', not s.get('none') and s['on'] > s['off'] + 3, s)
    # читаемость: герой в окне света почти так же ярок, как без света; подписи и HUD — после света
    s = await G('''(() => { const g = __game, [hx, hy] = g.toS(g.hero.x, g.hero.y); g.render(); const on = __lum(hx - 8, hy - 40, 16, 38);
        g.lightOff = true; g.render(); const off = __lum(hx - 8, hy - 40, 16, 38); g.lightOff = false; g.render(); return { on: +on.toFixed(1), off: +off.toFixed(1) }; })()''')
    check('v2light 1 читаемость: герой в свете ≥ 75% яркости кадра без света', s['on'] >= 0.75 * s['off'], s)
    # виньетка: углы кадра темнеют, центр — нет
    s = await G('''(() => { const R = __game.renderer, v = R.light.vignette();
        return { corner: __rd(v, 0, 0, 1, 1)[3], center: __rd(v, v.width >> 1, v.height >> 1, 1, 1)[3], a: __game.dbg.CFG.stats.light.vignette.a }; })()''')
    check('v2light 1 виньетка (в буфере темноты): края кадра затемнены (альфа угла ≈ stats.light.vignette.a), центр чистый', s['center'] == 0 and abs(s['corner'] / 255 - s['a']) < 0.08, s)
    # огонь дрожит: радиус огня меняется во времени (flick)
    s = await G('''(async () => { const L = await import('/src/render/light.js'); const v = [0, 0.3, 0.7, 1.1, 1.9].map(t => L.flick(t, 1.3)); return { v, span: Math.max(...v) - Math.min(...v) }; })()''')
    check('v2light 1 мягкое дрожание огня (flick 0..1, размах > 0,2)', s['span'] > 0.2 and all(0 <= x <= 1 for x in s['v']), s)

    # ================= 2. атмосфера Ладоги: туман над водой, клубы дыма; светлячков нет (не лес)
    await wait(1500)
    s = await G('''(() => { const g = __game, A = g.atmoInfo, S = g.dbg.CFG.stats.atmo; return { A, mistMax: S.mist.max, ff: (S.fireflies.zones || []).includes('ladoga') }; })()''')
    A = s['A']
    check('v2light 2 Ладога: туман над рекой (пятна ≤ atmo.mist.max), дым над печными постройками (≤ кап), светлячков нет',
          0 < A['mist'] <= s['mistMax'] and 0 < A['smoke'] <= A['smokeCap'] and A['fireflies'] == 0, A)
    await G('(() => { __game.lightOff = true; })()'); await wait(120)
    await pg.screenshot(path=SHOTS['ladoga_before'])
    await G('(() => { __game.lightOff = false; })()'); await wait(300)
    await pg.screenshot(path=SHOTS['ladoga_night'])
    check('v2light скриншоты screenshot_v2light_ladoga_before.png (свет выкл.) и screenshot_v2light_ladoga_night.png', all(os.path.exists(SHOTS[k]) for k in ('final', 'ladoga_before', 'ladoga_night')))
    await G(TP + "([__game.map.w * 0 + __game.hero.x - 6, __game.hero.y + 4])")
    await wait(500)
    await pg.screenshot(path=SHOTS['river_fog'])
    mist = await G('__game.atmoInfo.mist')
    check('v2light скриншот screenshot_v2light_river_fog.png: туман над водой', os.path.exists(SHOTS['river_fog']) and mist > 0, mist)
    rf = await G('__game.atmoInfo.reflect')
    check('v2light 2 отражения огней и окон в воде (дрожащие чёрточки только над водой)', rf > 0, rf)

    # главный кадр: Ладога у пристани — вода, избы с окнами, змей в полёте освещает землю, отражения
    await G("(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.x -= 1; h.y -= 3; g.updateCamera(); })()")
    await wait(1200)
    fz = await G('''(() => { const g = __game, h = g.hero; g.combat.castProjectile(h, 'zmey', h.x - 3, h.y + 5); const p = g.combat.projectiles[g.combat.projectiles.length - 1];
        g.simHold = true; for (let i = 0; i < 16 && g.combat.projectiles.includes(p); i++) { g.simulate(1 / 60); g.render(); }
        return { alive: g.combat.projectiles.includes(p), win: g.lightInfo.windows, rf: g.atmoInfo.reflect, sp: g.atmoInfo.sparks }; })()''')
    await pg.screenshot(path=SHOTS['final'])
    await G('(() => { __game.simHold = false; })()')
    check('v2light скриншот screenshot_v2light_final.png: пристань, окна изб, отражения, змей в полёте с искрами', os.path.exists(SHOTS['final']) and fz['alive'] and fz['win'] > 0 and fz['rf'] > 0 and fz['sp'] > 0, fz)

    # ================= 3. «Огненный змей» освещает землю; искры следа и взрыва с потолком
    await G("(() => { const g = __game; g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; g.combat.projectiles = []; const h = g.hero; h.invuln = 1e9; h.x = 30; h.y = 24; h.stop && h.stop(); g.updateCamera(); })()")
    await wait(300)
    s = await G('''(() => { const g = __game, h = g.hero; g.combat.projectiles = []; g.combat.castProjectile(h, 'zmey', h.x + 5, h.y - 5);
        const p = g.combat.projectiles[0]; p.x = h.x + 4.5; p.y = h.y - 4.5; p.vx = p.vy = 0; const [sx, sy] = g.toS(p.x, p.y);
        g.render(); const on = __lum(sx - 50, sy - 56, 100, 100, sx, sy - 6, 16, 46), zm = g.lightInfo.zmey.length;
        g.combat.projectiles = []; g.render(); const off = __lum(sx - 50, sy - 56, 100, 100, sx, sy - 6, 16, 46);
        return { on: +on.toFixed(1), off: +off.toFixed(1), zm, at: [sx, sy] }; })()''')
    check('v2light 3 «Огненный змей» в полёте освещает землю: яркость кольца 16–46 px вокруг точки под ним выше, чем без снаряда', s['zm'] == 1 and s['on'] > s['off'] * 1.15 + 4, s)
    s = await G('''(() => new Promise((res) => { const g = __game, h = g.hero; let mx = 0, cap = 0, burst = 0, i = 0;
        const iv = setInterval(() => { if (i < 30) { h.yar = h.maxYar; g.combat.castProjectile(h, 'zmey', h.x + 6 * Math.cos(i), h.y + 6 * Math.sin(i)); i++; }
          const A = g.atmoInfo; mx = Math.max(mx, A.sparks); cap = A.sparkCap; }, 40);
        setTimeout(() => { clearInterval(iv); const R = g.renderer; burst = R.atmo.lastBurst ? 1 : 0; res({ max: mx, cap, burst }); }, 2600); }))''')
    check('v2light 3 искры: след змея и залп при взрыве, число ≤ atmo.sparks.max даже при 30 змеях', 0 < s['max'] <= s['cap'] and s['burst'] == 1, s)
    # снимок: змей летит, земля под ним светится, искры
    await G("(() => { const g = __game, h = g.hero; for (let i = 0; i < 4; i++) { const e = g.spawnTest('upyr', h.x - 6.5 - i * 0.6, h.y + 4 + i * 0.5, 1); e.hp = e.maxHp = 1e6; e.stagger = 1e9; } g.combat.projectiles = []; h.yar = h.maxYar; g.combat.castProjectile(h, 'zmey', h.x - 6.5, h.y + 4); window.__zp = g.combat.projectiles[g.combat.projectiles.length - 1]; })()")
    await pg.mouse.move(*(await client_scr(200, 300)))
    zs = await G('''(() => { const g = __game; g.simHold = true; const p = window.__zp;
        for (let i = 0; i < 40 && g.combat.projectiles.includes(p) && p.travelled < 2.6; i++) { g.simulate(1 / 60); g.render(); }
        return { alive: g.combat.projectiles.includes(p), tr: +p.travelled.toFixed(2), sparks: g.atmoInfo.sparks }; })()''')
    await pg.screenshot(path=SHOTS['zmey_light'])
    await G('(() => { __game.simHold = false; })()')
    check('v2light скриншот screenshot_v2light_zmey_light.png: змей в полёте освещает землю, искры следа', os.path.exists(SHOTS['zmey_light']) and zs['alive'] and zs['sparks'] > 0, zs)

    # ================= 4. светлячки в лесной зоне
    await G("(() => { const g = __game; g.enemies = []; g.combat.projectiles = []; })()")
    await wait(800)
    s = await G('''(() => { const g = __game, A = g.atmoInfo, F = g.dbg.CFG.stats.atmo.fireflies; return { n: A.fireflies, max: F.max, want: F.n }; })()''')
    check('v2light 4 Залесье в сумерках: светлячки есть, не больше atmo.fireflies.max', 0 < s['n'] <= s['max'], s)
    await pg.screenshot(path=SHOTS['forest_fireflies'])
    check('v2light скриншот screenshot_v2light_forest_fireflies.png', os.path.exists(SHOTS['forest_fireflies']))

    # ================= 5. Капище: красноватая тьма сохранена, светлячков и тумана нет
    await G("(() => { const g = __game; g.enterZone('kapishche', 'start'); g.hero.invuln = 1e9; g.updateCamera(); })()")
    await wait(700)
    s = await G('''(() => { const g = __game, li = g.lightInfo, A = g.atmoInfo; return { am: li.ambient, fires: li.torches, ff: A.fireflies, mist: A.mist }; })()''')
    check('v2light 5 Капище: сумерки красноватые (R > 2B), огни горят, без светлячков и тумана', s['am'][0] > 2 * s['am'][2] and s['fires'] > 0 and s['ff'] == 0 and s['mist'] == 0, s)
    await pg.screenshot(path=SHOTS['kapishche'])
    check('v2light скриншот screenshot_v2light_kapishche.png', os.path.exists(SHOTS['kapishche']))

    # ================= 6. переключатель «Качество света» в паузе (ru.json), low: буфер ¼, частиц меньше
    await G("(() => { const g = __game; g.enterZone('zalesye', 'krada'); g.enemies = []; g.paused = true; })()")
    await wait(150)
    b = await G('''(async () => { const S = await import('/src/render/screens.js'); const b = S.PAUSE_BTNS.find(x => x.id === 'lightQ');
        return b && { key: b.key, txt: __game.t(b.key), p: [b.x + b.w - 10, b.y + 6] }; })()''')
    c = await client_scr(*b['p'])
    await pg.mouse.click(c[0], c[1]); await wait(120)
    await G('(() => { __game.paused = false; })()'); await wait(400)
    lo = await G('(() => ({ q: __game.settings.lightQ, k: __game.lightInfo.k, cap: __game.atmoInfo.sparkCap, ff: __game.atmoInfo.fireflies }))()')
    await G('(() => { __game.paused = true; })()'); await wait(120)
    await pg.mouse.click(c[0], c[1]); await wait(120)
    await G('(() => { __game.paused = false; })()'); await wait(300)
    hi = await G('(() => ({ q: __game.settings.lightQ, k: __game.lightInfo.k, cap: __game.atmoInfo.sparkCap, ff: __game.atmoInfo.fireflies }))()')
    ru = json.load(open(ROOT + 'data/ru.json', encoding='utf-8'))
    check('v2light 6 пауза: «Качество света» (ключ ru.json) — щелчок: low (буфер ¼ без сглаживания, кап искр ×0,5, светлячков меньше), ещё щелчок: high',
          b and b['key'] in ru and b['txt'] == ru[b['key']] and lo['q'] == 'low' and lo['k'] == 0.25 and hi['q'] == 'high' and hi['k'] == 0.5 and lo['cap'] < hi['cap'] and lo['ff'] < hi['ff'], {'btn': b, 'lo': lo, 'hi': hi})

    # ================= 7. «Ярь» → «Удаль»: нигде, что видит игрок
    r = subprocess.run([sys.executable, ROOT + 'tools/check_rename.py'], capture_output=True, text=True)
    vals = [v for k, v in ru.items() if k != '_about' and isinstance(v, str)] + [x for k, v in ru.items() if isinstance(v, list) for x in v if isinstance(x, str)]
    yar = [v for v in vals if re.search(r'(?<![\w-])[Яя]р(?:ь|и|ью|ей)(?![\w-])', v)]
    ui = open(ROOT + 'tools/export_ui.py', encoding='utf-8').read()
    hud = await G("__game.t('ui.hud.yar')")
    check('v2light 7 «Ярь» → «Удаль»: шар — «Удаль», в ru.json/данных/коде (check_rename) 0, в запекаемых надписях атласов (export_ui.py) нет',
          r.returncode == 0 and not yar and hud == 'Удаль' and not re.search(r'[Яя]р[ьи]\b', ui), {'hud': hud, 'ru': yar[:3], 'rc': r.returncode})

    # ================= 8. бюджет кадра: Game.render (мир + свет + атмосфера + HUD), Ладога ночью
    await G("(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.x += 6; h.y -= 4; g.updateCamera(); g.renderTimes.length = 0; })()")
    await wait(2500)
    s = await G('''(() => { const r = __game.renderTimes.slice().sort((a, b) => a - b); return { n: r.length, med: +r[Math.floor(r.length / 2)].toFixed(2), p95: +r[Math.floor(r.length * 0.95)].toFixed(2), budget: __game.dbg.CFG.stats.light.budgetMs }; })()''')
    check(f'v2light 8 бюджет кадра: медиана Game.render ≤ stats.light.budgetMs × замедление ЦП ({thr:g}×) в Ладоге ночью', s['n'] > 10 and s['med'] <= s['budget'] * thr, s)

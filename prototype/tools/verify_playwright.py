"""Автопроверка прототипа (итерация 2) в headless Chrome через Playwright.

  python3 -m http.server 8765 --bind 127.0.0.1 &      # из папки prototype
  python3 tools/verify_playwright.py [--url http://127.0.0.1:8765/index.html?seed=7] [--chrome /usr/bin/google-chrome]

Проверки: конфиги JSON загружены и числа по GDD v1.2 -> полутайловая коллизия (стоять в свободной половине
тайла у тонкой стены) -> нечисть не пропускает героя сквозь себя и не слипается -> взрыв «Огненного змея»
не бьёт через стену -> хит-стоп и отбрасывание -> анчутка кидает угли -> подписи добычи только с Alt и по Z ->
котомка: тултип, надеть щелчком и перетаскиванием (характеристики меняются), снять, выбросить ->
смерть: −10% серебра и возвращение у крады -> звуки -> чистая консоль. Скриншоты 1920x1080:
screenshot_iter2_gameplay.png (с мини-картой) и screenshot_iter2_inventory.png (котомка с тултипом).
Код выхода 1, если что-то не так.
"""
import argparse
import asyncio, json, os, sys
from checks_m1b import run_m1b
from checks_m1c import run_m1c
from checks_v18 import run_balance18
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SHOT_GAME = os.path.join(ROOT, 'screenshot_iter2_gameplay.png')
SHOT_INV = os.path.join(ROOT, 'screenshot_iter2_inventory.png')
SHOT_SKILLS = os.path.join(ROOT, 'screenshot_iter2_skills.png')

FREEZE = '(() => { for (const e of __game.enemies) { e.stagger = 1e9; e.moving = false; e.path = null; } })()'
UNFREEZE = '(() => { for (const e of __game.enemies) e.stagger = 0; })()'
# стаи в 9 тайлах от героя временно убираются (их спрайты под курсором превращали щелчок в атаку), BACK возвращает
AWAY = '(() => { const g = __game, h = g.hero; const far = g.enemies.filter(e => e.pack >= 0 && Math.hypot(e.x - h.x, e.y - h.y) < 9); window.__away = far; g.enemies = g.enemies.filter(e => !far.includes(e)); return far.length; })()'
BACK = '(() => { const g = __game; g.enemies.push(...(window.__away || [])); window.__away = null; })()'
TELEPORT = '''(([x, y]) => { const h = __game.hero; h.x = x; h.y = y; h.path = null; h.cmd = null; h.action = null; h.moving = false; h.kb = null; h.dashing = null; __game.rmbBuf = null; __game.dashBuf = null; __game.updateCamera(); })'''


async def main(a):
    results, errors = [], []

    def check(name, ok, info=''):
        results.append((name, bool(ok), info))
        print(('OK   ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''), flush=True)

    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path=a.chrome, args=['--autoplay-policy=no-user-gesture-required'])
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        if a.throttle and a.throttle > 1:
            cdp = await pg.context.new_cdp_session(pg)
            await cdp.send('Emulation.setCPUThrottlingRate', {'rate': a.throttle})
            print(f'ЦП замедлен в {a.throttle}×')
        pg.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        G = pg.evaluate

        async def client_of(x, y, lift=0):
            return await G(f'__game.clientOf({x}, {y}, {lift})')

        async def client_scr(sx, sy):
            return await G(f'__game.clientOfScreen({sx}, {sy})')

        async def wait(ms):
            # Пауза в «игровом» времени: при редких кадрах (нагрузка, --throttle) dt кадра ограничен 0,05 с и игра живёт
            # медленнее реального времени — ждём, пока она проживёт те же ms, и не меньше 2 кадров (ввод обработан).
            c0 = await G('[__game.clock || 0, __game.frames || 0]')
            await pg.wait_for_timeout(ms)
            for _ in range(250):
                c = await G('[__game.clock || 0, __game.frames || 0]')
                if c[0] - c0[0] >= ms / 1000 * 0.95 and c[1] - c0[1] >= 2:
                    break
                await pg.wait_for_timeout(20)

        await pg.goto(a.url)
        await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=15000)
        await pg.mouse.move(960, 540)
        await pg.mouse.click(960, 300)              # жест пользователя: разблокирует WebAudio (и шаг героя)
        await wait(200)
        # веха M1b: Мара Пепельная со свитой бродит по Залесью сверх 28 врагов зоны — для проверок M0/M1a её группу убираем
        # (её проверяют отдельно в разделе M1b на свежей загрузке)
        if a.balance_v18:                 # полный замер §12.3 GDD v1.8 (по N боёв на сценарий) → tools/balance_m1c.json
            await run_balance18(pg, G, a.balance_v18)
            print('консоль:', 'чисто' if not errors else errors[:5])
            await br.close()
            return 0
        if a.only_m1b or a.only_m1c:      # быстрый прогон только раздела M1b / M1c (отладка проверок)
            if a.only_m1b:
                await run_m1b(pg, G, check, wait, client_of, client_scr, a)
            if a.only_m1c:
                await run_m1c(pg, G, check, wait, client_of, client_scr, a)
            check('консоль без ошибок и предупреждений', not errors, errors[:5])
            await br.close()
            bad = [r for r in results if not r[1]]
            print(f'\n{len(results) - len(bad)}/{len(results)} проверок пройдено')
            return 1 if bad else 0
        await G('(() => { const g = __game; window.__maraGrp = g.enemies.filter(e => e.special); g.enemies = g.enemies.filter(e => !e.special); })()')

        # --- 1. баланс из JSON по GDD v1.2
        s = await G('''(() => { const g = __game, h = g.hero, d = g.dbg;
          return { cfg: Object.keys(d.CFG).sort(), hp: h.maxHp, yar: h.maxYar, regen: +h.yarRegen.toFixed(3), aps: h.attacksPerSec,
            xp: [1,2,3,10].map(d.xpToNext), up1: d.enemyStats('upyr', 1), an1: d.enemyStats('anchutka', 1), skill: [h.skillCost, h.skillRank],
            kit: Object.values(h.equip).filter(Boolean).map(i => i.name), belt: h.belt.map(b => b ? b.kind + 'x' + b.count : '-') }; })()''')
        check('конфиги data/*.json (+ uniques, ru, quests) и data/zones/*.json загружены', s['cfg'] == sorted(['stats', 'skills', 'monsters', 'bosses', 'items_base', 'affixes', 'droptables', 'uniques', 'ru', 'quests', 'zones']), s['cfg'])
        check('герой 1 ур.: 70 жизни / 40 Яри, Ярь +1,5%/с', s['hp'] == 70 and s['yar'] == 40 and abs(s['regen'] - 0.6) < 1e-6, (s['hp'], s['yar'], s['regen']))
        check('скорость атаки скрамасакса 1,4 удара/с', abs(s['aps'] - 1.4) < 1e-6, s['aps'])
        check('кривая опыта 100·L^1,75', s['xp'] == [100, 340, 680, 5620], s['xp'])
        u, an = s['up1'], s['an1']
        check('упырь mlvl1: 22 HP, 2–5 (урон ×1,1 по GDD v1.4), 10 опыта; анчутка: 13 HP, 1–3, 5 опыта',
              (u['hp'], u['dmgMin'], u['dmgMax'], u['xp']) == (22, 2, 5, 10) and (an['hp'], an['dmgMin'], an['dmgMax'], an['xp']) == (13, 1, 3, 5), (u, an))
        check('«Огненный змей» стоит 5 Яри на ранге 1', s['skill'] == [5, 1], s['skill'])
        hc = await G('''(() => { const g = __game, h = g.hero, d = g.dbg, u2 = d.enemyStats('upyr', 2), u1 = d.enemyStats('upyr', 1);
            return { heroVsM2: +d.hitChance(h.ar, u2.dfn, 1, 2).toFixed(3), upyrM2VsHero: +d.hitChance(u2.ar, h.def, 2, 1).toFixed(3),
              equal: [+d.hitChance(h.ar, u1.dfn, 1, 1).toFixed(3), +(2 * h.ar / (h.ar + u1.dfn) * 0.5).toFixed(3)], ar: h.ar, def: h.def, u2: [u2.ar, u2.dfn] }; })()''')
        f = lambda ar, df, la, ld: min(0.95, max(0.05, 2 * ar / (ar + df) * (la + 5) / (la + ld + 10)))
        check('шанс попадания (GDD v1.5): множитель (L_A+5)/(L_A+L_D+10) для обеих сторон; герой 1 ур. по mlvl 2 ≈ 77%; при равных уровнях как прежде',
              abs(hc['heroVsM2'] - 0.77) <= 0.03 and abs(hc['upyrM2VsHero'] - f(hc['u2'][0], hc['def'], 2, 1)) < 0.002 and hc['equal'][0] == min(0.95, hc['equal'][1]), hc)
        hc6 = await G('''(() => { const g = __game, h = g.hero, d = g.dbg, u1 = d.enemyStats('upyr', 1), u2 = d.enemyStats('upyr', 2), p = (v) => Math.round(v * 100);
            return { def: h.def, armor: h.armor, heroL1vsM2: p(d.hitChance(h.ar, u2.dfn, 1, 2)), upyrM2vsL1: p(d.hitChance(u2.ar, h.def, 2, 1)),
              upyrM1vsL2: p(d.hitChance(u1.ar, h.def, 1, 2)), heroL1vsM1: p(d.hitChance(h.ar, u1.dfn, 1, 1)) }; })()''')
        check('GDD v1.6 §9.3: стартовая броня 5/4/9 = 18, DEF 1 ур. = 23; попадание 78 / 57 / 41 / 88%',
              hc6['armor'] == 18 and hc6['def'] == 23 and [hc6['heroL1vsM2'], hc6['upyrM2vsL1'], hc6['upyrM1vsL2'], hc6['heroL1vsM1']] == [78, 57, 41, 88], hc6)
        z = await G('''(() => { const g = __game, z = g.zone, m = g.map, n = g.enemies.length, k = m.krada, c = m.churStone;
            const m1 = g.enemies.filter(e => e.mlvl === 1).length, pk = m.packs.map(p => ({ dk: +Math.hypot(p.x - k.x, p.y - k.y).toFixed(1), dc: c ? +Math.hypot(p.x - c.x, p.y - c.y).toFixed(1) : 99, n: p.kinds.length,
              u: p.kinds.filter(x => x === 'upyr').length, a: p.kinds.filter(x => x === 'anchutka').length, mlvl: p.mlvl }));
            const near = pk.slice().sort((a, b) => a.dk - b.dk)[0];
            return { n, m1: +(m1 / n).toFixed(2), pk, near, safe: z.safeZones.map(s => s.at + ':' + s.radius), well: !!m.props.find(p => p.type === 'well'), stone: !!c }; })()''')
        sizesOk = all((p['mlvl'] == 1 and ((p['a'] == 0 and 3 <= p['u'] <= 4) or (p['u'] == 0 and 4 <= p['a'] <= 5))) or
                      (p['mlvl'] == 2 and ((p['a'] == 0 and p['u'] == 3) or (p['u'] == 0 and p['a'] == 3) or (p['u'] <= 3 and p['a'] <= 1))) for p in z['pk'])
        check('Залесье (GDD v1.7): 28 врагов — 18 mlvl 1 + 10 mlvl 2, анчутки mlvl 2 по 3, смешанная ≤ 3 упыря + 1 анчутка, первая встреча — 3 упыря mlvl 1',
              z['n'] == 28 and z['m1'] == round(18 / 28, 2) and sizesOk and (z['near']['u'], z['near']['a'], z['near']['mlvl']) == (3, 0, 1), z)
        check('тихие круги: крада 10, Чуров камень у колодца 6; центры стай ≥ packMinDist = r+2 (12 / 8); колодец на карте',
              z['safe'] == ['krada:10', 'churStone:6'] and all(p['dk'] >= 12 and p['dc'] >= 8 for p in z['pk']) and z['well'] and z['stone'], z['safe'])
        check('стартовый комплект GDD v1.4 (скрамасакс, малый щит, клёпаный шелом, короткая кольчуга) и пояс', sorted(s['kit']) == sorted(['Скрамасакс', 'Малый щит', 'Клёпаный шелом', 'Короткая кольчуга']) and s['belt'][:3] == ['life1x2', 'life1x1', 'yar1x2'], (s['kit'], s['belt']))

        # --- 2. полутайловая коллизия: тонкая стена в западной половине тайла (30, 24)
        await G(FREEZE)
        s = await G('''(() => { const g = __game, m = g.map, d = g.dbg;
          return { tileBlocked: m.isBlocked(30, 24), westHalf: m.blockedAt(30.25, 24.5), eastFree: d.circleFree(m, 30.85, 24.5, 0.3), deep: d.circleFree(m, 30.4, 24.5, 0.3) }; })()''')
        check('тайл (30,24) занят стеной лишь наполовину: центр героя проходит в 30,85', s['tileBlocked'] and s['westHalf'] and s['eastFree'] and not s['deep'], s)
        await G(TELEPORT + '([32.4, 24.5])')
        tx, ty = await client_of(30.6, 24.5)
        await pg.mouse.click(tx, ty)
        await pg.mouse.move(960, 200)                         # мышь ушла сразу после щелчка: щелчок всё равно по точке нажатия
        for _ in range(40):                                   # ждём кадра, который примет щелчок
            if await G('!!__game.hero.cmd || __game.hero.moving'):
                break
            await wait(25)
        # дальше — фиксированный шаг 1/60 с, без зависимости от частоты кадров headless-браузера
        hx = await G('(() => { const g = __game, h = g.hero; g.simulate(4, () => !h.moving && !h.cmd); return h.x; })()')
        check('герой дошёл до стены и стоит в восточной половине её тайла', 30.75 <= hx < 31.0, round(hx, 3))

        # --- 3. нечисть преграждает путь
        info = await G('''(() => { const g = __game, h = g.hero; const e = g.enemies.find(e => !e.dead && e.kind === 'upyr');
          return { id: e.id, x: e.x, y: e.y }; })()''')
        await G(f'''(() => {{ const g = __game, e = g.enemies.find(e => e.id === {info['id']}); e.x = 25.5; e.y = 26.5; e.homeX = 25.5; e.homeY = 26.5; e.stagger = 1e9; }})()''')
        await G(TELEPORT + '([23.6, 26.5])')
        await G('''(() => { const g = __game; g.hero.moveTo(g.map, 27.6, 26.5); g._minD = 9; g._track = setInterval(() => {
             const e = g.enemies.find(e => e.id === %d); g._minD = Math.min(g._minD, Math.hypot(e.x - g.hero.x, e.y - g.hero.y)); }, 16); })()''' % info['id'])
        await wait(1600)
        s = await G('(() => { clearInterval(__game._track); return { minD: __game._minD, x: __game.hero.x, y: __game.hero.y }; })()')
        check('герой обходит упыря, а не проходит сквозь него', s['minD'] >= 0.6 and s['x'] > 27.0, s)
        # тело не даёт протолкнуться напрямую
        await G(TELEPORT + '([24.5, 26.5])')
        s = await G('''(() => { const g = __game, h = g.hero; const mv = []; for (let i = 0; i < 30; i++) mv.push(h.stepToward ? 0 : 0);
            const x0 = h.x; for (let i = 0; i < 30; i++) h.stepToward(g.map, 27, 26.5, h.speed, 1 / 60);
            const e = g.enemies.find(e => e.id === %d); return { x: h.x, d: Math.hypot(e.x - h.x, e.y - h.y), bumped: !!h.bumped }; })()''' % info['id'])
        check('прямой шаг в упыря упирается в его тело', s['d'] >= 0.64, s)
        await G(f'''(() => {{ const e = __game.enemies.find(e => e.id === {info['id']}); e.x = {info['x']}; e.y = {info['y']}; e.homeX = e.x; e.homeY = e.y; }})()''')

        # --- 4. взрыв не бьёт через стену; хит-стоп и отбрасывание
        s = await G('''(() => { const g = __game, h = g.hero; const e = g.enemies.find(e => !e.dead && e.kind === 'upyr');
            e.x = 30.95; e.y = 24.5; e.stagger = 1e9; h.x = 27.5; h.y = 24.5; h.yar = h.maxYar; h.action = null; h.cmd = null;
            const hp0 = e.hp; g.combat.lastBlast = null; h.tryCast(g, e.x, e.y); return { id: e.id, hp0 }; })()''')
        for _ in range(40):
            if await G('!!__game.combat.lastBlast'):
                break
            await wait(100)
        await wait(100)
        r = await G('''((id) => { const g = __game, e = g.enemies.find(e => e.id === id), b = g.combat.lastBlast;
            return { hp: e.hp, blast: b && { x: +b.x.toFixed(2), hit: b.hit, blocked: b.blocked } }; })''', s['id'])
        check('взрыв у стены не задел упыря за ней (прямая видимость от центра)',
              r['blast'] and s['id'] in r['blast']['blocked'] and r['hp'] == s['hp0'] and r['blast']['x'] < 30.0, r)
        s2 = await G('''((id) => { const g = __game, h = g.hero, e = g.enemies.find(e => e.id === id);
            e.x = 29.0; e.y = 24.5; h.x = 26.0; h.y = 24.5; h.yar = h.maxYar; h.action = null; const hp0 = e.hp; g.combat.lastBlast = null; h.tryCast(g, e.x, e.y); return hp0; })''', s['id'])
        for _ in range(40):
            if await G('!!__game.combat.lastBlast'):
                break
            await wait(100)
        await wait(100)
        r = await G('((id) => { const g = __game, e = g.enemies.find(e => e.id === id); return { hp: e.hp, dead: e.dead, hit: g.combat.lastBlast.hit }; })', s['id'])
        check('тот же взрыв по открытой цели наносит урон', (r['hp'] < s2 or r['dead']) and s['id'] in r['hit'], r)
        s = await G('''((id) => { const g = __game, h = g.hero, e = g.enemies.find(e => e.id === id && !e.dead) || g.enemies.find(e => !e.dead && e.kind === 'upyr');
            e.stagger = 0; e.x = h.x + 1.0; e.y = h.y; const r0 = Math.random; Math.random = () => 0.01;
            const hs0 = g.counters.hitStop; g.combat.heroMelee(h, e); Math.random = r0;
            return { kb: !!e.kb || e.dead, hitStop: g.counters.hitStop - hs0, hst: g.hitStopT, id: e.id }; })''', s['id'])
        check('удар даёт хит-стоп 50 мс и отбрасывание', s['kb'] and s['hitStop'] == 1 and s['hst'] > 0.04, s)
        await G(UNFREEZE)

        # --- 5. анчутка кидает угли
        cp = await G('''(() => { const g = __game; for (let r = 0; r < 4; r += 0.5) for (let a = 0; a < 12; a++) { const x = 36.5 + Math.cos(a / 12 * 6.283) * r, y = 30.5 + Math.sin(a / 12 * 6.283) * r;
            if (g.dbg.circleFree(g.map, x, y, 0.4) && g.map.isReachableAt(x, y) && !g.safeAt(x, y)) return [x, y]; } return [36.5, 30.5]; })()''')
        await G('(() => { const h = __game.hero; h.hp = h.maxHp; })()')
        await G(TELEPORT + '(' + json.dumps(cp) + ')')
        coal = False
        for _ in range(40):
            await wait(150)
            if await G('__game.combat.projectiles.some(p => p.hostile && p.coal) || (__game.audio.count.throw || 0) > 0'):
                coal = True
                break
        check('анчутка держит дистанцию и кидает угли', coal, await G('''(() => { const g = __game, h = g.hero; return { thr: g.audio.count.throw || 0, h: [h.x, h.y, h.hp, h.invuln, h.dead], st: g.state, p: g.paused,
            an: g.enemies.filter(e => e.kind === 'anchutka' && Math.hypot(e.x - h.x, e.y - h.y) < 9).map(e => e.state + ':' + e.stagger) }; })()'''))

        # --- 6. сцена для скриншота: бой у стаи анчуток, мини-карта, подписи по Alt
        await G('(() => { const h = __game.hero; h.hp = h.maxHp; h.invuln = 0; })()')
        for _ in range(40):
            st = await G('''(() => { const g = __game, h = g.hero; let b = null, bd = 1e9; for (const e of g.enemies) { if (e.dead) continue; const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; b = e; } }
                return { hp: h.hp, max: h.maxHp, e: b && { x: b.x, y: b.y, d: bd, h: b.def.height }, loot: g.loot.items.length }; })()''')
            if st['hp'] < st['max'] * 0.5:
                await G('(() => { const h = __game.hero; h.hp = h.maxHp; })()')
            if not st['e'] or st['e']['d'] > 7 or st['loot'] >= 3:
                break
            ex, ey = await client_of(st['e']['x'], st['e']['y'], st['e']['h'] / 2)
            await pg.mouse.move(ex, ey)
            if st['e']['d'] > 2.5:
                await pg.mouse.down(button='right'); await wait(60); await pg.mouse.up(button='right')
            else:
                await pg.mouse.down(); await wait(250); await pg.mouse.up()
            await wait(150)
        if await G('__game.loot.items.length') < 2:
            await G('(() => { __game.dropRandom(2); __game.dropRandom(3); __game.loot.spawnSilver(__game.hero.x - 1, __game.hero.y + 0.5, 11); })()')
        await wait(500)
        # отойти от кучки добычи, чтобы подписи не закрывали героя на скриншоте
        await G('''(() => { const g = __game, h = g.hero, it = g.loot.items; if (!it.length) return;
            const cx = it.reduce((a, i) => a + i.x, 0) / it.length, cy = it.reduce((a, i) => a + i.y, 0) / it.length;
            for (const [dx, dy] of [[1.6, -1.6], [-1.6, 1.6], [2.2, 0], [0, 2.2], [-2.2, 0], [0, -2.2]]) {
              const x = cx + dx, y = cy + dy; if (g.dbg.circleFree(g.map, x, y, 0.35) && g.map.isReachableAt(x, y)) { h.moveTo(g.map, x, y); return; } } })()''')
        await wait(900)
        await pg.mouse.move(*(await client_scr(250, 120)))
        await wait(100)
        n0 = await G('__game.labelRects.length')
        await pg.keyboard.down('Alt'); await wait(120)
        n1 = await G('__game.labelRects.length')
        check('подписи добычи видны только с зажатым Alt', n0 == 0 and n1 >= 1, (n0, n1))
        # скриншот: Alt зажат, мини-карта видна, рядом бой
        st = await G('__game.enemies.some(e => !e.dead && Math.hypot(e.x - __game.hero.x, e.y - __game.hero.y) < 6)')
        if st:
            e = await G('''(() => { const g = __game, h = g.hero; let b = null, bd = 1e9; for (const e of g.enemies) { if (e.dead) continue; const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; b = e; } } return { x: b.x, y: b.y, h: b.def.height }; })()''')
            ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
            await pg.mouse.move(ex, ey); await pg.mouse.down(button='right'); await wait(60); await pg.mouse.up(button='right'); await wait(260)
            await pg.mouse.move(ex, ey)
        mm = await G('__game.showMinimap && __game.topRightVisible')
        await pg.screenshot(path=SHOT_GAME)
        check('скриншот игры с мини-картой сохранён', mm and os.path.exists(SHOT_GAME), os.path.basename(SHOT_GAME))
        # подбор щелчком по подписи (Alt ещё зажат)
        lab = await G('(() => { const r = __game.labelRects.find(r => r.item.kind !== "silver") || __game.labelRects[0]; return r && { x: r.x + r.w / 2, y: r.y + r.h / 2, kind: r.item.kind }; })()')
        p0 = await G('(__game.audio.count.pickup || 0) + (__game.audio.count.silver || 0)')
        if lab:
            await pg.mouse.click(*(await client_scr(lab['x'], lab['y'])))
            await wait(1500)
        p1 = await G('(__game.audio.count.pickup || 0) + (__game.audio.count.silver || 0)')
        check('щелчок по подписи поднимает добычу', lab and p1 > p0, (lab, p0, p1))
        await pg.keyboard.up('Alt'); await wait(120)
        await G('(() => { const h = __game.hero; h.cmd = null; h.path = null; h.moving = false; __game.loot.spawnSilver(h.x + 2.2, h.y - 1.0, 7); })()'); await wait(80)
        n2 = await G('__game.labelRects.length')
        await pg.keyboard.press('KeyZ')
        n3 = 0
        for _ in range(30):                                   # ждём кадр с подписями (не фиксированную паузу — кадры бывают редкими)
            await wait(50)
            n3 = await G('__game.labelsAlways ? __game.labelRects.length : 0')
            if n3:
                break
        await pg.keyboard.press('KeyZ')
        for _ in range(30):
            await wait(50)
            if not await G('__game.labelsAlways'):
                break
        check('Z включает подписи «всегда» и выключает обратно', n2 == 0 and n3 >= 1 and not await G('__game.labelsAlways'), (n2, n3))
        await pg.keyboard.press('Tab'); await wait(100)
        ov = await G('__game.mapOverlay')
        await pg.keyboard.press('Tab'); await wait(100)
        check('Tab открывает и закрывает большую карту', ov and not await G('__game.mapOverlay'))

        # --- 7. котомка и снаряжение
        await G(FREEZE)
        await G(TELEPORT + '([24.5, 20.5])')
        await G('(() => { const g = __game; g.hero.hp = g.hero.maxHp; g.give("axe_1", "magic", { affixes: [["P01", 30], ["S10", 10]] }); g.give("ring_1", "magic", { affixes: [["S01", 8]] }); g.give("sword_2", "rare", { affixes: [["P01", 25], ["S02", 3]] }); g.give("potion:life1"); })()')
        await pg.keyboard.press('KeyI'); await wait(200)
        L = await G('__game.dbg.UI_ATLAS.inventory_layout')
        ents = await G('__game.hero.inv.entries.map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h, base: e.item.base, kind: e.item.kind, uid: e.item.uid, rar: e.item.rarity }))')

        def cell_center(e):
            return L['gx'] + (e['c'] + e['w'] / 2) * L['cell'], L['gy'] + (e['r'] + e['h'] / 2) * L['cell']

        def slot_center(name):
            x, y, w, h = L['slots'][name]
            return x + w / 2, y + h / 2

        # выданные тестом вещи — последние такого основания (раньше в котомку мог попасть обычный топор с поля)
        axe = [e for e in ents if e['base'] == 'axe_1' and e['rar'] == 'magic'][-1]
        sword = [e for e in ents if e['base'] == 'sword_2' and e['rar'] == 'rare'][-1]
        ring = [e for e in ents if e['base'] == 'ring_1' and e['rar'] == 'magic'][-1]
        # тултип
        await pg.mouse.move(*(await client_scr(*cell_center(axe)))); await wait(150)
        tip = await G('__game.ui.lastTip && { name: __game.ui.lastTip.item.name, w: __game.ui.lastTip.w, h: __game.ui.lastTip.h }')
        check('тултип предмета показывается при наведении', tip and tip['w'] > 60, tip)
        # щелчок: взять топор и щёлкнуть по деснице
        before = await G('({ min: __game.hero.dmgMin, max: __game.hero.dmgMax, aps: __game.hero.attacksPerSec })')
        await pg.mouse.click(*(await client_scr(*cell_center(axe)))); await wait(100)
        held = await G('__game.ui.hand && __game.ui.hand.base')
        await pg.mouse.click(*(await client_scr(*slot_center('rhand')))); await wait(100)
        after = await G('({ min: __game.hero.dmgMin, max: __game.hero.dmgMax, aps: __game.hero.attacksPerSec, hand: __game.ui.hand && __game.ui.hand.base, r: __game.hero.equip.rhand.base })')
        check('щелчком надет топор: урон и скорость атаки пересчитаны', held == 'axe_1' and after['r'] == 'axe_1' and after['max'] != before['max'] and abs(after['aps'] - 1.21) < 0.01 and after['hand'] == 'sword_1', (before, after))
        # старый скрамасакс — обратно в котомку (в свободную клетку)
        await pg.mouse.click(*(await client_scr(L['gx'] + 8 * L['cell'] + 12, L['gy'] + 1 * L['cell'] + 12))); await wait(100)
        check('снятый предмет положен в сетку', not await G('__game.ui.hand') and await G('__game.hero.inv.items.some(i => i.base === "sword_1")'))
        # требование по уровню
        await pg.mouse.click(*(await client_scr(*cell_center(sword)))); await wait(100)
        await pg.mouse.click(*(await client_scr(*slot_center('rhand')))); await wait(100)
        s = await G('({ r: __game.hero.equip.rhand.base, hand: __game.ui.hand && __game.ui.hand.base, err: __game.audio.count.error || 0 })')
        check('меч 6-го уровня не надевается на 1-м (ошибка, предмет остаётся в руке)', s['r'] == 'axe_1' and s['hand'] == 'sword_2' and s['err'] >= 1, s)
        await pg.mouse.click(*(await client_scr(*cell_center(sword)))); await wait(100)
        # перетаскивание перстня в слот: +8 жизни
        hp0 = await G('__game.hero.maxHp')
        await pg.mouse.move(*(await client_scr(*cell_center(ring))))
        await wait(80); await pg.mouse.down(); await wait(120)
        sx, sy = slot_center('ring1')
        for k in range(1, 6):
            cx, cy = cell_center(ring)
            await pg.mouse.move(*(await client_scr(cx + (sx - cx) * k / 5, cy + (sy - cy) * k / 5))); await wait(40)
        await wait(60); await pg.mouse.up(); await wait(120)
        hp1 = await G('__game.hero.maxHp')
        check('перетаскиванием надет перстень «живота»: +8 к жизни', hp1 == hp0 + 8 and await G('__game.hero.equip.ring1 && __game.hero.equip.ring1.base') == 'ring_1', (hp0, hp1))
        # скриншот с тултипом на надетом или новом предмете (меч — со сравнением и требованием)
        sw = await G('__game.hero.inv.entries.filter(e => e.item.base === "sword_2").map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h }))[0]')
        await pg.keyboard.press('KeyC'); await wait(100)
        await pg.mouse.move(*(await client_scr(*cell_center(sw)))); await wait(200)
        tip = await G('__game.ui.lastTip && __game.ui.lastTip.item.name')
        await pg.screenshot(path=SHOT_INV)
        check('скриншот котомки с тултипом сохранён', tip and os.path.exists(SHOT_INV), tip)
        await pg.keyboard.press('KeyC'); await wait(100)
        # ПКМ по перстню на кукле — снять в котомку
        await pg.mouse.click(*(await client_scr(*slot_center('ring1'))), button='right'); await wait(100)
        check('ПКМ по слоту снимает предмет в котомку', not await G('__game.hero.equip.ring1') and await G('__game.hero.maxHp') == hp0)
        # выбросить: взять предмет и щёлкнуть по миру слева
        n0 = await G('__game.loot.items.length')
        sw = await G('__game.hero.inv.entries.filter(e => e.item.base === "sword_2").map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h }))[0]')
        await pg.mouse.click(*(await client_scr(*cell_center(sw)))); await wait(100)
        await pg.mouse.click(*(await client_scr(120, 150))); await wait(100)
        check('предмет из котомки выброшен на землю', await G('__game.loot.items.length') == n0 + 1 and not await G('__game.hero.inv.items.some(i => i.base === "sword_2")'))
        await pg.keyboard.press('KeyI'); await wait(100)
        await G(UNFREEZE)

        # --- 8. смерть и возвращение у крады
        await G('(() => { const g = __game; g.hero.silver = 101; g.hero.invuln = 0; g.hero.takeDamage(9999, g, "fire"); })()')
        await wait(300)
        s = await G('({ st: __game.state, silver: __game.hero.silver, lost: __game.deathInfo.lost })')
        check('смерть: −10% серебра (вверх)', s['st'] == 'dead' and s['silver'] == 90 and s['lost'] == 11, s)
        await wait(1700)
        # Enter и Пробел на 2-й секунде гибели — кадр с этими клавишами прогоняем сами (без зависимости от частоты кадров)
        early = await G('''(() => { const g = __game, inp = g.input; g.deathT = Math.min(g.deathT, 2.0); inp.keysPressed.add('Enter'); inp.keysPressed.add('Space');
            g.update(1 / 60); inp.endFrame(); return { st: g.state, t: +g.deathT.toFixed(2) }; })()''')
        check('GDD v1.7: на экране гибели Пробел / Enter не срабатывают раньше 2,5 с', early['st'] == 'dead' and early['t'] < 2.5, early)
        await wait(800)
        await pg.keyboard.press('Enter'); await wait(200)
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; return { st: g.state, d: Math.hypot(h.x - k.x, h.y - k.y), hp: h.hp, max: h.maxHp, yar: h.yar, my: h.maxYar, inv: h.invuln, lvl: h.level }; })()''')
        check('возвращение у крады: полные жизнь и Ярь, неуязвимость, игра продолжается', s['st'] == 'play' and s['d'] < 5 and s['hp'] == s['max'] and s['yar'] == s['my'] and s['inv'] > 1, s)

        # --- 9. уровень и звуки
        await G('__game.hero.gainXp(100, __game)')
        c = await G('__game.audio.count')
        need = ['skill', 'levelup', 'death', 'respawn', 'equip', 'explode', 'throw']
        check('звуки-заглушки срабатывают: удар (hit/crit/bash), ' + ', '.join(need), all(c.get(k, 0) > 0 for k in need) and (c.get('hit', 0) + c.get('crit', 0) + c.get('bash', 0)) > 0, c)
        await pg.keyboard.press('KeyN'); await wait(50)
        m1 = await G('__game.audio.muted')
        await pg.keyboard.press('KeyN'); await wait(50)
        check('N выключает и включает звук', m1 and not await G('__game.audio.muted'))
        await wait(300)

        # --- 10. навыки, панель F1–F6, 8 направлений, правила дизайнера и QA (итерация 2, п. 3)
        await G(FREEZE)
        A = await G('''(() => { const g = __game, k = g.map.krada, ok = (x, y) => g.dbg.circleFree(g.map, x, y, 0.4) && g.map.isReachableAt(x, y); let best = null;
          for (let r = 12; r < 26; r++) for (let a = 0; a < 32; a++) { const x = k.x + Math.cos(a / 32 * 6.283) * r, y = k.y + Math.sin(a / 32 * 6.283) * r;
            if (g.safeAt(x, y, 5) || x < 4 || y < 4 || x > 44 || y > 44) continue;   // основная часть 48×48; тупик Мары (x≥48) не берём под площадку навыков
            let good = true; for (let dx = -3; dx <= 3 && good; dx++) for (let dy = -3; dy <= 3; dy++) if (!ok(x + dx, y + dy)) { good = false; break; }
            if (!good) continue;
            const ed = Math.min(...g.enemies.filter(e => !e.dead).map(e => Math.hypot(e.x - x, e.y - y)), 99);
            if (!best || ed > best[2]) best = [x, y, ed]; }
          return best ? [best[0], best[1]] : null; })()''')     # открытая площадка вне тихих кругов (стаи вокруг заморожены)
        A = [int(A[0] * 2) / 2 + 0.25, int(A[1] * 2) / 2 + 0.25]     # центр полутайла: путь начинается ровно от героя
        HOME = TELEPORT + f'([{A[0]}, {A[1]}])'
        await G('(() => { const g = __game, h = g.hero; h.invuln = 0; h.hp = h.maxHp; let n = 0; while (h.level < 6 && n++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g); })()')

        # 10.1 направление взгляда героя — 8 сторон по движению (настоящие щелчки мыши)
        got, kinds = {}, {}
        await G(HOME); await G(AWAY)
        # цели — центры полутайлов на чистых направлениях: по осям мира (на экране 26,6°) и по диагоналям мира (экранные
        # вертикаль/горизонталь); раньше щелчок по экранному вектору 2:1 попадал в соседний полутайл и уводил угол к границе октантов
        for name, (dx, dy), want in [('вниз', (2, 2), 0), ('влево', (-2, 2), 2), ('вверх', (-2, -2), 4), ('вправо', (2, -2), 6),
                                     ('вниз-вправо', (3, 0), 7), ('вверх-влево', (-3, 0), 3), ('вниз-влево', (0, 3), 1), ('вверх-вправо', (0, -3), 5)]:
            await G(HOME)
            # добыча с прошлых проверок под курсором превращала щелчок в «подобрать» (путь к предмету) — убираем её с площадки
            await G('''(([x, y]) => { const g = __game; g.loot.items = g.loot.items.filter(it => Math.hypot(it.x - x, it.y - y) > 6); })''', A)
            await wait(60)
            cx, cy = await client_of(A[0] + dx, A[1] + dy)
            # щелчок — настоящие DOM-события мыши, но нажатие и отпускание в одной задаче: при медленных кадрах (--throttle)
            # между ними не проходит кадров с «удержанием», когда цель под курсором уезжает вместе с камерой
            await G('''(([x, y]) => { const c = document.getElementById('game'), o = { clientX: x, clientY: y, button: 0, buttons: 1, bubbles: true };
                c.dispatchEvent(new MouseEvent('mousemove', o)); c.dispatchEvent(new MouseEvent('mousedown', o)); window.dispatchEvent(new MouseEvent('mouseup', { ...o, buttons: 0 })); })''', [cx, cy])
            for _ in range(40):                               # ждём кадр, который примет щелчок; дальше — фиксированный шаг
                if await G('!!__game.hero.cmd || __game.hero.moving'):
                    break
                await wait(25)
            # направление за весь отрезок пути (мода по кадрам): первый шаг A* по полутайлам бывает «вбок»
            kinds[name] = await G('(() => { const g = __game, h = g.hero; return [g.leftMode, h.cmd ? h.cmd.type : null, g.hoverEnemy ? g.hoverEnemy.kind : null, !!(g.hoverLabel || g.hoverGround), g.hoverObj ? g.hoverObj.type : null]; })()')
            got[name] = (await G('''(() => { const g = __game, h = g.hero, n = {}; for (let i = 0; i < 48 && (h.moving || h.cmd); i++) { g.simulate(1 / 60); if (h.moving) n[h.dir] = (n[h.dir] || 0) + 1; }
                return +Object.entries(n).sort((a, b) => b[1] - a[1])[0][0]; })()'''), want)
        await G(HOME); await G(BACK)
        check('герой смотрит туда, куда идёт (8 направлений: 0 — к камере, по часовой через «влево»)', all(a == b for a, b in got.values()),
              got if all(a == b for a, b in got.values()) else {'got': got, 'click': kinds})
        s = await G('''(async () => { const S = await import('/src/render/sprites.js'), g = __game, out = [];
            for (let d = 0; d < 8; d++) { const c = document.createElement('canvas'); c.width = 64; c.height = 72; const x = c.getContext('2d', { willReadFrequently: true });
              S.drawHero(x, 32, 64, g.hero, d, 0.5); out.push(Array.from(x.getImageData(0, 0, 64, 72).data).reduce((a, v, i) => (a * 31 + v * (i % 7 + 1)) % 1000000007, 7)); }
            const e = g.enemies.find(e => e.kind === 'upyr'), en = [];
            for (let d = 0; d < 8; d++) { const c = document.createElement('canvas'); c.width = 64; c.height = 72; const x = c.getContext('2d', { willReadFrequently: true });
              S.drawEnemy(x, 32, 64, e, d, 0.5, false); en.push(Array.from(x.getImageData(0, 0, 64, 72).data).reduce((a, v, i) => (a * 31 + v * (i % 7 + 1)) % 1000000007, 7)); }
            return { hero: new Set(out).size, upyr: new Set(en).size }; })()''')
        check('спрайты героя и упыря принимают dir 0–7: 8 разных ракурсов', s['hero'] == 8 and s['upyr'] == 8, s)
        s = await G(f'''(() => {{ const g = __game, h = g.hero; const e = g.spawnTest('upyr', h.x + 3.2, h.y, 1); e.aggro(g, false); e.stagger = 0; return e.id; }})()''')
        await wait(450)
        r = await G('''((id) => { const g = __game, h = g.hero, e = g.enemies.find(e => e.id === id); const want = g.dbg.dirOf(h.x - e.x, h.y - e.y);
            const d = (e.dir - want + 8) % 8; const res = { dir: e.dir, want, ok: d <= 1 || d === 7 }; g.enemies = g.enemies.filter(o => o !== e); return res; })''', s)
        check('враг разворачивается к герою (e.dir по направлению шага)', r['ok'], r)

        # 10.2 окно «Навыки» (T): очки, ранги, требования; F1–F6 над навыком — назначить
        await pg.keyboard.press('KeyT'); await wait(150)
        SL = await G('__game.dbg.UI_ATLAS.skills_layout')
        s0 = await G('({ open: __game.ui.skillsOpen, free: __game.hero.skillPoints, lvl: __game.hero.level, sk: Object.assign({}, __game.hero.skills) })')
        async def plus(id):
            x, y, w, h = SL['plus'][id]
            await pg.mouse.click(*(await client_scr(x + w / 2, y + h / 2))); await wait(90)
        async def hover(id):
            x, y, w, h = SL['slots'][id]
            await pg.mouse.move(*(await client_scr(x + w / 2, y + h / 2))); await wait(90)
        for sid in ('sshibka', 'morozko', 'chur'):
            await plus(sid)
        err0 = await G('__game.audio.count.error || 0')
        await plus('skok')
        s1 = await G('({ free: __game.hero.skillPoints, sk: Object.assign({}, __game.hero.skills), bar: __game.hero.bar.slice(), err: __game.audio.count.error || 0 })')
        check('T открывает «Навыки»; «+» покупает ранги за очки (Сшибка 1→2, Дыхание Морозко, Чур-оберег на 6-м ур.)',
              s0['open'] and s0['lvl'] == 6 and s1['sk'].get('sshibka') == 2 and s1['sk'].get('morozko') == 1 and s1['sk'].get('chur') == 1 and s1['free'] == s0['free'] - 3, (s0, s1))
        check('«Перунов скок» на 6-м уровне не учится (нужен 12-й): ошибка, ранг 0', not s1['sk'].get('skok') and s1['err'] > err0, s1)
        await hover('morozko'); await pg.keyboard.press('F5'); await wait(80)
        await hover('chur'); await pg.keyboard.press('F6'); await wait(80)
        b = await G('__game.hero.bar.slice()')
        check('F5/F6 над навыком в окне назначают его в ячейку (старая ячейка освобождается)', b[4] == 'morozko' and b[5] == 'chur' and b.count('morozko') == 1 and b.count('chur') == 1, b)
        await pg.keyboard.press('KeyT'); await wait(100)
        await pg.keyboard.press('F5'); await wait(60)
        r5 = await G('__game.hero.rmb')
        await pg.keyboard.press('F1'); await wait(60)
        r1 = await G('__game.hero.rmb')
        await pg.mouse.move(*(await client_of(A[0] + 2, A[1] - 2))); await pg.mouse.wheel(0, 120); await wait(80)
        rw = await G('__game.hero.rmb')
        check('F-клавиши (окно закрыто) ставят навык на ПКМ, колесо перебирает панель', r5 == 'morozko' and r1 == 'zmey' and rw != 'zmey', (r5, r1, rw))

        # 10.3 «Ратный» (+1 ко всем выученным навыкам «Ратного дела»), симметрично «Вещему»
        s = await G('''(() => { const g = __game, h = g.hero, d = g.dbg; const it = g.give('neck_1', 'magic', { affixes: [['P10a', 1]] });
            const b0 = [d.rankOf(h, 'sshibka'), d.rankOf(h, 'chur'), d.rankOf(h, 'stat'), d.rankOf(h, 'zmey')];
            h.putOn(it, 'neck'); h.inv.remove && h.inv.remove(it); const b1 = [d.rankOf(h, 'sshibka'), d.rankOf(h, 'chur'), d.rankOf(h, 'stat'), d.rankOf(h, 'zmey')];
            return { name: it.name, b0, b1 }; })()''')
        check('аффикс «Ратный»: +1 к рангу выученных навыков «Ратного дела», невыученные и «Ведовство» не трогает',
              s['b1'][0] == s['b0'][0] + 1 and s['b1'][1] == s['b0'][1] + 1 and s['b1'][2] == 0 and s['b1'][3] == s['b0'][3], s)

        # 10.4 применение навыков: Сшибка (отбрасывание), Морозко (замедление), Чур (бафф), КД блокирует повтор
        await G(HOME)
        # посторонние враги (например, уходящие к логову после удара из тихого круга) не должны стоять на линии удара/снаряда
        await G(AWAY)
        s = await G('''(() => { const g = __game, h = g.hero, d = g.dbg; const keepSk = { ...h.skills }, keepNeck = h.equip.neck; h.equip.neck = null; h.recalc();
            const bash = (rank, crit, kill) => { h.skills.sshibka = rank; h.recalc(); h.yar = h.maxYar; h.action = null; h.cmd = null; g.lastBash = null;
              const e = g.spawnTest('upyr', h.x + 0.95, h.y + 0.05, 1); e.stagger = 1e9; if (kill) e.hp = 1;
              const r0 = Math.random; Math.random = () => (crit ? 0.001 : Math.min(0.9, h.crit + 0.01));   // попадание всегда; крит — по желанию
              h.useSkill(g, 'sshibka', e.x, e.y, e); g.simulate(0.8, () => g.lastBash && g.lastBash.target === e); Math.random = r0; g.simulate(0.3);
              const out = +(Math.hypot(e.x - h.x, e.y - h.y) - 0.95).toFixed(2); g.enemies = g.enemies.filter(o => o !== e); return { moved: out, dead: e.dead, hp: [e.hp, e.maxHp] }; };
            const res = { dmgPct: [d.SKILLS.sshibka.dmgPct], r1crit: bash(1, true, false), r2kill: bash(2, false, true), r1hit: bash(1, false, false), r3crit: bash(3, true, false) };
            h.skills = keepSk; h.equip.neck = keepNeck; h.recalc(); return res; })()''')
        check('«Сшибка» v1.6: 175% +7%/ранг; отбрасывание 1 тайл только у добивающего (ранги 1–2), с 3-го ранга и у крита; обычный удар не отбрасывает',
              s['dmgPct'] == [[175, 7]] and s['r2kill']['dead'] and s['r2kill']['moved'] >= 0.8 and s['r1crit']['moved'] < 0.2 and s['r1hit']['moved'] < 0.2
              and s['r1hit']['hp'][0] < s['r1hit']['hp'][1] and s['r3crit']['moved'] >= 0.6, s)
        s = await G('''(() => { const g = __game, h = g.hero; h.yar = h.maxYar; const e = g.spawnTest('upyr', h.x + 3.5, h.y, 1); e.aggro(g, false);
            const r = h.useSkill(g, 'morozko', e.x, e.y, e); g.simulate(1.2, () => e.slowT > 0);
            const out = { r, slow: e.slowPct, t: +(e.slowT || 0).toFixed(2), spd: e.speed }; g.enemies = g.enemies.filter(o => o !== e); return out; })()''')
        check('«Дыхание Морозко»: попадание замедляет врага на 50%', s['r'] == 'ok' and s['slow'] == 50 and s['t'] > 1, s)
        s = await G('''(() => { const g = __game, h = g.hero; g.simulate(1.0); h.action = null; h.yar = h.maxYar; const e = g.spawnTest('upyr', h.x + 3.5, h.y, 1); e.elite = true; e.aggro(g, false);
            const r = h.useSkill(g, 'morozko', e.x, e.y, e); g.simulate(1.2, () => e.slowT > 0);
            const out = { r, slow: e.slowPct, range: g.dbg.SKILLS.morozko.range }; g.enemies = g.enemies.filter(o => o !== e); return out; })()''')
        check('GDD v1.6: «Морозко» дальность 12, по вожаку/боссу замедление вдвое слабее (25%)', s['r'] == 'ok' and s['slow'] == 25 and s['range'] == 12, s)
        await G(BACK)
        s = await G('''(() => { const g = __game, h = g.hero; g.simulate(1.0); h.action = null; h.yar = h.maxYar; const d0 = h.def; const r = h.useSkill(g, 'chur', h.x, h.y);
            g.simulate(0.7); return { r, d0, d1: h.def, buff: h.buffs.chur && +h.buffs.chur.t.toFixed(1) }; })()''')
        check('«Чур-оберег»: бафф +защита на 30 с', s['r'] == 'ok' and s['d1'] > s['d0'] and s['buff'] > 25, s)
        # уровень 12: «Перунов скок» с КД 3 с — настоящий ПКМ
        await G('(() => { const g = __game, h = g.hero; let n = 0; while (h.level < 12 && n++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g); h.learn("skok", g); h.yar = h.maxYar; })()')
        await G(HOME)
        bar = await G('__game.hero.bar.slice()')
        k = bar.index('skok')
        await pg.keyboard.press('F' + str(k + 1)); await wait(60)
        p0 = await G('[__game.hero.x, __game.hero.y]')
        # точка приземления свободна: Мара со свитой (M1b) ходит по Залесью и может встать в неё — тогда скок
        # по B-22 сажает героя у края тела (короче 3,5). Ближних врагов отводим и придерживаем на время каста.
        await G(f'''(() => {{ const g = __game, X = {A[0] + 2.5}, Y = {A[1] + 2.5};
            for (const e of g.enemies) {{ if (e.dead) continue; const d = Math.hypot(e.x - X, e.y - Y);
              if (d < 6) e.stagger = 1.5;
              if (d < 1.5) {{ const k = 1.6 / (d || 1); const nx = X + (e.x - X) * k, ny = Y + (e.y - Y) * k;
                if (g.dbg.circleFree ? g.dbg.circleFree(g.map, nx, ny, e.r) : true) {{ e.x = nx; e.y = ny; }} }} }} return 1; }})()''')
        tx, ty = await client_of(A[0] + 2.5, A[1] + 2.5)
        await pg.mouse.click(tx, ty, button='right'); await wait(380)
        p1 = await G('({ x: __game.hero.x, y: __game.hero.y, cd: __game.hero.cdLeft("skok"), skok: !!__game.combat.lastSkok || !!__game.lastSkok })')
        await wait(500)
        cb0 = await G('__game.counters.cdBlocked')
        tx2, ty2 = await client_of(A[0], A[1])
        await pg.mouse.click(tx2, ty2, button='right'); await wait(300)
        p2 = await G('({ x: __game.hero.x, y: __game.hero.y, cb: __game.counters.cdBlocked, casts: __game.counters.casts.skok })')
        check('ПКМ «Перунов скок»: перенос героя ≈3,5 тайла, удар грома, КД 3 с', abs(p1['x'] - p0[0]) > 2 and p1['cd'] > 2 and p1['skok'], (p0, p1))
        check('перезарядка блокирует повторное применение (герой не сдвинулся, счётчик cdBlocked)', abs(p2['x'] - p1['x']) < 0.05 and p2['cb'] == cb0 + 1 and p2['casts'] == 1, p2)
        await wait(2300)
        await pg.mouse.click(tx2, ty2, button='right'); await wait(450)
        check('после КД навык снова применяется', await G('__game.counters.casts.skok') == 2)
        # сцена для скриншота: у крады (открытая площадка), «Перунов скок» в пару упырей, «Чур-оберег» висит, «Морозко» на перезарядке нет — КД виден на скоке
        await wait(3100)
        sc = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; h.x = k.x + 1.5; h.y = k.y + 3.5; h.path = null; h.cmd = null; h.action = null; h.yar = h.maxYar; h.hp = h.maxHp;
            g.log.lines.length = 0; g.notice = null; h.levelFx = 0; h.cds = {}; h.buffs.chur = { t: 24, dur: 30, defPct: 50, resAll: 5 }; h.recalc();
            const t = [k.x + 4.5, k.y + 5.5]; const es = [g.spawnTest('upyr', t[0] + 0.6, t[1] - 0.4, 1), g.spawnTest('upyr', t[0] - 0.3, t[1] + 0.7, 1)];
            for (const e of es) e.stagger = 1e9; g.updateCamera(); return t; })()''')
        await pg.mouse.click(*(await client_of(sc[0], sc[1])), button='right'); await wait(330)
        await pg.mouse.move(*(await client_of(sc[0] - 4, sc[1] - 4)))
        await wait(60)
        await pg.screenshot(path=SHOT_SKILLS)
        await G('(() => { const g = __game; g.enemies = g.enemies.filter(e => e.pack !== -1); })()')
        check('скриншот панели навыков с перезарядкой и эффектом сохранён', os.path.exists(SHOT_SKILLS), os.path.basename(SHOT_SKILLS))
        # рывок (Пробел): КД 4 с
        await G(HOME); await G('(() => { const g = __game, h = g.hero; for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - h.x, e.y - h.y) < 5) { e.x = h.x + 8; e.y = h.y + 8; e.path = null; e.stagger = 1e9; } })()'); await wait(150)
        DT = await G('''import('./src/world/collision.js').then(({ circleFree }) => { const g = __game, h = g.hero; let best = [h.x + 3, h.y - 3];
          for (let a = 0; a < 16; a++) { const ang = -Math.PI / 4 + a * Math.PI / 8, cx = Math.cos(ang), cy = Math.sin(ang); let ok = true;
            for (let d = 0.25; d <= 3.4 && ok; d += 0.25) { const x = h.x + cx * d, y = h.y + cy * d; if (!circleFree(g.map, x, y, h.r) || g.enemies.some(e => !e.dead && Math.hypot(e.x - x, e.y - y) < 1.2)) ok = false; }
            if (ok) { best = [h.x + cx * 4, h.y + cy * 4]; break; } }
          return best; })''')                                  # свободное направление (рядом мог оказаться валун или тело)
        await pg.mouse.move(*(await client_of(DT[0], DT[1]))); await wait(80)
        await pg.mouse.move(*(await client_of(DT[0], DT[1]))); await wait(50)
        q0 = await G('[__game.hero.x, __game.hero.y, __game.counters.casts.dash || 0]')
        await pg.keyboard.press('Space')
        for _ in range(40):                                   # ждём кадр, который примет Пробел; дальше — фиксированный шаг
            if await G('(__game.counters.casts.dash || 0) > %d' % q0[2]):
                break
            await wait(25)
        q1 = await G('(() => { const g = __game, h = g.hero; g.simulate(0.3); return [h.x, h.y, h.cdLeft("dash")]; })()')
        await pg.keyboard.press('Space'); await wait(150)
        q2 = await G('(() => { const g = __game, h = g.hero; g.simulate(0.3); return [h.x, h.y, g.counters.casts.dash]; })()')
        check('рывок (Пробел): ≈3 тайла, повтор во время КД не срабатывает', 2.0 < ((q1[0] - q0[0]) ** 2 + (q1[1] - q0[1]) ** 2) ** 0.5 <= 3.05 and q1[2] > 3 and abs(q2[0] - q1[0]) < 0.01 and q2[2] == 1, (q0, q1, q2))

        # 10.5 QA: B-02 (ПКМ во время замаха не теряется), B-03 (смерть с летящим снарядом), фон большой карты
        await G(HOME)
        await pg.keyboard.press('F1'); await wait(50)
        e = await G('''(() => { const g = __game, h = g.hero; h.yar = h.maxYar; const e = g.spawnTest('upyr', h.x + 1.0, h.y + 0.1, 1); e.stagger = 1e9; return { id: e.id, x: e.x, y: e.y, h: e.def.height }; })()''')
        ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
        f0 = await G('__game.counters.bufferedFired || 0')
        await pg.mouse.click(ex, ey)
        for _ in range(80):                                        # ждём начала замаха
            if await G('(() => { const a = __game.hero.action; return !!(a && a.type === "attack"); })()'):
                break
            await wait(10)
        z0 = await G('__game.counters.casts.zmey || 0')
        # до конца замаха ставим ровно 0,2 с и в той же задаче — настоящие DOM-события ПКМ: следующий кадр примет нажатие
        # внутри окна буфера при любой частоте кадров (раньше под --throttle опрос успевал проскочить конец замаха)
        sw = await G('''(([x, y]) => { const a = __game.hero.action; if (!a || a.type !== 'attack') return null; a.t = Math.max(0, a.dur - 0.2);
            const c = document.getElementById('game'), o = { clientX: x, clientY: y, button: 2, buttons: 2, bubbles: true };
            c.dispatchEvent(new MouseEvent('mousemove', o)); c.dispatchEvent(new MouseEvent('mousedown', o)); window.dispatchEvent(new MouseEvent('mouseup', { ...o, buttons: 0 }));
            return [a.t, a.dur]; })''', [ex, ey])
        await wait(700)
        s = await G('({ b: __game.counters.buffered || 0, f: __game.counters.bufferedFired || 0, z: __game.counters.casts.zmey || 0 })')
        s['f0'] = f0; s['swing'] = sw
        check('B-02: ПКМ во время удара (окно 0,3 с) запоминается и срабатывает после замаха', s['f'] == f0 + 1 and s['z'] == z0 + 1, s)
        s = await G('''((id) => { const g = __game, h = g.hero; const e = g.enemies.find(o => o.id === id); h.action = null; h.cmd = null; h.yar = h.maxYar;
            e.x = h.x + 6; h.cds.zmey = 0; const r = h.useSkill(g, 'zmey', e.x, e.y, e); g.simulate(1, () => g.combat.projectiles.some(p => !p.hostile)); const fl = g.combat.projectiles.filter(p => !p.hostile).length;
            const xp0 = h.xp; h.invuln = 0; h.dashing = null; h.takeDamage(99999, g, 'fire'); const after = g.combat.projectiles.filter(p => !p.hostile).length; h.gainXp(50, g);
            const out = { fl, after, xpSame: h.xp === xp0, st: g.state, r }; g.enemies = g.enemies.filter(o => o !== e); return out; })''', e['id'])
        check('B-03: после гибели снаряды героя исчезают, опыт мёртвому не начисляется', s['fl'] >= 1 and s['after'] == 0 and s['xpSame'] and s['st'] == 'dead', s)
        await wait(2700); await pg.keyboard.press('Enter'); await wait(200)
        await G(FREEZE)
        await pg.keyboard.press('Tab'); await wait(120)
        PIX = '''(() => { const src = __game.ctx.canvas, c = document.createElement('canvas'); c.width = 8; c.height = 8; const x = c.getContext('2d', { willReadFrequently: true });
            x.drawImage(src, 4, 140, 8, 8, 0, 0, 8, 8); const d = x.getImageData(0, 0, 8, 8).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2]; return Math.round(s / 64); })()'''
        lum = await G(PIX)
        await pg.keyboard.press('Tab'); await wait(120)
        lum0 = await G(PIX)
        check('большая карта (Tab) на тёмной подложке', lum < 150 and lum <= lum0, (lum, lum0))

        # 10.6 правила дизайнера: базы 50/35/15, отход анчутки ≤ 1 раза в 3 с, реплики ≤ 1 раза в 15 с, тексты
        s = await G('''(() => { const d = __game.dbg; const cnt = (ilvl) => { const c = {}; for (let i = 0; i < 6000; i++) { const b = d.pickBase('sword', ilvl, Math.random); c[b.id] = (c[b.id] || 0) + 1; } return c; };
            return { i12: cnt(12), i7: cnt(7), i3: cnt(3) }; })()''')
        a12, a7 = s['i12'], s['i7']
        ok = abs(a12.get('sword_3', 0) / 6000 - 0.50) < 0.03 and abs(a12.get('sword_2', 0) / 6000 - 0.35) < 0.03 and abs(a12.get('sword_1', 0) / 6000 - 0.15) < 0.03
        ok = ok and abs(a7.get('sword_2', 0) / 6000 - 50 / 85) < 0.03 and 'sword_3' not in a7 and list(s['i3'].keys()) == ['sword_1']
        check('выбор базы: верхний тир 50%, предыдущий 35%, остальные 15% (без +3 к ilvl)', ok, s)
        s = await G('''(() => { const g = __game, h = g.hero; const a = g.spawnTest('anchutka', h.x + 1.6, h.y, 1); a.aggro(g, false); a.stagger = 0; h.invuln = 99;
            const b0 = g.counters.backoff || 0; g.simulate(2.9); const b1 = g.counters.backoff || 0; h.invuln = 0;
            g.enemies = g.enemies.filter(o => o !== a); return { n: b1 - b0, cd: g.dbg.CFG.monsters.anchutka ? g.dbg.CFG.monsters.anchutka.ranged.keepMinCooldown : null }; })()''')
        check('анчутка отходит от героя ближе 2,2 тайла не чаще раза в 3 с', s['n'] <= 1, s)
        s = await G('''(() => { const g = __game, h = g.hero, b0 = g.counters.barks, s0 = g.counters.barksSuppressed;
            const r = [g.bark(h, 'test.bark', 'Эй!'), g.bark(h, 'test.bark', 'Эй!')]; g.time += 15.1; r.push(g.bark(h, 'test.bark', 'Эй!'));
            return { r, barks: g.counters.barks - b0, sup: g.counters.barksSuppressed - s0 }; })()''')
        check('реплика над головой — не чаще раза в 15 с', s['r'] == [True, False, True] and s['sup'] == 1, s)
        s = await G('''(() => { const d = __game.dbg; return { p: [1, 3, 5, 11, 21, 22, 25, 111].map(n => n + ' ' + d.plural(n, 'враг', 'врага', 'врагов')),
            s: [d.silverText(1, 'counter'), d.silverText(21, 'lost'), d.silverText(86, 'ground')], ui: d.t('ui.error.no_yar') }; })()''')
        check('plural() для счётных слов; серебро без склонения («Серебро: N», «Потеряно серебра: N», «N сер.»); строки из data/ru.json',
              s['p'] == ['1 враг', '3 врага', '5 врагов', '11 врагов', '21 враг', '22 врага', '25 врагов', '111 врагов'] and s['s'] == ['Серебро: 1', 'Потеряно серебра: 21', '86 сер.'] and s['ui'] == 'Ярь на исходе', s)

        # 10.7 тихий круг у крады (QA B-16): не замечают, не заходят, погоня обрывается
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; h.invuln = 0; h.hp = h.maxHp;
            h.x = k.x + 6; h.y = k.y; h.path = null; h.cmd = null; h.action = null;
            const e = g.spawnTest('upyr', k.x + 11.5, k.y, 1); e.stagger = 0; g.simulate(3);
            const noticed = e.state !== 'idle';
            e.x = e.homeX; e.y = e.homeY; e.path = null; e.state = 'idle'; h.x = k.x + 14.5; e.aggro(g, false); g.simulate(0.3); const chasing = e.state === 'chase';
            h.x = k.x + 8; const b0 = g.counters.safeBreaks || 0; g.simulate(0.4);
            const out = { noticed, chasing, after: e.state, breaks: (g.counters.safeBreaks || 0) - b0 };
            g.enemies = g.enemies.filter(o => o !== e); return out; })()''')
        check('B-16: упырь в 5,5 тайла от героя в тихом круге не замечает его; погоня обрывается, когда герой вбегает в круг',
              not s['noticed'] and s['chasing'] and s['after'] in ('return', 'idle') and s['breaks'] >= 1, s)
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; h.x = k.x + 0.5; h.y = k.y + 2; h.path = null; h.cmd = null; h.hp = h.maxHp; h.invuln = 0;
            for (const e of g.enemies) e.stagger = 0; const hp0 = h.hp; g.simulate(30); const out = { hp0, hp: h.hp, st: g.state,
            inside: g.enemies.filter(e => !e.dead && g.safeAt(e.x, e.y)).length }; for (const e of g.enemies) e.stagger = 1e9; return out; })()''')
        check('B-16: 30 с у крады без действий — героя никто не трогает, нечисти в тихом круге нет', s['hp'] == s['hp0'] and s['st'] == 'play' and s['inside'] == 0, s)
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada, out = {}; h.x = k.x + 1; h.y = k.y + 2; h.path = null; h.cmd = null; h.action = null; h.hp = h.maxHp; h.invuln = 0;
            const a = g.spawnTest('anchutka', k.x + 12.5, k.y + 2, 1); a.stagger = 1e9; const f0 = g.counters.safeFizzle || 0, hp0 = h.hp;
            g.combat.throwCoal(a, h.x, h.y); const p = g.combat.projectiles[g.combat.projectiles.length - 1]; let last = null;
            g.simulate(2, () => { if (!p.dead) last = [p.x, p.y]; return p.dead; }); out.coal = { fizzled: (g.counters.safeFizzle || 0) - f0, hpSame: h.hp === hp0, at: last && +Math.hypot(last[0] - k.x, last[1] - k.y).toFixed(2) };
            g.enemies = g.enemies.filter(o => o !== a);
            const e = g.spawnTest('upyr', k.x + 11, k.y + 2, 1); e.homeX = k.x + 16; e.homeY = k.y + 2; e.stagger = 0; h.x = k.x + 8.5;
            e.takeDamage(6, g, 'fire', h); out.hit = { state: e.state, hp: e.hp, max: e.maxHp }; g.simulate(5); out.after = { state: e.state, hp: e.hp, dHome: +Math.hypot(e.x - e.homeX, e.y - e.homeY).toFixed(1) };
            g.enemies = g.enemies.filter(o => o !== e);
            const ar = g.spawnTest('chernoyarets_arsonist', k.x + 4, k.y + 10.3, 3); h.x = k.x; h.y = k.y + 10.3; h.hp = h.maxHp; const t0 = g.counters.torches || 0; ar.aggro(g, false);
            g.simulate(1.5); out.torch = { thrown: (g.counters.torches || 0) - t0, heroSafe: g.safeAt(h.x, h.y), cd: +ar.torchCd.toFixed(1) };
            g.enemies = g.enemies.filter(o => o !== ar); g.combat.fires = []; h.hp = h.maxHp; return out; })()''')
        check('GDD v1.6 §4.5: уголь гаснет на границе тихого круга; бьют из круга — враг уходит к логову и лечится; огонь в круг не ставится',
              s['coal']['fizzled'] == 1 and s['coal']['hpSame'] and s['coal']['at'] is not None and 9.4 <= s['coal']['at'] <= 10.6
              and s['hit']['state'] == 'return' and s['after']['state'] == 'idle' and s['after']['hp'] == s['hit']['max']
              and s['torch']['thrown'] == 0 and not s['torch']['heroSafe'], s)

        # 10.8 B-15: ПКМ по зелью в котомке соблюдает КД зелий
        s = await G('''(() => { const g = __game, h = g.hero; h.belt = [{ kind: 'life1', count: 5 }, { kind: 'life1', count: 5 }, { kind: 'yar1', count: 5 }, { kind: 'yar1', count: 5 }];
            for (let i = 0; i < 5; i++) g.give('potion:life1'); h.hp = 5; h.potionCd = 0; h.effects = [];
            const ents = h.inv.entries.filter(e => e.item.kind === 'potion'); let drunk = 0;
            for (const e of ents) { const n = h.inv.items.length; g.ui.quickEquip(e); if (h.inv.items.length < n) drunk++; }
            const cd = h.potionCd; g.simulate(1.05); const e2 = h.inv.entries.find(e => e.item.kind === 'potion'); const n2 = h.inv.items.length; if (e2) g.ui.quickEquip(e2);
            return { drunk, cd, second: n2 - h.inv.items.length, left: h.inv.items.filter(i => i.kind === 'potion').length }; })()''')
        check('B-15: из котомки ПКМ — одно зелье за КД 1 с, следующее после КД', s['drunk'] == 1 and s['cd'] > 0.9 and s['second'] == 1, s)
        await G('(() => { const h = __game.hero; for (const it of h.inv.items.filter(i => i.kind === "potion")) h.inv.remove(it); })()')
        s = await G('''(() => { const g = __game, h = g.hero; h.belt = [{ kind: 'life1', count: 5 }, { kind: 'yar1', count: 5 }, { kind: 'zhivaya', count: 3 }, { kind: 'life1', count: 5 }];
            h.potionCd = 0; h.effects = []; h.hp = 5; h.yar = 1; const c = (i) => h.belt[i] ? h.belt[i].count : 0; const n0 = [c(0), c(1), c(2), c(3)];
            h.drink(0, g); h.drink(1, g); h.drink(3, g); const n1 = [c(0), c(1), c(2), c(3)]; h.hp = 5; h.yar = 1; h.drink(2, g); const z = c(2);
            const cds = { ...h.potionCds }; g.simulate(1.05); h.hp = 5; h.drink(3, g); const n2 = c(3);
            h.belt = [{ kind: 'life1', count: 2 }, { kind: 'life1', count: 1 }, { kind: 'yar1', count: 2 }, null]; h.effects = []; h.hp = h.maxHp; h.yar = h.maxYar;
            return { n0, n1, zAfter: z, cds, n2 }; })()''')
        check('GDD v1.6 §4.4: перезарядка 1 с своя у жизни и у Яри; живая вода — вне перезарядки',
              s['n1'][0] == s['n0'][0] - 1 and s['n1'][1] == s['n0'][1] - 1 and s['n1'][3] == s['n0'][3] and s['zAfter'] == s['n0'][2] - 1
              and s['cds']['hp'] > 0.9 and s['cds']['yar'] > 0.9 and s['n2'] == s['n0'][3] - 1, s)

        # 10.9 B-17/B-18: сравнение по итоговым числам (DPS, свойства), перстни — с обоими
        s = await G('''(() => { const g = __game, h = g.hero;
            const mk = (b, aff) => { const it = g.give(b, aff ? 'magic' : 'normal', aff ? { affixes: aff } : {}); h.inv.remove(it); return it; };
            const sc = mk('sword_1'); const prev = h.equip.rhand; h.equip.rhand = sc; h.recalc();
            const axe = mk('axe_1'), ed = mk('sword_1', [['P01', 20]]), ias = mk('sword_1', [['S10', 10]]);
            const r = { axe: g.dbg.cmp(axe), ed: g.dbg.cmp(ed), ias: g.dbg.cmp(ias) };
            h.equip.rhand = prev; const o1 = h.equip.ring1, o2 = h.equip.ring2;
            const r1 = mk('ring_1', [['S01', 8]]), r2 = mk('ring_1', [['S01', 8]]), r3 = mk('ring_1', [['S01', 12]]);
            h.equip.ring1 = null; h.equip.ring2 = r2; h.recalc(); r.ring2only = g.dbg.cmp(r3);
            h.equip.ring1 = r1; h.recalc(); r.both = g.dbg.cmp(r3); h.equip.ring1 = o1; h.equip.ring2 = o2; h.recalc();
            return r; })()''')
        txt = lambda a: ' | '.join(x[0] for x in a)
        ok = any('Урон в секунду: −' in x[0] for x in s['axe']) and any('Урон в секунду: +' in x[0] for x in s['ed']) and any('Урон в секунду: +' in x[0] for x in s['ias'])
        ok = ok and any('свободен' in x[0] for x in s['ring2only']) and sum(1 for x in s['both'] if x[0].startswith('Вместо')) == 2
        check('B-17/B-18: топорик хуже скрамасакса по DPS, «Калёный»/«…сокола» лучше; перстень — свободный слот или оба надетых',
              ok, {k: txt(v) for k, v in s.items()})

        # 10.10 замеры баланса и симуляции дизайнера (свежий герой, без зелий)
        bal = await G("""(async () => { const g = __game, keep = g.hero, A = %s, { Hero } = await import('/src/entities/hero.js');
          // замеры воспроизводимы: на время прогонов — свой генератор случайных чисел с постоянным зерном (mulberry32)
          const rnd0 = Math.random; let seed = 20261008; Math.random = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
            t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
          // стаи зоны на время замеров убираем целиком (замороженные рядом с площадкой мешали бою и просыпались от «Сшибки»), в конце возвращаем
          const stash = g.enemies; g.enemies = [];
          const clean = () => { g.enemies = g.enemies.filter(e => e.pack !== -1); g.combat.projectiles.length = 0; g.state = 'play'; g.deathT = 0; g.hitStopT = 0; };
          const mk = (L) => { const h = new Hero(A[0], A[1]); let n = 0; while (h.level < L && n++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g);
            h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar; h.belt = [null, null, null, null]; h.levelFx = 0; g.hero = h; return h; };
          const mean = (a) => +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2);
          const near = (h, es) => { let b = null, bd = 1e9; for (const e of es) { if (e.dead) continue; const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; b = e; } } return b; };
          const melee = (h, es, lmb, refill) => g.simulate(90, () => { if (refill) h.hp = h.maxHp; const t = near(h, es); if (!t || h.dead) return true;
              if (!h.cmd && !h.action) h.attack(t, false, lmb ? h.lmbSkill() : null, true); return false; });
          const res = {};
          for (const [key, lmb] of [['sshibka', true], ['plain', false]]) { const ts = [];
            for (let i = 0; i < 60; i++) { clean(); const h = mk(1); const e = g.spawnTest('upyr', A[0] + 1.0, A[1], 1); e.aggro(g, false); ts.push(melee(h, [e], lmb, true)); }
            res['ttk_' + key] = { mean: mean(ts), min: +Math.min(...ts).toFixed(2), max: +Math.max(...ts).toFixed(2) }; }
          { const sk = g.dbg.SKILLS.sshibka, kb = sk.knockback; sk.knockback = 0; const ts = [];    // справочно: «Сшибка» без отбрасывания (герою не нужно догонять)
            for (let i = 0; i < 20; i++) { clean(); const h = mk(1); const e = g.spawnTest('upyr', A[0] + 1.0, A[1], 1); e.aggro(g, false); ts.push(melee(h, [e], true, true)); }
            sk.knockback = kb; res.ttk_sshibka_noKnockback = { mean: mean(ts), min: +Math.min(...ts).toFixed(2), max: +Math.max(...ts).toFixed(2) }; }
          { let xp = 0; for (const p of g.map.packs) for (const k of p.kinds) xp += g.dbg.enemyStats(k, p.mlvl).xp;
            let L = 1, need = 0; while (need + g.dbg.xpToNext(L) <= xp) { need += g.dbg.xpToNext(L); L++; }
            res.zoneXp = { total: xp, level: L, progress: +((xp - need) / g.dbg.xpToNext(L)).toFixed(2) }; }
          { const ts = []; for (let i = 0; i < 20; i++) { clean(); const h = mk(1); const e = g.spawnTest('upyr', A[0] + 2.5, A[1] + 0.5, 1); e.aggro(g, false);
              ts.push(g.simulate(30, () => { h.hp = h.maxHp; h.yar = h.maxYar; if (!h.action && !e.dead) h.useSkill(g, 'zmey', e.x, e.y, e); return e.dead; })); }
            res.ttk_fire = { mean: mean(ts), min: +Math.min(...ts).toFixed(2), max: +Math.max(...ts).toFixed(2) }; }
          for (const [L, ml] of [[1, 1], [2, 2]]) { let deaths = 0; const ts = [], hpLeft = [], yarEnd = [];
            for (let i = 0; i < 30; i++) { clean(); const h = mk(L); const es = [0, 1, 2].map(j => { const e = g.spawnTest('upyr', A[0] + 3.5, A[1] - 1 + j, ml); e.aggro(g, false); return e; });
              ts.push(melee(h, es, true, false)); if (h.dead) deaths++; else hpLeft.push(h.hp / h.maxHp); yarEnd.push(h.yar); }
            res['fight_L' + L + '_vs3upyr_m' + ml] = { runs: 30, deaths, time: mean(ts), hpLeftPct: hpLeft.length ? Math.round(mean(hpLeft) * 100) : 0, yarEnd: mean(yarEnd) }; }
          for (const [key, kinds] of [['fight_L2_vs3anchutka_m2', ['anchutka', 'anchutka', 'anchutka']], ['fight_L2_vs3upyr1anchutka_m2', ['upyr', 'upyr', 'upyr', 'anchutka']]]) {
            let deaths = 0; const ts = [], hpLeft = [];     // GDD v1.7 §9.3: 2 ур. (2 Жив / 2 Сила / 1 Ловк, «Сшибка» 2) против стай mlvl 2 у выхода из Залесья
            for (let i = 0; i < 30; i++) { clean(); const h = mk(2); h.base.vit += 2; h.base.str += 2; h.base.dex += 1; h.points = 0; h.skills.sshibka = 2; h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar;
              const es = kinds.map((k, j) => { const e = g.spawnTest(k, A[0] + 4, A[1] - 1.5 + j, 2); e.aggro(g, false); return e; });
              ts.push(melee(h, es, true, false)); if (h.dead) deaths++; else hpLeft.push(h.hp / h.maxHp); }
            res[key] = { runs: 30, deaths, time: mean(ts), hpLeftPct: hpLeft.length ? Math.round(mean(hpLeft) * 100) : 0 }; }
          // GDD v1.6 §9.1/§12.3: стоячий герой против 3 упырей mlvl = уровню героя; вещи и статы по таблице дизайнера, блок щита 0;
          // таймер — с момента, когда все трое вплотную; 30 прогонов
          const KITS = { 3: { st: [24, 22, 29, 15], gear: [['lhand', 'shield_1', 5], ['head', 'head_1', 4, 5], ['body', 'body_1', 9], ['gloves', 'gloves_1', 2]], hp: 91, def: 25 },
            6: { st: [30, 25, 35, 15], gear: [['body', 'body_2', 20, 12], ['head', 'head_1', 4], ['lhand', 'shield_1', 5], ['gloves', 'gloves_1', 2], ['feet', 'boots_1', 2], ['belt', 'belt_1', 2]], hp: 122, def: 41 },
            10: { st: [38, 29, 43, 15], gear: [['body', 'body_2', 20, 12], ['head', 'head_2', 9, 10], ['lhand', 'shield_2', 11], ['gloves', 'gloves_1', 3], ['feet', 'boots_2', 6], ['belt', 'belt_2', 6]], hp: 164, def: 62 } };
          const { makeItem } = await import('/src/data/items.js');
          const kit = (L) => { const h = mk(L), K = KITS[L]; [h.base.str, h.base.dex, h.base.vit, h.base.ene] = K.st; h.points = 0;
            for (const s of ['lhand', 'head', 'body', 'gloves', 'feet', 'belt', 'neck', 'ring1', 'ring2']) h.equip[s] = null;
            for (const [slot, base, armor, hpb] of K.gear) { const it = makeItem(base, hpb ? 'magic' : 'normal', L, Math.random, { armor, affixes: hpb ? [['S01', hpb]] : [] }); if (it.block) it.block = 0; h.equip[slot] = it; }
            h.recalc(); h.hp = h.maxHp; return h; };
          for (const L of [3, 6, 10]) { const out = []; let info = null;
            for (let i = 0; i < 30; i++) { clean(); const h = kit(L); info = { hp: h.maxHp, def: h.def, block: h.block, str: h.str, dex: h.dex, vit: h.vit };
              const es = [0, 1, 2].map(j => { const a = j * 2.094 + 0.3; const e = g.spawnTest('upyr', A[0] + Math.cos(a) * 1.05, A[1] + Math.sin(a) * 1.05, L); e.aggro(g, false); return e; });
              const adj = () => es.every(e => !e.dead && Math.hypot(e.x - h.x, e.y - h.y) <= e.def.reach + h.r * 0.5);
              g.simulate(10, adj); if (!adj()) { out.push(NaN); continue; }
              out.push(g.simulate(180, () => h.dead)); }
            const ok = out.filter(x => !isNaN(x));
            res['stand_L' + L] = { runs: ok.length, mean: mean(ok), min: +Math.min(...ok).toFixed(2), max: +Math.max(...ok).toFixed(2), ...info, expect: { hp: KITS[L].hp, def: KITS[L].def } }; }
          clean(); g.enemies = stash; g.hero = keep; keep.hp = keep.maxHp; Math.random = rnd0; return res; })()""" % json.dumps(A))
        print('БАЛАНС:', json.dumps(bal, ensure_ascii=False), flush=True)
        with open(os.path.join(ROOT, 'tools', 'balance_iter2.json'), 'w', encoding='utf-8') as f:
            json.dump(bal, f, ensure_ascii=False, indent=1)
        f1, f2 = bal['fight_L1_vs3upyr_m1'], bal['fight_L2_vs3upyr_m2']
        check('симуляция дизайнера: герой 1 ур. со «Сшибкой», без зелий, против 3 упырей mlvl 1 — 0 смертей из 30', f1['deaths'] == 0, f1)
        check('симуляция дизайнера: герой 2 ур. против 3 упырей mlvl 2 — не больше 5 смертей из 30', f2['deaths'] <= 5, f2)
        check('контрольная точка GDD v1.7 §9.3: Залесье — выход на 2-м уровне (±1), опыт ≈ 282 (допуск 270–330)', 1 <= bal['zoneXp']['level'] <= 3 and 270 <= bal['zoneXp']['total'] <= 330, bal['zoneXp'])
        f3 = bal['fight_L2_vs3anchutka_m2']
        check('контроль GDD v1.7: 2 ур. (2 Жив / 2 Сила / 1 Ловк, «Сшибка» 2) без зелий против 3 анчуток mlvl 2 — не больше 1 смерти из 30', f3['deaths'] <= 1, f3)
        f4 = bal['fight_L2_vs3upyr1anchutka_m2']
        check('контроль GDD v1.7: 2 ур. без зелий против смешанной «3 упыря + 1 анчутка» mlvl 2 — не больше 5 смертей из 30', f4['deaths'] <= 5, f4)
        check('замеры TTK и выживания получены (tools/balance_iter2.json)', bal['ttk_sshibka']['mean'] > 0 and bal['stand_L3']['mean'] > 0, {k: bal[k]['mean'] for k in ('ttk_sshibka', 'ttk_plain', 'ttk_fire', 'stand_L3', 'stand_L6', 'stand_L10')})
        check('GDD v1.6 §9.2: «Сшибка» убивает упыря mlvl 1 за 1,5–2,5 с (прогноз ≈2,2)', 1.5 <= bal['ttk_sshibka']['mean'] <= 2.5, bal['ttk_sshibka'])
        st = {L: bal['stand_L%d' % L] for L in (3, 6, 10)}
        check('GDD v1.6 §12.3: комплекты замера стоячего героя — HP 91/122/164, DEF 25/41/62, блок 0, 30 прогонов',
              all(st[L]['hp'] == st[L]['expect']['hp'] and st[L]['def'] == st[L]['expect']['def'] and st[L]['block'] == 0 and st[L]['runs'] == 30 for L in st), st)
        print('ВЫЖИВАНИЕ v1.6 (норма 9–12 с с 5 ур., до 15 с на 3 ур.): ' + ', '.join('L%d %.2f с' % (L, st[L]['mean']) for L in st), flush=True)
        await G(UNFREEZE)

        # --- 10.9 QA итерации 2b (B-20…B-25, доделки B-02 / B-18)
        await G(HOME)
        await G(FREEZE)
        await G(AWAY)
        s = await G('''(() => { const g = __game, h = g.hero; h.hp = h.maxHp; h.invuln = 0; h.graceT = 0; h.cds = {}; h.action = null; h.cmd = null;
            const us = [0, 1, 2].map(i => { const e = g.spawnTest('upyr', h.x + 2.2, h.y - 1 + i, 1); e.stagger = 0; e.aggro(g, false); return e; });
            g.simulate(0.3); const r = h.dash(g, h.x - 3, h.y); const st = []; g.simulate(1.2, () => { st.push(us.map(e => e.state).join()); return false; });
            const out = { r, after: us.map(e => e.state), returned: st.some(x => x.includes('return')), d: us.map(e => +e.distTo(h).toFixed(1)) };
            g.enemies = g.enemies.filter(e => !us.includes(e)); return out; })()''')
        check('B-20: «Рывок» (0,15 с неуязвимости) не обрывает погоню — упыри не уходят к логову',
              s['r'] == 'ok' and not s['returned'] and all(x in ('chase', 'attack') for x in s['after']), s)
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada, m = g.map; h.invuln = 0; h.cmd = null; h.action = null; h.hp = h.maxHp;
            // герой внутри круга у самой границы (9,75), анчутка снаружи (10,9): уголь касается героя, ещё не пересёк границу (≈10,2)
            let ang = null; for (let i = 0; i < 64 && ang === null; i++) { const a = i / 64 * 6.283, ok = [9.4, 9.75, 10.2, 10.6, 10.9, 11.3].every(r => !m.opaqueAt(k.x + Math.cos(a) * r, k.y + Math.sin(a) * r) && !m.blockedAt(k.x + Math.cos(a) * r, k.y + Math.sin(a) * r)); if (ok) ang = a; }
            const c = Math.cos(ang), sn = Math.sin(ang); h.x = k.x + c * 9.75; h.y = k.y + sn * 9.75;
            const a = g.spawnTest('anchutka', k.x + c * 10.9, k.y + sn * 10.9, 1); a.stagger = 1e9; const f0 = g.counters.safeFizzle || 0, hp0 = h.hp;
            g.combat.throwCoal(a, h.x, h.y); g.simulate(1.2); const out = { inside: g.safeAt(h.x, h.y), hp: [hp0, h.hp], fizzled: (g.counters.safeFizzle || 0) - f0, left: g.combat.projectiles.filter(p => p.hostile && !p.dead).length };
            g.enemies = g.enemies.filter(e => e !== a); return out; })()''')
        check('B-21: уголь, брошенный в героя у самой границы тихого круга, гаснет — урона внутри нет',
              s['inside'] and s['hp'][0] == s['hp'][1] and s['fizzled'] >= 1 and s['left'] == 0, s)
        await G(HOME)
        s = await G('''(() => { const g = __game, h = g.hero, keep = { ...h.skills }; h.skills.skok = 1; h.recalc(); h.yar = h.maxYar; h.cds = {}; h.action = null; h.cmd = null;
            const e = g.spawnTest('upyr', h.x + 3.5, h.y, 1); e.stagger = 1e9; e.hp = 9999; e.maxHp = 9999; const x0 = h.x, ex = e.x, ey = e.y;
            const r = h.useSkill(g, 'skok', e.x, e.y, e); g.simulate(0.8, () => g.lastSkok && g.lastSkok.t > 0 && Math.abs(h.x - x0) > 1);
            const to = g.lastSkok ? g.lastSkok.to : [h.x, h.y];
            const out = { r, d: +Math.hypot(to[0] - ex, to[1] - ey).toFixed(3), need: +(h.r + e.r).toFixed(3), jumped: +(h.x - x0).toFixed(2), hit: g.lastSkok && g.lastSkok.hit.includes(e.id) };
            g.enemies = g.enemies.filter(o => o !== e); h.skills = keep; h.recalc(); return out; })()''')
        check('B-22 / GDD v1.7: «Перунов скок» по врагу — приземление перед целью на r героя + r врага, удар проходит',
              s['r'] == 'ok' and abs(s['d'] - s['need']) <= 0.02 and s['jumped'] > 2 and s['hit'], s)
        await G(HOME)
        s = await G('''(() => { const g = __game, h = g.hero, inp = g.input; h.yar = h.maxYar; h.cds = {}; h.action = null; h.cmd = null; g.dashBuf = null;
            const c0 = g.counters.dashBufferedFired || 0; h.useSkill(g, 'zmey', h.x + 3, h.y); g.simulate(0.05); const busy = h.action && !h.action.fired;
            const [sx, sy] = g.toS(h.x - 3, h.y); inp.mx = sx; inp.my = sy; inp.keysPressed.add('Space'); g.update(1 / 60); inp.endFrame();
            const kept = !!g.dashBuf && !h.dashing; let dashed = false; g.simulate(1.0, () => { if (h.dashing) dashed = true; return dashed; });
            return { busy, kept, dashed, fired: (g.counters.dashBufferedFired || 0) - c0 }; })()''')
        check('B-23: Пробел во время каста запоминается — рывок срабатывает после выпуска снаряда', s['busy'] and s['kept'] and s['dashed'] and s['fired'] == 1, s)
        await G(HOME)
        s = await G('''(() => { const g = __game, h = g.hero, inp = g.input; g.simulate(0.5); h.dashing = null; h.yar = h.maxYar; h.cds = {}; h.action = null; h.cmd = null; g.rmbBuf = null; g.dashBuf = null; h.rmb = 'zmey';
            const z0 = g.counters.casts.zmey || 0; h.lmb = null; h.action = null;
            const rs = h.useSkill(g, 'sshibka', h.x + 1, h.y); if (rs !== 'ok' || !h.action) return { fail: rs };
            g.simulate(0.08); const [sx, sy] = g.toS(h.x + 3, h.y + 0.5); inp.mx = sx; inp.my = sy; inp.rightPressed = true; inp.right = false; g.update(1 / 60); inp.endFrame();
            const buf = !!g.rmbBuf, dur = +h.attackTime.toFixed(2); g.simulate(1.5, () => (g.counters.casts.zmey || 0) > z0);
            return { buf, dur, cast: (g.counters.casts.zmey || 0) - z0 }; })()''')
        check('B-02: ПКМ в самом начале замаха (0,1 с при замахе дольше 0,3 с) не теряется — змей вылетает после удара', s['buf'] and s['dur'] > 0.4 and s['cast'] == 1, s)
        s = await G('''(() => { const g = __game, h = g.hero; h.yar = h.maxYar; h.cds = {}; h.action = null; h.cmd = null; const d0 = h.def;
            h.useSkill(g, 'chur', h.x, h.y); g.simulate(0.7); h.cds.skok = 2.5; h.cds.dash = 3; const d1 = h.def, buff1 = !!h.buffs.chur;
            h.invuln = 0; h.graceT = 0; h.takeDamage(99999, g, 'fire'); const atDeath = { dead: h.dead, buff: !!h.buffs.chur, cds: Object.values(h.cds).filter(v => v > 0).length };
            g.respawnHero(); const out = { d0, d1, buff1, atDeath, buff: Object.keys(h.buffs).length, cds: Object.values(h.cds).filter(v => v > 0).length, def: h.def, grace: h.graceT > 0 };
            g.simulate(2.2); return out; })()''')
        check('B-24: гибель снимает «Чур-оберег» и обнуляет перезарядки; после возрождения Защита прежняя',
              s['buff1'] and s['d1'] > s['d0'] and s['atDeath']['dead'] and not s['atDeath']['buff'] and s['atDeath']['cds'] == 0 and s['buff'] == 0 and s['cds'] == 0 and s['def'] == s['d0'] and s['grace'], s)
        s = await G('''(() => { const g = __game, all = g.map.packs.flatMap(p => p.kinds.map(k => ({ kind: k, mlvl: p.mlvl }))); const kinds = (m) => ['upyr', 'anchutka'].map(k => all.filter(e => e.mlvl === m && e.kind === k).length);
            return { m1: kinds(1), m2: kinds(2), packs: g.map.packs.map(p => p.kinds.length) }; })()''')
        check('B-25 / GDD v1.7: Залесье — 28 врагов: 20 упырей / 8 анчуток, 18 mlvl 1 + 10 mlvl 2',
              s['m1'][0] + s['m2'][0] == 20 and s['m1'][1] + s['m2'][1] == 8 and sum(s['m1']) == 18 and sum(s['m2']) == 10, s)
        s = await G('''(() => { const g = __game, h = g.hero, keep = [h.equip.ring1, h.equip.ring2];
            const life = g.give('ring_1', 'magic', { affixes: [['S01', 1]] }), bear = g.give('ring_1', 'magic', { affixes: [['S02', 3]] });
            const life2 = g.give('ring_1', 'magic', { affixes: [['S01', 1]] }); if (life2) h.inv.remove(life2); if (life) h.inv.remove(life); h.equip.ring1 = life; h.equip.ring2 = life2; h.recalc();
            const lines = g.dbg.cmp(bear).map(l => l[0]); h.equip.ring1 = keep[0]; h.equip.ring2 = keep[1]; h.recalc(); for (const it of [life, bear]) if (it) h.inv.remove(it); return { name: bear.name, lines }; })()''')
        check('B-18: сравнение показывает свойства — «Перстень медведя» против «живота»: Сила +N и Жизнь −N', any(l.startswith('Сила: +') for l in s['lines']) and any(l.startswith('Жизнь: −') for l in s['lines']), s)
        # GDD v1.7 п.4: ввод во время замаха копится, срабатывает последний (ПКМ, затем Пробел → рывок; Пробел, затем ЛКМ → только ЛКМ)
        await G(HOME)
        s = await G('''(() => { const g = __game, h = g.hero, inp = g.input; g.simulate(0.3); h.dashing = null; h.yar = h.maxYar; h.cds = {}; h.action = null; h.cmd = null; g.rmbBuf = null; g.dashBuf = null; h.rmb = 'zmey';
            const press = (fn, wx, wy) => { const [sx, sy] = g.toS(wx, wy); inp.mx = sx; inp.my = sy; fn(); g.update(1 / 60); inp.endFrame(); };
            const c = () => ({ z: g.counters.casts.zmey || 0, d: g.counters.casts.dash || 0 });
            let c0 = c(); h.useSkill(g, 'sshibka', h.x + 1, h.y); g.simulate(0.05);
            press(() => { inp.rightPressed = true; inp.right = false; }, h.x + 3, h.y);
            press(() => inp.keysPressed.add('Space'), h.x - 3, h.y);
            g.simulate(1.5); let c1 = c(); const a = { zmey: c1.z - c0.z, dash: c1.d - c0.d };
            g.simulate(0.5); h.cds = {}; h.dashing = null; c0 = c(); h.useSkill(g, 'sshibka', h.x + 1, h.y); g.simulate(0.05);
            press(() => inp.keysPressed.add('Space'), h.x - 3, h.y);
            const tx = h.x + 2, ty = h.y + 2; press(() => { inp.leftPressed = true; inp.left = false; }, tx, ty);
            g.simulate(1.5); c1 = c(); const b = { zmey: c1.z - c0.z, dash: c1.d - c0.d, moved: +Math.hypot(h.x - tx, h.y - ty).toFixed(2) };
            return { a, b }; })()''')
        check('GDD v1.7: ввод во время замаха копится до конца действия, срабатывает последний (ПКМ→Пробел: рывок; Пробел→ЛКМ: шаг)',
              s['a'] == {'zmey': 0, 'dash': 1} and s['b']['zmey'] == 0 and s['b']['dash'] == 0 and s['b']['moved'] < 0.6, s)
        # GDD v1.7 п.2: отдых в тихом круге — +20%/с Жизни и Яри после 2 с без урона; вне круга регена Жизни нет
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; const R = g.zone.safeZones[0].rest; h.x = k.x + 2; h.y = k.y + 2; h.cmd = null; h.action = null;
            h.hp = Math.round(h.maxHp * 0.2); h.yar = 0; h.invuln = 0; h.takeDamage(1, g, 'fire'); const hp0 = h.hp;
            g.simulate(1.9); const at19 = h.hp; g.simulate(1.0); const at29 = h.hp, y29 = h.yar; g.simulate(4.5); const full = h.hp === h.maxHp && h.yar === h.maxYar;
            const [ox, oy] = (() => { for (let r = 13; r < 20; r++) for (let a = 0; a < 16; a++) { const x = k.x + Math.cos(a / 16 * 6.283) * r, y = k.y + Math.sin(a / 16 * 6.283) * r; if (!g.safeAt(x, y) && g.dbg.circleFree(g.map, x, y, 0.4)) return [x, y]; } return [k.x + 14, k.y]; })();
            h.x = ox; h.y = oy; h.hp = Math.round(h.maxHp / 2); const hpOut0 = h.hp; g.simulate(4); const hpOut = h.hp;
            const out = { R: [R.pctPerSec, R.noDamageSec], hp0, at19, at29, perSec: +((at29 - at19) / h.maxHp * 100).toFixed(1), y29: +y29.toFixed(1), maxYar: h.maxYar, full, hpOut: [hpOut0, Math.floor(hpOut)], restT: +(g.counters.restT || 0).toFixed(1) };
            h.hp = h.maxHp; return out; })()''')
        check('GDD v1.7: отдых — в тихом круге Жизнь и Ярь +20%/с после 2 с без урона (≈5 с до полной), вне круга Жизнь не растёт',
              s['R'] == [20, 2] and s['at19'] == s['hp0'] and 15 <= s['perSec'] <= 21 and s['full'] and s['hpOut'][1] == s['hpOut'][0], s)
        # Эффекты отдыха художника (fx_rest_*, fx_safe_ring) по правилам дизайнера 08.10: общая фаза покоя/отдыха, искры пока
        # растут шкалы (петля доигрывает), кольцо рез 50% — у границы (±3 тайла) или во время отдыха
        s = await G('''(async () => { const g = __game, h = g.hero, k = g.map.krada, FXm = await import('/src/render/rest_fx.js'), FX = FXm.FX;
            const sheets = Object.keys(FX.sheets).sort(), lay = FX.ring ? Object.values(FX.ring.layouts).map(l => [l.radius_tiles, l.pieces.length]) : [];
            const ki = FX.sheets.krada_idle, kr = FX.sheets.krada_rest, ci = FX.sheets.churov_idle, cr = FX.sheets.churov_rest;
            let phase = true; for (let t = 0; t < 3; t += 0.037) if (FXm.loopFrame(ki, t) !== FXm.loopFrame(kr, t) || FXm.loopFrame(ci, t) !== FXm.loopFrame(cr, t)) phase = false;
            const px = (R, lit) => { const c = document.createElement('canvas'); c.width = 520; c.height = 280; const x = c.getContext('2d', { willReadFrequently: true });
              FXm.drawSafeRing(x, R, 260, 140, 0.5, lit); const d = x.getImageData(0, 0, 520, 280).data; let n = 0, amax = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) { n++; amax = Math.max(amax, d[i]); } return [n, amax]; };
            const ringPx = { R10: px(10, false), R6: px(6, true) };
            const at = (d) => { h.x = k.x + d * 0.7071; h.y = k.y + d * 0.7071; h.cmd = null; h.action = null; h.path = null; };
            const ring = () => +g.restFx.rings.krada.a.toFixed(2), kp = g.map.props.find(p => p.krada);
            h.hp = h.maxHp; h.yar = h.maxYar; at(2.5); g.simulate(0.5); const mid = { a: ring(), src: g.restFx.src, sp: g.restFx.sparksFrame };
            at(8.5); g.simulate(0.5); const border = { a: ring(), lit: g.restFx.rings.krada.lit };
            at(12.5); g.simulate(0.5); const outNear = ring(); at(14.5); g.simulate(0.5); const far = ring();
            at(2.5); h.hp = Math.round(h.maxHp * 0.3); h.invuln = 0; h.takeDamage(1, g, 'fire'); g.simulate(1.0); const early = { r: g.resting, sp: g.restFx.sparksFrame, kp: kp.restOn };
            g.simulate(1.3); const rest = { r: g.resting, src: g.restFx.src, kp: kp.restOn, sp: g.restFx.sparksFrame, a: ring(), lit: g.restFx.rings.krada.lit };
            let tFull = 0; while (g.resting && tFull < 8) { g.simulate(1 / 60); tFull += 1 / 60; }
            let tEnd = 0; while (g.restFx.sparksFrame >= 0 && tEnd < 2) { g.simulate(1 / 60); tEnd += 1 / 60; }
            const after = { full: h.hp === h.maxHp, kp: kp.restOn, src: g.restFx.src, tEnd: +tEnd.toFixed(2) }; g.simulate(0.4); after.a = ring();
            h.hp = h.maxHp; return { sheets, lay, phase, ringPx, mid, border, outNear, far, early, rest, after }; })()''')
        ok = (len([k for k in s['sheets'] if not k.startswith(('k_', 'm_', 'a_'))]) == 13 and sorted(s['lay']) == [[6, 55], [10, 91]] and s['phase'] and s['ringPx']['R10'][0] > 300 and s['ringPx']['R6'][0] > 150
              and abs(s['ringPx']['R10'][1] - 128) <= 1 and s['mid']['a'] == 0 and s['mid']['src'] is None and s['mid']['sp'] == -1
              and s['border'] == {'a': 0.5, 'lit': False} and s['outNear'] == 0.5 and s['far'] == 0
              and not s['early']['r'] and s['early']['sp'] == -1 and not s['early']['kp']
              and s['rest']['r'] and s['rest']['src'] == 'krada' and s['rest']['kp'] and s['rest']['sp'] >= 0 and s['rest']['a'] == 0.5 and s['rest']['lit']
              and s['after']['full'] and not s['after']['kp'] and s['after']['src'] is None and 0 <= s['after']['tEnd'] <= 0.52 and s['after']['a'] == 0)
        check('эффекты отдыха (художник, правила дизайнера): крада/камень — покой и отдых в одной фазе, искры пока растут шкалы, кольцо рез 50% у границы или при отдыхе', ok, s)
        # GDD v1.7 п.6: F1–F6 в занятую ячейку — обмен; короткие имена; отказы в окне «Навыки» — тосты ui.skills.*
        s = await G('''(() => { const g = __game, h = g.hero, ui = g.ui; const keep = h.bar.slice(); h.bar = ['zmey', 'morozko', 'chur', null, null, null];
            ui.toggleSkills(true); ui.skills.hover = { skill: 'morozko' }; g.pressF(0); const bar = h.bar.slice(); ui.skills.hover = {}; ui.toggleSkills(false);
            const shorts = ['sshibka', 'chur', 'stat', 'secha', 'zmey', 'morozko', 'veshchee', 'skok'].map(id => g.dbg.short(id));
            h.bar = keep; return { bar, notice: g.notice && g.notice.text, shorts }; })()''')
        check('GDD v1.7: F-клавиша над навыком в занятую ячейку — навыки меняются местами; короткие имена (≤ 8) из act1_texts',
              s['bar'][:2] == ['morozko', 'zmey'] and s['shorts'] == ['Сшибка', 'Оберег', 'Стать', 'Сеча', 'Змей', 'Морозко', 'Слово', 'Скок'] and all(len(x) <= 8 for x in s['shorts']), s)
        s = await G('''(() => { const g = __game, h = g.hero, ui = g.ui, inp = g.input, sw = ui.skills; ui.toggleSkills(true); const L = sw.layout ? sw.layout() : null; const out = {};
            const click = (id) => { const pl = sw.L ? sw.L.plus[id] : null; return pl; };
            const tryLearn = (id) => { g.notice = null; const why = g.dbg.rankBlock(h, id); sw.computeHover = () => ({ plus: id }); inp.leftPressed = true; sw.handle(inp); inp.leftPressed = false; delete sw.computeHover; return [why, g.notice && g.notice.text]; };
            const keepSk = { ...h.skills }, keepLvl = h.level;
            out.skok = tryLearn('skok'); out.need = g.dbg.SKILLS.skok.req + (h.skills.skok || 0);
            h.level = 40; h.skills.morozko = 0; h.skills.skok = 0; out.prev = tryLearn('skok'); h.skills = keepSk; h.level = keepLvl;
            h.learn = () => 'points'; out.points = tryLearn('chur'); delete h.learn; h.recalc();
            ui.toggleSkills(false); return out; })()''')
        check('GDD v1.7: отказы в окне «Навыки» — короткие тосты (ui.skills.req_level / req_skill / no_points)',
              s['skok'][0] == 'level' and s['skok'][1] == f"Нужен {s['need']}-й уровень" and s['prev'] == ['prev', 'Сначала — Дыхание Морозко']
              and s['points'][1] == 'Нет очков навыков', s)
        # GDD v1.7 п.8: «Рывок» работает и с курсором над окном — к точке мира под курсором; окна не глотают клавиши
        await G(HOME)
        await G('(() => { const g = __game, h = g.hero; g.simulate(0.3); h.cds = {}; h.dashing = null; h.action = null; g.ui.toggleInv(true); })()')
        win = await G('(() => { const g = __game; for (let x = 600; x > 340; x -= 10) if (g.ui.over(x, 120)) return [x, 120]; return null; })()')
        if win:
            await pg.mouse.move(*(await client_scr(win[0], win[1])))
            await wait(80)
            d0 = await G('[__game.hero.x, __game.hero.y, __game.counters.casts.dash || 0, ...__game.toWorld(%d, %d)]' % (win[0], win[1]))
            await pg.keyboard.press('Space')
            for _ in range(40):
                if await G('(__game.counters.casts.dash || 0) > %d' % d0[2]):
                    break
                await wait(25)
            d1 = await G('(() => { const g = __game, h = g.hero; g.simulate(0.3); return [h.x, h.y, g.counters.casts.dash || 0, g.ui.anyOpen]; })()')
            vx, vy = d0[3] - d0[0], d0[4] - d0[1]; mx, my = d1[0] - d0[0], d1[1] - d0[1]
            cos = (vx * mx + vy * my) / (((vx * vx + vy * vy) ** 0.5) * ((mx * mx + my * my) ** 0.5) + 1e-9)
            s = {'win': win, 'dashes': d1[2] - d0[2], 'moved': round((mx * mx + my * my) ** 0.5, 2), 'cos': round(cos, 3), 'open': d1[3]}
        else:
            s = {'win': None}
        await G('__game.ui.toggleInv(false)')
        check('GDD v1.7: Пробел с курсором над окном — рывок к точке мира под курсором, окно остаётся открытым', bool(s.get('win')) and s['dashes'] == 1 and s['moved'] > 2 and s['cos'] > 0.95 and s['open'], s)
        await G(BACK)
        await G(UNFREEZE)

        # --- 11. Веха M1a: трекер «Огонь на капище», избы, Лесная тропа (переход зон), поджигатели, сундук, тело жреца
        SHOT_M1A = os.path.join(ROOT, 'screenshot_m1a.png')
        # миссия с чистого листа: в проверках выше в Залесье ставили тестового поджигателя (цель «Найди поджигателя» уже открыта)
        await G('(() => { const g = __game, h = g.hero; g.quest = new g.quest.constructor(g, "m1"); g._barks = {}; h.hp = h.maxHp; h.invuln = 0; h.cmd = null; h.action = null; g.state = "play"; g.ui.closeAll(); })()')
        s = await G('''(() => { const g = __game, d = g.dbg, q = g.quest; return { title: q.title, act: d.t('quest.act'), lines: q.lines().map(l => [l.text, l.count, l.state]),
            ru: ['quest.m1.obj.reach', 'quest.m1.obj.huts', 'quest.m1.obj.hearths'].map(k => d.t(k)), states: q.snapshot().map(o => o.id + ':' + o.state),
            img: !!(window.__assetsOk !== false), frame: d.UI_ATLAS.hud_quest, cfg: !!d.CFG.quests.m1 }; })()''')
        check('трекер: «Огонь на капище» / «Задание · Акт I», цели из data/quests.json, тексты из ru.json, не больше 3 строк',
              s['title'] == 'Огонь на капище' and s['act'] == 'Задание · Акт I' and [l[0] for l in s['lines']] == s['ru'] and len(s['lines']) == 3
              and s['lines'][1][1] == '0/3' and s['lines'][2][2] == 'locked' and 'arsonist:hidden' in s['states'] and s['cfg'] and s['frame']['w'] == 208, s)
        # выход на тропу закрыт, пока Мал не показал дорогу
        await G(FREEZE)
        # стая у выхода (role exit) стоит телами на дороге — перебиваем её
        ex = await G("(() => { const g = __game, o = g.objectById('to_trail'); for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - o.x, e.y - o.y) < 6) e.takeDamage(9999, g, 'melee', null); g.simulate(0.3); return [o.x, o.y]; })()")
        await G(TELEPORT + f'([{ex[0] - 1.2}, {ex[1] - 2.2}])')
        await G(f"(() => {{ const g = __game; g.hero.moveTo(g.map, {ex[0]}, {ex[1] + 0.2}); g.simulate(1.5); }})()")
        s = await G("({ zone: __game.zone.id, notice: __game.notice && __game.notice.text, d: Math.hypot(__game.hero.x - %s, __game.hero.y - %s) })" % (ex[0], ex[1]))
        check('выход на тропу закрыт до разговора с Малом: «Тропу покажет Мал…», герой остаётся в Залесье', s['zone'] == 'zalesye' and s['notice'] == 'Тропу покажет Мал. Он в избе у колодца.' and s['d'] > 1.2, s)
        # изба 1: настоящей мышью — навести, держать ЛКМ 2 с; урон прерывает
        o = await G('''(() => { const g = __game, o = g.objectById('hut1'), idx = g.map.packs.findIndex(p => p.role === 'izba1');
            const err0 = g.canInteract(o); for (const e of g.enemies) if (!e.dead && (e.pack === idx || Math.hypot(e.x - o.x, e.y - o.y) < 6)) e.takeDamage(9999, g, 'melee', null);
            return { x: o.x, y: o.y, sx: o.sx, sy: o.sy, err0, err1: g.canInteract(o) }; })()''')
        await G(TELEPORT + f"([{o['sx']}, {o['sy'] + 0.4}])")
        await wait(150)
        await pg.mouse.move(*(await client_of(o['x'], o['y'], 26)))
        await wait(120)
        hov = await G("(() => { const g = __game; return { id: g.hoverObj && g.hoverObj.id, label: g.hoverObj && g.objectLabel(g.hoverObj) }; })()")
        await pg.mouse.down()
        await wait(900)
        p1 = await G("(() => { const c = __game.hero.cmd; return c && c.type === 'interact' ? { started: c.started, t: +c.holdT.toFixed(2) } : null; })()")
        await G("__game.hero.takeDamage(1, __game, 'fire')")
        p2 = await G("({ cmd: __game.hero.cmd && __game.hero.cmd.type, notice: __game.notice && __game.notice.text, done: __game.objectById('hut1').done })")
        await pg.mouse.up(); await wait(100)
        await pg.mouse.down()
        await wait(2600)
        await pg.mouse.up(); await wait(100)
        p3 = await G("(() => { const g = __game; return { done: g.objectById('hut1').done, huts: g.quest.get('huts').n, npcs: g.npcs.map(n => n.name), ev: g.quest.events.filter(e => e.event === 'hutFreed').map(e => e.hut) }; })()")
        check('изба 1: дверь не выбить, пока жива стая; наведение — «Выбить дверь (держи ЛКМ)»; удержание ЛКМ 2 с, урон прерывает («Прервано!»)',
              o['err0'] == 'ui.obj.enemies_near' and o['err1'] is None and hov['id'] == 'hut1' and hov['label'] == 'Выбить дверь (держи ЛКМ)'
              and p1 and p1['started'] and p1['t'] > 0.2 and p2['cmd'] is None and p2['notice'] == 'Прервано!' and not p2['done'], (o, hov, p1, p2))
        check('изба 1 освобождена: «Спаси выживших» 1/3, селянка выбегает с репликой', p3['done'] and p3['huts'] == 1 and 'Селянка' in p3['npcs'] and p3['ev'] == ['hut1'], p3)
        # избы 2 и 3 (у колодца — Мал): цель 3/3, диалог Мала, тропа открыта
        s = await G('''(() => { const g = __game, h = g.hero, L = [], add0 = g.log.add; g.log.add = function (t, c) { L.push(t); return add0.call(this, t, c); };
            for (const id of ['hut2', 'hut3']) { const o = g.objectById(id), idx = g.map.packs.findIndex(p => p.role === o.pack);
              for (const e of g.enemies) if (!e.dead && (e.pack === idx || Math.hypot(e.x - o.x, e.y - o.y) < 6)) e.takeDamage(9999, g, 'melee', null);
              h.x = o.sx; h.y = o.sy + 0.3; h.cmd = null; g.autoHold = true; h.interact(o); g.simulate(4, () => o.done); g.autoHold = false; }
            g.simulate(9); g.log.add = add0; const q = g.quest;
            return { huts: q.get('huts').state + ' ' + q.get('huts').n, flag: q.flag('trailOpen'), mal: L.filter(t => t.startsWith('Мал:')), done: L.some(t => t.includes('Всех вывел')),
              lines: q.lines().map(l => [l.text, l.state, +l.alpha.toFixed(2)]) }; })()''')
        check('все 3 избы: цель выполнена («Всех вывел…»), Мал: «Они с капища шли!…» → тропа открыта (флаг trailOpen)',
              s['huts'] == 'done 3' and s['flag'] and len(s['mal']) == 2 and s['done'], s)
        # переход в Лесную тропу ногами через выход за колодцем
        await G(TELEPORT + f'([{ex[0] - 1.2}, {ex[1] - 2.2}])')
        await G(f"(() => {{ const g = __game; g.hero.moveTo(g.map, {ex[0]}, {ex[1] + 0.2}); g.simulate(3, () => g.zone.id === 'trail'); g.simulate(0.1); }})()")
        s = await G('''(() => { const g = __game, all = [...g.enemies, ...g.buried], cnt = (f) => all.filter(f).length, m = g.map, c = m.churStone;
            return { zone: g.zone.id, name: g.zone.name, size: [m.w, m.h], hero: [+g.hero.x.toFixed(1), +g.hero.y.toFixed(1)], m2: cnt(e => e.mlvl === 2), m3: cnt(e => e.mlvl === 3),
              mix2: ['upyr', 'anchutka'].map(k => cnt(e => e.mlvl === 2 && e.kind === k)), mix3: ['upyr', 'anchutka', 'chernoyarets_arsonist'].map(k => cnt(e => e.mlvl === 3 && e.kind === k)),
              ars: cnt(e => e.kind === 'chernoyarets_arsonist' && e.x < 50), buried: g.buried.length, safe: g.zone.safeZones.map(z => z.at + ':' + z.radius),
              pk: Math.min(...m.packs.map(p => Math.hypot(p.x - c.x, p.y - c.y))), notice: g.notice && g.notice.text, ev: g.quest.events.filter(e => e.event === 'zoneEnter').map(e => e.zone),
              reach: m.packs.every(p => m.isReachableAt(p.x, p.y)) && m.objects.every(o => m.isReachableAt(o.sx, o.sy)) }; })()''')
        check('Залесье → Лесная тропа (128×48): mlvl 2→3, 25 врагов mlvl 2 (упыри 16 / анчутки 9) + 45 mlvl 3 (20 / 14 / поджигатели 11), поджигатели ближе к капищу',
              s['zone'] == 'trail' and s['size'] == [128, 48] and s['m2'] == 25 and s['m3'] == 45 and s['mix2'] == [16, 9] and s['mix3'] == [20, 14, 11] and s['ars'] == 0
              and s['notice'] == 'Лесная тропа' and s['ev'][-1] == 'trail' and s['reach'], s)
        check('тропа: Чуров камень у ворот капища — тихий круг 6, стаи ≥ 8; волны упырей лежат под землёй', s['safe'] == ['churStone:6'] and s['pk'] >= 8 and s['buried'] == 16, s)
        # характеристики поджигателя и сопротивления огню
        s = await G('''(() => { const d = __game.dbg, M = d.CFG.monsters, a3 = d.enemyStats('chernoyarets_arsonist', 3), u3 = d.enemyStats('upyr', 3);
            return { a3, xpRatio: +(a3.xp / d.enemyStats('anchutka', 3).xp).toFixed(2), res: [M.chernoyarets_arsonist.res.fire, M.anchutka.res.fire, M.upyr.res.fire],
              t: M.chernoyarets_arsonist.torch, sp: M.chernoyarets_arsonist.speed, leash: M.chernoyarets_arsonist.leash, at: M.chernoyarets_arsonist.attackTime, u3hp: u3.hp }; })()''')
        check('поджигатель (E11): mlvl 3 — 36 HP, 4–9, скорость 3,0, удар 1,4 с, поводок 25; сопр. огню +25% (и у анчутки), у упыря −25%',
              (s['a3']['hp'], s['a3']['dmgMin'], s['a3']['dmgMax']) == (36, 4, 9) and s['sp'] == 3.0 and s['at'] == 1.4 and s['leash'] == 25 and s['res'] == [0.25, 0.25, -0.25], s)
        # «Поджог»: телеграф 0,8 с, зона Ø 2 тайла на 4 с, 5 огня/с на mlvl 3, на 1,5 тайла ближе к поджигателю, КД 8 с, одна зона, сам в огонь не заходит
        s = await G('''(() => { const g = __game, h = g.hero, m = g.map, P = m.packs.findIndex(p => p.kinds.every(k => k === 'chernoyarets_arsonist'));
            for (const e of g.enemies) e.stagger = 1e9; const a = g.enemies.find(e => e.pack === P && !e.dead); a.stagger = 0; a.torchCd = 0;
            const hx = a.x - 4; h.x = hx; h.y = m.yc(hx); h.cmd = null; h.path = null; h.action = null; h.recalc(); h.hp = h.maxHp; h.invuln = 0; a.x = h.x + 4; a.y = h.y; a.homeX = a.x; a.homeY = a.y;
            const out = { seen0: g.quest.get('arsonist').state };
            a.aggro(g, false); const t0 = g.counters.torches || 0; g.simulate(2, () => g.combat.fires.length > 0);
            const f = g.combat.fires[0]; if (!f) return { fail: 'no fire', out, st: a.state };
            out.fire = { tele: f.tele, r: f.r, burn: f.burn, dps: f.dps, closer: +(Math.hypot(h.x - a.x, h.y - a.y) - Math.hypot(f.x - a.x, f.y - a.y)).toFixed(2), cd: +a.torchCd.toFixed(1) };
            a.stagger = 1e9; h.x = f.x; h.y = f.y; h.hp = h.maxHp; const lit0 = f.lit; g.simulate(0.85); out.litAfterTele = f.lit && !lit0;
            const d0 = f.dealt || 0; g.simulate(2.0); out.dmg2s = (f.dealt || 0) - d0; out.ticks = f.ticks; out.heroRes = h.res.fire;
            g.simulate(2.3); out.burnedOut = !g.combat.fires.includes(f);
            // не заходит в огонь: зона между поджигателем и героем
            h.x = a.x - 4.5; h.y = a.y; h.hp = h.maxHp; a.stagger = 0; a.torchCd = 99; a.state = 'chase';
            const f2 = g.combat.throwTorch(a, a.x - 2, a.y); f2.t = f2.tele; let inside = 0; const dA0 = Math.hypot(a.x - h.x, a.y - h.y);
            g.simulate(2.5, () => { if (Math.hypot(a.x - f2.x, a.y - f2.y) < f2.r) inside++; return false; });
            out.enteredFire = inside; out.oneZone = g.combat.zonesOf(a); out.avoid = g.counters.fireAvoid || 0; out.closerBy = +(dA0 - Math.hypot(a.x - h.x, a.y - h.y)).toFixed(2);
            out.seen = g.quest.get('arsonist').state; out.barked = g._barks['bark.m1.arsonist'] != null;
            out.lines = g.quest.lines().map(l => l.text); g.combat.fires = []; for (const e of g.enemies) e.stagger = 1e9; h.hp = h.maxHp; return out; })()''')
        fr = s.get('fire') or {}
        check('«Поджог»: телеграф 0,8 с, зона Ø 2 тайла горит 4 с, 5 огня/с (mlvl 3), факел на 1,5 тайла ближе к поджигателю, КД 8 с',
              fr.get('tele') == 0.8 and fr.get('r') == 1.0 and fr.get('burn') == 4 and fr.get('dps') == 5 and abs(fr.get('closer', 0) - 1.5) < 0.05 and fr.get('cd', 0) > 7.5
              and s.get('litAfterTele') and s.get('burnedOut'), s)
        check('огонь жжёт героя в зоне (≈5/с с учётом сопротивления), поджигатель сам в огонь не заходит, одна зона на поджигателя',
              abs(s.get('dmg2s', 0) - 10 * (1 - s.get('heroRes', 0) / 100)) <= 2 and s.get('enteredFire') == 0 and s.get('oneZone') == 1, s)     # enteredFire=0 — главное; avoid/closerBy плавают, если путь вокруг огня не нашёлся
        check('первая встреча с поджигателем: реплика «Люди с факелами…» и цель «Найди поджигателя» в трекере',
              s.get('seen0') == 'hidden' and s.get('seen') == 'active' and s.get('barked') and 'Найди поджигателя' in s.get('lines', []), s)
        # волна: упыри встают из земли, когда герой подходит
        s = await G('''(() => { const g = __game, h = g.hero, m = g.map, i = m.packs.findIndex(p => p.ambush && !p.risen), p = m.packs[i];
            const b0 = g.buried.filter(e => e.pack === i).length; h.x = p.x - 4; h.y = m.yc(h.x); h.hp = h.maxHp; h.invuln = 99; g.simulate(0.2);
            const rising = g.enemies.filter(e => e.pack === i && e.state === 'rise').length; g.simulate(1.0);
            const out = { b0, rising, buried: g.buried.filter(e => e.pack === i).length, after: g.enemies.filter(e => e.pack === i).map(e => e.state) };
            for (const e of g.enemies) e.stagger = 1e9; h.invuln = 0; return out; })()''')
        check('волна: упыри поднимаются из земли (подъём 0,8 с), когда герой подходит', s['b0'] == 4 and s['rising'] == 4 and s['buried'] == 0 and all(x in ('chase', 'attack', 'idle', 'return') for x in s['after']), s)
        # сундук и тело жреца
        s = await G('''(() => { const g = __game, h = g.hero, c = g.objectById('trail_chest'), b = g.objectById('priest'); const out = {};
            const n0 = g.loot.items.length; h.x = c.sx; h.y = c.sy; h.cmd = null; h.interact(c); g.simulate(1.5, () => c.done);
            out.chest = { done: c.done, drops: (c.drops || []).map(d => d.item ? [d.item.type, d.item.rarity, d.item.ilvl] : [d.kind]), ev: g.quest.events.some(e => e.event === 'chestOpened'), notice: g.notice && g.notice.text };
            h.x = b.sx; h.y = b.sy; h.cmd = null; h.interact(b); g.simulate(1.5, () => b.done);
            out.body = { relics: h.relics.slice(), letters: h.letters.slice(), letter: g.letter && g.letter.name, ev: g.quest.events.filter(e => e.event === 'relicTaken' || e.event === 'letterRead').map(e => e.event) };
            return out; })()''')
        c0 = s['chest']['drops'][0] if s['chest']['drops'] else []
        check('кованый сундук: гарантированно заговорённое оружие ilvl 3 (меч или топор) + бросок по таблице, обучение котомке',
              s['chest']['done'] and c0[:1] in (['sword'], ['axe']) and c0[1] == 'magic' and c0[2] == 3 and len(s['chest']['drops']) == 2 and s['chest']['ev']
              and s['chest']['notice'] == 'I — котомка. Перетащи оружие в десницу.', s)
        check('тело жреца: заветное «Чёрный нож» и «Грамота жреца» (события relicTaken / letterRead)',
              s['body']['relics'] == ['knife'] and s['body']['letters'] == ['priest'] and s['body']['letter'] == 'Грамота жреца' and s['body']['ev'] == ['relicTaken', 'letterRead'], s)
        # ворота капища: цель «Доберись до капища», капище — следующая веха
        s = await G('''(() => { const g = __game, h = g.hero, o = g.objectById('kapishche_gate'); for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - o.x, e.y - o.y) < 14) e.takeDamage(9999, g, 'melee', null);
            h.x = o.x - 3.5; h.y = o.y; h.cmd = null; const safe = g.safeAt(h.x, h.y); h.moveTo(g.map, o.x, o.y); g.simulate(3, () => g.quest.get('reach').state === 'done');
            g.simulate(0.2); const out = { reach: g.quest.get('reach').state, zone: g.zone.id, churTouched: !!g.quest.flag('churTouched'), safe };
            g.enterZone('trail', 'gate'); out.back = g.zone.id; return out; })()''')
        check('ворота капища (веха M1b): «Доберись до капища» выполнена, ворота ведут в капище; у ворот тихий круг Чурова камня; мимо камня — не тронут',
              s['reach'] == 'done' and s['zone'] == 'kapishche' and s['safe'] and not s['churTouched'] and s['back'] == 'trail', s)
        # скриншот: тропа, трекер, поджигатели с факелами и анчутки, телеграф огня
        sc = await G('''(() => { const g = __game, h = g.hero, m = g.map; g.ui.closeAll(); g.letter = null; g.notice = null; g.log.lines.length = 0; h.cmd = null; h.path = null; h.action = null;
            const P = m.packs.findIndex(p => p.x > 76 && p.kinds.includes('chernoyarets_arsonist')); const p = m.packs[P];
            const x = p.x - 3.2; h.x = x; h.y = m.yc(x) + 0.4; h.hp = Math.round(h.maxHp * 0.8); h.face(1, 0); g.time += 20;
            const ars = g.enemies.filter(e => e.pack === P && !e.dead && e.def.torch); for (const e of g.enemies) { e.stagger = 1e9; e.moving = false; }
            for (const e of g.enemies.filter(e => e.pack === P || e.pack === P + 1)) { e.face(h.x - e.x, h.y - e.y); }
            if (ars[0]) { ars[0].state = 'torch'; ars[0].t = 0.4; const f = g.combat.throwTorch(ars[0], h.x + 1.3, h.y - 0.3); f.t = 0.5; }
            if (ars[1]) { const f = g.combat.throwTorch(ars[1], h.x + 0.8, h.y + 1.6); f.t = f.tele + 0.6; f.lit = true; f.litT = 0.6; }
            g.notice = null; g.updateCamera(); return [h.x + 2.5, h.y - 0.5]; })()''')
        await pg.mouse.move(*(await client_of(sc[0], sc[1], 20)))
        await wait(250)
        await pg.screenshot(path=SHOT_M1A)
        s = await G('''(() => { const g = __game, h = g.hero, near = g.enemies.filter(e => !e.dead && Math.abs(g.toS(e.x, e.y)[0] - 320) < 320 && g.toS(e.x, e.y)[1] > 0 && g.toS(e.x, e.y)[1] < 300);
            return { zone: g.zone.id, kinds: [...new Set(near.map(e => e.kind))].sort(), lines: g.quest.lines().length, fires: g.combat.fires.length }; })()''')
        check('скриншот screenshot_m1a.png: тропа, трекер, поджигатели и анчутки в кадре', os.path.exists(SHOT_M1A) and s['zone'] == 'trail' and 'chernoyarets_arsonist' in s['kinds'] and s['lines'] >= 2, s)
        await G('(() => { const g = __game; g.combat.fires = []; for (const e of g.enemies) e.stagger = 0; for (const e of g.enemies) e.stagger = 1e9; })()')
        # обратно в Залесье через западный выход; состояние тропы сохраняется
        s = await G('''(() => { const g = __game, h = g.hero, o = g.objectById('to_zalesye'); const dead = g.enemies.filter(e => e.dead).length + 0, alive = g.enemies.filter(e => !e.dead).length;
            h.x = o.x + 2.5; h.y = o.y; h.cmd = null; for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - h.x, e.y - h.y) < 10) e.takeDamage(9999, g, 'melee', null);
            const alive2 = g.enemies.filter(e => !e.dead).length; h.moveTo(g.map, o.x, o.y); g.simulate(3, () => g.zone.id === 'zalesye');
            const z1 = { zone: g.zone.id, hero: [+h.x.toFixed(1), +h.y.toFixed(1)], from: g.map.entries.from_trail, mlvl: g.zone.mlvl };
            const back = g.zoneStates.trail; const kept = back.enemies.filter(e => !e.dead).length;
            g.enterZone('trail', 'from_zalesye'); const z2 = { zone: g.zone.id, alive: g.enemies.filter(e => !e.dead).length, alive2, reach: g.quest.get('reach').state };
            g.enterZone('zalesye', 'from_trail'); for (const e of g.enemies) e.stagger = 0;
            return { z1, kept, alive2, z2 }; })()''')
        check('Лесная тропа → Залесье через западный выход (mlvl 1–2), при возвращении на тропу убитые остаются убитыми',
              s['z1']['zone'] == 'zalesye' and s['z1']['mlvl'] == [1, 2] and abs(s['z1']['hero'][0] - s['z1']['from']['x']) < 1.5 and s['kept'] == s['alive2'] and s['z2']['alive'] == s['alive2'], s)
        # гибель на тропе — возвращение у крады Залесья; GDD v1.7: убитые не возвращаются, раненые уходят к логову и лечатся
        s = await G('''(() => { const g = __game, h = g.hero; g.enterZone('trail', 'from_zalesye'); const m = g.map;
            const alive0 = g.enemies.filter(e => !e.dead).length, dead0 = g.enemies.filter(e => e.dead).length;
            const w = g.enemies.filter(e => !e.dead && e.def.torch === undefined)[0]; w.hp = Math.max(1, Math.floor(w.maxHp / 3)); w.stagger = 0; w.state = 'chase';
            // раненый — в 3 тайлах от логова, в свободной достижимой точке (раньше мог попасть в камень и застрять: тест плавал)
            const x0 = w.x, y0 = w.y; const off = [[3, 0], [-3, 0], [0, 3], [0, -3], [2.1, 2.1], [-2.1, -2.1], [2.1, -2.1], [-2.1, 2.1]].find(([dx, dy]) => m.isReachableAt(w.homeX + dx, w.homeY + dy) && !m.blockedAt(w.homeX + dx, w.homeY + dy)) || [3, 0];
            w.x = w.homeX + off[0]; w.y = w.homeY + off[1]; 
            h.invuln = 0; h.graceT = 0; h.dashing = null; h.takeDamage(99999, g, 'fire'); const st = g.state; g.respawnHero();
            const k = g.map.krada, out = { st, zone: g.zone.id, dk: +Math.hypot(h.x - k.x, h.y - k.y).toFixed(1), repop: !!g.zoneStates.trail.needRepop, hp: h.hp === h.maxHp,
              wState: w.state, alive0 };
            g.enterZone('trail', 'from_zalesye'); for (const e of g.enemies) if (e !== w) e.stagger = 1e9;
            g.simulate(12, () => w.state === 'idle' && w.hp === w.maxHp);
            out.alive1 = g.enemies.filter(e => !e.dead).length; out.buried = g.buried.length; out.wAfter = [w.state, w.hp, w.maxHp];
            g.enterZone('zalesye', 'krada', { respawn: true }); for (const e of g.enemies) e.stagger = 0; return out; })()''')
        check('GDD v1.7: гибель на тропе — возвращение у крады Залесья; убитые не возвращаются, раненый уходит к логову и восстанавливает HP',
              s['st'] == 'dead' and s['zone'] == 'zalesye' and s['dk'] < 5 and not s['repop'] and s['hp'] and s['wState'] == 'return'
              and s['alive1'] == s['alive0'] and s['wAfter'][0] == 'idle' and s['wAfter'][1] == s['wAfter'][2], s)

        # --- 12. Веха M1b: ответы дизайнера, Мара, вожаки, капище Перуна, Кривша (свежая загрузка; tools/checks_m1b.py)
        await run_m1b(pg, G, check, wait, client_of, client_scr, a)

        # --- 13. Веха M1c: береста возврата и Чуров проход, былинные вещи (свежая загрузка; tools/checks_m1c.py)
        await run_m1c(pg, G, check, wait, client_of, client_scr, a)

        check('консоль без ошибок и предупреждений', not errors, errors[:5])
        await br.close()

    bad = [r for r in results if not r[1]]
    print(f'\n{len(results) - len(bad)}/{len(results)} проверок пройдено')
    return 1 if bad else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8765/index.html?seed=7')
    ap.add_argument('--chrome', default='/usr/bin/google-chrome')
    ap.add_argument('--only-m1b', action='store_true', help='только проверки вехи M1b')
    ap.add_argument('--only-m1c', action='store_true', help='только проверки вехи M1c')
    ap.add_argument('--balance-v18', type=int, default=0, metavar='N', help='только замер §12.3 GDD v1.8: N боёв на сценарий (30 по GDD)')
    ap.add_argument('--throttle', type=float, default=1, help='замедление ЦП (CDP Emulation.setCPUThrottlingRate) — проверка на редких кадрах')
    sys.exit(asyncio.run(main(ap.parse_args())))

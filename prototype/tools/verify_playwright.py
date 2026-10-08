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
import argparse, asyncio, json, os, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SHOT_GAME = os.path.join(ROOT, 'screenshot_iter2_gameplay.png')
SHOT_INV = os.path.join(ROOT, 'screenshot_iter2_inventory.png')
SHOT_SKILLS = os.path.join(ROOT, 'screenshot_iter2_skills.png')

FREEZE = '(() => { for (const e of __game.enemies) { e.stagger = 1e9; e.moving = false; e.path = null; } })()'
UNFREEZE = '(() => { for (const e of __game.enemies) e.stagger = 0; })()'
TELEPORT = '''(([x, y]) => { const h = __game.hero; h.x = x; h.y = y; h.path = null; h.cmd = null; h.action = null; h.moving = false; h.kb = null; __game.updateCamera(); })'''


async def main(a):
    results, errors = [], []

    def check(name, ok, info=''):
        results.append((name, bool(ok), info))
        print(('OK   ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info else ''), flush=True)

    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path=a.chrome, args=['--autoplay-policy=no-user-gesture-required'])
        pg = await br.new_page(viewport={'width': 1920, 'height': 1080})
        pg.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        G = pg.evaluate

        async def client_of(x, y, lift=0):
            return await G(f'__game.clientOf({x}, {y}, {lift})')

        async def client_scr(sx, sy):
            return await G(f'__game.clientOfScreen({sx}, {sy})')

        async def wait(ms):
            await pg.wait_for_timeout(ms)

        await pg.goto(a.url)
        await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=15000)
        await pg.mouse.move(960, 540)
        await pg.mouse.click(960, 300)              # жест пользователя: разблокирует WebAudio (и шаг героя)
        await wait(200)

        # --- 1. баланс из JSON по GDD v1.2
        s = await G('''(() => { const g = __game, h = g.hero, d = g.dbg;
          return { cfg: Object.keys(d.CFG).sort(), hp: h.maxHp, yar: h.maxYar, regen: +h.yarRegen.toFixed(3), aps: h.attacksPerSec,
            xp: [1,2,3,10].map(d.xpToNext), up1: d.enemyStats('upyr', 1), an1: d.enemyStats('anchutka', 1), skill: [h.skillCost, h.skillRank],
            kit: Object.values(h.equip).filter(Boolean).map(i => i.name), belt: h.belt.map(b => b ? b.kind + 'x' + b.count : '-') }; })()''')
        check('конфиги data/*.json (+ uniques, ru) и data/zones/*.json загружены', s['cfg'] == sorted(['stats', 'skills', 'monsters', 'bosses', 'items_base', 'affixes', 'droptables', 'uniques', 'ru', 'zones']), s['cfg'])
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
        z = await G('''(() => { const g = __game, z = g.zone, m = g.map, n = g.enemies.length, k = m.krada, c = m.churStone;
            const m1 = g.enemies.filter(e => e.mlvl === 1).length, pk = m.packs.map(p => ({ dk: +Math.hypot(p.x - k.x, p.y - k.y).toFixed(1), dc: c ? +Math.hypot(p.x - c.x, p.y - c.y).toFixed(1) : 99, n: p.kinds.length,
              u: p.kinds.filter(x => x === 'upyr').length, a: p.kinds.filter(x => x === 'anchutka').length, mlvl: p.mlvl }));
            const near = pk.slice().sort((a, b) => a.dk - b.dk)[0];
            return { n, m1: +(m1 / n).toFixed(2), pk, near, safe: z.safeZones.map(s => s.at + ':' + s.radius), well: !!m.props.find(p => p.type === 'well'), stone: !!c }; })()''')
        sizesOk = all((p['mlvl'] == 1 and ((p['a'] == 0 and 3 <= p['u'] <= 4) or (p['u'] == 0 and 4 <= p['a'] <= 5))) or
                      (p['mlvl'] == 2 and ((p['a'] == 0 and p['u'] == 3) or (p['u'] == 0 and p['a'] == 4) or (p['u'] <= 3 and p['a'] <= 2))) for p in z['pk'])
        check('Залесье: ровно 18 mlvl 1 + 12 mlvl 2 (GDD v1.5), размеры стай по правилам, первая встреча — 3 упыря mlvl 1',
              z['n'] == 30 and z['m1'] == 0.6 and sizesOk and (z['near']['u'], z['near']['a'], z['near']['mlvl']) == (3, 0, 1), z)
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
        await pg.mouse.move(960, 200)
        await wait(400)
        for _ in range(40):                                   # ждём остановки (под нагрузкой кадры реже — время игры идёт медленнее)
            if not await G('__game.hero.moving || !!__game.hero.cmd'):
                break
            await wait(100)
        hx = await G('__game.hero.x')
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
        await G('__game.loot.spawnSilver(__game.hero.x + 1.2, __game.hero.y - 0.6, 7)'); await wait(80)
        n2 = await G('__game.labelRects.length')
        await pg.keyboard.press('KeyZ'); await wait(120)
        n3 = await G('__game.labelRects.length')
        await pg.keyboard.press('KeyZ'); await wait(120)
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
        ents = await G('__game.hero.inv.entries.map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h, base: e.item.base, kind: e.item.kind, uid: e.item.uid }))')

        def cell_center(e):
            return L['gx'] + (e['c'] + e['w'] / 2) * L['cell'], L['gy'] + (e['r'] + e['h'] / 2) * L['cell']

        def slot_center(name):
            x, y, w, h = L['slots'][name]
            return x + w / 2, y + h / 2

        axe = next(e for e in ents if e['base'] == 'axe_1')
        sword = next(e for e in ents if e['base'] == 'sword_2')
        ring = next(e for e in ents if e['base'] == 'ring_1')
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
        await wait(1800)
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
            if (g.safeAt(x, y, 5) || x < 4 || y < 4 || x > 44 || y > 44) continue;
            let good = true; for (let dx = -3; dx <= 3 && good; dx++) for (let dy = -3; dy <= 3; dy++) if (!ok(x + dx, y + dy)) { good = false; break; }
            if (!good) continue;
            const ed = Math.min(...g.enemies.filter(e => !e.dead).map(e => Math.hypot(e.x - x, e.y - y)));
            if (!best || ed > best[2]) best = [x, y, ed]; }
          return best ? [best[0], best[1]] : null; })()''')     # открытая площадка вне тихих кругов (стаи вокруг заморожены)
        A = [int(A[0] * 2) / 2 + 0.25, int(A[1] * 2) / 2 + 0.25]     # центр полутайла: путь начинается ровно от героя
        HOME = TELEPORT + f'([{A[0]}, {A[1]}])'
        await G('(() => { const g = __game, h = g.hero; h.invuln = 0; h.hp = h.maxHp; let n = 0; while (h.level < 6 && n++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g); })()')

        # 10.1 направление взгляда героя — 8 сторон по движению (настоящие щелчки мыши)
        got = {}
        for name, (dx, dy), want in [('вниз', (0, 56), 0), ('влево', (-96, 0), 2), ('вверх', (0, -56), 4), ('вправо', (96, 0), 6),
                                     ('вниз-вправо', (64, 32), 7), ('вверх-влево', (-64, -32), 3), ('вниз-влево', (-64, 32), 1), ('вверх-вправо', (64, -32), 5)]:
            await G(HOME); await wait(60)
            hx, hy = await client_of(A[0], A[1])
            await pg.mouse.click(hx + dx * 3, hy + dy * 3); await wait(160)
            got[name] = (await G('__game.hero.dir'), want)
        await G(HOME)
        check('герой смотрит туда, куда идёт (8 направлений: 0 — к камере, по часовой через «влево»)', all(a == b for a, b in got.values()), got)
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
        s = await G('''(() => { const g = __game, h = g.hero; h.yar = h.maxYar; const e = g.spawnTest('upyr', h.x + 0.95, h.y + 0.05, 1); e.stagger = 0;
            const r0 = Math.random; Math.random = () => 0.02; const x0 = e.x; h.useSkill(g, 'sshibka', e.x, e.y, e);
            g.simulate(0.8, () => g.lastBash && g.lastBash.target === e); Math.random = r0; g.simulate(0.3);
            const out = { moved: +(Math.hypot(e.x - h.x, e.y - h.y) - 0.95).toFixed(2), bash: !!g.lastBash, casts: g.counters.casts.sshibka || 0, hp: [e.hp, e.maxHp] };
            g.enemies = g.enemies.filter(o => o !== e); return out; })()''')
        check('«Сшибка»: удар с бонусом, отбрасывание ≈1 тайл', s['bash'] and s['moved'] >= 0.6 and s['hp'][0] < s['hp'][1], s)
        s = await G('''(() => { const g = __game, h = g.hero; h.yar = h.maxYar; const e = g.spawnTest('upyr', h.x + 3.5, h.y, 1); e.aggro(g, false);
            const r = h.useSkill(g, 'morozko', e.x, e.y, e); g.simulate(1.2, () => e.slowT > 0);
            const out = { r, slow: e.slowPct, t: +(e.slowT || 0).toFixed(2), spd: e.speed }; g.enemies = g.enemies.filter(o => o !== e); return out; })()''')
        check('«Дыхание Морозко»: попадание замедляет врага на 50%', s['r'] == 'ok' and s['slow'] == 50 and s['t'] > 1, s)
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
        await G(HOME); await wait(50)
        await pg.mouse.move(*(await client_of(A[0] + 3, A[1] - 3)))
        q0 = await G('[__game.hero.x, __game.hero.y]')
        await pg.keyboard.press('Space'); await wait(300)
        q1 = await G('[__game.hero.x, __game.hero.y, __game.hero.cdLeft("dash")]')
        await pg.keyboard.press('Space'); await wait(300)
        q2 = await G('[__game.hero.x, __game.hero.y, __game.counters.casts.dash]')
        check('рывок (Пробел): ≈3 тайла, повтор во время КД не срабатывает', 2.0 < ((q1[0] - q0[0]) ** 2 + (q1[1] - q0[1]) ** 2) ** 0.5 <= 3.05 and q1[2] > 3 and abs(q2[0] - q1[0]) < 0.01 and q2[2] == 1, (q0, q1, q2))

        # 10.5 QA: B-02 (ПКМ во время замаха не теряется), B-03 (смерть с летящим снарядом), фон большой карты
        await G(HOME)
        await pg.keyboard.press('F1'); await wait(50)
        e = await G('''(() => { const g = __game, h = g.hero; h.yar = h.maxYar; const e = g.spawnTest('upyr', h.x + 1.0, h.y + 0.1, 1); e.stagger = 1e9; return { id: e.id, x: e.x, y: e.y, h: e.def.height }; })()''')
        ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
        f0 = await G('__game.counters.bufferedFired || 0')
        await pg.mouse.click(ex, ey)
        sw = None
        for _ in range(80):                                        # ждём, пока до конца замаха останется ~0,2 с
            a_ = await G('(() => { const a = __game.hero.action; return a && a.type === "attack" ? [a.t, a.dur] : null; })()')
            if a_ and a_[1] - a_[0] <= 0.22:
                sw = a_
                break
            await wait(10)
        z0 = await G('__game.counters.casts.zmey || 0')
        await pg.mouse.click(ex, ey, button='right'); await wait(700)
        s = await G('({ b: __game.counters.buffered || 0, f: __game.counters.bufferedFired || 0, z: __game.counters.casts.zmey || 0 })')
        s['f0'] = f0; s['swing'] = sw
        check('B-02: ПКМ во время удара (окно 0,3 с) запоминается и срабатывает после замаха', s['f'] == f0 + 1 and s['z'] == z0 + 1, s)
        s = await G('''((id) => { const g = __game, h = g.hero; const e = g.enemies.find(o => o.id === id); h.action = null; h.cmd = null; h.yar = h.maxYar;
            e.x = h.x + 6; h.useSkill(g, 'zmey', e.x, e.y, e); g.simulate(0.45); const fl = g.combat.projectiles.filter(p => !p.hostile).length;
            const xp0 = h.xp; h.invuln = 0; h.dashing = null; h.takeDamage(99999, g, 'fire'); const after = g.combat.projectiles.filter(p => !p.hostile).length; h.gainXp(50, g);
            const out = { fl, after, xpSame: h.xp === xp0, st: g.state }; g.enemies = g.enemies.filter(o => o !== e); return out; })''', e['id'])
        check('B-03: после гибели снаряды героя исчезают, опыт мёртвому не начисляется', s['fl'] >= 1 and s['after'] == 0 and s['xpSame'] and s['st'] == 'dead', s)
        await wait(1700); await pg.keyboard.press('Enter'); await wait(200)
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
            h.x = k.x + 14; e.aggro(g, false); g.simulate(0.3); const chasing = e.state === 'chase';
            h.x = k.x + 8; const b0 = g.counters.safeBreaks || 0; g.simulate(0.4);
            const out = { noticed, chasing, after: e.state, breaks: (g.counters.safeBreaks || 0) - b0 };
            g.enemies = g.enemies.filter(o => o !== e); return out; })()''')
        check('B-16: упырь в 5,5 тайла от героя в тихом круге не замечает его; погоня обрывается, когда герой вбегает в круг',
              not s['noticed'] and s['chasing'] and s['after'] in ('return', 'idle') and s['breaks'] >= 1, s)
        s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; h.x = k.x + 0.5; h.y = k.y + 2; h.path = null; h.cmd = null; h.hp = h.maxHp; h.invuln = 0;
            for (const e of g.enemies) e.stagger = 0; const hp0 = h.hp; g.simulate(30); const out = { hp0, hp: h.hp, st: g.state,
            inside: g.enemies.filter(e => !e.dead && g.safeAt(e.x, e.y)).length }; for (const e of g.enemies) e.stagger = 1e9; return out; })()''')
        check('B-16: 30 с у крады без действий — героя никто не трогает, нечисти в тихом круге нет', s['hp'] == s['hp0'] and s['st'] == 'play' and s['inside'] == 0, s)

        # 10.8 B-15: ПКМ по зелью в котомке соблюдает КД зелий
        s = await G('''(() => { const g = __game, h = g.hero; h.belt = [{ kind: 'life1', count: 5 }, { kind: 'life1', count: 5 }, { kind: 'yar1', count: 5 }, { kind: 'yar1', count: 5 }];
            for (let i = 0; i < 5; i++) g.give('potion:life1'); h.hp = 5; h.potionCd = 0; h.effects = [];
            const ents = h.inv.entries.filter(e => e.item.kind === 'potion'); let drunk = 0;
            for (const e of ents) { const n = h.inv.items.length; g.ui.quickEquip(e); if (h.inv.items.length < n) drunk++; }
            const cd = h.potionCd; g.simulate(1.05); const e2 = h.inv.entries.find(e => e.item.kind === 'potion'); const n2 = h.inv.items.length; if (e2) g.ui.quickEquip(e2);
            return { drunk, cd, second: n2 - h.inv.items.length, left: h.inv.items.filter(i => i.kind === 'potion').length }; })()''')
        check('B-15: из котомки ПКМ — одно зелье за КД 1 с, следующее после КД', s['drunk'] == 1 and s['cd'] > 0.9 and s['second'] == 1, s)
        await G('(() => { const h = __game.hero; for (const it of h.inv.items.filter(i => i.kind === "potion")) h.inv.remove(it); })()')

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
          const clean = () => { g.enemies = g.enemies.filter(e => e.pack !== -1); g.combat.projectiles.length = 0; g.state = 'play'; g.deathT = 0; g.hitStopT = 0; };
          const mk = (L) => { const h = new Hero(A[0], A[1]); let n = 0; while (h.level < L && n++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g);
            h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar; h.belt = [null, null, null, null]; h.levelFx = 0; g.hero = h; return h; };
          const mean = (a) => +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2);
          const near = (h, es) => { let b = null, bd = 1e9; for (const e of es) { if (e.dead) continue; const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; b = e; } } return b; };
          const melee = (h, es, lmb, refill) => g.simulate(90, () => { if (refill) h.hp = h.maxHp; const t = near(h, es); if (!t || h.dead) return true;
              if (!h.cmd && !h.action) h.attack(t, false, lmb ? h.lmbSkill() : null, true); return false; });
          const res = {};
          for (const [key, lmb] of [['sshibka', true], ['plain', false]]) { const ts = [];
            for (let i = 0; i < 20; i++) { clean(); const h = mk(1); const e = g.spawnTest('upyr', A[0] + 1.0, A[1], 1); e.aggro(g, false); ts.push(melee(h, [e], lmb, true)); }
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
          for (const L of [3, 6, 10]) { const out = []; let hp = 0;
            for (let i = 0; i < 10; i++) { clean(); const h = mk(L); hp = h.maxHp;
              for (let j = 0; j < 3; j++) { const a = j * 2.094 + 0.3; const e = g.spawnTest('upyr', A[0] + Math.cos(a), A[1] + Math.sin(a), L); e.aggro(g, false); }
              out.push(g.simulate(120, () => h.dead)); }
            res['stand_L' + L] = { mean: mean(out), min: +Math.min(...out).toFixed(2), max: +Math.max(...out).toFixed(2), hp }; }
          clean(); g.hero = keep; keep.hp = keep.maxHp; return res; })()""" % json.dumps(A))
        print('БАЛАНС:', json.dumps(bal, ensure_ascii=False), flush=True)
        with open(os.path.join(ROOT, 'tools', 'balance_iter2.json'), 'w', encoding='utf-8') as f:
            json.dump(bal, f, ensure_ascii=False, indent=1)
        f1, f2 = bal['fight_L1_vs3upyr_m1'], bal['fight_L2_vs3upyr_m2']
        check('симуляция дизайнера: герой 1 ур. со «Сшибкой», без зелий, против 3 упырей mlvl 1 — 0 смертей из 30', f1['deaths'] == 0, f1)
        check('симуляция дизайнера: герой 2 ур. против 3 упырей mlvl 2 — не больше 5 смертей из 30', f2['deaths'] <= 5, f2)
        check('контрольная точка GDD v1.5 §9.3: всё Залесье даёт выход на 2-м уровне (±1)', 1 <= bal['zoneXp']['level'] <= 3, bal['zoneXp'])
        check('замеры TTK и выживания получены (tools/balance_iter2.json)', bal['ttk_sshibka']['mean'] > 0 and bal['stand_L3']['mean'] > 0, {k: bal[k]['mean'] for k in ('ttk_sshibka', 'ttk_plain', 'ttk_fire', 'stand_L3', 'stand_L6', 'stand_L10')})
        await G(UNFREEZE)

        check('консоль без ошибок и предупреждений', not errors, errors[:5])
        await br.close()

    bad = [r for r in results if not r[1]]
    print(f'\n{len(results) - len(bad)}/{len(results)} проверок пройдено')
    return 1 if bad else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8765/index.html?seed=7')
    ap.add_argument('--chrome', default='/usr/bin/google-chrome')
    sys.exit(asyncio.run(main(ap.parse_args())))

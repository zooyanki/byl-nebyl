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
        check('конфиги data/*.json и data/zones/zalesye.json загружены', s['cfg'] == sorted(['stats', 'skills', 'monsters', 'items_base', 'affixes', 'droptables', 'zones']), s['cfg'])
        check('герой 1 ур.: 70 жизни / 40 Яри, Ярь +1,5%/с', s['hp'] == 70 and s['yar'] == 40 and abs(s['regen'] - 0.6) < 1e-6, (s['hp'], s['yar'], s['regen']))
        check('скорость атаки скрамасакса 1,4 удара/с', abs(s['aps'] - 1.4) < 1e-6, s['aps'])
        check('кривая опыта 100·L^1,75', s['xp'] == [100, 340, 680, 5620], s['xp'])
        u, an = s['up1'], s['an1']
        check('упырь mlvl1: 22 HP, 2–6, 10 опыта; анчутка: 13 HP, 1–3, 5 опыта',
              (u['hp'], u['dmgMin'], u['dmgMax'], u['xp']) == (22, 2, 6, 10) and (an['hp'], an['dmgMin'], an['dmgMax'], an['xp']) == (13, 1, 3, 5), (u, an))
        check('«Огненный змей» стоит 5 Яри на ранге 1', s['skill'] == [5, 1], s['skill'])
        z = await G('''(() => { const g = __game, z = g.zone, n = g.enemies.length, u = g.enemies.filter(e => e.kind === 'upyr').length;
            return { n, u: u / n, mix: z.spawnMix, mlvl: [Math.min(...g.enemies.map(e => e.mlvl)), Math.max(...g.enemies.map(e => e.mlvl))], zm: z.mlvl }; })()''')
        check('Залесье: упыри 65% / анчутки 35%, mlvl 1–2', abs(z['u'] - z['mix']['upyr'] / 100) < 0.02 and z['mlvl'][0] >= z['zm'][0] and z['mlvl'][1] <= z['zm'][1], z)
        check('стартовый комплект и пояс по GDD', len(s['kit']) == 4 and s['belt'][:3] == ['life1x2', 'life1x1', 'yar1x2'], (s['kit'], s['belt']))

        # --- 2. полутайловая коллизия: тонкая стена в западной половине тайла (30, 24)
        await G(FREEZE)
        s = await G('''(() => { const g = __game, m = g.map, d = g.dbg;
          return { tileBlocked: m.isBlocked(30, 24), westHalf: m.blockedAt(30.25, 24.5), eastFree: d.circleFree(m, 30.85, 24.5, 0.3), deep: d.circleFree(m, 30.4, 24.5, 0.3) }; })()''')
        check('тайл (30,24) занят стеной лишь наполовину: центр героя проходит в 30,85', s['tileBlocked'] and s['westHalf'] and s['eastFree'] and not s['deep'], s)
        await G(TELEPORT + '([32.4, 24.5])')
        tx, ty = await client_of(30.6, 24.5)
        await pg.mouse.click(tx, ty)
        await pg.mouse.move(960, 200)
        await wait(1200)
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
            const hp0 = e.hp; h.tryCast(g, e.x, e.y); return { id: e.id, hp0 }; })()''')
        await wait(1500)
        r = await G('''((id) => { const g = __game, e = g.enemies.find(e => e.id === id), b = g.combat.lastBlast;
            return { hp: e.hp, blast: b && { x: +b.x.toFixed(2), hit: b.hit, blocked: b.blocked } }; })''', s['id'])
        check('взрыв у стены не задел упыря за ней (прямая видимость от центра)',
              r['blast'] and s['id'] in r['blast']['blocked'] and r['hp'] == s['hp0'] and r['blast']['x'] < 30.0, r)
        s2 = await G('''((id) => { const g = __game, h = g.hero, e = g.enemies.find(e => e.id === id);
            e.x = 29.0; e.y = 24.5; h.x = 26.0; h.y = 24.5; h.yar = h.maxYar; h.action = null; const hp0 = e.hp; h.tryCast(g, e.x, e.y); return hp0; })''', s['id'])
        await wait(1200)
        r = await G('((id) => { const g = __game, e = g.enemies.find(e => e.id === id); return { hp: e.hp, dead: e.dead, hit: g.combat.lastBlast.hit }; })', s['id'])
        check('тот же взрыв по открытой цели наносит урон', (r['hp'] < s2 or r['dead']) and s['id'] in r['hit'], r)
        s = await G('''((id) => { const g = __game, h = g.hero, e = g.enemies.find(e => e.id === id && !e.dead) || g.enemies.find(e => !e.dead && e.kind === 'upyr');
            e.stagger = 0; e.x = h.x + 1.0; e.y = h.y; const r0 = Math.random; Math.random = () => 0.01;
            const hs0 = g.counters.hitStop; g.combat.heroMelee(h, e); Math.random = r0;
            return { kb: !!e.kb || e.dead, hitStop: g.counters.hitStop - hs0, hst: g.hitStopT, id: e.id }; })''', s['id'])
        check('удар даёт хит-стоп 50 мс и отбрасывание', s['kb'] and s['hitStop'] == 1 and s['hst'] > 0.04, s)
        await G(UNFREEZE)

        # --- 5. анчутка кидает угли
        await G(TELEPORT + '([30.5, 30.5])')
        coal = False
        for _ in range(40):
            await wait(150)
            if await G('__game.combat.projectiles.some(p => p.hostile && p.coal) || (__game.audio.count.throw || 0) > 0'):
                coal = True
                break
        check('анчутка держит дистанцию и кидает угли', coal, await G('__game.audio.count.throw || 0'))

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
        await G('(() => { const g = __game; g.hero.hp = g.hero.maxHp; g.give("axe1", "magic", { affixes: [["P01", 30], ["S10", 10]] }); g.give("ring", "magic", { affixes: [["S01", 8]] }); g.give("sword_dr", "rare", { affixes: [["P01", 25], ["S02", 3]] }); g.give("potion:life1"); })()')
        await pg.keyboard.press('KeyI'); await wait(200)
        L = await G('__game.dbg.UI_ATLAS.inventory_layout')
        ents = await G('__game.hero.inv.entries.map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h, base: e.item.base, kind: e.item.kind, uid: e.item.uid }))')

        def cell_center(e):
            return L['gx'] + (e['c'] + e['w'] / 2) * L['cell'], L['gy'] + (e['r'] + e['h'] / 2) * L['cell']

        def slot_center(name):
            x, y, w, h = L['slots'][name]
            return x + w / 2, y + h / 2

        axe = next(e for e in ents if e['base'] == 'axe1')
        sword = next(e for e in ents if e['base'] == 'sword_dr')
        ring = next(e for e in ents if e['base'] == 'ring')
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
        check('щелчком надет топор: урон и скорость атаки пересчитаны', held == 'axe1' and after['r'] == 'axe1' and after['max'] != before['max'] and abs(after['aps'] - 1.21) < 0.01 and after['hand'] == 'scramasax', (before, after))
        # старый скрамасакс — обратно в котомку (в свободную клетку)
        await pg.mouse.click(*(await client_scr(L['gx'] + 8 * L['cell'] + 12, L['gy'] + 1 * L['cell'] + 12))); await wait(100)
        check('снятый предмет положен в сетку', not await G('__game.ui.hand') and await G('__game.hero.inv.items.some(i => i.base === "scramasax")'))
        # требование по уровню
        await pg.mouse.click(*(await client_scr(*cell_center(sword)))); await wait(100)
        await pg.mouse.click(*(await client_scr(*slot_center('rhand')))); await wait(100)
        s = await G('({ r: __game.hero.equip.rhand.base, hand: __game.ui.hand && __game.ui.hand.base, err: __game.audio.count.error || 0 })')
        check('меч 6-го уровня не надевается на 1-м (ошибка, предмет остаётся в руке)', s['r'] == 'axe1' and s['hand'] == 'sword_dr' and s['err'] >= 1, s)
        await pg.mouse.click(*(await client_scr(*cell_center(sword)))); await wait(100)
        # перетаскивание перстня в слот: +8 жизни
        hp0 = await G('__game.hero.maxHp')
        await pg.mouse.move(*(await client_scr(*cell_center(ring))))
        await pg.mouse.down(); await wait(50)
        sx, sy = slot_center('ring1')
        for k in range(1, 6):
            cx, cy = cell_center(ring)
            await pg.mouse.move(*(await client_scr(cx + (sx - cx) * k / 5, cy + (sy - cy) * k / 5))); await wait(16)
        await pg.mouse.up(); await wait(100)
        hp1 = await G('__game.hero.maxHp')
        check('перетаскиванием надет перстень «живота»: +8 к жизни', hp1 == hp0 + 8 and await G('__game.hero.equip.ring1 && __game.hero.equip.ring1.base') == 'ring', (hp0, hp1))
        # скриншот с тултипом на надетом или новом предмете (меч — со сравнением и требованием)
        sw = await G('__game.hero.inv.entries.filter(e => e.item.base === "sword_dr").map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h }))[0]')
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
        sw = await G('__game.hero.inv.entries.filter(e => e.item.base === "sword_dr").map(e => ({ c: e.c, r: e.r, w: e.item.w, h: e.item.h }))[0]')
        await pg.mouse.click(*(await client_scr(*cell_center(sw)))); await wait(100)
        await pg.mouse.click(*(await client_scr(120, 150))); await wait(100)
        check('предмет из котомки выброшен на землю', await G('__game.loot.items.length') == n0 + 1 and not await G('__game.hero.inv.items.some(i => i.base === "sword_dr")'))
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
        need = ['hit', 'skill', 'levelup', 'death', 'respawn', 'equip', 'explode', 'throw']
        check('звуки-заглушки срабатывают: ' + ', '.join(need), all(c.get(k, 0) > 0 for k in need), c)
        await pg.keyboard.press('KeyN'); await wait(50)
        m1 = await G('__game.audio.muted')
        await pg.keyboard.press('KeyN'); await wait(50)
        check('N выключает и включает звук', m1 and not await G('__game.audio.muted'))
        await wait(300)

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

"""Автопроверка прототипа в headless Chromium (Playwright).

  python3 -m http.server 8765 &        # из папки prototype
  python3 tools/verify_playwright.py [--url http://127.0.0.1:8765/index.html?seed=7] [--chrome /usr/bin/google-chrome]

Сценарий: загрузка без ошибок консоли -> клик-движение -> атака ЛКМ -> ПКМ «Перунов огонь» ->
клавиша 1 (зелье) -> бой до выпадения добычи -> подбор по подписи -> скриншот 1920x1080
(screenshot_iter1.png) -> смерть и рестарт. Код выхода 1, если что-то не так.
"""
import argparse, asyncio, json, os, sys
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'screenshot_iter1.png')


NEAREST = '''((kind) => { const g = __game, h = g.hero; let b = null, bd = 1e9;
    for (const e of g.enemies) { if (e.dead || (kind && e.kind !== kind)) continue; const d = Math.hypot(e.x-h.x, e.y-h.y); if (d < bd) { bd = d; b = e; } }
    return b ? { x: b.x, y: b.y, d: bd, h: b.def.height, kind: b.kind } : null; })'''


async def scene(pg, url, G, client_of, state):
    """Бьём стаю анчуток у старта, затем отходим к упырям: герой в центре, упыри подходят,
    летит «Перунов огонь», рядом лежит добыча с подписями."""
    await pg.goto(url)
    await pg.wait_for_function('window.__game && window.__game.time > 0.3')
    await pg.mouse.move(5, 5)
    for _ in range(120):
        s = await state()
        if s['kills'] >= 3 or s['dead']:
            break
        if s['hp'] < s['maxHp'] * 0.5:
            await pg.keyboard.press('Digit1' if s['belt'][0] != '-' else 'Digit2')
        e = await G(NEAREST + '("anchutka")')
        if not e or e['d'] > 10:
            break
        ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
        await pg.mouse.move(ex, ey); await pg.mouse.down(); await pg.wait_for_timeout(250); await pg.mouse.up()
        await pg.wait_for_timeout(120)
    await pg.wait_for_timeout(600)
    labels = await G('__game.labelRects.length')
    s = await state()
    if s['dead'] or labels < 2 or s['lvl'] > 1:
        return False, {'labels': labels, 'kills': s['kills']}
    await pg.wait_for_function('__game.time > 14.2', timeout=30000)  # стартовая подсказка погасла
    # отходим к стае упырей (их логово около (17.5, 29.5)); добыча остаётся лежать позади
    for _ in range(25):
        s = await state()
        if abs(s['x'] - 22.6) + abs(s['y'] - 29.2) < 1.0:
            break
        tx, ty = await client_of(22.6, 29.2)
        await pg.mouse.click(tx, ty)
        await pg.mouse.move(5, 5)
        await pg.wait_for_timeout(400)
    for _ in range(50):
        await pg.wait_for_timeout(200)
        e = await G(NEAREST + '("upyr")')
        if e and e['d'] < 3.9:
            break
    e = await G(NEAREST + '(null)')
    if not e:
        return False, {'reason': 'no enemy'}
    ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
    await pg.mouse.click(ex, ey, button='right')
    await pg.wait_for_timeout(330)
    e = await G(NEAREST + '(null)')
    ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
    await pg.mouse.move(ex + 4, ey)
    await pg.wait_for_timeout(40)
    labels = await G('__game.labelRects.map(r => r.item.label)')
    proj = await G('__game.combat.projectiles.length')
    return len(labels) >= 2, {'labels': labels, 'projectiles': proj, 'nearest': e}


async def main(a):
    problems, log = [], []
    async with async_playwright() as p:
        kw = {'args': ['--no-sandbox']}
        if a.chrome:
            kw['executable_path'] = a.chrome
        b = await p.chromium.launch(**kw)
        pg = await b.new_page(viewport={'width': 1920, 'height': 1080})
        errors = []
        pg.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        await pg.goto(a.url)
        await pg.wait_for_function('window.__game && window.__game.time > 0.3')

        G = lambda js: pg.evaluate(js)
        state = lambda: G('''(() => { const g = __game, h = g.hero; return {
            x: h.x, y: h.y, hp: h.hp, maxHp: h.maxHp, yar: h.yar, lvl: h.level, xp: h.xp, silver: h.silver,
            bag: h.bag.length, belt: h.belt.map(b => b ? b.kind + b.count : '-'), kills: g.killsTotal,
            items: g.loot.items.length, proj: g.combat.projectiles.length, state: g.state, dead: h.dead,
            alive: g.enemies.filter(e => !e.dead).length }; })()''')

        async def client_of(x, y, lift=0):
            return await G(f'__game.clientOf({x}, {y}, {lift})')

        s0 = await state(); log.append(('start', s0))
        # 1) клик-движение с обходом препятствия: цель за каменной стенкой (x=30, y=22..27)
        cx, cy = await client_of(32.5, 24.5)
        await pg.mouse.click(cx, cy)
        await pg.wait_for_timeout(3500)
        s1 = await state(); log.append(('click-move around wall -> (32.5,24.5)', s1))
        if abs(s1['x'] - 32.5) + abs(s1['y'] - 24.5) > 1.0:
            problems.append('клик-движение / обход стены не сработал')

        # 2) движение с зажатой ЛКМ: зажали, повели мышь, отпустили
        ax, ay = await client_of(s1['x'] - 2, s1['y'] + 2)
        await pg.mouse.move(ax, ay); await pg.mouse.down()
        for i in range(8):
            await pg.mouse.move(ax - 20 * i, ay + 6 * i)
            await pg.wait_for_timeout(120)
        await pg.mouse.up()
        await pg.wait_for_timeout(500)
        s2 = await state(); log.append(('hold-LMB move', s2))
        if abs(s2['x'] - s1['x']) + abs(s2['y'] - s1['y']) < 1.5:
            problems.append('движение с зажатой ЛКМ не сработало')

        # 3) бой: ЛКМ по ближайшему врагу, ПКМ «Перунов огонь», зелья по 1/2
        nearest = '''(() => { const g = __game, h = g.hero; let b = null, bd = 1e9;
            for (const e of g.enemies) { if (e.dead) continue; const d = Math.hypot(e.x-h.x, e.y-h.y); if (d < bd) { bd = d; b = e; } }
            return b ? { x: b.x, y: b.y, d: bd, h: b.def.height, name: b.name } : null; })()'''
        used_rmb = False
        yar_before_rmb = None
        for step in range(260):
            s = await state()
            if s['dead']:
                problems.append('герой погиб в автобою'); break
            if s['hp'] < s['maxHp'] * 0.45:
                await pg.keyboard.press('Digit1' if s['belt'][0] != '-' else 'Digit2')
            e = await G(nearest)
            if not e:
                break
            labels_n = await G('__game.labelRects.length')
            if s['kills'] >= 3 and labels_n >= 2 and e['d'] < 4.5:
                break
            if s['kills'] >= 10:
                break
            ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
            if e['d'] < 7 and s['yar'] >= 6 and (not used_rmb or step % 7 == 0):
                if not used_rmb:
                    yar_before_rmb = s['yar']
                await pg.mouse.click(ex, ey, button='right')
                if not used_rmb:
                    await pg.wait_for_timeout(250)
                    sr = await state(); log.append(('RMB cast', {'yar_before': yar_before_rmb, 'yar_after': sr['yar'], 'projectiles': sr['proj']}))
                    if sr['yar'] > yar_before_rmb - 5:
                        problems.append('ПКМ не потратил ярь')
                used_rmb = True
                await pg.wait_for_timeout(300)
                continue
            await pg.mouse.move(ex, ey)
            await pg.mouse.down(); await pg.wait_for_timeout(250); await pg.mouse.up()
            await pg.wait_for_timeout(150)
        s3 = await state(); log.append(('after fight', s3))
        if s3['kills'] < 1:
            problems.append('никого не убили')
        if s3['xp'] == 0 and s3['lvl'] == 1:
            problems.append('опыт не начислен')
        if not used_rmb:
            problems.append('ПКМ не использован')

        # 4) скриншот геймплея: ПКМ по ближайшему, курсор наведён на врага (полоса цели вверху)
        e = await G(nearest)
        if e:
            ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
            await pg.mouse.click(ex, ey, button='right')
            await pg.wait_for_timeout(170)
            e = await G(nearest)
            ex, ey = await client_of(e['x'], e['y'], e['h'] / 2)
            await pg.mouse.move(ex, ey)
        await pg.wait_for_timeout(60)
        await pg.screenshot(path='/tmp/proto_fight.png')
        log.append(('fight screenshot (/tmp/proto_fight.png)', await state()))

        # 5) зелье на клавишу 1
        await G('__game.enemies.forEach(e => { if (!e.dead) { e.state = "return"; e.path = null; } }); __game.hero.hp = 20')
        belt_before = (await state())['belt']
        await pg.keyboard.press('Digit1' if belt_before[0] != '-' else 'Digit2')
        await pg.wait_for_timeout(1700)
        sp = await state(); log.append(('potion key', {'hp_before': 20, 'hp_after': round(sp['hp'], 1), 'belt_before': belt_before, 'belt_after': sp['belt']}))
        if sp['hp'] < 35:
            problems.append('зелье жизни не лечит')

        # 6) подбор добычи щелчком по подписи
        labels = await G('__game.labelRects.map(r => ({x: r.x + r.w/2, y: r.y + r.h/2, label: r.item.label}))')
        log.append(('labels', [l['label'] for l in labels]))
        if labels:
            before = await state()
            L = labels[0]
            r = await G('(() => { const r = __game.canvas.getBoundingClientRect(); return [r.left, r.top, r.width / 640]; })()')
            await pg.mouse.click(r[0] + L['x'] * r[2], r[1] + L['y'] * r[2])
            await pg.wait_for_timeout(3000)
            after = await state()
            log.append(('pickup', {'label': L['label'], 'items_before': before['items'], 'items_after': after['items'],
                                    'silver': after['silver'], 'bag': after['bag'], 'belt': after['belt']}))
            if after['items'] >= before['items']:
                problems.append('подбор по подписи не сработал')
        else:
            problems.append('нет подписей добычи на земле')

        # 5) смерть и рестарт
        await G('__game.hero.takeDamage(99999, __game)')
        await pg.wait_for_timeout(2200)
        await pg.screenshot(path='/tmp/proto_death.png')
        if (await state())['state'] != 'dead':
            problems.append('экран смерти не показан')
        await pg.keyboard.press('Enter')
        await pg.wait_for_timeout(400)
        s5 = await state(); log.append(('after restart', s5))
        if s5['dead'] or s5['state'] != 'play' or s5['kills'] != 0:
            problems.append('рестарт не сработал')

        # 7) постановочный кадр для screenshot_iter1.png (честная игра, другой сид при неудаче)
        base = a.url.split('?')[0]
        for seed in range(1, 15):
            ok, info = await scene(pg, f'{base}?seed={seed}', G, client_of, state)
            log.append((f'scene seed={seed}', info))
            if ok:
                break
        await pg.screenshot(path=OUT)
        log.append(('screenshot_iter1', await state()))

        for k, v in log:
            print(k, json.dumps(v, ensure_ascii=False))
        print('console:', errors or 'чисто')
        if errors:
            problems.append('ошибки в консоли')
        await b.close()
    print('ПРОБЛЕМЫ:' if problems else 'OK', problems)
    return 1 if problems else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8765/index.html?seed=7')
    ap.add_argument('--chrome', default=None, help='путь к Chrome/Chromium (если не ставили браузер Playwright)')
    sys.exit(asyncio.run(main(ap.parse_args())))

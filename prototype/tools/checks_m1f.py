# Веха m1f: замечания критиков m1e (inbox/critics_m1f.md) — P0 (1–4) и P1 (5–10). Только миссия 1.
import os

ROOT = '/workspace/game/prototype/'
SHOT_DOOR = ROOT + 'screenshot_m1f_door.png'
SHOT_LOG = ROOT + 'screenshot_m1f_log.png'
SHOT_TREES = ROOT + 'screenshot_m1f_trees.png'

FRESH = '''(() => { const g = __game; g.ui.closeAll(); delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada');
  g.enemies = g.enemies.filter(e => !e.special); const h = g.hero; h.hp = h.maxHp; h.yar = h.maxYar; h.invuln = 0; h.cmd = null; h.action = null; g.state = 'play'; })()'''


async def run_m1f(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1f', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')
    await pg.mouse.click(960, 300)
    await wait(150)

    # ---------- P0.1 дверь Мала: раскладка
    await G(FRESH)
    s = await G('''(() => { const g = __game, m = g.map, o = g.objectById('hut3'), c = m.churStone, W = m.well || null;
        const idx = m.packs.findIndex(p => p.role === 'izba3'), pk = g.enemies.filter(e => e.pack === idx);
        const patch = []; for (let y = Math.floor(o.y) - 1; y <= Math.floor(o.y) + 1; y++) for (let x = Math.floor(o.x); x <= Math.floor(o.x) + 2; x++) patch.push(m.isBlocked(x, y) ? 1 : 0);
        const props = m.props.filter(p => p.type !== 'izba' && p.fp[0] < o.x + 3 && p.fp[0] + p.fp[2] > o.x && p.fp[1] < o.y + 1.5 && p.fp[1] + p.fp[3] > o.y - 1.5).length;
        const izba = m.props.find(p => p.type === 'izba' && p.door === '+x');
        const wl = g.zone.landmarks.well, wc = [wl.x + 1, wl.y + 1];
        const x0 = Math.floor(o.x), x1 = wl.x + 2, y0 = Math.min(Math.floor(o.y), wl.y) - 1, y1 = Math.max(Math.floor(o.y), wl.y + 2) + 1;
        const glade = m.props.filter(p => p.type === 'tree' && p.fp[0] + p.fp[2] > x0 && p.fp[0] < x1 && p.fp[1] + p.fp[3] > y0 && p.fp[1] < y1).length;
        return { glade, door: o.door, xy: [o.x, o.y], s: [o.sx, o.sy], out: o.out, reach: m.isReachableAt(o.sx, o.sy), patch, props, izba: !!izba,
          dWell: +Math.hypot(o.x - wc[0], o.y - wc[1]).toFixed(2), safe: g.safeAt(o.sx, o.sy), dChur: +Math.hypot(o.sx - c.x, o.sy - c.y).toFixed(2),
          pk: pk.length, pkKinds: m.packs[idx].kinds.length, pkReach: pk.every(e => m.isReachableAt(e.x, e.y)), pkSafe: pk.some(e => g.safeAt(e.x, e.y)) }; })()''')
    check('m1f P0.1 изба Мала повёрнута дверью к колодцу (+X), поляна 3×3 перед дверью свободна, точка у двери в тихом круге Чурова камня, между дверью и колодцем деревьев нет, до колодца ≤ 10 тайлов',
          s['door'] == '+x' and s['izba'] and s['reach'] and sum(s['patch']) == 0 and s['props'] == 0 and s['dWell'] <= 10 and s['safe'] and s['glade'] == 0
          and s['out'][0] > s['xy'][0], s)
    check('m1f P0.1 стая izba3 встаёт целиком (3 из 3) на открытом месте, все достижимы, никто в тихом круге',
          s['pk'] == s['pkKinds'] == 3 and s['pkReach'] and not s['pkSafe'], s)

    # ---------- P0.1 бот открывает дверь: от колодца перебивает стаю избы и выбивает дверь (остальные враги живы)
    s = await G('''(() => { const g = __game, h = g.hero, m = g.map, o = g.objectById('hut3'), wl = g.zone.landmarks.well;
        h.x = wl.x + 1; h.y = wl.y + 2.6; h.stop(); h.invuln = 1e9; const idx = m.packs.findIndex(p => p.role === 'izba3');
        const others0 = g.enemies.filter(e => !e.dead && e.pack !== idx).length;
        let phase = 'fight', t = 0, hits = 0; const td = h.takeDamage.bind(h);
        h.takeDamage = (...a) => { hits++; const r = td(...a); h.hp = h.maxHp; return r; };
        g.simulate(90, () => { t += 1 / 60;
          const pk = g.enemies.filter(e => !e.dead && e.pack === idx);
          if (pk.length) { if (!h.cmd || h.cmd.type !== 'attack' || h.cmd.target.dead) { const e = pk.sort((a, b) => Math.hypot(a.x - h.x, a.y - h.y) - Math.hypot(b.x - h.x, b.y - h.y))[0]; h.attack(e, false, null, true); } if (h.cmd) h.cmd.repeat = true; return false; }
          if (phase === 'fight') { phase = 'door'; g.autoHold = true; h.interact(o); }
          if (!h.cmd && !o.done) h.interact(o);
          return o.done; });
        g.autoHold = false; h.takeDamage = td; h.invuln = 0;
        const mal = g.npcs.find(n => n.kind === 'mal');
        return { done: o.done, t: +t.toFixed(1), phase, hits, mal: mal ? [+mal.x.toFixed(2), +mal.y.toFixed(2)] : null, out: o.out, q: g.quest.get('mal').state,
          others: g.enemies.filter(e => !e.dead && e.pack !== idx).length, others0, err: g.canInteract(o) }; })()''')
    check('m1f P0.1 бот от колодца перебивает стаю избы и выбивает дверь Мала; Мал выходит к колодцу (o.out); цель «Вызволи Мала» выполнена',
          s['done'] and s['mal'] and abs(s['mal'][0] - s['out'][0]) < 0.8 and s['q'] == 'done', s)

    # ---------- P0.1 удар приостанавливает удержание, не сбрасывает
    await G(FRESH)
    s = await G('''(() => { const g = __game, h = g.hero, m = g.map, o = g.objectById('hut1'), idx = m.packs.findIndex(p => p.role === o.pack);
        for (const e of g.enemies) if (!e.dead && (e.pack === idx || Math.hypot(e.x - o.x, e.y - o.y) < 6)) e.takeDamage(9999, g, 'melee', null);
        h.x = o.sx; h.y = o.sy; h.stop(); g.autoHold = true; h.interact(o); g.simulate(1.0);
        const t1 = h.cmd && h.cmd.holdT; h.invuln = 0; h.graceT = 0; h.takeDamage(1, g, 'fire', null);
        const after = { cmd: h.cmd && h.cmd.type, t: h.cmd && h.cmd.holdT, pause: h.cmd && h.cmd.holdPause, notice: g.notice && g.notice.text };
        g.simulate(0.1); const t2 = h.cmd && h.cmd.holdT;
        let tt = 0; g.simulate(3, () => { tt += 1 / 60; return o.done; }); g.autoHold = false;
        return { t1: +t1.toFixed(2), after, t2: +(t2 || 0).toFixed(2), done: o.done, rest: +tt.toFixed(2) }; })()''')
    check('m1f P0.1 удар во время «выбить дверь» — «Прервано!», прогресс удержания сохраняется (пауза), дверь выбивается без начала заново',
          s['after']['cmd'] == 'interact' and abs(s['after']['t'] - s['t1']) < 1e-6 and s['after']['pause'] > 0 and s['after']['notice'] == 'Прервано!'
          and s['done'] and s['rest'] < 1.5, s)

    # ---------- P0.2 трекер и метки цели
    await G(FRESH)
    s = await G('''(() => { const g = __game, q = new g.quest.constructor(g, 'm1'); g.quest = q;
        return { lines: q.lines().map(l => l.text), st: q.get('mal').state, want: g.dbg.t('quest.m1.obj.mal') }; })()''')
    await wait(200)
    s['marks'] = await G("(__game.goalMarks || []).map(m => m.id)")
    lad = await G("(() => { const g = __game; g.enterZone('ladoga', 'from_zalesye'); return g.zone.id; })()")
    await wait(200)
    s['lad'] = await G("(__game.goalMarks || []).map(m => m.id)")
    await G("(() => { const g = __game; g.enterZone('zalesye', 'krada'); })()")
    check('m1f P0.2 трекер: первая строка — quest.m1.obj.mal (m1g: «Вызволи Мала у колодца», строка сценариста); метка цели — дверь избы 3 в Залесье, восточные ворота в Ладоге',
          s['lines'][0] == s['want'] == 'Вызволи Мала у колодца' and s['st'] == 'active' and 'hut3' in s['marks'] and lad == 'ladoga' and 'to_zalesye' in s['lad'], s)

    # ---------- P0.1 скриншот: герой у колодца, дверь в кадре и подсвечена
    await G(FRESH)
    s = await G('''(() => { const g = __game, h = g.hero, wl = g.zone.landmarks.well, o = g.objectById('hut3');
        h.x = wl.x - 1.6; h.y = wl.y + 3.0; h.stop(); h.face(o.x - h.x, o.y - h.y); g.log.lines = []; g.notice = null; return [o.x, o.y]; })()''')
    # кадр: герой у колодца смещён вправо (как при открытой левой панели) — изба слева не уходит под трекер
    await G("(() => { const g = __game; g._ucam = g.updateCamera; g.updateCamera = function () { g._ucam.call(g); g.camCX = 470; }; })()")
    await pg.mouse.move(1500, 900)
    await wait(600)
    door = await G(f"(() => {{ const g = __game, [x, y] = g.clientOf({s[0]}, {s[1]}, 30); return {{ x, y, hi: g.doorHi, hero: g.clientOf(g.hero.x, g.hero.y, 0) }}; }})()")
    door['occl'] = await G('''(() => { const g = __game, m = g.map, o = g.objectById('hut3'), h = g.hero, hz = g.zone.landmarks.hut3;
        // деревья, чьи кроны по экрану между героем у колодца и фасадом избы (глубже избы)
        const S = (x, y) => g.toS(x, y), A = S(hz.x, hz.y + 4), B = S(hz.x + 4, hz.y), H = S(h.x, h.y);
        const x0 = Math.min(A[0], B[0], H[0]), x1 = Math.max(A[0], B[0], H[0]), y0 = S(hz.x, hz.y)[1] - 112, y1 = Math.max(A[1], B[1], H[1]);
        return m.props.filter(p => p.type === 'tree' && p.fp[0] + p.fp[2] / 2 + p.fp[1] + p.fp[3] / 2 > hz.x + hz.y && (() => { const [sx, sy] = S(p.fp[0] + p.fp[2] / 2, p.fp[1] + p.fp[3] / 2), hh = p.birch ? 132 : 166;
          return sx + 20 > x0 && sx - 20 < x1 && sy - 20 > y0 && sy - hh < y1; })()).length; })()''')
    await pg.screenshot(path=SHOT_DOOR)
    await G("(() => { const g = __game; g.updateCamera = g._ucam; delete g._ucam; })()")
    check('m1f P0.1 скриншот screenshot_m1f_door.png: герой у колодца, дверь и фасад избы Мала в кадре без деревьев между ними, дверь подсвечена',
          os.path.exists(SHOT_DOOR) and door['hi'] >= 1 and 640 < door['x'] < 1920 and 0 < door['y'] < 1080 and door['occl'] == 0, door)

    # ---------- P0.3 враг под кроной: кроны растворяются, силуэт поверх, курсор наводится
    await G(FRESH)
    s = await G('''(() => { const g = __game, m = g.map, h = g.hero;
        // берёзу/ель внутри поля: враг ровно за кроной (глубже по экрану, но ниже кроны), герой в 5 тайлах
        const tr = m.props.filter(p => p.type === 'tree' && p.fp[2] < 1 && p.x > 10 && p.x < 40 && p.y > 12 && p.y < 36)
          .find(p => m.isReachableAt(p.x + 0.25 - 3.5, p.y + 0.25 - 3.5) && m.isReachableAt(p.x + 3, p.y + 3) && !m.props.some(q => q !== p && q.type === 'tree' && Math.abs((q.x - q.y) - (p.x - p.y)) < 3 && q.x + q.y > p.x + p.y - 9 && q.x + q.y < p.x + p.y + 12));
        const e = g.enemies.find(e => e.kind === 'upyr' && !e.special);
        g.enemies = [e]; e.x = tr.x + 0.25 - 3.5; e.y = tr.y + 0.25 - 3.5; e.homeX = e.x; e.homeY = e.y; e.stagger = 1e9; e.state = 'chase'; e.hp = e.maxHp = 1e6;
        h.x = tr.x + 3; h.y = tr.y + 3; h.stop(); h.invuln = 1e9; g.log.lines = []; g.notice = null;
        window.__tr = tr; return { tree: [tr.x, tr.y], e: [e.x, e.y] }; })()''')
    await wait(500)
    cl = await G("__game.clientOf(__game.enemies[0].x, __game.enemies[0].y, 14)")
    await pg.mouse.move(*cl)
    await wait(300)
    t = await G("(() => { const g = __game; return { xa: +((window.__tr._xa ?? 1)).toFixed(2), aggro: g.xrayAggro, faded: g.xrayFaded, hover: g.hoverEnemy === g.enemies[0] }; })()")
    await pg.screenshot(path=SHOT_TREES)
    check('m1f P0.3 враг в агро за кроной: крона растворяется (альфа < 1), силуэт поверх, курсор наводится на врага; скриншот screenshot_m1f_trees.png',
          t['xa'] < 0.95 and t['aggro'] >= 1 and t['hover'] and os.path.exists(SHOT_TREES), {**s, **t})
    await pg.mouse.move(1700, 200)
    await G("(() => { const g = __game; g.enemies[0].dead = true; })()")
    await wait(700)
    t2 = await G("+((window.__tr._xa ?? 1)).toFixed(2)")
    check('m1f P0.3 враг исчез (не в агро, не под курсором) — крона плавно возвращается', t2 > t['xa'], {'xa_after': t2, 'xa': t['xa']})

    # ---------- P0.4 «Огненный змей»: ПКМ в пустую точку, двойной щелчок, ПКМ при зажатой ЛКМ, отказы
    await G('''(() => { const g = __game, h = g.hero; g.enemies = []; g.buried = []; h.x = 30; h.y = 18; h.stop(); h.invuln = 1e9; h.rmb = 'zmey'; h.yar = h.maxYar; })()''')
    await wait(300)
    res = []
    for dbl in (False, True, True):
        pt = await client_of(30 + 2.5, 18 - 1.5, 10)
        await pg.mouse.move(*pt)
        b = await G("({ c: __game.counters.casts.zmey || 0, y: __game.hero.yar })")
        await pg.mouse.click(*pt, button='right')
        if dbl:
            await pg.wait_for_timeout(60)
            await pg.mouse.click(*pt, button='right')
        await wait(1800)
        a2 = await G("({ c: __game.counters.casts.zmey || 0, y: __game.hero.yar })")
        res.append({'dbl': dbl, 'casts': a2['c'] - b['c'], 'spent': round(b['y'] - a2['y'], 2)})
        await G("__game.hero.yar = __game.hero.maxYar")
    check('m1f P0.4 ПКМ в пустую точку — змей вылетает и тратит Ярь; быстрый двойной щелчок — второй щелчок запомнен, два змея и двойная трата',
          res[0]['casts'] == 1 and res[0]['spent'] > 0 and all(r['casts'] == 2 and r['spent'] > res[0]['spent'] * 1.5 for r in res[1:]), res)
    # ПКМ при зажатой ЛКМ на враге: раньше ни один не вылетал до отпускания ЛКМ
    await G('''(() => { const g = __game, h = g.hero; delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const e = g.enemies.find(e => e.kind === 'upyr' && !e.special);
        g.enemies = [e]; g.buried = []; h.x = 30; h.y = 18; h.stop(); e.x = 31; e.y = 18; e.hp = e.maxHp = 1e6; e.stagger = 1e9; h.yar = h.maxYar; h.invuln = 1e9; })()''')
    await wait(300)
    ce = await client_of(31, 18, 14)
    await pg.mouse.move(*ce)
    await pg.mouse.down()
    await wait(500)
    got = []
    for i in range(4):
        c0 = await G("__game.counters.casts.zmey || 0")
        pt = await client_of(28, 20, 10)
        await pg.mouse.move(*pt)
        await pg.mouse.click(*pt, button='right')
        await pg.mouse.move(*ce)
        await wait(1000)
        got.append((await G("__game.counters.casts.zmey || 0")) - c0)
        await G("__game.hero.yar = __game.hero.maxYar")
    await pg.mouse.up()
    check('m1f P0.4 ПКМ в точку при зажатой ЛКМ на враге — змей вылетает после текущего замаха (каждый щелчок)', got == [1, 1, 1, 1], got)
    # отказы: нет Яри → вспышка на иконке ПКМ и звук ошибки
    await wait(800)
    await G("(() => { const g = __game, h = g.hero; g.enemies = []; h.yar = 0; window.__snd = []; const p0 = g.audio.play.bind(g.audio); g.audio.play = (k, ...r) => { window.__snd.push(k); return p0(k, ...r); }; })()")
    pt = await client_of(28, 16, 10)
    await pg.mouse.move(*pt)
    d0 = await G("__game.counters.rmbDenied || 0")
    await pg.mouse.click(*pt, button='right')
    await wait(120)
    d = await G("({ n: (__game.counters.rmbDenied || 0), why: __game.rmbDeny && __game.rmbDeny.why, t: __game.rmbDeny && __game.rmbDeny.t, snd: window.__snd.slice(), casts: __game.counters.casts.zmey })")
    await G("__game.hero.yar = __game.hero.maxYar")
    check('m1f P0.4 отказ ПКМ (нет Яри): вспышка на иконке ПКМ (rmbDeny «yar») и звук ошибки',
          d['n'] == d0 + 1 and d['why'] == 'yar' and d['t'] > 0 and 'error' in d['snd'], d)

    # ======================= P1 =======================
    # ---------- P1.5 журнал: левый край над шаром жизни, ≤ 4 строк, подложка, быстро гаснет, скрыт под окнами
    await G(FRESH)
    await G('''(() => { const g = __game, h = g.hero; g.notice = null; g.hint = null; g.log.lines = [];
        for (let i = 1; i <= 7; i++) g.log.add('Строка журнала номер ' + i + (i === 7 ? ' — длинная, чтобы перенестись по ширине журнала у левого края' : ''), '#f2ecd8'); })()''')
    await wait(150)
    s = await G("({ n: __game.logDrawn, box: __game.logBox })")
    await G("__game.ui.invOpen = true")
    await wait(150)
    s['win'] = await G("__game.logDrawn")
    await G("__game.ui.closeAll()")
    await G("(() => { const g = __game; g.log.time += 5.2; })()")
    await wait(150)
    s['late'] = await G("__game.logDrawn")
    b = s['box'] or {}
    check('m1f P1.5 журнал у левого края над шаром жизни: не больше 4 строк, не заходит на шар (x < 90, y ≥ 292), под окном скрыт, через ~5 с погас',
          s['n'] == 4 and b.get('x') == 4 and b.get('y', 0) + b.get('h', 999) <= 292 and s['win'] == 0 and s['late'] == 0, s)
    # подсказки обучения — отдельная плашка: не поверх трекера, не над героем (там «Блок»), уведомление не перебивают
    await G('''(() => { const g = __game; g.notice = null; g.notify('Блок', '#fff', 'blk'); g.notify(g.dbg.t('ui.tut.dash'), '#d39a45', 'tut'); })()''')
    await wait(150)
    s = await G('''(() => { const g = __game, hb = g.hintBox, [hx, hy] = g.toS(g.hero.x, g.hero.y);
        return { hint: g.hint && g.hint.text, notice: g.notice && g.notice.text, hb, hero: [hx, hy], seen: g.ctrlHintSeen }; })()''')
    hb = s['hb'] or {}
    over_tracker = hb and hb['x'] < 212 and hb['y'] < 88
    over_hero = hb and hb['x'] < s['hero'][0] + 30 and hb['x'] + hb['w'] > s['hero'][0] - 30 and hb['y'] < s['hero'][1] and hb['y'] + hb['h'] > s['hero'][1] - 80
    check('m1f P1.5 подсказка обучения — своя плашка справа (не поверх трекера и не над героем), уведомление «Блок» не перебивает',
          s['hint'] and s['hint'].startswith('Пробел') and s['notice'] == 'Блок' and hb and not over_tracker and not over_hero, s)
    s = await G('''(() => { const g = __game; g.time = Math.max(g.time, 15); return 1; })()''')
    await wait(150)
    s = await G("({ seen: __game.ctrlHintSeen, ls: localStorage.getItem('byl_ctrl_hint_seen') })")
    check('m1f P1.5 подсказка управления — только при первом входе (после показа помечена в localStorage)', s['seen'] and s['ls'] == '1', s)

    # ---------- P1.8 пояс: ячейки подкрашены по содержимому + скриншот журнала и пояса
    await G('''(() => { const g = __game, h = g.hero; h.belt = [{ kind: 'life1', count: 2 }, { kind: 'yar1', count: 2 }, { kind: 'life1', count: 1 }, { kind: 'zhivaya', count: 1 }];
        g.hint = null; g.notice = null; g.log.lines = [];
        g.log.add('Подобрано: Слабое зелье жизни', '#f2ecd8'); g.log.add('Упырь упокоен. +12 опыта', '#d39a45'); g.log.add('Ярь и так полна.', '#8db6ee'); g.log.add('Выпито: Слабое зелье жизни', '#f2ecd8'); })()''')
    await pg.mouse.move(1500, 700)
    await wait(250)
    s = await G("({ tint: (__game.beltTint || []).slice(0, 4), log: __game.logDrawn })")
    await pg.screenshot(path=SHOT_LOG)
    check('m1f P1.8 пояс: зелья жизни — красные ячейки, Яри — синие, живая вода — зелёная; скриншот screenshot_m1f_log.png (журнал и пояс)',
          s['tint'] == ['hp', 'yar', 'hp', 'both'] and s['log'] == 4 and os.path.exists(SHOT_LOG), s)

    # ---------- P1.6 очередь реплик и уведомлений; под окном подписи и реплики мира гаснут
    await G(FRESH)
    s = await G('''(() => { const g = __game, h = g.hero; g._barks = {}; g.speechUntil = 0; g.dialogQ.length = 0; g.fx.texts = [];
        g.bark(h, 'test.a', 'Первая реплика'); g.bark(h, 'test.b', 'Вторая реплика'); g.bark(h, 'test.d', 'Третья — диалог');
        const n0 = g.fx.texts.filter(t => t.speech).length;
        g.simulate(1.0); const n1 = g.fx.texts.filter(t => t.speech).map(t => t.str);
        g.simulate(2.0); const n2 = g.fx.texts.filter(t => t.speech).map(t => t.str);
        g.simulate(2.7); const n3 = g.fx.texts.filter(t => t.speech).map(t => t.str);
        g.notice = null; g.noticeQ = [];
        g.notify('Серебро: +300', '#fff', 'rew-s'); g.notify('Удаль I', '#fff', 'rew-y'); g.notify('Очко навыка: +1', '#fff', 'rew-p');
        const q0 = [g.notice.text, g.noticeQ.length]; g.simulate(1.7); const q1 = g.notice.text; g.simulate(1.7); const q2 = g.notice.text;
        return { n0, n1, n2, n3, q0, q1, q2 }; })()''')
    check('m1f P1.6 реплики не наслаиваются: барки и диалог идут по очереди по одной; награды — уведомления по очереди',
          s['n0'] == 1 and s['n1'] == ['Первая реплика'] and s['n2'] == ['Вторая реплика'] and s['n3'] == ['Третья — диалог']
          and s['q0'] == ['Серебро: +300', 2] and s['q1'] == 'Удаль I' and s['q2'] == 'Очко навыка: +1', s)
    await G('''(() => { const g = __game, h = g.hero; g.enterZone('ladoga', 'start'); g.ui.closeAll(); g._barks = {}; g.speechUntil = 0; g.dialogQ.length = 0;
        const tv = g.npcs.find(n => n.role === 'tverdyata'); h.x = tv.x + 0.3; h.y = tv.y + 0.9; h.stop(); g.bark(h, 'test.c', 'Реплика под окном'); })()''')
    await wait(200)
    s = await G('''(() => { const g = __game, L = g.labelsDrawn || [], [hx, hy] = g.toS(g.hero.x, g.hero.y), hb = { x: hx - 11, y: hy - 48, w: 22, h: 50 };
        const ov = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
        let pairs = 0; for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) if (ov(L[i], L[j])) pairs++;
        return { n: L.length, names: L.map(l => l.text), pairs, onHero: L.filter(l => ov(l, hb)).map(l => l.text), speech: g.speechDrawn }; })()''')
    await G("__game.ui.invOpen = true")
    await wait(200)
    s['win'] = await G("({ labels: (__game.labelsDrawn || []).length, speech: __game.speechDrawn })")
    await G("__game.ui.closeAll()")
    check('m1f P1.6 Ладога: имена и подписи мест не налезают друг на друга и на героя (Твердята рядом); под окном подписи и реплики мира скрыты',
          s['n'] >= 2 and 'Твердята' in s['names'] and s['pairs'] == 0 and not s['onHero'] and s['speech'] >= 1 and s['win']['labels'] == 0 and s['win']['speech'] == 0, s)

    # ---------- P1.10 Соломенник: без «· UNDEFINED»
    s = await G('''(() => { const g = __game, h = g.hero, d = g.enemies.find(e => e.dummy); h.x = d.x + 1.5; h.y = d.y + 1.5; h.stop(); g.updateCamera(); return { name: d.name, fam: d.def.family || null }; })()''')
    await wait(150)
    cl = await G("(() => { const d = __game.enemies.find(e => e.dummy); return __game.clientOf(d.x, d.y, 14); })()")
    await pg.mouse.move(*cl)
    await wait(200)
    s['sub'] = await G("__game.targetSub")
    s['hover'] = await G("!!(__game.hoverEnemy && __game.hoverEnemy.dummy)")
    check('m1f P1.10 Соломенник под курсором: строки «семья · царство» нет (раньше «· UNDEFINED»)', s['hover'] and s['sub'] is None, s)

    # ---------- P1.7 экран гибели: Пробел не воскрешает, Enter — после задержки, кнопка из ui.death.button
    await G(FRESH)
    await G('(() => { const g = __game, h = g.hero; h.invuln = 0; h.graceT = 0; h.takeDamage(99999, g, "fire", null); })()')
    await wait(200)
    s = await G('''(() => { const g = __game, inp = g.input; g.deathT = 3.5; inp.keysPressed.add('Space'); g.update(1 / 60); inp.endFrame();
        const afterSpace = g.state; inp.keysPressed.add('Enter'); g.update(1 / 60); inp.endFrame(); return { afterSpace, afterEnter: g.state, btn: g.dbg.t('ui.death.button') }; })()''')
    src = open(ROOT + 'src/render/screens.js', encoding='utf-8').read()
    check('m1f P1.7 экран гибели: Пробел (рывок) не воскрешает, Enter — воскрешает; надпись кнопки — ключ ui.death.button',
          s['afterSpace'] == 'dead' and s['afterEnter'] == 'play' and "t('ui.death.button')" in src and 'Очнуться у крады' not in src, s)

    # ---------- P1.9 пересвет: сумма тёплой альфы ограничена, вспышка удара ≤ 0,3
    await G(FRESH)
    await G('''(() => { const g = __game, h = g.hero; g.enemies = []; g.combat.fires = [];
        for (let i = 0; i < 9; i++) g.combat.fires.push({ id: 900 + i, kind: 'trail', x: h.x + (i % 3 - 1) * 0.7, y: h.y + (Math.floor(i / 3) - 1) * 0.7, r: 0.6, lit: true, t: 1, tele: 0, litT: 0.5, burn: 99, flight: 0 });
        for (let i = 0; i < 3; i++) g.fx.light && g.fx.light(h.x, h.y, 90, 0.4); })()''')
    await wait(120)
    s = await G("(async () => { const B = await import('/src/render/boss_art.js'); return { peak: +(__game.warmPeak || 0).toFixed(3), flash: B.FLASH_A }; })()")
    await G("(() => { __game.combat.fires = []; })()")
    check('m1f P1.9 пересвет: 9 пятен огня и вспышки в одной точке — сумма тёплой альфы ≤ 0,4; вспышка попадания ≤ 0,3',
          0 < s['peak'] <= 0.4 and s['flash'] <= 0.3, s)

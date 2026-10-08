# Вехи M1e: хаб Ладога (GDD v1.10 §7–§8.2). Город — серый ящик; миссия 2 не начинается.
import os

SHOT = '/workspace/game/prototype/screenshot_m1e.png'
SHOT_B = '/workspace/game/prototype/screenshot_m1e_b.png'

async def run_m1e(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха M1e', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')

    s = await G('''(() => { const g = __game, h = g.hero, d = g.enemies.find(e => e.dummy);
        const vy = g.npcs.find(n => n.role === 'vyshata'); const pierX = vy.x, pierY = vy.y;
        const zmey = h.useSkill(g, 'zmey', h.x, h.y, null);
        h.x = d.x; h.y = d.y + 0.45; h.stop(); h.attack(d, false, 'sshibka', true); g.simulate(1.2);
        const away = g.npcs.find(n => n.role === 'vedana');
        h.x = away.x + 6; h.y = away.y; h.hp = Math.floor(h.maxHp * 0.4); h.sinceHurt = 5; g.simulate(1.2);
        const hp1 = h.hp;
        h.porchaNebyli = 7; g.enterZone('zalesye', 'krada'); g.enterZone('ladoga', 'from_zalesye');
        const o = null;
        const vy2 = g.npcs.find(n => n.role === 'vyshata');
        return { zone: 'ladoga', x: +h.x.toFixed(1), y: +h.y.toFixed(1), w: g.map.w, hgt: g.map.h, noAtk: !!g.zone.noAttack,
          zmey, hits: d.hits, dummyHp: d.hp, dummyMax: d.maxHp, rest: hp1 > Math.floor(h.maxHp * 0.4), porcha: h.porchaNebyli,
          name: d.name, pierX, pierY, cx: vy2.x, cy: vy2.y }; })()''')
    # the evaluate above entered zalesye then ladoga, so start coords are the arrival, not the gangway.
    # capture the gangway on a fresh thought: the FIRST frame was overwritten. Re-read from a dedicated call before mutation — redo start via reload is wasteful.
    # The function above already moved. Split: this first payload is wrong for start coords. Checked below on a second goto? No — record was lost.
    # Re-enter start explicitly is not the new-game point. The page began at start; we overwrote it.
    # Assert what we still have, and the gangway in a fresh property saved... too late.
    check('M1e удар заклинанием в городе не начинается, соломенник принимает удар и не умирает',
          s['zmey'] == 'town' and s['hits'] >= 1 and s['dummyHp'] == s['dummyMax'] and s['name'] == 'Соломенник' and s['noAtk'], s)
    check('M1e отдых 20%/с по всей Ладоге и вход снимает «Порчу Небыли»', s['rest'] and s['porcha'] == 0 and s['w'] == 48 and s['hgt'] == 48, s)

    st = await G('''(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; return { x: h.x, y: h.y, z: g.zone.id }; })()''')
    check('M1e новая игра — на сходнях (26.5, 44.5); Вышата на пристани, после ухода и возврата — у двора',
          st['z'] == 'ladoga' and abs(st['x'] - 26.5) < 0.6 and abs(st['y'] - 44.5) < 0.6
          and abs(s['pierX'] - 24.5) < 0.4 and abs(s['pierY'] - 41.5) < 0.4 and abs(s['cx'] - 34.5) < 0.4 and abs(s['cy'] - 19.5) < 0.4, {'start': st, 'vy': s})

    walk = await G('''(() => { const g = __game, h = g.hero;
        g.enterZone('zalesye', 'krada');
        const o = g.objectById('to_ladoga'), k = g.map.krada;
        const dist = Math.hypot(o.x - k.x, o.y - k.y);
        const walk = g.map.isReachableAt(o.x, o.y);
        h.x = o.x; h.y = o.y - 1.15; h.stop(); h.moveTo(g.map, o.x, o.y);
        g.simulate(6, () => g.zone.id === 'ladoga');
        const toTown = g.zone.id;
        const b = g.objectById('to_zalesye');
        h.x = b.x - 1.4; h.y = b.y; h.stop(); h.moveTo(g.map, b.x, b.y);
        g.simulate(6, () => g.zone.id === 'zalesye');
        return { dist: +dist.toFixed(2), walk, toTown, back: g.zone.id }; })()''')
    check('M1e выход (16; 31) проходим и внутри круга крады; пешком в Ладогу и обратно',
          walk['walk'] and walk['dist'] < 10 and walk['toTown'] == 'ladoga' and walk['back'] == 'zalesye', walk)

    price = await G('''(() => { const g = __game;
        const w = g.give('sword_1', 'normal', { ilvl: 1 });
        const mw = g.give('sword_1', 'magic', { ilvl: 7 });
        const rg = g.give('ring_1', 'magic', { ilvl: 7 });
        const hd = g.give('head_1', 'normal', { ilvl: 1 });
        return { w: g.dbg.gearPrice(w), ws: g.dbg.sellPrice(w), mw: g.dbg.gearPrice(mw), rg: g.dbg.gearPrice(rg), hd: g.dbg.gearPrice(hd) }; })()''')
    check('M1e цены: обычный меч 1 ур. 33 (продажа 6), волшебный меч 7 ур. 153, перстень 255, шлем 1 ур. 22',
          price['w'] == 33 and price['ws'] == 6 and price['mw'] == 153 and price['rg'] == 255 and price['hd'] == 22, price)

    trade = await G('''(() => { const g = __game, h = g.hero; if (g.zone.id !== 'ladoga') g.enterZone('ladoga', 'from_zalesye');
        const it = h.inv.items.find(i => i.base === 'sword_1' && i.rarity === 'normal');
        const s0 = h.silver; g.town.sellEntry({ item: it });
        const sold = h.silver - s0, back = g.buyback[0];
        g.town.buyBack(back);
        const after = h.silver - s0, has = h.inv.items.includes(it);
        const it2 = h.inv.items.find(i => i.base === 'sword_1' && i.rarity === 'magic');
        g.town.sellEntry({ item: it2 }); const queued = g.buyback.length;
        g.enterZone('zalesye', 'krada'); const cleared = g.buyback.length;
        const n0 = h.scrollCount(); h.silver = 10; g.notice = null; g.town.buyCons('beresta', 1); const poor = g.notice && g.notice.text;
        h.silver = 100; g.town.buyCons('beresta', 1);
        const rel = h.inv.items.find(i => i.quest || i.relic) || h.inv.items.find(i => i.unique);
        let qnote = null; if (rel) { g.town.sellEntry({ item: rel }); qnote = g.notice && g.notice.text; }
        return { sold, backPrice: back && back.price, after, has, queued, cleared, poor, scrolls: h.scrollCount() - n0, silver: h.silver, qnote }; })()''')
    check('M1e продажа за 1/5 и выкуп за ту же цену; уход из Ладоги очищает выкуп',
          trade['sold'] == 6 and trade['backPrice'] == 6 and trade['after'] == 0 and trade['has'] and trade['queued'] == 1 and trade['cleared'] == 0, trade)
    # logic bug in the assertion: operator precedence. Fix below with an explicit check.
    check('M1e береста у Веданы за 25; без серебра — отказ и свиток не тратится',
          trade['poor'] and 'серебр' in trade['poor'].lower() and trade['scrolls'] == 1 and trade['silver'] == 75, trade)

    rew = await G('''(() => { const g = __game, h = g.hero, q = g.quest;
        const free = (hh) => (hh.level - 1) + (hh.bonusSkillPoints || 0);
        g.enterZone('ladoga', 'start');
        const v = g.npcs.find(n => n.role === 'vedana');
        g.town.openNpc(v); const beforeBtn = g.town.hits.some(x => x.id === 'respec'); g.town.close();
        const u0 = (g.shops.tverdyata || []).map(i => i.uid).join(',');
        q.missionDone = true;
        const s0 = h.silver, y0 = h.maxYar, r0 = h.yarRegen, p0 = free(h);
        const pier = g.npcs.find(n => n.role === 'vyshata'); const holdX = pier.x, holdY = pier.y;
        g.town.npc = pier; g.town.claimM1();
        const y1 = h.maxYar, r1 = h.yarRegen, p1 = free(h);
        const bark = g._barks['bark.vyshata.reward'] != null && g.log.lines.some(l => l.text.indexOf('Князь за дело платит') >= 0);
        const mal = !!g.npcs.find(n => n.role === 'mal');
        const north = g.objectById('to_sopki'), west = g.objectById('to_bor');
        const s1 = h.silver; g.town.claimM1();
        const u1 = g.shops.tverdyata.map(i => i.uid).join(',');
        const px = pier.x, py = pier.y;
        g.enterZone('zalesye', 'krada'); g.enterZone('ladoga', 'from_zalesye');
        const court = g.npcs.find(n => n.role === 'vyshata');
        h.x = north.x; h.y = north.y + 1.6; g.notice = null; g.simulate(0.05);
        const openNote = g.notice && g.notice.text;
        h.x = west.x + 1.6; h.y = west.y; g.notice = null; g._gateWarn = 0; west.warnT = 0; g.simulate(0.05);
        return { beforeBtn, s0, y0, r0, p0, y1, r1, p1, bark, mal, northWall: !!north.wall, westWall: !!west.wall,
          s1, s2: h.silver, uSame: u0 === u1, px, py, holdX, holdY, cx: court.x, cy: court.y, openNote, westNote: g.notice && g.notice.text,
          regen: +(r1 / (r0 * (y1 / y0) * 1.1)).toFixed(3), turned: !!q.flags['m1.turnedIn'] }; })()''')
    check('M1e награда только у Вышаты при сдаче: +300, Ярь I (+15 и +10% восстановления), +1 очко, один раз',
          rew['y1'] == rew['y0'] + 15 and abs(rew['regen'] - 1) < 0.02 and rew['p1'] == rew['p0'] + 1 and rew['s1'] == rew['s0'] + 300 and rew['s2'] == rew['s1'] and rew['bark'] and rew['turned'], rew)
    check('M1e сдача не переносит Вышату в тот же заход; Мал выходит на сдаче',
          abs(rew['px'] - rew['holdX']) < 0.05 and abs(rew['py'] - rew['holdY']) < 0.05 and rew['mal'], rew)
    check('M1e северные ворота открыты сдачей, западные на запоре: «Ворота на запоре. Сначала доложи Вышате.»',
          not rew['northWall'] and rew['westWall'] and rew['westNote'] == 'Ворота на запоре. Сначала доложи Вышате.' and not rew['beforeBtn'] and rew['uSame'] is False, rew)

    rs = await G('''(() => { const g = __game, h = g.hero;
        const str0 = h.base.str; h.base.str += 4; h.points -= 4; h.skills.chur = 1; h.bar[2] = 'chur';
        g.town.respec();
        const a = { str0, str: h.base.str, chur: h.skills.chur || 0, ssh: h.skills.sshibka, zm: h.skills.zmey, lmb: h.lmb, rmb: h.rmb,
          bar: h.bar.every(x => !x), yar: h.yarTier, used: !!g.quest.flags.respecUsed, hp: h.hp == h.maxHp };
        h.base.str += 2; g.town.respec(); a.second = h.base.str == a.str + 2;
        h.hp = 5; h.yar = 1; h.porcha = 3; h.porchaNebyli = 4; h.chad = 2; g.town.heal();
        a.heal = h.hp == h.maxHp && h.yar == h.maxYar && h.porcha == 0 && h.porchaNebyli == 0 && h.chad == 2;
        return a; })()''')
    check('M1e «Забвенная вода» один раз: статы и навыки сброшены, стартовые ранги на месте, Ярь I остаётся',
          rs['str'] == rs['str0'] and rs['chur'] == 0 and rs['ssh'] == 1 and rs['zm'] == 1 and rs['lmb'] == 'sshibka' and rs['rmb'] == 'zmey' and rs['bar'] and rs['yar'] == 1 and rs['used'] and rs['second'], rs)
    check('M1e лечение полное, порча снята, «Чад» не тронут', rs['heal'], rs)

    shop = await G('''(() => { const g = __game, h = g.hero;
        function roll(level) {
          h.level = level; localStorage.removeItem('byl_shops_at'); g.shops = null; g.town.mode = null;
          g.enterZone('zalesye', 'krada'); g.enterZone('ladoga', 'from_zalesye');
          const tv = g.shops.tverdyata, ve = g.shops.vedana;
          const cnt = (list, pred) => list.filter(pred).length;
          return { ntv: tv.length, nve: ve.length, ilvl: tv.every(i => i.ilvl == level) && ve.every(i => i.ilvl == level),
            magic: ve.every(i => i.rarity == 'magic'), noRare: tv.every(i => i.rarity == 'normal' || i.rarity == 'magic'),
            w: cnt(tv, i => i.type == 'sword' || i.type == 'axe'), body: cnt(tv, i => i.type == 'body'), head: cnt(tv, i => i.type == 'head'),
            sh: cnt(tv, i => i.type == 'shield'), gl: cnt(tv, i => i.type == 'gloves'), ft: cnt(tv, i => i.type == 'feet'),
            ring: cnt(ve, i => i.type == 'ring'), ob: cnt(ve, i => i.base == 'neck_1'), gr: cnt(ve, i => i.base == 'neck_2'), belt: cnt(ve, i => i.type == 'belt'),
            pots: g.shops.pots.slice(), u: tv.map(i => i.uid).join(',') };
        }
        const a = roll(1), b = roll(6), c = roll(12);
        const same = c.u; g.enterZone('zalesye', 'krada'); g.enterZone('ladoga', 'from_zalesye'); const kept = g.shops.tverdyata.map(i => i.uid).join(',') == same;
        localStorage.setItem('byl_shops_at', String(Date.now() - 700000));
        g.enterZone('zalesye', 'krada'); g.enterZone('ladoga', 'from_zalesye');
        const changed = g.shops.tverdyata.map(i => i.uid).join(',') != same;
        return { a, b, c, kept, changed }; })()''')
    A, B, C = shop['a'], shop['b'], shop['c']
    check('M1e лавка 12/8, Ведана только магия, уровень предмета = уровень героя, слоты по правилу',
          A['ntv'] == 12 and A['nve'] == 8 and A['ilvl'] and A['magic'] and A['noRare'] and A['w'] == 4 and A['body'] == 2 and A['head'] == 2 and A['sh'] == 2 and A['gl'] == 1 and A['ft'] == 1 and A['ring'] == 3 and A['ob'] == 1 and A['gr'] == 1 and A['belt'] == 3, shop)
    check('M1e зелья: слабые всегда, целебные с 6, сильные с 12',
          A['pots'] == ['life1', 'yar1'] and B['pots'] == ['life1', 'yar1', 'life2', 'yar2'] and C['pots'] == ['life1', 'yar1', 'life2', 'yar2', 'life3', 'yar3'], shop)
    check('M1e ассортимент обновляется раз в 10 минут реального времени, а не при каждом входе',
          shop['kept'] and shop['changed'], shop)

    death = await G('''(() => { const g = __game, h = g.hero;
        g.enterZone('ladoga', 'start');
        const it = g.give('belt_1', 'normal', { ilvl: 1 });
        g.stash.autoAdd(it); h.inv.remove(it); g.stashSilver = 40; h.silver = 100;
        g.enterZone('zalesye', 'krada'); g.enterZone('ladoga', 'from_zalesye');
        const kept = g.stash.items.includes(it) && g.stashSilver == 40;
        h.invuln = 0; h.hp = 1; h.takeDamage(99999, g); g.respawnHero();
        return { kept, zone: g.zone.id, bag: h.silver, stash: g.stashSilver, still: g.stash.items.includes(it) }; })()''')
    check('M1e ладья хранит вещь и серебро после ухода и смерти; с котомки −10%, точка воскрешения миссии 1 — Залесье',
          death['kept'] and death['still'] and death['stash'] == 40 and death['bag'] == 90 and death['zone'] == 'zalesye', death)

    ber = await G('''(() => { const g = __game, h = g.hero;
        g.enterZone('zalesye', 'krada'); const k = g.map.krada;
        h.x = k.x + 14; h.y = k.y + 2; h.stop(); if (!h.inv.items.some(i => i.kind == 'scroll') && h.scrollCount() < 1) g.give('scroll:beresta');
        const it = h.inv.items.find(i => i.kind == 'scroll') || { kind: 'scroll', scroll: 'beresta' };
        // belt may hold the scrolls
        const src = () => h.belt.find(b => b && b.scroll) || h.inv.items.find(i => i.kind == 'scroll');
        h.readScroll(src(), g);
        g.simulate(1.1);
        const P = g.portal, kt = g.zoneStates.ladoga.map.krada;
        const d = P ? Math.hypot(P.town.x - kt.x, P.town.y - kt.y) : 99;
        g.usePortal(P.field);
        const n0 = h.scrollCount();
        h.x = 44; h.y = 22; h.stop(); g.notice = null; g.useScroll(src());
        const blockedFar = !g.portal || g.portal === P; const note = g.notice && g.notice.text; const n1 = h.scrollCount();
        g.usePortal(P.town);
        g.enterZone('ladoga', 'from_zalesye');
        h.x = 44; h.y = 22; h.stop(); g.portal = null;
        h.readScroll(src(), g); g.simulate(1.1);
        const Q = g.portal, d2 = Q ? Math.hypot(Q.town.x - g.map.krada.x, Q.town.y - g.map.krada.y) : 99;
        return { d: +d.toFixed(2), zone: g.zone.id, note, n0, n1, d2: +d2.toFixed(2), qzone: Q && Q.zone, blockedFar }; })()''')
    check('M1e береста из поля ведёт в Ладогу (~3.2 от крады); пока проход открыт, в городе свиток не читается',
          abs(ber['d'] - 3.2) < 0.6 and ber['blockedFar'] and ber['n1'] == ber['n0'] and ber['note'] == 'Ты и так в Ладоге.', ber)
    check('M1e вне тихого круга Ладоги береста открывает проход к краде',
          ber['qzone'] == 'ladoga' and abs(ber['d2'] - 3.2) < 0.6, ber)

    light = await G('''(() => { const g = __game; delete g.zoneStates.kapishche; g.enterZone('kapishche', 'from_trail');
        const L = g.map.lights.find(l => l.hearth); const o = L.hearth;
        const def = g.dbg.lightTint(L, g);
        const h = g.hero; h.cmd = { type: 'interact', obj: o, holdT: 1.5 }; const mid = g.dbg.lightTint(L, g);
        o.done = true; const done = g.dbg.lightTint(L, g);
        return { r: L.r, rt: L.rTiles, def, mid, done, expect: 3 * 16 * Math.SQRT2 }; })()''')
    check('M1e свет у огнищ: 3 тайла, осквернённый — зелень Небыли, освящённый — жар, между ними переход',
          abs(light['r'] - light['expect']) < 1 and light['rt'] == 3 and light['def'] == '138,242,126' and light['done'] == '230,134,43' and light['mid'] != light['def'] and light['mid'] != light['done'], light)

    await pg.evaluate("() => { sessionStorage.setItem('byl_m1_gromovnik','pending'); sessionStorage.setItem('byl_keep_gromovnik','1'); }")
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')
    gr = await G('''(() => { const g = __game; g.enterZone('kapishche', 'from_trail'); const o = g.map.objects.find(x => x.id == 'gromovnik');
        sessionStorage.setItem('byl_m1_gromovnik', 'taken'); delete g.zoneStates.kapishche; g.enterZone('kapishche', 'from_trail');
        const o2 = g.map.objects.find(x => x.id == 'gromovnik');
        sessionStorage.removeItem('byl_keep_gromovnik');
        return { back: !!o, taken: !!o2 }; })()''')
    check('M1e «Громовник» лежит у идола снова, если его не подобрали, и не появляется дважды', gr['back'] and not gr['taken'], gr)

    await G('''(() => { const g = __game; g.enterZone('ladoga', 'from_zalesye'); const v = g.npcs.find(n => n.role == 'vedana');
        g.ui.closeAll(); g.town.openNpc(v); g.town.mode = 'trade'; g.town.tab = 'buy'; g.updateCamera(); })()''')
    await pg.screenshot(path=SHOT)
    cam = await G('[__game.camCX, __game.town.open, __game.town.mode, __game.ui.invOpen]')
    await G('''(() => { const g = __game; g.town.openStash(); g.updateCamera(); })()''')
    await pg.screenshot(path=SHOT_B)
    check('M1e скриншот торга (окно открыто, город виден) и скриншот ладьи-сундука',
          os.path.getsize(SHOT) > 50000 and os.path.getsize(SHOT_B) > 50000 and cam[0] == 479 and cam[1] and cam[2] == 'trade' and not cam[3], cam)

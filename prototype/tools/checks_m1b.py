"""Проверки вехи M1b (ответы дизайнера 08.10 и капище Перуна). Вызываются из verify_playwright.py на свежей загрузке."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_M1B = os.path.join(ROOT, 'screenshot_m1b.png')

# эталонный герой §9.1 на 6 ур. (как в замерах «стоячий герой»): 30/25/35/15, броня 41, оружие ≈ 4,5 + 0,9·6 = 9,9 (5–15), «Сшибка» 3
REF_HERO = '''const mkRef = async (L, A) => { const { Hero } = await import('/src/entities/hero.js'); const { makeItem } = await import('/src/data/items.js');
  const h = new Hero(A[0], A[1]); let n = 0; while (h.level < L && n++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g);
  [h.base.str, h.base.dex, h.base.vit, h.base.ene] = [30, 25, 35, 15]; h.points = 0; h.skills.sshibka = 3;
  for (const s of ['lhand', 'head', 'body', 'gloves', 'feet', 'belt', 'neck', 'ring1', 'ring2']) h.equip[s] = null;
  for (const [slot, base, armor, hpb] of [['body', 'body_2', 20, 12], ['head', 'head_1', 4], ['lhand', 'shield_1', 5], ['gloves', 'gloves_1', 2], ['feet', 'boots_1', 2], ['belt', 'belt_1', 2]]) {
    const it = makeItem(base, hpb ? 'magic' : 'normal', L, Math.random, { armor, affixes: hpb ? [['S01', hpb]] : [] }); if (it.block) it.block = 0; h.equip[slot] = it; }
  h.equip.rhand.dmg = [5, 15]; h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar; h.belt = [null, null, null, null]; h.levelFx = 0; g.hero = h; return h; };'''

SEEDED = '''const rnd0 = Math.random; let seed = 20261008; Math.random = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };'''


async def run_m1b(pg, G, check, wait, client_of, client_scr, a):
    await pg.goto(a.url)
    await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=15000)
    await pg.mouse.move(960, 540)
    await pg.mouse.click(960, 300)
    await wait(200)
    print('--- веха M1b', flush=True)
    await G("(() => { if (__game.zone.id !== 'zalesye') __game.enterZone('zalesye', 'start'); })()")

    # --- QA B-28 (первым): закрытый выход — стена, переход только по намерению; замер смешанной стаи у выхода
    s = await G('''(() => { const g = __game, h = g.hero, o = g.objectById('to_trail'), m = g.map; for (const e of g.enemies) e.stagger = 1e9;
        const beyond = [o.x, o.y + 1.6], out = { wall: !!o.wall, reachBeyond: m.isReachableAt(...beyond), reachExit: m.isReachableAt(o.x, o.y) };
        h.x = o.x; h.y = o.y - 4; h.stop(); const w0 = g.counters.exitLockedWarn || 0; let back = 0, py = h.y;
        g.simulate(3, () => { h.moveTo(m, o.x, o.y); if (h.y < py - 0.05) back++; py = h.y; return false; });          // «зажатая ЛКМ» на выходе 3 с
        out.hold = { zone: g.zone.id, warns: (g.counters.exitLockedWarn || 0) - w0, pushedBack: back, d: +Math.hypot(h.x - o.x, h.y - o.y).toFixed(2) };
        h.stop(); h.x = o.x; h.y = o.y - 4; g.simulate(1.5); const [fx, fy] = o.wall.front; h.moveTo(m, fx, fy); g.simulate(2); out.click = { warns: (g.counters.exitLockedWarn || 0) - w0, d: +Math.hypot(h.x - o.x, h.y - o.y).toFixed(2) };
        // анчутка не может уйти в проход за выходом
        const a = g.spawnTest('anchutka', o.x, o.y - 3, 2); a.setPath(m, beyond[0], beyond[1]); const L = a.path && a.path[a.path.length - 1]; out.anchPath = !!L && Math.hypot((L.x ?? L[0]) - beyond[0], (L.y ?? L[1]) - beyond[1]) < 0.6; g.enemies = g.enemies.filter(e => e !== a);
        // тропа открыта: бой у выхода не уводит на тропу, приказ идти в выход — уводит
        g.quest.flags.trailOpen = true; g.simulate(0.05); out.open = { wall: !!o.wall, reachBeyond: m.isReachableAt(...beyond) };
        const b = g.spawnTest('upyr', o.x + 0.3, o.y + 1.4, 1); b.stagger = 1e9; h.x = o.x; h.y = o.y - 2.5; h.stop(); let stay = true;
        g.simulate(4, () => { if (g.zone.id !== 'zalesye') stay = false; if (!h.cmd && !h.action && !b.dead) h.attack(b, false, null, true); return b.dead || !stay; });
        out.fight = { stay, dead: b.dead, passedCircle: (g.counters.exitNoIntent || 0) > 0 };
        g.enemies = g.enemies.filter(e => e !== b); h.stop(); h.moveTo(m, o.x, o.y); g.simulate(3, () => g.zone.id === 'trail'); out.go = g.zone.id;
        g.enterZone('zalesye', 'from_trail'); g.quest.flags.trailOpen = false; g.simulate(0.05); out.relock = !!o.wall; h.hp = h.maxHp; for (const e of g.enemies) e.stagger = 0; return out; })()''')
    check('QA B-28: закрытый выход — стена (герой не выталкивается, враги не уходят в проход), сообщение и звук один раз на попытку; открытый — переход только по приказу',
          s['wall'] and not s['reachBeyond'] and s['hold']['zone'] == 'zalesye' and s['hold']['warns'] == 1 and s['hold']['pushedBack'] == 0 and s['click']['warns'] == 2
          and not s['anchPath'] and not s['open']['wall'] and s['open']['reachBeyond'] and s['fight']['stay'] and s['go'] == 'trail' and s['relock'], s)
    s = await G('''(async () => { const g = __game, { Hero } = await import('/src/entities/hero.js'); __SEED__
        const m = g.map, o = g.objectById('to_trail'), stash = g.enemies, keep = g.hero; const key = (p) => p.kinds.slice().sort().join(',');
        const P = m.packs.map((p, i) => [i, p]).filter(([i, p]) => p.mlvl === 2 && key(p) === 'anchutka,upyr,upyr,upyr').sort((a, b) => Math.hypot(a[1].x - o.x, a[1].y - o.y) - Math.hypot(b[1].x - o.x, b[1].y - o.y))[0];
        const pk = P[1], spots = stash.filter(e => e.pack === P[0]).map(e => [e.kind, e.homeX, e.homeY]);
        const res = { pack: P[0], dExit: +Math.hypot(pk.x - o.x, pk.y - o.y).toFixed(1), runs: 0, deaths: 0, time: [], hpLeft: [], exitWarn: 0, zoneLeft: 0 };
        const dx = pk.x - o.x, dy = pk.y - o.y, dl = Math.hypot(dx, dy) || 1;
        for (let i = 0; i < 30; i++) {
          g.enemies = []; g.combat.projectiles.length = 0; g.combat.fires = []; g.state = 'play';
          const h = new Hero(pk.x + dx / dl * 6, pk.y + dy / dl * 6); let n = 0; while (h.level < 2 && n++ < 5) h.gainXp(g.dbg.xpToNext(h.level), g);
          h.base.vit += 2; h.base.str += 2; h.base.dex += 1; h.points = 0; h.skills.sshibka = 2; h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar; h.belt = [null, null, null, null]; h.levelFx = 0; g.hero = h;
          const es = spots.map(([k, x, y]) => { const e = g.spawnTest(k, x, y, 2); e.aggro(g, false); return e; });
          const w0 = g.counters.exitLockedWarn || 0; let tt = 0;
          g.simulate(90, () => { tt += 1 / 60; if (h.dead || g.zone.id !== 'zalesye') return true; let t = null, bd = 1e9; for (const e of es) { if (e.dead) continue; const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; t = e; } }
            if (!t) return true; if (!h.cmd && !h.action) h.attack(t, false, h.lmbSkill(), true); return false; });
          res.runs++; if (h.dead) res.deaths++; else res.hpLeft.push(h.hp / h.maxHp); res.time.push(tt); res.exitWarn += (g.counters.exitLockedWarn || 0) - w0; if (g.zone.id !== 'zalesye') { res.zoneLeft++; g.enterZone('zalesye', 'from_trail'); }
        }
        const mean = (a) => a.length ? +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2) : 0;
        res.time = mean(res.time); res.hpLeft = Math.round(mean(res.hpLeft) * 100); g.enemies = stash; g.hero = keep; g.state = 'play'; Math.random = rnd0; return res; })()'''.replace('__SEED__', SEEDED))
    print('БАЛАНС B-28 (смешанная стая у выхода, 2 ур., без зелий):', json.dumps(s, ensure_ascii=False), flush=True)
    check('QA B-28: 2 ур. против смешанной стаи у выхода (3 упыря + анчутка mlvl 2) на настоящем месте, тропа закрыта — смертей ≤ 5 из 30',
          s['runs'] == 30 and s['deaths'] <= 5 and s['zoneLeft'] == 0, s)

    # QA B-26: уход из Залесья посреди диалога Мала
    s = await G('''(() => { const g = __game; const o = g.objectById('hut3'); g.interact(o); g.simulate(3);
        const pend = g.dialogQ.map(l => l.text), before = { q: pend.length, mal: g.npcs.filter(n => n.kind === 'mal').length, open: g.quest.flag('trailOpen') };
        g.enterZone('trail', 'from_zalesye'); for (const e of g.enemies) e.stagger = 1e9; let over = 0;
        g.simulate(9, () => { if (g.fx.texts.some(x => pend.includes(x.str))) over++; return false; });
        const after = { q: g.dialogQ.length, over };
        g.enterZone('zalesye', 'from_trail'); g.simulate(1); after.malBack = g.npcs.filter(n => n.kind === 'mal' && !n.gone).length;
        for (const e of g.enemies) e.stagger = 0; return { before, after }; })()''')
    check('QA B-26: ушёл на тропу посреди диалога Мала — реплики не висят над Ратибором (только журнал), Мал не застревает у избы 3',
          s['before']['q'] > 0 and s['before']['mal'] == 1 and s['before']['open'] and s['after']['q'] == 0 and s['after']['over'] == 0 and s['after']['malBack'] == 0, s)
    # QA B-27: уведомление при открытом окне — ниже трекера и мини-карты
    out = {}
    for win in ('invOpen', 'charOpen', 'skillsOpen'):
        await G(f'(() => {{ const g = __game; g.ui.closeAll(); g.ui.{win} = true; g.notify("Морозко → F3, Оберег → F1 — проверка длинного уведомления при открытом окне", "#fff"); }})()')
        await wait(120)
        out[win] = await G('__game._noticeBox')
    await G('__game.ui.closeAll(); __game.notice = null')
    check('QA B-27: уведомления при открытом окне (котомка, «Витязь», «Навыки») — ниже трекера и мини-карты (y ≥ 160), в ширину свободной части',
          all(v and v['y'] >= 160 and v['w'] <= 300 for v in out.values()), out)

    # п.1, п.2, п.6: числа дизайнера в данных; принятые заглушки больше не помечены
    s = await G('''(() => { const C = __game.dbg.CFG, a = C.monsters.chernoyarets_arsonist, T = a.torch;
        const ph = []; const walk = (o, path) => { if (!o || typeof o !== 'object') return; for (const [k, v] of Object.entries(o)) { if (k === '_ph') ph.push(path + ':' + v.join(',')); else walk(v, path + '.' + k); } };
        walk(C.quests, 'quests'); walk(C.zones.zalesye, 'zalesye'); walk(C.zones.trail, 'trail'); walk(C.stats.restFx, 'restFx');
        return { r: a.r, reach: a.reach, aggro: a.aggro, T: [T.rangeMin, T.rangeMax, T.towardSelf, T.flightTime, T.telegraph, T.radius, T.burn, T.dpsMul, T.tick, T.cooldown, T.maxZones],
          sight: (C.quests.events || {}).arsonistSightRange, clear: C.zones.zalesye.interact.clearRadius, amb: C.zones.trail.ambush, ring: C.stats.restFx.ringFade,
          inv: [C.stats.death.respawnInvuln, C.stats.death.respawnInvulnBreaksOnAction], ph }; })()''')
    acc = ('sightRange', 'clearRadius', 'trigger', 'rise', 'ringFade')
    check('M1b п.1/п.2/п.6: поджигатель r 0,4 / досяг 1,0 / агро 9, факел 2–6, 1,5 ближе, полёт 0,6, телеграф 0,8, r 1, 4 с, 0,8×, тик 0,5, КД 8, одна зона; заглушки приняты; неуязвимость 2 с снимается действием',
          s['r'] == 0.4 and s['reach'] == 1.0 and s['aggro'] == 9 and s['T'] == [2, 6, 1.5, 0.6, 0.8, 1.0, 4, 0.8, 0.5, 8, 1]
          and s['sight'] == 9 and s['clear'] == 4 and s['ring'] == 0.25 and s['inv'] == [2, True]
          and not any(k in p for p in s['ph'] for k in acc), s)

    # п.1: тайминги факела на тропе (замах до кадра 3, полёт 0,6 с при любой дистанции, телеграф с броска 0,8 с, огонь в конце телеграфа)
    s = await G('''(() => { const g = __game, h = g.hero; g.enterZone('trail', 'from_zalesye'); const m = g.map;
        const P = m.packs.findIndex(p => p.kinds.every(k => k === 'chernoyarets_arsonist')); for (const e of g.enemies) e.stagger = 1e9;
        const a = g.enemies.find(e => e.pack === P && !e.dead); a.stagger = 0; a.torchCd = 0; const out = { runs: [] };
        for (const dist of [3, 5.5]) {
          const hx = a.homeX - dist; h.x = hx; h.y = m.yc(hx); h.cmd = null; h.path = null; h.action = null; h.hp = h.maxHp; h.invuln = 0; h.graceT = 0;
          a.x = a.homeX; a.y = h.y; a.state = 'idle'; a.torchCd = 0; g.combat.fires = []; a.aggro(g, false);
          let tTorch = null, tThrow = null, tt = 0; g.simulate(3, () => { tt += 1 / 60; if (tTorch === null && a.state === 'torch') tTorch = tt; if (g.combat.fires.length) { tThrow = tt; return true; } return false; });
          const f = g.combat.fires[0]; if (!f) { out.runs.push({ fail: true, st: a.state }); continue; }
          const tgt = Math.hypot(h.x - a.x, h.y - a.y), cl = +(tgt - Math.hypot(f.x - a.x, f.y - a.y)).toFixed(2);
          a.stagger = 1e9; const s = []; for (const T of [0.55, 0.65, 0.78, 0.83]) { g.simulate(T - f.t); s.push([+f.t.toFixed(2), f.lit]); }
          out.runs.push({ windup: +(tThrow - tTorch).toFixed(2), flight: f.flight, tele: f.tele, closer: cl, s, cd: +a.torchCd.toFixed(1) }); a.stagger = 0; }
        g.combat.fires = []; h.invuln = 0; for (const e of g.enemies) e.stagger = 1e9; g.enterZone('zalesye', 'from_trail'); return out; })()''')
    ok = len(s['runs']) == 2 and all(not r.get('fail') and abs(r['windup'] - 0.3) <= 0.05 and r['flight'] == 0.6 and r['tele'] == 0.8 and abs(r['closer'] - 1.5) < 0.05
                                     and [x[1] for x in r['s']] == [False, False, False, True] and r['cd'] > 7 for r in s['runs'])
    check('M1b п.1: факел — замах 0,3 с (кадр 3), полёт 0,6 с на 3 и 5,5 тайла, телеграф с момента броска 0,8 с, огонь вспыхивает в конце телеграфа', ok, s)

    # п.4: счётчика N/28 в HUD нет — только в отладочном слое; п.5: F-панель — иконка, клавиша, имя в подсказке
    s = await G('''(async () => { const g = __game, { LAYOUT } = await import('/src/render/hud.js'); const k = g.zoneKills(); const f = LAYOUT.f[0];
        return { k, debug: !!g.debug, lines: g.quest.lines().map(l => l.text + ' ' + (l.count || '')), f: [f.x + f.s / 2, f.y + f.s / 2], key: f.key, bar0: g.hero.bar[0] }; })()''')
    await pg.mouse.move(*(await client_scr(*s['f']))); await wait(120)
    tip = await G('__game._tip')
    await pg.mouse.move(960, 400)
    check('M1b п.4/п.5: «Убито N/28» только в отладочном слое (?debug), в трекере нет; F1–F6 — иконка и «F1», полное имя в подсказке',
          s['k']['total'] == 28 and not s['debug'] and not any('/28' in x for x in s['lines']) and s['key'] == 'F1' and tip and tip['slot'] == 0, {**s, 'tip': tip})

    # п.6: неуязвимость возрождения 2 с снимается атакой
    s = await G('''(() => { const g = __game, h = g.hero; h.invuln = 0; h.graceT = 0; h.dashing = null; h.takeDamage(99999, g, 'fire'); g.respawnHero();
        const inv0 = +h.invuln.toFixed(2), rp = h.respawnProt; const e = g.spawnTest('upyr', h.x + 1.2, h.y, 1); e.stagger = 1e9; h.attack(e, false, null, true); g.simulate(0.1);
        const out = { inv0, rp, inv1: h.invuln, broken: g.counters.respawnInvulnBroken || 0, zone: g.zone.id }; e.takeDamage(9999, g, 'melee', null);
        g.enemies = g.enemies.filter(x => x !== e); h.hp = h.maxHp; return out; })()''')
    check('M1b п.6: после возрождения неуязвимость 2 с, атака снимает её досрочно', s['inv0'] == 2 and s['rp'] and s['inv1'] == 0 and s['broken'] == 1 and s['zone'] == 'zalesye', s)

    # Мара Пепельная: былинный враг mlvl 4 в Залесье, свита анчуток, бродит по кругу, пепельный след, лечит свиту
    s = await G('''(() => { const g = __game, h = g.hero, M = g.enemies.find(e => e.kind === 'mara'); if (!M) return { fail: 'no mara' };
        const B = g.dbg.CFG.bosses.mara, ret = g.enemies.filter(e => e.special && e !== M);
        const out = { elite: M.elite, mlvl: M.mlvl, hp: M.maxHp, dmg: [M.dmgMin, M.dmgMax], xp: M.xp, mods: M.mods, res: M.res.fire, ret: ret.length, retK: [...new Set(ret.map(e => e.kind + '@' + e.mlvl))], title: g.dbg ? null : null };
        h.x = g.map.krada.x; h.y = g.map.krada.y; const c = B.route.center, d0 = [];
        let moved = 0, px = M.x, py = M.y; const patch0 = g.combat.fires.filter(f => f.kind === 'trail' && f.src === M).length;
        g.simulate(12, () => { d0.push(Math.hypot(M.x - c[0], M.y - c[1])); moved += Math.hypot(M.x - px, M.y - py); px = M.x; py = M.y; return false; });
        out.route = { min: +Math.min(...d0).toFixed(1), max: +Math.max(...d0).toFixed(1), moved: +moved.toFixed(1) };
        out.patches = g.combat.fires.filter(f => f.kind === 'trail' && f.src === M).length; out.follow = ret.filter(e => e.follow === M).length;
        // лечение свиты
        ret[0].hp = 1; M.healT = 0; g.simulate(B.heal.every + 0.2); out.healed = ret[0].hp > 1;
        // бой: герой рядом — реплика при агро, урон пепельного следа 8% HP/с
        h.x = M.x - 3; h.y = M.y; h.invuln = 0; h.graceT = 0; M.aggro(g, false); g.simulate(1.0, () => { h.hp = h.maxHp; return false; }); out.aggroBark = g._barks['elite.mara.aggro'] != null;
        const items0 = g.loot.items.length; for (const e of ret) e.takeDamage(99999, g, 'melee', null); M.takeDamage(99999, g, 'melee', null); g.simulate(0.3);
        const drops = g.loot.items.slice(items0).filter(i => i.item); out.drops = drops.map(i => i.item.rarity); out.deathBark = g._barks['elite.mara.death'] != null;
        h.invuln = 0; h.hp = h.maxHp; return out; })()''')
    ok = (not s.get('fail') and s['elite'] == 'bylina' and s['mlvl'] == 4 and s['hp'] == 258 and s['dmg'] == [8, 18] and s['mods'] == ['hot'] and 4 <= s['ret'] <= 6
          and s['retK'] == ['anchutka@2'] and s['route']['moved'] > 8 and s['route']['max'] <= 8.5 and s['patches'] > 0 and s['follow'] == s['ret']
          and s['healed'] and s['aggroBark'] and s['deathBark'] and len(s['drops']) >= 1 and any(r != 'normal' for r in s['drops']))
    check('Мара Пепельная: былинная (mlvl 4, 258 HP, 8–18, «Жаркая»), свита 4–6 анчуток mlvl 2, кружит по Залесью, пепельный след, лечит свиту, реплики, добыча ≥ 1 заговорённой', ok, s)

    # вожаки: в Залесье нет; на тропе 1 во второй половине (mlvl 3, упырь или анчутка); имя из генератора act1 §9
    s = await G('''(() => { const g = __game, C = g.dbg.CFG, z0 = g.enemies.filter(e => e.leader).length; g.enterZone('trail', 'from_zalesye');
        const L = [...g.enemies, ...g.buried].filter(e => e.leader); const ng = C.ru['namegen.leader'] || C.ru.namegen && C.ru.namegen.leader;
        const out = { z0, n: L.length, L: L.map(e => ({ k: e.kind, m: e.mlvl, x: Math.round(e.x), name: e.name, mods: e.mods, hp: e.maxHp, base: g.dbg.enemyStats(e.kind, e.mlvl).hp, ret: [...g.enemies, ...g.buried].filter(r => r.retinue && r.pack === e.pack).length })), w: g.map.w };
        for (const e of g.enemies) e.stagger = 1e9; g.enterZone('zalesye', 'from_trail'); return out; })()''')
    L = s['L'][0] if s['L'] else {}
    check('вожаки М1: в Залесье нет; на тропе один во второй половине, mlvl 3, упырь или анчутка, ×4 HP, 1 модификатор, свита 3–5, имя из двух слов',
          s['z0'] == 0 and s['n'] == 1 and L.get('k') in ('upyr', 'anchutka') and L.get('m') == 3 and L.get('x', 0) >= s['w'] / 2 and L.get('hp') == 4 * L.get('base', 0)
          and len(L.get('mods', [])) == 1 and 3 <= L.get('ret', 0) <= 5 and len(L.get('name', '').split(' ')) == 2, s)

    # переход тропа → капище через ворота, возрождение до и после Чурова камня
    s = await G('''(() => { const g = __game, h = g.hero; g.enterZone('trail', 'from_zalesye'); for (const e of g.enemies) e.stagger = 1e9;
        const o = g.objectById('kapishche_gate'), st = g.objectById('chur_kapishche'), out = { rp0: g.respawnPoint().zone };
        h.invuln = 0; h.graceT = 0; h.takeDamage(99999, g, 'fire'); g.respawnHero(); out.die0 = [g.zone.id, +Math.hypot(h.x - g.map.krada.x, h.y - g.map.krada.y).toFixed(1)];
        g.enterZone('trail', 'from_zalesye'); for (const e of g.enemies) e.stagger = 1e9; for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - st.x, e.y - st.y) < 12) e.takeDamage(99999, g, 'melee', null);
        h.x = st.sx; h.y = st.sy + 1.4; h.cmd = null; g.simulate(0.3); out.far = g.quest.flag('churTouched');           // 2,3 тайла — ещё не коснулся
        h.x = st.sx; h.y = st.sy + 0.4; g.simulate(0.3, () => g.quest.flag('churTouched'));                                  // 1,3 тайла — коснулся
        out.touched = g.quest.flag('churTouched'); out.ev = g.quest.events.some(e => e.event === 'churTouched'); out.rp1 = g.respawnPoint().zone;
        h.x = o.x - 2; h.y = o.y; h.cmd = null; h.moveTo(g.map, o.x, o.y); g.simulate(3, () => g.zone.id === 'kapishche');
        const fe = g.map.entries.from_trail; out.kap = { zone: g.zone.id, band: g.zone.band, mlvl: g.zone.mlvl, d: +Math.hypot(h.x - fe.x, h.y - fe.y).toFixed(1), safe: g.zone.safeZones.length,
          lines: g.quest.lines().map(l => l.text + (l.count ? ' ' + l.count : '')), q: [g.quest.get('hearths').state, g.quest.get('krivsha').state] };
        h.invuln = 0; h.graceT = 0; h.takeDamage(99999, g, 'fire'); g.respawnHero(); out.die1 = [g.zone.id, +Math.hypot(h.x - st.x, h.y - st.y).toFixed(1), h.invuln];
        out.log = g.log.lines.slice(-3).map(l => l.text || l);
        // выход из капища обратно на тропу
        g.enterZone('kapishche', 'from_trail'); const x = g.objectById('to_trail'); h.x = x.x + 2; h.y = x.y; h.cmd = null; h.moveTo(g.map, x.x, x.y);
        g.simulate(3, () => g.zone.id === 'trail'); out.back = g.zone.id; return out; })()''')
    k = s['kap']
    check('тропа → капище: ворота ведут в капище (mlvl 4–5, без тихих кругов), трекер «Отбей огнища у упырей 0/3» и «Одолей Крившу»; выход обратно на тропу',
          k['zone'] == 'kapishche' and k['mlvl'] == [4, 5] and k['safe'] == 0 and k['d'] < 2.5 and k['band'][0] == 'Капище Перуна'
          and any('Отбей огнища у упырей 0/3' in l for l in k['lines']) and k['q'] == ['active', 'active'] and s['back'] == 'trail', s)
    check('возрождение: у крады Залесья, пока не тронут Чуров камень у капища; коснулся — возрождение у камня (тропа)',
          s['rp0'] == 'zalesye' and not s['far'] and s['die0'][0] == 'zalesye' and s['die0'][1] < 5 and s['touched'] and s['ev'] and s['rp1'] == 'trail'
          and s['die1'][0] == 'trail' and s['die1'][1] < 5 and s['die1'][2] > 0, s)

    # состав капища, вожаки у огнищ 1 и 2, матёрые у третьего, «Чад»
    s = await G('''(() => { const g = __game, h = g.hero; const chadOut = h.chad || 0, reg0 = h.yarRegen, ar0 = h.ar; g.enterZone('kapishche', 'from_trail'); const m = g.map;
        const all = [...g.enemies, ...g.buried].filter(e => !e.boss), cnt = {}; for (const e of all) { const k = e.kind[0] + '@' + e.mlvl; cnt[k] = (cnt[k] || 0) + 1; }
        const hs = m.hearths.map(o => [o.id, o.x, o.y]); const near = (e) => { let b = null, bd = 1e9; for (const o of m.hearths) { const d = Math.hypot(e.x - o.x, e.y - o.y); if (d < bd) { bd = d; b = o.id; } } return [b, +bd.toFixed(1)]; };
        const lead = all.filter(e => e.leader).map(e => ({ k: e.kind, m: e.mlvl, at: near(e), name: e.name, hp: e.maxHp / g.dbg.enemyStats(e.kind, e.mlvl).hp }));
        const champ = all.filter(e => e.elite === 'champion').map(e => ({ k: e.kind, m: e.mlvl, at: near(e), hp: e.maxHp / g.dbg.enemyStats(e.kind, e.mlvl).hp }));
        g.simulate(0.05); const out = { cnt, n: all.length, lead, champ, chad: h.chad, reg: +(h.yarRegen / reg0).toFixed(2), ar: +(h.ar / ar0).toFixed(3), chadOut, debuffTxt: g.dbg.CFG.ru['ui.debuff.chad'] };
        g.enterZone('trail', 'from_trail' in g.zoneStates.trail.map.entries ? 'from_trail' : 'gate'); out.chadTrail = h.chad; out.regBack = +(h.yarRegen / reg0).toFixed(2);
        g.enterZone('kapishche', 'from_trail'); g.simulate(0.05); out.chadBack = h.chad; return out; })()''')
    c = s['cnt']
    check('капище (GDD v1.8 §8.2): 90 врагов — 30 mlvl 4 (упыри 14 / анчутки 10 / поджигатели 6) + 60 mlvl 5 (25 / 19 / 16); вожаки у огнищ 1 (mlvl 4) и 2 (mlvl 5), не поджигатели, ×4 HP; 16 матёрых упырей (×3 HP), из них 3 у третьего огнища',
          s['n'] == 90 and (c.get('u@4'), c.get('a@4'), c.get('c@4'), c.get('u@5'), c.get('a@5'), c.get('c@5')) == (14, 10, 6, 25, 19, 16)
          and sorted((l['at'][0], l['m']) for l in s['lead']) == [('hearth1', 4), ('hearth2', 5)] and all(l['k'] != 'chernoyarets_arsonist' and l['hp'] == 4 and l['at'][1] <= 6.5 for l in s['lead'])
          and len(s['champ']) == 16 and all(x['hp'] == 3 and x['k'] == 'upyr' for x in s['champ']) and sum(x['at'][0] == 'hearth3' and x['at'][1] <= 6.5 for x in s['champ']) == 3, s)
    check('«Чад» (GDD §4.4): в капище 3 ступени — Ярь −30%, меткость −15%; на тропе снимается, при возвращении снова 3',
          s['chad'] == 3 and s['reg'] == 0.7 and abs(s['ar'] - 0.85) < 0.01 and s['chadTrail'] == 0 and s['regBack'] == 1.0 and s['chadBack'] == 3, s)

    # огнище: пока жива пачка — нельзя; перебили — держать 3 с, урон прерывает; освящено — минус ступень Чада, цель 1/3
    s = await G('''(() => { const g = __game, h = g.hero, m = g.map, o = m.hearths.find(x => x.id === 'hearth1'); for (const e of g.enemies) e.stagger = 1e9;
        const P = m.packs.findIndex(p => p.role === 'hearth1'); const out = { blocked: g.canInteract(o) };
        for (const e of [...g.enemies]) if (!e.dead && (e.pack === P || Math.hypot(e.x - o.x, e.y - o.y) < 6)) e.takeDamage(99999, g, 'melee', null); g.simulate(0.3);
        out.free = g.canInteract(o); h.x = o.sx; h.y = o.sy; h.cmd = null; h.action = null; g.autoHold = true; h.interact(o);
        let tt = 0; g.simulate(5, () => { tt += 1 / 60; return o.done; }); g.autoHold = false;
        out.t = +tt.toFixed(2); out.done = o.done; out.cursed = o.prop.cursed; out.chad = h.chad; out.q = g.quest.get('hearths').n; out.bark = Object.keys(g._barks).filter(k => k.startsWith('bark.m1.hearth'));
        return out; })()''')
    check('огнище 1: при живой пачке «враги рядом»; перебили — освящение удержанием 3 с, пламя тёплое, «Чад» 2, цель 1/3, реплика',
          s['blocked'] == 'ui.obj.enemies_near' and s['free'] is None and s['done'] and 3.0 <= s['t'] <= 3.8 and not s['cursed'] and s['chad'] == 2 and s['q'] == 1 and 'bark.m1.hearth1' in s['bark'], s)

    # Кривша: подъём при входе в Круг, удар когтями с телеграфом, призыв упырей, прыжок в неосвящённое огнище на 50%, гибель → грамота → цели
    s = await G('''(async () => { const g = __game, m = g.map; __PRE__ const keep = g.hero;
        for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - m.idol.x, e.y - m.idol.y) < 16) e.takeDamage(99999, g, 'melee', null); g.simulate(0.2);
        for (const e of g.enemies) e.stagger = 1e9;
        const h = await mkRef(6, [m.idol.x, m.idol.y + 9]); h.relics = keep.relics; h.letters = keep.letters; const out = { st0: g.zs.bossState };
        h.moveTo(m, m.idol.x, m.idol.y + 6); g.simulate(3, () => g.zs.bossState !== 'dormant'); const b = g.boss; out.rise = [g.zs.bossState, g.counters.bossRise, b && b.state, b && b.invuln];
        out.early = g._barks['bark.m1.circle_early'] != null; out.hpBar = !!g.boss;
        g.simulate(2.2); out.fight = b.state;
        // удар когтями: телеграф-конус появляется за 0,6 с до удара
        let tele = null, hitT = null, tt = 0; const c0 = g.counters.krivshaClaws || 0; h.cmd = null; h.x = b.x + 1.2; h.y = b.y;
        g.simulate(6, () => { tt += 1 / 60; h.hp = h.maxHp; const T = g.combat.teles.find(x => x.src === b); if (T && tele === null) tele = { t: tt, shape: T.shape, r: T.r, dur: T.dur }; if ((g.counters.krivshaClaws || 0) > c0) { hitT = tt; return true; } return false; });
        out.claw = { tele, hitT, dt: tele && hitT ? +(hitT - tele.t).toFixed(2) : null };
        // призыв: 2 упыря mlvl 5 раз в 15 с, не больше 4
        g.simulate(32, () => { h.hp = h.maxHp; return false; }); const mins = b.minions.filter(e => !e.dead); out.summon = { n: g.counters.krivshaSummons, alive: mins.length, kinds: [...new Set(mins.map(e => e.kind + '@' + e.mlvl))] };
        for (const e of mins) e.takeDamage(99999, g, 'melee', null);
        // фаза огнища на 50%: прыжок в ближайшее НЕосвящённое огнище, 2 с неуязвим, ореол, сопр. огню +25%
        b.hp = Math.ceil(b.maxHp * 0.5) + 2; b.takeDamage(10, g, 'melee', h); let J = null; g.simulate(1.2, () => { if (b.state === 'jump' && b.jump) J = b.jump; return false; });
        const near = (x, y) => m.hearths.map(o => [o.id, Math.hypot(o.x - x, o.y - y), o.done]).sort((a, c) => a[1] - c[1]);
        out.jump = { state: b.state, inv: b.invuln > 0, target: J && J.hearth.id, hdone: J && J.hearth.done };
        const dmgInv = b.takeDamage(500, g, 'melee', h); g.simulate(1.2); out.phase = { p: b.phase, aura: b.aura, fire: b.res.fire, dmgInv, bark: g._barks['boss.krivsha.hearth'] != null };
        // гибель: тело, грамота, цели (избы Залесья для сдачи миссии считаем спасёнными)
        const hq = g.quest.get('huts'); hq.n = 3; hq.state = 'done'; hq.doneT = -99; h.invuln = 0; const items0 = g.loot.items.length; b.takeDamage(99999, g, 'melee', h); g.simulate(0.4);
        const drops = g.loot.items.slice(items0).filter(i => i.item).map(i => i.item.rarity);
        const body = g.objectById('krivsha_body'); out.dead = { dead: b.dead, xp: b.xp, drops, body: !!body, perun: m.perun && m.perun.burning, q: g.quest.get('krivsha').state, bark: g._barks['boss.krivsha.death'] != null };
        h.x = body.sx; h.y = body.sy; h.cmd = null; h.interact(body); g.simulate(1.5, () => body.done);
        out.letter = { name: g.letter && g.letter.name, text: g.letter && g.letter.text, ars: g.quest.get('arsonist').state, mission: g.quest.missionDone, req: g.quest.obj.filter(o => o.def.required).map(o => o.id + ':' + o.state) };
        const r = g.objectById('gromovnik'); out.reward = !!r; if (r) { h.x = r.sx; h.y = r.sy; h.cmd = null; h.interact(r); g.simulate(1, () => r.done); out.rewardDone = r.done; }
        g.hero = keep; keep.relics = h.relics; keep.letters = h.letters; Math.random = rnd0; return out; })()'''.replace('__PRE__', SEEDED + REF_HERO))
    cl, ph, d = s['claw'], s['phase'], s['dead']
    check('Кривша: встаёт при входе в Круг огнищ (с неотбитыми огнищами — реплика «рано»), 2 с подъёма, полоса здоровья босса',
          s['st0'] == 'dormant' and s['rise'][0] == 'active' and s['rise'][1] == 'circle' and s['rise'][3] > 1.5 and s['early'] and s['hpBar'] and s['fight'] == 'fight', s['rise'])
    check('Кривша: удар когтями — конус 2 тайла с телеграфом 0,6 с; призыв 2 упырей mlvl 4 (GDD v1.8: раз в 20 с), живых не больше 4',
          cl['tele'] and cl['tele']['shape'] == 'cone' and cl['tele']['r'] == 2 and abs(cl['dt'] - 0.6) <= 0.05
          and s['summon']['alive'] <= 4 and s['summon']['n'] >= 4 and s['summon']['kinds'] == ['upyr@4'], {'claw': cl, 'summon': s['summon']})
    check('Кривша: на 50% прыгает в неосвящённое огнище (2 с неуязвим), выходит с ореолом, +25% скорости атаки, сопр. огню +25%',
          s['jump']['state'] == 'jump' and s['jump']['inv'] and s['jump']['target'] in ('hearth2', 'hearth3') and s['jump']['hdone'] is False
          and ph['p'] == 2 and ph['aura'] and ph['fire'] == 0.25 and ph['dmgInv'] == 0 and ph['bark'], {'jump': s['jump'], 'phase': ph})
    check('Кривша пал: 1200 опыта, добыча 4 предмета (≥ 2 заговорённых), идол гаснет, «Одолей Крившу» выполнена; грамота «Приказ Чернояра» закрывает «Найди поджигателя»; миссия сдана; «Громовник» у подножия идола (вещь — проверки M1c)',
          d['dead'] and d['xp'] == 1200 and len(d['drops']) == 4 and sum(r != 'normal' for r in d['drops']) >= 2 and d['body'] and d['perun'] is False and d['q'] == 'done' and d['bark']
          and s['letter']['name'] == 'Приказ Чернояра' and s['letter']['ars'] == 'done' and s['letter']['mission'] and s['reward'] and s.get('rewardDone'), {'dead': d, 'letter': s['letter']})

    # все три огнища отбиты до боя — фазы нет; подъём от третьего огнища
    s = await G('''(async () => { const g = __game; __PRE__
        g.zoneStates.kapishche = null; delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map, keep = g.hero;
        for (const e of g.enemies) e.takeDamage(99999, g, 'melee', null); for (const e of g.buried) e.hp = 0; g.buried = []; g.simulate(0.3);
        const h = await mkRef(6, [m.hearths[0].sx, m.hearths[0].sy]); g.autoHold = true; const out = { freed: [] };
        for (const o of m.hearths) { h.x = o.sx; h.y = o.sy; h.cmd = null; h.interact(o); g.simulate(4, () => o.done); out.freed.push(o.done); }
        g.autoHold = false; const b = g.boss; out.rise = [g.zs.bossState, g.counters.bossRise, h.chad]; if (!b) { g.hero = keep; Math.random = rnd0; return out; }
        g.simulate(2.3); b.hp = Math.ceil(b.maxHp * 0.5) + 2; h.x = b.x + 1.2; h.y = b.y; b.takeDamage(10, g, 'melee', h); g.simulate(1.5);
        out.after = { state: b.state, phase: b.phase, aura: b.aura, fire: b.res.fire, noPhase: g.counters.krivshaNoPhase || 0 };
        g.hero = keep; Math.random = rnd0; return out; })()'''.replace('__PRE__', SEEDED + REF_HERO))
    check('все три огнища отбиты: Кривша встаёт от третьего огнища, «Чад» снят, огненной фазы нет (сопр. огню 0)',
          s['freed'] == [True, True, True] and s['rise'][0] == 'active' and s['rise'][1] == 'hearth3' and s['rise'][2] == 0
          and s.get('after', {}).get('phase') == 1 and not s['after']['aura'] and s['after']['fire'] == 0 and s['after']['noPhase'] >= 1, s)

    # замеры баланса: бой с Крившей (эталонный герой 6 ур. §9.1, «Сшибка», без зелий, HP героя восполняем — меряем время), опыт М1
    bal = await G('''(async () => { const g = __game; __PRE__
        const out = {};
        // focus — бьёт Крившу, упыря — только если тот заслонил путь (Кривша дальше 2,2 тайла; 1,5 с без замаха — ближайшего упыря, где бы он ни был); clear — сначала всех упырей вплотную (≤ 1,6 тайла)
        const fight = async (withPhase, refill, clear) => { const res = [];
          for (let i = 0; i < 4; i++) {
            delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map; g.enemies = []; g.buried = [];
            if (!withPhase) for (const o of m.hearths) { o.done = true; if (o.prop) o.prop.cursed = false; }
            const h = await mkRef(6, [m.idol.x, m.idol.y + 3]); g.applyChad(); const b = g.riseBoss('test'); let hpMin = 1;
            let tt = 0, swing = 0;   // застрял (1,5 с без замаха — Крившу заслонили упыри) — бьёт ближайшего упыря
            const near = () => { let best = b, bd = 1e9; const stuck = tt - swing > 1.5; if (!clear && !stuck && Math.hypot(b.x - h.x, b.y - h.y) <= 2.2) return b; for (const e of g.enemies) if (!e.dead && e !== b && Math.hypot(e.x - h.x, e.y - h.y) < (stuck ? 99 : 1.6)) { const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; best = e; } } return best; };
            g.simulate(300, () => { tt += 1 / 60; if (h.action) swing = tt; if (refill) h.hp = h.maxHp * 50; hpMin = Math.min(hpMin, h.hp / h.maxHp); if (b.dead || h.dead) return true; if (!h.action && b.state !== 'rise') { const tg = near(); if (!h.cmd || (tt - swing > 1.5 && h.cmd.target !== tg)) { if (h.cmd) swing = tt - 0.5; h.cmd = null; h.attack(tg, false, h.lmbSkill(), true); } } return false; });
            res.push({ t: +b.fightT.toFixed(1), dead: b.dead, heroDead: h.dead, phase: b.phase, summons: g.counters.krivshaSummons }); g.counters.krivshaSummons = 0; g.state = 'play'; }
          const ok = res.filter(r => r.dead); return { runs: res.length, killed: ok.length, mean: ok.length ? +(ok.reduce((a, r) => a + r.t, 0) / ok.length).toFixed(1) : null,
            min: ok.length ? Math.min(...ok.map(r => r.t)) : null, max: ok.length ? Math.max(...ok.map(r => r.t)) : null, heroDeaths: res.filter(r => r.heroDead).length }; };
        const keep = g.hero; out.focus_phase = await fight(true, true, false); out.focus_noPhase = await fight(false, true, false);
        out.clear_phase = await fight(true, true, true); out.clear_noPhase = await fight(false, true, true);
        out.noPotions_phase = await fight(true, false, false); out.noPotions_noPhase = await fight(false, false, false);
        // опыт М1 по зонам: Залесье + тропа + капище (с элитами) + Мара + Кривша
        const xpOf = (st) => [...st.enemies, ...st.buried].filter(e => !e.boss).reduce((a, e) => a + e.xp, 0);
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail');
        const z = g.zoneStates; const xz = xpOf(z.zalesye), xt = xpOf(z.trail), xk = xpOf(z.kapishche), xb = g.dbg.CFG.bosses.krivsha.xp;
        const lvl = (xp) => { let L = 1, need = 0; while (need + g.dbg.xpToNext(L) <= xp) { need += g.dbg.xpToNext(L); L++; } return [L, +((xp - need) / g.dbg.xpToNext(L)).toFixed(2)]; };
        out.xp = { zalesye: xz, trail: xt, kapishche: xk, beforeBoss: xz + xt + xk, afterBoss: xz + xt + xk + xb, lvlBefore: lvl(xz + xt + xk), lvlAfter: lvl(xz + xt + xk + xb), lvlTrail: lvl(xz + xt) };
        g.hero = keep; Math.random = rnd0; return out; })()'''.replace('__PRE__', SEEDED + REF_HERO))
    print('БАЛАНС M1b:', json.dumps(bal, ensure_ascii=False), flush=True)
    kp, kn = bal['focus_phase'], bal['focus_noPhase']
    check('замер: Кривша убиваем эталонным героем 6 ур. (§9.1, HP восполняется) — с огненной фазой дольше, чем без неё (цели GDD 70–80 / 60–75 с; расхождение — в отчёте)',
          kp['killed'] == kp['runs'] and kn['killed'] == kn['runs'] and kp['mean'] >= kn['mean'], bal)
    x = bal['xp']
    check('замер: опыт М1 — до босса ≈ 6 ур. (GDD ≈ 5 900), после Кривши ≈ 7 ур. (≈ 7 120)', x['lvlBefore'][0] in (5, 6) and x['lvlAfter'][0] in (6, 7), x)

    # скриншот: бой с Крившей в капище, трекер
    sc = await G('''(async () => { const g = __game; __PRE__
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map;
        for (const e of g.enemies) if (Math.hypot(e.x - m.idol.x, e.y - m.idol.y) < 9) e.takeDamage(99999, g, 'melee', null); g.simulate(0.2);
        const { Quest } = await import('/src/systems/quest.js'); g.quest = new Quest(g); for (const id of ['reach', 'huts']) { const o = g.quest.get(id); o.state = 'done'; o.doneT = -99; o.n = 3; }
        g.quest.emit({ event: 'zoneEnter', zone: 'kapishche' }); g.quest.get('arsonist').state = 'active';
        g.quest.get('hearths').n = 1; const o1 = m.hearths.find(o => o.id === 'hearth1'); o1.done = true; o1.prop.cursed = false;
        const h = await mkRef(6, [m.idol.x - 1.5, m.idol.y + 4]); h.relics = ['knife']; h.letters = ['priest'];
        const b = g.riseBoss('test'); g.simulate(2.2); for (const e of g.enemies) if (e !== b) e.stagger = 1e9;
        b.x = m.idol.x + 0.6; b.y = m.idol.y + 2.6; b.hp = Math.round(b.maxHp * 0.62); b.summonT = 0; b.updateSummon(0.01, g); b.minions.forEach((e, i) => { e.state = 'idle'; e.stagger = 1e9; e.x = b.x + (i ? -2.6 : 2.4); e.y = b.y + (i ? 1.2 : -1.6); e.face(-1, 1); });
        h.x = b.x - 0.9; h.y = b.y + 1.7; h.hp = Math.round(h.maxHp * 0.7); h.face(1, -1); b.face(h.x - b.x, h.y - b.y);
        for (let i = 0; i < 6; i++) g.combat.addPatch(b, b.x + 0.4 + i * 0.5, b.y - 1.4 - i * 0.35, b.B.fireTrail);
        b.stagger = 1e9; b.startClaw(g); b.t = 0.3; const T = g.combat.teles.find(x => x.src === b); if (T) { T.t = 0.45; T.hold = true; T.onFire = null; }   // кадр: телеграф когтей g.lastTarget = b; b.lastHitT = 0;
        g.ui.closeAll(); g.letter = null; g.notice = null; g.log.lines.length = 0; g.time += 20; g.updateCamera(); Math.random = rnd0;
        return [h.x - 3.5, h.y + 2.5]; })()'''.replace('__PRE__', SEEDED + REF_HERO))
    await pg.mouse.move(*(await client_of(sc[0], sc[1], 0)))
    await wait(250)
    await pg.screenshot(path=SHOT_M1B)
    s = await G('''(() => { const g = __game; return { zone: g.zone.id, boss: g.boss && !g.boss.dead, bhp: g.boss && +(g.boss.hp / g.boss.maxHp).toFixed(2), bst: g.boss && g.boss.state, T: g.combat.teles.map(T => [T.shape, +T.t.toFixed(2), T.dur, T.r]), tele: g.combat.teles.length, lines: g.quest.lines().map(l => l.text + (l.count ? ' ' + l.count : '')) }; })()''')
    check('скриншот screenshot_m1b.png (1920×1080): бой с Крившей в капище, трекер огнищ и босса', os.path.exists(SHOT_M1B) and s['zone'] == 'kapishche' and s['boss'] and len(s['lines']) == 3 and 'Отбей огнища у упырей 1/3' in s['lines'], s)
    await G('(() => { const g = __game; for (const e of g.enemies) e.stagger = 1e9; g.combat.teles.length = 0; })()')

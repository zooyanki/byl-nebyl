"""Проверки вехи M1d (inbox/designer_v1_9.md, GDD v1.9): береста (заглушки сняты), запрет на арене живого босса и поводок пешком,
береста в поясе, выбор былинной, награда Мала, B-34 (сравнение рангов навыков), B-35 (воспроизводимость замера).
Вызываются из verify_playwright.py на свежей загрузке; отдельно — `--only-m1d`. Скриншот — screenshot_m1d.png."""
import os
from checks_m1c import SEEDED, CLEAR
from checks_v18 import FIGHT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_M1D = os.path.join(ROOT, 'screenshot_m1d.png')
# бросить пачки рядом и поставить героя (зона уже построена)
KAP = '''const toKap = (g) => { delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); g.portal && g._finalizePortal('test'); return g.map; };
  const quiet = (g, keep) => { for (const e of g.enemies) if (e !== keep) e.stagger = 1e9; };'''


async def run_m1d(pg, G, check, wait, client_of, client_scr, a):
    await pg.goto(a.url)
    await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=15000)
    await pg.mouse.move(960, 540)
    await pg.mouse.click(960, 300)
    await wait(200)
    print('--- веха M1d', flush=True)
    P = SEEDED + CLEAR + KAP

    # --- 1. береста: заглушки закрыты (GDD v1.9 п.3)
    s = await G('''(() => { const g = __game, h = g.hero, B = g.dbg.CFG.items_base.scrolls.beresta; __P__ if (g.zone.id !== 'zalesye') g.enterZone('zalesye', 'krada'); const k = g.map.krada; clearNear(g, 14);
        h.x = k.x + 14; h.y = k.y + 2; h.stop(); h.dir = 0; const n0 = h.scrollCount(); const it = h.inv.items.find(i => i.kind === 'scroll'); h.readScroll(it, g); g.simulate(1.1);
        const P = g.portal, [vx, vy] = h.dirVec(); const out = { ph: B._ph, reach: B.portalReach, dist: B.town.dist, life: B.portalLife, one: B.oneAtATime, cor: B.closeOnReturn, size: B.size, solid: B.solid, bstack: B.beltStack, stack: B.stack,
          used: n0 - h.scrollCount(), dField: +Math.hypot(P.field.x - h.x, P.field.y - h.y).toFixed(2), ahead: +((P.field.x - h.x) * vx + (P.field.y - h.y) * vy).toFixed(2),
          dTown: +Math.hypot(P.town.x - g.zoneStates.ladoga.map.krada.x, P.town.y - g.zoneStates.ladoga.map.krada.y).toFixed(2), reachObj: P.field.reach };
        // не препятствие: герой проходит сквозь проход по прямой
        const sx = P.field.x - 1.2, sy = P.field.y; h.x = sx; h.y = sy; h.stop(); h.cmd = { type: 'move', x: P.field.x + 1.2, y: P.field.y, retries: 0 }; h.moveTo(g.map, P.field.x + 1.2, P.field.y);
        let minD = 9; g.simulate(1.5, () => { minD = Math.min(minD, Math.hypot(h.x - P.field.x, h.y - P.field.y)); return false; }); out.walkThrough = +minD.toFixed(2); out.passed = h.x > P.field.x + 0.5;
        // пауза: таймер стоит; игровое время идёт и в «Ладоге» (у крады)
        const t0 = P.t; g.paused = true; g.simulate(5); out.pauseDt = +(P.t - t0).toFixed(3); g.paused = false;
        g.usePortal(P.field); out.inTown = g.zone.id; const t1 = P.t; g.simulate(2); out.townDt = +(P.t - t1).toFixed(2);
        // второй проход — снова в поле (в Ладоге при открытом проходе из поля береста не читается)
        g.enterZone('zalesye', { x: k.x + 14, y: k.y + 2 });
        const it2 = h.inv.items.find(i => i.kind === 'scroll'); h.x = k.x + 14; h.y = k.y + 2; h.stop(); h.readScroll(it2, g); g.simulate(1.1); out.replaced = g.portal !== P && !!g.portal;
        const P2 = g.portal; g.usePortal(P2.field); g.usePortal(P2.town); g.simulate(0.7); out.closedOnReturn = !g.portal;
        Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('M1d п.1 береста по GDD v1.9: щелчок 0,9, проход 1×1 не препятствие (герой проходит сквозь), в поле 1,3 перед героем, у крады 3,2, 60 с игрового времени '
          '(на паузе стоит, у крады идёт), один проход, закрывается при возврате; _ph сняты',
          s['ph'] == [] and s['reach'] == 0.9 and s['reachObj'] == 0.9 and s['dist'] == 3.2 and s['life'] == 60 and s['one'] and s['cor'] and s['size'] == [1, 1] and s['solid'] is False
          and s['used'] == 1 and abs(s['dField'] - 1.3) < 0.05 and s['ahead'] > 1.2 and abs(s['dTown'] - 3.2) < 0.45 and s['walkThrough'] < 0.3 and s['passed']
          and s['pauseDt'] == 0 and s['inTown'] == 'ladoga' and s['townDt'] > 1.9 and s['replaced'] and s['closedOnReturn'] and s['bstack'] == 5 and s['stack'] == 20, s)

    # --- 2. арена: до подъёма и при живом боссе в 12 от идола береста серая; в 12,5 — можно; после смерти — можно
    s = await G('''(() => { const g = __game, h = g.hero; __P__ const m = toKap(g); const I = m.idol; g.enemies = []; h.invuln = 99; h.addScroll('beresta', 5);
        const at = (d) => { h.x = I.x - d; h.y = I.y; h.stop(); h.action = null; };
        const tryRead = () => { g.notice = null; const n0 = h.scrollCount(); const it = h.inv.items.find(i => i.kind === 'scroll'); const ok = g.useScroll(it); const note = g.notice && g.notice.text, busy = { act: h.action && h.action.type, stun: h.stun, dead: h.dead }; g.simulate(1.1); const r = { ok, n: n0 - h.scrollCount(), note, portal: !!g.portal, grey: g.berestaGrey() }; if (!ok && !note) r.busy = busy; g.portal && g._finalizePortal('test'); return r; };
        const out = {}; at(11.8); out.dormant = tryRead(); out.state0 = g.zs.bossState; at(12.4); out.out12 = tryRead();
        at(5); const b = g.riseBoss('test'); g.simulate(2.3); quiet(g, b); b.stagger = 1e9; out.alive = tryRead();
        b.hp = 1; b.takeDamage(99999, g, 'melee', h); g.simulate(0.5); out.bossDead = g.zs.bossState; out.after = tryRead(); h.invuln = 0;
        out.text = g.t('ui.error.beresta_arena'); Math.random = rnd0; return out; })()'''.replace('__P__', P))
    E = s['text']
    check('M1d п.2 арена Кривши: до подъёма (11,8 от идола) и при живом боссе береста серая, «' + E + '», не тратится; в 12,4 от идола — читается; после смерти Кривши — читается',
          E == 'Пока враг стоит, проход не откроется.' and s['state0'] == 'dormant'
          and s['dormant'] == {'ok': False, 'n': 0, 'note': E, 'portal': False, 'grey': True} and s['alive'] == {'ok': False, 'n': 0, 'note': E, 'portal': False, 'grey': True}
          and s['out12']['ok'] and s['out12']['portal'] and s['out12']['n'] == 1 and not s['out12']['grey']
          and s['bossDead'] == 'dead' and s['after']['ok'] and s['after']['portal'] and not s['after']['grey'], s)

    # --- 2б. поводок пешком: дальше 25 от идола — полное HP, фаза заново, призванные рассыпаются без опыта и добычи (B-33)
    s = await G('''(() => { const g = __game, h = g.hero; __P__ const m = toKap(g); const I = m.idol; g.enemies = []; h.invuln = 99; h.x = I.x - 5; h.y = I.y; h.stop();
        const b = g.riseBoss('test'); g.simulate(2.3); b.stagger = 1e9; b.summonT = 0.01; g.simulate(1.5); const mins = b.minions.filter(e => !e.dead).length;
        b.hp = Math.round(b.maxHp * 0.4); b.phase = 2; b.phaseDone = true; const xp0 = h.xp, it0 = g.loot.items.length; g.counters.krivshaLeash = 0; b.stagger = 0;
        h.x = I.x - 24.5; g.simulate(0.3); const at24 = { st: b.state, leash: g.counters.krivshaLeash };
        const W = g.map; let far = null; for (let d = 25.3; d < 34 && !far; d += 0.4) for (let a = 0; a < 24; a++) { const x = I.x + Math.cos(a / 24 * 6.283) * d, y = I.y + Math.sin(a / 24 * 6.283) * d; if (W.isReachableAt(x, y)) { far = [x, y]; break; } }
        h.x = far[0]; h.y = far[1]; h.stop(); g.simulate(0.1);
        const out = { mins, at24, leash: g.counters.krivshaLeash, why: g.counters.krivshaLeashWhy, hp: +(b.hp / b.maxHp).toFixed(2), phase: b.phase, phaseDone: b.phaseDone,
          left: g.enemies.filter(e => e.summoned && !e.dead).length, xp: h.xp - xp0, loot: g.loot.items.length - it0, d: +Math.hypot(h.x - I.x, h.y - I.y).toFixed(1) };
        g.simulate(12, () => b.state === 'idle'); out.idle = b.state; out.home = +Math.hypot(b.x - b.homeX, b.y - b.homeY).toFixed(1); h.invuln = 0; Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('M1d п.2 поводок пешком: в 24,5 от идола бой идёт; дальше 25 — сброс сразу: полное HP, фаза заново, призванные рассыпаются (без опыта и добычи); Кривша уходит к идолу',
          s['mins'] >= 1 and s['at24']['leash'] == 0 and s['leash'] == 1 and s['why'] == 'walk' and s['hp'] == 1.0 and s['phase'] == 1 and not s['phaseDone']
          and s['left'] == 0 and s['xp'] == 0 and s['loot'] == 0 and s['d'] > 25 and s['idle'] == 'idle' and s['home'] < 0.9, s)

    # --- 3. пояс: береста в ячейку (стопка 5, в котомке 20), клавиша ячейки / ПКМ по ячейке / ПКМ в котомке; не зелье — ui.error.belt
    s = await G('''(() => { const g = __game, h = g.hero; __P__ g.enterZone('zalesye', 'krada'); const k = g.map.krada; clearNear(g, 16); g.portal && g._finalizePortal('test');
        h.x = k.x + 14; h.y = k.y + 2; h.stop(); for (const it of h.inv.items.filter(i => i.kind === 'scroll')) h.inv.remove(it); h.addScroll('beresta', 12);
        h.belt[3] = null; const ui = g.ui; const st = h.inv.items.find(i => i.kind === 'scroll'); h.inv.remove(st); ui.hand = st; const ok = ui.toBelt(3);
        const out = { ok, belt: h.belt[3] && [h.belt[3].kind, h.belt[3].count], hand: ui.hand && ui.hand.count }; h.inv.autoAdd(ui.hand); ui.hand = null; out.bag = h.bagScrolls(); out.total = h.scrollCount();
        // подбор: доливает ячейку бересты (до 5), не занимает пустые
        h.belt[3].count = 3; const n0 = h.bagScrolls(); h.addScroll('beresta', 4); out.pick = [h.belt[3].count, h.bagScrolls() - n0];
        // не зелье и не береста — отказ
        const gear = h.inv.items.find(i => i.kind === 'gear') || g.give('sword_1'); h.inv.remove(gear); ui.hand = gear; g.notice = null; out.gear = ui.toBelt(0); out.gearNote = g.notice && g.notice.text; out.gearHand = ui.hand === gear;
        h.inv.autoAdd(gear); ui.hand = null; out.errText = g.t('ui.error.belt');
        return out; })()'''.replace('__P__', P))
    check('M1d п.3 пояс: береста ложится в ячейку стопкой до 5 (остаток в руке), подбор доливает ячейку бересты; вещь — отказ «' + s['errText'] + '»',
          s['ok'] and s['belt'] == ['beresta', 5] and s['hand'] == 7 and s['total'] == 12 and s['bag'] == 7 and s['pick'] == [5, 2]
          and s['gear'] is False and s['gearNote'] == s['errText'] == 'В пояс — только зелья и береста.' and s['gearHand'], s)

    # клавиша ячейки (настоящая клавиша 4) — чтение; потом ПКМ по ячейке (настоящая мышь); ПКМ в котомке; I и B — котомка
    await G('(() => { const g = __game, h = g.hero; g.ui.toggleInv(false); g.portal && g._finalizePortal("test"); h.belt[3].count = 5; h.stop(); h.action = null; g.counters.portalsOpened = 0; })()')
    await pg.keyboard.press('4')
    await wait(1400)
    s1 = await G('(() => { const g = __game, h = g.hero; return { belt: h.belt[3] && h.belt[3].count, portal: !!g.portal, opened: g.counters.portalsOpened }; })()')
    xy = await G('(async () => { const H = await import("/src/render/hud.js"); const s = H.LAYOUT.belt.slots[3]; return __game.clientOfScreen(s.x + 12, s.y + 12); })()')
    await pg.mouse.move(xy[0], xy[1])
    await wait(100)
    await pg.mouse.click(xy[0], xy[1], button='right')
    await wait(1400)
    s2 = await G('(() => { const g = __game, h = g.hero; return { belt: h.belt[3] && h.belt[3].count, opened: g.counters.portalsOpened }; })()')
    await pg.mouse.move(960, 540)
    await pg.keyboard.press('b')
    await wait(150)
    ib = [await G('__game.ui.invOpen')]
    await pg.keyboard.press('b')
    await wait(150)
    await pg.keyboard.press('i')
    await wait(150)
    ib.append(await G('__game.ui.invOpen'))
    await pg.keyboard.press('i')
    await wait(150)
    ib.append(await G('__game.ui.invOpen'))
    s3 = await G('''(() => { const g = __game, h = g.hero; const it = h.inv.items.find(i => i.kind === 'scroll'); const n0 = h.bagScrolls(), b0 = h.belt[3].count; g.ui.quickEquip({ item: it }); g.simulate(1.1);
        return { bag: n0 - h.bagScrolls(), belt: b0 - h.belt[3].count, opened: g.counters.portalsOpened, keyBerestaHotkey: !!(g.dbg.CFG.items_base.scrolls.beresta.hotkey) }; })()''')
    check('M1d п.3 береста из пояса читается клавишей ячейки (4) и ПКМ по ячейке (по 1 из ячейки), ПКМ в котомке — из котомки; своей клавиши нет; I и B открывают котомку',
          s1['belt'] == 4 and s1['portal'] and s1['opened'] == 1 and s2['belt'] == 3 and s2['opened'] == 2 and s3['bag'] == 1 and s3['belt'] == 0 and s3['opened'] == 3
          and not s3['keyBerestaHotkey'] and ib == [True, True, False], {'key': s1, 'rmb': s2, 'bag': s3, 'IB': ib})

    # --- 4. былинные: равные веса среди случайного пула с треб. ≤ ilvl, иначе дивная; _ph сняты
    s = await G('''(async () => { const g = __game; __P__ const I = await import('/src/data/items.js'); const U = g.dbg.CFG.uniques.uniques, UP = g.dbg.CFG.droptables.uniquePick;
        const cnt = {}; const N = 70000; for (let i = 0; i < N; i++) { const id = I.pickUnique(99); cnt[id] = (cnt[id] || 0) + 1; }
        const pool = U.filter(u => u.pool === 'random').map(u => u.id).sort(); const minReq = Math.min(...U.filter(u => u.pool === 'random').map(u => u.reqLevel));
        const low = I.pickUnique(minReq - 1); const lowOk = []; for (let i = 0; i < 2000; i++) { const id = I.pickUnique(minReq); lowOk.push(U.find(u => u.id === id).reqLevel <= minReq); }
        Math.random = rnd0; return { ph: UP._ph, w: UP.weights, fb: UP.fallback, ids: Object.keys(cnt).sort(), pool, pct: Object.values(cnt).map(v => +(v / N * 100).toFixed(2)), low, lowOk: lowOk.every(Boolean) }; })()'''.replace('__P__', P))
    eq = 100 / max(1, len(s['pool']))
    check('M1d п.4 былинные: равные веса среди %d вещей случайного пула (каждая %.1f%% ±10%%), треб. ≤ ilvl; нет подходящих — дивная; наградные не падают; _ph сняты' % (len(s['pool']), eq),
          s['ph'] == [] and s['w'] == 'equal' and s['fb'] == 'rare' and s['ids'] == s['pool'] and 'U2' not in s['ids'] and all(abs(p - eq) <= eq * 0.1 for p in s['pct'])
          and s['low'] is None and s['lowOk'], s)

    # --- 5. Мал: при выходе из избы — 2 слабых зелья жизни и 30 серебра, один раз, без опыта, реплика bark.m1.mal_gift
    s = await G('''(() => { const g = __game, h = g.hero; __P__ delete g.zoneStates.zalesye; g.quest.flags.malGift = false; g.enterZone('zalesye', 'krada'); const m = g.map;
        const hut = m.objects.find(o => o.type === 'hut' && o.npc === 'mal'); h.x = hut.sx; h.y = hut.sy + 0.6; h.stop(); clearNear(g, 14);
        const cnt = () => h.belt.reduce((a, b) => a + (b && b.kind === 'life1' ? b.count : 0), 0) + h.inv.items.filter(i => i.kind === 'potion' && i.potion === 'life1').length;
        const p0 = cnt(), s0 = h.silver, x0 = h.xp; const L = [], add0 = g.log.add; g.log.add = (tx, c) => { L.push(tx); return add0.call(g.log, tx, c); };
        g.interact(hut); const now = { pot: cnt() - p0, silver: h.silver - s0 }; g.simulate(10); g.log.add = add0; const mal = L.filter(x => x.startsWith('Мал:'));
        const out = { now, pot: cnt() - p0, silver: h.silver - s0, xp: h.xp - x0, gifts: g.counters.malGift, mal, bark: mal[1] === 'Мал: Вот, мамкины зелья. Тебе нужнее.' };
        g.malGift(); hut.done = false; g.interact(hut); out.again = [cnt() - p0, h.silver - s0, g.counters.malGift]; const G = g.dbg.CFG.quests.m1.malGift; out.data = [G.potions.life1, G.silver, G.xp, G.once];
        out.tip14 = g.t('tip.14'); Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('M1d п.5 Мал при выходе из избы: +2 слабых зелья жизни, +30 серебра, опыт 0, реплика «Вот, мамкины зелья. Тебе нужнее.»; повторно не даёт; tip.14 в ru.json',
          s['now'] == {'pot': 2, 'silver': 30} and s['pot'] == 2 and s['silver'] == 30 and s['xp'] == 0 and s['gifts'] == 1 and s['bark'] and s['again'] == [2, 30, 1] and s['data'] == [2, 30, 0, True]
          and s['tip14'].startswith('К боссу иди с полным поясом'), s)

    # --- 6. B-34: сравнение «Громового знака» — прибавка к каждому выученному навыку, а не сумма
    s = await G('''(async () => { const g = __game, h = g.hero; const W = await import('/src/ui/windows.js'), I = await import('/src/data/items.js');
        const keepSk = { ...h.skills }, keepNeck = h.equip.neck; h.equip.neck = null; h.recalc(); const U2 = I.makeUnique('U2'); const out = {};
        for (const k of Object.keys(h.skills)) h.skills[k] = 0; h.skills.sshibka = 1; h.recalc(); out.one = W.compareLines(U2, h).map(l => l[0]);
        h.skills.chur = 1; h.skills.stat = 2; h.recalc(); out.three = W.compareLines(U2, h).map(l => l[0]);
        for (const k of Object.keys(h.skills)) h.skills[k] = 0; h.recalc(); out.none = W.compareLines(U2, h).map(l => l[0]);
        out.lines = I.itemLines(U2).lines.map(l => l[0]);
        Object.assign(h.skills, keepSk); h.equip.neck = keepNeck; h.recalc(); return out; })()''')
    one, three = s['one'], s['three']
    check('B-34 сравнение «Громового знака»: 1 выученный навык → «Каждый выученный навык: +1»; 3 выученных → тоже +1 (не сумма +3); без навыков строки нет; свойство «+1 ко всем выученным навыкам»',
          'Каждый выученный навык: +1' in one and 'Каждый выученный навык: +1' in three and not any('+3' in l or 'Ранги' in l for l in one + three)
          and not any('навык' in l for l in s['none']) and any('+1 ко всем выученным навыкам' in str(l) for l in s['lines']), s)

    # --- 7. B-35: тот же замер (без фазы, запас 10+1+3) дважды с одним зерном — один итог (по каждому бою)
    await G(FIGHT)
    r = await G('''(async () => { const g = __game; const keep = g.hero; const o = { hearths: 0, kit: { life1: 10, zhivaya: 1, yar1: 3 }, runs: 3, seed: 20261008 };
        const a = await __fight(o); g.simulate(0.5); const b = await __fight(o); g.hero = keep; return [a.sig, b.sig, a.deaths, b.deaths, a.mean, b.mean]; })()''')
    await G('(() => { const g = __game; g.enterZone("zalesye", "krada", { respawn: true }); g.hero.hp = g.hero.maxHp; })()')
    check('B-35 замер Кривши воспроизводим: два прогона с одним зерном (живой цикл и звук между ними) дают одни и те же бои', r[0] == r[1] and r[2] == r[3] and r[4] == r[5], r)

    # --- скриншот: арена живой Кривши, береста в поясе серая, уведомление ui.error.beresta_arena
    await G('''(() => { const g = __game, h = g.hero; delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map, I = m.idol;
        g.enemies = g.enemies.filter(e => Math.hypot(e.x - I.x, e.y - I.y) > 13); h.x = I.x - 3.5; h.y = I.y + 3; h.stop(); h.action = null; h.invuln = 99;
        const b = g.riseBoss('test'); g.simulate(2.3); b.stagger = 1e9; h.face(b.x - h.x, b.y - h.y); h.belt[3] = { kind: 'beresta', scroll: 'beresta', count: 4 };
        g.ui.toggleInv(true); g.updateCamera(); })()''')
    await pg.mouse.move(960, 700)
    await pg.keyboard.press('4')
    await wait(250)
    note = await G('[__game.notice && __game.notice.text, __game.berestaGrey(), __game.hero.belt[3] && __game.hero.belt[3].count]')
    await pg.screenshot(path=SHOT_M1D)
    await G('(() => { const g = __game; g.ui.toggleInv(false); g.hero.invuln = 0; })()')
    check('M1d скриншот screenshot_m1d.png: арена живой Кривши, береста в поясе серая, клавиша 4 — уведомление, береста не потрачена',
          note[0] == 'Пока враг стоит, проход не откроется.' and note[1] and note[2] == 4 and os.path.getsize(SHOT_M1D) > 50000, note)

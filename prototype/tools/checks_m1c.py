"""Проверки вехи M1c: береста возврата и Чуров проход, былинные вещи. Вызываются из verify_playwright.py на свежей загрузке
(после раздела M1b); отдельно — `--only-m1c`."""
import json
import os
from checks_v18 import run_v18

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_M1C = os.path.join(ROOT, 'screenshot_m1c.png')

SEEDED = '''const rnd0 = Math.random; let seed = 20261008; Math.random = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };'''
# стаи ближе 12 тайлов к герою убираются из зоны (в window.__away1), враги замирают
CLEAR = '''const clearNear = (g, r = 12) => { const h = g.hero; const far = g.enemies.filter(e => Math.hypot(e.x - h.x, e.y - h.y) < r); g.enemies = g.enemies.filter(e => !far.includes(e)); for (const e of g.enemies) e.stagger = 1e9; return far.length; };'''


async def run_m1c(pg, G, check, wait, client_of, client_scr, a):
    await pg.goto(a.url)
    await pg.wait_for_function('window.__game && window.__game.time > 0.5', timeout=15000)
    await pg.mouse.move(960, 540)
    await pg.mouse.click(960, 300)
    await wait(200)
    print('--- веха M1c', flush=True)
    P = SEEDED + CLEAR

    # --- 1. береста: данные по GDD, старт, пояс
    s = await G('''(() => { const g = __game, h = g.hero, C = g.dbg.CFG, B = C.items_base.scrolls.beresta, pt = C.droptables.potionType;
        const st = h.inv.items.filter(i => i.kind === 'scroll');
        return { cast: B.castTime, life: B.portalLife, stack: B.stack, price: B.price, pt, start: h.scrollCount(), stacks: st.length, belt: h.belt.map(b => b && b.kind),
                 name: st[0] && st[0].name, ru: g.t('item.beresta') }; })()''')
    check('M1c береста (GDD §4.4, §6.7, §6.9): каст 1 с, проход 60 с, стопка 20, цена 25; зелья 55/30/10/5 (береста выделена из зелий жизни); на старте 3 бересты стопкой в котомке, в поясе только зелья',
          s['cast'] == 1 and s['life'] == 60 and s['stack'] == 20 and s['price'] == 25 and s['pt'] == {'life': 55, 'yar': 30, 'zhivaya': 10, 'beresta': 5}
          and s['start'] == 3 and s['stacks'] == 1 and all(b in (None, 'life1', 'yar1') for b in s['belt']) and s['name'] == s['ru'] == 'Береста возврата', s)

    # --- 2. выпадение: класс «зелье/береста» 10 000 бросков (sim_drop, допуск ±15%), обычный враг 20 000 убийств
    s = await G('''(() => { const g = __game; __P__ const L = g.loot, keep = L.items; const cnt = {}; const N = 10000;
        for (let i = 0; i < N; i++) { L.items = []; const it = L.spawnPotionRoll(10, 10, 1); const k = it.kind === 'scroll' ? 'beresta' : it.potion.replace(/[0-9]/g, ''); cnt[k] = (cnt[k] || 0) + 1; }
        const pct = Object.fromEntries(Object.entries(cnt).map(([k, v]) => [k, +(v / N * 100).toFixed(2)]));
        const kinds = {}; const fake = { x: 10, y: 10, mlvl: 2 }; L.items = [];
        for (let i = 0; i < 20000; i++) { L.items = []; L.dropFrom(fake); for (const it of L.items) kinds[it.kind] = (kinds[it.kind] || 0) + 1; }
        L.items = keep; Math.random = rnd0; return { pct, kinds, scrollPerKill: +((kinds.scroll || 0) / 20000 * 100).toFixed(3) }; })()'''.replace('__P__', P))
    pc = s['pct']
    check('M1c sim_drop: класс «зелье/береста» — береста 5% (±15%), жизни 55%, Яри 30%, живая вода 10%; с обычного врага береста ≈ 0,5% убийств (10% × 5%)',
          4.25 <= pc.get('beresta', 0) <= 5.75 and 46.75 <= pc.get('life', 0) <= 63.25 and 25.5 <= pc.get('yar', 0) <= 34.5 and 8.5 <= pc.get('zhivaya', 0) <= 11.5
          and 0.3 <= s['scrollPerKill'] <= 0.7, s)

    # --- 3. подбор: стопка до 20, лишнее — новой стопкой, в пояс не идёт
    s = await G('''(() => { const g = __game, h = g.hero; const belt0 = JSON.stringify(h.belt);
        const a = g.loot.spawnScroll(h.x + 0.5, h.y, 'beresta', 1); a.dropT = 1; const ok1 = g.loot.pickup(a); const n1 = h.scrollCount();
        const b = g.loot.spawnScroll(h.x + 0.5, h.y, 'beresta', 18); b.dropT = 1; g.loot.pickup(b);
        const stacks = h.inv.items.filter(i => i.kind === 'scroll').map(i => i.count);
        const belt1 = JSON.stringify(h.belt); for (const it of h.inv.items.filter(i => i.kind === 'scroll')) h.inv.remove(it); h.addScroll('beresta', 3);
        return { ok1, n1, stacks, beltSame: belt0 === belt1, after: h.scrollCount(), label: a.label }; })()''')
    check('M1c подбор бересты: в котомку стопкой до 20, остаток — новой стопкой; пояс не трогается (в пояс — только зелья)',
          s['ok1'] and s['n1'] == 4 and sorted(s['stacks']) == [2, 20] and s['beltSame'] and s['after'] == 3 and s['label'] == 'Береста возврата', s)

    # --- 4. у крады (город-заглушка) бересту не прочитать
    s = await G('''(() => { const g = __game, h = g.hero, k = g.map.krada; h.x = k.x + 2; h.y = k.y + 2; h.stop(); const n0 = h.scrollCount(); g.notice = null;
        const it = h.inv.items.find(i => i.kind === 'scroll'); const r = g.useScroll(it); g.simulate(1.3);
        return { r, portal: !!g.portal, n: h.scrollCount(), n0, notice: g.notice && g.notice.text }; })()''')
    check('M1c у крады Залесья (город вместо Ладоги) береста не читается: «Ты и так в Ладоге.», береста не тратится',
          s['r'] is False and not s['portal'] and s['n'] == s['n0'] and s['notice'] == 'Ты и так в Ладоге.', s)

    # --- 5. ПКМ по бересте в котомке на тропе (мышью): каст 1 с, проход открыт, береста −1
    s = await G('''(() => { const g = __game, h = g.hero; __P__ g.quest.flags.trailOpen = true; g.enterZone('trail', 'start'); clearNear(g, 14); h.hp = h.maxHp; Math.random = rnd0;
        h.stop(); h.face(1, 1); g.ui.closeAll(); g.ui.toggleInv(true); const e = h.inv.entries.find(x => x.item.kind === 'scroll'); return { c: e.c, r: e.r, n0: h.scrollCount(), zone: g.zone.id, L: g.dbg.UI_ATLAS.inventory_layout }; })()'''.replace('__P__', P))
    L = s['L']
    n0 = s['n0']
    cx, cy = L['gx'] + (s['c'] + 0.5) * L['cell'], L['gy'] + (s['r'] + 0.5) * L['cell']
    await pg.mouse.move(*(await client_scr(cx, cy))); await wait(120)
    tip = await G('__game.ui.lastTip && { name: __game.ui.lastTip.item.name, kind: __game.ui.lastTip.item.kind }')
    await pg.mouse.click(*(await client_scr(cx, cy)), button='right'); await wait(500)
    mid = await G('({ act: __game.hero.action && __game.hero.action.type, portal: !!__game.portal, n: __game.hero.scrollCount() })')
    await wait(800)
    s2 = await G('''(() => { const g = __game, h = g.hero, P = g.portal; if (!P) return { portal: false };
        const tz = g.zoneStates.zalesye.map, k = tz.krada;
        return { portal: true, zone: P.zone, tzone: P.tzone, n: h.scrollCount(), inField: g.map.objects.includes(P.field), inTown: tz.objects.includes(P.town),
                 dHero: +Math.hypot(P.field.x - h.x, P.field.y - h.y).toFixed(2), dKrada: +Math.hypot(P.town.x - k.x, P.town.y - k.y).toFixed(2),
                 log: g.log.lines.slice(-3).map(l => l.text || l[0] || ''), notice: g.notice && g.notice.text, ttl: P.ttl }; })()''')
    check('M1c ПКМ по бересте в котомке: подсказка «Береста возврата ×3», каст 1 с (на 0,5 с прохода ещё нет), затем «Чуров проход открыт», береста −1; конец прохода рядом с героем и у крады Залесья (в тихом круге)',
          tip and tip['kind'] == 'scroll' and mid['act'] == 'read' and not mid['portal'] and mid['n'] == n0 and s2['portal'] and s2['zone'] == 'trail' and s2['tzone'] == 'zalesye'
          and s2['n'] == n0 - 1 and s2['inField'] and s2['inTown'] and s2['dHero'] < 2.5 and s2['dKrada'] < 6 and s2['notice'] == 'Чуров проход открыт' and s2['ttl'] == 60,
          {'tip': tip, 'mid': mid, 'after': s2})

    # --- 6. туда и обратно щелчками по проходу
    await pg.keyboard.press('KeyI'); await wait(100)
    s = await G('''(() => { const g = __game, h = g.hero, P = g.portal; window.__open = [h.x, h.y]; return { x: P.field.x, y: P.field.y }; })()''')
    await pg.mouse.move(*(await client_of(s['x'], s['y'], 14))); await wait(150)
    hov = await G('__game.hoverObj && { type: __game.hoverObj.type, label: __game.objectLabel(__game.hoverObj) }')
    await pg.mouse.click(*(await client_of(s['x'], s['y'], 14)))
    for _ in range(40):
        await wait(100)
        z = await G('__game.zone.id')
        if z == 'zalesye':
            break
    s1 = await G('''(() => { const g = __game, h = g.hero, P = g.portal; return { zone: g.zone.id, inTown: g.inTown(), portal: !!P, d: P ? +Math.hypot(P.town.x - h.x, P.town.y - h.y).toFixed(2) : -1, tx: P && P.town.x, ty: P && P.town.y }; })()''')
    await wait(200)
    await pg.mouse.move(*(await client_of(s1['tx'], s1['ty'], 14))); await wait(150)
    await pg.mouse.click(*(await client_of(s1['tx'], s1['ty'], 14)))
    for _ in range(40):
        await wait(100)
        z = await G('__game.zone.id')
        if z == 'trail':
            break
    s3 = await G('''(() => { const g = __game, h = g.hero, o = window.__open; return { zone: g.zone.id, d: +Math.hypot(h.x - o[0], h.y - o[1]).toFixed(2), portal: !!g.portal,
        objs: Object.values(g.zoneStates).reduce((n, st) => n + st.map.objects.filter(x => x.type === 'portal').length, 0), uses: g.counters.portalUses }; })()''')
    check('M1c Чуров проход: щелчок по проходу (подпись «Чуров проход: Залесье») — к краде Залесья; щелчок по проходу у крады — назад на тропу, к месту открытия; после возвращения проход закрыт',
          hov and hov['type'] == 'portal' and hov['label'] == 'Чуров проход: Залесье' and s1['zone'] == 'zalesye' and s1['inTown'] and s1['d'] < 2.5
          and s3['zone'] == 'trail' and s3['d'] < 3 and not s3['portal'] and s3['objs'] == 0 and s3['uses'] == 2, {'hover': hov, 'town': s1, 'back': s3})

    # --- 7. срок прохода 60 с — в любой зоне; прерывание каста сильным ударом; гибель не закрывает проход
    s = await G('''(() => { const g = __game, h = g.hero, out = {}; h.addScroll('beresta', 10);
        const read = () => { const it = h.inv.items.find(i => i.kind === 'scroll'); h.stop(); h.action = null; const r = h.readScroll(it, g); g.simulate(1.1); return r; };
        out.r = read(); out.open = !!g.portal; g.simulate(58); out.at59 = !!g.portal; g.simulate(2.5); out.at60 = !!g.portal; out.why = g.counters.portalClosed;
        read(); const P = g.portal; g.usePortal(P.field); out.z = g.zone.id; g.simulate(61); out.townAfter = g.zoneStates.zalesye.map.objects.includes(P.town); out.portal2 = !!g.portal;
        // каст прерывается оглушением (удар > 12% макс. жизни), береста не тратится
        g.enterZone('trail', 'start'); clearNear(g, 14); const n0 = h.scrollCount(); const it = h.inv.items.find(i => i.kind === 'scroll'); h.stop(); h.readScroll(it, g); g.simulate(0.4);
        h.invuln = 0; h.takeDamage(Math.ceil(h.maxHp * 0.25), g, 'cold', null); g.simulate(1.0); out.interrupted = { portal: !!g.portal, n: h.scrollCount(), n0 }; h.hp = h.maxHp;
        // гибель: проход остаётся, герой у крады, через проход — обратно на тропу
        read(); const P2 = g.portal; const q0 = JSON.stringify(g.quest.obj.map(o => o.state)); h.invuln = 0; h.takeDamage(99999, g, 'cold', null); out.dead = g.state; g.respawnHero();
        out.death = { zone: g.zone.id, portal: g.portal === P2, q: JSON.stringify(g.quest.obj.map(o => o.state)) === q0 };
        g.usePortal(P2.town); out.death.back = g.zone.id; out.death.closed = !g.portal; return out; })()'''.replace('__P__', P).replace('clearNear(g, 14);', CLEAR + ' clearNear(g, 14);'))
    check('M1c проход живёт 60 с (закрывается и на тропе, и у крады, пока герой в другой зоне); сильный удар прерывает чтение — береста не тратится; гибель проход не закрывает, трекер не меняется',
          s['r'] is None and s['open'] and s['at59'] and not s['at60'] and s['why'] == 'expired' and s['z'] == 'zalesye' and not s['townAfter'] and not s['portal2']
          and not s['interrupted']['portal'] and s['interrupted']['n'] == s['interrupted']['n0'] and s['dead'] == 'dead'
          and s['death']['zone'] == 'zalesye' and s['death']['portal'] and s['death']['q'] and s['death']['back'] == 'trail' and s['death']['closed'], s)

    # --- 8. арена Кривши: береста разрешена (запрета в GDD нет); уход и возвращение — босс по поводку возвращается к идолу (§4.5)
    s = await G('''(() => { const g = __game, h = g.hero; __P__ g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map;
        h.x = m.idol.x - 1; h.y = m.idol.y + 4; h.stop(); const b = g.riseBoss('test'); g.simulate(2.3); for (const e of g.enemies) if (e !== b) e.stagger = 1e9;
        h.invuln = 99; b.hp = Math.round(b.maxHp * 0.6); const it = h.inv.items.find(i => i.kind === 'scroll'); const r = h.readScroll(it, g); g.simulate(1.1);
        const out = { r, open: !!g.portal && g.portal.zone, bossSt: b.state }; g.usePortal(g.portal.field); out.z = g.zone.id; g.simulate(2); g.usePortal(g.portal.town);
        out.back = g.zone.id; g.simulate(8, () => b.state === 'idle'); out.after = { st: b.state, hp: +(b.hp / b.maxHp).toFixed(2), resets: g.counters.krivshaResets || 0 };
        h.invuln = 0; Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('M1c береста на арене Кривши читается (запрета в GDD нет); уход через проход — босс возвращается к идолу и лечится, как при обрыве погони (§4.5; вопрос дизайнеру)',
          s['r'] is None and s['open'] == 'kapishche' and s['z'] == 'zalesye' and s['back'] == 'kapishche' and s['after']['st'] == 'idle' and s['after']['hp'] == 1.0, s)

    # --- 9. былинные: таблица босса 10 000 предметов (8% ±15%), выбор из пула по ilvl, фиксированные свойства
    s = await G('''(() => { const g = __game; __P__ const L = g.loot, keep = L.items, U = g.dbg.CFG.uniques.uniques; let n = 0, uq = 0; const ids = {}, bad = [];
        const fake = { x: 10, y: 10, mlvl: 6, dropTable: 'boss', kind: 'm1c_boss_test' };
        while (n < 10000) { L.items = []; L.dropElite(fake); for (const d of fake.drops) { if (!d.item) continue; n++; if (d.item.rarity === 'unique') { uq++; ids[d.item.unique] = (ids[d.item.unique] || 0) + 1;
            const u = U.find(x => x.id === d.item.unique); for (const [k, v] of Object.entries(u.mods)) { const val = d.item.mods[k]; if (Array.isArray(v) ? !(val >= v[0] && val <= v[1]) : val !== v) bad.push(u.id + ':' + k); }
            if (d.item.req !== u.reqLevel || !d.item.lore || d.label !== d.item.name) bad.push(u.id + ':meta'); } } }
        L.items = keep; Math.random = rnd0; return { n, uq, pct: +(uq / n * 100).toFixed(2), ids, bad: bad.slice(0, 5) }; })()'''.replace('__P__', P))
    check('M1c былинные с босса (GDD §6.7 «Босс» 0/60/32/8): 10 000 предметов — былинных 8% (±15%); только из случайного пула с треб. ≤ ilvl 6 (Жало Сокола, Шелом Курганного князя), свойства в диапазонах uniques.json',
          6.8 <= s['pct'] <= 9.2 and set(s['ids']) <= {'U1', 'U3'} and len(s['ids']) == 2 and not s['bad'], s)
    s = await G('''(async () => { const g = __game, I = await import('/src/data/items.js'); __P__ const out = {};
        const a = I.rollItem(1, Math.random, 0, { forceRarity: 'unique' }); out.low = a.rarity; const b = I.rollItem(6, Math.random, 0, { forceRarity: 'unique' }); out.mid = [b.rarity, b.unique];
        const c = I.rollItem(15, Math.random, 0, { forceRarity: 'unique' }); out.high = c.unique; const seen = new Set(); for (let i = 0; i < 400; i++) seen.add(I.rollItem(20, Math.random, 0, { forceRarity: 'unique' }).unique);
        out.pool = [...seen].sort(); const loot = g.loot.spawnItem(10, 10, b); out.color = loot.color; out.label = loot.label; g.loot.items = g.loot.items.filter(x => x !== loot);
        Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('M1c выбор былинной (заглушка droptables.uniquePick): нет подходящей по ilvl — выпадает дивной; наградные «Громовник» и «Лунница» в случайном пуле не встречаются; подпись на земле бронзой (bronze_lt)',
          s['low'] == 'rare' and s['mid'][0] == 'unique' and s['mid'][1] in ('U1', 'U3') and s['pool'] == ['U1', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8'] and s['color'] == '#d39a45', s)

    # --- 10. Кривша пал → «Громовник» у подножия идола: в котомку, один раз, фиксированные свойства
    s = await G('''(() => { const g = __game, h = g.hero; __P__ g.enterZone('trail', 'gate'); delete g.zoneStates.kapishche; g.enterZone('kapishche', 'from_trail'); const m = g.map;
        h.x = m.idol.x - 1; h.y = m.idol.y + 4; h.stop(); const b = g.riseBoss('test'); g.simulate(2.3); h.invuln = 0; b.takeDamage(99999, g, 'melee', h); g.simulate(0.3);
        const r = g.objectById('gromovnik'); h.x = r.sx; h.y = r.sy; h.cmd = null; h.interact(r); g.simulate(1, () => r.done);
        const items = h.inv.items.filter(i => i.unique === 'U2'); const it = items[0]; h.interact(r); g.simulate(1);
        Math.random = rnd0; return { done: r.done, n: items.length, n2: h.inv.items.filter(i => i.unique === 'U2').length, name: it && it.name, rar: it && it.rarity, mods: it && it.mods, req: it && it.req, lore: it && it.lore,
                 type: it && it.type, notice: g.notice && g.notice.text, hidden: !!(r.prop && r.prop.taken) }; })()'''.replace('__P__', P))
    check('M1c «Громовник» (U2, награда М1): после Кривши у подножия идола, щелчок — в котомку один раз; оберег, треб. 5, +1 ко всем навыкам, +15 к жизни, сопр. огню +10%, присказка из act1_texts §14',
          s['done'] and s['n'] == 1 and s['n2'] == 1 and s['name'] == 'Громовник' and s['rar'] == 'unique' and s['mods'] == {'skillAll': 1, 'hp': 15, 'resFire': 10}
          and s['req'] == 5 and s['lore'] == 'Уцелел в пепле капища. Перун своих не оставляет.' and s['type'] == 'neck' and s['hidden'] and s['notice'] == 'Былинная вещь: Громовник', s)

    # --- 11. тултип и сравнение (мышью), надевание ПКМ, свойства в силе
    s = await G('''(() => { const g = __game, h = g.hero; __P__ g.enterZone('zalesye', 'krada', { respawn: true }); let k = 0; while (h.level < 6 && k++ < 20) h.gainXp(g.dbg.xpToNext(h.level), g);
        h.equip.neck = null; h.recalc(); g.ui.closeAll(); g.ui.toggleInv(true); const e = h.inv.entries.find(x => x.item.unique === 'U2');
        Math.random = rnd0; return { c: e.c, r: e.r, w: e.item.w, h: e.item.h, hp: h.maxHp, rf: h.res.fire, rk: g.dbg.rankOf(h, 'sshibka') }; })()'''.replace('__P__', P))
    base = s
    cx, cy = L['gx'] + (s['c'] + s['w'] / 2) * L['cell'], L['gy'] + (s['r'] + s['h'] / 2) * L['cell']
    await pg.mouse.move(*(await client_scr(cx, cy))); await wait(150)
    tip = await G('''(() => { const g = __game, T = g.ui.lastTip; if (!T) return null; const { lines } = g.dbg.itemLines(T.item); return { name: T.item.name, w: T.w, h: T.h, lines: lines.map(l => l[0]), cols: lines.map(l => l[1]), cmp: g.dbg.cmp(T.item).map(l => l[0]) }; })()''')
    check('M1c тултип былинной: имя и «Былинная вещь» бронзой, база, требование, свойства, присказка бронзой; сравнение — слот «Шея» свободен: Жизнь +15, Ранги навыков +, Сопр. огню +10',
          tip and tip['lines'][0] == 'Громовник' and tip['lines'][1] == 'Былинная вещь' and tip['cols'][0] == tip['cols'][1] == 'bronze_lt' and 'Оберег-подвеска' in tip['lines']
          and '+1 ко всем навыкам' in tip['lines'] and '+15 к жизни' in tip['lines'] and 'Сопротивление огню +10%' in tip['lines'] and tip['lines'][-1].startswith('Уцелел') and tip['cols'][-1] == 'lore'
          and tip['cmp'][0].startswith('Слот «') and 'Жизнь: +15' in tip['cmp'] and 'Сопр. огню, %: +10' in tip['cmp'] and any(l.startswith('Ранги навыков: +') for l in tip['cmp']), tip)
    await pg.mouse.click(*(await client_scr(cx, cy)), button='right'); await wait(150)
    s = await G('''(() => { const g = __game, h = g.hero, n = h.equip.neck; return { neck: n && n.unique, hp: h.maxHp, rf: h.res.fire, rk: g.dbg.rankOf(h, 'sshibka'), skl: Object.keys(g.dbg.SKILLS).filter(id => (h.skills[id] || 0) > 0).length }; })()''')
    check('M1c ПКМ — «Громовник» надет: жизнь +15, сопр. огню +10, «Сшибка» +1 ранг (+1 ко всем навыкам действует на выученные)',
          s['neck'] == 'U2' and s['hp'] == base['hp'] + 15 and s['rf'] == base['rf'] + 10 and s['rk'] == base['rk'] + 1, {'before': base, 'after': s})
    # сравнение против надетого и свойства остальных былинных M1-пула
    s = await G('''(async () => { const g = __game, h = g.hero, I = await import('/src/data/items.js'); __P__ const out = {};
        const cmpNeck = g.dbg.cmp(I.makeItem('neck_1', 'magic', 6, Math.random, { affixes: [['S01', 8]] })).map(l => l[0]); out.cmpNeck = cmpNeck;
        const snap = () => ({ dmg: [h.dmgMin, h.dmgMax], fire: h.fireDmg, rk: g.dbg.rankOf(h, 'sshibka'), rf: h.res.fire, rc: h.res.cold, rp: h.res.poison, armor: h.armor, vit: h.vit, ls: +(h.lifesteal * 100).toFixed(0), vn: +(h.vsNechist * 100).toFixed(0), spd: +h.speed.toFixed(3), dex: h.dex, pot: h.potionPct || 0, hp: h.maxHp });
        const s0 = snap(); const U1 = I.makeUnique('U1'); const cmpU1 = g.dbg.cmp(U1).map(l => l[0]); const w0 = h.equip.rhand; h.putOn(U1, 'rhand'); const s1 = snap();
        const U3 = I.makeUnique('U3'); const hd0 = h.equip.head; h.putOn(U3, 'head'); const s3 = snap();
        const U4 = I.makeUnique('U4'); h.putOn(U4, 'belt'); const s4 = snap(); h.hp = 10; h.effects = []; h.potionCds.hp = 0; h.applyPotion('life1', g); const heal = h.effects[0].rate * h.effects[0].t;
        const U5 = I.makeUnique('U5'); h.putOn(U5, 'feet'); const s5 = snap();
        out.u1 = { ed: U1.mods.ed, d: [s0.dmg, s1.dmg], fire: s1.fire - s0.fire, rk: s1.rk - s0.rk, rf: s1.rf - s0.rf, cmp: cmpU1.slice(0, 7) };
        out.u3 = { pa: U3.mods.pctArmor, armorItem: U3.armor, armorBase: U3.armorBase, vit: s3.vit - s1.vit, ls: s3.ls - s1.ls, vn: s3.vn - s1.vn };
        out.u4 = { hp: s4.hp - s3.hp, res: [s4.rf - s3.rf, s4.rc - s3.rc, s4.rp - s3.rp], pot: s4.pot, heal: +heal.toFixed(2) };
        out.u5 = { spd: +(s5.spd / s4.spd).toFixed(3), dex: s5.dex - s4.dex, rc: s5.rc - s4.rc };
        // смена зоны: всё надетое и береста на месте
        const before = JSON.stringify(snap()), sc0 = h.scrollCount(); g.quest.flags.trailOpen = true; g.enterZone('trail', 'start'); g.enterZone('zalesye', 'from_trail'); g.enterZone('trail', 'start');
        out.zone = { same: JSON.stringify(snap()) === before, eq: ['rhand', 'head', 'belt', 'feet', 'neck'].map(s => h.equip[s] && h.equip[s].unique), sc: h.scrollCount() === sc0 };
        h.putOn(w0, 'rhand'); h.putOn(hd0, 'head'); h.equip.belt = null; h.equip.feet = null; h.recalc(); g.enterZone('zalesye', 'krada', { respawn: true }); h.hp = h.maxHp;
        Math.random = rnd0; return out; })()'''.replace('__P__', P))
    u1, u3, u4, u5 = s['u1'], s['u3'], s['u4'], s['u5']
    check('M1c сравнение против надетого: заговорённый оберег против «Громовника» — «Против надетого:», Жизнь и Ранги навыков в минусе',
          s['cmpNeck'][0] == 'Против надетого:' and any(l.startswith('Ранги навыков: −') for l in s['cmpNeck']), s['cmpNeck'])
    check('M1c свойства былинных в силе: Жало Сокола (+40–60% урона, +3 огня, +1 «Сшибка», огонь +10), Шелом (+30–40% брони, +3 Жив., кровопийство 3%, +20% по Нечисти), Пояс Святогоров (+20 жизни, +15% к зельям, +10% ко всем сопр.), Сапоги-скороходы (+20% бега, +10 Ловк., холод +15)',
          40 <= u1['ed'] <= 60 and u1['d'][1][1] > u1['d'][0][1] and u1['fire'] == 3 and u1['rk'] == 1 and u1['rf'] == 10
          and 30 <= u3['pa'] <= 40 and u3['armorItem'] == int(u3['armorBase'] * (1 + u3['pa'] / 100)) and u3['vit'] == 3 and u3['ls'] == 3 and u3['vn'] == 20
          and u4['hp'] == 20 + 0 and u4['res'] == [10, 10, 10] and u4['pot'] == 15 and abs(u4['heal'] - 45 * 1.15) < 0.6
          and u5['spd'] == 1.2 and u5['dex'] == 10 and u5['rc'] == 15, s)
    z = s['zone']
    check('M1c смена зон: надетые былинные, характеристики героя и береста сохраняются (тропа → Залесье → тропа)',
          z['same'] and z['eq'] == ['U1', 'U3', 'U4', 'U5', 'U2'] and z['sc'], z)

    # --- 12. замер: ожидаемые былинные за М1 (GDD §6.8: ≈ 0,3 случайных + «Громовник»)
    s = await G('''(() => { const g = __game; __P__ const L = g.loot, keep = L.items; const pools = [];
        for (const id of ['zalesye', 'trail', 'kapishche']) { const st = g.zoneStates[id] || null; const list = st ? [...(st === g.zs ? g.enemies : st.enemies), ...(st.buried || [])] : [];
          pools.push(...list.filter(e => !e.summoned).map(e => ({ x: 10, y: 10, mlvl: e.mlvl, dropTable: e.dropTable, kind: e.kind }))); }
        pools.push({ x: 10, y: 10, mlvl: 6, dropTable: 'boss', kind: 'krivsha' });
        const R = 400; let uq = 0, items = 0, magic = 0, rare = 0; g.firstKills = {};
        for (let r = 0; r < R; r++) { g.firstKills = {}; for (const e of pools) { L.items = []; L.dropFrom(e); for (const d of L.items) if (d.item) { items++; if (d.item.rarity === 'unique') uq++; if (d.item.rarity === 'magic') magic++; if (d.item.rarity === 'rare') rare++; } } }
        L.items = keep; Math.random = rnd0; return { enemies: pools.length, perRun: { items: +(items / R).toFixed(1), magic: +(magic / R).toFixed(1), rare: +(rare / R).toFixed(2), bylina: +(uq / R).toFixed(2) } }; })()'''.replace('__P__', P))
    print('ЗАМЕР M1c:', json.dumps(s, ensure_ascii=False), flush=True)
    check('M1c замер: добыча за М1 по всем врагам зон + Кривша (400 прогонов) — былинных в среднем > 0 (GDD §6.8 ≈ 0,3 + «Громовник»; расхождение — в отчёте)', s['perRun']['bylina'] > 0, s)

    # --- скриншот: тропа, открытый проход слева, котомка с тултипом «Громовника» (сравнение с надетым оберегом)
    sc = await G('''(async () => { const g = __game, h = g.hero, I = await import('/src/data/items.js'); __P__
        g.quest.flags.trailOpen = true; g.enterZone('trail', 'start'); const m = g.map; let best = null;
        for (let i = 0; i < 400 && !best; i++) { const x = m.w * (0.35 + 0.3 * Math.random()), y = m.h * (0.35 + 0.3 * Math.random()); if (g.dbg.circleFree(m, x, y, 0.5) && m.isReachableAt(x, y) && g.dbg.circleFree(m, x + 1, y - 1, 0.6)) best = [x, y]; }
        if (best) { h.x = best[0]; h.y = best[1]; } clearNear(g, 16); h.hp = Math.round(h.maxHp * 0.8); h.stop(); h.face(-1, 1);
        if (!h.inv.items.some(i => i.unique === 'U2')) h.inv.autoAdd(I.makeUnique('U2'));
        h.equip.neck = I.makeItem('neck_1', 'magic', 6, Math.random, { affixes: [['S01', 12]] }); h.recalc();
        if (g.portal) g.closePortal('replaced'); g.openPortal(); g.ui.closeAll(); g.ui.toggleInv(true); const P = g.portal; let hx = h.x, hy = h.y;
        for (let k = 0; k < 4; k++) { g.updateCamera(); const [sx, sy] = g.toS(P.field.x, P.field.y), [a1, b1] = g.toWorld(sx, sy), [a2, b2] = g.toWorld(258, 124); hx += a1 - a2; hy += b1 - b2; h.x = hx; h.y = hy; }
        g.updateCamera(); clearNear(g, 16);
        g.loot.items = []; g.letter = null; g.notice = null; g.log.lines.length = 0; g.time += 10; Math.random = rnd0;
        const e = h.inv.entries.find(x => x.item.unique === 'U2'); return { c: e.c, r: e.r, w: e.item.w, h: e.item.h, free: g.dbg.circleFree(g.map, hx, hy, 0.3) }; })()'''.replace('__P__', P))
    cx, cy = L['gx'] + (sc['c'] + sc['w'] / 2) * L['cell'], L['gy'] + (sc['r'] + sc['h'] / 2) * L['cell']
    await pg.mouse.move(*(await client_scr(cx, cy))); await wait(250)
    await pg.screenshot(path=SHOT_M1C)
    s = await G('''(() => { const g = __game, T = g.ui.lastTip, P = g.portal; const [sx, sy] = P ? g.toS(P.field.x, P.field.y) : [0, 0];
        return { zone: g.zone.id, tip: T && T.item.name, tipBox: T && [T.x, T.y, T.w, T.h], portal: !!P, ps: [Math.round(sx), Math.round(sy)] }; })()''')
    vis = s['portal'] and 0 < s['ps'][0] < 320 and 30 < s['ps'][1] < 300 and s['tipBox'] and (s['ps'][0] + 14 < s['tipBox'][0] or s['ps'][1] - 36 > s['tipBox'][1] + s['tipBox'][3] or s['ps'][1] + 6 < s['tipBox'][1])
    check('скриншот screenshot_m1c.png (1920×1080 = 640×360 ×3): тропа, открытый Чуров проход, котомка с тултипом «Громовника» и сравнением',
          os.path.exists(SHOT_M1C) and s['zone'] == 'trail' and s['tip'] == 'Громовник' and vis, s)
    await G('(() => { const g = __game; g.ui.closeAll(); if (g.portal) g.closePortal("replaced"); for (const e of g.enemies) e.stagger = 1e9; })()')
    await run_art(pg, G, check, wait, P)
    await run_v18(pg, G, check, wait)


async def run_art(pg, G, check, wait, P):
    """Спрайты художника вехи M1b (INTEGRATION_m1b.md): загрузка листов и совпадение кадров-событий с игровыми моментами."""
    # --- A1. листы загружены, размеры лент совпадают с JSON
    s = await G('''(() => { const g = __game, A = g.dbg.ART; const bad = [];
        const F = Object.entries(A.sheets); for (const [k, sh] of F) { const m = sh.meta, n = m.frame_count; if (sh.img.naturalWidth !== m.frame_size[0] * n || sh.img.naturalHeight !== m.frame_size[1]) bad.push(k); }
        return { ready: A.ready, failed: A.failed, n: F.length, bad }; })()''')
    fx = await G('''(async () => { const R = await import('/src/render/rest_fx.js'); return ['k_trail', 'k_aura', 'k_summon', 'k_burst', 'k_feed', 'k_feed_back', 'k_feed_src', 'm_ash', 'm_bolt', 'm_hit', 'a_coal'].filter(k => R.FX.sheets[k]).length; })()''')
    check('арт M1b: листы Кривши (15 анимаций × 2 вида), Мары (6 × 2), анчутки (5 × 2, 6а), огнища (4), идола (3) и 11 эффектов (вкл. «огнище питает» v1.8 и уголь анчутки) загружены, размеры лент = JSON',
          s['ready'] and not s['failed'] and s['n'] == 59 and not s['bad'] and fx == 11, {**s, 'fx': fx})

    # --- A2. Кривша: подъём, когти (кадр 6 = удар), призыв (кадр 5 = упыри), прыжок (кадр 6 = приземление), выход (кадр 5 = ореол), гибель
    s = await G('''(async () => { const g = __game; __P__
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map, h = g.hero, D = g.dbg;
        for (const e of g.enemies) if (Math.hypot(e.x - m.idol.x, e.y - m.idol.y) < 16) e.takeDamage(99999, g, 'melee', null); g.simulate(0.2);
        for (const e of g.enemies) e.stagger = 1e9;
        h.x = m.idol.x; h.y = m.idol.y + 4; h.cmd = null; h.invuln = 1e9;
        const b = g.riseBoss('test'), P = (e) => { const p = D.poseKrivsha(e, g.time); return p.anim.replace('krivsha_', '') + ':' + p.frame; }, out = {};
        let last = null; out.rise0 = P(b); g.simulate(3, () => { h.hp = h.maxHp; if (b.state !== 'rise') return true; last = P(b); return false; }); out.riseEnd = last;
        const claw = (n) => { const r = []; let c0 = g.counters.krivshaClaws || 0;
          g.simulate(12, () => { h.hp = h.maxHp; h.x = b.x + 1.0; h.y = b.y; const c = g.counters.krivshaClaws || 0; if (c > c0) { c0 = c; r.push(P(b)); } return r.length >= n; }); return r; };
        out.claw1 = claw(2);
        b.summonT = 1.5; b.minions.forEach(e => e.takeDamage(99999, g, 'melee', null)); let s0 = g.counters.krivshaSummons || 0, sp = null, pre = null;
        g.simulate(3, () => { h.hp = h.maxHp; h.x = b.x + 4; h.y = b.y; if (b.sumAnim != null && pre === null) pre = +b.summonT.toFixed(2); if ((g.counters.krivshaSummons || 0) > s0) { sp = P(b); return true; } return false; });
        out.summon = { pre, at: sp };
        const up = b.minions.find(e => !e.dead && e.state === 'rise'); out.upRise = up ? up.riseTime : null;
        b.minions.forEach(e => e.takeDamage(99999, g, 'melee', null));
        b.hp = Math.ceil(b.maxHp * 0.5) + 2; b.takeDamage(10, g, 'melee', h); const J = []; let wasJump = false, after = null;
        let f0 = g.counters.krivshaFeed || 0; out.feed = null;
        g.simulate(4, () => { h.hp = h.maxHp; h.x = b.x + 4; h.y = b.y; if ((g.counters.krivshaFeed || 0) > f0 && out.feed === null) out.feed = [+b.t.toFixed(3), D.feedFrame(b), P(b), b.state];
          if (b.state === 'jump') { wasJump = true; J.push([+b.t.toFixed(3), P(b)]); return false; } if (wasJump) { after = [b.state, b.aura, P(b)]; return true; } return false; });
        const land = J.findIndex(j => j[0] >= 0.6 - 1e-9); out.jump = { before: J[land - 1] && J[land - 1][1], land: J[land] && J[land][1], loop: [...new Set(J.filter(j => j[0] > 0.7 && j[0] < 1.2).map(j => j[1]))], end: J[J.length - 1], after };
        out.claw2 = claw(2); out.atkMul = b.atkMul;
        b.takeDamage(99999, g, 'melee', h); const dd = []; for (let i = 0; i < 4; i++) { g.simulate(0.4); dd.push(P(b)); }
        out.death = dd; out.perun = { burning: m.perun.burning, outAt: m.perun.outAt != null };
        Math.random = rnd0; return out; })()'''.replace('__P__', P))
    print('АРТ M1c Кривша:', json.dumps(s, ensure_ascii=False), flush=True)
    j = s['jump']
    check('арт Кривша: emerge — держит кадр 0, кадры 1–5 за последние 0,75 с подъёма 2 с (rise не менялся); удар когтями — кадр 6 (hit_frame) ровно в момент удара, в обеих фазах (огненная — fire_claw; v1.8 — скорость атаки прежняя)',
          s['rise0'] == 'emerge:0' and s['riseEnd'] == 'emerge:5' and s['claw1'] == ['claw:6', 'claw:6'] and s['claw2'] == ['fire_claw:6', 'fire_claw:6'] and s['atkMul'] == 1, s)
    check('арт Кривша: призыв — анимация стартует за 0,5 с до таймера, кадр 5 (spawn_frame) = появление упырей; упырь встаёт 0,8 с = 8 кадров fx_krivsha_summon',
          s['summon']['at'] == 'summon:5' and s['summon']['pre'] is not None and 0.45 <= s['summon']['pre'] <= 0.5 and s['upRise'] == 0.8, s['summon'])
    check('арт Кривша: прыжок — кадры 0–5 на дуге 0,6 с, кадр 6 = приземление, петля 6–7; «огнище питает» стартует с fire_emerge, +15% HP — на его кадре 6 (1,85 с); fire_emerge кончается (кадр 5) в момент выхода с ореолом (неуязвимость 2 с не менялась); гибель — 12 кадров, последний держится, идол гаснет',
          s['feed'] is not None and s['feed'][1] == 6 and s['feed'][3] == 'jump' and abs(s['feed'][0] - 1.85) < 0.02 and s['feed'][2].startswith('fire_emerge:')
          and j['before'] == 'leap:5' and j['land'] == 'leap:6' and set(j['loop']) == {'leap:6', 'leap:7'} and j['end'][1] == 'fire_emerge:5' and 1.98 <= j['end'][0] <= 2.0
          and j['after'][0] == 'fight' and j['after'][1] and s['death'][-1] == 'fire_death:11' and s['death'][1] == 'fire_death:8' and s['perun'] == {'burning': False, 'outAt': True}, s)

    # --- A3. Мара: каст — кадр 3 (release_frame) = вылет сгустка (hitAt 0,7), лечение — кадр 3 (apply_frame) = лечение
    s = await G('''(() => { const g = __game; __P__ g.enterZone('zalesye', 'krada'); const h = g.hero, D = g.dbg; const M = g.enemies.find(e => e.kind === 'mara' && !e.dead);
        if (!M) return { none: true }; const P = () => { const p = D.poseMara(M, g.time); return p.anim.replace('mara_', '') + ':' + p.frame; };
        for (const e of g.enemies) if (e !== M) e.stagger = 1e9; h.invuln = 1e9; h.cmd = null; M.route = null; let spot = null;
        for (let i = 0; i < 32 && !spot; i++) { const a = i / 32 * Math.PI * 2, r = 4 + (i % 2) * 0.5, x = M.x + Math.cos(a) * r, y = M.y + Math.sin(a) * r;
          if (D.circleFree(g.map, x, y, 0.4) && g.map.isReachableAt(x, y) && !g.safeAt(x, y, 1) && D.sightClear(g.map, M.x, M.y, x, y)) spot = [x, y]; }
        if (!spot) return { none: 'spot' }; h.x = spot[0]; h.y = spot[1]; M.aggro(g, false);
        const out = { rel: [] }; let fired = false;
        g.simulate(10, () => { h.hp = h.maxHp; h.x = spot[0]; h.y = spot[1]; if (M.state === 'attack' && M.attackFired && !fired) { fired = true; out.rel.push([+M.t.toFixed(2), P()]); } if (M.state !== 'attack') fired = false; return out.rel.length >= 2; });
        const ally = g.enemies.find(e => e !== M && e.pack === M.pack && !e.dead); out.ally = !!ally;
        if (ally) { ally.hp = Math.round(ally.maxHp * 0.5); ally.x = M.x + 1; ally.y = M.y; M.healT = 7; let h0 = g.counters.maraHeals || 0;
          g.simulate(3, () => { h.hp = h.maxHp; h.x = M.x + 30; h.y = M.y; M.state = 'idle'; if ((g.counters.maraHeals || 0) > h0) { out.heal = P(); return true; } return false; }); }
        M.takeDamage(99999, g, 'melee', h); g.simulate(1.2); out.death = P(); Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('арт Мара: каст — кадр 3 (release_frame) в момент вылета сгустка (hitAt 0,7 с); лечение — кадр 3 (apply_frame) в момент +15%; гибель — последний кадр держится',
          not s.get('none') and len(s['rel']) == 2 and all(r[1] == 'cast:3' for r in s['rel']) and s.get('heal') == 'heal:3' and s['death'] == 'death:7', s)

    # --- A4. отрисовка: в кадре реально рисуются листы (Кривша, огнище, идол), без ошибок консоли
    s = await G('''(async () => { const g = __game; __P__
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map, h = g.hero;
        for (const e of g.enemies) if (Math.hypot(e.x - m.idol.x, e.y - m.idol.y) < 16) e.takeDamage(99999, g, 'melee', null); g.simulate(0.2);
        h.x = m.idol.x - 1; h.y = m.idol.y + 4; h.invuln = 1e9; const b = g.riseBoss('test'); g.simulate(2.3); b.stagger = 1e9; g.updateCamera();
        const seen = new Set(), orig = CanvasRenderingContext2D.prototype.drawImage;
        CanvasRenderingContext2D.prototype.drawImage = function (im, ...a) { if (im && im.src) { const f = im.src.split('/').pop(); if (/^(krivsha|ognishche|idol_perun|fx_krivsha|mara)/.test(f)) seen.add(f.replace(/\\.png$/, '')); } return orig.call(this, im, ...a); };
        await new Promise(r => setTimeout(r, 300)); CanvasRenderingContext2D.prototype.drawImage = orig; Math.random = rnd0;
        return [...seen].sort(); })()'''.replace('__P__', P))
    check('арт: в кадре рисуются листы Кривши, огнищ и горящего идола (грей-бокс заменён)',
          any(x.startswith('krivsha_') for x in s) and 'ognishche_desecrated' in s and 'idol_perun_burning' in s, s)

    # --- A5. анчутка (6а, 08.10): бросок — кадр выпуска 3 ровно на hitAt 0,45; рост 26 не менялся; уголь в полёте — лист fx_anchutka_coal
    s = await G('''(async () => { const g = __game; __P__
        const h = g.hero, D = g.dbg; delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada');
        const a = g.enemies.find(e => e.kind === 'anchutka' && !e.special); if (!a) return { none: true };
        const pose = (t) => { const keep = { state: a.state, t: a.t, moving: a.moving }; a.state = 'attack'; a.t = t; a.moving = false; const p = D.poseAnchutka(a, 0); Object.assign(a, keep); return p.anim.replace('anchutka_', '') + ':' + p.frame; };
        h.x = a.x - 3.2; h.y = a.y; h.invuln = 1e9; a.aggro(g, false); const out = { h: a.def.height, at0: pose(0), atHit: pose(0.45), atAfter: pose(0.75) };
        g.simulate(2, () => { h.hp = h.maxHp; return a.attackFired; });
        out.fired = !!a.attackFired; const R = await import('/src/render/rest_fx.js'); out.fx = !!R.FX.sheets.a_coal;
        Math.random = rnd0; return out; })()'''.replace('__P__', P))
    check('арт анчутка (6а): кадр 3 (release_frame) броска угля — ровно на hitAt 0,45 с, дальше idle; рост 26; уголь — спрайт fx_anchutka_coal',
          not s.get('none') and s['at0'] == 'coal_throw:0' and s['atHit'] == 'coal_throw:3' and s['atAfter'].startswith('idle') and s['h'] == 26 and s['fired'] and s['fx'], s)


    await G('(() => { const g = __game; for (const e of g.enemies) e.stagger = 1e9; g.combat.teles.length = 0; })()')

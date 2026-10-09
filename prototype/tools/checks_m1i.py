# Веха m1i: замечания критиков m1f — P2 (п.11–16), 10b (подписи частей Ладоги), W (staff_3 «Жезл»).
import os, json
from check_cyrillic import scan as cyr_scan, selftest as cyr_selftest

ROOT = '/workspace/game/prototype/'
SHOT_STASH = ROOT + 'screenshot_m1i_stash.png'
SHOT_TRADE = ROOT + 'screenshot_m1i_trade.png'
SHOT_MENU = ROOT + 'screenshot_m1i_menu.png'
SHOT_WORLD = ROOT + 'screenshot_m1i_world.png'
BAK = '/tmp/proto_bak_m1i/'

TP = '''(([x, y]) => { const h = __game.hero; h.x = x; h.y = y; h.path = null; h.cmd = null; h.action = null; h.moving = false; __game.updateCamera(); })'''


async def run_m1i(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1i', flush=True)

    async def fresh(url, menu=False):
        await pg.goto(url)
        await pg.wait_for_function('() => window.__game && __game.state === "menu" && (__game.frames || 0) > 3' if menu else '() => window.__game && __game.time > 0.3')
        await wait(100)

    async def mouse(sx, sy):
        await pg.mouse.move(*(await client_scr(sx, sy))); await wait(120)

    # ---------- правило ru.json: в src/**/*.js нет кириллицы в строковых литералах (вне комментариев), кроме явного списка
    hits, allowed = cyr_scan()
    check('m1i ru.json: в src/**/*.js 0 строковых литералов с кириллицей (комментарии не в счёт; исключения — явный список '
          'tools/check_cyrillic.py: имена столбцов ru.json, сравнения с данными, console/исключения, таблица шрифта, атлас)',
          not hits and cyr_selftest(), {'hits': hits[:5], 'allowed': allowed})

    await fresh(a.url)
    s = await G('''(async () => { const g = __game, H = await import('/src/render/hud.js'), I = await import('/src/data/items.js');
        const L = I.itemLines(I.makeItem('sword_1', 'normal', 1)).lines.map(l => l[0]);
        return { btn: H.BTN.labels, name: g.hero.name, lines: L, raw: L.concat(H.BTN.labels).filter(x => /^(proto|ui)[.]/.test(x)) }; })()''')
    check('m1i перенос строк в ru.json: подписи кнопок HUD, имя героя, строки подсказки вещи — те же тексты, сырых ключей нет',
          s['btn'] == ['Витязь', 'Котомка', 'Навыки', 'Карта', 'Летопись', 'Меню'] and s['name'] == 'Ратибор' and not s['raw']
          and any(l.startswith('Урон: ') for l in s['lines']) and any(l.startswith('Требуется уровень: ') for l in s['lines']), s)

    # ---------- W. staff_3 «Жезл»: магические имена staff_1 и staff_3 различаются
    s = await G('''(async () => { const C = __game.dbg.CFG, I = await import('/src/data/items.js');
        const B = C.items_base.bases, b1 = B.find(b => b.id === 'staff_1'), b3 = B.find(b => b.id === 'staff_3');
        const fits = (b, k) => C.affixes.affixes.filter(x => x.kind === k && x.tiers && x.tiers[1] && x.slots.some(s => s === b.type || s === b.slot || s === 'weapon'));
        const pre = fits(b1, 'prefix')[0], suf = fits(b1, 'suffix')[0];
        const mk = id => I.makeItem(id, 'magic', 5, Math.random, { affixes: [[pre.id, pre.tiers[1][0]], [suf.id, suf.tiers[1][0]]] }).name;
        const mkS = id => I.makeItem(id, 'magic', 5, Math.random, { affixes: [[suf.id, suf.tiers[1][0]]] }).name;
        // все базы одного типа: имена «с суффиксом» (короткое имя) не совпадают
        const dup = [], seen = {};   // ни у каких двух баз короткое имя не совпадает (W + сценарист: head_2 «Наносник»)
        for (const b of B) { const k = b.shortName || b.name; if (seen[k]) dup.push([seen[k], b.id, k]); seen[k] = b.id; }
        const h = id => { const x = B.find(b => b.id === id); return [x.shortName, x.gender]; };
        return { heads: [h('head_2'), h('head_3')], short: [b1.shortName, b3.shortName], n1: mk('staff_1'), n3: mk('staff_3'), s1: mkS('staff_1'), s3: mkS('staff_3'), dup }; })()''')
    check('m1i W: staff_3 shortName «Жезл», staff_1 «Посох»; магические имена с аффиксами различаются (staff_3 — «…жезл…»); '
          'head_2 «Наносник», head_3 «Шелом»; ни у каких двух баз короткие имена не совпадают',
          s['short'] == ['Посох', 'Жезл'] and s['n1'] != s['n3'] and 'жезл' in s['n3'].lower() and s['s1'] != s['s3'] and 'Жезл' in s['s3'] and not s['dup'] and s['heads'] == [['Наносник', 'm'], ['Шелом', 'm']], s)

    # ---------- 11. Ладья
    await G('''(async () => { const g = __game, I = await import('/src/data/items.js'); g.ui.closeAll(); g.enterZone('ladoga', 'start');
        g.stash.entries.length = 0; g.stash.autoAdd(I.makeItem('ring_1', 'magic', 5)); g.stash.autoAdd(I.makeItem('sword_1', 'normal', 2)); g.stash.autoAdd(I.makePotion('life1'));
        g.stashSilver = 123; g.hero.silver = 45; g.town.openStash(); g.ui.toggleInv(true); g.updateCamera(); })()''')
    await mouse(52, 39)
    s = await G('''(async () => { const g = __game, T = await import('/src/ui/town.js'), tip = g.ui.lastTip, src = await (await fetch('/src/ui/town.js')).text(), w = await (await fetch('/src/ui/windows.js')).text();
        return { win: [T.STASH_WIN.w, T.STASH_WIN.h], grid: [g.stash.w, g.stash.h], gx: T.STASH_GRID.x, gright: T.STASH_GRID.x + g.stash.w * 24, wright: T.STASH_WIN.x + T.STASH_WIN.w,
          gbottom: T.STASH_GRID.y + g.stash.h * 24, wbottom: T.STASH_WIN.y + T.STASH_WIN.h, tip: tip && { from: tip.from, x: tip.x },
          shared: src.includes('drawGridEntries(ctx, g, g.stash') && w.includes('drawGridEntries(ctx'), silverKey: src.includes("t('ui.stash.silver'") && src.includes('silverText(g.hero.silver)'),
          hint: src.includes("t('ui.stash.hint')"), mode: g.town.mode }; })()''')
    check('m1i П.11 ладья: окно 256×232 (GDD §6.9), сетка 10×8 внутри окна, вещи рисует общий код котомки (drawGridEntries), '
          '«Серебро в ладье: N» + серебро при себе, подсказка ui.stash.hint; подсказка вещи ладьи справа от окна',
          s['win'] == [256, 232] and s['grid'] == [10, 8] and s['gright'] <= s['wright'] - 6 and s['gbottom'] + 12 <= s['wbottom'] and s['shared'] and s['silverKey'] and s['hint']
          and s['tip'] and s['tip']['from'] == 'stash' and s['tip']['x'] >= s['wright'], s)
    await pg.screenshot(path=SHOT_STASH, clip={'x': 0, 'y': 0, 'width': 1920, 'height': 1080})
    s = await G('''(() => { const g = __game, r = []; g.town.moveSilver(true); r.push([g.hero.silver, g.stashSilver]); g.town.moveSilver(false); r.push([g.hero.silver, g.stashSilver]); return r; })()''')
    check('m1i П.11 кнопки серебра переносят всё: 45/123 → 0/168 → 168/0', s == [[0, 168], [168, 0]], s)

    # ---------- 12. Торг
    await G('''(async () => { const g = __game, I = await import('/src/data/items.js'); g.ui.closeAll(); const v = g.npcs.find(n => n.role === 'vedana');
        g.hero.inv.entries.length = 0; g.hero.inv.add(I.makeItem('ring_1', 'magic', 5), 0, 0); g.hero.silver = 30;
        g.town.openNpc(v); g.town.mode = 'trade'; g.town.tab = 'buy'; g.ui.toggleInv(true); g.updateCamera(); })()''')
    await wait(100)
    rows = await G('''(() => { const g = __game; return g.town.layout().filter(r => r.kind === 'row').map(r => ({ x: r.x, y: r.y, h: r.h, icon: !!r.icon, price: r.price })); })()''')
    await mouse(rows[0]['x'] + 60, rows[0]['y'] + rows[0]['h'] // 2)
    s = await G('''(async () => { const g = __game, T = await import('/src/ui/town.js'), { t, silverText } = await import('/src/core/i18n.js'), tip = g.ui.lastTip;
        const rows = g.town.layout(); const src = await (await fetch('/src/ui/town.js')).text();
        return { head: rows.some(r => r.kind === 'head'), price: t('proto.trade.price'), sil: silverText(7, 'ground'), icons: rows.filter(r => r.kind === 'row').every(r => !!r.icon),
          tip: tip && { from: tip.from, x: tip.x, lines: tip.lines }, right: T.WIN.x + T.WIN.w, frame: src.includes('drawBagFrame(ctx, WIN.x'), buy: t('ui.tip.price_buy', { n: rows.find(r => r.kind === 'row').price }) }; })()''')
    check('m1i П.12 торг: рамка и шапка котомки (drawBagFrame), шапка «Цена», иконка в каждой строке, цены «N сер.»; '
          'подсказка строки лавки справа от окна с «Цена: N сер.»',
          s['head'] and s['price'] == 'Цена' and s['sil'] == '7 сер.' and s['icons'] and s['frame'] and len(rows) >= 3
          and s['tip'] and s['tip']['from'] == 'shop' and s['tip']['x'] >= s['right'] and s['buy'] in s['tip']['lines'], s)
    await mouse(371, 178)
    s = await G('''(async () => { const g = __game, { t } = await import('/src/core/i18n.js'), I = await import('/src/systems/trade.js'), tip = g.ui.lastTip, it = g.hero.inv.entries[0].item;
        return { tip: tip && { x: tip.x, lines: tip.lines }, sell: t('ui.tip.price_sell', { n: I.sellPrice ? I.sellPrice(it) : -1 }) }; })()''')
    check('m1i П.12 подсказка вещи котомки в торге — справа (x ≥ 320, не поверх цен) и со строкой «Продать за N сер.»',
          s['tip'] and s['tip']['x'] >= 320 and any(l.startswith('Продать за') for l in s['tip']['lines']), s)
    await mouse(rows[1]['x'] + 60, rows[1]['y'] + rows[1]['h'] // 2)
    await pg.screenshot(path=SHOT_TRADE)

    # ---------- 13. Пауза
    await G('(() => { const g = __game; g.town.close(); g.ui.closeAll(); g.paused = true; })()')
    await wait(150)
    s = await G('''(async () => { const g = __game, S = await import('/src/render/screens.js'), F = await import('/src/core/font.js'), { t } = await import('/src/core/i18n.js');
        const lw = S.PAUSE_BTNS.map(b => F.textWidth(t(b.key).replace(/ \\(.\\)$/, '')));
        return { lines: g.pauseLines, lw, bw: S.PAUSE_BTNS.map(b => b.w), on: t('proto.toggle.on'), off: t('proto.toggle.off') }; })()''')
    flat = ' '.join(a_ + ' ' + b_ for a_, b_ in s['lines'])
    check('m1i П.13 пауза: подпись и «вкл/выкл» раздельно (подпись не заходит на плашку 34 px), «Удали» с прописной, строка рывка «Пробел»',
          all(w + 4 <= bw - 34 for w, bw in zip(s['lw'], s['bw'])) and s['on'] == 'вкл' and s['off'] == 'выкл'
          and 'Удали' in flat and 'удали' not in flat and any(a_ == 'Пробел' and 'рывок' in b_ for a_, b_ in s['lines']) and len(s['lines']) == 11, s)
    await G('(() => { __game.paused = false; })()')

    # ---------- 14. Капище — realm nebyl; 16: красноватая темнота
    await G('''(() => { const g = __game; g.enterZone('kapishche', 'start'); g.updateCamera(); })()''')
    await wait(150)
    s = await G('''(() => { const g = __game; return { realm: g.dbg.CFG.zones.kapishche.realm, tint: g.darkTint }; })()''')
    rgb = [int(x) for x in s['tint'][5:].split(',')[:3]] if s['tint'] else [0, 0, 0]
    check('m1i П.14 капище в Небыли (realm "nebyl", GDD v1.11); П.16 темнота над капищем красноватая (R > B)', s['realm'] == 'nebyl' and rgb[0] > rgb[2] * 2, s)

    # ---------- 16. Залесье: камни, стены-тын, разнос подписей, баннер, труп
    await G('''(() => { const g = __game; g.enterZone('zalesye', 'start'); g.enemies = g.enemies.filter(e => !e.special); })()''')
    await G(TP + '([19.5, 30.2])')
    await G('''(async () => { const g = __game, h = g.hero, I = await import('/src/data/items.js'); g.loot.items.length = 0;
        for (const id of ['sword_1', 'ring_1', 'body_2', 'staff_3', 'staff_1', 'ring_1']) g.loot.spawnItem(h.x + 1, h.y, I.makeItem(id, 'magic', 4));
        g.labelsAlways = true;
        const e = g.spawnTest('chernoyarets_arsonist', h.x + 2, h.y + 1.2, 1); e.hp = 0; e.dead = true; e.corpseT = 1; e.state = 'dead'; window.__m1iCorpse = e;
        g.notify(g.t('ui.sys.mission_done', { mission: g.quest.title }), '#f2d48a', 'mission', 4); })()''')
    await pg.mouse.move(1910, 10)
    await wait(400)
    s = await G('''(async () => { const g = __game, P = await import('/src/render/props.js'), { PAL } = await import('/src/palette.js');
        const L = g.lootLabels || [], ov = [];
        for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { const p = L[i], q = L[j];
          if (p.x < q.x + q.w && p.x + p.w > q.x && p.y < q.y + q.h && p.y + p.h > q.y) ov.push([p.text, q.text]); }
        const cx = L.map(l => Math.round(l.x + l.w / 2)), lv = Math.max(0, ...L.map(l => l.level)), wall = (g.map.props || []).find(p => p.type === 'wall');
        const pal = new Set(Object.values(PAL)), stone = Object.values(P.STONE).flat();
        const e = window.__m1iCorpse, B = g.bannerDrawn;
        return { n: L.length, ov, lv, spread: new Set(cx).size, stoneOk: stone.length >= 8 && stone.every(c => pal.has(c)) && stone.includes(PAL.moss),
          tyn: wall ? P.wallAsTyn(wall) : null, corpse: { style: e.corpseStyle, canvas: !!(e._corpse && e._corpse.c) },
          banner: B && { w: B.w, h: B.h, text: B.text, fresh: g.time - B.t < 1 } }; })()''')
    check('m1i П.16 подписи добычи: 6 подписей без наложений, разнесены «лесенкой» (разные центры по x)',
          s['n'] >= 6 and not s['ov'] and s['spread'] >= 2 and s['lv'] >= 2, {k: s[k] for k in ('n', 'ov', 'spread', 'lv')})
    check('m1i П.16 камни — палитра v2 с мхом (STONE: тёплый серо-оливковый), стены Залесья рисуются логикой тына (wallAsTyn: высота 26–32, 2 перевязи)',
          s['stoneOk'] and s['tyn'] and 26 <= s['tyn']['tynH'] <= 32 and len(s['tyn']['bands']) == 2, {'stone': s['stoneOk'], 'tyn': s['tyn']})
    check('m1i П.16 «Миссия пройдена» — плашкой-баннером (bannerDrawn), труп без кадров смерти — затемнённый кадр «лёжа»',
          s['banner'] and s['banner']['fresh'] and s['banner']['text'].startswith('Миссия пройдена') and s['banner']['h'] >= 15
          and s['corpse'] == {'style': 'lying', 'canvas': True}, {'banner': s['banner'], 'corpse': s['corpse']})
    await pg.screenshot(path=SHOT_WORLD)
    await G('(() => { __game.labelsAlways = false; })()')

    # ---------- 10b. Подписи частей Ладоги: бледные, без рамки, не наводятся; NPC не сдвинуты
    await G('''(() => { const g = __game; g.enterZone('ladoga', 'start'); })()''')
    await G(TP + '([24.5, 19.5])')
    await wait(200)
    cap = await G('(() => __game.labelsDrawn.filter(l => l.caption))()')
    if cap:
        await mouse(cap[0]['x'] + cap[0]['w'] / 2, cap[0]['y'] + 4)
    s = await G('''(() => { const g = __game; return { hl: g.hoverLabel ? (g.hoverLabel.text || 'label') : null, ho: g.hoverObj ? g.hoverObj.id || 'obj' : null }; })()''')
    same = None
    if os.path.exists(BAK + 'data/zones/ladoga.json'):
        A = json.load(open(BAK + 'data/zones/ladoga.json')); B = json.load(open(ROOT + 'data/zones/ladoga.json'))
        same = json.dumps(A.get('npcs'), sort_keys=True) == json.dumps(B.get('npcs'), sort_keys=True)
    check('m1i П.10b подписи частей Ладоги: бледные (alpha ≤ 0.6), без обводки/рамки, наведение их не ловит; NPC на прежних местах',
          cap and all(c['alpha'] <= 0.6 and c['outline'] is False for c in cap) and s['hl'] is None and s['ho'] is None and same is not False,
          {'cap': cap[:2], **s, 'npcs_same': same})

    # ---------- 15. Сохранение: автосейв на сдаче, круговой цикл «сохранить → меню → Продолжить»
    s = await G('''(async () => { const g = __game, I = await import('/src/data/items.js'), q = g.quest; g.ui.closeAll();
        q.missionDone = true; delete q.flags['m1.turnedIn']; g.town.placeVyshata && g.town.placeVyshata();
        const vy = g.npcs.find(n => n.role === 'vyshata'); g.lastSave = null; const ok = vy ? g.town.claimM1() : null; g.town.close();
        const r1 = g.lastSave && g.lastSave.reason;
        q.flags['m1.gromovnik'] = true; q.flags.m1i_probe = 7;
        g.stash.entries.length = 0; g.stash.autoAdd(I.makeItem('staff_3', 'magic', 5)); g.stash.autoAdd(I.makePotion('life1')); g.stashSilver = 77; g.hero.silver = 33;
        g.hero.belt[0] = null; g.hero.inv.entries.length = 0; g.hero.inv.add(I.makeItem('ring_1', 'normal', 1), 2, 1);
        g.enterZone('zalesye', 'start'); g.lastSave = null; g.enterZone('ladoga', 'start'); const r2 = g.lastSave && g.lastSave.reason;
        const want = { flags: JSON.stringify(q.flags), stash: g.stash.entries.map(e => [e.item.name, e.c, e.r]), ss: g.stashSilver, silver: g.hero.silver,
          belt: JSON.stringify(g.hero.belt), inv: g.hero.inv.entries.map(e => [e.item.name, e.c, e.r]), obj: q.obj.map(o => o.state), done: q.missionDone, lvl: g.hero.level };
        return { vy: !!vy, ok, r1, r2, want, key: !!localStorage.getItem('bylnebyl.v1.slot1') }; })()''')
    check('m1i П.15 автосейв: при сдаче миссии (reason «turnin») и при входе в Ладогу (reason «ladoga»), слот bylnebyl.v1.slot1',
          s['r1'] == 'turnin' and s['r2'] == 'ladoga' and s['key'], {k: s[k] for k in ('vy', 'ok', 'r1', 'r2', 'key')})
    want = s['want']
    await fresh(a.url + ('&' if '?' in a.url else '?') + 'menu=1', True)
    s = await G('''(async () => { const g = __game, S = await import('/src/render/screens.js');
        return { state: g.state, slot: !!(g.menu && g.menu.slot), btns: S.MENU_BTNS.map(b => [b.id, b.x + b.w / 2, b.y + b.h / 2]) }; })()''')
    check('m1i П.15 главное меню (?menu=1): состояние «menu», слот найден, кнопки «Продолжить» / «Новая игра»',
          s['state'] == 'menu' and s['slot'] and [b[0] for b in s['btns']] == ['continue', 'new'], s)
    await pg.mouse.move(*(await client_scr(320, 120))); await wait(80)
    await pg.screenshot(path=SHOT_MENU)
    btn = {b[0]: b for b in s['btns']}
    # «Новая игра» при занятом слоте спрашивает подтверждение; «Нет» возвращает меню, слот цел
    await pg.mouse.click(*(await client_scr(btn['new'][1], btn['new'][2]))); await wait(150)
    c1 = await G('(() => ({ state: __game.state, confirm: !!__game.menu.confirm }))()')
    await pg.keyboard.press('Escape'); await wait(150)
    c2 = await G('(() => ({ state: __game.state, confirm: !!__game.menu.confirm, slot: !!localStorage.getItem("bylnebyl.v1.slot1") }))()')
    check('m1i П.15 «Новая игра» при занятом слоте — подтверждение; Esc — отмена, слот цел; «Летопись» — заглушка (в меню нет)',
          c1 == {'state': 'menu', 'confirm': True} and c2 == {'state': 'menu', 'confirm': False, 'slot': True}, [c1, c2])
    await pg.mouse.click(*(await client_scr(btn['continue'][1], btn['continue'][2]))); await wait(250)
    got = await G('''(() => { const g = __game, q = g.quest;
        return { state: g.state, zone: g.zone.id, flags: JSON.stringify(q.flags), stash: g.stash.entries.map(e => [e.item.name, e.c, e.r]), ss: g.stashSilver, silver: g.hero.silver,
          belt: JSON.stringify(g.hero.belt), inv: g.hero.inv.entries.map(e => [e.item.name, e.c, e.r]), obj: q.obj.map(o => o.state), done: q.missionDone, lvl: g.hero.level }; })()''')
    diff = [k for k in want if want[k] != got.get(k)]
    check('m1i П.15 загрузка слота («Продолжить»): игра в Ладоге, флаги (m1.gromovnik, m1.turnedIn…), ладья, серебро (при себе и в ладье), пояс, котомка, задание — как при сохранении',
          got['state'] == 'play' and got['zone'] == 'ladoga' and not diff, {'diff': diff, 'state': got['state'], 'zone': got['zone']})

    # ---------- GDD v1.12.2 §11: павшие боссы (bosses.dead) — навсегда; живой босс после загрузки — на месте с полным HP
    await fresh(a.url)
    s = await G('''(() => { const g = __game, h = g.hero; h.invuln = 1e9;
        g.enterZone('zalesye', 'start'); const mara = g.enemies.find(e => e.kind === 'mara' && !e.dead);
        const alive = mara ? [mara.hp === mara.maxHp, g.enemies.filter(e => e.special === 'mara').length] : null;
        if (mara) { h.x = mara.x - 1; h.y = mara.y; h.stop(); mara.takeDamage(99999, g, 'melee', h); g.simulate(0.3); }
        const k1 = [...g.bossesDead];
        g.enterZone('kapishche', 'start'); const m = g.map; h.x = m.idol.x - 1; h.y = m.idol.y + 4; h.stop();
        const b = g.riseBoss('test'); g.simulate(2.3); b.takeDamage(99999, g, 'melee', h); g.simulate(0.3);
        const k2 = [...g.bossesDead], st = g.zs.bossState;
        g.enterZone('ladoga', 'start'); const d = JSON.parse(localStorage.getItem('bylnebyl.v1.slot1'));
        return { alive, k1, k2, st, saved: d.bosses, reason: g.lastSave && g.lastSave.reason }; })()''')
    check('m1i §11 v1.12.2: гибель Огнеи (mara) и Кривши пишется в слот bosses.dead (при входе в Ладогу); до гибели Огнея со свитой и полным HP',
          s['alive'] and s['alive'][0] and s['alive'][1] >= 2 and s['k1'] == ['mara'] and sorted(s['k2']) == ['krivsha', 'mara'] and s['st'] == 'dead'
          and sorted((s['saved'] or {}).get('dead', [])) == ['krivsha', 'mara'] and s['reason'] == 'ladoga', s)
    await fresh(a.url + ('&' if '?' in a.url else '?') + 'menu=1', True)
    s = await G('''(() => { const g = __game; const ok = g.loadGame(), h = g.hero; h.invuln = 1e9;
        g.enterZone('zalesye', 'start'); g.simulate(1);
        const z = { mara: g.enemies.filter(e => e.kind === 'mara' || e.special === 'mara').length, loot: g.loot.items.length };
        g.enterZone('kapishche', 'start'); const m = g.map; h.x = m.idol.x; h.y = m.idol.y + 2; h.stop(); g.simulate(2);
        const k = { st: g.zs.bossState, boss: g.enemies.filter(e => e.kind === 'krivsha' || e.boss || e.summoned || e.pack === 'krivsha').length,
          rise: g.riseBoss('test') === null, loot: g.loot.items.filter(it => !it.quest).length, idolOut: !!(m.perun && !m.perun.burning),
          body: !!m.objects.find(o => o.id === 'krivsha_body') };
        return { ok, dead: [...g.bossesDead].sort(), z, k }; })()''')
    check('m1i §11 v1.12.2: после загрузки павшие не появляются — в Залесье нет Огнеи и свиты, в капище нет Кривши/призванных, '
          'босс не встаёт, добыча не выпадает снова; идол погас, тело Кривши на месте',
          s['ok'] and s['dead'] == ['krivsha', 'mara'] and s['z'] == {'mara': 0, 'loot': 0}
          and s['k'] == {'st': 'dead', 'boss': 0, 'rise': True, 'loot': 0, 'idolOut': True, 'body': True}, s)
    s = await G('''(() => { const g = __game; g.newGame(); g.enterZone('zalesye', 'start'); const mara = g.enemies.find(e => e.kind === 'mara');
        const r = { dead: [...g.bossesDead, ...g.bossesDeadLoaded], mara: !!mara && mara.hp === mara.maxHp }; g.enterZone('kapishche', 'start'); r.st = g.zs.bossState; return r; })()''')
    check('m1i §11 v1.12.2: новая игра — список павших пуст, Огнея на месте с полным HP, Кривша спит (dormant)',
          s == {'dead': [], 'mara': True, 'st': 'dormant'}, s)

    # ---------- PM п.4: иконки поясов в строках лавки — того же размера, что и прочие (1:1, без размытия)
    s = await G('''(async () => { const g = __game, A = await import('/src/ui/assets.js'); g.ui.closeAll(); g.enterZone('ladoga', 'start');
        g.town.openNpc(g.npcs.find(n => n.role === 'vedana')); g.town.mode = 'trade'; g.town.tab = 'buy';
        const rows = g.town.layout().filter(r => r.kind === 'row'); g.town.close();
        const sz = rows.map(r => [r.icon, ...A.iconFitSize(r.icon, 16, r.h - 1, { crop: true })]);
        const belts = sz.filter(x => /kushak|poyas/.test(x[0])), other = sz.filter(x => !/kushak|poyas/.test(x[0]));
        return { belts, maxOther: Math.max(...other.map(x => x[2])), rowH: rows[0] && rows[0].h }; })()''')
    check('m1i PM п.4: иконки поясов в лавке — высотой как прочие (вписаны по высоте 1:1, правый край с пряжкой), не 16×6',
          s['belts'] and all(b[2] >= s['maxOther'] - 2 and b[1] == 16 for b in s['belts']), s)

    # ---------- дизайнер: тын Залесья — низкий (колья 26–32, propHeight 44, герой виден); высокий — только посад Ладоги и капище
    s = await G('''(async () => { const g = __game, P = await import('/src/render/props.js'), out = {};
        for (const z of ['zalesye', 'ladoga', 'trail']) { g.enterZone(z, 'start');
          const f = (g.map.props || []).filter(p => p.type === 'wall' || p.type === 'palisade');
          const hs = f.flatMap(p => P.stakeHeights(p.type === 'wall' ? P.wallAsTyn(p) : p));
          out[z] = { n: f.length, min: Math.min(...hs), max: Math.max(...hs), ph: [...new Set(f.map(p => P.propHeight(p)))] }; }
        return { out, hero: g.hero.height || 46 }; })()''')
    zl, ld, tr = s['out']['zalesye'], s['out']['ladoga'], s['out']['trail']
    check('m1i дизайнер: тын Залесья низкий — колья 26–32 px, propHeight 44 (герой ≈46 px виден из-за него); посад Ладоги и частокол капища — 80+',
          zl['n'] > 0 and zl['min'] >= 26 and zl['max'] <= 32 and zl['ph'] == [44] and zl['max'] + 6 < s['hero']
          and ld['min'] >= 76 and tr['min'] >= 76, s)

    await fresh(a.url)
    await pg.mouse.click(960, 300)
    await wait(100)

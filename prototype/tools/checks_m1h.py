# Веха m1h: замена терминов (story/rename_map.md v1.0, inbox/rename_plan.md): видимые строки, длины/вёрстка, старые флаги сохранения.
import os, json
from check_rename import scan, selftest

ROOT = '/workspace/game/prototype/'
SHOT_HUD = ROOT + 'screenshot_m1h_hud.png'
SHOT_REWARD = ROOT + 'screenshot_m1h_reward.png'
LEN_OUT = ROOT + 'tools/length_m1h.json'


async def run_m1h(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1h', flush=True)
    # ---------- 1. grep старых форм по всему видимому игроку (tools/check_rename.py)
    hits, counted = scan()
    miss, false = selftest()
    check('m1h check_rename: в ru.json, именах data/*.json и литералах src/ нет старых форм (Ярь, Чуров, крада, чур-идол, Посох-чур, Громовник, '
          'Око Рода, Ведана, Мара, Сварожий, резы, родовая ярость); образцы ловят все формы таблицы и не задевают keep-list',
          not hits and not miss and not false and counted['src'] > 1000, {'hits': hits[:5], 'miss': miss, 'false': false})

    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')
    await pg.mouse.click(960, 300)
    await wait(150)

    # ---------- 2. новые имена в игре (данные загружены, ключи и id прежние)
    s = await G('''(async () => { const g = __game, C = g.dbg.CFG, I = await import('/src/data/items.js'), { t, tObj, RU } = await import('/src/core/i18n.js');
        const P07 = C.affixes.affixes.find(x => x.id === 'P07'), st = C.items_base.bases.find(b => b.id === 'staff_3');
        const pot = I.itemLines(I.makePotion('yar1')).lines.map(l => l[0]), both = Object.keys(I.POTIONS).find(k => I.POTIONS[k].res === 'both');
        return { hud: t('ui.hud.yar'), res: C.stats.resourceName, u2: I.makeUnique('U2').name, boss: C.bosses.mara.name, codex: RU['codex.mara']['Имя'],
          staff: [st.name, st.shortName], p07: P07 && P07.names, nouns: C.affixes.rareNames.nouns.map(n => n[0] || n),
          pots: ['yar1', 'yar2', 'yar3'].map(k => I.POTIONS[k].name), pot, both: both ? I.itemLines(I.makePotion(both)).lines[1][0] : null,
          vedana: [t('npc.vedana'), t('ui.trade.vedana')], yar1: tObj('skill.yar1').name, tier: t('ui.hero.yar_tier'), cost: t('ui.skills.cost', { n: 5 }),
          portal: t('obj.chur_portal'), stone: t('ui.obj.chur_stone'), idol: t('ui.obj.idol'), arena: t('ui.error.beresta_arena'),
          ids: [!!C.bosses.mara, !!P07, !!st, 'yar1' in I.POTIONS, !!RU['npc.vedana.s1'], !!RU['obj.chur_stone'], g.hero.maxYar > 0] }; })()''')
    check('m1h новые имена в игре: шар «Удаль», resourceName «Удаль», U2 «Громовой знак», «Огнея Пепельная», «Посох волхва»/«Жезл» (m1i W), P07 «Жгучий/-ая/-ее/-ие», '
          'rareNames «Отвага» (без «Удаль»), зелья Удали, «Милуша»/«Изба Милуши», «Удаль I», «Удаль: ступень I», «Удаль: 5»; id/ключи прежние',
          s['hud'] == 'Удаль' and s['res'] == 'Удаль' and s['u2'] == 'Громовой знак' and s['boss'] == s['codex'] == 'Огнея Пепельная'
          and s['staff'] == ['Посох волхва', 'Жезл'] and s['p07'] == {'m': 'Жгучий', 'f': 'Жгучая', 'n': 'Жгучее', 'pl': 'Жгучие'}
          and 'Отвага' in s['nouns'] and 'Удаль' not in s['nouns'] and s['pots'] == ['Слабое зелье Удали', 'Зелье Удали', 'Крепкое зелье Удали']
          and s['pot'][1].endswith('к Удали за 3 с') and (s['both'] is None or s['both'].endswith('жизни и Удали'))
          and s['vedana'] == ['Милуша', 'Изба Милуши'] and s['yar1'] == 'Удаль I' and s['tier'] == 'Удаль: ступень I' and s['cost'] == 'Удаль: 5'
          and s['portal'] == 'Путевой проход' and s['stone'] == 'Путевой камень' and s['idol'] == 'Чёрный идол: руби'
          and s['arena'] == 'Пока враг стоит, проход не откроется.' and all(s['ids']), s)

    # ---------- 2б. GDD v1.12.1: пепельный след Огнеи 6% макс. HP/с (было 8%); прочие поля следа, clearR и след Кривши (8%) — без изменений
    s = await G('''(() => { const C = __game.dbg.CFG, A = C.bosses.mara.ashTrail, K = C.bosses.krivsha; const kt = K.fireTrail || K.trail || {};
        return { a: A, k: kt.pctMaxHpPerSec, clearR: C.zones.zalesye.landmarks.maraDen.clearR, gdd: C.bosses.mara._gdd }; })()''')
    check('m1h GDD v1.12.1: mara.ashTrail 6% макс. HP/с (burn 3, r 0,6, every 0,4, tick 0,5 — прежние), clearR 8,9, след Кривши 8%; _gdd Огнеи — 6%, без модификаторов, свита 3–4 mlvl 1',
          s['a'] == {'burn': 3, 'pctMaxHpPerSec': 6, 'r': 0.6, 'every': 0.4, 'tick': 0.5} and s['k'] == 8 and s['clearR'] == 8.9
          and '6% макс. HP' in s['gdd'] and '3–4 анчутки mlvl 1' in s['gdd'] and 'без модификаторов' in s['gdd'], s)

    # ---------- 3. строки, вынесенные из кода в ru.json (текст прежний)
    s = await G('''(async () => { const g = __game, { t } = await import('/src/core/i18n.js'); g.ui.closeAll();
        g.notice = null; g.noticeQ = []; const h = g.hero; h.yar = h.maxYar; const k = h.belt.findIndex(b => b && b.kind.startsWith('yar'));
        const n0 = g.notice; h.drink(k, g); const full = g.notice && g.notice.text; g.notice = null; g.noticeQ = [];
        const empty = h.belt.findIndex(b => !b); if (empty >= 0) h.drink(empty, g); const emp = g.notice && g.notice.text; g.notice = null; g.noticeQ = [];
        const was = g.labelsAlways; g.toggleLabels(); const l1 = g.notice && g.notice.text; g.notice = null; g.noticeQ = []; g.toggleLabels(); const l2 = g.notice && g.notice.text;
        g.notice = null; g.noticeQ = []; g.log.lines.length = 0; g.ui.closeAll(); g.enterZone('zalesye', 'krada'); const zl = g.log.lines.map(l => l.text || l[0] || l).join('|');
        const Z = g.zone; return { full, emp, empty, l: [l1, l2].sort(), zl, want: Z.name + ' · ур. нечисти ' + (Z.mlvl || []).join('–'), labelsBack: g.labelsAlways === was }; })()''')
    check('m1h строки из кода → ru.json: «Удаль и так полна», «Ячейка N пуста», «Подписи добычи: всегда / по Alt», «Залесье · ур. нечисти 1–2» (текст прежний)',
          s['full'] == 'Удаль и так полна' and (s['empty'] < 0 or s['emp'] == 'Ячейка %d пуста' % (s['empty'] + 1))
          and s['l'] == ['Подписи добычи: всегда', 'Подписи добычи: по Alt'] and s['labelsBack'] and s['want'] in s['zl'].split('|'), s)

    # ---------- 4. длины: шар, окно «Витязь», плашка/уведомление награды, плашка Огнеи, полоса цели, тултипы, лавка Милуши
    s = await G('''(async () => { const g = __game, F = await import('/src/core/font.js'), { t, tObj, RU } = await import('/src/core/i18n.js'), I = await import('/src/data/items.js');
        const { UI_ATLAS } = await import('/src/data/ui_atlas.js'), tw = (x) => F.textWidth(x), CH = UI_ATLAS.character_layout;
        const np = t('proto.nameplate', { name: RU['codex.mara']['Имя'], level: t('ui.hud.level', { level: 4 }) });
        const longest = I.makeItem('staff_3', 'magic', 6, Math.random, { affixes: [['P07', 3]] });
        return {
          orb: [tw(t('ui.hud.yar')), tw('Жизнь'), 2 * 27 - 8],
          chr: [tw(tObj('skill.yar1').name) + tw('999 / 999') + 8 + 4, CH.colw],
          cmp: tw(t('ui.hud.yar') + ': +15'),
          reward: [tw(t('item.u2.name')) + 8, tw(t('proto.bylina.got', { item: t('item.u2.name') })), tw('Былинная вещь: Громовник')],
          nameplate: [np, tw(np), 140, tw('Мара Пепельная · ур. 4')],
          idol: [tw(t('ui.obj.idol')) + 8, tw('Чур-идол: руби') + 8],
          cost: [tw(t('ui.skills.cost', { n: 12 }) + ' · ' + t('ui.skills.cd', { n: 4 })), 300],
          vedana: [tw(t('npc.vedana')), tw(t('ui.trade.vedana')), 300 - 30],
          shop: [tw('Крепкое зелье Удали') + 8 + tw('999'), 300 - 16],
          longName: [longest.name, longest.name.length, tw(longest.name), 36],
          tier: tw(t('ui.hero.yar_tier')), tut: tw(t('ui.tut.chur')), obj: tw(t('ui.obj.chur_awake')) + 8 }; })()''')
    # уведомление о награде — как его на самом деле переносит HUD (maxW зависит от камеры и открытых окон): в одну строку и с котомкой, и без
    nb = []
    for inv in (False, True):
        await G('''(async () => { const g = __game, { t } = await import('/src/core/i18n.js'); g.ui.closeAll(); if (%s) g.ui.toggleInv(true);
            g.notice = null; g.noticeQ = []; g._noticeBox = null; g.notify(t('proto.bylina.got', { item: t('item.u2.name') }), '#fff', 'relic'); })()''' % ('true' if inv else 'false'))
        await wait(120)
        nb.append(await G('(() => { const b = __game._noticeBox; __game.ui.closeAll(); __game.notice = null; return b && [b.lines, b.w, b.x]; })()'))
    s['rewardNotice'] = nb
    # длинная одиночная строка (напр. ui.tut.chad «Чад душит Удаль…», 253 px) не наезжает на трекер задания (x ≤ 210, y ≤ 84)
    tb = []
    for key in ('ui.tut.chad', 'ui.error.no_yar'):
        await G('''(async () => { const g = __game, { t } = await import('/src/core/i18n.js'); g.ui.closeAll(); g.notice = null; g.noticeQ = []; g._noticeBox = null; g.notify(t('%s'), '#fff', 'm1h'); })()''' % key)
        await wait(120)
        tb.append(await G('(() => { const b = __game._noticeBox; __game.notice = null; return b && { y: b.y, l: b.x - b.w / 2, lines: b.lines }; })()'))
    s['trackerNotice'] = tb
    json.dump(s, open(LEN_OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok_len = (s['orb'][0] <= s['orb'][2] and s['orb'][0] <= s['orb'][1] + 2 and s['chr'][0] <= s['chr'][1] and all(b and b[0] == 1 for b in s['rewardNotice']) and all(b and (b['y'] >= 86 or b['l'] > 212) for b in s['trackerNotice']) and s['trackerNotice'][1]['y'] == 64
              and s['nameplate'][1] <= s['nameplate'][2] and s['cost'][0] <= s['cost'][1] and max(s['vedana'][:2]) <= s['vedana'][2]
              and s['shop'][0] <= s['shop'][1] and s['longName'][1] <= s['longName'][3])
    check('m1h длины (px шрифта игры): «Удаль» в шаре ≤ 46 и не шире «Жизнь»; «Удаль I 999 / 999» в поле «Витязя»; «Былинная вещь: Громовой знак» в одну строку (с котомкой и без); '
          '«Огнея Пепельная · ур. 4» в полосе цели 140; «Удаль: N · перезарядка» в тултипе; «Изба Милуши» в окне 300; одиночное уведомление не наезжает на трекер; самое длинное имя с «Жгучий» ≤ 36 симв.',
          ok_len, s)

    # ---------- 5. рендер: HUD с шаром «Удаль» (скриншот), окно «Витязь», тултип «Громового знака» и зелья — в пределах экрана
    await G('''(() => { const g = __game, h = g.hero; g.ui.closeAll(); g.enterZone('zalesye', 'krada'); for (const e of g.enemies) e.stagger = 1e9;
        h.yarTier = 1; h.recalc(); h.yar = Math.round(h.maxYar * 0.7); h.hp = Math.round(h.maxHp * 0.85); g.notice = null; g.noticeQ = []; g.letter = null; g.log.lines.length = 0; g.time += 20; })()''')
    await pg.mouse.move(960, 200); await wait(300)
    await pg.screenshot(path=SHOT_HUD)
    s = await G('''(() => { const g = __game; g.ui.toggleChar && g.ui.toggleChar(true); return { open: g.ui.anyOpen }; })()''')
    await wait(150)
    await pg.screenshot(path='/tmp/m1h_char.png')          # для глаза (окно «Витязь»: «Удаль I»), в отчёт не идёт
    s2 = await G('''(async () => { const g = __game, I = await import('/src/data/items.js'), h = g.hero; g.ui.closeAll(); g.ui.toggleInv(true);
        h.inv.items.filter(i => i.unique === 'U2').forEach(i => h.inv.remove ? h.inv.remove(i) : null);
        const it = I.makeUnique('U2'); const ok = h.inv.autoAdd(it); const e = h.inv.entries.find(x => x.item === it);
        return { ok, c: e && e.c, r: e && e.r, w: it.w, h: it.h, L: (await import('/src/data/ui_atlas.js')).UI_ATLAS.inventory_layout }; })()''')
    L = s2['L']
    cx, cy = L['gx'] + (s2['c'] + s2['w'] / 2) * L['cell'], L['gy'] + (s2['r'] + s2['h'] / 2) * L['cell']
    await pg.mouse.move(*(await client_scr(cx, cy))); await wait(250)
    await pg.screenshot(path=SHOT_REWARD)
    tip = await G('(() => { const T = __game.ui.lastTip; return T && { name: T.item.name, box: [T.x, T.y, T.w, T.h] }; })()')
    check('m1h скриншоты: ' + os.path.basename(SHOT_HUD) + ' (шар «Удаль»), ' + os.path.basename(SHOT_REWARD) + ' (тултип «Громовой знак» в котомке) — тултип целиком на экране 640×360',
          s['open'] and s2['ok'] and tip and tip['name'] == 'Громовой знак' and tip['box'][0] >= 0 and tip['box'][1] >= 0
          and tip['box'][0] + tip['box'][2] <= 640 and tip['box'][1] + tip['box'][3] <= 360
          and os.path.getsize(SHOT_HUD) > 50000 and os.path.getsize(SHOT_REWARD) > 50000, tip)
    await G('__game.ui.closeAll()')

    # ---------- 6. «сохранение» до переименования: флаг m1.gromovnik и ключи хранилища (sessionStorage byl_m1_gromovnik, localStorage byl_nebyl_labels)
    await G('''(() => { sessionStorage.setItem('byl_keep_gromovnik', '1'); sessionStorage.setItem('byl_m1_gromovnik', 'pending'); localStorage.setItem('byl_nebyl_labels', '1'); })()''')
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')
    s = await G('''(() => { const g = __game; g.ui.closeAll(); delete g.zoneStates.kapishche; g.enterZone('kapishche', 'start');
        const o = g.map.objects.find(x => x.id === 'gromovnik'); const label = o && g.objectLabel(o); const la = g.labelsAlways;
        if (o) { g.hero.x = o.x; g.hero.y = o.y + 0.5; g.interact ? g.interact(o) : g.useObject(o); }
        return { placed: !!o, label, la, flag: g.quest.flag('m1.gromovnik'), ss: sessionStorage.getItem('byl_m1_gromovnik'),
          got: g.hero.inv.items.filter(i => i.unique === 'U2').map(i => i.name) }; })()''')
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')
    s2 = await G('''(() => { const g = __game; g.ui.closeAll(); delete g.zoneStates.kapishche; g.enterZone('kapishche', 'start'); g.placeGromovnik(g.map);
        const r = { again: g.map.objects.some(x => x.id === 'gromovnik'), ss: sessionStorage.getItem('byl_m1_gromovnik') };
        sessionStorage.removeItem('byl_keep_gromovnik'); sessionStorage.removeItem('byl_m1_gromovnik'); localStorage.removeItem('byl_nebyl_labels'); return r; })()''')
    check('m1h сохранение до переименования: byl_m1_gromovnik «pending» → награда у идола с подписью «Громовой знак», подобрана — флаг m1.gromovnik, «taken»; '
          'после перезагрузки «taken» — второй раз не кладётся; byl_nebyl_labels «1» действует',
          s['placed'] and s['label'] == 'Громовой знак' and s['la'] and s['flag'] and s['ss'] == 'taken' and s['got'] == ['Громовой знак']
          and not s2['again'] and s2['ss'] == 'taken', [s, s2])
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')

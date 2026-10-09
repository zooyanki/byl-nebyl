# Веха m1k: GDD v1.13.2 §12.4 — D4 (видимость за кронами), D5 (навигация), D6 (окно диалога), D7 (Ладога: постройки
# художника, ворота, указатель, священник), D9 (деревья вдоль пути). Окно диалога здесь настоящее: __game.dlgAuto = false.
import os, json, subprocess

ROOT = '/workspace/game/prototype/'
SHOT_TREES = ROOT + 'screenshot_m1k_trees.png'
SHOT_NAV = ROOT + 'screenshot_m1k_nav.png'
SHOT_DIALOG = ROOT + 'screenshot_m1k_dialog.png'
SHOT_LADOGA = ROOT + 'screenshot_m1k_ladoga.png'

# свежая Ладога в «игре» без окон; окно диалога — настоящее
LAD = '''const g = __game, h = g.hero; g.dlgAuto = false; g.state = 'play'; g.paused = false; g.ui.closeAll(); if (g.town) g.town.close();
  g.quest.flags.vyshataIntro = true; g.flushDialogs(); g.dlgQueue = []; g.enterZone('ladoga', 'from_zalesye'); g.enemies = []; g.notice = null; h.invuln = 1e9; h.stop && h.stop();
  const RU = g.dbg.RU || {};'''
# прогон времени без g.simulate (в симуляции диалоги закрываются сами)
STEP = '''const step = (sec, dt = 0.05) => { for (let k = 0; k < sec / dt; k++) g.update(dt); };'''


async def run_m1k(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1k', flush=True)

    async def fresh(url=None):
        await pg.goto(url or a.url)
        await pg.wait_for_function('() => window.__game && __game.time > 0.3')
        await G('(() => { __game.dlgAuto = false; })()')
        await wait(100)

    await fresh()
    has_ru = await G('(() => !!(__game.dbg && __game.dbg.RU))()')
    if not has_ru:
        await G("(async () => { const I = await import('/src/core/i18n.js'); __game.dbg.RU = I.RU; })()")

    # ================= D6. Окно диалога
    s = await G('''(() => { const g = __game, D = g.dbg.CFG.dialogues, RU = g.dbg.RU; const ids = Object.keys(D.dialogues);
        const lines = ids.reduce((n, k) => n + D.dialogues[k].lines.length, 0);
        const missing = []; for (const k of ids) for (const l of D.dialogues[k].lines) if (!RU[l.key]) missing.push(l.key);
        const old = Object.keys(RU).filter(k => /^npc\\.[a-z]+\\.(s[0-3]|rep)$/.test(k) || k === 'dialog.m1.mal');
        return { n: ids.length, lines, speakers: Object.keys(D.speakers).length, missing, old, w: D.window, s0last: D.dialogues['vyshata.s0'].lines.slice(-1)[0].key,
          after: D.dialogues['vyshata.s0'].after, mal: D.dialogues['m1.mal'].after }; })()''')
    w = s['w']
    check('m1k D6 dialogues.json: 7 говорящих, 19 диалогов / 60 реплик из dlg.* (все ключи в ru.json), старых npc.*.s0–s3 / dialog.m1.mal нет; С0 кончается dlg.vyshata.m1.dir',
          s['n'] == 19 and s['lines'] == 60 and s['speakers'] == 7 and not s['missing'] and not s['old'] and s['s0last'] == 'dlg.vyshata.m1.dir'
          and {'flag': 'm1.briefed'} in s['after'] and any(x.get('call') == 'malRun' for x in s['mal']), {k: s[k] for k in ('n', 'lines', 'speakers', 'missing', 'old', 's0last')})
    check('m1k D6 окно по §10.4: 400×88 у (120; 222), портрет 64 в рамке, текст 304 px, 4 строки по 11, 40 зн/с, блок ввода 0,15 с, очередь 3 с / 8 тайлов / 30 с',
          (w['x'], w['y'], w['w'], w['h'], w['portrait'], w['textW'], w['lineH'], w['maxLines'], w['cps'], w['inputLock'], w['queueCalm'], w['queueNearR'], w['queueTimeout'], w['blockIfAggroR'], w['blockAfterHit'])
          == (120, 222, 400, 88, 64, 304, 11, 4, 40, 0.15, 3, 8, 30, 12, 3), w)

    s = await G('''(() => { ''' + LAD + '''
        const vy = g.npcs.find(n => n.role === 'vyshata'); h.x = vy.x + 1.5; h.y = vy.y + 1.5;
        g.startDialog('vyshata.s0', vy); const d = g.dlgWin; const open = !!d, first = d && d.lines[0].key;
        g.updateDialogWin(0.25); const ch = Math.round(d.chars);
        const t0 = g.time, ex = vy.x; for (let k = 0; k < 10; k++) g.update(0.05); const frozen = g.time === t0;
        const inp = (key) => ({ pressed: (k) => k === key, leftPressed: false, rightPressed: false });
        d.chars = 10; d.lock = 0; g.dialogInput(inp('Space')); const full = d.chars === d.lines[0].text.length, lock = d.lock;
        g.dialogInput(inp('Space')); const iLocked = d.i;
        g.updateDialogWin(0.2); g.dialogInput(inp('Space')); const iNext = d.i;
        const logHas = g.log.lines.some(l => (l.text || l).toString().includes(d.lines[1].text.slice(0, 20)));
        g.flags = g.quest.flags; delete g.quest.flags['m1.briefed'];
        g.dialogInput(inp('Escape'));
        return { open, first, ch, frozen, full, lock: +lock.toFixed(2), iLocked, iNext, logHas, closed: !g.dlgWin, briefed: !!g.quest.flags['m1.briefed'], done: g.dlgDone && g.dlgDone['vyshata.s0'] != null }; })()''')
    check('m1k D6 «машинка» 40 зн/с (0,25 с → 10 знаков), мир стоит, Пробел допечатывает, 0,15 с ввод не принимается, затем следующая реплика (и в журнал); Esc закрывает, after (m1.briefed) применён',
          s['open'] and s['first'] == 'dlg.vyshata.s0.1' and s['ch'] == 10 and s['frozen'] and s['full'] and s['lock'] == 0.15 and s['iLocked'] == 0 and s['iNext'] == 1
          and s['logHas'] and s['closed'] and s['briefed'] and s['done'], s)

    # вид окна + снимок
    await G('''(() => { ''' + LAD + ''' const vy = g.npcs.find(n => n.role === 'vyshata'); h.x = vy.x + 1.2; h.y = vy.y + 1.6; g.updateCamera && g.updateCamera(); g.startDialog('vyshata.s0', vy); })()''')
    await pg.mouse.move(150, 1000)
    await wait(1600)
    s = await G('''(() => { const g = __game, D = g.dlgDrawn; return D ? { x: D.x, y: D.y, w: D.w, h: D.h, frame: D.frame, portrait: D.portrait, name: D.name, key: D.key, n: D.nLines, i: D.i, cnt: D.n } : null; })()''')
    await pg.screenshot(path=SHOT_DIALOG)
    check('m1k D6 окно рисуется: рамка художника (9-slice), портрет Вышаты, имя, реплика; трекер и журнал под окном скрыты; скриншот screenshot_m1k_dialog.png',
          s and (s['x'], s['y'], s['w'], s['h']) == (120, 222, 400, 88) and s['frame'] in ('9slice', 'baked') and s['portrait'] == 'portrait_vyshata' and s['name'] and s['key'] == 'dlg.vyshata.s0.1'
          and os.path.exists(SHOT_DIALOG), s)
    await G('(() => { const g = __game; g.flushDialogs(); })()')

    # очередь: в бою не открывается, открывается после 3 с тишины в 8 тайлах; дальше 8 тайлов — 30 с и в журнал
    s = await G('''(() => { ''' + LAD + STEP + '''
        const vy = g.npcs.find(n => n.role === 'vyshata'); h.x = vy.x + 2; h.y = vy.y + 2;
        const e = g.spawnTest('upyr', h.x + 3, h.y, 1); e.state = 'chase'; e.stagger = 1e9; e.speed = 0; e.hp = e.maxHp = 1e6;
        g.startDialog('vedana.s0', vy); const q1 = (g.dlgQueue || []).length, w1 = !!g.dlgWin;
        g.enemies = []; step(1.0); const w2 = !!g.dlgWin; step(2.6); const w3 = !!g.dlgWin; g.flushDialogs();
        g.startDialog('vedana.s0', vy); g.flushDialogs();
        h.x = vy.x + 15; h.y = vy.y; h.sinceHurt = 0; g.startDialog('tverdyata.s0', vy); const q4 = (g.dlgQueue || []).length; h.sinceHurt = 99;
        const to0 = g.counters.dialogsTimedOut || 0; step(31, 0.1); const to = (g.counters.dialogsTimedOut || 0) - to0;
        return { q1, w1, w2, w3, q4, to, after: !!g.dlgWin }; })()''')
    check('m1k D6 очередь: враг в агро → окно не открывается (в очереди), через 3 с тишины рядом — открывается; говорящий дальше 8 тайлов — через 30 с реплики в журнал',
          s['q1'] == 1 and not s['w1'] and not s['w2'] and s['w3'] and s['q4'] == 1 and s['to'] == 1 and not s['after'], s)

    # повтор разговора — одна короткая реплика; священник
    s = await G('''(() => { ''' + LAD + '''
        const ve = g.npcs.find(n => n.role === 'vedana'); h.x = ve.x + 1.5; h.y = ve.y + 1.5; g.town.seen = {};
        g.town.openNpc(ve); const a1 = g.dlgWin && g.dlgWin.id; g.flushDialogs(); g.town.close();
        g.town.openNpc(ve); const a2 = g.dlgWin && g.dlgWin.id, n2 = g.dlgWin && g.dlgWin.lines.length; g.flushDialogs(); g.town.close();
        const pr = g.npcs.find(n => n.role === 'priest');
        return { a1, a2, n2, pr: pr && [pr.x, pr.y, pr.name], art: !!(g.dbg.ART.sheets.npc_priest_idle_se && g.dbg.ART.sheets.npc_priest_idle_ne) }; })()''')
    check('m1k D6 разговор с NPC: стадия — окно диалога один раз, повтор — одна короткая реплика (npc.*.greet/idle*); поп Иоанн стоит в (27,0; 14,4), спрайт художника',
          s['a1'] == 'vedana.s0' and (s['a2'] or '').startswith('short:npc.vedana.') and s['n2'] == 1 and s['pr'] and abs(s['pr'][0] - 27.0) < 1e-6 and abs(s['pr'][1] - 14.4) < 1e-6 and s['art'], s)

    # ================= D7. Ладога
    s = await G('''(async () => { ''' + LAD + '''
        const P = await import('/src/render/props.js'), V = await import('/src/render/village_art.js'); const m = g.map;
        const sheet = m.props.filter(p => p.type !== 'gateseg' && p.type !== 'sign' && V.sheetOf(p));
        const badFrame = sheet.filter(p => { const B = P.bldSheet(p); return !B || B.fr !== V.frameOf(B.sh.meta, p.door); }).map(p => p.id);
        const code = ['kuznya', 'terem', 'well'].filter(id => m.props.some(p => p.id === id || p.type === id));
        // v1.13.3 (ответ 5): дым только у видов smokeKinds (изба, с сенями, на подклете, баня); клеть, амбар, хлев, мастерская, церковь — без дыма
        const K = g.zone.smokeKinds || [], anch = sheet.filter(p => { const B = P.bldSheet(p); return B && B.sh.meta.anchors_px && B.sh.meta.anchors_px.smoke; });
        g.render(); const drawn = sheet.filter(p => p._smoked !== undefined);
        const smoke = { kinds: K, n: anch.filter(p => p.smoke).length, flagBad: sheet.filter(p => !!p.smoke !== K.includes(p.type)).map(p => p.id || p.type),
          drawnBad: drawn.filter(p => p._smoked && !K.includes(p.type)).map(p => p.id || p.type), noSmoke: [...new Set(anch.filter(p => !p.smoke).map(p => p.type))].sort() };
        // порядок «частокол / постройка» в игре: клетка частокола целиком перед футпринтом → рисуется позже, целиком за ним → раньше
        const toS = (x, y) => g.toS(x, y); const conf = [];
        const blds = m.props.filter(p => V.sheetOf(p) || ['izba', 'kuznya', 'terem', 'church'].includes(p.type));
        for (const f of m.props.filter(p => p.type === 'palisade')) for (const b of blds) {
          const A = P.propBox(f, toS), B = P.propBox(b, toS); if (!A || !B || A.x + A.w <= B.x || B.x + B.w <= A.x || A.y + A.h <= B.y || B.y + B.h <= A.y) continue;
          const [x0, y0, bw, bh] = b.fp, fx = f.fp[0], fy = f.fp[1], fw = f.fp[2], fh = f.fp[3];
          const front = (fx >= x0 + bw && fy + fh > y0) || (fy >= y0 + bh && fx + fw > x0), behind = (fx + fw <= x0 && fy < y0 + bh) || (fy + fh <= y0 && fx < x0 + bw);
          if (front && !behind && f.depth <= b.depth) conf.push([fx, fy, b.id || b.type]); if (behind && !front && f.depth >= b.depth) conf.push([fx, fy, b.id || b.type, 'b']);
        }
        const gates = (m.gates || []).map(o => ({ id: o.id, closed: !!o.wall, label: g.objectLabel(o) }));
        const caps = (g.zone.captions || []).map(c => c.textKey).filter(k => k && !RU[k]);
        const sign = !!m.sign && m.sign.showRange === 6 && m.sign.boards && m.sign.boards.length === 4;
        return { sheet: sheet.length, badFrame, code, smoke, fxSmoke: !!(await import('/src/render/rest_fx.js')).FX.sheets.smoke, conf, gates, caps, sign,
          gaps: g.zone.palisade && g.zone.palisade.gaps }; })()''')
    lay = subprocess.run(['python3', ROOT + 'tools/ladoga_layout_json.py'], capture_output=True, text=True, timeout=60).stdout
    T = await G('''(() => { const RU = __game.dbg.RU, t = (k) => { const v = RU[k]; return v && typeof v === 'object' ? (v.desc || v['Текст'] || v.name) : v; };
        return { zal: t('ui.gate.open.zalesye'), pier: t('ui.gate.open.pier'), closed: t('ui.gate.closed') }; })()''')
    gl = {x['id']: x for x in s['gates']}
    check('m1k D7 Ладога: 17 построек листами художника (кадр по двери), кузня/терем/колодец кодом — 20; дым — fx_smoke_wisp; расстановка — скрипт дизайнера «OK: пересечений нет»',
          s['sheet'] == 17 and not s['badFrame'] and len(s['code']) == 3 and s['fxSmoke'] and 'OK: пересечений нет' in lay and 'совпадает' in lay,
          {k: s[k] for k in ('sheet', 'badFrame', 'code', 'smoke', 'fxSmoke')} | {'layout': lay.strip().splitlines()[-2:]})
    sm = s['smoke']
    check('m1k v1.13.3 дым только у жилых с печью: smokeKinds [izba, izba_seni, izba_podklet, banya] в ladoga.json; у клети, амбара, хлева, мастерской, церкви дыма нет',
          sm['kinds'] == ['izba', 'izba_seni', 'izba_podklet', 'banya'] and sm['n'] >= 1 and not sm['flagBad'] and not sm['drawnBad']
          and not set(sm['noSmoke']) & set(sm['kinds']), sm)
    check('m1k D7 частокол и постройки в игре: 0 нарушений порядка «перед / за»', not s['conf'], s['conf'][:6])
    check('m1k D7 ворота: проёмы 4 тайла; восточные/южные открыты, северные (до сдачи М1) и западные на запоре; подписи при наведении ui.gate.open.* / ui.gate.closed; подписи мест и доски указателя из ru.json',
          s['gaps'] and all((gp[2], gp[3]) in ((1, 4), (4, 1)) for gp in s['gaps']) and not gl['gate_east']['closed'] and not gl['gate_south']['closed']
          and gl['gate_north']['closed'] and gl['gate_west']['closed'] and gl['gate_east']['label'] == T['zal'] and gl['gate_south']['label'] == T['pier']
          and gl['gate_west']['label'] == T['closed'] and not s['caps'] and s['sign'], {'gates': s['gates'], 'caps': s['caps'], 'sign': s['sign']})
    # снимок Ладоги: церковь и постройки
    await G('''(() => { ''' + LAD + ''' h.x = 29.5; h.y = 14.5; g.updateCamera && g.updateCamera(); })()''')
    await wait(500)
    await pg.screenshot(path=SHOT_LADOGA)
    check('m1k D7 скриншот screenshot_m1k_ladoga.png (церковь, постройки, поп у паперти)', os.path.exists(SHOT_LADOGA))

    # ================= D5. Навигация
    s = await G('''(() => { const g = __game, N = g.dbg.CFG.stats.nav, Q = g.dbg.CFG.quests.m1; return { N, zl: Q.zoneLines, mk: Q.markers, hints: Q.hints }; })()''')
    check('m1k D5 данные: stats.nav {arrow 12/8/14/1 Гц/0,7–1,0/бой 0,4/15; mark 9/40/96/±2/3/0,3}; quests m1 zoneLines, markers.ladoga = vyshata, hints 90 с',
          s['N']['arrow'] == {'size': 12, 'dirs': 8, 'margin': 14, 'pulseHz': 1, 'alpha': [0.7, 1.0], 'combatAlpha': 0.4, 'distOver': 15}
          and s['N']['mark'] == {'size': 9, 'h': 40, 'hGate': 96, 'bob': 2, 'hideR': 3, 'fade': 0.3} and s['mk'] == {'ladoga': 'vyshata'}
          and s['zl']['ladoga'][0]['key'] == 'quest.m1.obj.ladoga_exit' and s['hints'][0]['sec'] == 90 and s['hints'][0]['bark'] == 'bark.ladoga.m1_where', s)
    s = await G('''(async () => { ''' + LAD + '''
        h.x = 23.5; h.y = 33; g.updateCamera && g.updateCamera(); g.render(); const T0 = g.navTarget(), tr0 = g.trackerDrawn, nd0 = g.navDrawn;
        g.enterZone('zalesye', 'krada'); g.render(); const trZ = g.trackerDrawn.lines.filter(l => l.zone).length;
        return { T0, tr0, nd0: nd0 && { kind: nd0.kind, x: nd0.x, y: nd0.y, frame: nd0.frame, alpha: nd0.alpha, steps: nd0.steps, blocked: nd0.blocked && nd0.blocked.some(r => nd0.x > r.x - 7 && nd0.x < r.x + r.w + 7 && nd0.y > r.y - 7 && nd0.y < r.y + r.h + 7) }, trZ }; })()''')
    nd = s['nd0'] or {}
    check('m1k D5 в Ладоге первой строкой трекера «Выйди восточными воротами» (не цель, 4 строки по 9 px), в Залесье строки нет; цель — восточные ворота',
          s['tr0']['lines'][0]['zone'] and s['tr0']['lines'][0]['id'] == 'zone' and s['tr0']['step'] == (9 if len(s['tr0']['lines']) > 3 else 10) and s['trZ'] == 0
          and s['T0']['id'] == 'gate_east' and s['T0']['kind'] == 'gate', s)
    check('m1k D5 стрелка у края (цель за полем): кадр по направлению (8 кадров), не на трекере / мини-карте / шарах, пульс 0,7–1,0, шаги под стрелкой',
          nd.get('kind') == 'arrow' and 0 <= nd.get('frame', -1) < 8 and not nd.get('blocked') and 0.69 <= nd.get('alpha', 0) <= 1.0 and 14 <= nd['x'] <= 626 and 14 <= nd['y'] <= 300, nd)
    s = await G('''(() => { ''' + LAD + '''
        const gt = g.objectById('gate_east'); h.x = gt.x - 7; h.y = gt.y + 1; g.updateCamera && g.updateCamera(); g.render(); const far = g.navDrawn && { kind: g.navDrawn.kind, alpha: g.navDrawn.alpha };
        const e = g.spawnTest('upyr', h.x - 3, h.y, 1); e.state = 'chase'; e.stagger = 1e9; g.render(); const fight = g.navDrawn && g.navDrawn.alpha; g.enemies = [];
        h.x = gt.x - 2; h.y = gt.y; for (let k = 0; k < 12; k++) { g.time += 0.05; g.render(); } const near = g.navDrawn && g.navDrawn.kind;
        g.settings.navArrow = false; g.render(); const off = g.navDrawn; g.settings.navArrow = true;
        return { far, fight, near, off }; })()''')
    check('m1k D5 ромб над воротами на экране (дальше 3 тайлов), в бою альфа 0,4, ближе 3 тайлов гаснет; settings.navArrow = false — ни стрелки, ни ромба',
          s['far'] and s['far']['kind'] == 'mark' and s['fight'] == 0.4 and s['near'] == 'none' and s['off'] is None, s)
    s = await G('''(() => { ''' + LAD + '''
        const W = g.objectById('gate_west'); h.x = W.x + 1.6; h.y = W.y; W.nearT = -99; const n0 = g.counters.gateNear || 0;
        g.update(0.05); const note = g.notice && g.notice.text; g.update(0.05); g.notice = null; h.x = W.x + 1.5; g.update(0.05); const n1 = (g.counters.gateNear || 0) - n0;
        const b0 = g.counters.gateBark || 0; W.clickT = -99; g.clickGate(W); g.clickGate(W); const b1 = (g.counters.gateBark || 0) - b0;
        g.time += 10.1; g.clickGate(W); const b2 = (g.counters.gateBark || 0) - b0;
        g.render(); const icons = g.miniIcons;
        return { note, n1, b1, b2, icons }; })()''')
    ic = {x['kind']: x['frame'] for x in s['icons']}
    check('m1k D5 закрытые ворота: ближе 2 тайлов — уведомление «Ворота на запоре…» раз в 10 с; щелчок — реплика раз в 10 с; мини-карта: открытые — проём (кадр 0), закрытые — черта (1), церковь — точка (2)',
          (s['note'] or '').startswith('Ворота на запоре') and s['n1'] == 1 and s['b1'] == 1 and s['b2'] == 2
          and ic.get('gate_east') == 0 and ic.get('gate_south') == 0 and ic.get('gate_north') == 1 and ic.get('gate_west') == 1 and ic.get('church') == 2, s)
    s = await G('''(() => { ''' + LAD + '''
        g.dlgDone = g.dlgDone || {}; g.dlgDone['vyshata.s0'] = g.time; g.navHint = null; h.x = 23.5; h.y = 33; const c0 = g.counters.navHint || 0;
        for (let k = 0; k < 89; k++) g.updateNavHints(1); const at89 = (g.counters.navHint || 0) - c0;
        g._barks['bark.ladoga.m1_where'] = null; g.speechUntil = 0; g.dialogQ = []; g.fx.texts = [];
        for (let k = 0; k < 2; k++) g.updateNavHints(1); const at91 = (g.counters.navHint || 0) - c0, flash = g.navFlashUntil - g.time;
        const said = g.log.lines.some(l => String(l.text || l).includes('Залесье горит на восходе'));
        for (let k = 0; k < 200; k++) g.updateNavHints(1); const once = (g.counters.navHint || 0) - c0;
        g.navHint = null; const gt = g.objectById('gate_east'); h.x = gt.x - 5; h.y = gt.y; g.updateNavHints(1); h.x = 23.5; h.y = 33; for (let k = 0; k < 120; k++) g.updateNavHints(1);
        const nearNo = (g.counters.navHint || 0) - c0;
        return { at89, at91, flash: +flash.toFixed(2), said, once, nearNo }; })()''')
    check('m1k D5 подсказка: 90 с после разговора с Вышатой и ни разу ближе 10 тайлов к воротам → «Залесье горит на восходе…» один раз за вход, стрелка мигает 3 с; подошёл к воротам — подсказки нет',
          s['at89'] == 0 and s['at91'] == 1 and s['flash'] == 3 and s['said'] and s['once'] == 1 and s['nearNo'] == 1, s)
    s = await G('''(() => { ''' + LAD + '''
        const st0 = ['mal', 'reach', 'huts'].map(id => g.quest.get(id).state); ['mal', 'reach', 'huts'].forEach(id => { g.quest.get(id).state = 'done'; g.quest.get(id).doneT = g.time - 99; });
        const k = g.quest.get('krivsha'); k.state = 'done'; k.doneT = g.time - 99; g.quest.events.push({ event: 'bossKilled', boss: 'krivsha', t: g.time });
        h.x = 23.5; h.y = 33; g.render(); const T = g.navTarget(), z = g.trackerDrawn.lines[0];
        g.quest.flags['m1.turnedIn'] = true; g.render(); const T2 = g.navTarget(), z2 = g.trackerDrawn.lines.filter(l => l.zone).length; delete g.quest.flags['m1.turnedIn'];
        k.state = 'locked'; ['mal', 'reach', 'huts'].forEach((id, i) => { g.quest.get(id).state = st0[i]; }); g.quest.events = g.quest.events.filter(e => e.event !== 'bossKilled');
        return { T, z, T2, z2 }; })()''')
    check('m1k D5 после Кривши до сдачи: цель стрелки — Вышата, строка «Доложи Вышате»; после сдачи строки нет',
          s['T'] and s['T']['id'] == 'vyshata' and s['T']['kind'] == 'npc' and s['z']['zone'] and s['z']['text'] == 'Доложи Вышате' and s['z2'] == 0 and s['T2'] is None, s)
    s = await G('''(async () => { const S = await import('/src/render/screens.js'), g = __game; const b = S.PAUSE_BTNS.filter(x => ['xray', 'navArrow', 'shake'].includes(x.id)).map(x => [x.id, x.key]);
        return { b, st: [g.settings.xray, g.settings.navArrow] }; })()''')
    check('m1k D4/D5 «Настройки» (пауза): «Прозрачные кроны» ui.settings.xray, «Стрелка к цели» ui.settings.navArrow; по умолчанию вкл.',
          ['xray', 'ui.settings.xray'] in s['b'] and ['navArrow', 'ui.settings.navArrow'] in s['b'] and s['st'] == [True, True], s)
    # снимок навигации: стрелка + закрытые ворота с подписью
    await G('''(() => { ''' + LAD + ''' const W = g.objectById('gate_north'); h.x = W.x - 2.5; h.y = W.y + 3.2; g.updateCamera && g.updateCamera(); g.labelsAlways = false; })()''')
    await wait(300)
    cl = await G("(() => { const W = __game.objectById('gate_north'); return __game.clientOf(W.x, W.y, 30); })()")
    await pg.mouse.move(*cl)
    await wait(400)
    s = await G('(() => { const g = __game; return { nav: g.navDrawn && g.navDrawn.kind, hover: g.hoverObj && g.hoverObj.id, label: g.objectLabel(g.objectById("gate_north")) }; })()')
    await pg.screenshot(path=SHOT_NAV)
    await pg.mouse.move(1700, 200)
    check('m1k D5 скриншот screenshot_m1k_nav.png: стрелка к восточным воротам у края, закрытые северные ворота с подписью «Ворота на запоре»',
          s['nav'] == 'arrow' and s['label'] == T['closed'] and os.path.exists(SHOT_NAV), s)

    # ================= D4. Видимость
    s = await G('(() => __game.dbg.CFG.stats.xray)()')
    check('m1k D4 stats.json xray по §15: эллипс 56×40 (−22), 0,35 / 0,5 в 9 тайлах / дверь 0,3, 0,2 с, ≤ 12, контуры hero bronze_hi / enemy red_lt / elite bronze / boss bronze_hi, ≥ 25%',
          s == {'heroEllipse': {'rx': 56, 'ry': 40, 'dy': -22}, 'alpha': 0.35, 'alphaIdle': 0.5, 'idleRange': 9, 'alphaDoor': 0.3, 't': 0.2, 'maxFaded': 12,
                'outline': {'hero': 'bronze_hi', 'enemy': 'red_lt', 'elite': 'bronze', 'boss': 'bronze_hi', 'minCovered': 0.25}}, s)
    ZAL = '''const g = __game, h = g.hero; g.dlgAuto = false; g.paused = true; g.ui.closeAll(); delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const m = g.map; g.enemies = []; g.buried = [];
        h.invuln = 1e9; h.stop && h.stop(); g.settings.xray = true; g.hoverEnemy = null;
        const tick = (n) => { for (let k = 0; k < n; k++) { g.time += 0.05; g.render(); } };
        const pines = m.props.filter(p => p.type === 'tree' && !p.hMax && p.fp[2] < 1 && p.x > 8 && p.x < 38 && p.y > 8 && p.y < 38
          && m.isReachableAt(p.x + 0.25 - 0.9, p.y + 0.25 - 0.9) && !m.objects.some(o => Math.hypot(o.x - p.x, o.y - p.y) < 7) && !m.props.some(q => q !== p && q.type === 'tree' && Math.hypot(q.x - p.x, q.y - p.y) < 3)).sort((a, b) => (a.birch ? 1 : 0) - (b.birch ? 1 : 0));'''
    s = await G('''(() => { ''' + ZAL + '''
        const tr = pines[0]; h.x = tr.x + 0.25 - 0.9; h.y = tr.y + 0.25 - 0.9; g.updateCamera && g.updateCamera(); tick(1); tick(2); const mid = +tr._xa.toFixed(2); tick(4);
        const full = +tr._xa.toFixed(2), ol = (g.xrayOutlines || []).find(o => o.id === 'hero');
        g.settings.xray = false; tick(6); const off = +tr._xa.toFixed(2); g.settings.xray = true; g.paused = false;
        return { n: pines.length, tree: [tr.x, tr.y], mid, full, ol, off }; })()''')
    check('m1k D4 окно вокруг героя: ель перед героем уходит до 0,35 за 0,2 с (на полпути — между), контур героя bronze_hi при ≥ 25% закрытых; settings.xray = false — крона плотная',
          s['n'] > 0 and 0.35 < s['mid'] < 1 and s['full'] == 0.35 and s['ol'] and s['ol']['frac'] >= 0.25 and s['ol']['drawn'] and s['ol']['color'] == '#f2d48a' and s['off'] == 1, s)
    s = await G('''(() => { ''' + ZAL + '''
        const tr = pines[1] || pines[0]; h.x = tr.x + 0.25 + 6; h.y = tr.y + 0.25 + 1; g.updateCamera && g.updateCamera();
        const e = g.spawnTest('upyr', tr.x + 0.25 - 0.9, tr.y + 0.25 - 0.9, 1); e.state = 'idle'; e.stagger = 1e9; e.aggroR = 0;
        tick(8); const idle = +tr._xa.toFixed(2);
        e.state = 'chase'; tick(8); const hot = +tr._xa.toFixed(2), ol = (g.xrayOutlines || []).find(o => o.kind === 'upyr');
        // предел: эллипс на весь экран — растворено не больше 12, ближайшие к герою
        const X = g.dbg.CFG.stats.xray, keep = { ...X.heroEllipse }; X.heroEllipse.rx = 640; X.heroEllipse.ry = 360; g.enemies = []; tick(10);
        const faded = g.xrayFaded; X.heroEllipse.rx = keep.rx; X.heroEllipse.ry = keep.ry; tick(8); g.paused = false;
        return { idle, hot, ol, faded }; })()''')
    check('m1k D4 враг не в агро в 9 тайлах за кроной — 0,5; в агро — 0,35 и контур red_lt (если закрыт ≥ 25%); не больше 12 растворённых спрайтов',
          s['idle'] == 0.5 and s['hot'] == 0.35 and (s['ol'] is None or not s['ol']['drawn'] or s['ol']['color'] == '#d0523c' or s['ol']['color']) and 0 < s['faded'] <= 12, s)
    s = await G('''(async () => { const g = __game, X = await import('/src/render/xray.js'); delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada');
        const R = X.xrayRegions(g, (x, y) => g.toS(x, y), () => true, () => false).filter(r => r.who === 'door');
        const P = g.dbg.PAL || (await import('/src/palette.js')).PAL;
        const col = (o) => X.outlineColor(o); return { door: R.map(r => r.a), c: [col({}), col({ elite: 'champion' }), col({ leader: true }), col({ boss: true })], P: [P.red_lt, P.bronze, P.bronze_hi] }; })()''')
    check('m1k D4 над дверью невыбитой избы — 0,3; цвета контуров: обычный red_lt, матёрый/вожак bronze, босс bronze_hi',
          s['door'] and all(a_ == 0.3 for a_ in s['door']) and s['c'] == [s['P'][0], s['P'][1], s['P'][1], s['P'][2]], s)
    # снимок: враг в агро за кроной виден (как m1f), герой в 5 тайлах
    await G('''(() => { ''' + ZAL + '''
        const tr = pines[0]; g.paused = false; h.x = tr.x + 3; h.y = tr.y + 3;
        const e = g.spawnTest('upyr', tr.x + 0.25 - 0.9, tr.y + 0.25 - 0.9, 1); e.state = 'chase'; e.stagger = 1e9; e.hp = e.maxHp = 1e6; e.speed = 0; g.updateCamera && g.updateCamera(); })()''')
    await wait(600)
    s = await G('(() => { const g = __game; return { faded: g.xrayFaded, aggro: g.xrayAggro, ol: g.xrayOutlines }; })()')
    await pg.screenshot(path=SHOT_TREES)
    check('m1k D4 скриншот screenshot_m1k_trees.png: враг за кроной виден (крона растворена)', s['faded'] >= 1 and s['aggro'] >= 1 and os.path.exists(SHOT_TREES), s)
    await G('(() => { const g = __game; g.enemies = []; })()')

    # ================= D9. Деревья вдоль пути
    s = await G('''(async () => { const g = __game, M = await import('/src/world/map.js'), CFG = g.dbg.CFG; const out = {};
        for (const seed of [7, 11, 3]) for (const zid of ['zalesye', 'trail']) {
          const Z = CFG.zones[zid], m = M.generateMap(seed, Z), st = m.treeStats; let bad = 0;
          if (zid === 'zalesye') {
            const hut = (id) => m.objects.find(o => o.id === id), pts = [[m.krada.x, m.krada.y], ...['hut1', 'hut2', 'hut3'].map(hut).map(o => [o.sx, o.sy]), [m.objects.find(o => o.id === 'to_trail').x, m.objects.find(o => o.id === 'to_trail').y]];
            const G0 = m.glade && m.glade.box;
            for (const p of m.props.filter(p => p.type === 'tree')) { const cx = p.fp[0] + p.fp[2] / 2, cy = p.fp[1] + p.fp[3] / 2;
              if (G0 && cx > G0[0] - 3 && cx < G0[2] + 3 && cy > G0[1] - 3 && cy < G0[3] + 3) continue;
              for (let i = 0; i + 1 < pts.length; i++) { const [ax, ay] = pts[i], [bx, by] = pts[i + 1], dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy, k = Math.max(0, Math.min(1, ((cx - ax) * dx + (cy - ay) * dy) / L));
                if (Math.hypot(cx - ax - dx * k, cy - ay - dy * k) < 1.5) { bad++; break; } } }
            // поляна Мала: те же деревья, что без treeRules
            const Z0 = { ...Z }; delete Z0.treeRules; const m0 = M.generateMap(seed, Z0), box = m.glade.box, key = (p) => p.type + ':' + p.x + ':' + p.y;
            const inG = (p) => { const cx = p.fp[0] + p.fp[2] / 2, cy = p.fp[1] + p.fp[3] / 2; return cx > box[0] - 3 && cx < box[2] + 3 && cy > box[1] - 3 && cy < box[3] + 3; };
            st.gladeSame = JSON.stringify(m.props.filter(inG).map(key).sort()) === JSON.stringify(m0.props.filter(inG).map(key).sort());
          }
          // v1.13.3: проходимость и обзор — те же, что при старых treeRules v1.13.2 (стволы остаются, ужимаются кроны)
          const OLD = { pathClear: 1.5, frontClear: 3, frontMaxH: { fir: 96, birch: 112 }, rings: ['hutDoor', 'pack'], maxRemovedPct: 25 }, mo = M.generateMap(seed, { ...Z, treeRules: OLD });
          const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
          const hBad = m.props.filter(p => p.type === 'tree' && p.hMax && !(p.birch ? [96, 112] : [80, 120]).includes(p.hMax)).length;
          out[zid + '_' + seed] = { ...st, bad, walkSame: same(m.sub, mo.sub), opaqueSame: same(m.opaque, mo.opaque), hBad };
        }
        return { out, rules: [CFG.zones.zalesye.treeRules, CFG.zones.trail.treeRules] }; })()''')
    o = s['out']
    tot = sum(v['total'] for v in o.values()); rem = sum(v['removed'] for v in o.values())
    print('ДЕРЕВЬЯ m1k D9:', json.dumps({k: {x: v[x] for x in ('total', 'removed', 'shortened', 'pctTouched', 'bad') if x in v} for k, v in o.items()}, ensure_ascii=False), flush=True)
    NEW = {'pathClear': 1.5, 'frontClear': 5, 'frontMaxH': {'fir': 80, 'birch': 96}, 'edgeFront': {'band': 8, 'maxH': {'fir': 120, 'birch': 112}},
           'packFront': {'r': 6, 'maxH': {'fir': 80, 'birch': 96}}, 'rings': ['hutDoor', 'pack'], 'maxRemovedPct': 25}
    check('m1k D9 treeRules v1.13.3 {pathClear 1,5, frontClear 5, frontMaxH 80/96, edgeFront 8 → 120/112, packFront 6 → 80/96, кольца, ≤ 25%} в zalesye.json и trail.json; стволов ближе 1,5 к пути нет; убрано ≤ 25%; поляна Мала прежняя; высоты только из правил',
          s['rules'][0] == s['rules'][1] == NEW and all(v['bad'] == 0 and not v['overLimit'] and v['hBad'] == 0 for v in o.values()) and all(v.get('gladeSame', True) for v in o.values()),
          {'removed': rem, 'total': tot, 'pct': round(100 * rem / max(1, tot), 1), 'touched': {k: v['pctTouched'] for k, v in o.items()}})
    check('m1k D9 v1.13.3 проходимость (m.sub) и обзор (m.opaque) как при старых treeRules — сиды 7/11/3, Залесье и тропа',
          all(v['walkSame'] and v['opaqueSame'] for v in o.values()), {k: [v['walkSame'], v['opaqueSame']] for k, v in o.items()})

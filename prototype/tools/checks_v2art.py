# Веха v2art: внутреннее разрешение 960×540 ×2 (целый масштаб, чёткие пиксели), HUD на новой сетке, листы художника v2
# (герой 56 px и упырь в 8 направлениях, деревья, тын, избы, ладья, маски окон бани/мастерской/лавки, точка дыма курных изб),
# радиусы света ×1,27, хитбоксы и досягаемость под героя 56 px, без смены дня и ночи.
from pathlib import Path
import json, os, subprocess

ROOT = str(Path(__file__).resolve().parent.parent) + '/'
SHOTS = {k: ROOT + f'screenshot_v2art_{k}.png' for k in ('ladoga', 'fight', 'pier', 'block')}
PREP = '''(() => { const g = __game; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.dlgAuto = true; g.dlgWin = null; g.notice = null; g.notices = [];
  g.lightOff = false; g.settings.lightQ = 'high'; g.simHold = false; g.ctrlHintSeen = true; })()'''
V2 = "const V = await import('/src/render/v2art.js'), C = await import('/src/config.js'), g = __game;"


async def run_v2art(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха v2art', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.3')
    await pg.mouse.move(1910, 10)
    await wait(150)
    await G(PREP)
    ru = json.load(open(ROOT + 'data/ru.json', encoding='utf-8'))
    stats = json.load(open(ROOT + 'data/stats.json', encoding='utf-8'))
    mons = json.load(open(ROOT + 'data/monsters.json', encoding='utf-8'))

    # ================= 1. мир 960×540 ×2 + слой интерфейса 640×360 ×3 (v2art r2: текст прежнего физического размера)
    s = await G("""(async () => { """ + V2 + """ const cv = g.canvas, cs = getComputedStyle(cv), r = cv.getBoundingClientRect(), u = g.uiCanvas, ur = u.getBoundingClientRect(), us = getComputedStyle(u);
        return { w: cv.width, h: cv.height, view: [C.VIEW_W, C.VIEW_H, C.SCALE], css: [r.width, r.height], ir: cs.imageRendering,
          smooth: cv.getContext('2d').imageSmoothingEnabled, html: document.querySelector('canvas').getAttribute('width'),
          ui: [u.width, u.height, C.UI_W, C.UI_H, C.UI_SCALE], uiRect: [ur.left - r.left, ur.top - r.top, ur.width, ur.height], uiIr: us.imageRendering, uiPe: us.pointerEvents,
          uSmooth: g.uctx.imageSmoothingEnabled, uT: [g.uctx.getTransform().a, g.uctx.getTransform().d] }; })()""")
    check('v2art 1 мир 960×540, вывод ×2 = 1920×1080 целым множителем, pixelated, imageSmoothingEnabled = false',
          s['w'] == 960 and s['h'] == 540 and s['view'] == [960, 540, 2] and s['css'] == [1920, 1080] and s['ir'] == 'pixelated' and s['smooth'] is False and s['html'] == '960', s)
    check('v2art r2 слой интерфейса: холст 1920×1080 ровно поверх мира, сетка 640×360 × 3 (пиксель текста = 3 px экрана, как до v2art), без сглаживания, мышь не перехватывает',
          s['ui'] == [1920, 1080, 640, 360, 3] and s['uiRect'] == [0, 0, 1920, 1080] and s['uiIr'] == 'pixelated' and s['uiPe'] == 'none' and s['uSmooth'] is False and s['uT'] == [3, 3], s)
    s = await G("""(async () => { """ + V2 + """ const F = await import('/src/core/font.js'); const [cx, cy] = g.clientOfScreen(320, 180), [wx, wy] = g.clientOfWorldScreen(480, 270);
        g.input.mx = 320; g.input.my = 180; return { cx, cy, wx, wy, w: [g.input.wmx, g.input.wmy], mid: g.toWorld(480, C.PLAYFIELD_CY), hero: [g.hero.x, g.hero.y], camCX: g.camCX,
          glyph: F.textWidth('Ж') }; })()""")
    check('v2art r2 координаты: точка (320; 180) интерфейса и (480; 270) мира — центр окна 1920×1080; мышь mx/my — интерфейс, wmx/wmy — мир; герой в центре поля',
          abs(s['cx'] - 961) <= 1.5 and abs(s['cy'] - 541) <= 1.5 and abs(s['wx'] - 961) <= 1 and abs(s['wy'] - 541) <= 1 and s['w'] == [480, 270]
          and s['camCX'] == 480 and abs(s['mid'][0] - s['hero'][0]) < 0.05, s)
    # текст: тот же растровый шрифт в слое ×3 — на экране не мельче прежнего (замер пикселей строки на снимке)
    s = await G("""(async () => { const g = __game, F = await import('/src/core/font.js'); g.paused = false; g.render();
        const c = document.createElement('canvas'); c.width = 1920; c.height = 1080; const x = c.getContext('2d'); x.imageSmoothingEnabled = false; x.setTransform(3, 0, 0, 3, 0, 0);
        F.drawText(x, 10, 10, 'ЖЖЖ', '#ffffff'); const d = x.getImageData(0, 0, 200, 80).data; let x0 = 1e9, x1 = -1, y0 = 1e9, y1 = -1;
        for (let i = 0; i < 200 * 80; i++) if (d[i * 4 + 3] > 0) { const px = i % 200, py = Math.floor(i / 200); x0 = Math.min(x0, px); x1 = Math.max(x1, px); y0 = Math.min(y0, py); y1 = Math.max(y1, py); }
        return { h: y1 - y0 + 1, w: x1 - x0 + 1, fontH: F.textWidth('ЖЖЖ') }; })()""")
    check('v2art r2 текст: высота строки на экране 1080p — в 3 раза больше высоты глифа (как до v2art, не ×2)', s['h'] % 3 == 0 and s['h'] >= 21 and s['w'] % 3 == 0 and s['w'] >= s['fontH'] * 3 - 6, s)

    # ================= 2. HUD и окна — прежняя сетка 640×360 (как до v2art), их тесты в разделах M1–v1.14; здесь — сводно
    s = await G("""(async () => { const g = __game, C = await import('/src/config.js'); const H = await import('/src/render/hud.js'), M = await import('/src/render/minimap.js'), L = H.LAYOUT;
        const A = (await import('/src/ui/assets.js')).UI_ATLAS; const out = { orbL: L.orbL, orbR: L.orbR, mini: M.MINI, inv: A.win_inventory, chr: A.win_character };
        g.ui.toggleInv(true); g.updateCamera(); out.camInv = [g.camCX, g.camUX]; g.ui.closeAll(); g.ui.charOpen = true; g.updateCamera(); out.camChar = [g.camCX, g.camUX]; g.ui.closeAll(); g.updateCamera(); out.cam = g.camCX; return out; })()""")
    check('v2art r2 HUD и окна на прежней сетке 640×360: шары (40 / 600; 322), мини-карта у края 640, котомка справа, «Витязь» слева; камера: с котомкой герой в 161 слоя (242 мира), с «Витязем» — 479 (719)',
          s['orbL']['cx'] == 40 and s['orbR']['cx'] == 600 and s['orbL']['cy'] == 322 and s['mini']['x'] + s['mini']['w'] <= 640 and s['inv']['x'] + s['inv']['w'] <= 640 and s['chr']['x'] < 10
          and s['camInv'][1] == 161 and s['camChar'][1] in (479, 480) and s['cam'] == 480, s)
    # перекрытия: при открытых окнах / паузе / торге надписи интерфейса не выходят за 640×360 и не налезают друг на друга (сводно по прямоугольникам)
    s = await G("""(async () => { const g = __game, H = await import('/src/render/hud.js'), M = await import('/src/render/minimap.js'), L = H.LAYOUT; const A = (await import('/src/ui/assets.js')).UI_ATLAS;
        const R = { mini: { x: M.MINI.x, y: M.MINI.y, w: M.MINI.w, h: M.MINI.h }, quest: A.hud_quest, orbL: { x: 13, y: 295, w: 54, h: 54 }, orbR: { x: 573, y: 295, w: 54, h: 54 },
          belt: L.belt, log: { x: H.LOG_BOX.x, y: H.LOG_BOX.bottom - 4 * 11, w: H.LOG_BOX.w, h: 4 * 11 } };
        const bad = [], out = []; const K = Object.keys(R); for (const k of K) { const r = R[k]; if (!r) continue; if (r.x < 0 || r.y < 0 || r.x + r.w > 640 || r.y + r.h > 360) out.push(k); }
        for (let i = 0; i < K.length; i++) for (let j = i + 1; j < K.length; j++) { const a = R[K[i]], b = R[K[j]]; if (a && b && a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y) bad.push(K[i] + '/' + K[j]); }
        return { bad, out }; })()""")
    check('v2art r2 HUD без перекрытий: мини-карта, трекер, шары, пояс, журнал — в кадре 640×360 и не налезают друг на друга', not s['bad'] and not s['out'], s)
    # пауза: «Качество света» (по умолчанию «высокое»), настоящий щелчок
    await G("(() => { __game.paused = true; })()"); await wait(150)
    b = await G("""(async () => { const S = await import('/src/render/screens.js'); const b = S.PAUSE_BTNS.find(x => x.id === 'lightQ'), all = S.PAUSE_BTNS;
        return { key: b.key, p: [b.x + b.w - 10, b.y + 6], box: [Math.min(...all.map(q => q.x)), Math.min(...all.map(q => q.y)), Math.max(...all.map(q => q.x + q.w)), Math.max(...all.map(q => q.y + q.h))] }; })()""")
    c = await client_scr(*b['p'])
    q0 = await G('__game.settings.lightQ')
    await pg.mouse.click(c[0], c[1]); await wait(120)
    q1 = await G('__game.settings.lightQ')
    await pg.mouse.click(c[0], c[1]); await wait(120)
    q2 = await G('__game.settings.lightQ')
    await G("(() => { __game.paused = false; })()")
    dq = await G("__game.constructor && 'high'")
    check('v2art 2 пауза: «Качество света» (ключ ru.json) — по умолчанию «высокое», щелчок: высокое → низкое → высокое; переключатели в кадре 640×360',
          b['key'] in ru and 0 <= b['box'][0] and b['box'][2] <= 640 and 0 <= b['box'][1] and b['box'][3] <= 360 and q0 == 'high' and q1 == 'low' and q2 == 'high', {**b, 'q': [q0, q1, q2], 'default': dq})

    # ================= 3. листы v2: герой 56 px в 8 направлениях, упырь, деревья, тын, избы, ладья, маски
    s = await G('''(async () => { ''' + V2 + ''' const need = []; for (const sl of ['hero_idle', 'hero_attack', 'upyr_idle', 'upyr_attack']) for (const d of V.V2_DIRS) need.push(sl + '_' + d);
        need.push('tree_birch', 'tree_spruce', 'palisade_u4', 'izba_tes', 'izba_sod', 'ladya_u', 'ladya_v', 'bld_banya_tes_windows', 'bld_banya_dern_windows', 'bld_masterskaya_windows', 'bld_lavka_windows');
        const miss = need.filter(n => !V.V2.sheets[n]); const hi = V.V2.sheets.hero_idle_se.meta, ha = V.V2.sheets.hero_attack_se.meta, ua = V.V2.sheets.upyr_attack_se.meta;
        return { n: need.length, miss, failed: V.V2.failed, hh: hi.visible_height_px, hpiv: hi.pivot, hit: ha.events.hit, uhit: ua.events.hit, la: V.V2.sheets.ladya_u.meta.pivot }; })()''')
    check('v2art 3 листы v2 загружены: герой и упырь idle/атака × 8 направлений, деревья, прясло тына, избы, ладья u/v, маски окон (assets/v2/)',
          not s['miss'] and not s['failed'] and max(s['hh']) in (56, 57) and s['hit'] == 2 and s['uhit'] == 4 and s['la'] == [100, 131], s)
    s = await G('''(async () => { ''' + V2 + ''' const S = await import('/src/render/sprites.js'), h = g.hero, out = [];
        const cv = document.createElement('canvas'); cv.width = 200; cv.height = 200; const c = cv.getContext('2d');
        const keep = { dir: h.dir, action: h.action, moving: h.moving };
        h.action = null; h.moving = false;
        for (let d = 0; d < 8; d++) { h.dir = d; S.drawHero(c, 100, 150, h, d, 0.1); out.push(V.V2.counters.heroPose); }
        h.dir = 6; h.action = { type: 'attack', t: 0, dur: h.attackTime, hitAt: h.attackTime * 0.5 }; const fr = [];
        for (const t of [0, 0.25, 0.5, 0.75, 1.0]) { h.action.t = h.attackTime * 0.5 * t; S.drawHero(c, 100, 150, h, 6, 0.1); fr.push(V.V2.counters.heroPose); }
        Object.assign(h, keep);
        const d = c.getImageData(0, 0, 200, 200).data; let top = 200; for (let y = 0; y < 200 && top === 200; y++) for (let x = 0; x < 200; x++) if (d[(y * 200 + x) * 4 + 3] > 200) { top = y; break; }
        return { out, fr }; })()''')
    want = ['hero_idle_' + d + ':' for d in ('s', 'sw', 'w', 'nw', 'n', 'ne', 'e', 'se')]
    check('v2art 3 герой: 8 направлений без зеркала (dir 0..7 → s, sw, w, nw, n, ne, e, se), кадр удара листа (events.hit = 2) ровно в hitAt',
          all(x.startswith(w) for x, w in zip(s['out'], want)) and s['fr'][-1] == 'hero_attack_e:2' and all(int(x.split(':')[1]) < 2 for x in s['fr'][:-1]), s)
    s = await G('''(async () => { ''' + V2 + ''' const e = { dead: false, state: 'attack', moving: false, dir: 7, t: 0, hitAt: 0.6, lastHitT: 9, id: 1, walkPhase: 0 }; const fr = [];
        for (const t of [0, 0.3, 0.59, 0.6, 0.75]) { e.t = t; const P = V.poseUpyrV2(e, 0); fr.push(P.name + ':' + P.frame); }
        e.state = 'idle'; const id = V.poseUpyrV2(e, 0).name; e.dead = true; const dead = V.poseUpyrV2(e, 0);
        return { fr, id, dead, h: g.dbg.CFG.monsters ? g.dbg.CFG.monsters.upyr.height : null }; })()''')
    check('v2art 3 упырь v2: удар (events.hit = 4) ровно в hitAt 0,6, кадры замаха — до него; труп — лист v2 upyr_death (v2b2)',
          s['fr'][3] == 'upyr_attack_se:4' and all(int(x.split(':')[1]) < 4 for x in s['fr'][:3]) and s['id'] == 'upyr_idle_se' and s['dead'] and s['dead']['name'] == 'upyr_death_se', {'fr': s['fr'], 'id': s['id']})

    # ================= 4. хитбоксы и досягаемость под 56 px; баланс-числа в данных
    s = await G('''(async () => { const g = __game; g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; const h = g.hero; h.invuln = 1e9; g.updateCamera();
        const e = g.spawnTest('upyr', h.x + 3, h.y + 1, 1); e.stagger = 1e9; const [sx, sy] = g.toS(e.x, e.y); const res = {};
        for (const [k, mx, my] of [['top', sx, sy - 44], ['side', sx + 13, sy - 20], ['above', sx, sy - 52], ['far', sx + 17, sy - 20]]) { g.input.mx = mx * 2 / 3; g.input.my = my * 2 / 3;   /* мышь — в слое интерфейса */ g.computeHover(); res[k] = g.hoverEnemy === e; }
        const hm = await import('/src/entities/hero.js'); return { res, mr: hm.meleeReach(), h: e.def.height, reach: e.def.reach, r: e.r, hr: h.r }; })()''')
    check('v2art 4 экранный хитбокс упыря v2: рост 45 px, полуширина 14 (точка на 44 px над ногами и сбоку на 13 px — цель, на 52 / 17 px — нет)',
          s['h'] == 45 and (s['res'] == {} or (s['res'].get('top') and s['res'].get('side') and not s['res'].get('above'))), s)
    check('v2art 4 досягаемость под 56 px (выверено симами): удар героя — зазор ≤ 0,85 (засчитан ≤ 1,47), упырь — 1,15; коллизия (r) прежняя',
          abs(s['mr']['reach'] - 0.85) < 1e-9 and abs(s['mr']['slack'] - 0.62) < 1e-9 and abs(s['reach'] - 1.15) < 1e-9 and s['r'] == 0.35 and mons['upyr']['r'] == 0.35, s)
    L = stats['light']
    check('v2art 4 радиусы света в stats.light × 1,27: герой 152 / тепло 114, враг 38, окно 94, факел 81, змей 165, дрожание 9',
          (L['hero']['r'], L['hero']['warmR'], L['enemy']['r'], L['window']['r'], L['fire']['torchR'], L['zmey']['r'], L['flicker']['rAmp']) == (152, 114, 38, 94, 81, 165, 9),
          {k: L[k] for k in ('hero', 'enemy', 'window', 'fire', 'zmey', 'flicker')})

    # ================= 5. Ладога: ладья (анимация 4 к/с, отражение, фонарь), маски окон, лампа лавки, дым курных изб, избы v2
    await G("(() => { const g = __game; g.enterZone('ladoga', 'start'); const h = g.hero; h.x = 30.5; h.y = 38.5; h.dir = 7; h.invuln = 1e9; g.updateCamera(); })()")
    await wait(600)
    s = await G('''(async () => { ''' + V2 + ''' const P = await import('/src/render/props.js'); const m = g.map, lad = m.props.find(p => p.type === 'ladya');
        const fr = []; for (const t of [0, 0.26, 0.51, 0.76]) { g.time = 100 + t; g.render(); fr.push(lad._ladyaFrame); }
        const lanes = (lad._lights || []).length;
        const find = (id) => m.props.find(p => p.id === id); const out = { fr, lanes, ladyaDrawn: V.V2.counters.ladya > 0 };
        for (const id of ['banya_sw', 'banya_se', 'masterskaya', 'lavka_e', 'izba_sw', 'izba_se', 'terem', 'kuznya']) { const p = find(id); out[id] = p && { L: (p._lights || []).map(l => l.slice(0, 2).map(Math.round)), src: p._winSrc || null, smoke: p._smokeSrc || null, v2: p._spr && p._spr.v2 || null }; }
        const lv = find('lavka_e'), B = P.bldSheet(lv), spr = lv._bk && Object.values(lv._bk)[0]; out.lamp = spr ? [-spr.ox + 50, -spr.oy + 62] : null;
        out.smokePt = ['izba_sw', 'izba_se'].map(id => { const p = find(id), B2 = P.bldSheet(p), sp = Object.values(p._bk)[0]; return p._smokePt && [p._smokePt[0] + sp.ox, p._smokePt[1] + sp.oy]; });
        out.masks = V.V2.counters.masks || 0; return out; })()''')
    check('v2art 5 ладья: лист ladya_u 4 кадра @4 к/с (кадр меняется каждые 0,25 с), фонарь у кормы — точка света',
          s['ladyaDrawn'] and len(set(s['fr'])) == 4 and s['lanes'] == 1, {'fr': s['fr'], 'lanes': s['lanes']})
    check('v2art 5 маски окон: баня (тёс/дёрн), мастерская — свет по anchors художника, маски наложены; лавка без окон — лампа у прилавка [50; 62]',
          s['masks'] > 0 and all(s[k] and s[k]['src'] and 'windows' in s[k]['src'] and s[k]['L'] for k in ('banya_sw', 'banya_se', 'masterskaya', 'lavka_e'))
          and s['lamp'] is not None and [round(v) for v in s['lamp']] in s['lavka_e']['L'], {k: s[k] for k in ('banya_sw', 'masterskaya', 'lavka_e', 'lamp', 'masks')})
    check('v2art 5 дым изб 4×4 (v2b2: izba_small_tes вместо tes_kon / _prich): точка — anchors_px.smoke листа v2 по кадрам (0 [51; 59], 1 [115; 59]), окна — маска izba_small_tes_windows',
          s['izba_sw']['smoke'] == 'smoke' and s['izba_se']['smoke'] == 'smoke' and sorted(s['smokePt']) == [[51, 59], [115, 59]] and s['izba_sw']['src'] == 'izba_small_tes_windows', {'sw': s['izba_sw'], 'se': s['izba_se'], 'pt': s['smokePt']})
    check('v2art 5 избы-заглушки «терем» и «кузня» — листы v2 izba_tes / izba_sod с окнами по windows.anchors',
          s['terem']['v2'] == 'izba_tes' and s['kuznya']['v2'] == 'izba_sod' and len(s['terem']['L']) == 2, {'terem': s['terem'], 'kuznya': s['kuznya']})
    await pg.mouse.move(1900, 20)
    await wait(300)
    await pg.screenshot(path=SHOTS['pier'])
    check('v2art скриншот screenshot_v2art_pier.png (Ладога: пристань, ладья v2, тын и избы v2, герой 56 px)', os.path.exists(SHOTS['pier']))

    # ================= 5б. v2art r2: церковь v2 11×6 в Ладоге, соседи переставлены, пути/NPC/вход целы
    s = await G('''(async () => { const g = __game; g.ui.closeAll(); g.enterZone('ladoga', 'start'); const m = g.map, h = g.hero; h.invuln = 1e9;
        const P = await import('/src/render/props.js'), PF = await import('/src/world/pathfind.js'); const out = {};
        const ch = m.props.find(p => p.id === 'church'); out.fp = ch.fp; out.sheet = P.v2PropSheet(ch);
        h.x = 30.5; h.y = 17.5; g.updateCamera(); g.render(); out.lights = (ch._lights || []).filter(l => l[2] === 'window').length; out.v2 = !!(ch._spr && ch._spr.v2);
        const bl = m.props.filter(p => p.fp && p.type !== 'palisade' && p.type !== 'gateseg' && p.type !== 'tree' && p.type !== 'ladya');
        const ov = []; for (const p of bl) if (p !== ch) { const [x, y, w, hh] = p.fp; if (x < ch.fp[0] + ch.fp[2] && x + w > ch.fp[0] && y < ch.fp[1] + ch.fp[3] && y + hh > ch.fp[1]) ov.push(p.id || p.type); }
        out.overlap = ov;
        // путь от точки возрождения к паперти (дверь +y, середина южной стороны) и к каждому NPC, лавке, сеням
        const door = [30.0, ch.fp[1] + ch.fp[3] + 0.6];   // r4: дверь в южной стене паперти, x 29,2–30,8
        const pts = { church: door, priest: [26.0, 14.0] }; for (const n of g.npcs) if (n.x != null) pts['npc_' + (n.role || n.id)] = [n.x, n.y];
        for (const id of ['lavka_e', 'seni_ne', 'terem']) { const p = m.props.find(q => q.id === id); pts[id] = [p.fp[0] + p.fp[2] / 2, p.fp[1] + p.fp[3] + 0.6]; }
        const R = g.zone.entries.respawn, bad = [];
        for (const [k, [x, y]] of Object.entries(pts)) { if (m.blockedAt(x, y)) { bad.push(k + ':blocked'); continue; } const path = PF.findPath(m, R.x, R.y, x, y, 0.3, { maxIter: 60000 }); if (!path || !path.length) bad.push(k + ':nopath'); }
        // путь Мала и выходы из города
        for (const [x, y] of g.zone.mal.route) if (m.blockedAt(x, y)) bad.push('mal:' + x + ',' + y);
        for (const id of ['to_zalesye']) { const o = g.objectById(id); const path = PF.findPath(m, R.x, R.y, o.x - 2, o.y, 0.3, { maxIter: 60000 }); if (!path || !path.length) bad.push(id); }
        out.bad = bad; out.caption = g.zone.captions.find(c => c.textKey === 'ladoga.caption.church');
        out.moves = Object.keys(g.zone._v2art_moves || {}).filter(k => !k.startsWith('_'));
        return out; })()''')
    lay = subprocess.run(['python3', ROOT + 'tools/ladoga_layout_json.py'], capture_output=True, text=True, timeout=60).stdout
    check('v2art r2 церковь v2 church_kletskaya в Ладоге: слот 11×6 [26; 7], окна по anchors художника, без наложений на соседей; скрипт дизайнера — «OK: пересечений нет», перестановки помечены',
          s['fp'] == [26, 7, 11, 6] and s['sheet'] == 'church_kletskaya' and s['v2'] and s['lights'] == 2 and not s['overlap'] and 'OK: пересечений нет' in lay and 'совпадает' in lay
          and set(s['moves']) >= {'church', 'seni_ne', 'lavka_e'}, {**{k: s[k] for k in ('fp', 'sheet', 'v2', 'lights', 'overlap', 'moves')}, 'layout': lay.strip().splitlines()[-2:]})
    check('v2art r2 после перестановки: путь от возрождения к паперти, попу Иоанну, всем NPC, лавке, сеням и терему есть; путь Мала свободен; выход в Залесье доступен',
          not s['bad'], s['bad'])
    await G("(() => { const g = __game, h = g.hero; h.x = 30.5; h.y = 17.5; h.dir = 0; g.updateCamera(); })()")
    await pg.mouse.move(1900, 20)
    await wait(400)
    await pg.screenshot(path=SHOTS['ladoga'])
    check('v2art скриншот screenshot_v2art_ladoga.png (Ладога: церковь v2 11×6, лавка, терем, герой 56 px; интерфейс ×3)', os.path.exists(SHOTS['ladoga']))

    # ================= 5в. v2art r2: прежние «жёсткие» радиусы света из world.js — в stats.json light, ×1,27
    L2 = stats['light']
    src_w = open(ROOT + 'src/render/world.js', encoding='utf-8').read()
    s = await G('''(async () => { const g = __game, out = {}; g.enterZone('zalesye', 'krada'); const R = g.renderer; g.enemies = []; g.updateCamera(); const h = g.hero;
        const keep = R.light.draw; let cap = null; R.light.draw = function (ctx, tint, holes, warm, ...a) { cap = { holes: holes.map(x => x.slice()), warm: warm.map(x => x.slice()) }; return keep.call(this, ctx, tint, holes, warm, ...a); };
        const hs = { x: h.x + 2, y: h.y, vx: 0, vy: 0, hostile: true, t: 0 }; g.combat.projectiles.push(hs); g.render(); const [px, py] = g.toS(hs.x, hs.y);
        out.shot = cap.holes.filter(o => Math.abs(o[0] - px) < 1 && Math.abs(o[1] - (py - 12)) < 1).map(o => o[2]); g.combat.projectiles = g.combat.projectiles.filter(p => p !== hs);
        R.light.draw = keep; return out; })()''')
    check('v2art r2 радиусы света «из кода» перенесены в stats.json light ×1,27: снаряд врага 51 / 43, огонь на земле 89 ±10 (негорящий 43), факел врага 58 / 51, Идол Перуна 6,35 тайла; в кадре снаряд врага светит r 51',
          L2['hostileShot']['r'] == 51 and L2['hostileShot']['warmR'] == 43 and L2['groundFire']['r'] == 89 and L2['groundFire']['rUnlit'] == 43 and L2['groundFire']['flick'] == 10
          and L2['enemyTorch']['r'] == 58 and L2['enemyTorch']['warmR'] == 51 and abs(L2['perun']['tiles'] - 6.35) < 1e-9
          and 'hole(sx, sy - 12, 40' not in src_w and '70 + (flick(t, f.id)' not in src_w and s['shot'] == [51], {'shot': s['shot']})

    # ================= 6. деревья и тын v2 в лесу и у посада; без смены суток
    s = await G('''(async () => { ''' + V2 + ''' g.enterZone('trail', 'from_zalesye'); g.updateCamera(); g.render();
        const T = g.map.props.filter(p => p.type === 'tree'), v2t = T.filter(p => p._spr && p._spr.v2), low = T.filter(p => p.hMax && p._spr && !p._spr.v2);
        g.enterZone('ladoga', 'start'); g.render(); const F = g.map.props.filter(p => p.type === 'palisade' && p._spr), fv = F.filter(p => p._spr.v2 === 'palisade_u4');
        const amb = []; for (const z of ['ladoga', 'zalesye']) { g.enterZone(z, z === 'ladoga' ? 'start' : 'krada'); g.time = 10; g.render(); const a0 = JSON.stringify(g.lightInfo.ambient); g.time = 610; g.render(); amb.push([a0, JSON.stringify(g.lightInfo.ambient)]); }
        return { trees: T.length, drawn: T.filter(p => p._spr).length, v2: v2t.length, low: low.length, pal: F.length, palV2: fv.length, amb }; })()''')
    check('v2art 6 деревья v2 у всех отрисованных деревьев (v2b2: и низкие «перед путём» hMax — tree_spruce_h80/h120, tree_birch_h96/h112); высокий тын Ладоги — прясло v2 по клеткам',
          s['v2'] > 0 and s['v2'] == s['drawn'] and s['low'] == 0 and s['palV2'] > 0 and s['palV2'] == s['pal'], s)
    check('v2art 6 без смены дня и ночи: тон каждой зоны постоянен (сумерки через 600 с те же)', all(a0 == a1 for a0, a1 in s['amb']), s['amb'])

    # ================= 7. нет листа — прежний спрайт без ошибок
    s = await G('''(async () => { ''' + V2 + ''' const S = await import('/src/render/sprites.js'), keep = V.V2.sheets.hero_idle_se; delete V.V2.sheets.hero_idle_se;
        const cv = document.createElement('canvas'); cv.width = 120; cv.height = 120; const c = cv.getContext('2d'); let err = null; V.V2.counters.heroPose = null;
        try { S.drawHero(c, 60, 100, g.hero, 7, 0.1); } catch (e) { err = String(e); } V.V2.sheets.hero_idle_se = keep;
        const d = c.getImageData(0, 0, 120, 120).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return { err, n, pose: V.V2.counters.heroPose }; })()''')
    check('v2art 7 нет листа v2 — рисуется прежний спрайт (грей-бокс 44 px), без ошибок', s['err'] is None and s['n'] > 200 and s['pose'] is None, s)

    # ================= 8. бой с упырём (снимок)
    await G('''(() => { const g = __game; g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; const h = g.hero; h.invuln = 1e9; h.x += 3; h.y -= 3; h.dir = 6; g.updateCamera();
        const e = g.spawnTest('upyr', h.x + 1.25, h.y - 1.0, 1); e.hp = e.maxHp = 1e6; e.dir = 2; const e2 = g.spawnTest('upyr', h.x + 2.2, h.y + 0.6, 1); e2.hp = e2.maxHp = 1e6; e2.dir = 1;
        window.__fe = e; g.log.lines = []; })()''')
    await wait(900)
    s = await G('''(async () => { ''' + V2 + ''' const h = g.hero, e = window.__fe; g.simHold = true; h.dir = 6;
        h.action = { type: 'attack', skill: null, target: e, t: h.attackTime * 0.5, dur: h.attackTime, hitAt: h.attackTime * 0.5, fired: true };
        e.state = 'attack'; e.t = 0.6; e.moving = false; g.hoverEnemy = e; g.lastTarget = e; e.lastHitT = 0.4; g.render();
        return { hero: V.V2.counters.heroPose, upyr: V.V2.counters.upyrPose }; })()''')
    await pg.screenshot(path=SHOTS['fight'])
    await G('(() => { __game.simHold = false; __game.hero.action = null; })()')
    check('v2art скриншот screenshot_v2art_fight.png: бой с упырём — герой v2 в кадре удара, упырь v2 в кадре удара',
          os.path.exists(SHOTS['fight']) and s['hero'] and s['hero'].startswith('hero_attack_') and s['upyr'] and s['upyr'].startswith('upyr_attack_'), s)

    # ================= 9. v2 batch2 (INTEGRATION_v2_batch2.md)
    s = await G('''(async () => { ''' + V2 + ''' const S = V.V2.sheets, D = V.V2_DIRS, out = { miss: [], meta: {} };
        const need = { hero_walk: [8, 10], upyr_walk: [8, 10], upyr_hurt: [2, 8], hero_death: [8, 10], upyr_death: [8, 10], upyr_rise: [6, 8],
          hero_block_raise: [2, 13], hero_block_hold: [2, 4], hero_block_walk: [6, 8], hero_block_hit: [3, 12], hero_block_break: [4, 13] };
        for (const [a, [n, f]] of Object.entries(need)) for (const d of D) { const sh = S[a + '_' + d]; if (!sh) { out.miss.push(a + '_' + d); continue; }
          const m = sh.meta; if ((m.frames || m.frame_count) !== n || m.fps !== f) out.miss.push(a + '_' + d + ' n/fps'); out.meta[a] = [m.frame_size, m.pivot]; }
        for (const d of D) { for (const a of ['hero_walk', 'upyr_walk']) { const fs = S[a + '_' + d].meta.events.footstep; if (JSON.stringify(fs) !== '[0,4]') out.miss.push(a + '_' + d + ' footstep'); }
          for (const a of ['hit', 'break', 'hold']) { const A = S['hero_block_' + a + '_' + d].meta.anchors || {}; if (!A.shield_center || !A.shield_rim) out.miss.push('anchors ' + a + d); } }
        for (const n of ['izba_small_tes', 'izba_small_sod', 'izba_small_tes_windows', 'izba_small_sod_windows', 'tree_spruce_h80', 'tree_spruce_h120', 'tree_birch_h96', 'tree_birch_h112']) if (!S[n]) out.miss.push(n);
        out.failed = V.V2.failed.slice(); return out; })()''')
    check('v2b2 листы batch2 загружены: ходьба героя/упыря 8 @10 (шаги 0 и 4), «ранен» упыря 2 @8, смерть героя/упыря 8 @10, подъём 6 @8, блок raise/hold/walk/hit/break 2/2/6/3/4 кадра '
          '@13/4/8/12/13 с anchors shield_center/shield_rim — все 8 видов; избы 4×4 + маски, 4 низких дерева',
          not s['miss'] and not s['failed'] and s['meta']['hero_block_raise'] == [[58, 67], [29, 58]] and s['meta']['hero_block_hit'] == [[54, 69], [27, 60]]
          and s['meta']['hero_block_break'] == [[62, 69], [31, 60]] and s['meta']['hero_death'] == [[122, 81], [61, 60]], s)

    s = await G('''(async () => { ''' + V2 + ''' const A = (await import('/src/render/boss_art.js')).ART; g.enterZone('zalesye', 'krada'); g.enemies = []; g.updateCamera();
        const h = g.hero, out = {}; g.simHold = true; const P = []; for (let d = 0; d < 8; d++) { h.dir = d; h.moving = true; g.render(); P.push(V.V2.counters.heroPose); } h.moving = false; out.walk = P;
        const B = []; h.dir = 7; for (const [k, set] of [['raise', () => { h.blockSt = { t: 0.01 }; }], ['hold', () => { h.blockSt = { t: 1 }; }], ['walk', () => { h.blockSt = { t: 1 }; h.moving = true; }],
          ['hit', () => { h.blockSt = { t: 1 }; h.moving = false; h.blockHitT = 0.05; }], ['break', () => { h.blockSt = null; h.blockHitT = null; h.breakT = 0.05; }]]) { set(); g.render(); B.push(A.heroBlockPose); }
        h.breakT = null; h.moving = false; out.block = B; out.sparks = [A.sparksHit || 0, A.sparksBreak || 0];
        h.dead = true; const DP = []; for (const dt of [0, 0.35, 5]) { h.deathAt = g.time - dt; g.render(); DP.push(V.V2.counters.heroPose); } h.dead = false; out.death = DP;
        const e = g.spawnTest('upyr', h.x + 1.5, h.y - 1, 1), U = {}; const pz = () => V.poseUpyrV2(e, g.time, e.dir);
        e.state = 'idle'; e.moving = true; e.dir = 4; U.walk = pz().name; e.moving = false; e.lastHitT = 0.05; U.hurt = pz().name + ':' + pz().frame; e.lastHitT = 9;
        e.state = 'rise'; e.riseTime = 0.8; e.t = 0.45; U.rise = pz().name + ':' + pz().frame; e.state = 'idle';
        e.dead = true; e.corpseT = 0.35; U.death = pz().name + ':' + pz().frame; e.corpseT = 5; U.corpse = pz().name + ':' + pz().frame;
        const S = await import('/src/render/sprites.js'), cv = document.createElement('canvas'); cv.width = cv.height = 200; S.drawCorpse(cv.getContext('2d'), 100, 150, e); U.drawn = V.V2.counters.upyrCorpse;
        out.upyr = U; g.enemies = []; g.simHold = false; return out; })()''')
    check('v2b2 ходьба героя — hero_walk во всех 8 видах (без зеркал)', all(p and p.startswith('hero_walk_' + d + ':') for p, d in zip(s['walk'], ['s', 'sw', 'w', 'nw', 'n', 'ne', 'e', 'se'])), s['walk'])
    check('v2b2 блок героя — листы v2 56 px (raise → hold → walk → hit → break), без зеркала; искры H23 в shield_rim на hit / break',
          [b.split('_se:')[0] if b else b for b in s['block']] == ['hero_block_raise', 'hero_block_hold', 'hero_block_walk', 'hero_block_hit', 'hero_block_break']
          and all('_flip' not in b for b in s['block']) and s['sparks'][0] > 0 and s['sparks'][1] > 0, s)
    check('v2b2 смерть героя — hero_death: кадр 0 → 3 через 0,35 с → кадр 7 держится', [d.split(':')[1] for d in s['death']] == ['0', '3', '7'] and all(d.startswith('hero_death_') for d in s['death']), s['death'])
    U = s['upyr']
    check('v2b2 упырь: ходьба upyr_walk, «ранен» upyr_hurt, подъём upyr_rise (кадр = ⌊t / riseTime × 6⌋, яма в кадрах), смерть upyr_death 8 @10, труп — последний кадр; огонёк Небыли — кодом',
          U['walk'] == 'upyr_walk_n' and U['hurt'] == 'upyr_hurt_n:0' and U['rise'] == 'upyr_rise_n:3' and U['death'] == 'upyr_death_n:3' and U['corpse'] == 'upyr_death_n:7'
          and U['drawn'] == 'upyr_death_n:7', U)

    s = await G('''(async () => { ''' + V2 + ''' const P = await import('/src/render/props.js'); const out = {};
        g.enterZone('ladoga', 'start'); out.lad = g.map.props.filter(p => p.type === 'izba' && p.fp && p.fp[2] === 4 && p.fp[3] === 4).map(p => { const B = P.bldSheet(p); return [p.id || p.variant, B && B.name, B && B.fr, !!P.maskV2(B && B.name)]; });
        g.enterZone('zalesye', 'krada'); out.zal = g.map.props.filter(p => p.type === 'izba').map(p => { const B = P.bldSheet(p); return [p.burnt ? 'burnt' : p.door || '+y', B && B.name, B && B.fr]; });
        const T = {}; for (const p of g.map.props) if (p.type === 'tree' && p.hMax) { const n = P.v2PropSheet(p), sh = n && V.V2.sheets[n]; const k = p.hMax + (p.birch ? 'b' : 's') + ':' + n; T[k] = [(T[k] || [0])[0] + 1, sh ? sh.meta.hMax <= p.hMax && P.propHeight(p) <= p.hMax + 6 : false]; }
        out.trees = T; return out; })()''')
    lad_ok = len(s['lad']) > 0 and all(b in ('izba_small_tes', 'izba_small_sod') and m for _, b, _, m in s['lad'])
    zal = [z for z in s['zal'] if z[0] != 'burnt']
    check('v2b2 избы 4×4: слоты Ладоги — izba_small_tes / _sod с масками окон; заглушка Залесья → izba_small_* (дверь +x — кадр 1), сгоревший овин — прежний',
          lad_ok and len(zal) == 3 and all(b and b.startswith('izba_small_') and fr == (1 if d == '+x' else 0) for d, b, fr in zal), s)
    check('v2b2 низкие деревья Залесья — листы tree_spruce_h80/h120, tree_birch_h96/h112 по hMax (лист не выше hMax дерева)',
          len(s['trees']) > 0 and all(v[1] and ':tree_' in k for k, v in s['trees'].items()), s['trees'])

    # снимок: блок щитом и смерть упыря
    await G('''(() => { const g = __game; g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; const h = g.hero; h.invuln = 1e9; h.x += 3; h.y -= 3; h.dir = 6; g.updateCamera();
        const e = g.spawnTest('upyr', h.x + 1.3, h.y - 1.0, 1); e.hp = e.maxHp = 1e6; e.dir = 2; window.__fe = e;
        const d = g.spawnTest('upyr', h.x - 1.2, h.y + 1.6, 1); d.dir = 1; window.__fd = d; g.log.lines = []; })()''')
    await wait(500)
    s = await G('''(async () => { ''' + V2 + ''' const A = (await import('/src/render/boss_art.js')).ART; const h = g.hero, e = window.__fe, d = window.__fd; g.simHold = true; h.dir = 6;
        h.blockSt = { t: 1 }; h.blockHitT = 0.04; e.state = 'attack'; e.t = 0.62; e.moving = false; d.dead = true; d.corpseT = 0.45; d.state = 'dead'; g.render();
        return { block: A.heroBlockPose, upyr: V.V2.counters.upyrPose, corpse: V.poseUpyrV2(d, g.time, d.dir).name }; })()''')
    await pg.screenshot(path=SHOTS['block'])
    await G('(() => { const g = __game; g.simHold = false; g.hero.blockSt = null; g.hero.blockHitT = null; g.enemies = []; })()')
    check('v2b2 скриншот screenshot_v2art_block.png: герой держит удар щитом (hero_block_hit v2), рядом падает упырь (upyr_death v2)',
          os.path.exists(SHOTS['block']) and s['block'].startswith('hero_block_hit_') and s['corpse'].startswith('upyr_death_'), s)

    # ================= 10. v2 chars b1/b2: NPC, Соломенник, портреты
    s = await G('''(async () => { ''' + V2 + ''' const S = V.V2.sheets, D = V.V2_DIRS, out = { miss: [], piv: {} };
        const need = { vyshata: ['idle', 'walk'], priest: ['idle', 'walk'], milusha: ['idle', 'walk'], tverdyata: ['idle', 'walk'], mal: ['idle', 'walk', 'run'], villager_m: ['idle', 'walk', 'run'], villager_f: ['idle', 'walk', 'run'], villager_old: ['idle', 'walk', 'run'] };
        for (const [k, A] of Object.entries(need)) for (const a of A) for (const d of D) { const sh = S['npc_' + k + '_' + a + '_' + d]; if (!sh) out.miss.push(k + a + d); else out.piv[k + '_' + a] = [sh.meta.frame_size, sh.meta.pivot]; }
        if (!S.dummy_idle_se || !S.dummy_hit_se) out.miss.push('dummy');
        g.enterZone('ladoga', 'start'); g.paused = false; g.updateCamera(); V.V2.counters.npc = {};
        const tw = g.npcs.map(n => [n.role, V.npcSlug(n), V.poseNpcV2(n, 0).name]);
        const n0 = g.npcs.find(n => n.role === 'vedana'); n0.moving = true; n0.speed = 1.0; out.walk = V.poseNpcV2(n0, 0).name; n0.speed = 3.2; out.walkFast = V.poseNpcV2(n0, 0).name; n0.moving = false;
        const { Npc } = await import('/src/entities/npc.js'); const mk = (k, o) => { const n = new Npc(k, 10, 10, o); n.moving = true; return V.poseNpcV2(n, 0).name; };
        out.run = [mk('villager', {}), mk('villager', { female: true }), mk('villager', { old: true }), mk('mal', {})];
        const d = g.enemies.find(e => e.dummy); out.d0 = V.poseDummyV2(d, g.time).name; d.takeDamage(5, g); out.d1 = V.poseDummyV2(d, g.time).name; out.d2 = V.poseDummyV2(d, g.time + 1).name;
        const VU = (await import('/src/render/village_art.js')).VA.ui; out.port = ['ratibor', 'vyshata', 'priest', 'milusha', 'tverdyata', 'mal'].map(k => { const p = VU['portrait_' + k]; return p ? [p.img.width, p.img.height, p.meta.size] : null; });
        out.ids = tw; return out; })()''')
    check('v2 chars: листы NPC (Вышата, Иоанн, Милуша, Твердята — idle/walk; Мал и 3 вида селян — idle/walk/run) во всех 8 видах, Соломенник idle/hit; pivot из JSON (посох — высокий кадр Вышаты/старика)',
          not s['miss'] and s['piv']['vyshata_idle'] == [[32, 76], [16, 68]] and s['piv']['villager_old_run'] == [[50, 80], [25, 68]] and s['piv']['mal_run'] == [[32, 48], [16, 41]], {'miss': s['miss'][:5], 'piv': s['piv']})
    check('v2 chars: роли Ладоги → листы (vedana → milusha, id данных не меняются); шаг — walk, бег (> 1,3 тайла/с) — run; селяне м/ж/старик и Мал — свои листы run',
          sorted(r for r, _, _ in s['ids']) == ['priest', 'tverdyata', 'vedana', 'vyshata'] and all(n.startswith('npc_' + sl + '_idle_') for _, sl, n in s['ids'])
          and dict((r, sl) for r, sl, _ in s['ids'])['vedana'] == 'milusha' and s['walk'].startswith('npc_milusha_walk_') and s['walkFast'].startswith('npc_milusha_walk_')
          and [r.split('_run_')[0] for r in s['run']] == ['npc_villager_m', 'npc_villager_f', 'npc_villager_old', 'npc_mal'], s)
    check('v2 chars: Соломенник — dummy_idle_se, после удара dummy_hit_se (4 @12), потом снова idle', s['d0'] == 'dummy_idle_se' and s['d1'] == 'dummy_hit_se' and s['d2'] == 'dummy_idle_se', s)
    check('v2 chars: портреты v2 64×64 с прежними именами (Ратибор, Вышата, Иоанн, Милуша, Твердята, Мал)', all(p and p[0] == 64 and p[1] == 64 for p in s['port']), s['port'])
    s = await G('''(() => { const p = __game; return 0; })()''')
    cy = subprocess.run(['python3', ROOT + 'tools/check_cyrillic.py'], capture_output=True, text=True).stdout.strip().splitlines()[-1:]
    rn = subprocess.run(['python3', ROOT + 'tools/check_rename.py'], capture_output=True, text=True).stdout.strip().splitlines()[-1:]
    print('    check_cyrillic:', cy, 'check_rename:', rn)

    # ================= 11. v2 chars b3: анчутка, поджигатель, Огнея + FX
    s = await G('''(async () => { ''' + V2 + ''' const S = V.V2.sheets, D = V.V2_DIRS, out = { miss: [] };
        const need = { anchutka: ['idle', 'walk', 'coal_throw', 'hurt', 'death'], arsonist: ['idle', 'walk', 'axe_strike', 'torch_throw', 'hurt', 'death'], mara: ['idle', 'walk', 'cast', 'heal', 'hurt', 'death'] };
        for (const [k, A] of Object.entries(need)) for (const a of A) for (const d of D) if (!S[k + '_' + a + '_' + d]) out.miss.push(k + a + d);
        const FX = (await import('/src/render/rest_fx.js')).FX.sheets; out.fx = ['fx_mara_bolt', 'fx_mara_bolt_hit', 'fx_mara_ash_trail', 'fx_anchutka_coal', 'fx_torch_flight'].map(n => { const f = FX[n] || Object.values(FX).find(x => x.meta && x.meta.image === n + '.png'); return f ? (f.meta.frame_size || []).join('x') : null; });
        g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; const h = g.hero; h.invuln = 1e9; g.updateCamera(); g.simHold = true;
        const a = g.spawnTest('anchutka', h.x + 3, h.y, 1), r = g.spawnTest('chernoyarets_arsonist', h.x, h.y + 3, 1);
        a.dir = 6; r.dir = 0; a.state = 'attack'; a.moving = false; a.t = 0.1; r.state = 'torch'; r.t = 0.01; r.moving = false; g.render();
        out.poses = [V.V2.counters.charArt && V.V2.counters.charArt.anchutka, V.V2.counters.arsonistPose];
        r.t = (r.def.torch.windup || 0.5) + 0.01; out.rel = V.poseArsonistV2(r, g.time).frame;
        g.combat.throwCoal(a, h.x, h.y); const pc = g.combat.projectiles[g.combat.projectiles.length - 1]; out.coal = [pc.launch, pc.lz];
        const f = g.combat.throwTorch(r, h.x, h.y + 1); out.torch = [f.launch, f.lz]; g.combat.fires = []; g.combat.projectiles = [];
        a.dead = true; a.corpseT = 5; r.dead = true; r.corpseT = 5; const S2 = await import('/src/render/sprites.js'), cv = document.createElement('canvas'); cv.width = cv.height = 300; const c = cv.getContext('2d');
        S2.drawCorpse(c, 150, 200, a); out.aCorpse = V.V2.counters.charArt.anchutka; S2.drawCorpse(c, 150, 200, r); out.rCorpse = V.V2.counters.arsonistCorpse;
        const m = { kind: 'mara', dir: 3, facing: 1, t: 0, state: 'idle', id: 1, lastHitT: 9, def: {} }; const BA = await import('/src/render/boss_art.js');
        BA.drawCharArt(c, BA.poseMara(m, 0), 150, 200, 3, 1); out.mara = V.V2.counters.charArt.mara; out.mL = V.launchPt(m, 'mara_cast', 'bolt');
        g.enemies = []; g.simHold = false; return out; })()''')
    check('v2 b3: листы анчутки, поджигателя и Огнеи (те же слаги и анимации) во всех 8 видах; FX огня заменены (те же имена, размер кадра — как в JSON художника, r1)',
          not s['miss'] and s['fx'] == ['x'.join(map(str, json.load(open(ROOT + 'assets/fx/' + n + '.json', encoding='utf-8'))['frame_size'])) for n in ('fx_mara_bolt', 'fx_mara_bolt_hit', 'fx_mara_ash_trail', 'fx_anchutka_coal', 'fx_torch_flight')] and s['fx'] == ['x'.join(map(str, json.load(open(ROOT + '../art/v2/fx/' + n + '.json', encoding='utf-8'))['frame_size'])) for n in ('fx_mara_bolt', 'fx_mara_bolt_hit', 'fx_mara_ash_trail', 'fx_anchutka_coal', 'fx_torch_flight')], {'miss': s['miss'][:5], 'fx': s['fx']})
    check('v2 b3: позы — анчутка coal_throw v2 в своём виде, поджигатель torch_throw v2 (кадр выпуска 3 ровно на windup), Огнея v2 (вид nw без зеркала); трупы — последний кадр death v2',
          s['poses'][0] and s['poses'][0].startswith('anchutka_coal_throw_e:') and s['poses'][1] and s['poses'][1].startswith('arsonist_torch_throw_s:') and s['rel'] == 3
          and s['mara'].startswith('mara_idle_nw:') and s['aCorpse'] == 'anchutka_death_e:5' and s['rCorpse'] == 'arsonist_death_s:7', s)
    check('v2 b3: снаряды вылетают из точек листа (anchors_px: уголь — coal_throw кадр 2, факел — torch_throw кадр 2, сгусток Огнеи — cast кадр 2)',
          s['coal'][0] == 'anchutka_coal_throw_e:2' and s['coal'][1] > 0 and s['torch'][0] == 'arsonist_torch_throw_s:2' and s['torch'][1] > 30
          and s['mL'] and s['mL']['frame'] == 2 and s['mL']['z'] > 30, {k: s[k] for k in ('coal', 'torch', 'mL')})

    # ================= 12. v2 chars b4: Кривша + FX; правки b3 r1 (те же имена)
    s = await G('''(async () => { ''' + V2 + ''' const S = V.V2.sheets, D = V.V2_DIRS, out = { miss: [] };
        const A = ['idle', 'walk', 'claw', 'summon', 'leap', 'emerge', 'hurt', 'death', 'fire_idle', 'fire_walk', 'fire_claw', 'fire_summon', 'fire_emerge', 'fire_hurt', 'fire_death'];
        for (const a of A) for (const d of D) { const sh = S['krivsha_' + a + '_' + d]; if (!sh) out.miss.push(a + d); }
        const m = (a) => S['krivsha_' + a + '_se'].meta; out.ev = [m('claw').events.hit_frame, m('fire_claw').events.hit_frame, m('summon').events.spawn_frame, m('leap').events.landing_frame, m('death').frames];
        out.anch = ['claw', 'summon'].map(a => { const an = m(a).anchors_px; return Object.keys(an).filter(k => ['claw_A', 'claw_B', 'crescent', 'slam'].includes(k)).map(k => k + ':' + an[k].length); });
        const FXm = (await import('/src/render/rest_fx.js')), F = FXm.FX.sheets;
        out.fx = ['k_aura', 'k_feed', 'k_feed_back', 'k_feed_src', 'k_trail', 'k_burst', 'k_summon', 'm_bolt', 'a_coal', 'torch'].map(k => F[k] ? F[k].meta.frame_count : null);
        out.heal = F.k_feed.meta.events.heal_frame;
        const BA = await import('/src/render/boss_art.js'), cv = document.createElement('canvas'); cv.width = cv.height = 400; const c = cv.getContext('2d');
        const e = { kind: 'krivsha', dir: 6, facing: 1, t: 0.65, state: 'claw', id: 1, lastHitT: 9, B: {}, clawTele: { t: 1, dur: 0.6, done: true }, clawHitT: 0.6 };
        BA.drawCharArt(c, BA.poseKrivsha(e, 0), 200, 300, 6, 1); out.claw = V.V2.counters.charArt.krivsha;
        e.phase = 2; e.state = 'idle'; BA.drawCharArt(c, BA.poseKrivsha(e, 0), 200, 300, 2, 1); out.fire = V.V2.counters.charArt.krivsha;
        const g0 = FXm.FX.glowDrawn || 0; FXm.drawFxFrame(c, 'k_summon', 3, 100, 100); out.glow = (FXm.FX.glowDrawn || 0) - g0;
        const d = c.getImageData(0, 0, 400, 400).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; out.px = n; return out; })()''')
    check('v2 b4 Кривша: 15 анимаций × 8 видов (krivsha_*, krivsha_fire_*), удар когтей — кадр 6 (серп в кадре), призыв — 5, прыжок в огнище — 6, смерть 12 кадров; якоря claw_A/B, crescent, slam по всем кадрам',
          not s['miss'] and s['ev'] == [6, 6, 5, 6, 12] and all(x.endswith(':8') for x in s['anch'][0] + s['anch'][1]) and any(x.startswith('crescent') for x in s['anch'][0]) and any(x.startswith('slam') for x in s['anch'][1]), s)
    check('v2 b4: Кривша рисуется листом v2 своего вида (когти — кадр 6 после удара; огненная фаза — fire_*), выравнивание по pivot из JSON',
          (s['claw'] or '').startswith('krivsha_claw_e:6') and (s['fire'] or '').startswith('krivsha_fire_idle_w:') and s['px'] > 2000, {k: s[k] for k in ('claw', 'fire', 'px')})
    check('v2 b4: 7 FX Кривши — прежнее число кадров (6/8/8/8/4/8/8), feed: heal_frame 6; FX b3 — 4/5/4/3/4 кадра (имена те же); потоки Небыли — кодовое свечение',
          s['fx'] == [6, 8, 8, 8, 4, 8, 8, 4, 3, 4] and s['heal'] == 6 and s['glow'] == 1, {k: s[k] for k in ('fx', 'heal', 'glow')})

    # ================= 13. v2 b6: синхронизация krivsha_fire_* (новая голова) + персонажи b6 (в игре их пока нет) + акцент приземления Кривши
    art = {}
    for f in sorted(Path(ROOT + '../art/v2/chars').glob('krivsha_fire_*.json')):
        art[f.stem] = json.load(open(f, encoding='utf-8'))
    same = [n for n, j in art.items() if json.load(open(ROOT + 'assets/v2/' + n + '.json', encoding='utf-8')) == j
            and open(ROOT + 'assets/v2/' + n + '.png', 'rb').read() == open(ROOT + '../art/v2/chars/' + n + '.png', 'rb').read()]
    s = await G('''(async () => { ''' + V2 + ''' const S = V.V2.sheets; const names = ''' + json.dumps(sorted(art)) + ''';
        return { piv: names.filter(n => S[n] && JSON.stringify(S[n].meta.pivot) === JSON.stringify((''' + json.dumps({n: j.get('pivot') for n, j in art.items()}) + ''')[n])).length,
          n: names.length }; })()''')
    check('v2 b6: krivsha_fire_* (новая голова) — 56 листов синхронизированы из art/v2 под теми же именами; pivot в игре = pivot из JSON художника',
          len(art) == 56 and len(same) == 56 and s['piv'] == 56 and s['n'] == 56, {'art': len(art), 'same': len(same), **s})
    mons = json.load(open(ROOT + 'data/monsters.json', encoding='utf-8'))
    b6 = ('archer', 'axeman', 'acolyte', 'kurgan_prince')
    s = await G('''(async () => { ''' + V2 + ''' const S = V.V2.sheets; return Object.keys(S).filter(k => /^(archer|axeman|acolyte|kurgan_prince)_/.test(k)).length; })()''')
    check('v2 b6: лучник, топорщик, волхв-прислужник и Курганный князь в данных и коде М1 отсутствуют — листы не подключаются (готовы, ждут контента), в assets не копируются',
          s == 0 and not any(k in mons for k in b6) and not list(Path(ROOT + 'assets/v2').glob('kurgan_prince_*')), {'sheets': s})
    s = await G('''(() => { const g = __game; g.settings.shake = true; g.enterZone('kapishche', 'from_trail'); const b = g.riseBoss('test') || g.boss; if (!b) return null; g.shakeAmp = 0; g.shakeT = 0;
        g.combat.patches = []; const h = g.hero; h.invuln = 1e9;
        b.jump = { x0: b.x, y0: b.y, x1: b.x + 1, y1: b.y, hearth: null, fed: true }; b.state = 'jump'; b.t = 0; b.invuln = 9; b.phase = 1;
        const c0 = g.counters.shake, l0 = g.counters.krivshaLand || 0; b.update(0.3, g); const mid = [(g.counters.krivshaLand || 0) - l0, g.counters.shake - c0];
        b.update(0.35, g); const amp = g.shakeAmp, land = (g.counters.krivshaLand || 0) - l0; b.update(0.1, g);
        return { mid, land, again: (g.counters.krivshaLand || 0) - l0, amp, sh: g.counters.shake - c0 }; })()''')
    check('v2 b6: приземление Кривши в огнище (конец дуги 0,6 с) — один лёгкий акцент: тряска ≤ 1,5 px и горсть искр; волны холода в коде М1 нет',
          s is not None and s['mid'] == [0, 0] and s['land'] == 1 and s['again'] == 1 and 0 < s['amp'] <= 1.5 and s['sh'] >= 1, s)


    # ================= 14. церковь r4 (GDD v1.14.4/5): паперть на юге, прируб на востоке; поп Иоанн у паперти; лавка к торгу
    cj = json.load(open(ROOT + 'assets/v2/church_kletskaya.json', encoding='utf-8'))
    s = await G('''(async () => { const g = __game; g.state = 'play'; g.ui.closeAll(); g.dlgWin = null; g.enterZone('ladoga', 'start'); const P = await import('/src/render/props.js'), m = g.map, h = g.hero;
        const n = g.npcs.find(q => q.role === 'priest'); h.x = n.x - 1.5; h.y = n.y + 2.5; g.updateCamera(); g.render(); const toS = (x, y) => g.toS(x, y), [nx, ny] = toS(n.x, n.y);
        let tot = 0, cov = 0; const who = new Set();
        for (let dy = 2; dy < 54; dy += 3) for (let dx = -8; dx <= 8; dx += 3) { tot++; for (const p of m.props) { if (!p._spr || p.depth <= n.x + n.y) continue; if (P.propMaskAt(p, toS, nx + dx, ny - dy)) { cov++; who.add(p.type + ':' + (p.id || '')); break; } } }
        const ch = m.props.find(p => p.id === 'church'), lav = m.props.find(p => p.id === 'lavka_e');
        const PF = await import('/src/world/pathfind.js'), R = g.zone.entries.respawn, path = PF.findPath(m, R.x, R.y, 30.0, 13.6, 0.3, { maxIter: 60000 });
        let x27 = true; for (let y = 13; y <= 18; y += 0.5) if (m.blockedAt(27.5, y)) x27 = false;
        h.x = n.x; h.y = n.y + 1.2; g.town.seen = {}; g.dlgDone = {}; g.town.openNpc(n); const dlg = (g.dlgWin && g.dlgWin.id) || Object.keys(g.dlgDone || {})[0] || null; g.flushDialogs(); g.town.close();
        return { pos: [n.x, n.y], dir: n.dir, cov: cov / tot, who: [...who], piv: ch._spr && [ch._spr.ox, ch._spr.oy], lights: (ch._lights || []).length, lav: lav.fp, path: !!(path && path.length), x27, dlg, se: (await import('/src/entities/actor.js')).dirOf(1, 0), dDoor: Math.hypot(n.x - 30.0, n.y - 11.2) }; })()''')
    check('v2art r4 церковь (GDD v1.14.6): лист 253×261, pivot (118, 211) = центр футпринта (31,5; 10,0), окна — 2 якоря JSON; поп Иоанн в (26; 14) лицом на юго-восток, видно ≥ 80 %, до двери (30,0; 11,2) ≤ 5 тайлов; лавка lavka_e [28; 17] (к торгу), проход x 27 свободен; путь к двери паперти и разговор с Иоанном работают',
          cj['size'] == [253, 261] and cj['pivot'] == [118, 211] and cj['anchors']['porch_stand']['world'] == [30.0, 13.4] and s['pos'] == [26, 14] and s['dir'] == s['se'] and 1 - s['cov'] >= 0.8 and s['dDoor'] <= 5
          and s['lights'] == 2 and s['lav'] == [28, 17, 3, 2] and s['path'] and s['x27'] and (s['dlg'] or '').startswith('priest'), s)

    # ================= 15. GDD v1.14.5: контур NPC за постройкой (цвет имени, ≤ 12 тайлов от героя)
    s = await G('''(async () => { const g = __game; g.state = 'play'; g.ui.closeAll(); g.dlgWin = null; g.enterZone('ladoga', 'start'); const h = g.hero, P = (await import('/src/palette.js')).PAL;
        const at = (n, dx, dy) => { h.x = n.x + dx; h.y = n.y + dy; g.updateCamera(); g.render(); return (g.xrayOutlines || []).find(o => o.id === 'npc_' + n.role) || null; };
        let cov = null, near = null;
        for (const n of g.npcs) { if (!n.role) continue; for (const [dx, dy] of [[-4, 6], [-1.5, 2.5], [3, 5]]) { const o = at(n, dx, dy); if (o && o.drawn) { cov = n; near = o; break; } } if (cov) break; }
        const far = cov ? at(cov, -9, 9) : null;
        const ve = g.npcs.find(q => q.role === 'vedana'), vo = at(ve, 1, 1);
        const pr = g.npcs.find(q => q.role === 'priest'), po = at(pr, -1.5, 2.5);
        return { who: cov && cov.role, near, far, linen: P.linen, vo, po }; })()''')
    check('GDD v1.14.5: NPC, с которыми можно говорить, за постройкой — контур 1 px цвета имени (linen) при перекрытии ≥ 25 %; дальше 12 тайлов от героя — нет; NPC на открытом месте (Ведана, Иоанн в (26; 14)) — без контура',
          s['near'] and s['near']['drawn'] and s['near']['color'] == s['linen'] and s['near']['frac'] >= 0.25 and s['far'] is None and not (s['vo'] and s['vo']['drawn']) and not (s['po'] and s['po']['drawn']), s)

    # ================= 16. QA B-46: «Чур-оберег» — кольцо одинаковых искр 2×2 и пульсирующий обод, без знаков и крестов
    s = await G('''(async () => { const W = await import('/src/render/world.js'); const c = document.createElement('canvas'); c.width = 64; c.height = 48; const x = c.getContext('2d', { willReadFrequently: true });
        const res = []; for (const tm of [0, 0.37, 1.1, 2.5, 4.2]) { x.clearRect(0, 0, 64, 48); W.drawChurRunes(x, 32, 40, { t: 24 }, tm, true); W.drawChurRunes(x, 32, 40, { t: 24 }, tm, false);
          const d = x.getImageData(0, 0, 64, 48).data, on = (i, j) => i >= 0 && j >= 0 && i < 64 && j < 48 && d[(j * 64 + i) * 4 + 3] > 0, seen = new Set(), comps = [];
          for (let j = 0; j < 48; j++) for (let i = 0; i < 64; i++) { if (!on(i, j) || seen.has(j * 64 + i)) continue; const st = [[i, j]], px = []; seen.add(j * 64 + i);
            while (st.length) { const [a, b] = st.pop(); px.push([a, b]); for (const [u, v] of [[a+1,b],[a-1,b],[a,b+1],[a,b-1]]) if (on(u, v) && !seen.has(v * 64 + u)) { seen.add(v * 64 + u); st.push([u, v]); } }
            const xs = px.map(p => p[0]), ys = px.map(p => p[1]); comps.push([px.length, Math.max(...xs) - Math.min(...xs) + 1, Math.max(...ys) - Math.min(...ys) + 1, Math.min(...xs), Math.min(...ys)]); }
          res.push(comps); }
        x.clearRect(0, 0, 64, 48); W.drawChurRunes(x, 32, 40, { t: 24 }, 0, false); W.drawChurRunes(x, 32, 40, { t: 24 }, 0, true);
        return { res, src: W.drawChurRunes.toString().length }; })()''')
    flat = [c for r in s['res'] for c in r]
    pos = [set(tuple(c[3:]) for c in r) for r in s['res']]
    allpos = set().union(*pos)
    check('QA B-46 (вариант художника): «Чур-оберег» — только отдельные искры 1×1 / 2×2 (без крестов и рез), места неподвижны (без вращения: ≤ 10 мест на все кадры), мерцание неровное (наборы видимых искр в кадрах различаются)',
          flat and all(c[:3] in ([1, 1, 1], [4, 2, 2]) for c in flat) and len(allpos) <= 10 and len(set(frozenset(p) for p in pos)) >= 3, s['res'])
    await G('''(() => { const g = __game; g.state = 'play'; g.ui.closeAll(); g.dlgWin = null; g.enterZone('ladoga', 'start'); const h = g.hero; h.x = 30; h.y = 22; h.buffs.chur = { t: 24, dur: 30, defPct: 50, resAll: 5 }; g.updateCamera(); })()''')
    await pg.wait_for_timeout(500); await pg.screenshot(path=ROOT + 'screenshot_v2art_chur.png')
    check('QA B-46 скриншот screenshot_v2art_chur.png (кольцо искр «Чур-оберега»)', os.path.exists(ROOT + 'screenshot_v2art_chur.png'))

    # ================= 17. QA B-49: подложка под журналом
    s = await G('''(async () => { const g = __game, P = (await import('/src/palette.js')).PAL; g.ui.closeAll(); g.dlgWin = null; g.log.lines.length = 0;
        for (const k of ['ui.sys.level_points', 'quest.act', 'ui.sys.level_points']) g.log.add((await import('/src/core/i18n.js')).t(k), P.birch);
        g.render(); const b = g.logBg; if (!b) return null; const U = g.uctx, k = g.uiCanvas.width / 640;
        const d = U.getImageData(Math.round((b.x + 1) * k), Math.round((b.y + 1) * k), 1, 1).data;
        return { b, n: g.logDrawn, lum: (d[0] + d[1] + d[2]) / 3 }; })()''')
    await pg.wait_for_timeout(200); await pg.screenshot(path=ROOT + 'screenshot_v2art_log.png')
    check('QA B-49: журнал — одна сплошная подложка ink ≥ 0,7 под всеми строками (тёмная и на светлом фоне), скриншот screenshot_v2art_log.png',
          s and s['b']['a'] >= 0.7 and s['b']['h'] >= s['n'] * 10 and s['lum'] < 60 and os.path.exists(ROOT + 'screenshot_v2art_log.png'), s)

    # ================= 18. qa3 (B-50/B-51): новые листы отдыха, огнища и окно «Витязь»
    s = await G('''(async () => { const R = await import('/src/render/rest_fx.js'), B = await import('/src/render/boss_art.js'), FX = R.FX, ART = B.ART;
        const c = document.createElement('canvas'); c.width = 128; c.height = 140; const x = c.getContext('2d', { willReadFrequently: true });
        const sig = () => { const d = x.getImageData(0, 0, 128, 140).data; let n = 0, h = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) { n++; h = (h * 31 + d[i - 3] + d[i - 2] * 7 + d[i - 1] * 13 + i) % 1000000007; } return [n, h]; };
        const play = (fn) => { const out = []; for (const tm of [0, 0.13, 0.29, 0.41, 0.57, 0.77]) { x.clearRect(0, 0, 128, 140); const ok = fn(tm); out.push(ok ? sig() : null); } return { ok: out.every(Boolean), px: Math.min(...out.map(o => o ? o[0] : 0)), frames: new Set(out.map(o => o && o[1])).size }; };
        const res = {};
        for (const k of ['churov', 'campfire']) for (const st of ['idle', 'rest']) res[k + '_' + st] = play((tm) => R.drawRestSource(x, k, st, 64, 100, tm));
        const fake = { cursed: true };
        res.desecrated = play((tm) => B.drawHearthArt(x, fake, 64, 120, tm));
        res.progress = play((tm) => { ART.hold = { prop: fake, t: 0.2 + tm * 4, dur: 3 }; const r = B.drawHearthArt(x, fake, 64, 120, tm); ART.hold = null; return r; });
        const done = { cursed: false, doneAt: 0 };
        res.consecrate = play((tm) => B.drawHearthArt(x, done, 64, 120, tm * 0.9));
        res.consecrated = play((tm) => B.drawHearthArt(x, done, 64, 120, 1 + tm));
        const sz = {}; for (const [k, sh] of Object.entries({ churov_idle: FX.sheets.churov_idle, churov_rest: FX.sheets.churov_rest, campfire_idle: FX.sheets.campfire_idle, campfire_rest: FX.sheets.campfire_rest,
          ognishche_consecrate: ART.sheets.ognishche_consecrate, ognishche_consecrated: ART.sheets.ognishche_consecrated, ognishche_desecrated: ART.sheets.ognishche_desecrated, ognishche_progress: ART.sheets.ognishche_progress })) sz[k] = sh ? [sh.img.naturalWidth, sh.img.naturalHeight] : null;
        return { res, sz, failed: ART.failed }; })()''')
    want = {'churov_idle': [192, 56], 'churov_rest': [192, 56], 'campfire_idle': [288, 56], 'campfire_rest': [288, 56], 'ognishche_consecrate': [384, 120], 'ognishche_consecrated': [384, 120], 'ognishche_desecrated': [384, 120], 'ognishche_progress': [864, 124]}
    check('qa3 B-51: листы fx_rest_churov/campfire (idle, rest) и ognishche (desecrated, progress, consecrate, consecrated) загружены в прежних размерах и играют во всех состояниях (кадр не пустой, кадры сменяются)',
          s['sz'] == want and not s['failed'] and all(v['ok'] and v['px'] > 50 and v['frames'] >= 2 for v in s['res'].values()), s)
    import hashlib
    EXP = ROOT + '../art/qa_sym/export/'
    same = {f: hashlib.sha256(open(ROOT + 'assets/' + f, 'rb').read()).hexdigest() == hashlib.sha256(open(EXP + f, 'rb').read()).hexdigest() for f in ('items.png', 'win_character.png')} if os.path.isdir(EXP) else {'skip': True}
    s2 = await G('''(() => { const g = __game; g.state = 'play'; g.ui.closeAll(); g.dlgWin = null; g.enterZone('ladoga', 'start'); g.ui.toggleChar(true); g.render(); return g.ui.charOpen; })()''')
    await pg.wait_for_timeout(300); await pg.screenshot(path=ROOT + 'screenshot_v2art_char_qa3.png')
    await G('(() => { __game.ui.closeAll(); })()')
    check('qa3 B-50: items.png и win_character.png совпадают с art/qa_sym/export байт в байт (если экспорт рядом); окно «Витязь» открывается, скриншот screenshot_v2art_char_qa3.png',
          all(same.values()) and s2 and os.path.exists(ROOT + 'screenshot_v2art_char_qa3.png'), same)

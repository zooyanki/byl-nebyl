# Веха m1l: баг Ильи «ЛКМ по врагу в 2–3 тайлах — герой стоит и машет» (подход и удар по-диабловски, Shift+ЛКМ, удержание ЛКМ),
# B-39 (пути в tools/ относительно репозитория), B-40 (дым над izba_sw / izba_se в Ладоге).
from pathlib import Path
import os, re

ROOT = str(Path(__file__).resolve().parent.parent) + '/'   # корень прототипа от расположения файла
SHOT_APPROACH = ROOT + 'screenshot_m1l_click_approach.png'
SHOT_SMOKE = ROOT + 'screenshot_m1l_smoke.png'

# стенд: Залесье у крады, враги убраны, герой неуязвим; один упырь (много HP, стоит на месте) в dist тайлах на северо-восток.
# Журнал __m1l: каждый замах (startAttack) — по кому, расстояние, досягаемость; каждый heroMelee — попал ли.
STAND = '''(([dist, ang, frozen]) => { const g = __game, h = g.hero; g.dlgAuto = true; g.state = 'play'; g.paused = false; g.ui.closeAll();
  g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; g.notice = null; g.combat.projectiles = [];
  const X = 34, Y = 21; h.x = X; h.y = Y; h.stop(); h.action = null; h.kb = null; h.invuln = 1e9; h.hp = h.maxHp; h.yar = h.maxYar; g.rmbBuf = null; g.dashBuf = null; g.lastTarget = null;
  const e = g.spawnTest('upyr', X + dist * Math.cos(ang), Y + dist * Math.sin(ang), 1); e.state = 'idle'; e.hp = e.maxHp = 1e6;
  if (frozen) { e.stagger = 1e9; e.speed = 0; e.moving = false; e.path = null; }
  g.updateCamera(); g.counters.blockerHits = 0;
  const L = window.__m1l = { sw: [], hits: [], x0: h.x, y0: h.y, e, minD: 1e9 };
  if (!window.__m1lHook) {
    window.__m1lHook = true;
    const P = Object.getPrototypeOf(h), sa = P.startAttack;
    P.startAttack = function (t, s, gm) { const r = sa.call(this, t, s, gm); const L = window.__m1l;
      if (L && this.action && this.action.type === 'attack') L.sw.push({ d: this.distTo(t), reach: this.r + t.r + 0.75, same: t === L.e, moved: Math.hypot(this.x - L.x0, this.y - L.y0), stand: !!(this.cmd && this.cmd.stand) });
      return r; };
    const C = g.combat, hm = C.heroMelee.bind(C);
    C.heroMelee = function (hero, tg, sk) { const L = window.__m1l, hp0 = tg ? tg.hp : 0, rnd = Math.random; Math.random = () => 0.5;   // бросок меткости — попадание без крита
      try { hm(hero, tg, sk); } finally { Math.random = rnd; }
      if (L && tg) L.hits.push({ same: tg === L.e, dmg: hp0 - tg.hp, d: hero.distTo(tg) }); };
  }
  return [e.x, e.y]; })'''
TRACK = '''(() => { const L = window.__m1l, h = __game.hero; L.iv = setInterval(() => { L.minD = Math.min(L.minD, h.distTo(L.e)); }, 16); })()'''
RESULT = '''(() => { const L = window.__m1l, h = __game.hero; clearInterval(L.iv); const r = (v) => +v.toFixed(2);
  return { sw: L.sw.map(s => ({ d: r(s.d), reach: r(s.reach), same: s.same, moved: r(s.moved), stand: s.stand })), hits: L.hits.map(x => ({ same: x.same, dmg: x.dmg, d: r(x.d) })),
    moved: r(Math.hypot(h.x - L.x0, h.y - L.y0)), dEnd: r(h.distTo(L.e)), blk: __game.counters.blockerHits || 0 }; })()'''


async def run_m1l(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1l', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.3')
    await wait(150)

    async def click_enemy(hold_ms=60, shift=False):
        c = await G('(() => { const e = window.__m1l.e; return __game.clientOf(e.x, e.y, 14); })()')
        await pg.mouse.move(c[0], c[1])
        await wait(50)
        hov = await G('__game.hoverEnemy === window.__m1l.e')
        await G(TRACK)
        if shift:
            await pg.keyboard.down('Shift')
        await pg.mouse.down()
        await pg.wait_for_timeout(hold_ms)
        await pg.mouse.up()
        if shift:
            await pg.keyboard.up('Shift')
        return hov

    # ================= 1. ЛКМ по врагу в 1 / 2 / 3 / 5 тайлах: подойти до досягаемости, потом ударить и попасть
    for dist in (1, 2, 3, 5):
        await G(STAND, [dist, -0.785, True])
        await wait(150)
        hov = await click_enemy()
        await wait(int(1500 + dist * 260))
        s = await G(RESULT)
        sw = s['sw']
        first = sw[0] if sw else None
        out_of_reach = [x for x in sw if x['d'] > x['reach'] + 0.02]
        need = max(0, dist - 1.35)
        ok = (hov and first and first['same'] and not out_of_reach and not first['stand'] and first['moved'] >= need - 0.15
              and s['hits'] and s['hits'][0]['same'] and s['hits'][0]['dmg'] > 0 and s['blk'] == 0)
        check(f'm1l баг ЛКМ: враг в {dist} тайл. — герой подходит до досягаемости (v1.14 E1: зазор ≤ reach 0,75), затем бьёт и попадает; замахов вне досягаемости нет',
              ok, {'hover': hov, 'first': first, 'outOfReach': out_of_reach, 'hits': s['hits'][:2], 'moved': s['moved'], 'blk': s['blk']})

    # ================= 2. Соседи по стае сбоку от пути и цель, которая сама отходит, — не «заслон»
    s = await G('''(async () => { const g = __game, h = g.hero; (''' + STAND + ''')([3.2, 0, true]); const L = window.__m1l, e = L.e;
        // два соседа цели: через 0,3 с пути они в секторе ±60° и в 1,6 тайла от героя, но сбоку от отрезка герой → цель (не на пути)
        const n1 = g.spawnTest('upyr', h.x + 2.3, h.y + 1.25, 1), n2 = g.spawnTest('upyr', h.x + 2.3, h.y - 1.25, 1);
        for (const n of [n1, n2]) { n.state = 'idle'; n.stagger = 1e9; n.speed = 0; n.hp = n.maxHp = 1e6; }
        h.attack(e, false, h.lmbSkill(), true); const v = h.speed; let tt = 0;
        // цель отходит со скоростью героя (как анчутка, что держит дистанцию) — расстояние к ней не сокращается (до m1l это включало «заслон»)
        g.simulate(1.0, () => { tt += 1 / 60; e.x += v / 60; return false; });
        const side = { blk: g.counters.blockerHits || 0, swOther: L.sw.filter(s => !s.same).length, moved: +Math.hypot(h.x - L.x0, h.y - L.y0).toFixed(2) };
        return side; })()''')
    check('m1l заслон не путается: соседи сбоку от пути (в секторе ±60°, 1,6 тайла) и отходящая цель — герой идёт за целью, по соседям не бьёт',
          s['blk'] == 0 and s['swOther'] == 0 and s['moved'] >= 3.5, s)

    # ================= 3. Shift+ЛКМ — удар на месте (как и было): замах сразу, герой не сходит с места
    await G(STAND, [3, -0.785, True])
    await wait(150)
    hov = await click_enemy(shift=True)
    await wait(500)
    s = await G(RESULT)
    check('m1l Shift+ЛКМ по врагу в 3 тайлах — замах на месте без подхода (стоячая атака сохранена)',
          hov and s['sw'] and s['sw'][0]['stand'] and s['sw'][0]['moved'] < 0.05 and s['moved'] < 0.05 and not [x for x in s['hits'] if x['dmg'] > 0], s)

    # ================= 4. Удержание ЛКМ на враге в 3 тайлах: подход, затем удары подряд, все — в досягаемости
    await G(STAND, [3, 2.356, True])
    await wait(150)
    hov = await click_enemy(hold_ms=2600)
    await wait(200)
    s = await G(RESULT)
    oor = [x for x in s['sw'] if x['d'] > x['reach'] + 0.02]
    check('m1l удержание ЛКМ на враге в 3 тайлах — подход, затем ≥ 2 удара подряд; все замахи в досягаемости, все по цели',
          hov and len(s['sw']) >= 2 and not oor and all(x['same'] for x in s['sw']) and s['sw'][0]['moved'] >= 1.4 and sum(1 for x in s['hits'] if x['dmg'] > 0) >= 2, s)

    # ================= 5. Подвижный враг (в агро): клик в 3 тайлах — замах только в досягаемости
    await G(STAND, [3, 0.4, False])
    await wait(100)
    hov = await click_enemy()
    await wait(1600)
    s = await G(RESULT)
    oor = [x for x in s['sw'] if x['d'] > x['reach'] + 0.02]
    check('m1l враг в агро в 3 тайлах (идёт навстречу) — первый замах по нему и в досягаемости, попадание',
          hov and s['sw'] and s['sw'][0]['same'] and not oor and any(x['dmg'] > 0 and x['same'] for x in s['hits']), s)

    # снимок: герой на полпути к упырю после клика (5 тайлов)
    await G(STAND, [5, -0.785, True])
    await wait(150)
    await click_enemy()
    for _ in range(60):
        d = await G('(() => { const h = __game.hero, e = window.__m1l.e; return [h.distTo(e), !!h.moving, !!h.action]; })()')
        if d[1] and not d[2] and 2.2 <= d[0] <= 3.6:
            break
        await pg.wait_for_timeout(15)
    await G('(() => { __game.simHold = true; })()')
    await pg.wait_for_timeout(60)
    await pg.screenshot(path=SHOT_APPROACH)
    await G('(() => { __game.simHold = false; })()')
    check('m1l скриншот screenshot_m1l_click_approach.png: герой на подходе к упырю после клика (идёт, не машет)',
          os.path.exists(SHOT_APPROACH) and d[1] and not d[2] and 2.0 <= d[0] <= 3.8, {'dist': round(d[0], 2), 'moving': d[1], 'action': d[2]})

    # ================= B-40. Дым: у каждой постройки smokeKinds в Ладоге дым рисуется, у прочих — нет
    s = await G('''(async () => { const g = __game, h = g.hero; g.dlgAuto = true; g.state = 'play'; g.paused = false; g.ui.closeAll();
        g.quest.flags.vyshataIntro = true; g.flushDialogs && g.flushDialogs(); g.dlgQueue = []; g.enterZone('ladoga', 'from_zalesye'); g.enemies = []; g.notice = null; h.invuln = 1e9; h.stop();
        const P = await import('/src/render/props.js'); const K = g.zone.smokeKinds || [];
        const bld = g.map.props.filter(p => P.bldSheet && P.bldSheet(p));
        await new Promise(r => setTimeout(r, 300));
        // каждую постройку — в кадр (камера за героем у её футпринта) и отрисовать: _smoked ставит drawBld
        g.simHold = true;
        for (const p of bld) { const fp = p.fp || [p.x, p.y, 1, 1]; h.x = fp[0] + fp[2] + 1.5; h.y = fp[1] + fp[3] + 1.5; g.updateCamera(); p._smoked = undefined; g.render(); }
        g.simHold = false;
        const row = (p) => ({ id: p.id || p.type, kind: p.type, variant: p.variant || null, smoke: !!p.smoke, drawn: p._smoked, src: p._smokeSrc || null });
        const smokers = bld.filter(p => K.includes(p.type)).map(row), others = bld.filter(p => !K.includes(p.type)).map(row);
        const kon = await (await fetch('/assets/bld/bld_izba_small_tes_kon.json')).json(), pr = await (await fetch('/assets/bld/bld_izba_small_tes_prich.json')).json();
        const meta = (j) => j.meta || j;
        return { K, smokers, others, noAnchor: [!meta(kon).anchors_px.smoke, !meta(pr).anchors_px.smoke] }; })()''')
    sm = {x['id']: x for x in s['smokers']}
    check('m1l B-40 дым: все постройки видов smokeKinds в Ладоге дымят (в т. ч. izba_sw / izba_se — точка gable_vent: в листах tes_kon / tes_prich нет anchors_px.smoke); у остальных дыма нет',
          s['K'] == ['izba', 'izba_seni', 'izba_podklet', 'banya'] and s['smokers'] and all(x['drawn'] for x in s['smokers'])
          and all(x['drawn'] is False for x in s['others']) and sm.get('izba_sw', {}).get('src') == 'gable_vent' and sm.get('izba_se', {}).get('src') == 'gable_vent'
          and all(s['noAnchor']), {'smokers': s['smokers'], 'othersDrawn': [x['id'] for x in s['others'] if x['drawn']]})
    # снимок: герой между izba_sw и izba_se (обе крыши с дымником в кадре)
    vis = await G('''(() => { const g = __game, h = g.hero; h.x = 19.5; h.y = 30.5; h.stop(); g.log.lines = []; g.updateCamera && g.updateCamera();
        return g.map.props.filter(p => p.id === 'izba_sw' || p.id === 'izba_se').map(p => g.clientOf(p.fp[0] + 2, p.fp[1] + 2, 90).map(Math.round)); })()''')
    await wait(700)
    await pg.screenshot(path=SHOT_SMOKE)
    check('m1l скриншот screenshot_m1l_smoke.png: izba_sw и izba_se дымят (обе в кадре)',
          os.path.exists(SHOT_SMOKE) and len(vis) == 2 and all(0 < x < 1920 and 0 < y < 1080 for x, y in vis), vis)

    # ================= B-39. tools/: нет абсолютных путей /workspace/ (вне прототипа — только относительно корня)
    bad = []
    for f in sorted(Path(ROOT, 'tools').glob('*.py')):
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if '/workspace/' in line and f.name != 'checks_m1l.py':
                bad.append(f'{f.name}:{i}')
    lay = Path(ROOT, 'tools', 'ladoga_layout_json.py').read_text(encoding='utf-8')
    check('m1l B-39: в tools/*.py нет «/workspace/»; корень — Path(__file__).resolve().parent.parent, скрипт дизайнера — <корень>/../../gamedesign или BYL_GAMEDESIGN',
          not bad and 'Path(__file__).resolve().parent.parent' in lay and 'BYL_GAMEDESIGN' in lay, bad[:10])

    await run_v114(pg, G, check, wait, client_of, client_scr, a)


# ===================================================================== GDD v1.14: E1–E4
SHOT_BLOCK = ROOT + 'screenshot_m1l_block.png'
SHOT_ZMEY = ROOT + 'screenshot_m1l_zmey_e.png'
SHOT_ENTRY = ROOT + 'screenshot_m1l_zalesye_entry.png'
SHOT_TRANS = ROOT + 'screenshot_m1l_block_transition.png'

# стенд v1.14: Залесье у крады, врагов нет, герой с щитом (стартовый), Удаль полна, щит опущен
BASE = '''const g = __game, h = g.hero; g.dlgAuto = true; g.state = 'play'; g.paused = false; g.ui.closeAll();
  g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; g.notice = null; g.combat.projectiles = []; g.combat.fires = []; g.combat.teles = [];
  h.recalc(); h.x = 34; h.y = 21; h.stop(); h.action = null; h.kb = null; h.dashing = null; h.invuln = 0; h.stun = 0; h.cds = {}; h.hp = h.maxHp; h.yar = h.maxYar;
  h.blockWant = null; h.blockSt = null; h.blockCd = 0; h.lowerT = h.breakT = h.blockHitT = null; g.rmbBuf = null; g.dashBuf = null; g.blockHeld = false; g.lastTarget = null; g.settings.shake = true;
  const step = (n) => { for (let i = 0; i < n; i++) { g.update(1 / 60); g.input.endFrame(); } };
  step(2); g.updateCamera();'''


async def run_v114(pg, G, check, wait, client_of, client_scr, a):
    print('--- v1.14 (E1–E4)', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.3')
    await wait(150)

    # ================= E1: автотест дизайнера (gamedesign/work/e1/e1_autotest.js, копия tools/e1_autotest.js) — 4 случая
    r = await G(Path(ROOT, 'tools', 'e1_autotest.js').read_text(encoding='utf-8'))
    for c in r['checks']:
        check('v1.14 ' + c['id'], c['pass'], {k: v for k, v in c.items() if k not in ('id', 'pass')})

    # E1: досягаемость по зазору (stats.melee), отмена взмаха — Удаль возвращается, после 2 отмен подряд приказ снимается
    s = await G('''(() => { ''' + BASE + '''
        const M = g.dbg.CFG.stats.melee, e = g.spawnTest('anchutka', 35.2, 21, 1); e.state = 'idle'; e.stagger = 1e9; e.speed = 0; e.hp = e.maxHp = 1e6;
        const yr = h.yarRegen; h.yarRegen = 0; const y0 = h.yar, c0 = g.counters.swingCancel || 0, d0 = g.counters.chaseDropped || 0;
        const SK = g.dbg.SKILLS.sshibka, c0s = SK.cost; SK.cost = [2, 0];   // «Сшибка» в данных сейчас бесплатна — для проверки возврата ставим цену 2 на время теста
        h.lmb = 'sshibka'; h.attack(e, false, 'sshibka', true); let gapAtSwing = null, paidMax = 0, frames = 0;
        for (let f = 0; f < 600 && h.cmd; f++) { step(1); frames++; const A = h.action;
          if (A && A.type === 'attack' && !A.fired) { if (gapAtSwing == null) gapAtSwing = +h.gapTo(e).toFixed(2); paidMax = Math.max(paidMax, y0 - h.yar);
            if (A.t > 0.1) { const dx = e.x - h.x, dy = e.y - h.y, d = Math.hypot(dx, dy) || 1; e.x += dx / d * 1.6; e.y += dy / d * 1.6; } } }
        const out = { M, gapAtSwing, paidMax: +paidMax.toFixed(2), yarBack: +(y0 - h.yar).toFixed(2), cancels: (g.counters.swingCancel || 0) - c0, dropped: (g.counters.chaseDropped || 0) - d0, cmd: !!h.cmd, t: +(frames / 60).toFixed(2) };
        h.yarRegen = yr; SK.cost = c0s; return out; })()''')
    check('v1.14 E1: stats.melee reach 0,75 / slack 0,55 / cancelChase 2 / cancelMax 2; взмах начат при зазоре ≤ reach; цель ушла — взмах снят, Удаль возвращена; после 3-й отмены приказ снят (ЛКМ не зажата)',
          s['M']['reach'] == 0.75 and s['M']['slack'] == 0.55 and s['M']['cancelChase'] == 2 and s['M']['cancelMax'] == 2
          and s['gapAtSwing'] is not None and s['gapAtSwing'] <= 0.75 + 0.02 and s['paidMax'] > 0 and s['yarBack'] == 0 and s['cancels'] == 3 and s['dropped'] == 1 and not s['cmd'], s)

    # ================= E2: правила блока (числа §4.7) — прямые вызовы takeDamage со стойкой
    s = await G('''(() => { ''' + BASE + '''
        const B = g.dbg.CFG.stats.block, rnd = Math.random; Math.random = () => 0.99;   // пассивный блок не срабатывает
        const e = g.spawnTest('upyr', 35, 21, 1); e.state = 'idle'; e.stagger = 1e9; e.speed = 0; e.hp = e.maxHp = 1e6;
        const out = { B, shield: h.hasShield(), lhand: h.equip.lhand && h.equip.lhand.type };
        h.blockWant = { x: 36, y: 21 }; step(6); out.up010 = h.blocking; step(6); out.up020 = h.blocking;
        const hit = (amt, opts, att = e, type = 'melee') => { h.invuln = 0; h.stun = 0; h.hp = h.maxHp; h.yar = h.maxYar; if (!h.blockSt) { h.blockCd = 0; step(12); }
          const y0 = h.yar, b0 = g.counters.blocked || 0, hs0 = g.counters.hitStop || 0, sh0 = g.counters.shake || 0, p0 = g.fx.parts.length; const d = h.takeDamage(amt, g, type, att, opts);
          return { d, yar: +(y0 - h.yar).toFixed(2), blk: (g.counters.blocked || 0) - b0, stun: +h.stun.toFixed(2), hs: (g.counters.hitStop || 0) - hs0, sh: (g.counters.shake || 0) - sh0, sparks: g.fx.parts.length - p0, up: !!h.blockSt }; };
        const pb = h.block;
        h.block = 0; out.front = hit(40, { src: 'melee', from: [35, 21] });
        out.txt = g.fx.texts.slice(-3).map(t => t.str).find(x => x === 'Блок') || g.fx.texts.slice(-3).map(t => t.str).join('|');
        h.block = 0.15; out.p15 = hit(40, { src: 'melee', from: [35, 21] });
        h.block = 0.30; out.cap = hit(40, { src: 'melee', from: [35, 21] });
        h.block = 0; out.heavy = hit(40, { src: 'melee', from: [35, 21], heavy: true });
        out.back = hit(40, { src: 'melee', from: [33, 21] });
        out.side = hit(40, { src: 'melee', from: [34, 22] });
        out.proj = hit(40, { src: 'proj', from: [37, 21] }, null, 'melee');
        out.ground = hit(40, {}, null, 'fire');
        out.big = hit(Math.round(h.maxHp * 0.5), { src: 'melee', from: [35, 21] });
        h.yar = 20; step(60); out.regen = +(h.yar - 20).toFixed(2); out.speed = +(h.curSpeed() / (h.speed * (h.slowT > 0 ? 1 - (h.slowPct || 0) / 100 : 1))).toFixed(2);
        // пробитие: Удали меньше цены — удар полностью, щит опущен, откат 1,5 с, оглушение 0,3 с; «Щит пробит»
        h.invuln = 0; h.hp = h.maxHp; h.stun = 0; h.yar = 1; const gb0 = g.counters.guardBreak || 0, sh0 = g.counters.shake || 0, p0 = g.fx.parts.length; const dB = h.takeDamage(40, g, 'melee', e, { src: 'melee', from: [35, 21] });
        out.brk = { d: dB, up: !!h.blockSt, cd: +h.blockCd.toFixed(2), stun: +h.stun.toFixed(2), n: (g.counters.guardBreak || 0) - gb0, shake: (g.counters.shake || 0) - sh0, sparks: g.fx.parts.length - p0, txt: g.fx.texts.slice(-3).map(t => t.str).find(x => x === 'Щит пробит') || g.fx.texts.slice(-3).map(t => t.str).join('|') };
        h.yar = h.maxYar; step(60); out.brk.upAt1 = !!h.blockSt; step(45); out.brk.upAt175 = h.blocking;
        // рывок опускает щит; во время замаха (до кадра удара) щит не поднять, после удара — хвост обрезается
        h.dash(g, 30, 21); out.dashUp = !!h.blockSt; h.dashing = null; h.cds = {}; h.blockWant = null; step(2);
        h.x = 34; h.y = 21; e.x = 35; e.y = 21; h.attack(e, false, null, true); for (let f = 0; f < 60 && !(h.action && h.action.type === 'attack'); f++) step(1);
        h.blockWant = { x: 36, y: 21 }; step(2); out.duringSwing = !!h.blockSt; for (let f = 0; f < 90 && h.action && !h.action.fired; f++) step(1); step(2); out.afterHit = !!h.blockSt && !h.action;
        // ЛКМ со щитом — приказ ждёт; после отпускания — бьёт
        h.stop(); h.action = null; step(12); const sw0 = g.counters.swings || 0; let swungWhile = 0; h.attack(e, false, null, true); for (let f = 0; f < 60; f++) { step(1); if (h.action && h.action.type === 'attack') swungWhile++; }
        out.lmbWhileBlock = swungWhile; h.blockWant = null; let swungAfter = 0; for (let f = 0; f < 60; f++) { step(1); if (h.action && h.action.type === 'attack') swungAfter++; } out.lmbAfter = swungAfter > 0;
        h.block = pb; h.recalc(); Math.random = rnd; return out; })()''')
    B = s['B']
    check('v1.14 E2: stats.block — raise 0,15, сектор 120°, снижение 50% (кап 75%), цена 2, тяжёлые не держит (heavyBlock false), бег × 0,5, откат 1,5 с, оглушение 0,3 с, реген Удали стоит; стартовый щит в шуйце',
          B['raise'] == 0.15 and B['sectorDeg'] == 120 and B['reduceBase'] == 50 and B['reduceCap'] == 75 and B['cost'] == 2 and B['heavyBlock'] is False
          and B['speedMul'] == 0.5 and B['breakCd'] == 1.5 and B['breakStun'] == 0.3 and B['regen'] is False and s['shield'] and s['lhand'] == 'shield', s)
    check('v1.14 E2: щит держит через 0,15 с после нажатия (0,1 с — ещё нет)', not s['up010'] and s['up020'], {k: s[k] for k in ('up010', 'up020')})
    check('v1.14 E2: удар спереди 40 → 20 (−50%), 2 Удали; пассивный 15% → 14 (−65%); 30% → кап 75% → 10; тяжёлый (когти Кривши, heavy) — щит не держит: 40, Удаль не тратится',
          s['front']['d'] == 20 and s['front']['yar'] == 2 and s['p15']['d'] == 14 and s['cap']['d'] == 10 and s['heavy']['d'] == 40 and s['heavy']['yar'] == 0 and s['heavy']['blk'] == 0,
          {k: s[k] for k in ('front', 'p15', 'cap', 'heavy')})
    check('v1.14 E2: со спины и сбоку (вне ±60°) — полный урон, Удаль не тратится; снаряд спереди — −50%; огонь на земле (src ground) — полный',
          s['back']['d'] == 40 and s['back']['yar'] == 0 and s['side']['d'] == 40 and s['side']['yar'] == 0 and s['proj']['d'] == 20 and s['proj']['blk'] == 1
          and s['ground']['blk'] == 0 and s['ground']['yar'] == 0 and s['ground']['d'] >= 30, {k: s[k] for k in ('back', 'side', 'proj', 'ground')})
    check('v1.14 E2: принятый удар — «Блок», хит-стоп, ≥ 6 искр, без тряски; удар в 25% HP в щит не оглушает и щит не опускает',
          s['txt'] == 'Блок' and s['front']['hs'] == 1 and s['front']['sparks'] >= 6 and s['front']['sh'] == 0 and s['big']['blk'] == 1 and s['big']['stun'] == 0 and s['big']['up'],
          {'txt': s['txt'], 'front': s['front'], 'big': s['big']})
    check('v1.14 E2: пока щит поднят, Удаль не восполняется; бег × 0,5', s['regen'] == 0 and s['speed'] == 0.5, {k: s[k] for k in ('regen', 'speed')})
    check('v1.14 E2: пробитие (Удали 1 < 2) — удар полностью, щит опущен, откат 1,5 с, оглушение 0,3 с, «Щит пробит», 10 искр, тряска; через 1 с щит ещё не поднят, через 1,75 с — снова держит',
          s['brk']['d'] == 40 and not s['brk']['up'] and s['brk']['cd'] == 1.5 and s['brk']['stun'] == 0.3 and s['brk']['n'] == 1 and s['brk']['txt'] == 'Щит пробит'
          and s['brk']['sparks'] >= 10 and s['brk']['shake'] == 1 and not s['brk']['upAt1'] and s['brk']['upAt175'], s['brk'])
    check('v1.14 E2: рывок опускает щит; в замахе до кадра удара щит не поднимается, после удара — поднимается и обрезает хвост; ЛКМ со щитом не бьёт, после отпускания — бьёт',
          not s['dashUp'] and not s['duringSwing'] and s['afterHit'] and s['lmbWhileBlock'] == 0 and s['lmbAfter'],
          {k: s[k] for k in ('dashUp', 'duringSwing', 'afterHit', 'lmbWhileBlock', 'lmbAfter')})

    # E2: настоящий ввод — ПКМ (держать) поднимает щит к курсору; E со щитом запоминается и срабатывает после отпускания; без щита — ui.error.no_shield раз в 1,2 с
    await G('''(() => { ''' + BASE + ''' window.__nt = []; if (!g.__ntHook) { g.__ntHook = true; const n0 = g.notify.bind(g); g.notify = (txt, c, key, d) => { window.__nt.push([key, txt]); return n0(txt, c, key, d); }; }
        window.__snd = []; if (!g.__sndHook) { g.__sndHook = true; const p0 = g.audio.play.bind(g.audio); g.audio.play = (k, ...r) => { window.__snd.push(k); return p0(k, ...r); }; } h.rmb = 'zmey'; })()''')
    await wait(100)
    await pg.mouse.move(*(await client_of(37, 21)))
    await wait(60)
    z0 = await G('__game.counters.casts.zmey || 0')
    await pg.mouse.down(button='right')
    await wait(350)
    st = await G('''(() => { const g = __game, h = g.hero, B = h.blockSt; return { up: h.blocking, dx: B && +B.dx.toFixed(2), slot: g._shieldSlot, arc: g._blockArcDrawn || 0 }; })()''')
    await pg.keyboard.press('KeyE')
    await wait(250)
    mid = await G('({ z: __game.counters.casts.zmey || 0, buf: !!__game.rmbBuf, up: __game.hero.blocking })')
    await pg.mouse.up(button='right')
    await wait(700)
    aft = await G('({ z: __game.counters.casts.zmey || 0, up: !!__game.hero.blockSt, slot: __game._shieldSlot })')
    check('v1.14 E2/E3: ПКМ (держать) — щит к курсору (слот щита «поднят», дуга на земле), ПКМ навык не применяет; E со щитом запомнен и вылетает после отпускания ПКМ',
          st['up'] and st['dx'] > 0.9 and st['slot'] == 'raised' and st['arc'] > 0 and mid['z'] == z0 and mid['buf'] and mid['up'] and aft['z'] == z0 + 1 and not aft['up'] and aft['slot'] == 'ready',
          {'held': st, 'mid': mid, 'after': aft, 'z0': z0})
    await G('''(() => { const g = __game, h = g.hero; window.__lh = h.equip.lhand; h.equip.lhand = null; h.recalc(); window.__nt.length = 0; window.__snd.length = 0; g.noShieldT = 0; })()''')
    n0 = await G('__game.counters.noShield || 0')
    for _ in range(3):
        await pg.mouse.down(button='right'); await wait(40); await pg.mouse.up(button='right'); await wait(120)
    ns = await G('''(() => { const g = __game, h = g.hero; const r = { n: g.counters.noShield || 0, notes: window.__nt.filter(x => x[0] === 'noshield').map(x => x[1]), err: window.__snd.filter(k => k === 'error').length, up: !!h.blockSt, slot: g._shieldSlot };
        h.equip.lhand = window.__lh; h.recalc(); return r; })()''')
    check('v1.14 E2: без щита в шуйце ПКМ — «Без щита не прикрыться.» (ui.error.no_shield) и звук ошибки раз в 1,2 с (3 нажатия — 1 сообщение), слот щита серый',
          ns['n'] == n0 + 3 and len(ns['notes']) == 1 and ns['notes'][0] == 'Без щита не прикрыться.' and ns['err'] == 1 and not ns['up'] and ns['slot'] == 'none', ns)

    # E2: справочно — функциональный тест дизайнера (e2_func): упырь спереди со щитом / без, со спины, огонь на земле, уголь анчутки
    s = await G('''(async () => { const r = await (async () => { const g = __game; const out = {};
      const stand = () => { const h = g.hero; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = []; g.combat.projectiles = []; g.combat.fires = [];
        h.x = 34; h.y = 21; h.stop(); h.action = null; h.invuln = 0; h.hp = h.maxHp; h.yar = h.maxYar; h.blockWant = null; h.blockSt = null; h.blockCd = 0; for (let i = 0; i < 3; i++) { g.update(1/60); g.input.endFrame(); } return h; };
      const step = (n) => { for (let i = 0; i < n; i++) { g.update(1 / 60); g.input.endFrame(); } };
      let h = stand(); let e = g.spawnTest('upyr', 35, 21, 1); e.hp = e.maxHp = 999; e.aggro(g, false); h.maxHp = 1e4; h.hp = 1e4; h.blockWant = { x: 35, y: 21 }; const b0 = g.counters.blocked || 0, hp0 = h.hp; step(900);
      out.melee = { blocked: (g.counters.blocked || 0) - b0, hpLost: hp0 - h.hp };
      h = stand(); e = g.spawnTest('upyr', 35, 21, 1); e.hp = e.maxHp = 999; e.aggro(g, false); h.maxHp = 1e4; h.hp = 1e4; const hp1 = h.hp; step(900); out.noBlock = { hpLost: hp1 - h.hp };
      h = stand(); e = g.spawnTest('anchutka', 37, 21, 1); e.hp = e.maxHp = 999; e.aggro(g, false); h.blockWant = { x: 37, y: 21 }; const k0 = g.counters.blocked || 0; step(360); out.coal = { blocked: (g.counters.blocked || 0) - k0 };
      h.blockWant = null; h.recalc(); h.hp = h.maxHp; return out; })(); return r; })()''')
    check('v1.14 E2 (e2_func дизайнера): упырь спереди 15 с — со щитом урона меньше, чем без; уголь анчутки спереди принят в щит',
          s['melee']['blocked'] >= 1 and s['melee']['hpLost'] < s['noBlock']['hpLost'] and s['coal']['blocked'] >= 1, s)

    # ================= E3: E — навык (зажать — повтор), F-клавиша назначает на E, HUD/справка/подсказки, сохранение поля e
    await G('''(() => { ''' + BASE + ''' h.rmb = 'zmey'; window.__nt.length = 0; })()''')
    await pg.mouse.move(*(await client_of(38, 21)))
    await wait(60)
    z0 = await G('({ z: __game.counters.casts.zmey || 0, y: __game.hero.yar })')
    await pg.keyboard.press('KeyE')
    await wait(400)
    z1 = await G('({ z: __game.counters.casts.zmey || 0, y: __game.hero.yar })')
    await G('__game.hero.yar = __game.hero.maxYar')
    await pg.keyboard.down('KeyE')
    await wait(2000)
    await pg.keyboard.up('KeyE')
    z2 = await G('__game.counters.casts.zmey || 0')
    check('v1.14 E3: E — «Огненный змей» в точку под курсором (Удаль тратится); зажатая E повторяет (≥ 2 змея за 2 с)',
          z1['z'] == z0['z'] + 1 and z1['y'] < z0['y'] and z2 - z1['z'] >= 2, {'before': z0, 'after': z1, 'held': z2 - z1['z']})
    s = await G('''(async () => { const g = __game, h = g.hero, H = await import('/src/render/hud.js'), S = await import('/src/render/screens.js'), Sv = await import('/src/systems/save.js'), t = g.dbg.t, F = await import('/src/core/font.js');
        const L = H.LAYOUT; window.__nt.length = 0; const k = h.bar.findIndex(id => id && id !== 'zmey' && g.dbg.rankOf(h, id) && g.dbg.SKILLS[id].type !== 'passive');
        let fset = null; if (k >= 0) { g.pressF(k); fset = { id: h.rmb, note: (window.__nt.find(x => x[0] === 'rmb') || [])[1] }; } h.setRmb('zmey');
        const snap = Sv.snapshot(g), old = JSON.parse(JSON.stringify(snap)); delete old.hero.e; old.hero.rmb = 'chur';
        const hr = h.rmb; const keep = { inv: h.inv }; let loaded = null; try { h.rmb = 'zmey'; Sv.applySave(g, old); loaded = h.rmb; } catch (e) { loaded = 'ERR ' + e; } h.rmb = hr;
        g.paused = true; g.render(); const lines = g.pauseLines; g.paused = false;
        return { rmb: L.rmb, dash: L.dash, shield: L.shield, silver: L.silver, e: t('proto.hud.e'), slotAt: H.hudSlotAt(515, 350), fset, saveE: snap.hero.e, saveRmb: snap.hero.rmb === undefined ? null : snap.hero.rmb,
          loaded, lines, hintW: F.textWidth(t('proto.hud.ctrl_hint')), helpW: Math.max(...lines.map(l => F.textWidth(l[1]))), hint: t('proto.hud.ctrl_hint'), skHint: t('proto.skills.hint'), toE: t('ui.skills.to_e'), def: g.dbg.SKILLS.zmey.defaultSlot }; })()''')
    check('v1.14 E3/§10 HUD: большой правый слот (32×32, x 454) — подпись «E»; слот рывка (488; 342); слот щита 18×18 (509; 342); серебро x 530, ширина 40',
          s['rmb']['x'] == 454 and s['rmb']['s'] == 32 and s['e'] == 'E' and s['dash']['x'] == 488 and s['dash']['y'] == 342
          and s['shield'] == {'x': 509, 'y': 342, 's': 18} and s['silver']['x'] == 530 and s['silver']['w'] == 40 and s['slotAt'] == {'kind': 'shield'},
          {k: s[k] for k in ('rmb', 'dash', 'shield', 'silver', 'e', 'slotAt')})
    rows = {a_: b_ for a_, b_ in s['lines']}
    check('v1.14 E3: F-клавиша назначает навык на E («E: …»); справка паузы — «E» навык и «ПКМ (держать)» щит; подсказки управления и окна навыков — про E и ПКМ-щит, влезают (подсказка ≤ 630 px, справка ≤ 204 px); zmey defaultSlot «E»',
          (s['fset'] is None or (s['fset']['note'] or '').startswith('E: ')) and 'E' in rows and any(k.startswith('ПКМ') and 'щит' in v for k, v in rows.items())
          and 'E — навык' in s['hint'] and 'ПКМ — щит' in s['hint'] and 'на E' in s['skHint'] and s['toE'] == 'Назначить на E' and s['def'] == 'E' and len(s['lines']) == 12 and s['hintW'] <= 630 and s['helpW'] <= 204,
          {k: s[k] for k in ('fset', 'lines', 'hint', 'skHint', 'def', 'hintW', 'helpW')})
    check('v1.14 E3: сохранение — навык слота E пишется в поле hero.e (rmb нет), старый слот с hero.rmb читается в E (навык не теряется)',
          s['saveE'] == 'zmey' and s['saveRmb'] is None and s['loaded'] == 'chur', {k: s[k] for k in ('saveE', 'saveRmb', 'loaded')})

    # E3 / §12.2.4: обучение и строки — «E — навык» при первом входе в Залесье, «ПКМ — держать щит» при первом ударе врага; в ru.json нет «ПКМ» как кнопки навыка
    s = await G('''(() => { const g = __game, h = g.hero; g._tutSkillE = false; g._tutBlock = false; window.__nt.length = 0; delete g.zoneStates.zalesye;
        g.enterZone('ladoga', 'start'); g.enterZone('zalesye', 'from_ladoga'); const a = window.__nt.filter(x => x[0] === 'tut').map(x => x[1]);
        const e = g.spawnTest('upyr', h.x + 1, h.y, 1); h.invuln = 0; h.takeDamage(1, g, 'melee', e, { src: 'melee', from: [e.x, e.y] }); g.enemies = [];
        const b = window.__nt.filter(x => x[0] === 'tut').map(x => x[1]); return { a, b, skE: g.dbg.t('ui.tut.skill_e'), blk: g.dbg.t('ui.tut.block') }; })()''')
    import json as _json
    ru = _json.loads(Path(ROOT, 'data', 'ru.json').read_text(encoding='utf-8'))
    bad_ru = [k for k, v in ru.items() if isinstance(v, str) and re.search(r'ПКМ — навык|на ПКМ|ПКМ: |Урон ПКМ', v)]
    gone = [k for k in ('ui.tut.rmb', 'ui.skills.to_rmb', 'proto.hud.rmb', 'proto.help.rmb', 'proto.help.rmb.key', 'proto.sys.rmb_set', 'proto.hero.dmg_rmb') if k in ru]
    check('v1.14 §12.2.4: при первом входе в Залесье — «E — навык…» (ui.tut.skill_e), при первом ударе врага по герою со щитом — ui.tut.block; в ru.json нет «ПКМ» как кнопки навыка, старые ключи сняты; есть tip.15',
          s['a'] == [s['skE']] and s['b'] == [s['skE'], s['blk']] and s['skE'].startswith('E — навык') and s['blk'].startswith('ПКМ') and not bad_ru and not gone and 'tip.15' in ru,
          {'tut': s, 'badRu': bad_ru, 'oldKeys': gone})

    # ================= E4: Ладога ↔ Залесье по одной тропе
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.3')
    await wait(150)
    s = await G('''(() => { const g = __game, h = g.hero; g.dlgAuto = true; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.quest.flags.vyshataIntro = true;
        const dirOf = (fx, fy) => { const d0 = h.dir, f0 = h.facing; h.face(fx, fy); const d = h.dir; h.dir = d0; h.facing = f0; return d; };
        delete g.zoneStates.zalesye; g.enterZone('ladoga', 'start'); g.enterZone('zalesye', 'from_ladoga');
        const m = g.map, o = g.objectById('to_ladoga'), Z = { at: [h.x, h.y], dir: h.dir, east: dirOf(1, 0), ground: m.groundAt(Math.floor(h.x), Math.floor(h.y)),
          dExit: +Math.hypot(h.x - o.x, h.y - o.y).toFixed(2), r: o.r, label: g.dbg.t('proto.exit.to', { zone: g.zoneName('ladoga') }),
          props: m.props.filter(p => (p.type === 'tree' || p.type === 'rock') && Math.hypot(p.fp[0] + p.fp[2] / 2 - h.x, p.fp[1] + p.fp[3] / 2 - h.y) < 1.2).length,
          clearLeft: m.props.filter(p => (p.type === 'tree' || p.type === 'rock') && p.fp[0] + p.fp[2] > 0 && p.fp[0] < 5 && p.fp[1] + p.fp[3] > 28 && p.fp[1] < 32).length,
          pack0: [m.packs[0].x, m.packs[0].y], path: m.ladPath, toKrada: m.isReachableAt(m.krada.x, m.krada.y + 1.5) };
        let gaps = 0; for (let x = 1; x <= 19; x++) { let ok = false; for (let y = 28; y <= 32; y++) if (m.groundAt(x, y) === 1) ok = true; if (!ok) gaps++; } Z.trailGaps = gaps;
        g.simulate(1.0); Z.stay = g.zone.id;
        h.moveTo(m, o.x, o.y); g.simulate(6, () => g.zone.id === 'ladoga');
        const Lg = { zone: g.zone.id, at: [h.x, h.y], dir: h.dir, west: dirOf(-1, 0), walk: g.map.isReachableAt(h.x, h.y) };
        const gate = g.objectById('to_zalesye'); Lg.gateReach = gate && g.map.isReachableAt(gate.x - 0.6, gate.y);
        g.simulate(1.0); Lg.stay = g.zone.id;
        h.moveTo(g.map, gate.x, gate.y); g.simulate(6, () => g.zone.id === 'zalesye');
        const back = { zone: g.zone.id, at: [+h.x.toFixed(2), +h.y.toFixed(2)], dir: h.dir };
        return { Z, Lg, back }; })()''')
    Z, Lg, bk = s['Z'], s['Lg'], s['back']
    check('v1.14 E4: вход из Ладоги — герой на тропе (3; 31), земля-тропа под ногами, лицом на восток, вне круга выхода (2,6 > r 1,3), рядом ни ствола, ни камня; 1 с стоит — в Ладогу не уходит',
          Z['at'] == [3, 31] and Z['ground'] == 1 and Z['dir'] == Z['east'] and Z['dExit'] > Z['r'] + 0.6 and Z['props'] == 0 and Z['stay'] == 'zalesye', Z)
    check('v1.14 E4: устье тропы — выход (0,7; 29,6) r 1,3 «Путь: Ладога», вырубка x 0–5 / y 28–32 после генерации, земля-тропа до (19,5; 31) без разрывов, стая избы 1 — (9,5; 17,5), костёр достижим',
          Z['path'] and Z['path']['clear'] == [0, 28, 5, 4] and Z['clearLeft'] == 0 and Z['trailGaps'] == 0 and Z['pack0'] == [9.5, 17.5] and Z['toKrada'] and Z['label'] == 'Путь: Ладога', Z)
    check('v1.14 E4: обратно — пешком в устье → Ладога (44,5; 22) за восточными воротами, лицом на запад, точка проходима, 1 с стоит; через ворота «Путь: Залесье» — снова (3; 31) на тропе',
          Lg['zone'] == 'ladoga' and Lg['at'] == [44.5, 22] and Lg['dir'] == Lg['west'] and Lg['walk'] and Lg['gateReach'] and Lg['stay'] == 'ladoga'
          and bk['zone'] == 'zalesye' and abs(bk['at'][0] - 3) < 0.3 and abs(bk['at'][1] - 31) < 0.3 and bk['dir'] == Z['east'], {'ladoga': Lg, 'back': bk})

    # ================= скриншоты
    # 1) вход в Залесье: герой на тропе у западной опушки (там же, где снимок Ильи — приход из Ладоги)
    await G('''(() => { const g = __game, h = g.hero; delete g.zoneStates.zalesye; g.enterZone('zalesye', 'from_ladoga'); g.notice = null; g.log.lines = []; g.updateCamera(); })()''')
    await pg.mouse.move(*(await client_scr(320, 60)))
    await wait(900)
    at = await G('[__game.zone.id, +__game.hero.x.toFixed(2), +__game.hero.y.toFixed(2)]')
    await pg.screenshot(path=SHOT_ENTRY)
    check('v1.14 скриншот screenshot_m1l_zalesye_entry.png: герой на тропе у входа в Залесье (3; 31)', os.path.exists(SHOT_ENTRY) and at == ['zalesye', 3, 31], at)

    # 2) блок: упырь спереди бьёт, щит поднят к нему — «Блок», искры, слот щита «поднят»
    await G('''(() => { ''' + BASE + ''' h.x = 35; h.y = 21.5; h.stop(); h.hp = h.maxHp; g.log.lines = [];
        const e1 = g.spawnTest('upyr', 35.85, 20.65, 1); for (const e of [e1]) { e.hp = e.maxHp = 1e5; e.aggro(g, false); }
        const rnd = Math.random; window.__rnd = rnd; Math.random = () => 0.3;   // на снимке — попадание упыря (принят в щит), без промаха
        h.blockWant = { x: 37, y: 19.5 }; window.__b0 = g.counters.blocked || 0; g.updateCamera(); })()''')
    ok = False
    for _ in range(300):
        st = await G('(() => { const g = __game, h = g.hero; h.hp = h.maxHp; h.yar = h.maxYar; h.blockWant = { x: 37, y: 19.5 }; return (g.counters.blocked || 0) > window.__b0 && h.blocking; })()')
        if st:
            ok = True
            break
        await pg.wait_for_timeout(20)
    await wait(90)
    await G('(() => { __game.simHold = true; })()')
    await pg.mouse.move(*(await client_of(37, 19.5)))
    await pg.wait_for_timeout(60)
    sl = await G('[__game._shieldSlot, __game.fx.texts.some(t => t.str === "Блок")]')
    await pg.screenshot(path=SHOT_BLOCK)
    await G('(() => { __game.simHold = false; __game.hero.blockWant = null; if (window.__rnd) Math.random = window.__rnd; })()')
    check('v1.14 скриншот screenshot_m1l_block.png: герой держит щит, принятый удар — «Блок», слот щита «поднят»',
          os.path.exists(SHOT_BLOCK) and ok and sl[0] == 'raised' and sl[1], {'blocked': ok, 'slot': sl})

    # ================= v1.14 H21–H23: арт блока (INTEGRATION_v114_shield.md) — листы героя, значок ic_block, искры
    s = await G('''(async () => { const A = await import('/src/render/boss_art.js'), F = await import('/src/render/rest_fx.js');
        const keys = []; for (const an of ['raise', 'hold', 'walk', 'hit', 'break']) for (const v of ['s', 'se', 'e', 'ne', 'n']) keys.push('hero_block_' + an + '_' + v);
        const miss = keys.filter(k => !A.ART.sheets[k]), m = A.ART.sheets.hero_block_hold_se.meta;
        const views = [0, 1, 2, 3, 4, 5, 6, 7].map(d => A.heroView(d).join(':'));
        return { miss, ic: !!A.ART.sheets.ic_block, sp: !!F.FX.sheets.bsparks, spMeta: F.FX.sheets.bsparks && [F.FX.sheets.bsparks.meta.pivot, F.FX.sheets.bsparks.meta.frame_count],
          frame: m.frame_size, pivot: m.pivot, views }; })()''')
    check('v1.14 H21–H23 арт: 25 листов hero_block_<raise|hold|walk|hit|break>_<s|se|e|ne|n> (64×64, pivot 32;56), ic_block и fx_block_sparks (pivot 4;8, 3 кадра) загружены; вид 0→s, 7→se, 6→e, 5→ne, 4→n, 1/2/3 — зеркало se/e/ne',
          not s['miss'] and s['ic'] and s['sp'] and s['spMeta'] == [[4, 8], 3] and s['frame'] == [64, 64] and s['pivot'] == [32, 56]
          and s['views'] == ['s:false', 'se:true', 'e:true', 'ne:true', 'n:false', 'ne:false', 'e:false', 'se:false'], s)
    s = await G('''(async () => { ''' + BASE + ''' const A = await import('/src/render/boss_art.js'); const P = () => { const q = A.poseHeroBlock(h, g.time); return q && q.anim.slice(11) + ':' + q.frame; }; h.block = 0; g.settings.shake = false;   // без пассивного блока и стоп-кадра
        const out = {}; out.none = P(); h.blockWant = { x: 36, y: 22 }; step(3); out.raise = P(); step(10); out.hold = P();
        h.moving = true; out.walk = P(); h.moving = false;
        const e = g.spawnTest('upyr', 34.8, 21.3, 1); e.state = 'idle'; e.stagger = 1e9; e.speed = 0;
        h.takeDamage(10, g, 'melee', e, { src: 'melee', from: [e.x, e.y] }); out.hit = P(); out.left = h.blockFromLeft; g.enemies = []; step(24); out.afterHit = P();
        h.blockWant = null; step(1); out.lower = P(); step(12); out.lowered = P();
        h.blockWant = { x: 36, y: 22 }; step(20); h.yar = 0; h.takeDamage(10, g, 'melee', e, { src: 'melee', from: [e.x, e.y] }); out.brk = P(); step(17); out.brkEnd = P(); step(30); out.brkDone = P();
        A.ART.sparksHit = 0; return out; })()''')
    check('v1.14 H21 позы: опущен — кодом; подъём raise (2 кадра) → hold; шаг — walk; принятый удар — hit; пробитие — break (держит последний кадр); отпустил — raise назад; затем снова кодом',
          s['none'] is None and s['raise'] == 'raise:0' and s['hold'] and s['hold'].startswith('hold:') and s['walk'] and s['walk'].startswith('walk:')
          and s['hit'] == 'hit:0' and s['afterHit'].startswith('hold:') and s['lower'] == 'raise:1' and s['lowered'] is None
          and s['brk'] == 'break:0' and s['brkEnd'] == 'break:3' and s['brkDone'] is None, s)
    # отрисовка: в кадре блока рисуется лист (не грей-бокс), искры у обода на hit; значок ic_block в слоте по состоянию
    s = await G('''(async () => { ''' + BASE + ''' const A = await import('/src/render/boss_art.js'); A.ART.sparksHit = 0; A.ART.heroBlockPose = null; h.block = 0; g.settings.shake = false;
        const fr = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        await fr(); const ic0 = A.ART.icBlockDrawn, pose0 = A.ART.heroBlockPose;
        h.blockWant = { x: 36, y: 22 }; step(20); await fr(); const ic1 = A.ART.icBlockDrawn, pose1 = A.ART.heroBlockPose;
        const e = g.spawnTest('upyr', 35, 22, 1); e.state = 'idle'; e.stagger = 1e9; e.speed = 0;
        h.takeDamage(10, g, 'melee', e, { src: 'melee', from: [e.x, e.y] }); g.enemies = []; await fr(); const sp = A.ART.sparksHit, pose2 = A.ART.heroBlockPose;
        h.blockWant = null; h.blockCd = 1; step(1); await fr(); const ic2 = A.ART.icBlockDrawn;
        const lh = h.equip.lhand; h.equip.lhand = null; h.blockCd = 0; step(1); await fr(); const ic3 = A.ART.icBlockDrawn; h.equip.lhand = lh;
        return { ic0, ic1, ic2, ic3, pose0, pose1, pose2, sp }; })()''')
    check('v1.14 H21–H23 отрисовка: в блоке — лист художника (вид se, без зеркала при dir 7), принятый удар — кадр hit + искры у shield_rim; значок ic_block: готов / поднят / пробит / нет щита',
          s['pose0'] is None and s['pose1'] and s['pose1'].startswith('hero_block_hold_') and s['pose2'] and s['pose2'].startswith('hero_block_hit_') and s['sp'] > 0
          and [s['ic0'], s['ic1'], s['ic2'], s['ic3']] == ['ready', 'raised', 'broken', 'none'], s)

    # пара «до / в блоке» — склейка screenshot_m1l_block_transition.png (вырез вокруг героя, ×2)
    await G('''(() => { ''' + BASE + ''' h.x = 35; h.y = 21.5; h.dir = 7; h.facing = 1; g.log.lines = []; g.fx.texts = []; g.fx.parts && (g.fx.parts.length = 0); g.updateCamera(); g.simHold = true; })()''')
    await wait(150)
    cx, cy = await client_of(35, 21.5)
    box = (int(cx) - 150, int(cy) - 200, int(cx) + 150, int(cy) + 50)
    await pg.screenshot(path='/tmp/m1l_tr_a.png')
    await G('''(() => { const g = __game, h = g.hero; g.simHold = false; h.blockWant = { x: 37, y: 22.5 }; })()''')
    for _ in range(60):
        if await G('(() => { const h = __game.hero; return !!(h.blockSt && h.blockSt.t > 0.4); })()'):
            break
        await pg.wait_for_timeout(20)
    await G('(() => { const h = __game.hero; h.dir = 7; h.facing = 1; __game.simHold = true; })()')
    await wait(120)
    await pg.screenshot(path='/tmp/m1l_tr_b.png')
    pz = await G('(() => { const g = __game; g.simHold = false; g.hero.blockWant = null; return (window.__ba || null); })()')
    from PIL import Image as _Im
    A_ = _Im.open('/tmp/m1l_tr_a.png').crop(box); B_ = _Im.open('/tmp/m1l_tr_b.png').crop(box)
    W_, H_ = A_.size
    out = _Im.new('RGB', (W_ * 2 + 12, H_), (13, 11, 10)); out.paste(A_, (0, 0)); out.paste(B_, (W_ + 12, 0))
    out.save(SHOT_TRANS)
    check('v1.14 скриншот screenshot_m1l_block_transition.png: склейка «до блока (герой кодом) / в блоке (лист hero_block_hold_se)»', os.path.exists(SHOT_TRANS), box)

    # 3) змей на E: E в упыря — змей в полёте, на панели слот «E»
    await G('''(() => { ''' + BASE + ''' h.x = 35; h.y = 21; h.stop(); h.rmb = 'zmey'; g.log.lines = [];
        const e = g.spawnTest('upyr', 39.5, 20, 1); e.state = 'idle'; e.stagger = 1e9; e.speed = 0; e.hp = e.maxHp = 1e5; g.updateCamera(); })()''')
    await wait(200)
    await pg.mouse.move(*(await client_of(39.5, 20, 14)))
    await wait(80)
    await pg.keyboard.press('KeyE')
    fly = False
    for _ in range(100):
        p = await G('(() => { const g = __game, P = g.combat.projectiles.find(p => !p.hostile && !p.dead); return P ? Math.hypot(P.x - g.hero.x, P.y - g.hero.y) : -1; })()')
        if p > 1.6:
            fly = True
            break
        await pg.wait_for_timeout(10)
    await G('(() => { __game.simHold = true; })()')
    await pg.wait_for_timeout(60)
    await pg.screenshot(path=SHOT_ZMEY)
    await G('(() => { __game.simHold = false; })()')
    check('v1.14 скриншот screenshot_m1l_zmey_e.png: «Огненный змей» по E в полёте, на панели слот «E»', os.path.exists(SHOT_ZMEY) and fly, {'fly': fly})

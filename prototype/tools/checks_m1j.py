# Веха m1j: GDD v1.13 §12.4, часть A P0 — D1 (бой, пакет F), D2 (ощущение удара §4.6), D13 (плашка «Награда», очередь
# уведомлений §10.5), D17 (serve.py, сообщение вместо чёрного экрана, репозиторий на Gitea в README).
from pathlib import Path
import os, json, urllib.request

ROOT = str(Path(__file__).resolve().parent.parent) + '/'   # B-39: корень прототипа от расположения файла
SHOT_COMBAT = ROOT + 'screenshot_m1j_combat.png'
SHOT_REWARD = ROOT + 'screenshot_m1j_reward.png'

# стенд боя: Залесье, враги убраны, герой в (x, y) лицом на восток; spawn(kind, dx, dy) — тестовый враг рядом
STAND = '''const g = __game, h = g.hero; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = [];
  g.combat.projectiles = []; g.fx.parts = []; g.fx.smears = []; g.fx.texts = []; g.notice = null; g.rewardCard = null; g.settings.shake = true;
  const X = 34, Y = 21; h.x = X; h.y = Y; h.stop && h.stop(); h.cmd = null; h.action = null; h.invuln = 1e9; h.hsT = 0; g.hitStopT = 0; g.shakeT = 0; g.shakeAmp = 0; g.shakeDur = 0;
  const spawn = (kind, dx, dy, mlvl = 1) => { const e = g.spawnTest(kind, X + dx, Y + dy, mlvl); e.state = 'idle'; return e; };
  const R = (v) => { Math.random = () => v; };            // фиксированный «бросок»: 0,5 — попадание без крита
  const rnd0 = Math.random;'''


async def run_m1j(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1j', flush=True)

    async def fresh(url=None):
        await pg.goto(url or a.url)
        await pg.wait_for_function('() => window.__game && __game.time > 0.3')
        await wait(100)

    await fresh()
    # ================= D1. Бой, пакет F
    s = await G('''(() => { const g = __game, S = g.dbg.SKILLS, h = g.hero, sk = S.sshibka, z = S.zmey, d = g.dbg;
        const cost = (id, r) => Math.max(0, Math.floor(S[id].cost[0] + S[id].cost[1] * (r - 1)));   // формула skillCost (data/skills.js)
        return { sk: { cost: sk.cost, yarOnHit: sk.yarOnHit, arc: sk.arc, flinch: sk.flinch, dmg: sk.dmgPct, ar: sk.arPct, kb: sk.knockback },
                 z: { cost: z.cost, kb: z.knockback, r1: cost('zmey', 1), r5: cost('zmey', 5), r10: cost('zmey', 10) }, sc: h.skillCost }; })()''')
    check('m1j D1 данные: «Сшибка» cost [0,0], yarOnHit 1, arc {120°, r 1,5, ×0,35, свой бросок}, flinch {0,2 с, раз в 1,5 с, не боссы}; '
          '«Змей» cost [6,0.5] (ранг 1/5/10 — 6/8/10), отброс 0,35; урон/меткость «Сшибки» прежние',
          s['sk']['cost'] == [0, 0] and s['sk']['yarOnHit'] == 1 and s['sk']['arc'] == {'deg': 120, 'r': 1.5, 'mul': 0.35, 'hitRoll': True}
          and s['sk']['flinch'] == {'t': 0.2, 'cd': 1.5, 'bosses': False} and s['sk']['dmg'] == [175, 7] and s['sk']['ar'] == [20, 5]
          and s['z']['cost'] == [6, 0.5] and s['z']['kb'] == 0.35 and (s['z']['r1'], s['z']['r5'], s['z']['r10']) == (6, 8, 10) and s['sc'] == 6, s)

    # Удаль: замах «Сшибки» не тратит; +1 за попадание основной цели (не за промах, не за соседей), не выше максимума
    s = await G('''(() => { ''' + STAND + '''
        const a1 = spawn('upyr', 1.0, 0), b1 = spawn('upyr', 0.7, 0.8), c1 = spawn('upyr', 0.7, -0.8);
        h.yar = 10; h.cmd = { type: 'attack', target: a1, lmb: true }; h.startAttack(a1, 'sshibka', g); const spend = 10 - h.yar, fb = g.counters.lmbFallback || 0; h.action = null;
        R(0.5); h.yar = 10; g.combat.heroMelee(h, a1, 'sshibka'); const hit = h.yar - 10, arcN = (g.counters.arcHits || 0);
        R(0.999); h.yar = 10; g.combat.heroMelee(h, a1, 'sshibka'); const miss = h.yar - 10;
        R(0.5); h.yar = h.maxYar; g.combat.heroMelee(h, b1, 'sshibka'); const cap = h.yar === h.maxYar;
        R(0.5); h.yar = 10; g.combat.heroMelee(h, a1, null); const basic = h.yar - 10;
        Math.random = rnd0; return { spend, fb, hit, arcN, miss, cap, basic }; })()''')
    check('m1j D1 Удаль: замах «Сшибки» Удаль не тратит (подмены на базовый удар нет); +1 за попадание основной цели (не за соседей в дуге), 0 за промах, не выше максимума; базовый удар — 0',
          s['spend'] == 0 and s['fb'] == 0 and s['hit'] == 1 and s['arcN'] >= 2 and s['miss'] == 0 and s['cap'] and s['basic'] == 0, s)

    # Дуга 120°, r 1,5: соседям ≈ 35% урона, у каждого свой бросок (может быть «Мимо»); вне сектора и дальше r — не задевает
    s = await G('''(() => { ''' + STAND + '''
        const a1 = spawn('upyr', 1.0, 0), l = spawn('upyr', 0.75, 0.85), r = spawn('upyr', 0.75, -0.85), back = spawn('upyr', -1.0, 0), far = spawn('upyr', 2.3, 0.2);
        for (const e of [a1, l, r, back, far]) e.hp = e.maxHp = 500;
        R(0.5); g.combat.heroMelee(h, a1, 'sshibka');
        const dmg = (e) => 500 - e.hp, out = { main: dmg(a1), l: dmg(l), r: dmg(r), back: dmg(back), far: dmg(far) };
        // промах соседа: основная цель — попадание (0,5), сосед — свой бросок 0,999
        for (const e of [a1, l, r]) e.hp = 500; g.fx.texts = [];
        const dfn0 = l.dfn; l.dfn = 1e6; R(0.5);                 // у левого соседа меткость упирается в минимум 5% — бросок 0,5 мимо
        const m0 = g.counters.arcMiss || 0; g.combat.heroMelee(h, a1, 'sshibka'); l.dfn = dfn0;
        out.arcMiss = (g.counters.arcMiss || 0) - m0; out.missText = g.fx.texts.filter(t => t.str === g.t('ui.combat.miss')).length;
        out.someUnhit = [l, r].filter(e => e.hp === 500).length;
        Math.random = rnd0; return out; })()''')
    ratio = (s['l'] / s['main']) if s['main'] else 0
    check('m1j D1 дуга: соседи в секторе 120° и r 1,5 получают ≈ 35% урона удара; сзади и дальше r — 0; промах соседа — «Мимо» (свой бросок меткости)',
          s['main'] > 0 and s['l'] > 0 and s['r'] > 0 and 0.25 <= ratio <= 0.45 and s['back'] == 0 and s['far'] == 0
          and s['arcMiss'] == 1 and s['missText'] >= 1 and s['someUnhit'] == 1, {**s, 'ratio': round(ratio, 2)})

    # «Вздрог»: 0,2 с, неначатый удар сорван, не чаще раза в 1,5 с на цель
    s = await G('''(() => { ''' + STAND + '''
        const e = spawn('upyr', 1.0, 0); e.hp = e.maxHp = 500; e.state = 'attack'; e.t = 0.05; e.attackFired = false;
        const f0 = g.counters.flinch || 0; R(0.5); g.combat.heroMelee(h, e, 'sshibka');
        const first = { st: +e.stagger.toFixed(2), state: e.state, n: (g.counters.flinch || 0) - f0 };
        e.stagger = 0; e.age += 0.8; g.combat.heroMelee(h, e, 'sshibka'); const second = (g.counters.flinch || 0) - f0;
        e.stagger = 0; e.age += 0.8; g.combat.heroMelee(h, e, 'sshibka'); const third = (g.counters.flinch || 0) - f0;
        Math.random = rnd0; return { first, second, third }; })()''')
    check('m1j D1 «вздрог»: 0,2 с, неначатый удар врага сорван (attack → chase); через 0,8 с — нет, через 1,6 с — снова',
          s['first'] == {'st': 0.2, 'state': 'chase', 'n': 1} and s['second'] == 1 and s['third'] == 2, s)

    # исключение боссов — по флагу сущности e.boss: Кривша (def.boss нет) не вздрагивает; Огнея (mara, былинный враг) — вздрагивает
    s = await G('''(async () => { const g = __game, h = g.hero; const rnd0 = Math.random;
        delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const M = g.enemies.find(e => e.kind === 'mara');
        const out = { maraBoss: M ? !!M.boss : null };
        if (M) { h.x = M.x - 1.0; h.y = M.y; h.invuln = 1e9; M.stagger = 0; M.lastFlinch = -99; const f0 = g.counters.flinch || 0; Math.random = () => 0.5;
          g.combat.heroMelee(h, M, 'sshibka'); out.maraFlinch = (g.counters.flinch || 0) - f0; out.maraSt = +M.stagger.toFixed(2); Math.random = rnd0; }
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map; g.enemies = []; g.buried = [];
        const b = g.riseBoss('test'); g.simulate(2.2); out.kDefBoss = b.def.boss === undefined ? 'нет' : b.def.boss; out.kBoss = !!b.boss;
        h.x = b.x - (b.r + 0.9); h.y = b.y; h.invuln = 1e9; b.lastFlinch = -99; b.stagger = 0; const f1 = g.counters.flinch || 0; Math.random = () => 0.5;
        g.combat.heroMelee(h, b, 'sshibka'); out.kFlinch = (g.counters.flinch || 0) - f1; Math.random = rnd0;
        g.enterZone('zalesye', 'krada'); return out; })()''')
    check('m1j D1 боссы: исключение по e.boss — Кривша (def.boss нет, e.boss есть) не вздрагивает; Огнея (mara, не босс) вздрагивает 0,2 с',
          s.get('maraBoss') is False and s.get('maraFlinch') == 1 and s.get('maraSt') == 0.2 and s['kDefBoss'] == 'нет' and s['kBoss'] and s['kFlinch'] == 0, s)

    s = await G('''(() => { ''' + STAND + '''
        g.combat.castProjectile(h, 'zmey', X + 5, Y); const p = g.combat.projectiles[g.combat.projectiles.length - 1]; const kb = p.knockback; g.combat.projectiles = [];
        return { kb }; })()''')
    check('m1j D1 «Змей»: снаряд несёт отброс 0,35 тайла', s['kb'] == 0.35, s)

    # ================= D2. Ощущение удара (§4.6)
    s = await G('''(() => { ''' + STAND + '''
        const F = g.dbg.CFG.stats.hitFx; const out = { F: { hs: F.hitStop, sh: F.shake, fl: F.flash, sp: F.sparks, sm: F.smear, sfx: F.sfx, glow: F.yarGlow, push: F.hitPush } };
        const snd = []; const play0 = g.audio.play.bind(g.audio); g.audio.play = (n, o) => { snd.push([n, o || null]); return play0(n, o); };
        const tier = (kind, v, setup) => { g.enemies = []; g.fx.parts = []; g.fx.smears = []; snd.length = 0; g.hitStopT = 0; g.shakeT = 0; g.shakeAmp = 0; g.shakeDur = 0; h.hsT = 0;
          const e = spawn(kind, 1.0, 0); e.hp = e.maxHp = 500; if (setup) setup(e); const hs0 = g.counters.hitStop, other = spawn('upyr', -4, 0); const o0 = other.age;
          R(v); g.combat.heroMelee(h, e, 'sshibka'); Math.random = rnd0;
          const sp = g.fx.parts.filter(p => p.spark), PAL = {}; for (const p of sp) PAL[p.color] = (PAL[p.color] || 0) + 1;
          const L = g.lastHitFx || {};
          // мир идёт: прогон 0,05 с — замер у цели и героя (hsT), сторонний враг живёт
          const ea = e.age, ha = h.hsT; g.update(0.05); const r = { tier: L.tier, hs: L.hitStop, hst: +g.hitStopT.toFixed(3), heroHs: +ha.toFixed(2), tgtFrozen: e.age === ea, otherLives: other.age > o0,
            stops: g.counters.hitStop - hs0, amp: g.shakeAmp, dur: g.shakeDur, sx: g.shakeX, sy: g.shakeY, flash: [e.flash != null ? +Math.max(e.flash, 0).toFixed(2) : null, e.flashA],
            sparks: sp.length, colors: PAL, spDur: sp.length ? sp[0].dur : null, smear: g.fx.smears.length ? { deg: g.fx.smears[0].deg, r: g.fx.smears[0].r, fr: g.fx.smears[0].frames, ft: g.fx.smears[0].ft, c: g.fx.smears[0].color } : null,
            snd: snd.filter(x => x[0] === 'hit').map(x => x[1] && [x[1].mat, x[1].tier, x[1].pitch]) };
          return r; };
        out.hit = tier('upyr', 0.5);
        out.crit = tier('anchutka', 0.5, () => { h.crit0 = h.crit; h.crit = 1; }); h.crit = h.crit0;
        out.kill = tier('chernoyarets_arsonist', 0.5, (e) => { e.hp = 1; });
        g.audio.play = play0; return out; })()''')
    F = s['F']
    check('m1j D2 stats.hitFx = §15: хит-стоп 0,07/0,11/0,09 (max на взмах), тряска 1/2/1 px целыми (0,06/0,12/0,10; «Змей» 1 px 0,10), вспышка 0,08·0,35 / 0,10·0,45, '
          'искры 6+2 / 10+3 (bronze_hi, ember; 10–18 px за 0,15 с), след 120° r 22 2×0,06 с, звук 3 варианта ±8%, «Мимо» −6 дБ, шар Удали 0,15 с, hitPush 0',
          F['hs'] == {'hit': 0.07, 'crit': 0.11, 'kill': 0.09, 'perSwing': 'max'} and F['sh']['hit'] == [1, 0.06] and F['sh']['crit'] == [2, 0.12] and F['sh']['kill'] == [1, 0.1]
          and F['sh']['zmey'] == [1, 0.1] and F['sh']['intPx'] and F['fl'] == {'hit': [0.08, 0.35], 'crit': [0.1, 0.45]} and F['sp']['hit'] == [6, 2] and F['sp']['crit'] == [10, 3]
          and F['sp']['spread'] == [10, 18] and F['sp']['t'] == 0.15 and F['sm']['deg'] == 120 and F['sm']['r'] == 22 and F['sm']['frames'] == 2 and F['sm']['ft'] == 0.06
          and F['sfx'] == {'variants': 3, 'pitch': 0.08, 'missDb': -6, 'critDb': 2, 'killDb': -3} and F['glow'] == 0.15 and F['push'] == 0, F)
    h_, c_, k_ = s['hit'], s['crit'], s['kill']
    check('m1j D2 хит-стоп по ярусам: обычное 0,07, удачный 0,11, добивание 0,09; один на взмах; замирают герой и цель, сторонний враг живёт (мир идёт)',
          (h_['tier'], h_['hs']) == ('hit', 0.07) and (c_['tier'], c_['hs']) == ('crit', 0.11) and (k_['tier'], k_['hs']) == ('kill', 0.09)
          and all(x['stops'] == 1 and x['heroHs'] == x['hs'] and x['tgtFrozen'] and x['otherLives'] for x in (h_, c_)), {k: {kk: v[kk] for kk in ('tier', 'hs', 'stops', 'heroHs', 'tgtFrozen', 'otherLives')} for k, v in (('hit', h_), ('crit', c_), ('kill', k_))})
    check('m1j D2 тряска целыми px: обычное 1 px / 0,06 с, удачный 2 px / 0,12 с, добивание 1 px / 0,10 с; смещение кадра — целые числа в пределах амплитуды',
          (h_['amp'], h_['dur']) == (1, 0.06) and (c_['amp'], c_['dur']) == (2, 0.12) and (k_['amp'], k_['dur']) == (1, 0.1)
          and all(x['sx'] == int(x['sx']) and x['sy'] == int(x['sy']) and abs(x['sx']) <= x['amp'] and abs(x['sy']) <= x['amp'] for x in (h_, c_)),
          {k: (v['amp'], v['dur'], v['sx'], v['sy']) for k, v in (('hit', h_), ('crit', c_), ('kill', k_))})
    check('m1j D2 вспышка (0,08/0,35; удачный 0,10/0,45), искры 6+2 / 10+3 bronze_hi+ember по 0,15 с, след взмаха 120° r 22 (2 кадра по 0,05; удачный — bronze_lt)',
          h_['flash'][1] == 0.35 and c_['flash'][1] == 0.45 and h_['sparks'] == 8 and c_['sparks'] == 13 and set(h_['colors'].values()) == {6, 2}
          and sorted(c_['colors'].values()) == [3, 10] and h_['spDur'] == 0.15 and h_['smear'] and h_['smear']['deg'] == 120 and h_['smear']['r'] == 22
          and h_['smear']['fr'] == 2 and h_['smear']['ft'] == 0.06 and h_['smear']['c'] != c_['smear']['c'],
          {k: (v['flash'], v['sparks'], v['colors'], v['smear']) for k, v in (('hit', h_), ('crit', c_))})
    check('m1j D2 звук удара: 3 варианта по материалу (упырь — кость, анчутка — плоть, поджигатель — дерево/щит), высота ±8%, ярусы hit / crit / kill',
          h_['snd'] == [['bone', 'hit', 0.08]] and c_['snd'] == [['flesh', 'crit', 0.08]] and k_['snd'] == [['wood', 'kill', 0.08]], (h_['snd'], c_['snd'], k_['snd']))

    # дуга: хит-стоп один на взмах (наибольший), тряска не складывается; промах — без хит-стопа и тряски; шар Удали светлеет
    s = await G('''(() => { ''' + STAND + '''
        const a1 = spawn('upyr', 1.0, 0), l = spawn('upyr', 0.75, 0.85), r = spawn('upyr', 0.75, -0.85); r.hp = 1;
        const hs0 = g.counters.hitStop, sh0 = g.counters.shake; R(0.5); h.yar = 10; g.combat.heroMelee(h, a1, 'sshibka');
        const arc = { stops: g.counters.hitStop - hs0, shakes: g.counters.shake - sh0, tier: g.lastHitFx.tier, n: g.lastHitFx.n, hs: g.hitStopT, glow: h.yarGlow };
        g.hitStopT = 0; g.shakeT = 0; g.shakeAmp = 0; const hs1 = g.counters.hitStop, sh1 = g.counters.shake; R(0.999); g.combat.heroMelee(h, a1, 'sshibka');
        const miss = { stops: g.counters.hitStop - hs1, shakes: g.counters.shake - sh1 }; Math.random = rnd0;
        return { arc, miss }; })()''')
    await wait(60)
    glow = await G('__game.yarGlowDrawn != null')
    check('m1j D2 взмах по дуге с добиванием соседа: один хит-стоп (наибольший — 0,09), одна тряска; промах — без хит-стопа и тряски; шар Удали коротко светлеет (0,15 с)',
          s['arc']['stops'] == 1 and s['arc']['shakes'] == 1 and s['arc']['tier'] == 'kill' and s['arc']['n'] == 3 and abs(s['arc']['hs'] - 0.09) < 1e-9
          and s['arc']['glow'] == 0.15 and s['miss'] == {'stops': 0, 'shakes': 0} and glow, {**s, 'glowDrawn': glow})

    # settings.shake: переключатель в паузе, сохраняется; выключено — ни тряски, ни хит-стопа
    p = await G('''(async () => { const S = await import('/src/render/screens.js'); const b = S.PAUSE_BTNS.find(x => x.id === 'shake'); return b && [b.x + 6, b.y + 6]; })()''')
    await G("localStorage.removeItem('byl_nebyl_settings'); __game.settings.shake = true; __game.ui.closeAll(); __game.paused = true;")
    await wait(80)
    await pg.mouse.click(*(await client_scr(*p)))
    await wait(120)
    s = await G('''(() => { const g = __game; const L = (g.pauseLines || []).length; const st = g.settings.shake, ls = localStorage.getItem('byl_nebyl_settings');
        g.paused = false; ''' + STAND.replace("const g = __game, h = g.hero; ", "const h = g.hero; ").replace("g.settings.shake = true;", "") + '''
        const e = spawn('upyr', 1.0, 0); e.hp = e.maxHp = 500; const hs0 = g.counters.hitStop, sh0 = g.counters.shake; R(0.5); g.combat.heroMelee(h, e, 'sshibka'); Math.random = rnd0;
        return { st, ls, stops: g.counters.hitStop - hs0, shakes: g.counters.shake - sh0, hsT: h.hsT || 0, label: g.t('ui.settings.shake') }; })()''')
    await fresh()
    s2 = await G("({ st: __game.settings.shake })")
    await G("__game.setSetting('shake', true)")
    check('m1j D2 настройка «Тряска при ударе» (подпись ui.settings.shake, поле settings.shake): переключатель в паузе, выкл. — нет ни тряски, ни хит-стопа; сохраняется после перезагрузки',
          s['st'] is False and json.loads(s['ls'] or '{}').get('shake') is False and s['stops'] == 0 and s['shakes'] == 0 and s['hsT'] == 0
          and s2['st'] is False and s['label'] == 'Тряска при ударе', {**s, 'reload': s2})

    # снимок: удар с искрами и следом по 2+ врагам в дуге (кадр держим — g.simHold)
    s = await G('''(() => { ''' + STAND + '''
        h.x = 27.5; h.y = 32.5;   /* открытая поляна: circleFree r 3,2 */ const X2 = h.x, Y2 = h.y; h.face && h.face(1, 0.3);
        const mk = (dx, dy) => { const e = g.spawnTest('upyr', X2 + dx, Y2 + dy, 1); e.state = 'idle'; e.hp = e.maxHp = 500; return e; };
        const a1 = mk(1.0, 0.25), l = mk(0.55, 0.95), r = mk(0.95, -0.6);
        g.updateCamera(); R(0.5); g.simHold = true; g.combat.heroMelee(h, a1, 'sshibka'); Math.random = rnd0;
        return { arcHit: [l, r].filter(e => e.hp < 500).length, main: a1.hp < 500, sparks: g.fx.parts.filter(p => p.spark).length, smears: g.fx.smears.length }; })()''')
    await wait(60)
    sd = await G('__game.smearDrawn && [__game.smearDrawn.frame, __game.smearDrawn.sprite, __game.smearDrawn.under]')
    s['drawn'] = sd
    await pg.screenshot(path=SHOT_COMBAT, clip={'x': 0, 'y': 0, 'width': 1920, 'height': 1080})
    await G('__game.simHold = false')
    check('m1j D2 снимок screenshot_m1j_combat.png: удар «Сшибкой» — основная цель и 2 соседа в дуге, искры и след взмаха (спрайт fx_swing_se, кадр 0) на кадре',
          s['main'] and s['arcHit'] == 2 and s['sparks'] >= 24 and s['smears'] == 1 and sd == [0, 'sw_se', False] and os.path.exists(SHOT_COMBAT), s)

    # H10: лист и зеркало следа по направлению взмаха (экранные 8 сторон), N/NE/NW — под героем
    dirs = {'E': [1, -1], 'SE': [1, 0], 'S': [1, 1], 'SW': [0, 1], 'W': [-1, 1], 'NW': [-1, 0], 'N': [-1, -1], 'NE': [0, -1]}
    got = {}
    for nm, (dx, dy) in dirs.items():
        await G('''(() => { const g = __game, h = g.hero; g.fx.smears.length = 0; g.smearDrawn = null; g.simHold = true;
            g.fx.smears.push({ x: h.x, y: h.y, dx: %s, dy: %s, deg: 120, r: 22, frames: 2, ft: 0.05, t: 0, dur: 0.1, color: '#fff' }); })()''' % (dx / (abs(dx) + abs(dy)) ** 0.5, dy / (abs(dx) + abs(dy)) ** 0.5))
        await wait(3)
        got[nm] = await G('__game.smearDrawn && [__game.smearDrawn.sprite, __game.smearDrawn.flip, __game.smearDrawn.under]')
    await G('__game.fx.smears.length = 0; __game.simHold = false')
    want = {'E': ['sw_se', False, False], 'SE': ['sw_se', False, False], 'S': ['sw_s', False, False], 'SW': ['sw_se', True, False], 'W': ['sw_se', True, False],
            'NW': ['sw_ne', True, True], 'N': ['sw_n', False, True], 'NE': ['sw_ne', False, True]}
    check('m1j D2 след взмаха — спрайт художника (H10): SE/NE/S/N, SW/NW/W — зеркало, E → SE; S/SE поверх героя, N/NE под ним',
          got == want, got)

    # ================= D13. Плашка «Награда» и очередь уведомлений
    await fresh()
    s = await G('''(() => { const g = __game, h = g.hero, q = g.quest; g.ui.closeAll(); g.notice = null; g.enterZone('ladoga', 'start');
        q.missionDone = true; delete q.flags['m1.turnedIn']; g.town.placeVyshata && g.town.placeVyshata(); const vy = g.npcs.find(n => n.role === 'vyshata'); g.town.npc = vy;
        g.log.lines.length = 0; const ok = g.town.claimM1(); g.town.close && g.town.close(); const logTxt = g.log.lines.map(l => l.text || l[0] || '').join(' | '); g.simulate(0.3); const C = g.rewardCard;
        return { ok, card: C && { x: C.x, y: C.y, w: C.w, h: C.h, hold: C.hold, fade: C.fade, lines: C.lines.map(l => l.text) },
                 rew: (g.notices || []).concat(g.noticeQ || []).map(n => n.key), log: logTxt, tier: h.yarTier }; })()''')
    await G('__game.simHold = true')
    await wait(80)
    d = await G('__game.rewardDrawn')
    await pg.screenshot(path=SHOT_REWARD, clip={'x': 0, 'y': 0, 'width': 1920, 'height': 1080})
    await G('__game.simHold = false')
    check('m1j D13 сдача М1: одна плашка «Награда» 220×64 в (210; 64) на 6 с (+1 с угасание) — сразу три строки «Серебро: +300», «Удаль: ступень I», «Очко навыка: +1 · T — навыки»; '
          'отдельных уведомлений наград нет; журнал — одна строка; снимок screenshot_m1j_reward.png',
          s['ok'] and s['card'] == {'x': 210, 'y': 64, 'w': 220, 'h': 64, 'hold': 6, 'fade': 1, 'lines': ['Серебро: +300', 'Удаль: ступень I', 'Очко навыка: +1 · T — навыки']}
          and not any(k and k.startswith('rew') for k in s['rew']) and 'm2' not in s['rew'] and 'Серебро: +300 · Удаль: ступень I · Очко навыка: +1' in s['log']
          and d and d['title'] == 'НАГРАДА' and d['lines'] == s['card']['lines'] and (d['x'], d['y'], d['w'], d['h']) == (210, 64, 220, 64) and s['tier'] == 1
          and os.path.exists(SHOT_REWARD), {**s, 'drawn': d})
    s = await G('''(() => { const g = __game; g.simulate(5.5); const at55 = !!g.rewardCard && g.notices.filter(n => g.noticeLive(n)).map(n => n.text);
        g.simulate(1.7); const after = { card: !!g.rewardCard, n: g.notices.filter(n => g.noticeLive(n)).map(n => n.text) };
        // закрыть щелчком / Esc
        g.showReward([{ text: 'x', color: '#fff' }], () => { g._closedBy = 'cb'; }); const C = g.rewardCard;
        return { at55, after, rect: [C.x + 20, C.y + 20] }; })()''')
    await pg.mouse.click(*(await client_scr(*s['rect'])))
    await wait(100)
    s['click'] = await G('[!!__game.rewardCard, __game._closedBy || null]')
    await G("__game._closedBy = null; __game.showReward([{ text: 'x', color: '#fff' }], () => { __game._closedBy = 'esc'; })")
    await pg.keyboard.press('Escape')
    await wait(100)
    s['esc'] = await G('[!!__game.rewardCard, __game._closedBy || null, __game.paused]')
    await G('__game.paused = false')
    check('m1j D13 плашка держится 6 с, затем «Открыта миссия: «Сопки Волхова»» обычным уведомлением; щелчок по плашке и Esc закрывают её (Esc не открывает паузу)',
          s['at55'] == [] and s['after']['card'] is False and any('Открыта миссия' in x for x in s['after']['n'])
          and s['click'] == [False, 'cb'] and s['esc'] == [False, 'esc', False], s)

    s = await G('''(() => { const g = __game; g.notice = null; g.log.lines.length = 0;
        g.notify('A', '#fff', 'ka'); g.notify('B', '#fff', 'kb'); g.notify('C', '#fff', 'kc'); g.notify('D', '#fff', 'kd');
        const s0 = [g.notices.map(n => n.text), g.noticeQ.map(n => n.text)];
        g.notify('B2', '#fff', 'kb'); g.notify('D2', '#fff', 'kd'); const s1 = [g.notices.map(n => n.text), g.noticeQ.map(n => n.text)];
        g.notify('E', '#fff', 'ke'); g.notify('F', '#fff', 'kf'); g.notify('G', '#fff', 'kg'); const s2 = [g.noticeQ.map(n => n.text), g.log.lines.map(l => l.text || l[0])];
        g.simulate(1.2); const s3 = g.notices.map(n => n.text); g.simulate(0.4); const s4 = g.notices.map(n => n.text);
        g.notice = null; return { s0, s1, s2, s3, s4 }; })()''')
    check('m1j D13 очередь уведомлений: разные ключи не затирают — на экране 2 (новое снизу), остальные ждут; тот же ключ заменяет своё; в очереди ≤ 4, лишнее — в журнал; каждое ≥ 1,5 с',
          s['s0'] == [['A', 'B'], ['C', 'D']] and s['s1'] == [['A', 'B2'], ['C', 'D2']] and s['s2'][0] == ['C', 'D2', 'E', 'F'] and 'G' in s['s2'][1]
          and s['s3'] == ['A', 'B2'] and s['s4'] == ['C', 'D2'], s)

    # ================= D17. serve.py, сообщение вместо чёрного экрана, README → Gitea
    base = a.url.split('/index.html')[0]
    hdr = {}
    for path in ('/src/main.js', '/data/stats.json', '/index.html'):
        with urllib.request.urlopen(base + path) as r:
            hdr[path] = [r.headers.get('Content-Type'), r.headers.get('Cache-Control')]
    srv = open(ROOT + 'serve.py', encoding='utf-8').read(); run = open(ROOT + 'run.sh', encoding='utf-8').read()
    check('m1j D17 serve.py: .js — text/javascript, .json — application/json, no-cache (этот прогон идёт через serve.py); run.sh запускает serve.py',
          hdr['/src/main.js'][0].startswith('text/javascript') and hdr['/data/stats.json'][0].startswith('application/json') and hdr['/index.html'][1] == 'no-cache'
          and 'ThreadingHTTPServer' in srv and 'serve.py' in run, hdr)
    br = pg.context.browser
    pg2 = await br.new_page()
    await pg2.route('**/src/main.js', lambda route: route.fulfill(status=404, body='nope'))
    await pg2.goto(a.url)
    await pg2.wait_for_selector('#boot-fail', timeout=8000)
    t1 = await pg2.inner_text('#boot-fail')
    await pg2.unroute('**/src/main.js')
    await pg2.route('**/src/core/i18n.js', lambda route: route.fulfill(status=200, content_type='text/javascript', body='export const t = ;'))
    await pg2.goto(a.url)
    await pg2.wait_for_selector('#boot-fail', timeout=8000)
    t2 = await pg2.inner_text('#boot-fail')
    await pg2.unroute('**/src/core/i18n.js')
    await pg2.goto('file://' + ROOT + 'index.html')
    await pg2.wait_for_selector('#boot-fail', timeout=8000)
    t3 = await pg2.inner_text('#boot-fail')
    vis = await pg2.evaluate("(() => { const d = document.getElementById('boot-fail'), s = getComputedStyle(d); return [s.color, s.fontSize, d.getBoundingClientRect().width > 300]; })()")
    await pg2.close()
    rd = open(ROOT + 'README.md', encoding='utf-8').read()
    check('m1j D17 index.html вместо чёрного экрана — читаемое сообщение: main.js не загрузился, ошибка в модуле, страница как file://; README и запуск — репозиторий на Gitea strg.gardariki.xyz/i_brachunov/G-2D, не GitHub',
          'Игра не запустилась' in t1 and 'main.js' in t1 and 'Игра не запустилась' in t2 and 'file://' in t3 and 'serve.py' in t3 and vis[2]
          and 'strg.gardariki.xyz/i_brachunov/G-2D' in rd and 'github' not in rd.lower(), {'t1': t1[:60], 't2': t2[:60], 't3': t3[:60], 'vis': vis})

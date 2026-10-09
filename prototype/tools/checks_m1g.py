# Веха m1g: GDD v1.11 (inbox/designer_v1_11.md п.1–6) + декор тупика Мары (art/layout) + пустой футпринт не блокирует. Только миссия 1.
import os, re

ROOT = '/workspace/game/prototype/'
SHOT_MARA = ROOT + 'screenshot_m1g_mara.png'

FRESH = '''(() => { const g = __game; g.ui.closeAll(); delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada');
  const h = g.hero; h.hp = h.maxHp; h.yar = h.maxYar; h.invuln = 0; h.cmd = null; h.action = null; g.state = 'play'; })()'''
TP = '''(([x, y]) => { const h = __game.hero; h.x = x; h.y = y; h.path = null; h.cmd = null; h.action = null; h.moving = false; h.kb = null; h.dashing = null; })'''


async def run_m1g(pg, G, check, wait, client_of, client_scr, a):
    print('--- веха m1g', flush=True)
    await pg.goto(a.url)
    await pg.wait_for_function('() => window.__game && __game.time > 0.2')
    await pg.mouse.click(960, 300)
    await wait(150)

    # ---------- п.1 стартовый пояс
    s = await G('''(async () => { const { Hero } = await import('/src/entities/hero.js'); const { POTIONS } = await import('/src/data/items.js');
        const h = new Hero(10, 10); return { belt: h.belt.map(b => b && [b.kind, b.count]), life1: POTIONS.life1 }; })()''')
    L = s['life1']
    check('m1g п.1 стартовый пояс [life1×2, life1×2, yar1×2, пусто] — 4 слабых зелья жизни; у слабого зелья нет мгновенной части (45 HP за 3 с)',
          s['belt'] == [['life1', 2], ['life1', 2], ['yar1', 2], None] and L['amount'] == 45 and L['dur'] == 3
          and not any(k for k in L if 'inst' in k.lower() or k in ('pct', 'now')), s)

    # ---------- п.2 стаи Залесья
    await G(FRESH)
    s = await G('''(() => { const g = __game, m = g.map, Z = g.zone, P = m.packs, pl = g.enemies.concat(g.buried || []).filter(e => !e.special);
        const kinds = (i) => P[i].kinds.join(','), cnt = (f) => pl.filter(f).length;
        return { p1: kinds(1), p1m: P[1].mlvl, p2: kinds(2), p6: [P[6].x, P[6].y], p7: [P[7].x, P[7].y], ps: Z.mlvlRules.packSize['1'].anchutka,
          n: pl.length, upyr: cnt(e => e.kind === 'upyr'), anch: cnt(e => e.kind === 'anchutka'), m1: cnt(e => e.mlvl === 1), m2: cnt(e => e.mlvl === 2),
          p6reach: pl.filter(e => e.pack === 6).every(e => m.isReachableAt(e.x, e.y)), p6n: pl.filter(e => e.pack === 6).length }; })()''')
    check('m1g п.2 стая 1 — 3 анчутки mlvl 1, стая 2 — 3 упыря + 1 анчутка, стая 6 в (43,5; 29,5) (встаёт целиком, достижима), стая 7 на месте (42,5; 42,5); packSize["1"].anchutka [3, 4]',
          s['p1'] == 'anchutka,anchutka,anchutka' and s['p1m'] == 1 and s['p2'] == 'upyr,upyr,upyr,anchutka' and s['p6'] == [43.5, 29.5]
          and s['p7'] == [42.5, 42.5] and s['ps'] == [3, 4] and s['p6n'] == 3 and s['p6reach'], s)
    check('m1g п.2 в Залесье 28 обычных врагов: 20 упырей / 8 анчуток, 18 mlvl 1 / 10 mlvl 2',
          s['n'] == 28 and s['upyr'] == 20 and s['anch'] == 8 and s['m1'] == 18 and s['m2'] == 10, s)

    # ---------- п.3 Мара: без «Жаркой», свита 3–4 анчутки mlvl 1, плашка, поляна, пепел, предупреждение, трекер
    s = await G('''(() => { const g = __game, Z = g.zone, M = g.enemies.find(e => e.kind === 'mara'), R = g.enemies.filter(e => e.special === 'mara' && e.kind !== 'mara');
        const B = g.dbg.CFG.bosses.mara, D = Z.landmarks.maraDen, c = D.center;
        const trees = g.map.props.filter(p => p.type === 'tree' && Math.hypot(p.x + 0.5 - c[0], p.y + 0.5 - c[1]) <= D.clearR).length;
        const throat = D.ash.filter(([x, y]) => x >= 36 && x <= 49 && y >= 17 && y <= 19).length;
        return { mods: (M.mods || []).length, bmods: B.mods, mlvl: M.mlvl, rn: R.length, rk: [...new Set(R.map(e => e.kind))], rm: [...new Set(R.map(e => e.mlvl))],
          cnt: B.retinue.count, mr: Z.mlvlRules.maraRetinue, clearR: D.clearR, trees, ash: D.ash.length, throat, stumps: (D.stumps || []).length,
          ashProps: g.map.props.filter(p => p.type === 'ash').length, stumpProps: g.map.props.filter(p => p.type === 'stump').length, thinned: g.map.thinned || 0 }; })()''')
    check('m1g п.3 Мара без модификаторов (mods []), свита 3–4 анчутки mlvl 1 (bosses.json [3,4], maraRetinue 1)',
          s['mods'] == 0 and s['bmods'] == [] and s['mlvl'] == 4 and 3 <= s['rn'] <= 4 and s['rk'] == ['anchutka'] and s['rm'] == [1]
          and s['cnt'] == [3, 4] and s['mr'] == 1, s)
    check('m1g п.3/декор поляна clearR 8,9 без деревьев; пепел 19 (10 в горловине x 36–49, y 17–19), пни 13 + южная/юго-восточная кромка прорежена (3 ряда: пни или пусто вместо елей)',
          s['clearR'] == 8.9 and s['trees'] == 0 and s['ash'] == 19 and s['throat'] == 10 and s['ashProps'] == 19 and s['stumps'] == 13
          and s['thinned'] > 0 and 13 < s['stumpProps'] <= 13 + s['thinned'], s)

    # предупреждение: один раз за посещение
    s = await G('''(async () => { const g = __game, h = g.hero, W = g.zone.landmarks.maraDen.warn, tp = ''' + TP + ''';
        g.enemies.filter(e => !e.special).forEach(e => { e.dead = true; }); g._barks = {}; g.speechUntil = 0; g.dialogQ = [];
        const c0 = g.counters.maraWarn || 0; tp([W.x - 4, W.y]); g.simulate(0.2); const far = (g.counters.maraWarn || 0) - c0;
        tp([W.x - 1.5, W.y]); g.simulate(0.2); const once = (g.counters.maraWarn || 0) - c0;
        tp([W.x - 4, W.y]); g.simulate(0.2); tp([W.x, W.y]); g.simulate(0.2); const again = (g.counters.maraWarn || 0) - c0;
        g.enterZone('ladoga', 'from_zalesye'); g.enterZone('zalesye', 'from_ladoga'); tp([W.x, W.y]); g._barks = {}; g.simulate(0.2);
        const visit2 = (g.counters.maraWarn || 0) - c0;
        const log = g.log.lines ? g.log.lines.map(l => l.text || l).filter(t => typeof t === 'string' && t.includes('Пепел ещё тёплый')).length : -1;
        return { far, once, again, visit2, txt: g.dbg.t('bark.m1.mara_warn'), w: [W.x, W.y, W.r, W.once], log }; })()''')
    check('m1g п.3 bark.m1.mara_warn при входе в r 2 у (39,5; 18): вдали — нет, первый вход — 1 раз, повторный вход за то же посещение — нет, новое посещение зоны — снова',
          s['far'] == 0 and s['once'] == 1 and s['again'] == 1 and s['visit2'] == 2 and s['w'] == [39.5, 18, 2, 'visit']
          and s['txt'] == 'Пепел ещё тёплый… Тут кто-то ходит в огне.', s)

    # плашка над Марой — поверх крон, из ru.json
    await G(FRESH)
    s = await G('''(() => { const g = __game, M = g.enemies.find(e => e.kind === 'mara'), tp = ''' + TP + ''';
        g.enemies.filter(e => !e.special).forEach(e => { e.dead = true; });
        tp([M.x - 9.5, M.y + 0.5]); g.hero.invuln = 99; g.updateCamera && g.updateCamera(); return 1; })()''')
    await wait(400)
    s = await G('''(() => { const g = __game; return { np: g.nameplatesDrawn || [], hov: g.hoverEnemy ? g.hoverEnemy.kind : null }; })()''')
    np = [n for n in s['np'] if n['kind'] == 'mara']
    src = open(ROOT + 'src/render/world.js', encoding='utf-8').read()
    check('m1g п.3 плашка Мары без наведения: «Огнея Пепельная · ур. 4» / «Былинный враг», у свиты плашек нет; строки из ru.json (не в коде)',
          len(np) == 1 and np[0]['line1'] == 'Огнея Пепельная · ур. 4' and np[0]['line2'] == 'Былинный враг' and len(s['np']) == 1
          and 'Былинный' not in src and 'Пепельная' not in src, s)
    i_pl, i_cr = src.find('this.renderNameplates(ctx, game, toS)'), src.find('drawProp(')
    check('m1g п.3 плашка рисуется после сцены (крон), света и подписей', i_pl > 0 and i_pl > src.find('this.renderLight(ctx, game, toS)') and i_pl > src.find('this.renderLabels(ctx, game, toS)'), [i_pl, i_cr])
    await pg.screenshot(path=SHOT_MARA)
    check('m1g скриншот плашки Мары: ' + os.path.basename(SHOT_MARA), os.path.exists(SHOT_MARA) and os.path.getsize(SHOT_MARA) > 50000, '')

    # трекер обходит тупик
    s = await G('''(() => { const g = __game, A = g.zone.landmarks.trackerAvoid, tp = ''' + TP + ''';
        const res = {}; for (const [k, p] of Object.entries({ krada: null, den: [61, 16.5], throat: [46.5, 18], hut2: [38, 6] })) {
          if (p) tp(p); else { const kr = g.map.krada; tp([kr.x + 1.6, kr.y + 1.6]); }
          const T = g.trackerPath(); const d = T.pts.map(([x, y]) => Math.hypot(x - A.x, y - A.y)), d0 = Math.hypot(g.hero.x - A.x, g.hero.y - A.y);
          let mono = true; const lim = Math.min(A.r, d0) - 0.6; for (const v of d) if (v < lim) mono = false;
          const last = T.pts[T.pts.length - 1] || [0, 0];
          res[k] = { goal: T.goal, n: T.pts.length, min: +Math.min(...d).toFixed(2), d0: +d0.toFixed(1), mono, endD: +Math.hypot(last[0] - g.objectById(T.target).x, last[1] - g.objectById(T.target).y).toFixed(1) }; }
        return { A: [A.x, A.y, A.r], res }; })()''')
    R = s['res']
    check('m1g п.3 трекер: путь к цели не берёт клеток ближе 16 к (56,5; 16,5) (от крады и избы 2 — ≥ 16; из тупика и горловины — не ближе к центру, чем старт: выводит на запад), доходит до цели',
          s['A'] == [56.5, 16.5, 16] and R['krada']['min'] >= 16 and R['hut2']['min'] >= 16 and all(R[k]['mono'] and R[k]['n'] > 0 and R[k]['endD'] < 2 for k in R), s)

    # ---------- п.4 Залесье 66×48, выход в Ладогу (16; 31)
    s = await G('''(() => { const g = __game, m = g.map, o = g.objectById('to_ladoga'); return { w: m.w, h: m.h, ex: [o.x, o.y, o.to], reach: m.isReachableAt(o.x, o.y) }; })()''')
    check('m1g п.4 Залесье 66×48 (основная часть 48×48 + тупик Мары), выход в Ладогу (16; 31) достижим', s['w'] == 66 and s['h'] == 48 and s['ex'] == [16, 31, 'ladoga'] and s['reach'], s)

    # ---------- п.5 капище realm nebyl
    s = await G('''(() => { const g = __game, CFG = g.dbg.CFG; g.enterZone('kapishche', 'start'); const z = g.zone.realm, n = g.enemies.length;
        const r = { kap: z, zones: ['zalesye', 'trail', 'ladoga'].map(id => (g.zoneStates[id] && g.zoneStates[id].zone.realm) || null), n, id: g.zone.id };
        g.enterZone('zalesye', 'krada'); return r; })()''')
    # m1i (critics_m1f П.16): единственное чтение realm — оттенок темноты в render/world.js (визуал, на правила не влияет)
    jsrc = ''.join(open(os.path.join(dp, f), encoding='utf-8').read() for dp, _, fs in os.walk(ROOT + 'src') for f in fs if f.endswith('.js') and f != 'world.js')
    zone_realm_reads = re.findall(r'zone\.realm|zone\[.realm.\]', jsrc)
    check('m1g п.5 капище realm "nebyl" (Залесье byl, тропа byl_to_nebyl); зона грузится, правила поле realm зоны не читают (m1i: только оттенок темноты)',
          s['kap'] == 'nebyl' and s['id'] == 'kapishche' and s['n'] > 0 and not zone_realm_reads, s)

    # ---------- п.6 подцель Мала: текст сценариста, изба Мала в «Спаси выживших» — один раз
    s = await G('''(() => { const g = __game, q0 = g.quest, q = new q0.constructor(g, 'm1'); g.quest = q;
        q.emit({ event: 'hutFreed', hut: 'hut3' }); q.emit({ event: 'hutFreed', hut: 'hut3' }); const a = [q.get('huts').n, q.get('mal').state];
        q.emit({ event: 'hutFreed', hut: 'hut1' }); q.emit({ event: 'hutFreed', hut: 'hut2' }); const b = [q.get('huts').n, q.get('huts').state];
        g.quest = q0; return { a, b, t: g.dbg.t('quest.m1.obj.mal'), huts: g.dbg.t('quest.m1.obj.huts'), death: g.dbg.t('ui.death.button') }; })()''')
    exp = open(ROOT + 'tools/export_ru.py', encoding='utf-8').read()
    check('m1g п.6 quest.m1.obj.mal = «Вызволи Мала у колодца» (из act1.md, временного ключа в export_ru.py нет); ui.death.button «Очнуться»',
          s['t'] == 'Вызволи Мала у колодца' and 'Вызволи' not in exp and s['death'] == 'Очнуться', s)
    check('m1g п.6 изба Мала засчитывается в «Спаси выживших» один раз: hut3 дважды → 1/3 (цель Мала выполнена), + hut1, hut2 → 3/3',
          s['a'] == [1, 'done'] and s['b'] == [3, 'done'], s)

    # ---------- декор: пустой футпринт не блокирует; проходимость с декором и без совпадает
    s = await G('''(async () => { const { generateMap } = await import('/src/world/map.js'); const { MAP_SEED } = await import('/src/config.js');
        const z = __game.zone, z2 = JSON.parse(JSON.stringify(z)); const D = z2.landmarks.maraDen; D.ash = []; D.stumps = []; delete D.thinSouth;
        const walk = (m) => { let s = ''; for (let y = 0; y < m.sh; y++) for (let x = 0; x < m.sw; x++) s += m.subBlocked(x, y) ? '#' : '.'; return s; };
        const a = generateMap(MAP_SEED, z), b = generateMap(MAP_SEED, z2);
        const sub = (m) => m.subBlocked(Math.floor(46.7 * 2), Math.floor(18.1 * 2)); const before = sub(b);
        b.addProp('ash', 46.2, 17.6, 1, { fp: [46.7, 18.1, 0, 0] }); const after = sub(b);
        return { same: walk(a) === walk(b), before, after, thin: a.thinned, forest: (() => { let ok = true; for (const p of a.props) if (p.type === 'stump' && p.x >= 46 && Math.hypot(p.x + .5 - 56.5, p.y + .5 - 16.5) > 9.5) ok = ok && a.isBlocked(Math.floor(p.x), Math.floor(p.y)); return ok; })() }; })()''')
    check('m1g декор: проп с пустым футпринтом (0×0) на нецелой ½-координате не блокирует (было: стенка ½ тайла в горловине (46,5; 18)); проходимость Залесья с декором и без — побитно одна',
          s['same'] and not s['before'] and not s['after'], s)
    check('m1g декор: на месте снятых елей южной кромки — пни, лес там по-прежнему непроходим', s['thin'] > 0 and s['forest'], s)
    s = await G('''(async () => { const r = await fetch('/assets/fx/prop_stump_burnt.png'); const j = await fetch('/assets/fx/prop_stump_burnt.json'); return [r.status, j.status]; })()''')
    check('m1g декор: спрайт prop_stump_burnt (png + json) в assets/fx', s == [200, 200], s)
    await G(FRESH)

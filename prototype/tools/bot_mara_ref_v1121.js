// Справочный бот Огнеи Пепельной (id mara), правила GDD v1.12.1 §9.3 «разумный игрок 4 ур.».
// window.__N, __SEED, __LVL, __POT, __CAP как в tools/bot_mara_ref.js; __RULE: 'v1121' (по умолчанию) | 'petr' (правила m1g);
// __FLEE (0 по умолчанию: справка без отхода, §9.3; 1 — справочный вариант с отходом), __PATCH — строка кода (async, аргументы g, CFG) для промеров вариантов цифр.
(async () => { const g = __game; const { Hero } = await import('/src/entities/hero.js'); const { makeRng } = await import('/src/core/rng.js'); const { CFG } = await import('/src/data/config.js'); const rnd0 = Math.random;
  const N = window.__N || 30, SEED = window.__SEED ?? 7, LVL = window.__LVL || 4, POT = window.__POT ?? 6, CAP = window.__CAP || 180, DT = 1 / 60;
  const RULE = window.__RULE || 'v1121', V = RULE === 'v1121', FLEE = V && (window.__FLEE ?? 0), STEP = V && (window.__STEP ?? 1);
  if (window.__PATCH) await (new (Object.getPrototypeOf(async function(){}).constructor)('g', 'CFG', window.__PATCH))(g, CFG);
  g.simHold = true; Math.random = makeRng(SEED);
  const runs = []; let MM = null;
  for (let n = 0; n < N; n++) {
    delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const m = g.map;
    g.enemies.splice(0, g.enemies.length, ...g.enemies.filter(e => e.special === 'mara')); g.buried && g.buried.splice(0);
    const h = new Hero(49, 18); h.belt = [null, null, null, null]; for (const it of h.inv.items.filter(i => i.kind === 'potion' || i.kind === 'scroll')) h.inv.remove(it);
    for (let i = 0, left = POT; left > 0; i++) { const c = Math.min(2, left); h.belt[i] = { kind: 'life1', count: c }; left -= c; }
    g.hero = h; let need = 0; for (let L = 1; L < LVL; L++) need += g.dbg.xpToNext(L); h.gainXp(need, g);
    while (h.points > 0) for (const a of ['vit', 'vit', 'str', 'str', 'dex']) if (h.points > 0) h.spendPoint(a);
    if (V) { let k = 0; while (h.skillPoints > 0 && k++ < 10) { if (h.learn('sshibka', g)) break; } }   // все очки навыков — в «Сшибку»
    else while (h.skillPoints > 0) { if (!h.learn('sshibka', g)) break; }
    h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar;
    const grp = () => g.enemies.filter(e => !e.dead && e.special === 'mara'), M = g.enemies.find(e => e.kind === 'mara');
    MM = M; const ret = g.enemies.filter(e => e.special === 'mara' && e.kind !== 'mara').length;
    const trailAt = (x, y, pad) => g.combat.fires.some(f => f.kind === 'trail' && Math.hypot(x - f.x, y - f.y) <= f.r + pad);
    let tt = 0, drunk = 0, minHp = 1, inFire = 0, stepT = 0, steps = 0, fled = false, trail0 = 0;
    const res = g.simulate(CAP, () => { tt += DT; if (h.dead || M.dead) return true;
      minHp = Math.min(minHp, h.hp / h.maxHp);
      const left = h.belt.reduce((a, b) => a + (b && b.kind === 'life1' ? b.count : 0), 0);
      if (h.hp < h.maxHp * 0.5) { const s = h.belt.findIndex(b => b && b.kind === 'life1' && b.count > 0); if (s >= 0 && h.canDrink('life1', g)) { if (h.drink(s, g) !== false) drunk++; } }
      // отход: зелий нет и HP < 25% — уходит назад в горловину (за поводок 8 от центра круга)
      if (FLEE && (fled || (left === 0 && h.hp < h.maxHp * 0.25))) { if (!fled) { fled = true; h.moveTo(m, 40, 18); } if (h.x < 44) return true; if (!h.cmd || h.cmd.type !== 'move') h.moveTo(m, 40, 18); return false; }
      // пепельный след: заметил, что стоит в огне (реакция 0,4 с) — шаг 1,5 тайла на ближнюю к цели чистую точку
      if (STEP) { if (stepT > 0) { stepT -= DT; if (h.cmd && h.cmd.type === 'move') return false; }
        if (trailAt(h.x, h.y, h.r * 0.5)) inFire += DT; else inFire = 0;
        if (inFire >= 0.4) { const c = h.cmd && h.cmd.type === 'attack' && h.cmd.target && !h.cmd.target.dead ? h.cmd.target : M; let best = null, bd = 1e9;
          for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4, x = h.x + Math.cos(a) * 1.5, y = h.y + Math.sin(a) * 1.5;
            if (m.blockedAt(x, y) || trailAt(x, y, h.r)) continue; const d = Math.hypot(x - c.x, y - c.y); if (d < bd) { bd = d; best = [x, y]; } }
          if (best) { h.moveTo(m, best[0], best[1]); stepT = 0.6; inFire = 0; steps++; return false; } } }
      let t = null, bd = 1e9;
      if (V) { const c = h.cmd; if (c && c.type === 'attack' && c.target && !c.target.dead) t = c.target; }   // цель держит до смерти
      if (!t) for (const e of grp()) { const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; t = e; } }
      if (t && (!h.cmd || h.cmd.type !== 'attack' || h.cmd.target !== t)) h.attack(t, false, h.lmbSkill(), true);
      return false; });
    runs.push({ res: h.dead ? 'death' : M.dead ? 'win' : fled ? 'fled' : 'timeout', t: +tt.toFixed(1), drunk, ret, steps, lvl: h.level, maxHp: h.maxHp, minHp: +minHp.toFixed(2), trail: Math.round(M.trailDealt || 0) });
  }
  g.simHold = false; Math.random = rnd0;
  const ts = runs.map(r => r.t).sort((a, b) => a - b), md = a => { const b = [...a].sort((x, y) => x - y); return b[Math.floor(b.length / 2)]; };
  return { seed: SEED, rule: RULE, lvl: LVL, pot: POT, runs: N, deaths: runs.filter(r => r.res === 'death').length, wins: runs.filter(r => r.res === 'win').length,
           timeouts: runs.filter(r => r.res === 'timeout').length, medianT: ts[Math.floor(ts.length / 2)], retinue: [...new Set(runs.map(r => r.ret))],
           drunkAvg: +(runs.reduce((a, r) => a + r.drunk, 0) / N).toFixed(1),
           mara: { mlvl: MM.mlvl, mods: (MM.mods || []).length, hp: MM.maxHp, dmg: [MM.dmgMin, MM.dmgMax] },
           extra: { fled: runs.filter(r => r.res === 'fled').length, steps: md(runs.map(r => r.steps)), trailMed: md(runs.map(r => r.trail)), heroMaxHp: runs[0].maxHp, minHpMed: md(runs.map(r => r.minHp)) } };
})()

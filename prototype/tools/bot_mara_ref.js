// Справочный замер Мары (GDD v1.11 §5.3/§9.3, inbox/designer_v1_11.md п.3): «герой 4 ур. с 6 слабыми зельями — гибель ≤ 10/30».
// Запуск: page.evaluate(файл) на index.html?seed=7; window.__N (30), window.__SEED (7), window.__LVL (4), window.__POT (6), window.__CAP (180).
// Правила бота (m1g, разработчик; по описанию Марфы «бьётся стоя, пьёт при 50%»):
//  - свежее Залесье (Мара со свитой по bosses.json), остальные враги зоны убраны; герой — новый Hero со стартовым снаряжением;
//  - уровень __LVL: опыт до уровня, очки — как у бота Залесья (2 Жив / 2 Сила / 1 Ловк), очко навыка — в «Сшибку»;
//  - пояс: только __POT слабых зелий жизни (по 2 в ячейке), Яри и бересты нет; пьёт, когда HP < 50% (с учётом отката пояса);
//  - window.__FOCUS = 1 — вариант: бьёт саму Мару, свиту не трогает (справочно);
//  - старт у входа на поляну (49; 18), цель — ближайший живой из группы Мары, ЛКМ «Сшибка»; не отступает, без ПКМ и рывка;
//  - бой кончается гибелью героя, гибелью Мары (победа; свиту можно не добивать) или пределом __CAP с (тайм-аут).
(async () => { const g = __game; const { Hero } = await import('/src/entities/hero.js'); const { makeRng } = await import('/src/core/rng.js'); const rnd0 = Math.random;
  const N = window.__N || 30, SEED = window.__SEED ?? 7, LVL = window.__LVL || 4, POT = window.__POT ?? 6, CAP = window.__CAP || 180, FOCUS = !!window.__FOCUS, DT = 1 / 60;
  g.simHold = true; Math.random = makeRng(SEED);
  const runs = [];
  for (let n = 0; n < N; n++) {
    delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const m = g.map;
    g.enemies.splice(0, g.enemies.length, ...g.enemies.filter(e => e.special === 'mara')); g.buried && g.buried.splice(0);
    const h = new Hero(49, 18); h.belt = [null, null, null, null]; for (const it of h.inv.items.filter(i => i.kind === 'potion' || i.kind === 'scroll')) h.inv.remove(it);
    for (let i = 0, left = POT; left > 0; i++) { const c = Math.min(2, left); h.belt[i] = { kind: 'life1', count: c }; left -= c; }
    g.hero = h; let need = 0; for (let L = 1; L < LVL; L++) need += g.dbg.xpToNext(L); h.gainXp(need, g);
    while (h.points > 0) for (const a of ['vit', 'vit', 'str', 'str', 'dex']) if (h.points > 0) h.spendPoint(a);
    while (h.skillPoints > 0) { if (!h.learn('sshibka', g)) break; }
    h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar;
    const grp = () => g.enemies.filter(e => !e.dead && e.special === 'mara'), M = g.enemies.find(e => e.kind === 'mara');
    const ret = g.enemies.filter(e => e.special === 'mara' && e.kind !== 'mara').length;
    let tt = 0, drunk = 0, minHp = 1;
    g.simulate(CAP, () => { tt += DT; if (h.dead || M.dead) return true;
      minHp = Math.min(minHp, h.hp / h.maxHp);
      if (h.hp < h.maxHp * 0.5) { const s = h.belt.findIndex(b => b && b.kind === 'life1' && b.count > 0); if (s >= 0 && h.canDrink('life1', g)) { if (h.drink(s, g) !== false) drunk++; } }
      let t = FOCUS && !M.dead ? M : null, bd = 1e9; if (!t) for (const e of grp()) { const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; t = e; } }
      if (t && (!h.cmd || h.cmd.type !== 'attack' || h.cmd.target !== t)) h.attack(t, false, h.lmbSkill(), true);
      return false; });
    runs.push({ res: h.dead ? 'death' : M.dead ? 'win' : 'timeout', t: +tt.toFixed(1), drunk, ret, lvl: h.level, maxHp: h.maxHp, minHp: +minHp.toFixed(2) });
  }
  g.simHold = false; Math.random = rnd0;
  const ts = runs.map(r => r.t).sort((a, b) => a - b);
  return { seed: SEED, focus: FOCUS, retMlvl: [...new Set(g.enemies.filter(e => e.special === 'mara' && e.kind !== 'mara').map(e => e.mlvl))], lvl: LVL, pot: POT, runs: N, deaths: runs.filter(r => r.res === 'death').length, wins: runs.filter(r => r.res === 'win').length,
           timeouts: runs.filter(r => r.res === 'timeout').length, medianT: ts[Math.floor(ts.length / 2)], retinue: [...new Set(runs.map(r => r.ret))],
           drunkAvg: +(runs.reduce((a, r) => a + r.drunk, 0) / N).toFixed(1), heroLvl: runs[0].lvl, heroMaxHp: runs[0].maxHp,
           mara: { mlvl: g.enemies.find(e => e.kind === 'mara')?.mlvl, mods: (g.enemies.find(e => e.kind === 'mara')?.mods || []).length } };
})()

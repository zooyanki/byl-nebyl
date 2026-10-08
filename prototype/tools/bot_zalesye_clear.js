// Эталонный бот зачистки Залесья (GDD v1.9 §9.3, журнал п.1; inbox/designer_v1_9.md п.1). Запуск: page.evaluate(файл) на index.html?seed=7;
// window.__N (30), window.__SEED (7), window.__CAP (400). Воспроизводимо: живой цикл держится (g.simHold), зерно — makeRng(__SEED) на всю серию.
//  - герой 1 ур., пояс пуст, без зелий, добычу не подбирает, без ПКМ и рывка;
//  - на каждом уровне сразу 2 Жив / 2 Сила / 1 Ловк, очко навыка — в «Сшибку»;
//  - цель — ближайший живой обычный враг (Мару и свиту не трогает), ЛКМ «Сшибка»;
//  - отступает к ближайшему тихому кругу, если HP < 35% и в погоне > 2 врагов, или HP < 25%; стоит до HP ≥ 90%; один вход в круг — один отдых;
//  - из круга не бьёт; цель ближе 3 тайлов — выходит на 1,5 тайла за границу круга в её сторону;
//  - 1,5 с без движения — шаг в сторону на 0,6 с; 20 с без убийства — цель пропускается на 10 с;
//  - предел 400 с; прогон без конца и без гибели — «застрял» (считается отдельно).
(async () => { const g = __game; const { Hero } = await import('/src/entities/hero.js'); const { makeRng } = await import('/src/core/rng.js'); const rnd0 = Math.random;
  const N = window.__N || 30, SEED = window.__SEED ?? 7, CAP = window.__CAP || 400, DT = 1 / 60;
  g.simHold = true; Math.random = makeRng(SEED);
  const runs = [];
  for (let n = 0; n < N; n++) {
    delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const m = g.map, k = m.krada;
    const h = new Hero(k.x + 1.6, k.y + 1.6); h.belt = [null, null, null, null]; for (const it of h.inv.items.filter(i => i.kind === 'potion')) h.inv.remove(it);
    h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar; g.hero = h; g.counters.pickups = 0;
    const circles = (g.zone.safeZones || []).map(z => ({ c: m[z.at], r: z.radius })).filter(z => z.c);
    const inCircle = (x, y) => circles.find(z => Math.hypot(x - z.c.x, y - z.c.y) < z.r) || null;
    const plain = () => g.enemies.filter(e => !e.dead && !e.special);
    const levelUp = () => { while (h.points > 0) { for (const a of ['vit', 'vit', 'str', 'str', 'dex']) if (h.points > 0) h.spendPoint(a); }
      while (h.skillPoints > 0) { if (h.learn('sshibka', g)) break; } };
    let tt = 0, rests = 0, retreat = false, resting = false, pulled = false, still = 0, side = 0, sideDir = 1, px = h.x, py = h.y;
    let lastKill = 0, alive0 = plain().length, skip = new Map(), stepOut = null, unstick = 0, skips = 0, minHp = 1;
    const M = g.enemies.find(e => e.kind === 'mara');
    g.simulate(CAP, () => { tt += DT; if (h.dead) return true; const P = plain(); if (!P.length) return true;
      if (h.points > 0 || h.skillPoints > 0) levelUp();
      minHp = Math.min(minHp, h.hp / h.maxHp);
      if (M && M.state !== 'idle') pulled = true;
      if (P.length < alive0) { alive0 = P.length; lastKill = tt; }
      const here = inCircle(h.x, h.y);
      // отступление и отдых
      const chasing = P.filter(e => e.state === 'chase' || e.state === 'attack').length;
      if (!retreat && ((h.hp < h.maxHp * 0.35 && chasing > 2) || h.hp < h.maxHp * 0.25)) { retreat = true; resting = false; }
      if (retreat) {
        if (here) { if (!resting) { resting = true; rests++; } h.cmd = null; h.path = null;
          if (h.hp >= h.maxHp * 0.9) { retreat = false; resting = false; } else return false; }
        else { const z = circles.slice().sort((a, b) => Math.hypot(a.c.x - h.x, a.c.y - h.y) - Math.hypot(b.c.x - h.x, b.c.y - h.y))[0];
          if (!h.cmd || h.cmd.type !== 'move') h.moveTo(m, z.c.x + 1.2, z.c.y + 1.2); still = 0; px = h.x; py = h.y; return false; }
      }
      // залипание: 1,5 с без движения — шаг в сторону 0,6 с
      if (Math.hypot(h.x - px, h.y - py) < 0.02 && !h.action) still += DT; else { still = 0; px = h.x; py = h.y; }
      if (side > 0) { side -= DT; return false; }
      if (still > 1.5) { still = 0; side = 0.6; unstick++; sideDir = -sideDir; const t0 = h.cmd && h.cmd.target; const ang = t0 ? Math.atan2(t0.y - h.y, t0.x - h.x) : 0;
        h.cmd = null; h.moveTo(m, h.x + Math.cos(ang + sideDir * Math.PI / 2) * 1.5, h.y + Math.sin(ang + sideDir * Math.PI / 2) * 1.5); return false; }
      // цель: ближайший обычный враг, кроме пропущенных
      let t = null, bd = 1e9; for (const e of P) { if ((skip.get(e) || 0) > tt) continue; const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; t = e; } }
      if (!t) return false;
      if (tt - lastKill > 20) { skip.set(t, tt + 10); lastKill = tt; skips++; h.cmd = null; return false; }
      // из круга не бьём: цель ближе 3 тайлов — выйти на 1,5 тайла за границу в её сторону
      if (here) { if (bd < 3) { const a = Math.atan2(t.y - here.c.y, t.x - here.c.x), R = here.r + 1.5; const x = here.c.x + Math.cos(a) * R, y = here.c.y + Math.sin(a) * R;
          if (!h.cmd || h.cmd.type !== 'move') h.moveTo(m, x, y); return false; }
        if (!h.cmd || h.cmd.type !== 'attack' || h.cmd.target !== t) h.attack(t, false, h.lmbSkill(), true);
        if (h.cmd && h.cmd.type === 'attack' && bd < 3) h.cmd = null; return false; }
      if (!h.cmd || h.cmd.type !== 'attack' || h.cmd.target !== t || h.cmd.target.dead) h.attack(t, false, h.lmbSkill(), true);
      return false; });
    const left = plain().length, res = h.dead ? 'death' : left === 0 ? 'clear' : 'stuck';
    runs.push({ n, res, t: +tt.toFixed(1), rests, pulled, lvl: h.level, left, unstick, skips, minHp: +minHp.toFixed(2), sk: h.skills.sshibka, vit: h.base.vit });
  }
  g.simHold = false; Math.random = rnd0;
  const clear = runs.filter(r => r.res === 'clear'), ts = clear.map(r => r.t).sort((a, b) => a - b), all = runs.map(r => r.t).sort((a, b) => a - b);
  const med = (a) => a.length ? (a.length % 2 ? a[(a.length - 1) / 2] : +((a[a.length / 2 - 1] + a[a.length / 2]) / 2).toFixed(1)) : null;
  return { seed: SEED, runs: N, clear: clear.length, deaths: runs.filter(r => r.res === 'death').length, stuck: runs.filter(r => r.res === 'stuck').length,
           median: med(ts), medianAll: med(all), min: ts[0] ?? null, max: ts[ts.length - 1] ?? null, rests12: runs.filter(r => r.rests >= 1 && r.rests <= 2).length,
           restsHist: runs.reduce((o, r) => (o[r.rests] = (o[r.rests] || 0) + 1, o), {}), pulls: runs.filter(r => r.pulled).length,
           lvl: runs.reduce((o, r) => (o[r.lvl] = (o[r.lvl] || 0) + 1, o), {}), unstick: runs.reduce((a, r) => a + r.unstick, 0), skips: runs.reduce((a, r) => a + r.skips, 0),
           det: runs.map(r => [r.t, r.res[0], r.rests, r.lvl, r.left, r.minHp]) };
})()

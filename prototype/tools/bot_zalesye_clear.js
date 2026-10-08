// Бот зачистки Залесья (GDD v1.8.1 §9.3, B-31): 30 прогонов, герой 1 ур. без зелий, бьёт ближайшего обычного врага (Мару и свиту не трогает),
// при HP < 40% уходит в ближайший тихий круг (крада / Чуров камень) и отдыхает до полного; из тихого круга не бьёт. Мара втянута = вышла из idle.
// Запуск: page.evaluate(содержимое файла) на index.html?seed=7. Результат 08.10 — REPORT_m1c.md §5.
(async () => { const g = __game; const { Hero } = await import('/src/entities/hero.js'); const rnd0 = Math.random;
  const res = { runs: 0, deaths: 0, time: [], rests: 0, pulls: 0, left: [], pulled: [], restHp: [] };
  const N = window.__N || 30; res.det = []; for (let n = 0; n < N; n++) { delete g.zoneStates.zalesye; g.enterZone('zalesye', 'krada'); const m = g.map, k = m.krada;
    const h = new Hero(k.x + 1.6, k.y + 1.6); let lv = 0; while (h.level < 1 && lv++ < 3) h.gainXp(g.dbg.xpToNext(h.level), g); h.recalc(); h.hp = h.maxHp; h.yar = h.maxYar; h.belt = [null, null, null, null]; g.hero = h;
    if (window.__noMara) g.enemies = g.enemies.filter(e => e.special !== 'mara');
    const plain = () => g.enemies.filter(e => !e.dead && !e.special);
    let tt = 0, restN = 0, resting = false, pulled = false, retreat = false, px = h.x, py = h.y, still = 0, bail = 0;
    g.simulate(400, () => { tt += 1 / 60; if (h.dead) return true; if (!plain().length) return true;
      if (Math.hypot(h.x - px, h.y - py) < 0.02 && !h.action) still += 1 / 60; else { still = 0; px = h.x; py = h.y; }
      if (still > 1.5 && !retreat && !g.safeAt(h.x, h.y)) { bail = 0.6; still = 0; }
      if (bail > 0) { bail -= 1 / 60; if (!h.cmd || h.cmd.type !== 'move') h.moveTo(m, h.x + (n % 2 ? 2.5 : -2.5), h.y + 1.5); return false; }
      const M = g.enemies.find(e => e.kind === 'mara'); if (M && M.state !== 'idle') pulled = true;
      
      const need = h.hp < h.maxHp * 0.4 || ((resting || retreat) && h.hp < h.maxHp * 0.98); if (need) retreat = true;
      if (need && !g.safeAt(h.x, h.y)) { const cs = [k, m.churStone].filter(Boolean).sort((a, b) => Math.hypot(a.x - h.x, a.y - h.y) - Math.hypot(b.x - h.x, b.y - h.y))[0]; if (!h.cmd || h.cmd.type !== 'move') h.moveTo(m, cs.x + 1.2, cs.y + 1.2); return false; }
      if (need && g.safeAt(h.x, h.y)) { if (!resting) { restN++; resting = true; } h.cmd = null; return false; }
      resting = false; retreat = false;   // отдых — бот сам ушёл в тихий круг (HP < 50%) и стоит до восстановления
      let t = null, bd = 1e9; for (const e of plain()) { const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; t = e; } }
      if (t && g.safeAt(h.x, h.y) && bd < 3) { if (!h.cmd || h.cmd.type !== 'move') h.moveTo(m, t.x, t.y); return false; }   // из тихого круга не бьём: враг там лечится (сброс в idle)
      if (t && (!h.cmd || h.cmd.type !== 'attack' || h.cmd.target.dead)) h.attack(t, false, h.lmbSkill(), true);
      return false; });
    res.runs++; if (h.dead) res.deaths++; res.time.push(+tt.toFixed(1)); if (restN >= 1 && restN <= 2) res.rests++; if (pulled) { res.pulls++; res.pulled.push(n); }
    res.left.push(plain().length); res.det.push([+tt.toFixed(0), h.dead ? 'D' : '', plain().length, h.level, restN, h.cmd && h.cmd.type, +h.x.toFixed(1), +h.y.toFixed(1)]); }
  res.time.sort((a, b) => a - b); const med = res.time[Math.floor(N / 2)]; const mean = +(res.time.reduce((a, b) => a + b, 0) / res.time.length).toFixed(1);
  const out = { runs: res.runs, deaths: res.deaths, median: med, mean, min: res.time[0], max: res.time[N - 1], rests12: res.rests, pulls: res.pulls, left: Math.max(...res.left), det: res.det };
  Math.random = rnd0; return out; })()

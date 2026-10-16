// Копия автотеста дизайнера gamedesign/work/e1/e1_autotest.js (GDD v1.14 §12.4.1 E1) — в наборе: checks_m1l.py, раздел v1.14.
// v1.14 E1 автотест (GDD §12.4 E1, §12.3): «клик по врагу — подойти и ударить, без взмахов в воздух».
// Запуск: page.evaluate(файл) после новой игры. Возвращает {pass, checks:[...]}.
(async () => {
  const g = __game; const { makeRng } = await import('/src/core/rng.js'); const rnd0 = Math.random; const checks = [];
  const M = (g.dbg && g.dbg.CFG && g.dbg.CFG.stats && g.dbg.CFG.stats.melee) || { reach: 0.75, slack: 0.55 };
  const stand = () => { const h = g.hero; g.state = 'play'; g.paused = false; g.ui.closeAll(); g.enterZone('zalesye', 'krada'); g.enemies = []; g.buried = [];
    g.combat.projectiles = []; g.notice = null; g.rewardCard = null; h.x = 34; h.y = 21; h.stop(); h.action = null; h.invuln = 0; h.maxHp = 1e5; h.hp = 1e5;
    for (let i = 0; i < 6; i++) { g.update(1 / 60); g.input.endFrame(); } return h; };
  const click = (e, shift = false) => { const [sx, sy] = g.toU(e.x, e.y); g.input.mx = sx; g.input.my = sy - (e.def.height || 30) * 0.5 * 2 / 3; /* v2art r2: мышь — в слое интерфейса */ g.input.leftPressed = true; g.input.shift = shift; };
  const step = (n) => { for (let i = 0; i < n; i++) { g.update(1 / 60); g.input.endFrame(); } };
  const spy = () => { const r = { swings: [], air: 0 }; const o = g.combat.heroMelee.bind(g.combat);
    g.combat.heroMelee = (h, t, s) => { const gap = t ? h.gapTo(t) : 9; r.swings.push(+gap.toFixed(2)); if (!t || gap > M.reach + M.slack) r.air++; o(h, t, s); }; r.off = () => { g.combat.heroMelee = o; }; return r; };
  // T1: упырь в 2,5 тайла по 8 направлениям — герой подходит, удар по цели (зазор ≤ reach + slack), начало замаха при зазоре ≤ reach
  { let ok = 0, bad = []; for (let k = 0; k < 8; k++) { Math.random = makeRng(10 + k); const h = stand(); const a = k * Math.PI / 4;
      const e = g.spawnTest('upyr', 34 + Math.cos(a) * 2.5, 21 + Math.sin(a) * 2.5, 1); e.state = 'idle'; e.hp = e.maxHp = 999;
      const sp = spy(); let gap0 = null; click(e); for (let f = 0; f < 120 && !sp.swings.length; f++) { step(1); if (h.action && h.action.type === 'attack' && gap0 == null) gap0 = h.gapTo(e); } sp.off();
      if (sp.swings.length && !sp.air && gap0 != null && gap0 <= M.reach + 0.05) ok++; else bad.push({ k, gap0, sw: sp.swings }); }
    checks.push({ id: 'E1-T1 подход и удар по цели в 8 направлениях', pass: ok === 8, bad }); }
  // T2: анчутка отскакивает во время замаха — замах снимается, Удаль не теряется, приказ продолжается; удара в воздух нет
  { let air = 0, cancels = 0, connected = 0; for (let n = 0; n < 20; n++) { Math.random = makeRng(40 + n); const h = stand();
      const e = g.spawnTest('anchutka', 35.2, 21, 1); e.state = 'idle'; e.hp = e.maxHp = 999; const sp = spy(); const c0 = g.counters.swingCancel || 0;
      click(e); for (let f = 0; f < 240; f++) { step(1); if (h.action && h.action.type === 'attack' && !h.action.fired && h.action.t > 0.1 && e.state !== 'flee') e.scare(e.x - h.x, e.y - h.y, 0.6); if (sp.swings.length) break; }
      sp.off(); air += sp.air; cancels += (g.counters.swingCancel || 0) - c0; if (sp.swings.length && !sp.air) connected++; }
    checks.push({ id: 'E1-T2 отскок цели во время замаха: 0 ударов в воздух, замах снимается', pass: air === 0 && cancels > 0, air, cancels, connected }); }
  // T3: смешанная стая (3 упыря, 2 анчутки, поджигатель), 20 зёрен × 25 с, клики по врагам в 1,5–3,5 тайла — 0 ударов в воздух
  { let air = 0, swings = 0; for (let n = 0; n < 20; n++) { Math.random = makeRng(500 + n); const h = stand();
      for (const k of ['upyr', 'upyr', 'upyr', 'anchutka', 'anchutka', 'chernoyarets_arsonist']) { let x, y; do { const a = Math.random() * 6.283, d = 3 + Math.random() * 3; x = 34 + Math.cos(a) * d; y = 21 + Math.sin(a) * d; } while (g.map.blockedAt(x, y));
        const e = g.spawnTest(k, x, y, 1); e.hp = e.maxHp = 400; e.aggro(g, false); }
      step(6); const sp = spy();
      for (let f = 0; f < 60 * 25; f++) { const live = g.enemies.filter(e => !e.dead); if (!live.length) break;
        if (!h.cmd && !h.action) { const c = live.filter(e => { const d = h.distTo(e); return d > 1.5 && d < 3.5; }); click(c.length ? c[Math.floor(Math.random() * c.length)] : live.sort((a, b) => h.distTo(a) - h.distTo(b))[0]); }
        step(1); }
      sp.off(); air += sp.air; swings += sp.swings.length; }
    checks.push({ id: 'E1-T3 смешанная стая 20 зёрен: 0 ударов в воздух', pass: air === 0 && swings > 300, air, swings }); }
  // T4: Shift+ЛКМ — удар на месте (D2): по цели в 2,5 тайла взмах в воздух со следом и свистом, по цели рядом — попадание
  { Math.random = makeRng(77); const h = stand(); const e = g.spawnTest('upyr', 36.5, 21, 1); e.state = 'idle'; e.hp = e.maxHp = 999; e.speed = 0;
    const x0 = h.x; const a0 = g.counters.airSwing || 0; click(e, true); step(50); const moved = Math.abs(h.x - x0);
    checks.push({ id: 'E1-T4 Shift+ЛКМ: на месте, в воздух — след и свист', pass: moved < 0.05 && (g.counters.airSwing || 0) > a0, moved }); }
  Math.random = rnd0;
  return { pass: checks.every(c => c.pass), checks };
})()

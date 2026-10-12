// Копия gamedesign/work/e2/block_policy.js («разумный блокирующий», GDD v1.14 §4.7, §9.3) для справочных замеров m1l (--block у run_bot_*.py / run_krivsha_pool.py).
// v1.14 E2: «разумный блокирующий» — слой поверх любого бота. Каждый кадр решает, держать ли щит (hero.blockWant):
//  1) телеграф когтей Кривши (конус) накрывает героя и до удара ≤ 0,45 с → щит к Кривше (только если тяжёлые удары щит держит, heavyBlock !== false);
//  2) вражеский снаряд летит в героя (промах по перпендикуляру < r + 0,25), до попадания ≤ 0,4 с → щит к снаряду;
//  3) замах врага ближнего боя (до удара ≤ 0,3 с, враг в досягаемости) — только если замахиваются двое и больше или HP < 50%.
//  Удали меньше цены удара — не поднимает. Огонь по земле не прикрывает (щит его не держит).
(() => { const g = __game; if (g.__blockPolicy) return 'already';
  const orig = g.update.bind(g); const st = { frames: 0, want: 0 };
  g.update = function (dt) {
    const h = g.hero;
    if (h && !h.dead && h.hasShield && h.hasShield()) {
      const B = (g.dbg && g.dbg.CFG && g.dbg.CFG.stats.block) || { cost: 2, costHeavy: 5 }; let th = null;
      if (B.heavyBlock !== false) for (const T of g.combat.teles) if (T.src && T.src.boss !== undefined && T.shape === 'cone' && T.dur - T.t <= 0.45 && g.combat.inTele(T, h.x, h.y, h.r)) th = [T.src.x, T.src.y];
      if (!th) for (const p of g.combat.projectiles) { if (!p.hostile || p.dead) continue; const rx = h.x - p.x, ry = h.y - p.y, v = Math.hypot(p.vx, p.vy) || 1;
        const along = (rx * p.vx + ry * p.vy) / v, perp = Math.abs(rx * p.vy - ry * p.vx) / v; if (along > 0 && perp < h.r + 0.25 && along / v <= 0.4) { th = [p.x, p.y]; break; } }
      if (!th) { const att = g.enemies.filter(e => !e.dead && e.state === 'attack' && !e.attackFired && !e.def.ranged && e.distTo(h) <= (e.def.reach || 1) + h.r + 0.35);
        const soon = att.filter(e => (e.hitAt ?? e.def.hitAt ?? 0.5) - e.t <= 0.3);
        if (soon.length && (att.length >= 2 || h.hp < h.maxHp * 0.5)) th = [soon[0].x, soon[0].y]; }
      const cost = th ? B.cost : 0;
      h.blockWant = th && h.yar >= cost ? { x: th[0], y: th[1] } : null; if (h.blockWant) st.want++;
    }
    st.frames++; return orig(dt);
  };
  g.__blockPolicy = st; return 'on';
})()

"""Решения дизайнера GDD v1.8 по вехе (б) (журнал v1.8, §4.1, §5, §8.2, §9.2–9.3, §12.3, §15): проверки и замеры.
Вызываются из checks_m1c.run_m1c (короткие серии); полный замер §12.3 по 30 боёв — `verify_playwright.py --balance-v18`
(результат — tools/balance_m1c.json)."""
import json
import os
from checks_m1b import REF_HERO, SEEDED

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAL_OUT = os.path.join(ROOT, 'tools', 'balance_m1c.json')

# Бот замера (GDD v1.8 §9.3 «Условия замера»): эталонный герой 6 ур. §9.1, «Сшибка» 3, бьёт стоя, телеграфы не обходит.
# hearths: сколько огнищ НЕ отбито (0 — фазы нет); refill — HP восполняется (замер времени); clear — «сначала призванные»;
# kit — запас зелий {life1, zhivaya, yar1}: жизнь при HP < 50% (КД 1 с), живая вода при HP < 25%, Ярь при Яри < 3.
# Цель — ЛКМ по Кривше (lmb: правило заслона §4.1 v1.8 само бьёт призванного, вставшего на пути).
FIGHT = '''(() => { window.__fight = async (o) => { const g = __game; ''' + REF_HERO + '''
  const res = [];
  for (let i = 0; i < o.runs; i++) {
    delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map; g.enemies = []; g.buried = [];
    m.hearths.forEach((x, j) => { if (j < 3 - o.hearths) { x.done = true; if (x.prop) x.prop.cursed = false; } });
    const h = await mkRef(6, [m.idol.x, m.idol.y + 3]); g.applyChad(); const b = g.riseBoss('test'); const kit = o.kit ? { ...o.kit } : null;
    const used = { life1: 0, zhivaya: 0, yar1: 0 }; let tt = 0, hpMin = 1; g.counters.krivshaSummons = 0; g.counters.blockerHits = 0; g.counters.krivshaClaws = 0; g.counters.krivshaClawHits = 0;
    const drink = (k) => { if (!kit || !(kit[k] > 0) || !h.canDrink(k, g)) return; h.applyPotion(k, g); kit[k]--; used[k]++; };
    g.simulate(o.limit || 300, () => { tt += 1 / 60;
      if (o.refill) h.hp = h.maxHp * 50;
      hpMin = Math.min(hpMin, h.hp / h.maxHp); if (b.dead || h.dead) return true;
      if (kit) { if (h.hp < h.maxHp * 0.25) drink('zhivaya'); if (h.hp < h.maxHp * 0.5) drink('life1'); if (h.yar < 3) drink('yar1'); }
      if (!h.action && b.state !== 'rise') {
        let tg = b;
        if (o.clear) { let bd = 1e9; for (const e of b.minions) if (!e.dead && e.state !== 'rise') { const d = Math.hypot(e.x - h.x, e.y - h.y); if (d < bd) { bd = d; tg = e; } } }
        if (!h.cmd || h.cmd.target !== tg) { h.cmd = null; h.attack(tg, false, h.lmbSkill(), true); }
      }
      return false; });
    res.push({ t: +b.fightT.toFixed(1), won: b.dead, died: h.dead, phase: b.phase, heal: b.phaseHeal || 0, summons: g.counters.krivshaSummons, blk: g.counters.blockerHits,
               claws: g.counters.krivshaClaws, clawHits: g.counters.krivshaClawHits || 0, used, hpMin: +hpMin.toFixed(2) });
    g.state = 'play';
  }
  const won = res.filter(r => r.won), ts = won.map(r => r.t), avg = (a) => a.length ? +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(1) : null;
  const sum = (k) => res.reduce((a, r) => a + r.used[k], 0);
  return { runs: res.length, won: won.length, deaths: res.filter(r => r.died).length, mean: avg(ts), min: ts.length ? Math.min(...ts) : null, max: ts.length ? Math.max(...ts) : null,
           phase: res.filter(r => r.phase === 2).length, heal: Math.max(...res.map(r => r.heal)), summonsAvg: avg(res.map(r => r.summons)), blockerHits: res.reduce((a, r) => a + r.blk, 0),
           clawHitPct: +(100 * res.reduce((a, r) => a + r.clawHits, 0) / Math.max(1, res.reduce((a, r) => a + r.claws, 0))).toFixed(0),
           potions: { life1: sum('life1'), zhivaya: sum('zhivaya'), yar1: sum('yar1') } };
}; return 1; })()'''

# опыт М1 по контрольным точкам §9.3 (свежие зоны; опыт по коду прототипа — сумма e.xp без штрафа уровня; призванные не в счёт)
XP = '''(() => { const g = __game;
  for (const id of ['zalesye', 'trail', 'kapishche']) delete g.zoneStates[id];
  g.enterZone('zalesye', 'krada'); g.quest.flags.trailOpen = true; g.enterZone('trail', 'start'); g.enterZone('kapishche', 'from_trail');
  const Z = g.zoneStates, list = (st) => [...st.enemies, ...st.buried].filter(e => !e.boss && !e.summoned), xpOf = (st, f = () => true) => list(st).filter(f).reduce((a, e) => a + e.xp, 0);
  const xz = xpOf(Z.zalesye), xzNoMara = xpOf(Z.zalesye, e => !e.special), xt = xpOf(Z.trail), xk = xpOf(Z.kapishche), xb = g.dbg.CFG.bosses.krivsha.xp;
  const lvl = (xp) => { let L = 1, need = 0; while (need + g.dbg.xpToNext(L) <= xp) { need += g.dbg.xpToNext(L); L++; } return [L, +((xp - need) / g.dbg.xpToNext(L)).toFixed(2)]; };
  const ks = list(Z.kapishche), ts = list(Z.trail);
  const champPacks = (arr) => [...new Set(arr.filter(e => e.elite === 'champion').map(e => e.pack))].length;
  return { zalesye: xz, trail: xt, kapishche: xk, exitZalesye: xz, exitTrail: xz + xt, beforeBoss: xz + xt + xk, afterBoss: xz + xt + xk + xb,
           beforeNoMara: xzNoMara + xt + xk, afterNoMara: xzNoMara + xt + xk + xb,
           lvl: { zalesye: lvl(xz), trail: lvl(xz + xt), before: lvl(xz + xt + xk), after: lvl(xz + xt + xk + xb), afterNoMara: lvl(xzNoMara + xt + xk + xb) },
           kap: { n: ks.length, m4: ks.filter(e => e.mlvl === 4).length, m5: ks.filter(e => e.mlvl === 5).length, champ: ks.filter(e => e.elite === 'champion').length, champPacks: champPacks(ks),
                  leaders: ks.filter(e => e.leader).map(e => e.mlvl).sort() },
           trailElite: { champ: ts.filter(e => e.elite === 'champion').map(e => e.kind + '@' + e.mlvl), champPacks: champPacks(ts),
                         leaderPack: (ts.find(e => e.leader) || {}).pack, champPack: (ts.find(e => e.elite === 'champion') || {}).pack,
                         champPackKinds: ts.filter(e => e.pack === (ts.find(x => x.elite === 'champion') || {}).pack).map(e => e.kind[0]).sort().join('') } }; })()'''


async def run_v18(pg, G, check, wait):
    P = SEEDED
    # --- 1. данные v1.8 (§5.3–5.4, §15): заглушки закрыты
    s = await G('''(() => { const C = __game.dbg.CFG, k = C.bosses.krivsha, m = C.bosses.mara, hot = C.stats.elites.mods ? C.stats.elites.mods.hot : C.stats.elites.hot, M = C.monsters;
        return { claw: k.claw, summon: k.summon, hp: k.hearthPhase, arena: k.arena, kph: k._ph, mara: [m.height, m.res.fire, m._ph], hot: [hot.deathBlast.dmgMul, hot._ph],
                 ars: [M.chernoyarets_arsonist.height, M.chernoyarets_arsonist._ph] }; })()''')
    ag = await G('''(async () => { const E = await import('/src/data/enemies.js'); return ['upyr', 'anchutka', 'chernoyarets_arsonist'].map(id => E.ENEMIES[id].aggro); })()''')
    c, sm, hp = s['claw'], s['summon'], s['hp']
    check('v1.8 данные Кривши (§5.4, §15): когти ±45°, телеграф 0,6, ×1,2, цикл 2,4 с, с проверкой попадания; призыв 2 упыря раз в 20 с, первый через 8 с, ≤ 4, mlvl 4, без опыта и добычи; фаза: +15% HP, ореол 2%/с, скорость атаки прежняя, сопр. огню +25%; подъём 7 тайлов или 3-е огнище; заглушек нет',
          c['halfAngleDeg'] == 45 and c['telegraph'] == 0.6 and c['mul'] == 1.2 and c['cycle'] == 2.4 and c['hitRoll'] is True
          and (sm['every'], sm['first'], sm['count'], sm['max'], sm['mlvl'], sm['xpMul'], sm['drop']) == (20, 8, 2, 4, 4, 0, False)
          and hp['healPct'] == 15 and hp['aura']['pctMaxHpPerSec'] == 2 and hp['atkSpeedPct'] == 0 and hp['res']['fire'] == 0.25 and hp['invuln'] == 2
          and s['arena']['triggerRadius'] == 7 and s['arena'].get('orThirdHearth') is True and s['kph'] == [], s)
    check('v1.8 данные: Мара рост 48, сопр. огню +25%, заглушек нет; «Жаркий» взрыв ×1,0 (заглушка снята); поджигатель рост 46; агро 9 у упыря, анчутки, поджигателя',
          s['mara'] == [48, 0.25, []] and s['hot'] == [1.0, []] and s['ars'] == [46, []] and ag == [9, 9, 9], {**s, 'aggro': ag})

    # --- 2. бой: когти с проверкой попадания, призванные без опыта/добычи, фаза +15% HP, скорость атаки прежняя, подъём только в 7 тайлах
    s = await G(('''(async () => { const g = __game; __P__ ''' + REF_HERO + '''
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map; g.enemies = []; g.buried = [];
        const h = await mkRef(6, [m.idol.x - 9.2, m.idol.y]); const out = {}; h.cmd = null; g.simulate(1.5); out.at9 = [g.zs.bossState, +Math.hypot(h.x - m.idol.x, h.y - m.idol.y).toFixed(1)];
        h.x = m.idol.x - 6.8; g.simulate(0.3); out.at7 = g.zs.bossState; const b = g.boss; g.simulate(2.3);
        out.firstSummon = null; g.counters.krivshaSummons = 0; let tt = 0; const c0 = g.counters.krivshaClaws || 0, m0 = g.counters.krivshaClawMiss || 0, h0 = g.counters.krivshaClawHits || 0; const clawT = [];
        g.simulate(60, () => { tt += 1 / 60; h.hp = h.maxHp * 50; h.x = b.x + 1.0; h.y = b.y; h.cmd = null; const T = g.combat.teles.find(x => x.src === b); if (T && T.t < 1 / 60 + 1e-9) clawT.push(+tt.toFixed(2));
          if (out.firstSummon === null && (g.counters.krivshaSummons || 0) > 0) out.firstSummon = +(b.fightT).toFixed(2); return false; });
        const gaps = clawT.slice(1).map((t, i) => +(t - clawT[i]).toFixed(2)); out.claw = { n: (g.counters.krivshaClaws || 0) - c0, miss: (g.counters.krivshaClawMiss || 0) - m0, hits: (g.counters.krivshaClawHits || 0) - h0, gap: gaps.length ? Math.min(...gaps) : null };
        const mins = b.minions.filter(e => !e.dead); out.summon = { n: g.counters.krivshaSummons, alive: mins.length, xp: mins.map(e => e.xp), mlvl: [...new Set(mins.map(e => e.mlvl))] };
        const xp0 = h.xp, it0 = g.loot.items.length; for (const e of mins) { e.hp = 1; e.takeDamage(99999, g, 'melee', h); } g.simulate(0.3); out.killXp = h.xp - xp0; out.killLoot = g.loot.items.length - it0;
        b.hp = Math.ceil(b.maxHp * 0.5) + 2; b.takeDamage(10, g, 'melee', h); const hpJump = b.hp; g.simulate(3.5, () => { h.hp = h.maxHp * 50; h.x = b.x + 4; h.y = b.y; return b.phase === 2; });
        out.phase = { p: b.phase, healed: b.hp - hpJump, heal15: Math.round(b.maxHp * 0.15), atkMul: b.atkMul, fire: b.res.fire, aura: b.aura };
        const hp1 = h.hp = h.maxHp; h.x = b.x + 0.5; h.y = b.y + 0.3; b.stagger = 1e9; const a0 = b.auraDealt || 0; g.simulate(4, () => { h.hp = h.maxHp; h.x = b.x + 0.5; h.y = b.y + 0.3; return false; });
        out.auraPerSec = +(((b.auraDealt || 0) - a0) / 4 / h.maxHp * 100).toFixed(2);
        Math.random = rnd0; return out; })()''').replace('__P__', P))
    cl = s['claw']
    check('v1.8 Кривша не встаёт от боя у огнищ (9,2 тайла от идола), встаёт ближе 7 тайлов; первый призыв через 8 с',
          s['at9'][0] == 'dormant' and s['at7'] == 'active' and s['firstSummon'] is not None and 7.9 <= s['firstSummon'] <= 8.2, s)
    check('v1.8 когти: удары не чаще 2,4 с, проверка попадания — есть промахи («Мимо»), попаданий 35–85%',
          cl['n'] >= 15 and cl['gap'] is not None and cl['gap'] >= 2.35 and cl['miss'] > 0 and 0.35 <= cl['hits'] / max(1, cl['hits'] + cl['miss']) <= 0.85, cl)
    check('v1.8 призванные упыри: mlvl 4, живых ≤ 4, опыта и добычи не дают',
          s['summon']['alive'] <= 4 and s['summon']['mlvl'] == [4] and all(x == 0 for x in s['summon']['xp']) and s['killXp'] == 0 and s['killLoot'] == 0, s['summon'] | {'killXp': s['killXp'], 'killLoot': s['killLoot']})
    ph = s['phase']
    check('v1.8 огненная фаза: выходя из огнища, +15% HP (214), скорость атаки прежняя (×1), сопр. огню +25%, ореол ≈ 2% макс. HP героя в секунду',
          ph['p'] == 2 and ph['healed'] == ph['heal15'] == 214 and ph['atkMul'] == 1 and ph['fire'] == 0.25 and ph['aura'] and 1.6 <= s['auraPerSec'] <= 2.4, {**ph, 'auraPerSec': s['auraPerSec']})

    # --- 3. заслон (§4.1 v1.8): упырь между героем и Крившей; стена — обход; Shift+ЛКМ — нет
    s = await G(('''(async () => { const g = __game; __P__ ''' + REF_HERO + '''
        delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail'); const m = g.map; g.enemies = []; g.buried = [];
        const { Enemy } = await import('/src/entities/enemy.js'); const out = {};
        const h = await mkRef(6, [m.idol.x - 5, m.idol.y + 4]); const b = g.riseBoss('test'); g.simulate(2.2); b.stagger = 1e9; b.x = m.idol.x; b.y = m.idol.y + 4; b.homeX = b.x; b.homeY = b.y;
        h.x = b.x - 3.2; h.y = b.y; const u = new Enemy('upyr', b.x - 1.9, b.y, 'krivsha', 4); u.stagger = 1e9; u.mass = 99; g.enemies.push(u);
        for (const e of [b, u]) { e.state = 'idle'; } b.stagger = 1e9;
        g.lastTarget = b; h.cmd = null; h.attack(b, false, h.lmbSkill(), true); let tHit = null, tt = 0; const u0 = u.hp;
        g.simulate(1.5, () => { tt += 1 / 60; if (u.hp < u0 || (h.action && h.action.target === u)) { tHit = +tt.toFixed(2); return true; } return false; });
        out.block = { tHit, plate: g.lastTarget === b, cmdTarget: h.cmd && h.cmd.target === b, actT: h.action && h.action.target === u };
        u.hp = 1; let bHit = null; tt = 0; const b0 = b.hp; g.simulate(5, () => { tt += 1 / 60; if (h.action && h.action.target === b) { bHit = +tt.toFixed(2); return true; } return false; });
        out.after = { uDead: u.dead, bHit, plate: g.lastTarget === b };
        // Shift+ЛКМ: удар на месте, заслон не включается
        const u2 = new Enemy('upyr', b.x - 1.9, b.y, 'krivsha', 4); u2.stagger = 1e9; u2.mass = 99; g.enemies.push(u2); h.x = b.x - 3.2; h.y = b.y; h.cmd = null; h.action = null; g.counters.blockerHits = 0;
        h.attack(b, true, h.lmbSkill(), true); g.simulate(1.2); out.shift = g.counters.blockerHits || 0;
        // ПКМ («Сшибка» на ПКМ по Кривше): правило не включается
        h.cmd = null; h.action = null; h.x = b.x - 3.2; h.y = b.y; g.counters.blockerHits = 0; h.attack(b, false, h.lmbSkill(), false); g.simulate(1.2); out.rmb = g.counters.blockerHits || 0;
        Math.random = rnd0; return out; })()''').replace('__P__', P))
    bl = s['block']
    check('v1.8 заслон (§4.1): упырь на пути к Кривше — через ≈ 0,3 с без продвижения герой бьёт упыря, цель (плашка и приказ) остаётся Крившей; после гибели упыря сам идёт и бьёт Крившу; Shift+ЛКМ и ПКМ правило не включают',
          bl['tHit'] is not None and 0.25 <= bl['tHit'] <= 1.0 and bl['plate'] and bl['cmdTarget'] and s['after']['uDead'] and s['after']['bHit'] is not None and s['after']['plate']
          and s['shift'] == 0 and s['rmb'] == 0, s)
    s = await G(('''(async () => { const g = __game; __P__ ''' + REF_HERO + '''
        g.enterZone('zalesye', 'krada'); const m = g.map; g.enemies = []; g.buried = []; const { Enemy } = await import('/src/entities/enemy.js');
        let spot = null; for (let y = 4; y < m.h - 4 && !spot; y++) for (let x = 4; x < m.w - 6 && !spot; x++) {
          if (m.isBlocked(x + 2, y) && !m.isBlocked(x, y) && !m.isBlocked(x + 4, y) && !m.isBlocked(x + 1, y) && !m.isBlocked(x + 3, y) && g.dbg.circleFree(m, x + 0.5, y + 0.5, 0.4) && g.dbg.circleFree(m, x + 4.5, y + 0.5, 0.4) && m.isReachableAt(x + 0.5, y + 0.5) && m.isReachableAt(x + 4.5, y + 0.5) && !g.safeAt(x + 0.5, y + 0.5, 1)) spot = [x, y]; }
        if (!spot) return { none: true }; const h = await mkRef(6, [spot[0] + 0.5, spot[1] + 0.5]); const e = new Enemy('upyr', spot[0] + 4.5, spot[1] + 0.5, 'test', 1); e.stagger = 1e9; g.enemies.push(e);
        g.counters.blockerHits = 0; h.attack(e, false, h.lmbSkill(), true); let reached = false; g.simulate(6, () => { if (h.action && h.action.target === e) { reached = true; return true; } return false; });
        Math.random = rnd0; return { blk: g.counters.blockerHits || 0, reached }; })()''').replace('__P__', P))
    check('v1.8 заслон: стена или объект на пути — герой обходит (по A*), а не бьёт', s.get('none') or (s['blk'] == 0 and s['reached']), s)

    # --- 4. опыт М1 и состав (§8.2, §9.3 v1.8)
    x = await G(XP)
    print('ОПЫТ v1.8:', json.dumps(x, ensure_ascii=False), flush=True)
    k, te = x['kap'], x['trailElite']
    check('v1.8 состав: капище 90 (30@4 / 60@5), 16 матёрых в 5 стаях, вожаки mlvl 4 и 5; тропа — 1 стая матёрых (3 упыря mlvl 3 + 2 поджигателя), не стая вожака',
          k == {'n': 90, 'm4': 30, 'm5': 60, 'champ': 16, 'champPacks': 5, 'leaders': [4, 5]}
          and te['champ'] == ['upyr@3'] * 3 and te['champPacks'] == 1 and te['champPack'] != te['leaderPack'] and te['champPackKinds'] == 'ccuuu', x)
    check('v1.8 опыт М1 (§9.3, допуск ±10% / ±1 ур.): до Кривши 5 310–6 490 (≈ 5 730), после ≥ 6 220 и 7 ур. (≈ 6 930), в том числе без Мары; выход тропы — 4 ур. (±1)',
          5310 <= x['beforeBoss'] <= 6490 and x['afterBoss'] >= 6220 and x['lvl']['after'][0] == 7 and x['afterNoMara'] >= 6220 and 3 <= x['lvl']['trail'][0] <= 5, x)

    # --- 5. короткая серия боя (бот §9.3, HP восполняется; полный замер 30 боёв — --balance-v18)
    await G(FIGHT)
    b0 = await G('''(async () => { const g = __game; __P__ const keep = g.hero; const r = await __fight({ runs: 6, hearths: 0, refill: true }); g.hero = keep; Math.random = rnd0; return r; })()'''.replace('__P__', P))
    b1 = await G('''(async () => { const g = __game; __P__ const keep = g.hero; const r = await __fight({ runs: 6, hearths: 1, refill: true }); g.hero = keep; Math.random = rnd0; return r; })()'''.replace('__P__', P))
    print('БОЙ v1.8 (6 боёв):', json.dumps({'noPhase': b0, 'phase1': b1}, ensure_ascii=False), flush=True)
    check('v1.8 бой бота (6 боёв, HP восполняется): без фазы и с фазой все бои выиграны; фаза дольше; средние в нормах бота ±10% (50–65 / 65–80 с; полный замер — REPORT_m1c.md)',
          b0['won'] == 6 and b1['won'] == 6 and b1['phase'] == 6 and b0['phase'] == 0 and b1['mean'] > b0['mean'] and 45 <= b0['mean'] <= 71.5 and 58.5 <= b1['mean'] <= 88, {'noPhase': b0, 'phase1': b1})
    await G('(() => { const g = __game; g.enemies = []; g.state = "play"; })()')
    # --- 6. B-31 (v1.8.1): круг Мары в тупике — расстояния до изб, стай и пути; поводок 8; рассыпание призванных (B-33)
    s = await G('''(() => { const g = __game; g.enterZone('zalesye', 'krada'); const m = g.map, R = g.dbg.CFG.bosses.mara.route, C = R.center, r = R.radius;
        const pts = []; for (let i = 0; i < 32; i++) { const a = i / 32 * Math.PI * 2; pts.push([C[0] + Math.cos(a) * r, C[1] + Math.sin(a) * r]); }
        const minD = (list) => +Math.min(...pts.flatMap(p => list.map(q => Math.hypot(p[0] - q[0], p[1] - q[1])))).toFixed(1);
        const huts = m.objects.filter(o => o.type === 'hut').map(o => [o.x, o.y]);
        const packs = m.packs.map(p => [p.x, p.y]);
        const seg = (ax, ay, bx, by) => { const n = Math.ceil(Math.hypot(bx - ax, by - ay) * 2), o = []; for (let i = 0; i <= n; i++) { const t = i / n; o.push([ax + (bx - ax) * t + Math.sin(t * 9) * 0.8, ay + (by - ay) * t]); } return o; };
        const S = { x: 24, y: 26 }, W = [35, 37], E = [44.5, 45];
        const path = [...seg(S.x, S.y, 38, 7), ...seg(S.x, S.y, 17, 35), ...seg(S.x, S.y, 14, 17), ...seg(S.x, S.y, W[0], W[1] + 1), ...seg(W[0] + 1, W[1] + 2, E[0], E[1])];
        const M = g.enemies.find(e => e.kind === 'mara'); const ret = g.enemies.filter(e => e.special === 'mara' && e !== M);
        const barn = m.props.some(p => p.burnt), ash = m.props.filter(p => p.type === 'ash').length;
        return { minHut: minD(huts), minPack: minD(packs), minPath: minD(path), minKrada: minD([[m.krada.x, m.krada.y]]),
                 leash: R.leash, center: C, size: [m.w, m.h], free: pts.filter(p => m.isReachableAt(p[0], p[1])).length, pts: pts.length,
                 mara: !!M, ret: ret.length, anchor: M && M.anchor && M.anchor.r, retAnchor: ret.every(e => e.anchor && e.anchor.r === R.leash), barn, ash }; })()''')
    check('v1.8.1 B-31: круг Мары в тупике — каждая точка ≥ 12 тайлов от изб, их стай и пути «крада → избы → колодец → выход», ≥ 14 от крады; все точки проходимы; у входа обгоревший сарай и пепел; поводок 8 у Мары и свиты',
          s['minHut'] >= 12 and s['minPack'] >= 12 and s['minPath'] >= 12 and s['minKrada'] >= 14 and s['free'] == s['pts'] and s['leash'] == 8
          and s['mara'] and 4 <= s['ret'] <= 6 and s['anchor'] == 8 and s['retAnchor'] and s['barn'] and s['ash'] >= 3 and s['size'][0] > 48, s)
    s = await G('''(() => { const g = __game, h = g.hero; g.enterZone('zalesye', 'krada'); const M = g.enemies.find(e => e.kind === 'mara');
        h.x = M.x - 4; h.y = M.y; h.invuln = 1e9; M.aggro(g, false); g.simulate(2, () => M.state === 'chase');
        h.x = M.anchor.x - (M.anchor.r + 6); h.y = M.anchor.y; h.hp = h.maxHp; M.hp = Math.round(M.maxHp * 0.6); const l0 = g.counters.anchorLeash || 0;
        g.simulate(12, () => M.state === 'idle' && M.hp === M.maxHp);
        const out = { st: M.state, hp: M.hp, max: M.maxHp, d: +Math.hypot(M.x - M.anchor.x, M.y - M.anchor.y).toFixed(1), leash: (g.counters.anchorLeash || 0) - l0 };
        h.invuln = 0; h.x = g.map.krada.x; h.y = g.map.krada.y + 2; return out; })()''')
    check('v1.8.1 B-31: дальше 8 тайлов от центра круга Мара бросает погоню, возвращается на круг и восстанавливает HP',
          s['st'] == 'idle' and s['hp'] == s['max'] and s['d'] <= 8 and s['leash'] > 0, s)
    s = await G('''(() => { const g = __game, h = g.hero; delete g.zoneStates.kapishche; g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail');
        const m = g.map; for (const e of g.enemies) if (Math.hypot(e.x - m.idol.x, e.y - m.idol.y) < 16) e.takeDamage(99999, g, 'melee', null); g.simulate(0.2);
        h.x = m.idol.x - 6.5; h.y = m.idol.y; h.invuln = 1e9; g.counters.krivshaSummons = 0; g.counters.krivshaResets = 0; g.counters.krivshaCrumbled = 0; g.simulate(0.3); const b = g.boss; b.stagger = 1e9;
        g.simulate(12, () => (g.counters.krivshaSummons || 0) > 0); g.simulate(1); const n = g.enemies.filter(e => e.summoned && !e.dead).length; const xp0 = h.xp, it0 = g.loot.items.length;
        b.stagger = 0; b.state = 'return'; b.path = null; g.simulate(8, () => (g.counters.krivshaResets || 0) > 0);
        const left = g.enemies.filter(e => e.summoned && !e.dead).length; const out = { n, left, xp: h.xp - xp0, loot: g.loot.items.length - it0, resets: g.counters.krivshaResets || 0, crumbled: g.counters.krivshaCrumbled || 0, bhp: b.hp === b.maxHp };
        g.enemies = []; h.invuln = 0; return out; })()''')
    check('v1.8.1 B-33: сброс Кривши (гибель героя, обрыв боя) — призванные упыри рассыпаются, без опыта и добычи; босс с полным HP',
          s['n'] > 0 and s['left'] == 0 and s['crumbled'] == s['n'] and s['xp'] == 0 and s['loot'] == 0 and s['resets'] > 0 and s['bhp'], s)

    # --- 7. v1.8.1 §8.2: «миссия пройдена» при огнищах 2/3; неотбитое огнище и его пачка остаются, цель 3 закрывается позже
    s = await G('''(() => { const g = __game; delete g.zoneStates.kapishche; g.quest = new g.quest.constructor(g, 'm1'); g.enterZone('trail', 'gate'); g.enterZone('kapishche', 'from_trail');
        const m = g.map, h = g.hero; h.invuln = 1e9; for (const e of g.enemies) e.stagger = 1e9;
        const hs = m.hearths.slice(), left = hs[2], packOf = (o) => m.packs.findIndex(p => p.role === o.pack);
        for (const o of hs.slice(0, 2)) { const idx = packOf(o); for (const e of g.enemies) if (!e.dead && e.pack === idx) e.takeDamage(99999, g, 'melee', null); o.done = true; g.quest.emit({ event: 'hearthFreed', hearth: o.id }); }
        g.quest.emit({ event: 'reach', target: 'kapishche_gate' }); g.quest.emit({ event: 'arsonistSeen' }); g.quest.emit({ event: 'letterRead', letter: 'order' });
        for (let i = 0; i < 3; i++) g.quest.emit({ event: 'hutFreed', hut: 'hut' + (i + 1) });
        const before = { md: !!g.quest.missionDone };
        h.x = m.idol.x - 6.5; h.y = m.idol.y; g.simulate(0.3); const b = g.boss; g.simulate(2.5, () => b && b.state === 'fight'); if (b) { b.invuln = 0; b.hp = 1; b.takeDamage(999999, g, 'melee', h); } g.simulate(1); for (const o of g.quest.obj) if (o.def.required && o.state !== 'done') { if (o.def.count) { while (o.n < o.def.count) g.quest.emit({ ...(o.def.progressOn) }); } else if (o.def.doneOn) g.quest.emit({ ...o.def.doneOn }); } g.simulate(0.2);
        const idx = packOf(left), packAlive = g.enemies.filter(e => !e.dead && e.pack === idx).length;
        const after = { md: !!g.quest.missionDone, hearths: g.quest.get('hearths').state + ' ' + g.quest.get('hearths').n, done: left.done, err: g.canInteract(left), lines: g.quest.lines().map(l => [l.text, l.count || '', l.state]) };
        for (const e of g.enemies) if (!e.dead && e.pack === idx) e.takeDamage(99999, g, 'melee', null); g.simulate(0.3);
        for (const e of g.enemies) if (!e.dead && Math.hypot(e.x - left.x, e.y - left.y) < 6) e.takeDamage(99999, g, 'melee', null); g.simulate(0.3);
        h.x = left.sx; h.y = left.sy; h.cmd = null; g.autoHold = true; h.interact(left); g.simulate(5, () => left.done); g.autoHold = false;
        const closed = { hearths: g.quest.get('hearths').state + ' ' + g.quest.get('hearths').n };
        g.enemies = []; h.invuln = 0; return { before, packAlive, after, closed }; })()''')
    check('v1.8.1 §8.2: миссия пройдена при огнищах 2/3; неотбитое огнище и его пачка остаются, строка «Отбей огнища 2/3» висит в трекере и закрывается позже',
          not s['before']['md'] and s['after']['md'] and s['after']['hearths'] == 'active 2' and s['after']['done'] is False and s['packAlive'] > 0
          and s['after']['err'] == 'ui.obj.enemies_near' and any('Отбей огнища' in l[0] and l[1] == '2/3' for l in s['after']['lines']) and s['closed']['hearths'] == 'done 3', s)



async def run_balance18(pg, G, n=30):
    """Полный замер §12.3 v1.8: время боя (3 режима), гибель с зельями (оба запаса), опыт по зонам. Пишет tools/balance_m1c.json."""
    await G(FIGHT)
    P = SEEDED
    out = {}
    plan = [
        ('time_noPhase', {'hearths': 0, 'refill': True}),
        ('time_phase1', {'hearths': 1, 'refill': True}),
        ('time_phase3', {'hearths': 3, 'refill': True}),
        ('time_addsFirst_noPhase', {'hearths': 0, 'refill': True, 'clear': True}),
        ('time_addsFirst_phase1', {'hearths': 1, 'refill': True, 'clear': True}),
        ('time_addsFirst_phase3', {'hearths': 3, 'refill': True, 'clear': True}),
        ('deaths_noPhase_kit10', {'hearths': 0, 'kit': {'life1': 10, 'zhivaya': 1, 'yar1': 3}}),
        ('deaths_phase1_belt15', {'hearths': 1, 'kit': {'life1': 15, 'zhivaya': 1, 'yar1': 0}}),
        ('deaths_phase3_belt15', {'hearths': 3, 'kit': {'life1': 15, 'zhivaya': 1, 'yar1': 0}}),
        ('deaths_phase1_kit10', {'hearths': 1, 'kit': {'life1': 10, 'zhivaya': 1, 'yar1': 3}}),
        ('deaths_noPotions_noPhase', {'hearths': 0}),
    ]
    for name, o in plan:
        o = {**o, 'runs': n}
        r = await G('''(async () => { const g = __game; __P__ const keep = g.hero; const r = await __fight(__O__); g.hero = keep; Math.random = rnd0; return r; })()'''
                    .replace('__P__', P).replace('__O__', json.dumps(o)))
        out[name] = r
        print(name, json.dumps(r, ensure_ascii=False), flush=True)
    out['xp'] = await G(XP)
    print('xp', json.dumps(out['xp'], ensure_ascii=False), flush=True)
    with open(BAL_OUT, 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out

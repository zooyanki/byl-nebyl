// Окно «Навыки» (T, GDD §3.6 / §10): две ветки — «Ратное дело» и «Ведовство», тиры I/II/III, ранги x/10,
// кнопка «+» тратит очко навыка, ЛКМ по иконке — назначить на ПКМ, F1–F6 над иконкой — положить в ячейку панели.
// Тексты — act1_texts §16 и §21 (data/ru.json). Фон и раскладка — tools/export_ui.py (win_skills.png, skills_layout).
import { PAL } from '../palette.js';
import { rect } from '../render/shapes.js';
import { drawText, textWidth } from '../core/font.js';
import { IMG, drawIcon, UI_ATLAS } from './assets.js';
import { SKILLS, RULES, DASH, rankOf, boughtRank, rankBlock, pointsFree, descVars, branchOf, skillShort } from '../data/skills.js';
import { t, tObj } from '../core/i18n.js';

const L = UI_ATLAS.skills_layout;
const inR = (mx, my, [x, y, w, h]) => mx >= x && my >= y && mx < x + w && my < y + h;
const TIER_NAMES = ['I', 'II', 'III'];
const TIER_REQ = [1, 6, 12];

export class SkillsWindow {
  constructor(game) { this.game = game; this.hover = {}; }
  over(mx, my) { const [x, y, w, h] = L.win; return mx >= x - 2 && my >= y - 4 && mx < x + w + 2 && my < y + h + 2; }

  computeHover(mx, my) {
    const H = this.hover = {};
    for (const [id, r] of Object.entries(L.slots)) {
      if (inR(mx, my, L.plus[id])) H.plus = id;
      else if (inR(mx, my, [r[0], r[1], L.colw, r[3]])) H.skill = id;
    }
    const [cx, cy, cs] = L.close;
    if (inR(mx, my, [cx, cy, cs, cs])) H.close = true;
    return H;
  }

  /** ЛКМ по окну. true — клик съеден окном. */
  handle(input) {
    const g = this.game, h = g.hero;
    const H = this.computeHover(input.mx, input.my);
    if (!input.leftPressed) return this.over(input.mx, input.my);
    if (H.close) { g.ui.toggleSkills(false); return true; }
    if (H.plus) {
      const why = SKILLS[H.plus].implemented === false ? 'soon' : h.learn(H.plus, g);
      if (!why) { g.audio.play('learn'); g.log.add(SKILLS[H.plus].name + ': ' + t('ui.skills.rank', { n: boughtRank(h, H.plus) }), PAL.bronze_hi); }
      else {
        // GDD v1.7: отказ — короткий тост (тексты ui.skills.* у сценариста)
        g.audio.play('error');
        const sk = SKILLS[H.plus], msg = why === 'points' ? t('ui.skills.no_points')
          : why === 'level' ? t('ui.skills.req_level', { n: sk.req + boughtRank(h, H.plus) })
          : why === 'prev' ? t('ui.skills.req_skill', { skill: SKILLS[sk.needs].name }) : null;
        if (msg) g.notify(msg, PAL.red_lt, 'sp', 1.6);
        g.counters.skillRefusals = (g.counters.skillRefusals || 0) + 1;
      }
      return true;
    }
    if (H.skill) {
      if (h.setRmb(H.skill)) { g.audio.play('ui'); g.notify(t('ui.skills.to_rmb') + ': ' + SKILLS[H.skill].name, PAL.bronze_lt, 'rmb'); }
      else g.audio.play('error');
      return true;
    }
    return this.over(input.mx, input.my);
  }

  draw(ctx) {
    const g = this.game, h = g.hero, W = UI_ATLAS.win_skills, m = g.input;
    if (IMG.winSkills && IMG.winSkills.complete) ctx.drawImage(IMG.winSkills, W.x, W.y);
    const H = this.hover;
    // тиры
    L.tiers.forEach((y, i) => {
      const txt = TIER_NAMES[i] + ' · ' + (TIER_REQ[i] > 1 ? t('proto.skills.tier_from', { n: String(TIER_REQ[i]) }) : t('proto.skills.tier_start'));
      for (const b of ['ratnoe', 'vedovstvo']) drawText(ctx, L.cols[b][0] + 2, y, txt, h.level >= TIER_REQ[i] ? PAL.bronze_lt : PAL.slate_lt, { shadow: false });
    });
    // связи «нужен навык»
    for (const sk of Object.values(SKILLS)) {
      if (!sk.needs || !L.slots[sk.id]) continue;
      const a = L.slots[sk.needs], b = L.slots[sk.id];
      const x = a[0] + 14, on = boughtRank(h, sk.needs) > 0;
      if (b[1] - (a[1] + 28) > 2) rect(ctx, x, a[1] + 28, 1, b[1] - a[1] - 28, on ? PAL.bronze : PAL.wood_md);
    }
    for (const [id, r] of Object.entries(L.slots)) {
      const sk = SKILLS[id];
      const have = boughtRank(h, id), eff = rankOf(h, id), soon = sk.implemented === false;
      const block = soon ? 'soon' : rankBlock(h, id);
      const hv = H.skill === id;
      drawIcon(ctx, 'sk_' + sk.icon + '_20', r[0] + 1, r[1] + 1, 26, 26, have ? 1 : block === 'points' || !block ? 0.75 : 0.3);
      if (h.rmb === id) rect(ctx, r[0], r[1], 28, 1, PAL.flame), rect(ctx, r[0], r[1] + 27, 28, 1, PAL.flame);
      if (hv) { ctx.strokeStyle = PAL.bronze_hi; ctx.lineWidth = 1; ctx.strokeRect(r[0] + 0.5, r[1] + 0.5, 27, 27); }
      const k = h.bar.indexOf(id);
      if (k >= 0) drawText(ctx, r[0] + 2, r[1] + 1, 'F' + (k + 1), PAL.bronze_hi, { outline: true });
      // имя и ранг
      const tx = r[0] + 35, avail = L.plus[id][0] - tx - 3;
      const fit = (str) => { if (textWidth(str) <= avail) return str; while (str.length > 1 && textWidth(str + '…') > avail) str = str.slice(0, -1); return str.trimEnd() + '…'; };
      drawText(ctx, tx, r[1] + 4, fit(skillShort(id)), have ? PAL.linen : soon ? PAL.slate_lt : PAL.birch, { shadow: false });
      let rk = t('ui.skills.rank', { n: have });
      if (eff > have && have) rk += ' (+' + (eff - have) + ')';
      const sub = fit(soon ? t('proto.skills.soon') : sk.type === 'passive' ? rk + ' · ' + t('proto.skills.passive') : rk);
      drawText(ctx, tx, r[1] + 15, sub, eff > have && have ? PAL.blue_lt : PAL.mist, { shadow: false });
      // «+»
      const [px, py, ps] = L.plus[id];
      const can = !block, hp = H.plus === id;
      rect(ctx, px - 1, py - 1, ps + 2, ps + 2, PAL.ink);
      rect(ctx, px, py, ps, ps, can ? PAL.bronze_lt : PAL.slate);
      rect(ctx, px + 1, py + 1, ps - 2, ps - 2, can ? PAL.red : PAL.slate_dk);
      const c = can ? (hp ? PAL.linen : PAL.bronze_hi) : PAL.slate_lt, mid = ps >> 1;
      rect(ctx, px + 3, py + mid, ps - 6, 1, c); rect(ctx, px + mid, py + 3, 1, ps - 6, c);
    }
    // очки и подсказка
    const [fx, fy, fw] = L.points, pts = pointsFree(h);
    drawText(ctx, fx + 5, fy + 3, t('ui.skills.points', { n: pts }), pts > 0 ? PAL.flame : PAL.birch, { shadow: false });
    drawText(ctx, fx + fw - 5, fy + 3, t('proto.sys.rmb_set', { skill: SKILLS[h.rmb] ? SKILLS[h.rmb].name : '—' }), PAL.bronze_lt, { align: 'r', shadow: false });
    drawText(ctx, L.hint[0] + 2, L.hint[1], t('proto.skills.hint'), PAL.mist, { shadow: false });
    // подсказка навыка
    const id = H.skill || H.plus;
    if (id) drawSkillTooltip(ctx, h, id, L.win[0] - 3, m.my - 20, 'tr');
  }
}

/** Строки подсказки навыка (общие для окна и панели HUD). */
export function skillTipLines(h, id) {
  if (id === 'dash') {
    const o = tObj('skill.dash');
    return [[DASH.name, PAL.bronze_hi], [DASH.key + ' · ' + t('ui.skills.cd', { n: DASH.cd }), PAL.mist], [o ? o.chant : '', PAL.birch], [o ? o.desc : '', PAL.linen]];
  }
  const sk = SKILLS[id], o = tObj(sk.textKey) || {};
  const have = boughtRank(h, id), eff = rankOf(h, id);
  const L = [[sk.name, PAL.bronze_hi], [(branchOf(sk.branch) || {}).name + ' · ' + TIER_NAMES[sk.tier - 1] + (sk.type === 'passive' ? ' · ' + t('ui.skills.passive') : ''), PAL.mist]];
  if (o.chant) L.push([o.chant, PAL.birch]);
  const fill = (r) => (o.desc || '').replace(/\{(\w+)\}/g, (m, k) => { const v = descVars(h, id, r)[k]; return v == null ? m : String(Math.round(v * 10) / 10).replace('.', ','); });
  if (sk.implemented === false) { L.push([t('proto.skills.not_impl'), PAL.slate_lt]); return L; }
  if (eff) {
    L.push([t('ui.skills.rank', { n: eff }) + (eff > have ? ' ' + t('proto.skills.from_items', { n: String(eff - have) }) : ''), PAL.linen]);
    L.push([fill(eff), PAL.linen]);
  }
  const cost = descVars(h, id, Math.max(1, eff)).cost;
  if (sk.type !== 'passive') L.push([t('ui.skills.cost', { n: cost }) + (sk.cd ? ' · ' + t('ui.skills.cd', { n: sk.cd }) : ''), PAL.blue_lt]);
  if (h.lmb === id) L.push([t('proto.skills.lmb_basic'), PAL.nebyl]);
  if (have < (sk.maxRank || RULES.maxRank)) {
    L.push([t('ui.skills.next') + ':', PAL.bronze_lt]);
    L.push([fill(eff + 1 > 10 ? 10 : (eff || 0) + 1), PAL.mist]);
    const why = rankBlock(h, id);
    if (why === 'level') L.push([t('ui.skills.req_level', { n: sk.req + have }), PAL.red_lt]);
    else if (why === 'prev') L.push([t('ui.skills.req_skill', { skill: SKILLS[sk.needs].name }), PAL.red_lt]);
  }
  return L;
}

export function drawSkillTooltip(ctx, h, id, ax, ay, anchor = 'tr') {
  const lines = skillTipLines(h, id).filter(([s]) => s);
  // перенос длинных строк по 46 символов
  const wrapped = [];
  for (const [s, c] of lines) {
    let rest = s;
    while (rest.length > 48) { let k = rest.lastIndexOf(' ', 48); if (k < 10) k = 48; wrapped.push([rest.slice(0, k), c]); rest = rest.slice(k + 1); }
    wrapped.push([rest, c]);
  }
  const pad = 5, lh = 11;
  const w = Math.max(...wrapped.map(([s]) => textWidth(s))) + pad * 2 + 2, hh = wrapped.length * lh - 2 + pad * 2;
  let x = anchor === 'tr' ? ax - w : anchor === 'bc' ? ax - w / 2 : ax, y = anchor === 'bc' ? ay - hh : ay;
  x = Math.round(Math.max(2, Math.min(638 - w, x))); y = Math.round(Math.max(2, Math.min(312 - hh, y)));
  ctx.save(); ctx.globalAlpha = 0.9; rect(ctx, x, y, w, hh, PAL.ink); ctx.restore();
  ctx.strokeStyle = PAL.wood_md; ctx.lineWidth = 1; ctx.strokeRect(x + 1.5, y + 1.5, w - 3, hh - 3);
  wrapped.forEach(([s, c], i) => drawText(ctx, x + pad + 1, y + pad + i * lh, s, c, { shadow: false }));
  return { x, y, w, h: hh };
}

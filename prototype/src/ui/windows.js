// Окна «Котомка» (I) и «Витязь» (C) по макетам mockup_inventory_v2 / mockup_character_v2:
// кукла с 10 слотами, сетка 10×4, перетаскивание/щелчок, подсказки с редкостью и сравнением.
import { PAL } from '../palette.js';
import { rect } from '../render/shapes.js';
import { drawText, textWidth } from '../core/font.js';
import { IMG, drawIcon, UI_ATLAS } from './assets.js';
import { itemLines, RARITY, SLOT_NAMES, TYPE_SLOTS } from '../data/items.js';
import { ATTRS, hitChance } from '../data/progression.js';
import { itemColor } from '../systems/loot.js';

const INV = UI_ATLAS.inventory_layout, CHR = UI_ATLAS.character_layout;
const CELL = INV.cell;
const inR = (mx, my, x, y, w, h) => mx >= x && my >= y && mx < x + w && my < y + h;
const fmtNum = (n) => (n === Infinity ? '—' : String(Math.floor(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' '));

export class InventoryUI {
  constructor(game) {
    this.game = game;
    this.invOpen = false;
    this.charOpen = false;
    this.hand = null;          // предмет «на курсоре»
    this.drag = null;          // {x, y} — откуда начали тащить
    this.hover = {};
  }

  get anyOpen() { return this.invOpen || this.charOpen; }
  overInv(mx, my) { const [x, y, w, h] = INV.win; return this.invOpen && inR(mx, my, x - 2, y - 4, w + 4, h + 6); }
  overChar(mx, my) { const [x, y, w, h] = CHR.win; return this.charOpen && inR(mx, my, x - 2, y - 4, w + 4, h + 6); }
  over(mx, my) { return this.overInv(mx, my) || this.overChar(mx, my); }

  toggleInv(v = !this.invOpen) { this.invOpen = v; if (!v) this.returnHand(); this.game.audio.play('ui'); }
  toggleChar(v = !this.charOpen) { this.charOpen = v; this.game.audio.play('ui'); }
  closeAll() { const any = this.anyOpen; this.invOpen = false; this.charOpen = false; this.returnHand(); return any; }

  // предмет с курсора — обратно в котомку, а если некуда — на землю
  returnHand() {
    if (!this.hand) return;
    const h = this.game.hero;
    if (!h.inv.autoAdd(this.hand)) this.dropHand();
    this.hand = null; this.drag = null;
  }
  dropHand() {
    const g = this.game, it = this.hand;
    if (!it) return;
    g.loot.spawnItem(g.hero.x, g.hero.y, it);
    g.log.add('Выброшено: ' + it.name, itemColor(it));
    g.audio.play('ui');
    this.hand = null; this.drag = null;
  }

  // --- что под курсором
  computeHover(mx, my) {
    const H = this.hover = {};
    const hero = this.game.hero;
    if (this.invOpen) {
      for (const [slot, r] of Object.entries(INV.slots)) if (inR(mx, my, r[0], r[1], r[2], r[3])) H.slot = slot;
      if (inR(mx, my, INV.gx, INV.gy, CELL * 10, CELL * 4)) {
        H.cell = [Math.floor((mx - INV.gx) / CELL), Math.floor((my - INV.gy) / CELL)];
        H.entry = hero.inv.at(H.cell[0], H.cell[1]);
      }
      const [cx, cy, cs] = INV.close;
      if (inR(mx, my, cx, cy, cs, cs)) H.closeInv = true;
    }
    if (this.charOpen) {
      ATTRS.forEach((a, k) => { const y = CHR.ry + k * 17; if (inR(mx, my, CHR.lx0 + CHR.colw - 13, y, 13, 13)) H.plus = a.id; });
      const [cx, cy, cs] = CHR.close;
      if (inR(mx, my, cx, cy, cs, cs)) H.closeChar = true;
    }
    return H;
  }

  // позиция предмета в сетке для курсора (предмет держим за центр)
  gridTarget(item, mx, my) {
    let c = Math.round((mx - INV.gx) / CELL - item.w / 2), r = Math.round((my - INV.gy) / CELL - item.h / 2);
    c = Math.max(0, Math.min(10 - item.w, c)); r = Math.max(0, Math.min(4 - item.h, r));
    return [c, r];
  }

  tryPlace(mx, my) {
    const g = this.game, inv = g.hero.inv, it = this.hand;
    const [c, r] = this.gridTarget(it, mx, my);
    const ov = inv.overlapping(it, c, r);
    if (ov.length > 1) { g.audio.play('error'); return false; }
    if (ov.length === 1) inv.remove(ov[0].item);
    inv.add(it, c, r);
    this.hand = ov.length === 1 ? ov[0].item : null;
    g.audio.play('ui');
    return true;
  }

  tryEquip(item, slot) {
    const g = this.game, h = g.hero;
    const err = h.canEquip(item, slot);
    if (err === 'type') { g.notify('Сюда это не надеть', PAL.mist, 'eqtype'); g.audio.play('error'); return false; }
    if (err === 'level') { g.notify('Требуется уровень ' + item.req, PAL.red_lt, 'eqlvl'); g.audio.play('error'); return false; }
    const old = h.putOn(item, slot);
    this.hand = old;
    g.log.add('Надето: ' + item.name, itemColor(item));
    g.audio.play('equip');
    return true;
  }

  quickEquip(entry) {
    const g = this.game, h = g.hero, it = entry.item;
    if (it.kind === 'potion') { h.inv.remove(it); h.applyPotion(it.potion, g); return; }
    const slot = h.slotFor(it);
    const err = h.canEquip(it, slot);
    if (err === 'level') { g.notify('Требуется уровень ' + it.req, PAL.red_lt, 'eqlvl'); g.audio.play('error'); return; }
    if (err) { g.audio.play('error'); return; }
    h.inv.remove(it);
    const old = h.putOn(it, slot);
    if (old && !(h.inv.fits(old, entry.c, entry.r) && h.inv.add(old, entry.c, entry.r)) && !h.inv.autoAdd(old)) this.hand = old;
    g.log.add('Надето: ' + it.name, itemColor(it));
    g.audio.play('equip');
  }

  unequipToBag(slot) {
    const g = this.game, h = g.hero, it = h.equip[slot];
    if (!it) return;
    if (!h.inv.autoAdd(it)) { g.notify('Некуда положить', PAL.red_lt, 'full'); g.audio.play('error'); return; }
    h.takeOff(slot);
    g.log.add('Снято: ' + it.name, itemColor(it));
    g.audio.play('equip');
  }

  /** Обработка мыши. Возвращает true, если щелчок «съеден» окнами. */
  handle(input) {
    const g = this.game, h = g.hero, mx = input.mx, my = input.my;
    const H = this.computeHover(mx, my);
    const over = this.over(mx, my);
    if (input.leftPressed) {
      if (H.closeInv) { this.toggleInv(false); return true; }
      if (H.closeChar) { this.toggleChar(false); return true; }
      if (H.plus) { if (h.spendPoint(H.plus)) g.audio.play('ui'); else g.audio.play('error'); return true; }
      if (this.hand) {
        if (H.slot) this.tryEquip(this.hand, H.slot);
        else if (H.cell) this.tryPlace(mx, my);
        else if (!over && !g.overHud) this.dropHand();
        this.drag = null;
        return true;
      }
      if (H.slot && h.equip[H.slot]) { this.hand = h.takeOff(H.slot); this.drag = { x: mx, y: my }; g.audio.play('ui'); return true; }
      if (H.entry) { h.inv.remove(H.entry.item); this.hand = H.entry.item; this.drag = { x: mx, y: my }; g.audio.play('ui'); return true; }
      return over;
    }
    if (input.leftReleased && this.hand && this.drag) {
      const moved = Math.hypot(mx - this.drag.x, my - this.drag.y) > 6;
      this.drag = null;
      if (moved) {
        if (H.slot) this.tryEquip(this.hand, H.slot);
        else if (H.cell) this.tryPlace(mx, my);
        else if (!over && !g.overHud) this.dropHand();
      }
      return true;
    }
    if (input.rightPressed) {
      if (H.entry) { this.quickEquip(H.entry); return true; }
      if (H.slot && h.equip[H.slot]) { this.unequipToBag(H.slot); return true; }
      return over;
    }
    return over || !!this.hand;
  }

  // --- отрисовка
  draw(ctx) {
    const g = this.game, h = g.hero, m = g.input;
    if (this.charOpen) this.drawChar(ctx, h);
    if (this.invOpen) this.drawInv(ctx, h);
    // подсказка
    const H = this.hover;
    let tip = null;
    if (!this.hand) {
      if (H.slot && h.equip[H.slot]) tip = h.equip[H.slot];
      else if (H.entry) tip = H.entry.item;
    }
    if (tip) drawItemTooltip(ctx, tip, h, INV.win[0] - 3, m.my - 40, tip.kind === 'gear' && !Object.values(h.equip).includes(tip));
    else if (H.plus) drawPlainTip(ctx, plusTip(H.plus), m.mx + 8, m.my + 10);
    if (this.hand) {
      const [iw, ih] = [this.hand.w * CELL, this.hand.h * CELL];
      drawIcon(ctx, this.hand.icon, Math.round(m.mx - iw / 2), Math.round(m.my - ih / 2), iw, ih);
    }
  }

  drawInv(ctx, h) {
    const W = UI_ATLAS.win_inventory;
    ctx.drawImage(IMG.winInv, W.x, W.y);
    const H = this.hover;
    // кукла
    for (const [slot, r] of Object.entries(INV.slots)) {
      const it = h.equip[slot];
      const [x, y, w, hh] = r;
      if (it) {
        ctx.save(); ctx.globalAlpha = 0.35; rect(ctx, x + 2, y + 2, w - 4, hh - 4, PAL[RARITY[it.rarity].tint]); ctx.restore();
        drawIcon(ctx, it.icon, x, y, w, hh);
      }
      if (this.hand && H.slot === slot) frame(ctx, x - 1, y - 1, w + 2, hh + 2, h.canEquip(this.hand, slot) ? PAL.red_lt : PAL.nebyl);
      else if (H.slot === slot && it) frame(ctx, x - 1, y - 1, w + 2, hh + 2, PAL.bronze_lt);
      else if (this.hand && TYPE_SLOTS[this.hand.type] && TYPE_SLOTS[this.hand.type].includes(slot)) frame(ctx, x - 1, y - 1, w + 2, hh + 2, PAL.bronze);
    }
    // сетка
    const gx = INV.gx, gy = INV.gy;
    for (const e of h.inv.entries) {
      const x = gx + e.c * CELL, y = gy + e.r * CELL, w = e.item.w * CELL, hh = e.item.h * CELL;
      const hov = H.entry === e && !this.hand;
      ctx.save();
      ctx.globalAlpha = hov ? 0.45 : 0.4;
      rect(ctx, x + 1, y + 1, w - 1, hh - 1, hov ? PAL.bronze : e.item.kind === 'potion' ? PAL.wood : PAL[RARITY[e.item.rarity].tint]);
      ctx.restore();
      if (hov) frame(ctx, x, y, w + 1, hh + 1, PAL.bronze_lt);
      drawIcon(ctx, e.item.icon, x, y, w + 1, hh + 1);
      if (e.item.kind === 'gear' && e.item.req > h.level) { ctx.save(); ctx.globalAlpha = 0.25; rect(ctx, x + 1, y + 1, w - 1, hh - 1, PAL.red); ctx.restore(); }
    }
    // куда ляжет предмет с курсора
    if (this.hand && H.cell) {
      const [c, r] = this.gridTarget(this.hand, g_mx(this), g_my(this));
      const ov = h.inv.overlapping(this.hand, c, r);
      ctx.save(); ctx.globalAlpha = 0.3;
      rect(ctx, gx + c * CELL + 1, gy + r * CELL + 1, this.hand.w * CELL - 1, this.hand.h * CELL - 1, ov.length > 1 ? PAL.red : PAL.nebyl_dk);
      ctx.restore();
    }
    // подвал
    drawText(ctx, INV.ix + 6, INV.fy + 3, 'Места: ' + h.inv.used + '/40', PAL.mist, { shadow: false });
    drawText(ctx, INV.ix + INV.iw - 9, INV.fy + 3, fmtNum(h.silver), PAL.linen, { align: 'r', shadow: false });
    if (H.closeInv) frame(ctx, INV.close[0], INV.close[1], INV.close[2], INV.close[2], PAL.flame);
  }

  drawChar(ctx, h) {
    const W = UI_ATLAS.win_character, C = CHR;
    ctx.drawImage(IMG.winChar, W.x, W.y);
    const top = C.top, hx = C.hx;
    const [lx, ly] = C.lvl;
    drawText(ctx, lx + 1, ly - 4, String(h.level), PAL.bronze_hi, { align: 'c', outline: true });
    field(ctx, hx, top + 28, 150, 'Опыт', fmtNum(h.xp));
    field(ctx, hx, top + 43, 150, h.level >= 20 ? 'Предел уровней' : 'До уровня ' + (h.level + 1), fmtNum(h.xpNext), PAL.mist, PAL.mist);
    const ratio = Math.max(0, Math.min(1, h.xpRatio));
    rect(ctx, hx, top + 60, 150, 5, PAL.ink); rect(ctx, hx + 1, top + 61, 148, 3, PAL.night);
    rect(ctx, hx + 1, top + 61, Math.round(148 * ratio), 3, PAL.bronze); rect(ctx, hx + 1, top + 61, Math.round(148 * ratio), 1, PAL.bronze_hi);
    for (let i = 1; i < 10; i++) rect(ctx, hx + Math.round(150 * i / 10), top + 61, 1, 3, PAL.ink);
    drawText(ctx, C.ix + C.iw - 6, top + 58, Math.round(ratio * 100) + '%', PAL.bronze_lt, { align: 'r', shadow: false });
    // свойства
    const colw = C.colw, lx0 = C.lx0, rx0 = C.rx0, ry = C.ry;
    ATTRS.forEach((a, k) => {
      const y = ry + k * 17;
      const bonus = h[a.id] - h.base[a.id];
      field(ctx, lx0, y, colw - 18, a.name, String(h[a.id]), null, bonus > 0 ? PAL.blue_lt : PAL.bronze_hi);
      plusButton(ctx, lx0 + colw - 12, y + 1, 11, h.points > 0, this.hover.plus === a.id);
    });
    const py = C.py;
    rect(ctx, lx0, py, colw, 15, PAL.ink);
    rect(ctx, lx0 + 1, py + 1, colw - 2, 13, h.points > 0 ? PAL.red_dk : PAL.wood_dk);
    frame(ctx, lx0 + 1, py + 1, colw - 2, 13, h.points > 0 ? PAL.ember : PAL.wood_md);
    drawText(ctx, lx0 + 5, py + 4, 'Свободных очков', h.points > 0 ? PAL.flame : PAL.mist, { shadow: false });
    drawText(ctx, lx0 + colw - 6, py + 4, String(h.points), PAL.linen, { align: 'r', outline: true });
    // показатели
    const refDef = 8 + 6 * h.level;
    const derived = [
      ['Урон ЛКМ', h.dmgMin + '–' + h.dmgMax, null],
      ['Урон ПКМ', h.skillMin + '–' + h.skillMax, PAL.ember],
      ['Меткость', String(h.ar), null],
      ['Шанс попасть', Math.round(hitChance(h.ar, refDef, h.level, h.level) * 100) + '%', null],
      ['Защита', String(h.def), null],
      ['Удачный удар', Math.round(h.crit * 100) + '%', null],
      ['Жизнь', Math.ceil(h.hp) + ' / ' + h.maxHp, PAL.red_lt],
      ['Ярь', Math.floor(h.yar) + ' / ' + h.maxYar, PAL.blue_lt],
    ];
    derived.forEach(([l, v, c], k) => field(ctx, rx0, ry + k * 15, colw, l, v, null, c));
    // сопротивления
    const res = [['Огню', h.res.fire, PAL.ember], ['Холоду', h.res.cold, PAL.blue_lt], ['Порче', h.res.poison, PAL.nebyl]];
    res.forEach(([l, v, c], k) => {
      const y = C.rsy + 13 + k * 15;
      drawText(ctx, lx0 + 13, y + 3, l, c, { shadow: false });
      drawText(ctx, lx0 + colw - 4, y + 3, v + '%', PAL.linen, { align: 'r', shadow: false });
    });
    drawText(ctx, C.ix + C.iw / 2, C.hy, h.points > 0 ? 'Жми [+], чтобы вложить свободные очки' : 'Очки свойств даются за новый уровень (+5)', PAL.mist, { align: 'c', shadow: false });
    if (this.hover.closeChar) frame(ctx, C.close[0], C.close[1], C.close[2], C.close[2], PAL.flame);
  }
}

const g_mx = (ui) => ui.game.input.mx;
const g_my = (ui) => ui.game.input.my;

function frame(ctx, x, y, w, h, c) {
  rect(ctx, x, y, w, 1, c); rect(ctx, x, y + h - 1, w, 1, c); rect(ctx, x, y, 1, h, c); rect(ctx, x + w - 1, y, 1, h, c);
}
function field(ctx, x, y, w, label, value, lc, vc) {
  drawText(ctx, x + 4, y + 3, label, lc || PAL.birch, { shadow: false });
  drawText(ctx, x + w - 4, y + 3, value, vc || PAL.linen, { align: 'r', shadow: false });
}
function plusButton(ctx, x, y, s, active, hover) {
  rect(ctx, x - 1, y - 1, s + 2, s + 2, PAL.ink);
  rect(ctx, x, y, s, s, active ? PAL.bronze_lt : PAL.slate);
  rect(ctx, x + 1, y + 1, s - 2, s - 2, active ? PAL.red : PAL.slate_dk);
  rect(ctx, x + 1, y + 1, s - 2, 1, active ? PAL.red_lt : PAL.slate);
  const c = hover && active ? PAL.linen : active ? PAL.bronze_hi : PAL.slate_lt, m = s >> 1;
  rect(ctx, x + 3, y + m, s - 6, 1, c); rect(ctx, x + m, y + 3, 1, s - 6, c);
  if (hover && active) frame(ctx, x - 1, y - 1, s + 2, s + 2, PAL.flame);
}
function plusTip(attr) {
  return {
    str: ['Сила: +1% к физическому урону'],
    dex: ['Ловкость: +5 к меткости, +0,1% к удачному удару,', '+1 к защите за каждые 4 очка'],
    vit: ['Живучесть: +2 к жизни'],
    ene: ['Дух: +2 к яри, +1% к урону ведовства'],
  }[attr];
}

export function drawPlainTip(ctx, lines, x, y) {
  const w = Math.max(...lines.map((l) => textWidth(l))) + 10, h = lines.length * 10 + 6;
  x = Math.max(2, Math.min(638 - w, x)); y = Math.max(2, Math.min(312 - h, y));
  tipBox(ctx, x, y, w, h);
  lines.forEach((l, i) => drawText(ctx, x + 5, y + 4 + i * 10, l, PAL.linen, { shadow: false }));
}

function tipBox(ctx, x, y, w, h) {
  ctx.save(); ctx.globalAlpha = 0.88; rect(ctx, x, y, w, h, PAL.ink); ctx.restore();
  frame(ctx, x, y, w, h, PAL.ink);
  frame(ctx, x + 1, y + 1, w - 2, h - 2, PAL.wood_md);
  for (const [cx, cy, sx, sy] of [[x + 1, y + 1, 1, 1], [x + w - 2, y + 1, -1, 1], [x + 1, y + h - 2, 1, -1], [x + w - 2, y + h - 2, -1, -1]]) {
    rect(ctx, sx > 0 ? cx : cx - 3, cy, 4, 1, PAL.bronze_lt); rect(ctx, cx, sy > 0 ? cy : cy - 3, 1, 4, PAL.bronze_lt);
  }
}

/** Подсказка предмета (как на макете: имя цветом редкости, база, урон/броня, требования, свойства, сравнение). */
export function drawItemTooltip(ctx, it, hero, ax, ay, compare = true, anchor = 'tr') {
  const { lines, seps } = itemLines(it);
  const L = lines.map(([t, c]) => [t, c === 'req' ? (hero.level < it.req ? PAL.red_lt : PAL.linen) : PAL[c]]);
  const sepSet = new Set(seps);
  if (it.kind === 'gear') {
    if (hero.level < it.req) { sepSet.add(L.length - 1); L.push([`Снарядить можно с ${it.req}-го уровня`, PAL.mist]); }
    if (compare) {
      const slot = TYPE_SLOTS[it.type][0], cur = hero.equip[slot];
      const cmp = compareLine(it, cur);
      if (cmp) { sepSet.add(L.length - 1); L.push(cmp); }
    }
  }
  const pad = 5, lh = 11;
  const w = Math.max(...L.map(([t]) => textWidth(t))) + pad * 2 + 2;
  const h = L.length * lh - 2 + pad * 2 + sepSet.size * 3 - (sepSet.has(L.length - 1) ? 3 : 0);
  let x = anchor === 'tr' ? ax - w : ax, y = ay;
  if (x < 2) x = 2;
  x = Math.min(x, 638 - w);
  y = Math.max(2, Math.min(312 - h, y));
  tipBox(ctx, x, y, w, h);
  let yy = y + pad;
  L.forEach(([t, c], i) => {
    drawText(ctx, x + Math.round((w - textWidth(t)) / 2), yy, t, c, { shadow: false });
    yy += lh;
    if (sepSet.has(i) && i < L.length - 1) { for (let k = x + 8; k < x + w - 8; k += 2) rect(ctx, k, yy - 2, 1, 1, PAL.bronze_dk); yy += 3; }
  });
  return { x, y, w, h };
}

function compareLine(it, cur) {
  const fmt = (v) => (Math.abs(v - Math.round(v)) < 1e-6 ? String(Math.round(v)) : v.toFixed(1).replace('.', ','));
  if (it.dmg) {
    const a = (it.dmg[0] + it.dmg[1]) / 2, b = cur && cur.dmg ? (cur.dmg[0] + cur.dmg[1]) / 2 : 1.5;
    const d = a - b;
    if (Math.abs(d) < 1e-6) return ['Средний урон как у надетого', PAL.mist];
    return [`Средний урон: ${d > 0 ? '+' : '−'}${fmt(Math.abs(d))} к надетому`, d > 0 ? PAL.nebyl : PAL.red_lt];
  }
  if (it.armor != null) {
    const d = it.armor - (cur && cur.armor ? cur.armor : 0);
    if (d === 0) return ['Броня как у надетого', PAL.mist];
    return [`Броня: ${d > 0 ? '+' : '−'}${Math.abs(d)} к надетому`, d > 0 ? PAL.nebyl : PAL.red_lt];
  }
  if (!cur) return ['Слот «' + SLOT_NAMES[TYPE_SLOTS[it.type][0]] + '» свободен', PAL.nebyl];
  return null;
}

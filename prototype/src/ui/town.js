// Окна Ладоги: разговор, торг, ладья-сундук, лечение, «Забвенная вода» (GDD v1.10 §7.2–7.3).
// m1i (critics_m1f П.11–12): «Ладья» по GDD §6.9/§10 — 256×232, сетка 10×8 по 24 px, иконки тем же кодом, что в «Котомке»;
// торг — в рамке и с шапкой «Котомки», иконка у строки, столбец «Цена», цены «N сер.» (§10.1), подсказки у строк лавки.
import { PAL } from '../palette.js';
import { rect } from '../render/shapes.js';
import { drawText, textWidth } from '../core/font.js';
import { t, RU, silverText } from '../core/i18n.js';
import { CFG } from '../data/config.js';
import { POTIONS, makePotion, makeScroll } from '../data/items.js';
import { itemColor } from '../systems/loot.js';
import { priceOf, sellPrice, ensureShops } from '../systems/trade.js';
import { Npc } from '../entities/npc.js';
import { drawBagFrame, drawGrid } from './frame.js';
import { IMG, drawIconFit } from './assets.js';
import { drawGridEntries } from './grid_items.js';

const inR = (mx, my, x, y, w, h) => mx >= x && my >= y && mx < x + w && my < y + h;
/** Окно разговора и торга — на месте «Витязя» (левая половина, размер «Котомки»). */
export const WIN = { x: 3, y: 6, w: 316, h: 287 };
/** «Ладья» (GDD §6.9/§10): 256×232 в левой половине; под ней — полоса с кнопками серебра и подсказкой. */
export const STASH_WIN = { x: 32, y: 8, w: 256, h: 232 };
export const STASH_BAR = { x: 32, y: 244, w: 256, h: 54 };
export const STASH_GRID = { x: STASH_WIN.x + 8, y: STASH_WIN.y + 19 };

export class TownUI {
  constructor(game) {
    this.game = game;
    this.open = false;
    this.mode = null;
    this.role = null;
    this.npc = null;
    this.tab = 'buy';
    this.hits = [];
    this.seen = {};
    this.rumor = 0;
  }
  close() { this.open = false; this.mode = null; this.npc = null; }
  over(mx, my) {
    if (!this.open) return false;
    if (this.mode === 'stash') return inR(mx, my, STASH_WIN.x, STASH_WIN.y, STASH_WIN.w, STASH_WIN.h) || inR(mx, my, STASH_BAR.x, STASH_BAR.y, STASH_BAR.w, STASH_BAR.h);
    return inR(mx, my, WIN.x, WIN.y, WIN.w, WIN.h);
  }

  onEnter() {
    const g = this.game;
    if (g.hero) g.hero.porchaNebyli = 0;
    ensureShops(g, false);
    this.placeVyshata();
    if (g.quest.flag('m1.turnedIn')) this.ensureMal();
  }
  onLeave() {
    const g = this.game;
    g.buyback = [];
    if (g.quest.flag('vyshataSpoke')) g.quest.flags.vyshataCourt = true;
    this.close();
  }
  placeVyshata() {
    const g = this.game, d = (g.zone.npcs || []).find((n) => n.role === 'vyshata');
    if (!d) return;
    const at = g.quest.flag('vyshataCourt') ? d.court : d.pier;
    const n = g.npcs.find((x) => x.role === 'vyshata');
    const o = g.map.objects.find((x) => x.role === 'vyshata');
    if (n) { n.x = at[0]; n.y = at[1]; }
    if (o) { o.x = at[0]; o.y = at[1]; o.sx = at[0]; o.sy = at[1] + 0.7; }
  }
  ensureMal() {
    const g = this.game, M = g.zone.mal;
    if (!M || g.npcs.some((n) => n.role === 'mal')) return;
    const p = M.route[0];
    const n = new Npc('town', p[0], p[1], { name: t(M.nameKey), role: 'mal', grey: true, route: M.route, speed: M.speed, stop: M.stop });
    n.role = 'mal'; n.ri = 0; n.pause = 0;
    g.npcs.push(n);
    g.map.objects.push({ id: 'mal', type: 'npc', role: 'mal', npc: n, x: p[0], y: p[1], sx: p[0], sy: p[1] + 0.7, reach: 1.3, done: false });
  }

  openNpc(npc) {
    const g = this.game;
    g.ui.charOpen = false;
    this.open = true; this.mode = 'menu'; this.npc = npc; this.role = npc.role; this.tab = 'buy';
    g.audio.play('ui');
    const greet = RU['npc.' + npc.role + '.greet'];
    if (typeof greet === 'string') g.bark(npc, 'greet-' + npc.role, greet);
    if (npc.role === 'vyshata') { g.quest.flags.vyshataSpoke = true; this.claimM1(); }
    if (npc.role === 'mal') { this.rumorLine(); return; }
    const stage = g.quest.flag('m1.turnedIn') ? 's1' : 's0';
    const key = npc.role + ':' + stage;
    if (!this.seen[key]) { this.seen[key] = true; this.play(npc.role, stage); }
  }
  openStash() {
    const g = this.game;
    g.ui.charOpen = false;
    if (!g.ui.invOpen) g.ui.toggleInv(true);
    this.open = true; this.mode = 'stash'; this.role = 'stash'; this.npc = null;
    g.audio.play('ui');
  }
  play(role, stage) {
    const lines = RU['npc.' + role + '.' + stage];
    if (Array.isArray(lines)) this.game.dialog(lines);
  }
  rumorLine() {
    const lines = RU['npc.mal.s1'];
    if (!Array.isArray(lines) || !lines.length) return;
    const line = lines[this.rumor % lines.length];
    this.rumor++;
    this.game.dialog([line]);
  }

  claimM1() {
    const g = this.game, q = g.quest;
    if (!q.missionDone || q.flag('m1.turnedIn')) return false;
    const R = (CFG.quests.m1 || {}).reward || {}, h = g.hero, old = h.maxYar;
    h.silver += R.silver || 0;
    h.yarTier = R.yarTier || 1;
    h.yarBonusMax = R.yarMax || 0;
    h.yarRegenBonus = R.yarRegenPct || 0;
    h.bonusSkillPoints = (h.bonusSkillPoints || 0) + (R.skillPoints || 0);
    h.recalc();
    h.yar += Math.max(0, h.maxYar - old);
    q.flags['m1.turnedIn'] = true;
    q.flags.m1Reward = true;
    g.say(this.npc, R.bark || 'bark.vyshata.reward');
    g.notify(t('ui.sys.reward_silver', { n: R.silver }), PAL.bronze_hi, 'rew-s');
    g.notify(t('ui.hero.yar_tier'), PAL.blue_lt, 'rew-y');
    g.notify(t('ui.sys.reward_skill'), PAL.bronze_lt, 'rew-p');
    g.notify(t('ui.sys.mission_open', { mission: t('ui.map.m2') }), PAL.bronze_hi, 'm2');
    g.log.add(t('ui.sys.reward_silver', { n: R.silver }) + ' · ' + t('ui.hero.yar_tier') + ' · ' + t('ui.sys.reward_skill'), PAL.bronze_lt);
    g.audio.play('silver');
    ensureShops(g, true);
    this.ensureMal();
    g.syncExitWalls();
    g.autosave('turnin');   // m1i (П.15): автосейв при сдаче миссии
    return true;
  }

  heal() {
    const H = CFG.trade.heal, g = this.game, h = g.hero;
    if (H.fullHp) h.hp = h.maxHp;
    if (H.fullYar) h.yar = h.maxYar;
    if (H.clearPorcha) h.porcha = 0;
    if (H.clearPorchaNebyli) h.porchaNebyli = 0;
    g.notify(t('ui.trade.healed'), PAL.nebyl, 'heal');
    g.audio.play('buff');
    if (typeof RU['npc.vedana.heal'] === 'string' && this.npc) g.bark(this.npc, 'vedana-heal', RU['npc.vedana.heal']);
  }
  respec() {
    const g = this.game, h = g.hero;
    if (g.quest.flag('respecUsed')) return;
    h.respec();
    g.quest.flags.respecUsed = true;
    h.hp = h.maxHp; h.yar = h.maxYar;
    g.audio.play('buff');
    g.log.add(t('respec.name'), PAL.bronze_lt);
    this.mode = 'menu';
  }

  consPrice(id) { return id === 'beresta' ? CFG.trade.vedana.berestaPrice : (POTIONS[id] && POTIONS[id].price) || 0; }
  consName(id) { return id === 'beresta' ? t('item.beresta') : (POTIONS[id] && POTIONS[id].name) || id; }

  buyGear(it) {
    const g = this.game, h = g.hero, price = priceOf(it), list = g.shops[this.role];
    const i = list.indexOf(it);
    if (i < 0) return;
    if (h.silver < price) { g.notify(t('ui.error.no_silver', { n: price }), PAL.red_lt, 'silver'); g.audio.play('error'); return; }
    list.splice(i, 1);
    if (!h.inv.autoAdd(it)) { list.splice(i, 0, it); g.notify(t('ui.inventory.full'), PAL.red_lt, 'full'); g.audio.play('error'); return; }
    h.silver -= price; g.audio.play('silver');
  }
  buyCons(id, n) {
    const g = this.game, h = g.hero, price = this.consPrice(id);
    const count = Math.max(1, n | 0);
    if (h.silver < price * count) { g.notify(t('ui.error.no_silver', { n: price * count }), PAL.red_lt, 'silver'); g.audio.play('error'); return; }
    const got = [];
    for (let i = 0; i < count; i++) {
      const ok = id === 'beresta' ? h.addScroll('beresta', 1) === 0 : h.addPotion(id);
      if (!ok) break;
      got.push(1);
    }
    if (!got.length) { g.notify(t('ui.inventory.full'), PAL.red_lt, 'full'); g.audio.play('error'); return; }
    h.silver -= price * got.length;
    g.audio.play('silver');
  }
  sellEntry(entry) {
    const g = this.game, h = g.hero, it = entry.item;
    if (it.quest || it.relic) { g.notify(t('ui.error.quest_item'), PAL.mist, 'quest'); g.audio.play('error'); return; }
    const price = sellPrice(it);
    let sold;
    if (it.count > 1) { sold = { ...it, count: 1, uid: it.uid + ':' + it.count }; it.count--; }
    else { h.inv.remove(it); sold = it; }
    h.silver += price;
    g.buyback.unshift({ item: sold, price });
    g.buyback.length = Math.min(g.buyback.length, CFG.trade.buyback);
    g.audio.play('silver');
    g.log.add(t('ui.trade.sell') + ': ' + sold.name + ' +' + price, itemColor(sold));
  }
  buyBack(row) {
    const g = this.game, h = g.hero, i = g.buyback.indexOf(row);
    if (i < 0) return;
    if (h.silver < row.price) { g.notify(t('ui.error.no_silver', { n: row.price }), PAL.red_lt, 'silver'); g.audio.play('error'); return; }
    if (!h.inv.autoAdd(row.item)) { g.notify(t('ui.inventory.full'), PAL.red_lt, 'full'); g.audio.play('error'); return; }
    h.silver -= row.price;
    g.buyback.splice(i, 1);
    g.audio.play('silver');
  }
  moveSilver(toStash) {
    const g = this.game, h = g.hero;
    if (toStash) { g.stashSilver += h.silver; h.silver = 0; }
    else { h.silver += g.stashSilver; g.stashSilver = 0; }
    g.audio.play('silver');
  }
  toStash(entry) {
    const g = this.game, it = entry.item;
    if (!g.stash.autoAdd(it)) { g.notify(t('ui.inventory.full'), PAL.red_lt, 'full'); g.audio.play('error'); return; }
    g.hero.inv.remove(it);
    g.audio.play('ui');
  }
  toBag(entry) {
    const g = this.game, it = entry.item;
    if (!g.hero.inv.autoAdd(it)) { g.notify(t('ui.inventory.full'), PAL.red_lt, 'full'); g.audio.play('error'); return; }
    g.stash.remove(it);
    g.audio.play('ui');
  }

  /** Вещь-образец для подсказки строки зелья / бересты в лавке (кэш по id). */
  consItem(id) {
    this._cons = this._cons || {};
    return this._cons[id] || (this._cons[id] = id === 'beresta' ? makeScroll('beresta', 1) : makePotion(id));
  }

  handle(input) {
    const mx = input.mx, my = input.my, hit = this.hits.find((h) => inR(mx, my, h.x, h.y, h.w, h.h));
    if (!input.leftPressed) return this.over(mx, my);
    if (!hit) return this.over(mx, my);
    const g = this.game;
    if (hit.id === 'close' || hit.id === 'leave') { this.close(); g.audio.play('ui'); return true; }
    if (hit.id === 'talk') { if (this.role === 'mal') this.rumorLine(); else this.play(this.role, g.quest.flag('m1.turnedIn') ? 's1' : 's0'); return true; }
    if (hit.id === 'trade') {
      this.mode = 'trade'; this.tab = 'buy';
      const rep = RU['npc.' + this.role + '.rep'];
      if (Array.isArray(rep) && rep[0] && this.npc) g.bark(this.npc, 'rep-' + this.role, rep[0]);
      return true;
    }
    if (hit.id === 'heal') { this.heal(); return true; }
    if (hit.id === 'respec') { this.mode = 'confirm'; return true; }
    if (hit.id === 'yes') { this.respec(); return true; }
    if (hit.id === 'buyback') { this.tab = this.tab === 'back' ? 'buy' : 'back'; return true; }
    if (hit.id === 'gear') { this.buyGear(hit.item); return true; }
    if (hit.id === 'cons') { this.buyCons(hit.item, input.shift ? 5 : 1); return true; }
    if (hit.id === 'back') { this.buyBack(hit.item); return true; }
    if (hit.id === 'put') { this.moveSilver(true); return true; }
    if (hit.id === 'take') { this.moveSilver(false); return true; }
    if (hit.id === 'st-cell') {
      const e = g.stash.at(hit.c, hit.r);
      if (e && input.shift) this.toBag(e);
      return true;
    }
    return true;
  }

  /** Раскладка окна: кнопки и строки (экранные px) + зоны щелчка this.hits. */
  layout() {
    const g = this.game, hits = [], rows = [];
    if (this.mode === 'stash') {
      const S = STASH_WIN, Bb = STASH_BAR, cell = 24;
      for (let r = 0; r < g.stash.h; r++) for (let c = 0; c < g.stash.w; c++) hits.push({ id: 'st-cell', c, r, x: STASH_GRID.x + c * cell, y: STASH_GRID.y + r * cell, w: cell, h: cell });
      hits.push({ id: 'close', x: S.x + S.w - 23, y: S.y + 11, w: 13, h: 13 });
      const bw = Math.floor((Bb.w - 28) / 2);
      for (const [id, key, k] of [['put', 'ui.stash.put', 0], ['take', 'ui.stash.take', 1]]) {
        const b = { id, label: t(key), x: Bb.x + 10 + k * (bw + 8), y: Bb.y + 8, w: bw, h: 15 };
        rows.push({ ...b, kind: 'btn' }); hits.push(b);
      }
      this.hits = hits;
      return rows;
    }
    const x = WIN.x, y = WIN.y, w = WIN.w, h = WIN.h;
    hits.push({ id: 'close', x: x + w - 23, y: y + 11, w: 13, h: 13 });
    const addBtn = (id, label) => { const yy = y + 30 + rows.length * 22; const b = { id, label, x: x + 12, y: yy, w: w - 24, h: 18 }; rows.push({ ...b, kind: 'btn' }); hits.push(b); };
    if (this.mode === 'menu') {
      addBtn('talk', t('ui.npc.talk'));
      if (this.role === 'vedana' || this.role === 'tverdyata') addBtn('trade', t('ui.npc.trade'));
      if (this.role === 'vedana') addBtn('heal', t('ui.npc.heal'));
      if (this.role === 'vedana' && g.quest.flag('m1.turnedIn') && !g.quest.flag('respecUsed')) addBtn('respec', t('ui.npc.respec'));
      addBtn('leave', t('ui.npc.leave'));
    } else if (this.mode === 'confirm') {
      rows.push({ kind: 'txt', label: t('ui.trade.respec_confirm'), x: x + 14, y: y + 30, w: w - 28 });
      const yy0 = y + 30 + 40;
      for (const [k, id, label] of [[0, 'yes', t('ui.npc.respec')], [1, 'leave', t('ui.npc.leave')]]) {
        const b = { id, label, x: x + 12, y: yy0 + k * 22, w: w - 24, h: 18 }; rows.push({ ...b, kind: 'btn' }); hits.push(b);
      }
    } else if (this.mode === 'trade') {
      const back = this.tab === 'back', list = back ? g.buyback : (g.shops[this.role] || []);
      const all = list.map((it) => (back ? { item: it.item, price: it.price, hitId: 'back', ref: it, color: itemColor(it.item) } : { item: it, price: priceOf(it), hitId: 'gear', ref: it, color: itemColor(it) }));
      if (!back && this.role === 'vedana') for (const id of (g.shops.pots || []).concat(['beresta'])) all.push({ item: this.consItem(id), cons: id, price: this.consPrice(id), hitId: 'cons', ref: id, color: PAL.birch, name: this.consName(id) });
      const top = y + 34, bottom = y + h - 34, rowH = Math.max(13, Math.min(17, Math.floor((bottom - top) / Math.max(1, all.length))));
      rows.push({ kind: 'head', x: x + 12, y: y + 22, w: w - 24 });
      all.forEach((r, i) => {
        const yy = top + i * rowH;
        if (yy + rowH > bottom) return;
        rows.push({ kind: 'row', label: r.name || r.item.name, price: r.price, icon: r.item.icon, item: r.item, cons: r.cons, x: x + 12, y: yy, w: w - 24, h: rowH, color: r.color });
        hits.push({ id: r.hitId, item: r.ref, x: x + 12, y: yy, w: w - 24, h: rowH });
      });
      const b = { id: 'buyback', label: back ? t('ui.trade.buy') : t('ui.trade.buyback'), x: x + 12, y: y + h - 28, w: 120, h: 16 };
      rows.push({ ...b, kind: 'btn' }); hits.push(b);
    }
    this.hits = hits;
    return rows;
  }

  draw(ctx) {
    if (!this.open) return;
    const g = this.game, rows = this.layout(), m = g.input;
    this.hoverRow = null; this.hoverStash = null;
    if (this.mode === 'stash') return this.drawStash(ctx, rows);
    const title = this.mode === 'trade' ? t(this.role === 'vedana' ? 'ui.trade.vedana' : 'ui.trade.tverdyata') : (this.npc ? this.npc.name : '');
    drawBagFrame(ctx, WIN.x, WIN.y, WIN.w, WIN.h, title);
    this.closeBtn(ctx, WIN.x + WIN.w - 23, WIN.y + 11);
    for (const r of rows) {
      const hov = inR(m.mx, m.my, r.x, r.y, r.w, r.h || 0);
      if (r.kind === 'head') {
        drawText(ctx, r.x + r.w - 2, r.y, t('proto.trade.price'), PAL.bronze_lt, { align: 'r', shadow: false });
        for (let k = r.x; k < r.x + r.w; k += 2) rect(ctx, k, r.y + 10, 1, 1, PAL.bronze_dk);
      } else if (r.kind === 'row') {
        if (hov) { this.hoverRow = r; ctx.save(); ctx.globalAlpha = 0.35; rect(ctx, r.x, r.y, r.w, r.h - 1, PAL.bronze_dk); ctx.restore(); }
        rect(ctx, r.x, r.y, 16, r.h - 1, PAL.night);
        drawIconFit(ctx, r.icon, r.x, r.y, 16, r.h - 1, { crop: true });
        const ty = r.y + Math.round((r.h - 9) / 2);
        drawText(ctx, r.x + 20, ty, r.label, r.color || PAL.linen, { shadow: false });
        drawText(ctx, r.x + r.w - 2, ty, silverText(r.price, 'ground'), g.hero.silver >= r.price ? PAL.bronze_lt : PAL.red_lt, { align: 'r', shadow: false });
      } else if (r.kind === 'txt') {
        wrap(r.label, r.w).forEach((l, i) => drawText(ctx, r.x, r.y + i * 11, l, PAL.linen, { shadow: false }));
      } else if (r.kind === 'btn') button(ctx, r, hov);
    }
  }

  drawStash(ctx, rows) {
    const g = this.game, S = STASH_WIN, Bb = STASH_BAR, m = g.input;
    drawBagFrame(ctx, S.x, S.y, S.w, S.h, t('ui.stash.title'));
    this.closeBtn(ctx, S.x + S.w - 23, S.y + 11);
    drawGrid(ctx, STASH_GRID.x, STASH_GRID.y, g.stash.w, g.stash.h);
    const hc = inR(m.mx, m.my, STASH_GRID.x, STASH_GRID.y, g.stash.w * 24, g.stash.h * 24) ? g.stash.at(Math.floor((m.mx - STASH_GRID.x) / 24), Math.floor((m.my - STASH_GRID.y) / 24)) : null;
    this.hoverStash = g.ui.hand ? null : hc;
    drawGridEntries(ctx, g, g.stash, STASH_GRID.x, STASH_GRID.y, this.hoverStash);
    const sy = STASH_GRID.y + g.stash.h * 24 + 3;
    drawText(ctx, S.x + 10, sy, t('ui.stash.silver', { n: g.stashSilver }), PAL.bronze_lt, { shadow: false });
    drawText(ctx, S.x + S.w - 10, sy, silverText(g.hero.silver), PAL.linen, { align: 'r', shadow: false });
    drawBagFrame(ctx, Bb.x, Bb.y, Bb.w, Bb.h);
    for (const r of rows) if (r.kind === 'btn') button(ctx, r, inR(m.mx, m.my, r.x, r.y, r.w, r.h));
    const hint = wrap(t('ui.stash.hint'), Bb.w - 20);
    hint.forEach((l, i) => drawText(ctx, Bb.x + Bb.w / 2, Bb.y + 27 + i * 10, l, PAL.mist, { align: 'c', shadow: false }));
  }

  closeBtn(ctx, x, y) {
    const im = IMG.winInv;
    if (im && im.complete && im.naturalWidth) ctx.drawImage(im, 293, 11, 13, 13, x, y, 13, 13);
    else drawText(ctx, x + 6, y + 1, '×', PAL.linen, { align: 'c' });
    const m = this.game.input;
    if (inR(m.mx, m.my, x, y, 13, 13)) { rect(ctx, x, y, 13, 1, PAL.flame); rect(ctx, x, y + 12, 13, 1, PAL.flame); rect(ctx, x, y, 1, 13, PAL.flame); rect(ctx, x + 12, y, 1, 13, PAL.flame); }
  }

  /** Подсказка строки лавки или вещи в ладье — рисуется после «Котомки», справа от окна (не поверх цен). */
  drawTip(ctx, drawItemTooltip) {
    if (!this.open || this.game.ui.hand) return null;
    const g = this.game, m = g.input, h = g.hero;
    if (this.mode === 'trade' && this.hoverRow) {
      const r = this.hoverRow, it = r.item;
      const extra = [[t('ui.tip.price_buy', { n: r.price }), h.silver >= r.price ? PAL.bronze_lt : PAL.red_lt]];
      return { item: it, from: 'shop', ...drawItemTooltip(ctx, it, h, WIN.x + WIN.w + 4, m.my - 20, it.kind === 'gear', 'tl', extra) };
    }
    if (this.mode === 'stash' && this.hoverStash) {
      const it = this.hoverStash.item;
      return { item: it, from: 'stash', ...drawItemTooltip(ctx, it, h, STASH_WIN.x + STASH_WIN.w + 4, m.my - 20, it.kind === 'gear', 'tl') };
    }
    return null;
  }
}

function wrap(text, w) {
  const out = []; let cur = '';
  for (const word of String(text).split(' ')) { const nx = cur ? cur + ' ' + word : word; if (cur && textWidth(nx) > w) { out.push(cur); cur = word; } else cur = nx; }
  if (cur) out.push(cur);
  return out;
}
function button(ctx, r, hov) {
  rect(ctx, r.x, r.y, r.w, r.h, PAL.ink);
  rect(ctx, r.x + 1, r.y + 1, r.w - 2, r.h - 2, hov ? PAL.bronze_lt : PAL.bronze_dk);
  rect(ctx, r.x + 2, r.y + 2, r.w - 4, r.h - 4, hov ? PAL.red_dk : PAL.wood_dk);
  drawText(ctx, r.x + r.w / 2, r.y + Math.round((r.h - 9) / 2), r.label, hov ? PAL.flame : PAL.linen, { align: 'c', shadow: false });
}

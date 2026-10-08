// Окна Ладоги: разговор, торг, ладья-сундук, лечение, «Забвенная вода» (GDD v1.10 §7.2–7.3). Серый ящик.
import { PAL } from '../palette.js';
import { rect } from '../render/shapes.js';
import { drawText } from '../core/font.js';
import { t, RU } from '../core/i18n.js';
import { CFG } from '../data/config.js';
import { POTIONS } from '../data/items.js';
import { itemColor } from '../systems/loot.js';
import { priceOf, sellPrice, ensureShops } from '../systems/trade.js';
import { Npc } from '../entities/npc.js';

const inR = (mx, my, x, y, w, h) => mx >= x && my >= y && mx < x + w && my < y + h;
const WIN = { x: 8, y: 8, w: 300, h: 286 };

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
  over(mx, my) { return this.open && inR(mx, my, WIN.x, WIN.y, WIN.w, WIN.h); }

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
    g.notify(t('ui.sys.mission_open', { mission: 'Сопки Волхова' }), PAL.bronze_hi, 'm2');
    g.log.add(t('ui.sys.reward_silver', { n: R.silver }) + ' · ' + t('ui.hero.yar_tier') + ' · ' + t('ui.sys.reward_skill'), PAL.bronze_lt);
    g.audio.play('silver');
    ensureShops(g, true);
    this.ensureMal();
    g.syncExitWalls();
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

  layout() {
    const g = this.game, hits = [];
    const x = WIN.x, y = WIN.y, w = WIN.w;
    hits.push({ id: 'close', x: x + w - 16, y: y + 4, w: 12, h: 12 });
    const rows = [];
    const addBtn = (id, label) => { const yy = y + 28 + rows.length * 22; rows.push({ id, label, x: x + 8, y: yy, w: w - 16, h: 18 }); hits.push({ id, x: x + 8, y: yy, w: w - 16, h: 18 }); };
    if (this.mode === 'menu') {
      addBtn('talk', t('ui.npc.talk'));
      if (this.role === 'vedana' || this.role === 'tverdyata') addBtn('trade', t('ui.npc.trade'));
      if (this.role === 'vedana') addBtn('heal', t('ui.npc.heal'));
      if (this.role === 'vedana' && g.quest.flag('m1.turnedIn') && !g.quest.flag('respecUsed')) addBtn('respec', t('ui.npc.respec'));
      addBtn('leave', t('ui.npc.leave'));
    } else if (this.mode === 'confirm') {
      rows.push({ id: 'txt', label: t('ui.trade.respec_confirm'), x: x + 8, y: y + 36, w: w - 16, h: 48 });
      addBtn('yes', t('ui.npc.respec'));
      addBtn('leave', t('ui.npc.leave'));
    } else if (this.mode === 'trade') {
      const list = this.tab === 'back' ? g.buyback : (g.shops[this.role] || []);
      list.forEach((it, i) => {
        const yy = y + 26 + i * 15;
        if (yy > y + WIN.h - 36) return;
        const row = this.tab === 'back' ? it : { item: it };
        const price = this.tab === 'back' ? it.price : priceOf(it);
        const name = this.tab === 'back' ? it.item.name : it.name;
        rows.push({ id: 'row', label: name, price, x: x + 8, y: yy, w: w - 16, h: 14, color: itemColor(this.tab === 'back' ? it.item : it) });
        hits.push({ id: this.tab === 'back' ? 'back' : 'gear', item: this.tab === 'back' ? it : it, x: x + 8, y: yy, w: w - 16, h: 14 });
      });
      if (this.tab === 'buy' && this.role === 'vedana') {
        const pots = (g.shops.pots || []).concat(['beresta']);
        pots.forEach((id, i) => {
          const yy = y + 26 + (list.length + i) * 15;
          if (yy > y + WIN.h - 36) return;
          rows.push({ id: 'row', label: this.consName(id), price: this.consPrice(id), x: x + 8, y: yy, w: w - 16, h: 14, color: PAL.birch });
          hits.push({ id: 'cons', item: id, x: x + 8, y: yy, w: w - 16, h: 14 });
        });
      }
      const by = y + WIN.h - 22;
      hits.push({ id: 'buyback', x: x + 8, y: by, w: 120, h: 16 });
      rows.push({ id: 'bb', label: this.tab === 'back' ? t('ui.trade.buy') : t('ui.trade.buyback'), x: x + 8, y: by, w: 120, h: 16 });
    } else if (this.mode === 'stash') {
      const cell = 24, gx = x + 8, gy = y + 36;
      for (let r = 0; r < g.stash.h; r++) for (let c = 0; c < g.stash.w; c++) hits.push({ id: 'st-cell', c, r, x: gx + c * cell, y: gy + r * cell, w: cell, h: cell });
      rows.push({ id: 'grid', gx, gy, cell });
      const by = y + WIN.h - 22;
      hits.push({ id: 'put', x: x + 8, y: by, w: 130, h: 16 });
      hits.push({ id: 'take', x: x + 146, y: by, w: 130, h: 16 });
      rows.push({ id: 'sil', label: t('ui.stash.put'), x: x + 8, y: by, w: 130, h: 16 });
      rows.push({ id: 'sil2', label: t('ui.stash.take'), x: x + 146, y: by, w: 130, h: 16 });
    }
    this.hits = hits;
    return rows;
  }

  draw(ctx) {
    if (!this.open) return;
    const g = this.game, rows = this.layout();
    rect(ctx, WIN.x, WIN.y, WIN.w, WIN.h, PAL.night);
    rect(ctx, WIN.x + 1, WIN.y + 1, WIN.w - 2, WIN.h - 2, PAL.wood_dk);
    const title = this.mode === 'stash' ? t('obj.stash') : (this.npc ? this.npc.name : '');
    drawText(ctx, WIN.x + 8, WIN.y + 6, title, PAL.bronze_hi, { outline: true });
    drawText(ctx, WIN.x + WIN.w - 14, WIN.y + 4, '×', PAL.linen, { align: 'c' });
    if (this.mode === 'stash') {
      const grid = rows.find((r) => r.id === 'grid');
      const cell = grid.cell;
      for (let r = 0; r < g.stash.h; r++) for (let c = 0; c < g.stash.w; c++) rect(ctx, grid.gx + c * cell + 1, grid.gy + r * cell + 1, cell - 2, cell - 2, PAL.ink);
      for (const e of g.stash.entries) {
        rect(ctx, grid.gx + e.c * cell + 1, grid.gy + e.r * cell + 1, e.item.w * cell - 2, e.item.h * cell - 2, PAL.slate);
        drawText(ctx, grid.gx + e.c * cell + 2, grid.gy + e.r * cell + 2, e.item.name.slice(0, 6), itemColor(e.item), { shadow: false });
      }
      drawText(ctx, WIN.x + 8, WIN.y + 22, g.hero.silver + ' / ' + g.stashSilver, PAL.linen, { shadow: false });
    }
    for (const r of rows) {
      if (r.id === 'grid') continue;
      if (r.id === 'row') {
        drawText(ctx, r.x, r.y, r.label, r.color || PAL.linen, { shadow: false });
        drawText(ctx, r.x + r.w, r.y, String(r.price), PAL.bronze_lt, { align: 'r', shadow: false });
      } else if (r.id === 'txt') {
        drawText(ctx, r.x, r.y, r.label, PAL.linen, { shadow: false });
      } else if (r.id !== 'sil' && r.id !== 'sil2' && r.id !== 'bb') {
        rect(ctx, r.x, r.y, r.w, r.h, PAL.ink);
        drawText(ctx, r.x + 6, r.y + 4, r.label, PAL.linen, { shadow: false });
      } else {
        rect(ctx, r.x, r.y, r.w, r.h, PAL.ink);
        drawText(ctx, r.x + 4, r.y + 3, r.label, PAL.bronze_lt, { shadow: false });
      }
    }
  }
}

// Мини-карта в правом верхнем углу (макет HUD v2: 128×84 под надписью зоны, кнопки меню под ней)
// и наложение карты на всё поле по Tab (как в Diablo II). Туман войны: видно только разведанное.
import { PAL } from '../palette.js';
import { pline, rect, disc } from './shapes.js';
import { SUB } from '../world/collision.js';

const TYPE = { free: 0, water: 1, tree: 2, rock: 3, wall: 4, palisade: 5, izba: 6, idol: 7, fire: 8, bush: 2, gate: 5 };
const EDGE = { 1: PAL.sea, 2: PAL.moss, 3: PAL.slate_lt, 4: PAL.mist, 5: PAL.bronze_lt, 6: PAL.birch, 7: PAL.bronze, 8: PAL.ember };
export const MINI = { x: 506, y: 26, w: 128, h: 84 };
const REVEAL = 11;

export class Minimap {
  constructor(map) {
    this.map = map;
    const t = new Uint8Array(map.sw * map.sh);
    for (let i = 0; i < t.length; i++) if (map.water[i]) t[i] = TYPE.water;
    for (const p of map.props) {
      const [x, y, w, h] = p.fp, v = TYPE[p.type] || TYPE.rock;
      for (let sy = Math.round(y * SUB); sy < Math.round((y + h) * SUB); sy++)
        for (let sx = Math.round(x * SUB); sx < Math.round((x + w) * SUB); sx++)
          if (sx >= 0 && sy >= 0 && sx < map.sw && sy < map.sh) t[sy * map.sw + sx] = v;
    }
    // чаща тропы: непроходимый тайл без пропса — тоже лес
    if (map.forest) for (let i = 0; i < t.length; i++) if (t[i] === TYPE.free && map.sub[i]) t[i] = TYPE.tree;
    this.types = t;
    this.seen = new Uint8Array(map.w * map.h);
    this.layers = {};
    this.dirty = true;
    this.lastTile = -1;
    this.revealedCount = 0;
  }

  // слой карты для масштаба k (пикселей на тайл по полуширине ромба: тайл = 2k × k)
  layer(k) {
    let L = this.layers[k];
    if (L) return L;
    const m = this.map, ks = k / SUB;
    const W = Math.ceil((m.w + m.h) * k) + 4, H = Math.ceil(((m.w + m.h) * k) / 2) + 4;
    const ox = m.h * k + 2, oy = 2;
    const P = (u, v) => [ox + (u - v) * ks, oy + ((u + v) * ks) / 2];   // u,v — в сабтайлах
    const base = document.createElement('canvas'); base.width = W; base.height = H;
    const c = base.getContext('2d');
    const T = this.types, SW = m.sw, SH = m.sh;
    const typ = (sx, sy) => (sx < 0 || sy < 0 || sx >= SW || sy >= SH ? 2 : T[sy * SW + sx]);
    for (let sy = 0; sy < SH; sy++) for (let sx = 0; sx < SW; sx++) {
      const v = T[sy * SW + sx];
      const [px, py] = P(sx + 0.5, sy + 0.5);
      if (v === TYPE.water) { if ((sx + sy) % 2 === 0) rect(c, Math.round(px), Math.round(py), 1, 1, PAL.sea_dk); continue; }
      if (v === TYPE.tree && (sx * 7 + sy * 13) % 5 === 0) rect(c, Math.round(px), Math.round(py), 1, 1, PAL.pine);
      if (v !== TYPE.free) continue;
      if ((sx * 3 + sy * 5) % 11 === 0) rect(c, Math.round(px), Math.round(py), 1, 1, PAL.pine_dk);
      // рёбра проходимого сабтайла, граничащие с препятствием
      const sides = [[1, 0, [sx + 1, sy], [sx + 1, sy + 1]], [-1, 0, [sx, sy], [sx, sy + 1]], [0, 1, [sx, sy + 1], [sx + 1, sy + 1]], [0, -1, [sx, sy], [sx + 1, sy]]];
      for (const [dx, dy, a, b] of sides) {
        const n = typ(sx + dx, sy + dy);
        if (n === TYPE.free) continue;
        const pa = P(a[0], a[1]), pb = P(b[0], b[1]);
        pline(c, Math.round(pa[0]), Math.round(pa[1]), Math.round(pb[0]), Math.round(pb[1]), EDGE[n] || PAL.mist);
      }
    }
    const mask = document.createElement('canvas'); mask.width = W; mask.height = H;
    const out = document.createElement('canvas'); out.width = W; out.height = H;
    L = { k, base, mask, out, W, H, ox, oy, P: (x, y) => [ox + (x - y) * k, oy + ((x + y) * k) / 2] };
    this.layers[k] = L;
    this.repaintMask(L, true);
    return L;
  }

  repaintMask(L, all) {
    const c = L.mask.getContext('2d'), m = this.map, k = L.k;
    if (all) c.clearRect(0, 0, L.W, L.H);
    c.fillStyle = '#fff';
    for (let ty = 0; ty < m.h; ty++) for (let tx = 0; tx < m.w; tx++) {
      if (!this.seen[ty * m.w + tx]) continue;
      const [x, y] = L.P(tx, ty);
      c.beginPath();
      c.moveTo(x, y - 1); c.lineTo(x + k + 1, y + k / 2); c.lineTo(x, y + k + 1); c.lineTo(x - k - 1, y + k / 2); c.closePath(); c.fill();
    }
    const o = L.out.getContext('2d');
    o.globalCompositeOperation = 'source-over';
    o.clearRect(0, 0, L.W, L.H);
    o.drawImage(L.base, 0, 0);
    o.globalCompositeOperation = 'destination-in';
    o.drawImage(L.mask, 0, 0);
    o.globalCompositeOperation = 'source-over';
  }

  /** Разведать область вокруг героя (раз в смене тайла). */
  reveal(hx, hy) {
    const m = this.map, tx = Math.floor(hx), ty = Math.floor(hy);
    const id = ty * m.w + tx;
    if (id === this.lastTile) return;
    this.lastTile = id;
    let changed = false;
    for (let y = ty - REVEAL; y <= ty + REVEAL; y++) for (let x = tx - REVEAL; x <= tx + REVEAL; x++) {
      if (!m.inside(x, y) || (x - tx) ** 2 + (y - ty) ** 2 > REVEAL * REVEAL) continue;
      const i = y * m.w + x;
      if (!this.seen[i]) { this.seen[i] = 1; changed = true; this.revealedCount++; }
    }
    if (changed) this.dirty = true;
  }
  isSeen(x, y) { const m = this.map, tx = Math.floor(x), ty = Math.floor(y); return m.inside(tx, ty) && this.seen[ty * m.w + tx] === 1; }

  refresh() {
    if (!this.dirty) return;
    for (const k in this.layers) this.repaintMask(this.layers[k], true);
    this.dirty = false;
  }

  markers(ctx, game, L, offX, offY, clip) {
    const P = (x, y) => { const [a, b] = L.P(x, y); return [Math.round(a + offX), Math.round(b + offY)]; };
    const inClip = ([x, y]) => x >= clip.x + 1 && y >= clip.y + 1 && x < clip.x + clip.w - 1 && y < clip.y + clip.h - 1;
    for (const it of game.loot.items) {
      if (it.kind !== 'item' || it.item.rarity === 'normal' || !this.isSeen(it.x, it.y)) continue;
      const p = P(it.x, it.y); if (inClip(p)) rect(ctx, p[0], p[1], 1, 1, it.color);
    }
    for (const e of game.enemies) {
      if (e.dead || !this.isSeen(e.x, e.y) || Math.hypot(e.x - game.hero.x, e.y - game.hero.y) > 14) continue;
      const p = P(e.x, e.y); if (inClip(p)) rect(ctx, p[0], p[1], L.k > 3 ? 2 : 1, 1, PAL.red_lt);
    }
    const kr = game.map.krada;
    if (kr) {
      const q = P(kr.x, kr.y);
      if (inClip(q)) { disc(ctx, q[0], q[1], 3.5, PAL.ink); disc(ctx, q[0], q[1], 2.6, PAL.bronze_lt); rect(ctx, q[0], q[1], 1, 1, PAL.ink); }
    }
    const cs = game.map.churStone;
    if (cs && this.isSeen(cs.x, cs.y)) { const q = P(cs.x, cs.y); if (inClip(q)) { disc(ctx, q[0], q[1], 2.5, PAL.ink); disc(ctx, q[0], q[1], 1.6, PAL.blue_lt); } }
    // объекты задания: двери изб, сундук, тело — ромбик; выходы и ворота — всегда видны
    for (const o of game.map.objects || []) {
      if (o.done) continue;
      const way = o.type === 'exit' || o.type === 'gate';
      if (!way && !this.isSeen(o.x, o.y)) continue;
      const q = P(o.x, o.y); if (!inClip(q)) continue;
      const c = way ? (o.requires && !game.quest.flag(o.requires) ? PAL.slate_lt : PAL.bronze_hi) : PAL.flame;
      for (let r = 0; r <= 2; r++) { rect(ctx, q[0] - 2 + r, q[1] - r, 5 - r * 2, 1, r === 0 ? PAL.ink : c); rect(ctx, q[0] - 2 + r, q[1] + r, 5 - r * 2, 1, r === 0 ? PAL.ink : c); }
      rect(ctx, q[0] - 3, q[1], 1, 1, PAL.ink); rect(ctx, q[0] + 3, q[1], 1, 1, PAL.ink); rect(ctx, q[0] - 2, q[1], 5, 1, c);
    }
    const h = game.hero, hp = P(h.x, h.y);
    rect(ctx, hp[0] - 2, hp[1], 5, 1, PAL.linen); rect(ctx, hp[0], hp[1] - 2, 1, 5, PAL.linen); rect(ctx, hp[0], hp[1], 1, 1, PAL.red_lt);
  }

  drawCorner(ctx, game) {
    const { x, y, w, h } = MINI;
    this.refresh();
    const L = this.layer(2);
    ctx.save();
    ctx.globalAlpha = 0.62; rect(ctx, x, y, w, h, PAL.ink); ctx.globalAlpha = 1;
    ctx.beginPath(); ctx.rect(x + 1, y + 1, w - 2, h - 2); ctx.clip();
    const cx = x + w / 2, cy = y + h / 2 + 6;
    const [hx, hy] = L.P(game.hero.x, game.hero.y);
    const offX = Math.round(cx - hx), offY = Math.round(cy - hy);
    ctx.drawImage(L.out, offX, offY);
    this.markers(ctx, game, L, offX, offY, MINI);
    ctx.restore();
    // рамка: бронзовые уголки и пунктир (как на макете)
    const corner = (bx, by, sx, sy) => { rect(ctx, sx > 0 ? bx : bx - 6, by, 7, 1, PAL.bronze_lt); rect(ctx, bx, sy > 0 ? by : by - 6, 1, 7, PAL.bronze_lt); rect(ctx, bx + sx, by + sy, 1, 1, PAL.bronze_hi); };
    corner(x, y, 1, 1); corner(x + w - 1, y, -1, 1); corner(x, y + h - 1, 1, -1); corner(x + w - 1, y + h - 1, -1, -1);
    for (let t = 10; t < w - 10; t += 4) { rect(ctx, x + t, y, 1, 1, PAL.wood_md); rect(ctx, x + t, y + h - 1, 1, 1, PAL.wood_md); }
    for (let t = 10; t < h - 10; t += 4) { rect(ctx, x, y + t, 1, 1, PAL.wood_md); rect(ctx, x + w - 1, y + t, 1, 1, PAL.wood_md); }
  }

  drawOverlay(ctx, game) {
    this.refresh();
    const L = this.layer(6);
    const clip = { x: 0, y: 0, w: 640, h: 314 };
    const [hx, hy] = L.P(game.hero.x, game.hero.y);
    const offX = Math.round(game.camCX - hx), offY = Math.round(157 - hy);
    ctx.save();
    // тёмная подложка под большой картой (Tab/M), чтобы линии не терялись на пёстром мире
    ctx.globalAlpha = 0.62; ctx.fillStyle = PAL.ink; ctx.fillRect(clip.x, clip.y, clip.w, clip.h);
    ctx.globalAlpha = 0.9;
    ctx.drawImage(L.out, offX, offY);
    ctx.globalAlpha = 1;
    this.markers(ctx, game, L, offX, offY, clip);
    ctx.restore();
  }
}

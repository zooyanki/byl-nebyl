// Отрисовка мира: пол (пререндер), сортировка по глубине пропсов/персонажей/добычи, свет, эффекты, подписи.
import { VIEW_W, VIEW_H, HALF_W, HALF_H, PANEL_Y } from '../config.js';
import { PAL } from '../palette.js';
import { w2s } from '../core/iso.js';
import { hash2 } from '../core/rng.js';
import { T_GRASS, T_DIRT, T_WATER, T_FOREST, T_ASH } from '../world/map.js';
import { diamond, rect, ellipse, ellipseStroke, disc } from './shapes.js';
import { drawProp, propHeight, propCovers } from './props.js';
import { drawHero, drawEnemy, drawCorpse, drawGroundItem, drawProjectile, drawNpc } from './sprites.js';
import { drawText, textWidth } from '../core/font.js';
import { drawSafeRing, drawRestSparks, drawFxFrame } from './rest_fx.js';
import { CFG } from '../data/config.js';
import { drawPortal } from './portal.js';
import { ART } from './boss_art.js';

export class WorldRenderer {
  constructor(map) {
    this.map = map;
    this.floor = buildFloor(map);
    this.dark = document.createElement('canvas');
    this.dark.width = VIEW_W; this.dark.height = VIEW_H;
    this.dctx = this.dark.getContext('2d');
  }

  render(ctx, game) {
    const { map, hero, cam } = game;
    const time = game.time;
    const toS = (x, y) => game.toS(x, y);

    ctx.fillStyle = PAL.pine_dk;
    ctx.fillRect(0, 0, VIEW_W, VIEW_H);
    ctx.drawImage(this.floor, Math.round(-map.h * HALF_W - cam.x + game.camCX + game.shakeX), Math.round(-cam.y + game.camCY + game.shakeY));

    // кольца рез безопасных зон — наземный слой под всем (fx_safe_ring, раскладка R10 / R6 из JSON художника)
    const RF = game.restFx;
    if (RF) for (const R of Object.values(RF.rings)) if (R.a > 0.01) { const [cx, cy] = toS(R.x, R.y); drawSafeRing(ctx, R.R, cx, cy, R.a, R.lit); }

    // трупы и добыча — плоско на земле, всегда под персонажами (scale.md §4.1)
    for (const e of game.enemies) if (e.dead) { const [sx, sy] = toS(e.x, e.y); drawCorpse(ctx, sx, sy, e); }
    for (const it of game.loot.items) {
      const k = Math.min(1, it.dropT / 0.35);
      const [sx, sy] = toS(it.fromX + (it.x - it.fromX) * k, it.fromY + (it.y - it.fromY) * k);
      drawGroundItem(ctx, sx, sy - Math.round(Math.sin(k * Math.PI) * 16), it);
    }

    this.renderFires(ctx, game, toS, time);

    // список для сортировки по глубине
    const list = [];
    const vis = (sx, sy, h = 40) => sx > -60 && sx < VIEW_W + 60 && sy > -10 && sy - h < VIEW_H + 10;
    for (const p of map.props) {
      const [sx, sy] = toS(p.x + p.size / 2, p.y + p.size / 2);
      if (!vis(sx, sy + p.size * HALF_H, propHeight(p) + p.size * HALF_H)) continue;
      list.push({ d: p.depth, k: 0, p });
    }
    for (const e of game.enemies) if (!e.dead) list.push({ d: e.x + e.y, k: 2, e });
    if (!hero.dead) list.push({ d: hero.x + hero.y, k: 3 });
    for (const p of game.combat.projectiles) list.push({ d: p.x + p.y, k: 4, p });
    for (const n of game.npcs || []) if (!n.gone) list.push({ d: n.x + n.y, k: 5, n });
    for (const o of map.objects) if (o.type === 'portal') list.push({ d: o.x + o.y, k: 6, o });   // Чуров проход (M1c)
    list.sort((a, b) => a.d - b.d);

    // «рентген» (scale.md §4.4): то, что стоит перед героем или врагом под курсором и закрывает их, полупрозрачно
    const xray = [];
    if (!hero.dead) { const [sx, sy] = toS(hero.x, hero.y); xray.push({ d: hero.x + hero.y, x: sx - 10, y: sy - 46, w: 20, h: 48 }); }
    if (game.hoverEnemy) { const e = game.hoverEnemy, [sx, sy] = toS(e.x, e.y); xray.push({ d: e.x + e.y, x: sx - 10, y: sy - e.def.height, w: 20, h: e.def.height }); }
    const covers = (p, d) => xray.some((q) => d > q.d && propCovers(p, toS, q));
    for (const o of list) {
      if (o.k === 0) {
        if (o.p.type !== 'fire' && covers(o.p, o.d)) { ctx.save(); ctx.globalAlpha = 0.45; drawProp(ctx, o.p, toS, time); ctx.restore(); }
        else drawProp(ctx, o.p, toS, time);
      } else if (o.k === 2) {
        const [sx, sy] = toS(o.e.x, o.e.y);
        if (!vis(sx, sy)) continue;
        if (o.e.state === 'rise' && !o.e.boss) {
          // упырь со спрайтом: яма уже в кадрах rise — без clip/offset/эллипса; призванный скрыт до t=0,3
          if (o.e.kind === 'upyr' && ART.sheets.upyr_rise_se) {
            if (o.e.summoned) {
              drawFxFrame(ctx, 'k_summon', Math.floor(o.e.t * 10), sx, sy);
              if (o.e.t < 0.3) continue;
            }
            drawEnemy(ctx, sx, sy, o.e, o.e.dir, time, game.hoverEnemy === o.e);
          } else {
            const k = Math.min(1, o.e.t / (o.e.riseTime || 0.8)), hgt = o.e.def.height + 8;
            if (o.e.summoned && drawFxFrame(ctx, 'k_summon', Math.floor(o.e.t * 10), sx, sy)) {
              if (o.e.t < 0.3) continue;
            }
            ctx.save(); ctx.beginPath(); ctx.rect(sx - 30, sy - hgt - 10, 60, hgt + 12); ctx.clip();
            drawEnemy(ctx, sx, sy + Math.round((1 - k) * hgt), o.e, o.e.dir, time, game.hoverEnemy === o.e);
            ctx.restore();
            ellipse(ctx, sx, sy, 12, 4, PAL.wood_dk, 0.8 * (1 - k * 0.5));
          }
        } else drawEnemy(ctx, sx, sy, o.e, o.e.dir, time, game.hoverEnemy === o.e);
      } else if (o.k === 6) {
        const [sx, sy] = toS(o.o.x, o.o.y), P = game.portal;
        drawPortal(ctx, sx, sy, time, P ? Math.max(0, 1 - P.t / P.ttl) : 1, P ? { opened: P.opened, closingT: P.closing && P.closing.t } : null);
      } else if (o.k === 5) {
        const [sx, sy] = toS(o.n.x, o.n.y);
        ctx.save(); ctx.globalAlpha = o.n.alpha ?? 1; drawNpc(ctx, sx, sy, o.n, time); ctx.restore();
        if (o.n.role) {
          drawText(ctx, sx, sy - (o.n.def.height || 40) - 16, o.n.name, PAL.linen, { align: 'c', outline: true });
          if (o.n.mark) drawText(ctx, sx + textWidth(o.n.name) / 2 + 8, sy - (o.n.def.height || 40) - 16, o.n.mark, PAL.bronze_hi, { align: 'c', outline: true });
        }
      } else if (o.k === 3) {
        const [sx, sy] = toS(hero.x, hero.y);
        if (hero.buffs.chur) drawChurRunes(ctx, sx, sy, hero.buffs.chur, time, false);
        drawHero(ctx, sx, sy, hero, hero.dir, time);
        if (hero.buffs.chur) drawChurRunes(ctx, sx, sy, hero.buffs.chur, time, true);
        if (RF && RF.sparksFrame >= 0) drawRestSparks(ctx, sx, sy, RF.sparksFrame);     // искры отдыха поверх героя
      } else {
        const [sx, sy] = toS(o.p.x, o.p.y);
        drawProjectile(ctx, sx, sy, o.p, time);
      }
    }
    // силуэт героя, если он за препятствием
    if (!hero.dead) {
      const [sx, sy] = toS(hero.x, hero.y);
      ctx.save(); ctx.globalAlpha = 0.28; drawHero(ctx, sx, sy, hero, hero.dir, time); ctx.restore();
    } else {
      const [sx, sy] = toS(hero.x, hero.y);
      ctx.fillStyle = PAL.ink; ctx.fillRect(sx - 15, sy - 7, 30, 8);
      ctx.fillStyle = PAL.red_dk; ctx.fillRect(sx - 14, sy - 6, 22, 6);
      ctx.fillStyle = PAL.slate_lt; ctx.fillRect(sx + 7, sy - 7, 7, 6);
    }

    this.renderFx(ctx, game, toS);
    if (game.map.captions) for (const c of game.map.captions) { const [sx, sy] = toS(c.x, c.y); drawText(ctx, sx, sy, c.text, PAL.mist, { align: 'c', outline: true }); }
    this.renderLight(ctx, game, toS);
    this.renderFxText(ctx, game, toS);
    this.renderObjects(ctx, game, toS);
    this.renderLabels(ctx, game, toS);
  }

  /** Огонь на земле: факелы поджигателей (полёт по дуге — fx_torch_flight, телеграф — красный круг, GDD §5.2 E11; горящая
   *  земля — fx_burning_ground), огненный след Кривши и пепельный след Мары (kind 'trail'), телеграфы боссов (combat.teles). */
  renderFires(ctx, game, toS, time) {
    const k2 = (r) => [r * HALF_W * Math.SQRT2, r * HALF_H * Math.SQRT2];
    for (const f of game.combat.fires || []) {
      const [sx, sy] = toS(f.x, f.y), [rx, ry] = k2(f.r);
      if (!f.lit) {
        const k = Math.min(1, f.t / f.tele);
        ellipse(ctx, sx, sy, rx, ry, PAL.red, 0.12 + 0.22 * k);
        ellipseStroke(ctx, sx, sy, rx, ry, PAL.red_lt, 0.9, 1);
        ellipseStroke(ctx, sx, sy, rx * k, ry * k, PAL.red_lt, 0.7, 1);
        if (f.t < f.flight) {                                        // факел в полёте по дуге (0,6 с при любой дистанции)
          const q = f.t / f.flight, wx = f.fx + (f.x - f.fx) * q, wy = f.fy + (f.y - f.fy) * q;
          const [tx, ty] = toS(wx, wy), [ax] = toS(f.fx, f.fy), z = 22 + Math.sin(q * Math.PI) * 30;
          ellipse(ctx, tx, ty, 4, 2, PAL.ink, 0.4);                  // тень под дугой (заметка художника)
          if (!drawFxFrame(ctx, 'torch', Math.floor(f.t * 12), tx, ty - z, { flip: sx < ax })) {
            rect(ctx, tx - 1, ty - z, 2, 7, PAL.wood_lt); disc(ctx, tx, ty - z - 2, 3, PAL.ember); disc(ctx, tx, ty - z - 2, 1.6, PAL.flame);
          }
        } else {                                                     // факел лежит в центре круга
          rect(ctx, sx - 4, sy - 1, 8, 2, PAL.wood_lt);
          disc(ctx, sx + 4, sy - 3, 2.5 + Math.sin(time * 20) * 0.6, PAL.ember);
        }
      } else {
        const fade = Math.min(1, (f.burn - f.litT) / 0.6, f.kind === 'trail' ? f.litT / 0.25 : 1);
        if (f.kind === 'trail' && f.src && (f.src.kind === 'krivsha' || f.src.kind === 'mara')) {   // следы боссов — спрайты M1b (r 0,6 в родном размере)
          const kr = f.src.kind === 'krivsha', fr = Math.floor((f.litT + (f.id % 4) * 0.12) * (kr ? 8 : 6));
          if (drawFxFrame(ctx, kr ? 'k_trail' : 'm_ash', fr, sx, sy, { alpha: fade, scale: f.r / 0.6 })) continue;
        }
        if (drawFxFrame(ctx, 'burning', Math.floor((f.litT + (f.id % 6) * 0.1) * 10), sx, sy, { alpha: fade, scale: f.r })) continue;   // спрайт художника — Ø 2 тайла (r 1) в родном размере
        ellipse(ctx, sx, sy, rx, ry, PAL.red_dk, 0.55 * fade);
        ellipse(ctx, sx, sy, rx * 0.8, ry * 0.8, PAL.ember, 0.35 * fade);
        ctx.save(); ctx.globalAlpha = fade;
        for (let i = 0; i < 11; i++) {                               // языки пламени
          const a = hash2(i, f.id, 3) * Math.PI * 2, rr = Math.sqrt(hash2(i, f.id, 5)) * 0.85;
          const fx = Math.round(sx + Math.cos(a) * rx * rr), fy = Math.round(sy + Math.sin(a) * ry * rr);
          const h = 5 + Math.round((Math.sin(time * 11 + i * 1.7) + 1) * 3 + hash2(i, f.id, 7) * 4);
          rect(ctx, fx - 1, fy - h, 3, h, PAL.red_lt);
          rect(ctx, fx, fy - h + 2, 1, h - 2, PAL.flame);
        }
        ctx.restore();
      }
    }
    // телеграфы боссов и элит: конус удара когтями, круг взрыва «Жаркого» (красные, растут к моменту удара)
    for (const T of game.combat.teles || []) {
      const k = Math.min(1, T.t / T.dur), [cx, cy] = toS(T.x, T.y);
      if (T.shape === 'circle') {
        const [rx, ry] = k2(T.r);
        ellipse(ctx, cx, cy, rx, ry, PAL.red, 0.15 + 0.2 * k);
        ellipseStroke(ctx, cx, cy, rx, ry, PAL.red_lt, 0.9, 1);
        ellipseStroke(ctx, cx, cy, rx * k, ry * k, PAL.red_lt, 0.7, 1);
      } else if (T.shape === 'cone') {
        const pts = [[cx, cy]], pts2 = [[cx, cy]], n = 8;
        for (let i = 0; i <= n; i++) {
          const a = T.dir - T.half + (2 * T.half * i) / n;
          pts.push(toS(T.x + Math.cos(a) * T.r, T.y + Math.sin(a) * T.r));
          pts2.push(toS(T.x + Math.cos(a) * T.r * k, T.y + Math.sin(a) * T.r * k));
        }
        ctx.save(); ctx.globalAlpha = 0.18 + 0.2 * k; ctx.fillStyle = PAL.red; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.fill();
        ctx.globalAlpha = 0.85; ctx.strokeStyle = PAL.red_lt; ctx.lineWidth = 1; ctx.stroke();
        ctx.globalAlpha = 0.6; ctx.beginPath(); pts2.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.stroke(); ctx.restore();
      }
    }
  }

  /** Подсветка интерактивных объектов под курсором, подпись действия и полоса удержания (выбить дверь). */
  renderObjects(ctx, game, toS) {
    const o = game.hoverObj;
    if (o) {
      const [sx, sy] = toS(o.x, o.y);
      const label = game.objectLabel(o), w = textWidth(label) + 8;
      const lift = o.type === 'hut' ? 66 : o.type === 'exit' || o.type === 'gate' ? 40 : 26;
      const x0 = Math.round(sx - w / 2), y0 = sy - lift - 13;
      ctx.save(); ctx.globalAlpha = 0.85; rect(ctx, x0, y0, w, 13, PAL.ink); ctx.restore();
      ctx.strokeStyle = PAL.bronze_lt; ctx.lineWidth = 1; ctx.strokeRect(x0 + 0.5, y0 + 0.5, w - 1, 12);
      drawText(ctx, x0 + 4, y0 + 2, label, PAL.bronze_hi);
      if (o.type === 'hut') { ellipseStroke(ctx, sx, sy + 4, 14, 5, PAL.bronze_hi, 0.8, 1); }
      else ellipseStroke(ctx, sx, sy, 14, 6, PAL.bronze_hi, 0.8, 1);
    }
    const ra = game.hero.action;
    if (ra && ra.type === 'read' && !game.hero.dead) {          // чтение бересты: полоса каста 1 с
      const [sx, sy] = toS(game.hero.x, game.hero.y);
      const w = 30, k = Math.min(1, ra.t / ra.dur), y = sy - 60;
      rect(ctx, sx - w / 2 - 1, y - 1, w + 2, 5, PAL.ink);
      rect(ctx, sx - w / 2, y, w, 3, PAL.wood_dk);
      rect(ctx, sx - w / 2, y, Math.round(w * k), 3, PAL.bronze_lt);
      ellipseStroke(ctx, sx, sy, 10 + 4 * k, 4 + 2 * k, PAL.bronze_hi, 0.4 + 0.5 * k, 1);
    }
    const c = game.hero.cmd;
    ART.hold = c && c.type === 'interact' && c.started && c.obj.hold && c.obj.prop ? { prop: c.obj.prop, t: c.holdT, dur: c.obj.hold } : null;   // оверлей прогресса освящения огнища
    if (c && c.type === 'interact' && c.started && c.obj.hold) {
      const [sx, sy] = toS(game.hero.x, game.hero.y);
      const w = 30, k = Math.min(1, c.holdT / c.obj.hold), y = sy - 60;
      rect(ctx, sx - w / 2 - 1, y - 1, w + 2, 5, PAL.ink);
      rect(ctx, sx - w / 2, y, w, 3, PAL.wood_dk);
      rect(ctx, sx - w / 2, y, Math.round(w * k), 3, PAL.bronze_hi);
    }
  }

  renderFx(ctx, game, toS) {
    const fx = game.fx;
    for (const f of game.combat.sprFx || []) { const [sx, sy] = toS(f.x, f.y); drawFxFrame(ctx, f.key, Math.min(4, Math.floor(f.t * f.fps)), sx, sy); }
    for (const r of fx.rings) {
      const [sx, sy] = toS(r.x, r.y);
      const k = r.t / r.dur;
      const rr = r.radius * (0.3 + 0.7 * k);
      ellipse(ctx, sx, sy, rr * HALF_W * Math.SQRT2, rr * HALF_H * Math.SQRT2, PAL.flame, 0.35 * (1 - k));
      ellipseStroke(ctx, sx, sy, rr * HALF_W * Math.SQRT2, rr * HALF_H * Math.SQRT2, r.color, 1 - k, 2);
    }
    for (const p of fx.parts) {
      if (p.t < 0) continue;
      const [sx, sy] = toS(p.x, p.y);
      ctx.globalAlpha = Math.max(0, 1 - p.t / p.dur);
      rect(ctx, sx + p.ox, sy + p.oy, p.size, p.size, p.color);
    }
    ctx.globalAlpha = 1;
    // молнии «Перунова скока»
    for (const b of fx.bolts) {
      const k = b.t / b.dur, [sx, sy] = toS(b.x1, b.y1), [ox, oy] = toS(b.x0, b.y0);
      ctx.save();
      ctx.globalAlpha = 1 - k;
      ctx.lineWidth = 1;
      ctx.strokeStyle = PAL.blue_lt;
      ctx.setLineDash([2, 3]); ctx.beginPath(); ctx.moveTo(ox + 0.5, oy - 20.5); ctx.lineTo(sx + 0.5, sy - 20.5); ctx.stroke(); ctx.setLineDash([]);
      for (const [w, c] of [[3, PAL.blue_lt], [1, PAL.linen]]) {
        ctx.lineWidth = w; ctx.strokeStyle = c; ctx.beginPath();
        b.seg.forEach(([dx, f], i) => { const x = sx + dx + 0.5, y = sy - 150 * (1 - f); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.stroke();
      }
      ctx.restore();
    }
    // столп света при новом уровне
    const h = game.hero;
    if (h.levelFx > 0) {
      const [sx, sy] = toS(h.x, h.y);
      const a = Math.min(1, h.levelFx) * 0.45;
      ctx.save(); ctx.globalAlpha = a;
      rect(ctx, sx - 12, sy - 96, 24, 96, PAL.bronze_hi);
      ctx.globalAlpha = a * 0.6;
      rect(ctx, sx - 16, sy - 110, 32, 110, PAL.flame);
      ctx.restore();
    }
  }

  renderLight(ctx, game, toS) {
    const d = this.dctx;
    d.globalCompositeOperation = 'source-over';
    d.clearRect(0, 0, VIEW_W, VIEW_H);
    d.fillStyle = 'rgba(8,10,20,0.5)';
    d.fillRect(0, 0, VIEW_W, VIEW_H);
    d.globalCompositeOperation = 'destination-out';
    const hole = (sx, sy, r, a = 1) => {
      const g = d.createRadialGradient(sx, sy, 0, sx, sy, r);
      g.addColorStop(0, `rgba(0,0,0,${a})`);
      g.addColorStop(0.55, `rgba(0,0,0,${a * 0.7})`);
      g.addColorStop(1, 'rgba(0,0,0,0)');
      d.fillStyle = g;
      d.fillRect(sx - r, sy - r, r * 2, r * 2);
    };
    const [hx, hy] = toS(game.hero.x, game.hero.y);
    hole(hx, hy - 20, 190, 0.95);
    const warm = [];
    for (const l of game.map.lights) {
      const [sx, sy] = toS(l.x, l.y);
      // отдых у крады: свет шире и ярче (подсказка художника: радиус 3 → 4 тайла, +25%); у Чурова камня — +25%
      const src = game.restFx && game.restFx.src, F = CFG.stats.restFx || {};
      const restL = (l.krada && src === 'krada') || (l.kind === 'chur' && src === 'churov');
      const r = (l.r + (l.kind === 'fire' ? Math.sin(game.time * 7) * 4 : 0)) * (restL && l.krada ? (F.kradaLightRestMul ?? 1.333) : 1);
      hole(sx, sy - 8, r, 1); warm.push([sx, sy - 8, r, 0.22 * (restL ? (F.kradaLightRestIntensity ?? 1.25) : 1), l.hearth ? lightTint(l, game) : null]);
    }
    const pr = game.map.perun;                                       // горящий Идол Перуна: тёплый свет ~5 тайлов от корня пламени (y − 70), подсказка художника
    if (pr && pr.burning) { const [sx, sy] = toS(pr.x + 1, pr.y + 1), r = 5 * HALF_W * Math.SQRT2 + Math.sin(game.time * 7) * 4; hole(sx, sy - 70, r, 1); warm.push([sx, sy - 70, r, 0.15]); }
    for (const p of game.combat.projectiles) { const [sx, sy] = toS(p.x, p.y); hole(sx, sy - 12, 60, 0.9); warm.push([sx, sy - 12, 50, 0.25]); }
    for (const f of game.combat.fires || []) { const [sx, sy] = toS(f.x, f.y); const r = f.lit ? 70 + Math.sin(game.time * 9 + f.id) * 4 : 34; hole(sx, sy - 6, r, f.lit ? 1 : 0.6); warm.push([sx, sy - 6, r, f.lit ? 0.3 : 0.12]); }
    for (const e of game.enemies) if (!e.dead && e.def.torch) { const [sx, sy] = toS(e.x, e.y); if (sx > -60 && sx < VIEW_W + 60 && sy > -60 && sy < VIEW_H + 60) { hole(sx + 9 * e.facing, sy - 40, 46, 0.85); warm.push([sx + 9 * e.facing, sy - 40, 40, 0.22]); } }
    for (const f of game.fx.flashes) { const [sx, sy] = toS(f.x, f.y); const k = 1 - f.t / f.dur; hole(sx, sy, f.r, k); warm.push([sx, sy, f.r, 0.35 * k]); }
    ctx.drawImage(this.dark, 0, 0);
    // тёплый подсвет от огня
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (const [sx, sy, r, a, rgb] of warm) {
      const col = rgb || '230,134,43';
      const g = ctx.createRadialGradient(sx, sy, 0, sx, sy, r);
      g.addColorStop(0, `rgba(${col},${a})`);
      g.addColorStop(1, `rgba(${col},0)`);
      ctx.fillStyle = g;
      ctx.fillRect(sx - r, sy - r, r * 2, r * 2);
    }
    ctx.restore();
  }

  renderFxText(ctx, game, toS) {
    for (const t of game.fx.texts) {
      const [sx, sy] = toS(t.x, t.y);
      const k = t.t / t.dur;
      const a = k > 0.7 ? 1 - (k - 0.7) / 0.3 : 1;
      drawText(ctx, sx + t.ox, sy - t.z - k * 16, t.str, t.color, { align: 'c', outline: true, alpha: a, scale: t.big ? 2 : 1 });
    }
  }

  // Подписи предметов на земле (как в Diablo II): видны, пока зажат Alt (или включены всегда — Z);
  // без них подписывается только предмет под курсором. Плашки раздвигаются, чтобы не перекрывались.
  renderLabels(ctx, game, toS) {
    const rects = [];
    const show = game.labelsShown;
    const items = game.loot.items.filter((it) => it.dropT > 0.3 && (show || it === game.hoverGround));
    const pos = items.map((it) => { const [sx, sy] = toS(it.x, it.y); return { it, sx, sy }; });
    pos.sort((a, b) => b.sy - a.sy);
    // тела героя и врага под курсором — препятствия для плашек (подписи не закрывают героя и цель)
    const blockers = [];
    const body = (a, hgt, half) => { const [bx, by] = toS(a.x, a.y); blockers.push({ x: bx - half, y: by - hgt - 2, w: half * 2, h: hgt + 4, block: true }); };
    if (!game.hero.dead) body(game.hero, 46, 10);
    if (game.hoverEnemy && !game.hoverEnemy.dead) body(game.hoverEnemy, game.hoverEnemy.def.height, 11);
    const overlaps = (x, y, w, h, list) => list.find((r) => x < r.x + r.w && x + w > r.x && y < r.y + r.h + 1 && y + h + 1 > r.y);
    for (const p of pos) {
      const w = textWidth(p.it.label) + 7, h = 13;
      const x0 = Math.round(p.sx - w / 2), y0 = p.sy - 26;
      if (x0 + w < 0 || x0 > VIEW_W || y0 > PANEL_Y || y0 + h < 0) continue;
      // столбик вверх; если упёрлись в верх экрана — соседние столбики (QA B-08: большая куча добычи)
      let best = null;
      for (const off of [0, 1, -1, 2, -2, 3, -3]) {
        let x = x0 + off * Math.round(w / 2 + 24), y = y0;
        if (off && (x < 0 || x + w > VIEW_W)) continue;
        for (let guard = 0; guard < 60; guard++) {
          const hit = overlaps(x, y, w, h, rects) || overlaps(x, y, w, h, blockers);
          if (!hit) break;
          y = hit.y - h - 1;
        }
        if (y >= 2) { best = { x, y }; break; }
      }
      const fit = !!best;
      if (!best) best = { x: x0, y: y0 };
      const r = { x: best.x, y: best.y, w, h, item: p.it, faded: !fit && !!overlaps(best.x, best.y, w, h, blockers) };
      rects.push(r);
    }
    const m = game.input;
    let hovered = null;
    if (!game.overUi) for (const r of rects) if (m.mx >= r.x && m.mx < r.x + r.w && m.my >= r.y && m.my < r.y + r.h) hovered = r.item;
    for (const r of rects) {
      const hv = r.item === hovered || r.item === game.hoverGround;
      ctx.save();
      const fa = r.faded && !hv ? 0.4 : 1;   // не нашли места — плашка поверх героя полупрозрачна
      ctx.globalAlpha = (hv ? 0.9 : 0.72) * fa;
      ctx.fillStyle = PAL.ink;
      ctx.fillRect(r.x, r.y, r.w, r.h);
      ctx.restore();
      ctx.strokeStyle = hv ? PAL.bronze_lt : PAL.wood_md;
      ctx.lineWidth = 1;
      ctx.strokeRect(r.x + 0.5, r.y + 0.5, r.w - 1, r.h - 1);
      for (const [px, py] of [[r.x, r.y], [r.x + r.w - 1, r.y], [r.x, r.y + r.h - 1], [r.x + r.w - 1, r.y + r.h - 1]]) rect(ctx, px, py, 1, 1, PAL.bronze_lt);
      drawText(ctx, r.x + 4, r.y + 2, r.item.label, hv ? PAL.bronze_hi : r.item.color, fa < 1 ? { alpha: fa } : undefined);
    }
    game.labelRects = show ? rects : [];
    game.hoverLabel = show ? hovered : null;
  }
}

// ромб сабтайла 16×8 (½ тайла по каждой оси)
function subDiamond(ctx, x, y, c) {
  ctx.fillStyle = c;
  for (let r = 0; r < 8; r++) {
    const half = r < 4 ? 2 * (r + 1) : 2 * (8 - r);
    ctx.fillRect(x + 8 - half, y + r, half * 2, 1);
  }
}

function buildFloor(map) {
  const c = document.createElement('canvas');
  c.width = (map.w + map.h) * HALF_W;
  c.height = (map.w + map.h) * HALF_H + 2;
  const ctx = c.getContext('2d');
  const ox = map.h * HALF_W;
  const noise = (x, y) => Math.sin(x * 0.35) + Math.sin(y * 0.29 + 1) + Math.sin((x + y) * 0.17 + 2);
  const wet = (sx, sy) => map.waterSub(sx, sy) || sx < 0 || sy < 0 || sx >= map.sw || sy >= map.sh;
  for (let y = 0; y < map.h; y++) {
    for (let x = 0; x < map.w; x++) {
      const [ix, iy] = w2s(x, y);
      const px = ix + ox - HALF_W, py = iy;
      const g = map.groundAt(x, y);
      const h = hash2(x, y, 1), n = noise(x, y);
      let base, spk, spk2;
      if (g === T_WATER) {
        const shore = [[1, 0], [0, -1], [1, -1]].some(([dx, dy]) => map.groundAt(x + dx, y + dy) !== T_WATER && map.inside(x + dx, y + dy));
        base = shore ? PAL.sea : PAL.sea_dk; spk = PAL.sea; spk2 = shore ? PAL.birch : PAL.slate_lt;
      } else if (g === T_DIRT) {
        base = h < 0.5 ? PAL.wood_md : PAL.wood; spk = PAL.wood_dk; spk2 = PAL.wood_lt;
      } else if (g === T_FOREST) {                     // пол чащи: тёмная хвоя
        base = h < 0.5 ? PAL.pine_dk : PAL.pine; spk = PAL.pine_dk; spk2 = PAL.moss;
      } else if (g === T_ASH) {                        // пепелище тупика Мары (GDD v1.8.1 B-31)
        base = h < 0.5 ? PAL.slate_dk : PAL.slate; spk = PAL.ink; spk2 = PAL.slate_lt;
      } else {
        base = n < -1.1 ? PAL.pine : (n > 1.6 && h < 0.5 ? PAL.moss_lt : PAL.moss); spk = PAL.pine; spk2 = PAL.moss_lt;
      }
      diamond(ctx, px, py, base);
      for (let i = 0; i < 7; i++) {
        const a = hash2(x * 7 + i, y * 13 - i, 5), b = hash2(x * 3 - i, y * 11 + i, 9);
        const sx = Math.floor(6 + a * 20), sy = Math.floor(4 + b * 8);
        ctx.fillStyle = i % 3 === 0 ? spk2 : spk;
        if (g === T_WATER) ctx.fillRect(px + sx, py + sy, 3, 1);
        else ctx.fillRect(px + sx, py + sy, 1, 1);
      }
      if (g === T_GRASS && h > 0.8) { ctx.fillStyle = PAL.moss_lt; ctx.fillRect(px + 14, py + 6, 1, 2); ctx.fillRect(px + 16, py + 5, 1, 3); }
      // берег с точностью до сабтайла: вода на части тайла
      if (g !== T_WATER) {
        for (let j = 0; j < 2; j++) for (let i = 0; i < 2; i++) {
          const sx = x * 2 + i, sy = y * 2 + j;
          if (!map.waterSub(sx, sy)) continue;
          const [qx, qy] = w2s(sx / 2, sy / 2);
          const edge = !wet(sx + 1, sy) || !wet(sx, sy - 1) || !wet(sx + 1, sy - 1);
          subDiamond(ctx, qx + ox - 8, qy, edge ? PAL.sea : PAL.sea_dk);
          ctx.fillStyle = edge ? PAL.birch : PAL.sea;
          ctx.fillRect(qx + ox - 3 + Math.floor(hash2(sx, sy, 4) * 4), qy + 3, 3, 1);
        }
      }
    }
  }
  return c;
}

// «Чур-оберег»: кольцо рез вокруг героя (задняя половина — под героем, передняя — поверх)
function drawChurRunes(ctx, sx, sy, buff, time, front) {
  const fade = Math.min(1, buff.t / 2);
  ctx.save();
  ctx.globalAlpha = 0.85 * fade;
  for (let i = 0; i < 8; i++) {
    const a = time * 1.2 + (i * Math.PI) / 4;
    const s = Math.sin(a);
    if ((s > 0) !== front) continue;
    const x = Math.round(sx + Math.cos(a) * 16), y = Math.round(sy - 14 + s * 7);
    rect(ctx, x, y - 3, 1, 6, PAL.bronze_hi); rect(ctx, x - 1, y - 2 + (i % 3), 3, 1, PAL.bronze_hi);
  }
  ctx.restore();
  if (!front) ellipseStroke(ctx, sx, sy, 16, 7, PAL.bronze_lt, 0.5 * fade, 1);
}

/** Цвет света огнища: nebyl, пока осквернено, ember после освящения, переход за время удержания (GDD v1.10 §8.2). */
export function lightTint(l, game) {
  if (!l || !l.hearth) return '230,134,43';
  const o = l.hearth;
  let k = o.done ? 1 : 0;
  const c = game && game.hero && game.hero.cmd;
  if (!o.done && c && c.type === 'interact' && c.obj === o && c.holdT) k = Math.min(1, c.holdT / (o.hold || 3));
  const a = [138, 242, 126], b = [230, 134, 43];
  return a.map((v, i) => Math.round(v + (b[i] - v) * k)).join(',');
}

// Окно диалога (GDD v1.13 §10.4): 400×88 в (120; 222), рамка художника ui_dlg_frame_400x88 в (119; 221) (или 9-slice
// ui_dlg_frame 64×40, вставки 8 px), фон night 0,92 — кодом; портрет 64×64 в (130; 234) в рамке 68×68 (128; 232); имя (204; 230),
// черта bronze_dk y 241 (204–508); текст x 204, первая строка y 246, шаг 11, до 4 строк, ширина 304; ▼ / ■ в (502; 298), «2/3» в (470; 296).
import { PAL } from '../palette.js';
import { CFG } from '../data/config.js';
import { drawText, textWidth } from '../core/font.js';
import { rect } from './shapes.js';
import { VA } from './village_art.js';
import { t } from '../core/i18n.js';

/** 9-slice рамки ui_dlg_frame (вставки 8 px) на прямоугольник x,y,w,h; false — арта нет. */
export function drawFrame9(ctx, x, y, w, h) {
  const F = VA.ui.ui_dlg_frame;
  if (!F) return false;
  const im = F.img, [fw, fh] = F.meta.frame_size || [im.width, im.height], I = 8;
  const sx = [0, I, fw - I], sw = [I, fw - 2 * I, I], dx = [x, x + I, x + w - I], dw = [I, w - 2 * I, I];
  const sy = [0, I, fh - I], sh = [I, fh - 2 * I, I], dy = [y, y + I, y + h - I], dh = [I, h - 2 * I, I];
  for (let j = 0; j < 3; j++) for (let i = 0; i < 3; i++) if (!(i === 1 && j === 1)) ctx.drawImage(im, sx[i], sy[j], sw[i], sh[j], dx[i], dy[j], dw[i], dh[j]);
  return true;
}

export function wrapText(text, w) {
  const out = []; let cur = '';
  for (const word of String(text).split(' ')) { const nx = cur ? cur + ' ' + word : word; if (cur && textWidth(nx) > w) { out.push(cur); cur = word; } else cur = nx; }
  if (cur) out.push(cur);
  return out;
}

export function drawDialogWin(ctx, game) {
  const d = game.dlgWin;
  if (!d) return;
  const W = (CFG.dialogues && CFG.dialogues.window) || {}, x = W.x ?? 120, y = W.y ?? 222, w = W.w ?? 400, h = W.h ?? 88;
  const l = d.lines[d.i], sp = game.dlgSpeaker(l.speaker);
  ctx.save();
  ctx.globalAlpha = W.bgAlpha ?? 0.92; rect(ctx, x + 2, y + 2, w - 4, h - 4, PAL.night); ctx.globalAlpha = 1;
  const FB = VA.ui[W.frame || 'ui_dlg_frame_400x88'], [fx, fy] = W.frameAt || [119, 221];
  let frame = 'none';
  if (FB) { ctx.drawImage(FB.img, fx, fy); frame = 'baked'; } else if (drawFrame9(ctx, x, y, w, h)) frame = '9slice';
  else { ctx.strokeStyle = PAL.bronze; ctx.lineWidth = 2; ctx.strokeRect(x + 1, y + 1, w - 2, h - 2); }
  // портрет: рамка 68×68 кодом, внутри 64×64; нет портрета — силуэт slate и буква имени уставом
  const [pfx, pfy, pfw, pfh] = W.portraitFrame || [128, 232, 68, 68], [px, py] = W.portraitAt || [130, 234];
  rect(ctx, pfx, pfy, pfw, pfh, PAL.ink); rect(ctx, pfx + 1, pfy + 1, pfw - 2, pfh - 2, PAL.bronze_dk);
  const P = VA.ui[sp.portrait];
  if (P) ctx.drawImage(P.img, px, py, 64, 64);
  else { rect(ctx, px, py, 64, 64, PAL.ink); rect(ctx, px + 20, py + 14, 24, 24, PAL.slate); rect(ctx, px + 12, py + 40, 40, 24, PAL.slate); drawText(ctx, px + 32, py + 4, l.name[0] || '?', PAL.bronze_hi, { align: 'c', font: 'ustav' }); }
  // имя: NPC — bronze_hi, Ратибор — linen; черта bronze_dk
  const [nx, ny] = W.nameAt || [204, 230], tx = W.textX ?? 204, tw = W.textW ?? 304;
  drawText(ctx, nx, ny, l.name, l.speaker === 'ratibor' ? PAL.linen : PAL.bronze_hi, { outline: true });
  rect(ctx, tx, W.ruleY ?? 241, tw, 1, PAL.bronze_dk);
  // текст «машинкой»
  const lines = wrapText(l.text, tw), shown = Math.floor(d.chars);
  let left = shown;
  const drawn = [];
  for (let i = 0; i < Math.min(lines.length, W.maxLines ?? 4); i++) {
    const s = lines[i].slice(0, Math.max(0, left)); left -= lines[i].length + 1;
    if (s) drawText(ctx, tx, (W.textY ?? 246) + i * (W.lineH ?? 11), s, PAL.linen);
    drawn.push(s);
  }
  const done = shown >= l.text.length, last = d.i === d.lines.length - 1, [mx, my] = W.moreAt || [502, 298];
  if (done) {
    const ic = VA.ui[last ? 'ui_dlg_end' : 'ui_dlg_more'];
    const on = last || Math.floor(d.t * 2 * (W.blinkHz ?? 2)) % 2 === 0;
    if (on) { if (ic) ctx.drawImage(ic.img, mx, my); else drawText(ctx, mx, my - 2, last ? '■' : '▼', PAL.bronze_hi); }
  }
  if (d.lines.length > 1) { const [cx, cy] = W.counterAt || [470, 296]; drawText(ctx, cx, cy, (d.i + 1) + '/' + d.lines.length, PAL.mist); }
  ctx.restore();
  game.dlgDrawn = { x, y, w, h, frame, portrait: P ? sp.portrait : null, name: l.name, key: l.key, lines: drawn, nLines: lines.length, done, last, i: d.i, n: d.lines.length, t: game.time };
}

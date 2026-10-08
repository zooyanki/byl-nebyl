// Чуров проход (веха M1c): спрайт художника (64×84, pivot 32,74) — open / loop / fading / close @10 fps.
// Грей-бокс остаётся запасным, если ассет не загрузился. Состояния: open 0,6 с → loop → fading (life < 0,17) → closing 0,6 с.
import { PAL } from '../palette.js';
import { ellipse, ellipseStroke, rect } from './shapes.js';
import { FX, drawFxFrame, loopFrame } from './rest_fx.js';

export function drawPortal(ctx, sx, sy, time, life = 1, st = null) {
  const age = st && st.opened != null ? Math.max(0, time - st.opened) : 0;
  const closing = st && st.closingT != null;
  let key = null, fr = 0;
  if (closing) {                                         // close: 6 кадров @10 = 0,6 с
    key = 'p_close'; fr = Math.min(5, Math.floor((st.closingT || 0) * 10));
  } else if (age < 0.6) {                                // open: 6 кадров @10
    key = 'p_open'; fr = Math.min(5, Math.floor(age * 10));
  } else if (life < 0.17) {                              // fading: последние 10 с жизни (заменяет мерцание)
    key = 'p_fading'; fr = FX.sheets.p_fading ? loopFrame(FX.sheets.p_fading, time) : 0;
  } else {
    key = 'p_loop'; fr = FX.sheets.p_loop ? loopFrame(FX.sheets.p_loop, time) : 0;
  }
  if (key && FX.sheets[key] && drawFxFrame(ctx, key, fr, sx, sy)) return;
  // грей-бокс
  const fade = life < 0.17 ? 0.55 + 0.45 * Math.abs(Math.sin(time * 9)) : 1;
  const H = 40, W = 13, cy = sy - H / 2 - 2;
  ellipse(ctx, sx, sy, 16, 6, PAL.bronze_hi, 0.22 * fade);
  ellipse(ctx, sx, cy, W + 2, H / 2 + 2, PAL.ink, 0.55 * fade);
  ellipse(ctx, sx, cy, W, H / 2, PAL.sea_dk, 0.9 * fade);
  ellipse(ctx, sx, cy + 2, W - 4, H / 2 - 5, PAL.bronze, 0.35 * fade + 0.1 * Math.sin(time * 3));
  ellipseStroke(ctx, sx, cy, W, H / 2, PAL.bronze_lt, 0.95 * fade, 2);
  ellipseStroke(ctx, sx, cy, W - 2, H / 2 - 2, PAL.flame, 0.5 * fade, 1);
  for (let i = 0; i < 7; i++) {
    const a = time * 2.2 + (i / 7) * Math.PI * 2;
    const x = sx + Math.cos(a) * W, y = cy + Math.sin(a) * (H / 2);
    rect(ctx, Math.round(x), Math.round(y), 2, 2, i % 2 ? PAL.flame : PAL.bronze_hi);
  }
  for (let i = 0; i < 3; i++) {
    const y = Math.round(cy - 6 + i * 6 + Math.sin(time * 2 + i) * 1.5);
    rect(ctx, sx - 2, y, 4, 1, PAL.bronze_hi);
  }
}

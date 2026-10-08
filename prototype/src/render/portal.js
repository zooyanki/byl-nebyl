// Чуров проход (веха M1c): грей-бокс до спрайта художника (GDD §12.1.5 «Чуров проход», 8 кадров, P0).
// Стоячий овал из бронзового огня с тёплым ядром и искрами; к концу жизни (последние 10 с) мерцает и тускнеет.
import { PAL } from '../palette.js';
import { ellipse, ellipseStroke, rect } from './shapes.js';

export function drawPortal(ctx, sx, sy, time, life = 1) {
  const fade = life < 0.17 ? 0.55 + 0.45 * Math.abs(Math.sin(time * 9)) : 1;
  const H = 40, W = 13, cy = sy - H / 2 - 2;
  ellipse(ctx, sx, sy, 16, 6, PAL.bronze_hi, 0.22 * fade);                    // отсвет на земле
  ellipse(ctx, sx, cy, W + 2, H / 2 + 2, PAL.ink, 0.55 * fade);
  ellipse(ctx, sx, cy, W, H / 2, PAL.sea_dk, 0.9 * fade);                     // глубина прохода
  ellipse(ctx, sx, cy + 2, W - 4, H / 2 - 5, PAL.bronze, 0.35 * fade + 0.1 * Math.sin(time * 3));
  ellipseStroke(ctx, sx, cy, W, H / 2, PAL.bronze_lt, 0.95 * fade, 2);
  ellipseStroke(ctx, sx, cy, W - 2, H / 2 - 2, PAL.flame, 0.5 * fade, 1);
  for (let i = 0; i < 7; i++) {                                               // искры по кромке
    const a = time * 2.2 + (i / 7) * Math.PI * 2;
    const x = sx + Math.cos(a) * W, y = cy + Math.sin(a) * (H / 2);
    rect(ctx, Math.round(x), Math.round(y), 2, 2, i % 2 ? PAL.flame : PAL.bronze_hi);
  }
  for (let i = 0; i < 3; i++) {                                               // резы в ядре
    const y = Math.round(cy - 6 + i * 6 + Math.sin(time * 2 + i) * 1.5);
    rect(ctx, sx - 2, y, 4, 1, PAL.bronze_hi);
  }
}

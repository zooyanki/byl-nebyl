// Проекция мира (тайловые координаты, float) <-> изо-пиксели (до сдвига камеры).
import { HALF_W, HALF_H } from '../config.js';

export function w2s(x, y) {
  return [(x - y) * HALF_W, (x + y) * HALF_H];
}

export function s2w(sx, sy) {
  const a = sx / HALF_W, b = sy / HALF_H;
  return [(a + b) / 2, (b - a) / 2];
}

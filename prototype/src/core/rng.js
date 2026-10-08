// Детерминированный ГПСЧ (mulberry32) с удобными помощниками.
// B-35 (M1d): косметическая случайность (звук, частицы, всплывающие числа) берётся из crand — родного Math.random,
// захваченного до засева ?seed=N / тестового зерна. Так игровое зерно не зависит от того, включён ли звук и сколько
// звуков отсеяно по настенным часам (audio.last), и одно зерно даёт один и тот же бой.
export const crand = Math.random;
export function makeRng(seed) {
  let a = seed >>> 0;
  const r = () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  r.int = (lo, hi) => lo + Math.floor(r() * (hi - lo + 1));
  r.range = (lo, hi) => lo + r() * (hi - lo);
  r.pick = (arr) => arr[Math.floor(r() * arr.length)];
  r.chance = (p) => r() < p;
  return r;
}

// Хеш тайла -> [0,1), для стабильных «случайных» деталей рисования.
export function hash2(x, y, seed = 0) {
  let h = (x * 374761393 + y * 668265263 + seed * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

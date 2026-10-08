export const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const dist = (ax, ay, bx, by) => Math.hypot(bx - ax, by - ay);
export const rnd = (lo, hi) => lo + Math.random() * (hi - lo);
export const rndInt = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));

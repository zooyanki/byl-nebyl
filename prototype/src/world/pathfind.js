// A* по решётке узлов с шагом ½ тайла (design/scale.md §1), 8 направлений без срезания углов,
// штраф за узлы рядом с другими телами (обход толпы) + сглаживание пути по прямой проходимости.
import { SUB, lineWalkable, circleFree } from './collision.js';

class Heap {
  constructor() { this.f = []; this.v = []; }
  get size() { return this.v.length; }
  push(f, v) {
    const F = this.f, V = this.v; F.push(f); V.push(v);
    let i = V.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (F[p] <= F[i]) break;
      [F[p], F[i]] = [F[i], F[p]]; [V[p], V[i]] = [V[i], V[p]]; i = p;
    }
  }
  pop() {
    const F = this.f, V = this.v, top = V[0];
    const lf = F.pop(), lv = V.pop();
    if (V.length) {
      F[0] = lf; V[0] = lv;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < V.length && F[l] < F[m]) m = l;
        if (r < V.length && F[r] < F[m]) m = r;
        if (m === i) break;
        [F[m], F[i]] = [F[i], F[m]]; [V[m], V[i]] = [V[i], V[m]]; i = m;
      }
    }
    return top;
  }
}

const DIRS = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, Math.SQRT2], [1, -1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2]];

function nearestNode(pass, NW, NH, fx, fy, maxR) {
  const ci = Math.round(fx), cj = Math.round(fy);
  if (ci >= 0 && cj >= 0 && ci < NW && cj < NH && pass[cj * NW + ci]) return [ci, cj];
  for (let r = 1; r <= maxR; r++) {
    let best = null, bd = Infinity;
    for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
      if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
      const i = ci + di, j = cj + dj;
      if (i < 0 || j < 0 || i >= NW || j >= NH || !pass[j * NW + i]) continue;
      const dd = (i - fx) ** 2 + (j - fy) ** 2;
      if (dd < bd) { bd = dd; best = [i, j]; }
    }
    if (best) return best;
  }
  return null;
}

/**
 * Путь из (sx,sy) в (tx,ty) (мировые координаты) для круга радиуса r.
 * opts.avoid — тела, которые желательно обойти. Возвращает [[x,y],...] без стартовой точки или null.
 * Если цель недостижима — ведёт к ближайшему достижимому узлу.
 */
export function findPath(map, sx, sy, tx, ty, r = 0.3, opts = {}) {
  const avoid = opts.avoid && opts.avoid.length ? opts.avoid : null;
  const maxIter = opts.maxIter || 9000;
  // m1g (GDD v1.11 §8.2): opts.forbid {x, y, r} — клетки ближе r к точке не берутся; если старт уже внутри круга —
  // путь не подходит к центру ближе старта (выводит наружу в обход, а не через центр)
  const F = opts.forbid || null, fd = F ? (x, y) => Math.hypot(x - F.x, y - F.y) : null;
  const fr = F ? Math.min(F.r, fd(sx, sy) - 0.01) : 0;
  const segOk = !F || segDist(F.x, F.y, sx, sy, tx, ty) >= fr;
  if (segOk && circleFree(map, tx, ty, r) && lineWalkable(map, sx, sy, tx, ty, r, avoid)) return [[tx, ty]];
  const pass = map.passGrid(r), NW = map.sw + 1, NH = map.sh + 1;
  const st = nearestNode(pass, NW, NH, sx * SUB, sy * SUB, 3);
  const gt = nearestNode(pass, NW, NH, tx * SUB, ty * SUB, 14);
  if (!st || !gt) return null;
  const exactGoal = Math.abs(gt[0] / SUB - tx) < 0.3 && Math.abs(gt[1] / SUB - ty) < 0.3 && circleFree(map, tx, ty, r);
  const otx = tx, oty = ty;
  if (!exactGoal) { tx = gt[0] / SUB; ty = gt[1] / SUB; }
  const start = st[1] * NW + st[0], goal = gt[1] * NW + gt[0];
  // штраф у тел (кроме тех, что совсем рядом с целью или стартом)
  let pen = null;
  if (avoid) {
    pen = new Uint8Array(NW * NH);
    for (const o of avoid) {
      if (Math.hypot(o.x - tx, o.y - ty) < 1.0 || Math.hypot(o.x - sx, o.y - sy) < r + o.r + 0.05) continue;
      const rr = r + o.r + 0.1;
      for (let j = Math.floor((o.y - rr) * SUB); j <= Math.ceil((o.y + rr) * SUB); j++)
        for (let i = Math.floor((o.x - rr) * SUB); i <= Math.ceil((o.x + rr) * SUB); i++)
          if (i >= 0 && j >= 0 && i < NW && j < NH && Math.hypot(i / SUB - o.x, j / SUB - o.y) < rr) pen[j * NW + i] = 1;
    }
  }
  const N = NW * NH;
  const g = new Float32Array(N).fill(Infinity);
  const came = new Int32Array(N).fill(-1);
  const closed = new Uint8Array(N);
  const hf = (i) => {
    const dx = Math.abs((i % NW) - gt[0]), dy = Math.abs(((i / NW) | 0) - gt[1]);
    return Math.max(dx, dy) + (Math.SQRT2 - 1) * Math.min(dx, dy);
  };
  const heap = new Heap();
  g[start] = 0; heap.push(hf(start), start);
  let best = start, bestH = hf(start), iter = 0, found = false;
  while (heap.size && iter++ < maxIter) {
    const cur = heap.pop();
    if (closed[cur]) continue;
    closed[cur] = 1;
    if (cur === goal) { found = true; break; }
    const cx = cur % NW, cy = (cur / NW) | 0;
    const h = hf(cur);
    if (h < bestH) { bestH = h; best = cur; }
    for (const [dx, dy, c] of DIRS) {
      const nx = cx + dx, ny = cy + dy;
      if (nx < 0 || ny < 0 || nx >= NW || ny >= NH) continue;
      const ni = ny * NW + nx;
      if (!pass[ni] || closed[ni]) continue;
      if (dx && dy && (!pass[cy * NW + nx] || !pass[ny * NW + cx])) continue;
      if (F && fd(nx / SUB, ny / SUB) < fr) continue;
      const ng = g[cur] + c + (pen && pen[ni] ? 6 : 0);
      if (ng < g[ni]) { g[ni] = ng; came[ni] = cur; heap.push(ng + hf(ni), ni); }
    }
  }
  const end = found ? goal : best;
  const nodes = [];
  for (let i = end; i !== -1; i = came[i]) nodes.push(i);
  nodes.reverse();
  const pts = [[sx, sy]];
  for (let k = 1; k < nodes.length; k++) pts.push([(nodes[k] % NW) / SUB, ((nodes[k] / NW) | 0) / SUB]);
  if (found) { if (pts.length > 1) pts[pts.length - 1] = [tx, ty]; else pts.push([tx, ty]); }
  // цель внутри препятствия: дошагиваем от узла к ней, насколько пускает полутайловая сетка (встать вплотную к стене)
  if (found && !exactGoal) {
    const d = Math.hypot(otx - tx, oty - ty);
    let bx = tx, by = ty;
    for (let k = 1; k * 0.05 <= d; k++) {
      const qx = tx + ((otx - tx) * k * 0.05) / d, qy = ty + ((oty - ty) * k * 0.05) / d;
      if (!circleFree(map, qx, qy, r)) break;
      bx = qx; by = qy;
    }
    if (Math.hypot(bx - tx, by - ty) > 0.04) pts.push([bx, by]);
  }
  if (pts.length < 2) return null;
  // string pulling
  const out = [];
  let i = 0;
  while (i < pts.length - 1) {
    let j = pts.length - 1;
    while (j > i + 1 && !lineWalkable(map, pts[i][0], pts[i][1], pts[j][0], pts[j][1], r, avoid)) j--;
    out.push(pts[j]);
    i = j;
  }
  return out;
}

/** Расстояние от точки (px, py) до отрезка (ax, ay)–(bx, by). */
function segDist(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
  const k = L ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / L)) : 0;
  return Math.hypot(ax + dx * k - px, ay + dy * k - py);
}

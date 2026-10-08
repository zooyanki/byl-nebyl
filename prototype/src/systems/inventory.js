// Котомка: сетка 10×4 (GDD §6.9, макет «Места: 22/40»). Предмет занимает w×h ячеек.
export const GRID_W = 10, GRID_H = 4;

export class Inventory {
  constructor(w = GRID_W, h = GRID_H) { this.w = w; this.h = h; this.entries = []; } // {item, c, r}

  inBounds(item, c, r) { return c >= 0 && r >= 0 && c + item.w <= this.w && r + item.h <= this.h; }
  /** Записи, пересекающие прямоугольник предмета в позиции (c,r). */
  overlapping(item, c, r, ignore = null) {
    return this.entries.filter((e) => e.item !== ignore && c < e.c + e.item.w && c + item.w > e.c && r < e.r + e.item.h && r + item.h > e.r);
  }
  fits(item, c, r, ignore = null) { return this.inBounds(item, c, r) && this.overlapping(item, c, r, ignore).length === 0; }
  add(item, c, r) { this.entries.push({ item, c, r }); return true; }
  /** Первое свободное место: по столбцам слева направо, сверху вниз (как в D2). */
  findSpot(item) {
    for (let c = 0; c + item.w <= this.w; c++)
      for (let r = 0; r + item.h <= this.h; r++)
        if (this.fits(item, c, r)) return [c, r];
    return null;
  }
  autoAdd(item) {
    const s = this.findSpot(item);
    if (!s) return false;
    this.add(item, s[0], s[1]);
    return true;
  }
  remove(item) { const n = this.entries.length; this.entries = this.entries.filter((e) => e.item !== item); return this.entries.length < n; }
  entryOf(item) { return this.entries.find((e) => e.item === item) || null; }
  at(c, r) { return this.entries.find((e) => c >= e.c && c < e.c + e.item.w && r >= e.r && r < e.r + e.item.h) || null; }
  get used() { return this.entries.reduce((s, e) => s + e.item.w * e.item.h, 0); }
  get items() { return this.entries.map((e) => e.item); }
}

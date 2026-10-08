// Журнал событий (подобрано, выпито, новый уровень) и короткие уведомления.
export class Log {
  constructor(max = 6) { this.lines = []; this.max = max; this.time = 0; }
  add(text, color) {
    this.lines.push({ text, color, t: this.time });
    if (this.lines.length > this.max) this.lines.shift();
  }
  update(dt) { this.time += dt; this.lines = this.lines.filter((l) => this.time - l.t < 8); }
}

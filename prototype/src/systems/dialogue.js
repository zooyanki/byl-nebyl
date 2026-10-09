// Окно диалога (GDD v1.13 §10.4, задача D6): data/dialogues.json — реестр говорящих, диалоги из ключей dlg.* (act1_texts v1.3 §5).
// «Машинка» 40 зн/с; ЛКМ / Пробел / Enter — допечатать, затем следующая реплика (0,15 с ввод не принимается); Esc — закрыть,
// последствия (after) применяются как при дочитывании. Пока окно открыто — мир стоит. В бою (враг в агро в 12 тайлах) или в 3 с
// после урона окно не открывается: ждёт 3 с тишины, если герой в 8 тайлах от говорящего; не открылось за 30 с — реплики в журнал.
import { CFG } from '../data/config.js';
import { PAL } from '../palette.js';
import { t, RU } from '../core/i18n.js';

const W = () => (CFG.dialogues && CFG.dialogues.window) || {};
const isAggro = (e) => !e.dead && !e.dummy && e.state !== 'idle' && e.state !== 'return' && e.state !== 'wander' && !e.buried;

export const DialogueMixin = {
  /** Текст реплики по ключу: dlg.* — поле text; npc.*.greet/idle* — строка. */
  dlgText(key) { const v = RU[key]; return v && typeof v === 'object' && v.text != null ? v.text : t(key); },
  dlgSpeaker(id) { const S = (CFG.dialogues && CFG.dialogues.speakers) || {}; return S[id] || { nameKey: 'npc.' + id, portrait: 'portrait_' + id }; },
  /** Сборка окна: lines [{speaker, key}], after — последствия, actor — говорящий NPC (для очереди «в 8 тайлах»). */
  makeDialog(id, lines, after, actor) {
    return { id, lines: lines.map((l) => ({ speaker: l.speaker, key: l.key, text: this.dlgText(l.key), name: t(this.dlgSpeaker(l.speaker).nameKey) })),
      after: after || [], actor: actor || null, i: 0, chars: 0, lock: 0, t: 0, logged: -1 };
  },
  /** Открыть диалог по id из dialogues.json (или очередь, если опасно). true — открыт или поставлен в очередь. */
  startDialog(id, actor = null) {
    const D = CFG.dialogues && CFG.dialogues.dialogues && CFG.dialogues.dialogues[id];
    if (!D) return false;
    this.counters.dialogsStarted = (this.counters.dialogsStarted || 0) + 1;
    return this.openOrQueue(this.makeDialog(id, D.lines, D.after, actor || this.npcs.find((n) => n.role === D.who) || null));
  },
  /** Короткая реплика повторного разговора (npc.*.greet / idle* / idle_m1) — окно с одной репликой. */
  shortLine(npc, key) {
    return this.openOrQueue(this.makeDialog('short:' + key, [{ speaker: npc.role, key }], [], npc));
  },
  dlgBlocked() {
    const h = this.hero, w = W();
    if ((h.sinceHurt ?? 99) < (w.blockAfterHit ?? 3)) return true;
    return this.enemies.some((e) => isAggro(e) && Math.hypot(e.x - h.x, e.y - h.y) <= (w.blockIfAggroR ?? 12));
  },
  openOrQueue(d) {
    if (this.dlgAuto || this._sim) { this.finishDialogWin(d, true); return true; }   // замеры (g.simulate) и старые автотесты: без окна
    if (this.dlgWin || this.dlgBlocked()) { d.queuedT = this.time; d.calmT = this.time; (this.dlgQueue || (this.dlgQueue = [])).push(d); return true; }
    this.openDialogWin(d);
    return true;
  },
  openDialogWin(d) {
    this.dlgWin = d; d.i = 0; d.chars = 0; d.lock = 0; d.t = 0;
    if (this.hero.stop) this.hero.stop();
    this.logDlgLine(d);
    this.counters.dialogsOpened = (this.counters.dialogsOpened || 0) + 1;
  },
  logDlgLine(d) {
    if (d.logged >= d.i) return;
    d.logged = d.i; const l = d.lines[d.i];
    if (l) this.log.add(l.name + ': ' + l.text, PAL.linen);
  },
  /** Закрыть (дочитан / Esc / тайм-аут очереди): недочитанные реплики — в журнал, последствия — всегда. */
  finishDialogWin(d, toLog = false) {
    for (let i = Math.max(d.logged + 1, toLog ? 0 : d.i + 1); i < d.lines.length; i++) { const l = d.lines[i]; this.log.add(l.name + ': ' + l.text, PAL.linen); }
    d.logged = d.lines.length;
    if (this.dlgWin === d) this.dlgWin = null;
    this.dlgDone = this.dlgDone || {};
    this.dlgDone[d.id] = this.time;
    for (const a of d.after) {
      if (a.flag) this.quest.flags[a.flag] = true;
      if (a.bark) { this._barks[a.bark] = null; this.say(this.npcs.find((n) => n.kind === 'mal' && !n.gone) || this.hero, a.bark); }
      if (a.call === 'malRun') this.afterMalDialog();
    }
    this.quest.emit({ event: 'dialogEnd', dialog: d.id });
  },
  /** Ввод окна: true — ввод съеден (в мир не идёт). */
  dialogInput(inp) {
    const d = this.dlgWin;
    if (!d) return false;
    if (inp.pressed('Escape')) { this.finishDialogWin(d); this.audio.play('ui'); return true; }
    const go = inp.leftPressed || inp.pressed('Space') || inp.pressed('Enter') || inp.pressed('NumpadEnter');
    inp.leftPressed = false; inp.rightPressed = false;
    if (!go || d.lock > 0) return true;
    const l = d.lines[d.i];
    if (d.chars < l.text.length) { d.chars = l.text.length; d.lock = W().inputLock ?? 0.15; return true; }
    if (d.i + 1 >= d.lines.length) { this.finishDialogWin(d); this.audio.play('ui'); return true; }
    d.i++; d.chars = 0; d.lock = W().inputLock ?? 0.15; d.t = 0; this.logDlgLine(d);
    return true;
  },
  /** Каждый кадр (реальное dt): «машинка» и блокировка ввода; очередь — по игровому времени. */
  updateDialogWin(dt) {
    const d = this.dlgWin;
    if (d) {
      d.t += dt; d.lock = Math.max(0, d.lock - dt);
      const l = d.lines[d.i];
      if (l && d.chars < l.text.length) d.chars = Math.min(l.text.length, d.chars + (W().cps ?? 40) * dt);
    }
  },
  updateDialogQueue() {
    const Q = this.dlgQueue;
    if (!Q || !Q.length || this.dlgWin) return;
    const w = W(), d = Q[0], h = this.hero;
    if (this.dlgBlocked()) d.calmT = this.time;
    const near = !d.actor || d.actor === h || Math.hypot(d.actor.x - h.x, d.actor.y - h.y) <= (w.queueNearR ?? 8);
    if (this.time - d.calmT >= (w.queueCalm ?? 3) && near) { Q.shift(); this.openDialogWin(d); return; }
    if (this.time - d.queuedT >= (w.queueTimeout ?? 30)) { Q.shift(); this.finishDialogWin(d, true); this.counters.dialogsTimedOut = (this.counters.dialogsTimedOut || 0) + 1; }
  },
  /** Уход из зоны / гибель: открытое окно и очередь — в журнал, последствия применяются. */
  flushDialogs() {
    if (this.dlgWin) this.finishDialogWin(this.dlgWin);
    for (const d of this.dlgQueue || []) this.finishDialogWin(d, true);
    if (this.dlgQueue) this.dlgQueue.length = 0;
  },
};

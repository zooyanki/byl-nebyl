// Миссия и трекер целей (GDD v1.5 §8.2). Машина состояний целиком в data/quests.json:
// цель hidden → locked (серым) → active → done; условия — события игры {event, ...}; действия — реплики, диалоги, флаги.
import { CFG } from '../data/config.js';
import { t, RU } from '../core/i18n.js';
import { PAL } from '../palette.js';

const match = (cond, ev) => !!cond && Object.keys(cond).every((k) => k.startsWith('_') || cond[k] === ev[k]);

export class Quest {
  constructor(game, id = 'm1') {
    this.game = game;
    this.id = id;
    this.def = CFG.quests[id];
    this.flags = {};
    this.events = [];          // журнал событий (для автотестов)
    this.fired = new Set();    // сработавшие триггеры
    this.obj = this.def.objectives.map((o) => ({ id: o.id, def: o, state: o.state0 || 'active', n: 0, doneT: null }));
  }
  get(id) { return this.obj.find((o) => o.id === id); }
  flag(name) { return !!this.flags[name]; }
  text(o) { return t(o.def.textKey); }
  count(o) { return o.def.count ? Math.min(o.n, o.def.count) + '/' + o.def.count : ''; }
  get title() { return t(this.def.titleKey); }

  /** Событие игры: { event: 'hutFreed', hut: 'hut1' } и т. п. */
  emit(ev) {
    this.events.push({ ...ev, t: this.game.time });
    for (const o of this.obj) {
      const d = o.def;
      if (o.state === 'done') continue;
      if ((o.state === 'hidden' || o.state === 'locked') && match(d.activateOn, ev)) this.activate(o);
      if (o.state === 'done') continue;
      if (d.count && match(d.progressOn, ev)) {
        // m1g (GDD v1.11): progressUnique — счётчик по разным значениям поля (изба Мала в «Спаси выживших» — один раз)
        if (d.progressUnique) { o.seen = o.seen || new Set(); const k = ev[d.progressUnique]; if (o.seen.has(k)) continue; o.seen.add(k); }
        o.n++;
        if (o.n >= d.count) this.complete(o);
      } else if (match(d.doneOn, ev)) this.complete(o);
    }
    (this.def.triggers || []).forEach((tr, i) => {
      if (this.fired.has(i) || !match(tr.on, ev)) return;
      this.fired.add(i);
      this.run(tr.do);
    });
  }
  activate(o) {
    if (o.state === 'active') return;
    o.state = 'active';
    this.run(o.def.onActivate);
  }
  complete(o) {
    if (o.state === 'hidden' || o.state === 'locked') o.state = 'active';
    o.state = 'done';
    o.doneT = this.game.time;
    const g = this.game;
    g.notify(t('ui.sys.quest_done') + ': ' + this.text(o), PAL.bronze_hi, 'quest');
    g.log.add(t('ui.sys.quest_done') + ': ' + this.text(o), PAL.bronze_hi);
    g.audio.play('levelup');
    this.run(o.def.onDone);
    // миссия сдана, когда выполнены все обязательные цели (GDD §8.2 п.7: обязательны 1, 2, 4, 5)
    if (!this.missionDone && this.obj.every((x) => !x.def.required || x.state === 'done')) {
      this.missionDone = true;
      const m = t('ui.sys.mission_done', { mission: this.title });
      g.log.add(m, PAL.bronze_hi); g.log.add(t('proto.reward_ladoga'), PAL.bronze_lt);
      g.notify(m, PAL.bronze_hi, 'mission', 4);
      this.emit({ event: 'missionDone', mission: this.id });
    }
  }
  run(actions) {
    const g = this.game;
    for (const a of actions || []) {
      if (a.flag) this.flags[a.flag] = true;
      if (a.bark) g.say(g.hero, a.bark);
      if (a.dialog) g.startDialog(a.dialog);   // v1.13 §15: id диалога из data/dialogues.json (окно §10.4)
      if (a.notify) g.notify(t(a.notify), PAL.bronze_lt, 'qn');
      if (a.log) g.log.add(t(a.log), PAL.bronze_lt);
    }
  }
  /** Строки трекера: [{ text, count, state, alpha }] — не больше maxLines. */
  lines() {
    const now = this.game.time, fade = this.def.doneFade || 4;
    const recent = this.obj.filter((o) => o.state === 'done' && now - o.doneT < fade);
    // GDD v1.8.1 §8.2: огнища необязательны — после «Миссия пройдена» открытая цель 3 не вытесняется гаснущими обязательными
    const act = this.obj.filter((o) => o.state === 'active');
    const next = this.obj.filter((o) => o.state === 'locked' && !this.missionDone);
    const optOpen = act.filter((o) => o.def.optional), restAct = act.filter((o) => !o.def.optional);
    const ordered = this.missionDone && optOpen.length ? [...optOpen, ...recent, ...restAct, ...next] : [...recent, ...act, ...next];
    return [...this.zoneLines(), ...ordered.slice(0, this.def.maxLines || 3).map((o) => ({
      id: o.id, text: this.text(o), count: this.count(o), state: o.state,
      alpha: o.state === 'done' ? Math.max(0, Math.min(1, (fade - (now - o.doneT)) / 1.5)) : 1,
    }))];
  }
  /** m1k D5 (GDD v1.13 §7.4 п. 1): строки зоны (quests.json zoneLines[зона]) — первой строкой трекера, не цель,
   *  не считаются в maxLines; гаснут при выходе из зоны. Условия: anyActive [цели], bossKilled + notTurnedIn. */
  zoneLines() {
    const zid = this.game.zone && this.game.zone.id, Z = this.def.zoneLines && this.def.zoneLines[zid];
    if (!Z) return [];
    const ok = (w) => {
      if (!w) return true;
      if (w.anyActive && !w.anyActive.some((id) => { const o = this.get(id); return o && o.state === 'active'; })) return false;
      if (w.bossKilled && !this.events.some((e) => e.event === 'bossKilled' && e.boss === w.bossKilled)
        && !(this.obj.some((o) => o.def.doneOn && o.def.doneOn.boss === w.bossKilled && o.state === 'done'))) return false;
      if (w.notTurnedIn && this.flag(this.id + '.turnedIn')) return false;
      return true;
    };
    for (const L of Z) if (ok(L.while)) return [{ id: 'zone', zone: true, key: L.key, text: t(L.key), count: '', state: 'active', alpha: 1 }];
    return [];
  }
  /** m1k D5: метка цели зоны (§10.2): после Кривши и до сдачи — markers[зона] миссии, иначе — markers активной цели. */
  markerId(zid) {
    const M = this.def.markers && this.def.markers[zid];
    if (M && this.obj.some((o) => o.def.doneOn && o.def.doneOn.event === 'bossKilled' && o.state === 'done') && !this.flag(this.id + '.turnedIn')) return M;
    for (const q of this.obj) {
      const id = q.state === 'active' && q.def.markers && q.def.markers[zid];
      if (id) return id;
    }
    return null;
  }
  /** Все обязательные цели, доступные в прототипе, выполнены? */
  snapshot() { return this.obj.map((o) => ({ id: o.id, state: o.state, n: o.n })); }
}

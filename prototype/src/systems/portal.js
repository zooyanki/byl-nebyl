// Веха M1c: «Береста возврата» и Чуров проход (GDD v1.7 §4.4: «Открывает Чуров проход в Ладогу и обратно на 60 с», каст 1 с).
// Ладоги в прототипе нет — городской конец прохода ставится у крады Залесья (items_base.scrolls.beresta.town).
// Один проход за раз; проход живёт portalLife секунд игрового времени (в любой зоне); возвращение через него
// закрывает его (closeOnReturn — заглушка по образцу D2). Гибель проход не закрывает. Подмешивается в Game.
import { PAL } from '../palette.js';
import { CFG } from '../data/config.js';
import { SCROLLS } from '../data/items.js';
import { t, RU } from '../core/i18n.js';
import { circleFree } from '../world/collision.js';

const SC = () => SCROLLS.beresta;

export const PortalMixin = {
  /** Город-заглушка: внутри безопасного круга крады Залесья (там, где в игре будет Ладога). */
  inTown() {
    const T = SC().town, k = this.map.krada;
    if (!this.zone || this.zone.id !== T.zone || !k) return false;
    const z = (this.zone.safeZones || []).find((q) => q.at === T.at);
    return Math.hypot(this.hero.x - k.x, this.hero.y - k.y) < (z ? z.radius : 10);
  },
  /** Почему бересту сейчас не прочитать (ключ ru.json) или null. Запрета на аренах боссов в GDD нет. */
  portalBlocked() {
    if (this.inTown()) return 'ui.error.beresta_town';
    return null;
  },
  /** ПКМ по бересте в котомке. */
  useScroll(item) {
    const err = this.hero.readScroll(item, this);
    if (!err) { this.audio.play('skill'); return true; }
    if (err === 'busy') return false;
    if (err !== 'dead') { this.notify(t(err), PAL.mist, 'beresta'); this.audio.play('error'); }
    return false;
  },
  /** Конец каста: тратится одна береста, открывается проход (прежний закрывается). */
  finishScroll(item) {
    const h = this.hero;
    let stack = h.inv.items.includes(item) && item.count > 0 ? item : h.inv.items.find((it) => it.kind === 'scroll' && it.scroll === 'beresta' && it.count > 0);
    if (!stack || this.portalBlocked()) return false;
    stack.count--;
    if (stack.count <= 0) h.inv.remove(stack);
    this.openPortal();
    return true;
  },
  /** Свободное место у точки (cx, cy) на карте map на расстоянии ~r0. */
  freeSpot(map, cx, cy, r0, ang0 = Math.PI / 2) {
    for (let ring = r0; ring < r0 + 4; ring += 0.4) {
      for (let a = 0; a < 16; a++) {
        const ang = ang0 + (a % 2 ? 1 : -1) * Math.ceil(a / 2) * (Math.PI / 8);
        const x = cx + Math.cos(ang) * ring, y = cy + Math.sin(ang) * ring;
        if (circleFree(map, x, y, 0.5) && map.isReachableAt(x, y)) return [x, y];
      }
    }
    return [cx, cy];
  },
  openPortal() {
    const S = SC(), h = this.hero;
    if (this.portal) this.closePortal('replaced');
    const zone = this.zone.id, map = this.map;
    const [vx, vy] = h.dirVec();
    const [fx, fy] = this.freeSpot(map, h.x, h.y, 1.3, Math.atan2(vy, vx));
    const tst = this.zoneStates[S.town.zone] || (this.zoneStates[S.town.zone] = this.buildZone(S.town.zone));
    const k = tst.map[S.town.at] || tst.map.start;
    const [tx, ty] = this.freeSpot(tst.map, k.x, k.y, S.town.dist, Math.PI / 4);
    const mk = (end, x, y) => ({ id: 'portal_' + end, type: 'portal', end, x, y, sx: x, sy: y + 0.7, reach: S.portalReach, r: S.portalR, done: false });
    const field = mk('field', fx, fy), town = mk('town', tx, ty);
    map.objects.push(field);
    tst.map.objects.push(town);
    this.portal = { zone, tzone: S.town.zone, field, town, t: 0, ttl: S.portalLife, opened: this.time };
    this.counters.portalsOpened = (this.counters.portalsOpened || 0) + 1;
    this.fx.ring(fx, fy, 1.1, PAL.bronze_hi, 0.6); this.fx.rise(fx, fy, PAL.bronze_lt, 16, 34);
    this.audio.play('respawn');
    this.notify(t('ui.sys.portal_open'), PAL.bronze_hi, 'portal');
    this.log.add(t('ui.sys.portal_open') + ' · ' + this.portalDest(field), PAL.bronze_lt);
    if (!this._tipPortal) { this._tipPortal = true; this.log.add(t('tip.12'), PAL.birch); }
    this.quest.emit({ event: 'portalOpened', zone });
    return this.portal;
  },
  closePortal(why = 'expired') {
    const P = this.portal;
    if (!P) return;
    for (const st of Object.values(this.zoneStates)) st.map.objects = st.map.objects.filter((o) => o !== P.field && o !== P.town);
    if (this.hoverObj === P.field || this.hoverObj === P.town) this.hoverObj = null;
    const c = this.hero.cmd;
    if (c && c.type === 'interact' && (c.obj === P.field || c.obj === P.town)) this.hero.cmd = null;
    this.portal = null;
    this.counters.portalClosed = why;
    if (why === 'expired') this.log.add(t('proto.portal.closed'), PAL.mist);
  },
  /** Куда ведёт конец прохода (имя зоны назначения). */
  portalDest(o) {
    const P = this.portal, to = o.end === 'field' ? P.tzone : P.zone, z = CFG.zones[to];
    return z ? z.name : to;
  },
  portalLabel(o) {
    const name = (RU['obj.chur_portal'] || {})['Текст'] || 'Чуров проход';
    return this.portal ? name + ': ' + this.portalDest(o) : name;
  },
  /** Шагнуть в проход: из поля — к краде (город), из города — туда, где проход открыт. */
  usePortal(o) {
    const P = this.portal;
    if (!P || (o !== P.field && o !== P.town)) return false;
    const S = SC(), dst = o === P.field ? P.town : P.field, to = o === P.field ? P.tzone : P.zone;
    this.counters.portalUses = (this.counters.portalUses || 0) + 1;
    this.audio.play('respawn');
    const st = this.zoneStates[to], [x, y] = this.freeSpot(st.map, dst.x, dst.y, 0.9, Math.PI / 4);
    this.enterZone(to, { x, y });
    this.fx.ring(dst.x, dst.y, 1.0, PAL.bronze_hi, 0.5);
    this.quest.emit({ event: 'portalUsed', to: o === P.field ? 'town' : 'field' });
    if (o === P.town && S.closeOnReturn) this.closePortal('used');
    return true;
  },
  updatePortal(dt) {
    const P = this.portal;
    if (!P) return;
    P.t += dt;
    if (P.t >= P.ttl) this.closePortal('expired');
  },
};

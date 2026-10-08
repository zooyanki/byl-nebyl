// Эффекты отдыха в безопасных зонах (GDD v1.7 §4.5, §12.1.5) — спрайты художника из /workspace/game/art/sprites
// (fx_rest_krada, fx_rest_churov, fx_rest_campfire, fx_rest_sparks, fx_safe_ring; копии с метаданными — assets/fx/).
// Правила дизайнера: петли «покой» (idle) и «отдых» (rest) идут в одной фазе — состояние меняется без сброса кадра;
// искры над героем — пока растут Жизнь или Ярь (петля доигрывает до конца); кольцо рез собирается из кусков по
// раскладке JSON (R10 / R6), прозрачность 50%, видно только в 3 тайлах от границы или во время отдыха. Позы героя нет.

const DIR = 'assets/fx/';
const SHEETS = {
  krada_idle: 'fx_rest_krada_idle', krada_rest: 'fx_rest_krada_rest',
  churov_idle: 'fx_rest_churov_idle', churov_rest: 'fx_rest_churov_rest',
  campfire_idle: 'fx_rest_campfire_idle', campfire_rest: 'fx_rest_campfire_rest',     // костры М3 — в прототипе пока не стоят
  sparks: 'fx_rest_sparks',
  groove_dim: 'fx_safe_ring_grooves_dim', groove_lit: 'fx_safe_ring_grooves_lit',
  rune_dim: 'fx_safe_ring_runes_dim', rune_lit: 'fx_safe_ring_runes_lit',
  torch: 'fx_torch_flight', burning: 'fx_burning_ground',       // «Поджог» поджигателя (веха M1b)
  k_trail: 'fx_krivsha_fire_trail', k_aura: 'fx_krivsha_aura', k_summon: 'fx_krivsha_summon', k_burst: 'fx_krivsha_leap_burst',   // Кривша (спрайты M1b)
  k_feed: 'fx_krivsha_feed', k_feed_back: 'fx_krivsha_feed_back', k_feed_src: 'fx_krivsha_feed_source',                                 // «огнище питает» (v1.8)
  m_ash: 'fx_mara_ash_trail', m_bolt: 'fx_mara_bolt', m_hit: 'fx_mara_bolt_hit', a_coal: 'fx_anchutka_coal',
  p_open: 'fx_chur_portal_open', p_loop: 'fx_chur_portal_loop', p_fading: 'fx_chur_portal_fading', p_close: 'fx_chur_portal_close',   // Чуров проход (m1c)
  item_beresta: '../items/item_beresta_ground',                                                                                       // береста на земле (m1c)                                                     // Мара (спрайты M1b)
};
export const FX = { sheets: {}, ring: null, ready: false };

export function loadRestFx() {
  const one = (key, base) => Promise.all([
    fetch(DIR + base + '.json').then((r) => r.json()),
    new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => { console.warn('Не загрузился ассет', base); res(null); }; im.src = DIR + base + '.png'; }),
  ]).then(([meta, img]) => { if (img) FX.sheets[key] = { meta, img }; }).catch(() => console.warn('Не загрузился ассет', base));
  const ring = fetch(DIR + 'fx_safe_ring.json').then((r) => r.json()).then((j) => { FX.ring = j; }).catch(() => console.warn('Не загрузился ассет fx_safe_ring'));
  return Promise.all([...Object.entries(SHEETS).map(([k, b]) => one(k, b)), ring]).then(() => { FX.ready = true; });
}

/** Кадр петли: одна и та же функция времени для idle и rest — переключение без скачка (общая фаза). */
export function loopFrame(sheet, time) {
  const m = sheet.meta;
  return Math.floor(time * (m.fps || 8)) % (m.frame_count || 1);
}

function blit(ctx, sheet, frame, x, y) {
  const m = sheet.meta, [fw, fh] = m.frame_size, [px, py] = m.pivot;
  ctx.drawImage(sheet.img, frame * fw, 0, fw, fh, Math.round(x - px), Math.round(y - py), fw, fh);
}

/** Объект-источник безопасной зоны (крада / Чуров камень / костёр). Возвращает false, если спрайта нет (рисуется заглушка). */
export function drawRestSource(ctx, kind, state, x, y, time) {
  const sh = FX.sheets[kind + '_' + (state === 'rest' ? 'rest' : 'idle')];
  if (!sh) return false;
  blit(ctx, sh, loopFrame(sh, time), x, y);
  return true;
}

/** Искры над героем (кадр героя 64×64, точка опоры (32,56)). */
export function drawRestSparks(ctx, sx, sy, frame) {
  const sh = FX.sheets.sparks;
  if (!sh) return;
  blit(ctx, sh, frame, sx, sy);
}

/** Кольцо рез безопасной зоны радиуса R (тайлы) с центром (cx, cy) на экране; lit — бронзовые куски (во время отдыха). */
export function drawSafeRing(ctx, R, cx, cy, alpha, lit) {
  const L = FX.ring && FX.ring.layouts && Object.values(FX.ring.layouts).find((l) => l.radius_tiles === R);
  if (!L || alpha <= 0) return false;
  const G = FX.sheets[lit ? 'groove_lit' : 'groove_dim'], Ru = FX.sheets[lit ? 'rune_lit' : 'rune_dim'];
  if (!G || !Ru) return false;
  ctx.save(); ctx.globalAlpha = alpha;
  for (const pc of L.pieces) blit(ctx, pc.piece === 'rune' ? Ru : G, pc.index, cx + pc.dx, cy + pc.dy);
  ctx.restore();
  return true;
}

/** Спрайт-эффект по ключу: кадр frame, опора в (x, y). o.flip — зеркально (полёт факела влево), o.alpha, o.scale. */
export function drawFxFrame(ctx, key, frame, x, y, o = {}) {
  const sh = FX.sheets[key];
  if (!sh) return false;
  const m = sh.meta, [fw, fh] = m.frame_size, [px, py] = m.pivot, n = m.frame_count || 1, k = o.scale || 1;
  ctx.save(); if (o.alpha != null && o.alpha < 1) ctx.globalAlpha *= Math.max(0, o.alpha);
  ctx.translate(Math.round(x), Math.round(y)); ctx.scale(o.flip ? -k : k, k);
  ctx.drawImage(sh.img, (frame % n) * fw, 0, fw, fh, -px, -py, fw, fh);
  ctx.restore();
  return true;
}

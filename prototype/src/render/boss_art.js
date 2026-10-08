// Спрайты художника вехи M1b (art/sprites/INTEGRATION_m1b.md): Кривша (обычная и огненная фаза), Мара Пепельная,
// огнища капища, Идол Перуна. Листы — горизонтальные ленты, JSON рядом (frame_size, frame_count, fps, pivot, events);
// копии — assets/chars/<slug>/. Направления: dir 3,4,5 — лист *_ne, остальные — *_se; при dirSide < 0 — зеркало.
// Правило синхронизации (ведущий, 08.10): игровые тайминги GDD не трогаем — анимацию растягиваем / держим кадр так,
// чтобы кадр события совпал с игровым моментом. Позы — чистые функции (pose*), их проверяет tools/checks_m1c.py.
const DIR = 'assets/chars/';
const SETS = {
  krivsha: ['idle', 'walk', 'claw', 'summon', 'leap', 'emerge', 'hurt', 'death', 'fire_idle', 'fire_walk', 'fire_claw', 'fire_summon', 'fire_emerge', 'fire_hurt', 'fire_death'],
  mara: ['idle', 'walk', 'cast', 'heal', 'hurt', 'death'],
  anchutka: ['idle', 'walk', 'coal_throw', 'hurt', 'death'],          // 6а (08.10, 22:42): стаи, свита Мары
};
const PROPS = { ognishche: ['desecrated', 'consecrate', 'consecrated', 'progress'], idol_perun: ['burning', 'extinguish', 'smoking'] };
export const ART = { sheets: {}, ready: false, failed: [], hold: null };

function loadSheet(path, key) {
  return Promise.all([
    fetch(path + '.json').then((r) => r.json()),
    new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = path + '.png'; }),
  ]).then(([meta, img]) => { if (img) ART.sheets[key] = { meta, img }; else ART.failed.push(key); })
    .catch(() => { ART.failed.push(key); console.warn('Не загрузился ассет', key); });
}

export function loadBossArt() {
  const jobs = [];
  for (const [slug, anims] of Object.entries(SETS)) for (const a of anims) for (const v of ['se', 'ne']) {
    const key = `${slug}_${a}_${v}`;
    jobs.push(loadSheet(DIR + slug + '/' + key, key));
  }
  for (const [slug, states] of Object.entries(PROPS)) for (const s of states) jobs.push(loadSheet(DIR + slug + '/' + slug + '_' + s, slug + '_' + s));
  return Promise.all(jobs).then(() => { ART.ready = true; if (ART.failed.length) console.warn('Не загрузились листы:', ART.failed.join(', ')); });
}

const BACK = new Set([3, 4, 5]);
const side = (dir, fb = 1) => (dir >= 5 ? 1 : dir >= 1 && dir <= 3 ? -1 : fb);
const loopF = (time, fps, n) => Math.floor(time * fps) % n;
const once = (t, fps, n) => Math.max(0, Math.min(n - 1, Math.floor(t * fps + 1e-6)));

/** Поза Кривши: { anim, frame }. anim — без суффикса вида (krivsha_claw / krivsha_fire_claw). */
export function poseKrivsha(e, time) {
  const B = e.B || {}, fire = e.phase === 2 || e.aura, P = fire ? 'krivsha_fire_' : 'krivsha_';
  if (e.dead) return { anim: P + 'death', frame: once(e.corpseT || 0, 10, 12) };
  if (e.state === 'rise') {                                  // rise 2 с (_ph): держим кадр 0, 6 кадров @8 — последние 0,75 с
    const T = B.rise || 2, t0 = T - 6 / 8;
    return { anim: 'krivsha_emerge', frame: e.t < t0 ? 0 : once(e.t - t0, 8, 6) };
  }
  if (e.state === 'jump') {                                  // дуга 0,6 с = кадры 0–5 @10; петля 6–7; выход из огнища — за 0,75 с до конца неуязвимости
    const inv = (B.hearthPhase && B.hearthPhase.invuln) || 2, tE = inv - 6 / 8;
    if (e.t < 0.6) return { anim: 'krivsha_leap', frame: once(e.t, 10, 6) };
    if (e.t < tE) return { anim: 'krivsha_leap', frame: 6 + (Math.floor((e.t - 0.6) * 10) % 2) };
    return { anim: 'krivsha_fire_emerge', frame: once(e.t - tE, 8, 6) };
  }
  if (e.state === 'claw') {                                  // кадры 0–5 — телеграф 0,6 с (/atkMul), кадр 6 (hit_frame) — с момента удара, затем 7
    const T = e.clawTele, k = 10 * (e.atkMul || 1);
    if (T && !T.done) return { anim: P + 'claw', frame: Math.min(5, Math.floor((T.t / T.dur) * 6)) };
    const tHit = T && e.clawHitT != null ? Math.min(e.clawHitT, e.t) : 0.6 / (e.atkMul || 1);
    return { anim: P + 'claw', frame: e.t < tHit ? Math.min(5, Math.floor(e.t * k)) : Math.min(7, 6 + Math.floor((e.t - tHit) * k)) };
  }
  if (e.sumAnim != null) return { anim: P + 'summon', frame: once(e.sumAnim, 10, 8) };   // кадр 5 = срабатывание таймера призыва
  if (e.lastHitT < 0.25 && !e.moving) return { anim: P + 'hurt', frame: once(e.lastHitT, 8, 2) };
  if (e.moving) return { anim: P + 'walk', frame: loopF(time + e.id * 0.13, 9, 8) };
  return { anim: P + 'idle', frame: loopF(time + e.id * 0.13, 5, 4) };
}

/** Кадр эффекта «огнище питает» (fx_krivsha_feed*, 8 кадров @10) или -1: стартует с кадром 0 fire_emerge, кадр 6 = +15% HP. */
export function feedFrame(e) {
  if (e.state !== 'jump' || !e.B) return -1;
  const t0 = (e.B.hearthPhase.invuln || 2) - 6 / 8, u = e.t - t0;
  return u >= 0 && u < 0.8 ? Math.min(7, Math.floor(u * 10 + 1e-6)) : -1;
}

/** Поза Мары. cast: hitAt 0,7 (_ph) — анимация @10 с t = 0,4, кадр выпуска 3 = 0,7 с. heal: кадр 3 = момент лечения. */
export function poseMara(e, time) {
  if (e.dead) return { anim: 'mara_death', frame: once(e.corpseT || 0, 10, 8) };
  if (e.state === 'attack') {
    const t0 = (e.hitAt != null ? e.hitAt : 0.7) - 0.3;
    if (e.t >= t0 && e.t < t0 + 0.6) return { anim: 'mara_cast', frame: once(e.t - t0, 10, 6) };
    if (e.t < t0) return { anim: 'mara_cast', frame: 0 };
  }
  if (e.healAnim != null) return { anim: 'mara_heal', frame: once(e.healAnim, 10, 6) };
  if (e.lastHitT < 0.25) return { anim: 'mara_hurt', frame: once(e.lastHitT, 8, 2) };
  if (e.moving) return { anim: 'mara_walk', frame: loopF(time + e.id * 0.17, 8, 6) };
  return { anim: 'mara_idle', frame: loopF(time + e.id * 0.17, 8, 6) };
}

/** Поза анчутки (6а): бросок — кадр выпуска 3 ровно на hitAt (0,45; у художника 0,43 @7) — кадры 0–2 растянуты на 0..hitAt,
 *  3–4 @7 после; остаток attackTime — idle. Бег (погоня, отход, бегство) — walk @12; hurt; death @10 (последний кадр — труп). */
export function poseAnchutka(e, time) {
  if (e.dead) return { anim: 'anchutka_death', frame: once(e.corpseT || 0, 10, 6) };
  if (e.state === 'attack' && !e.moving) {
    const hitAt = e.hitAt != null ? e.hitAt : 0.45;
    if (e.t < hitAt - 1e-9) return { anim: 'anchutka_coal_throw', frame: Math.min(2, Math.floor((e.t / hitAt) * 3 + 1e-6)) };
    if (e.t < hitAt + 2 / 7) return { anim: 'anchutka_coal_throw', frame: Math.min(4, 3 + Math.floor((e.t - hitAt) * 7 + 1e-6)) };
  }
  if (e.lastHitT < 0.25 && !e.moving) return { anim: 'anchutka_hurt', frame: once(e.lastHitT, 8, 2) };
  if (e.moving) return { anim: 'anchutka_walk', frame: loopF(time + e.id * 0.11, 12, 6) };
  return { anim: 'anchutka_idle', frame: loopF(time + e.id * 0.11, 6, 4) };
}

/** Лист вида и зеркало по направлению. */
export function viewOf(dir, facing) {
  return { view: BACK.has(dir) ? 'ne' : 'se', flip: side(dir, facing) < 0 };
}

function blitF(ctx, sh, frame, x, y, flip, alpha) {
  const m = sh.meta, [fw, fh] = m.frame_size, [px, py] = m.pivot, n = m.frame_count || 1;
  ctx.save();
  if (alpha != null && alpha < 1) ctx.globalAlpha *= Math.max(0, alpha);
  ctx.translate(Math.round(x), Math.round(y)); if (flip) ctx.scale(-1, 1);
  ctx.drawImage(sh.img, (Math.max(0, frame) % n) * fw, 0, fw, fh, -px, -py, fw, fh);
  ctx.restore();
}

/** Нарисовать персонажа по позе; false — листа нет (рисуется грей-бокс). */
export function drawCharArt(ctx, pose, x, y, dir, facing, o = {}) {
  const { view, flip } = viewOf(dir, facing);
  const sh = ART.sheets[pose.anim + '_' + view] || ART.sheets[pose.anim + '_se'];
  if (!sh) return false;
  blitF(ctx, sh, pose.frame, x, y, flip, o.alpha);
  if (o.flash) {                                             // вспышка попадания: силуэт светлым поверх
    ctx.save(); ctx.globalAlpha *= 0.5; ctx.globalCompositeOperation = 'lighter'; blitF(ctx, sh, pose.frame, x, y, flip); ctx.restore();
  }
  return true;
}

/** Обводка «под курсором / элита» — 1 px контур силуэта цветом c (рисуется до спрайта). */
export function drawCharOutline(ctx, pose, x, y, dir, facing, c) {
  const { view, flip } = viewOf(dir, facing);
  const sh = ART.sheets[pose.anim + '_' + view] || ART.sheets[pose.anim + '_se'];
  if (!sh) return;
  const m = sh.meta, [fw, fh] = m.frame_size;
  const key = pose.anim + '_' + view + '_' + pose.frame + '_' + c;
  ART.ol = ART.ol || {};
  let cv = ART.ol[key];
  if (!cv) {
    cv = document.createElement('canvas'); cv.width = fw; cv.height = fh;
    const g = cv.getContext('2d');
    g.drawImage(sh.img, (pose.frame % (m.frame_count || 1)) * fw, 0, fw, fh, 0, 0, fw, fh);
    g.globalCompositeOperation = 'source-in'; g.fillStyle = c; g.fillRect(0, 0, fw, fh);
    ART.ol[key] = cv;
  }
  const [px, py] = m.pivot;
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
    ctx.save(); ctx.translate(Math.round(x) + dx, Math.round(y) + dy); if (flip) ctx.scale(-1, 1);
    ctx.drawImage(cv, -px, -py); ctx.restore();
  }
}

/** Огнище: осквернено (петля) / прогресс освящения поверх / освящение (один раз) / освящено (петля). */
export function drawHearthArt(ctx, p, x, y, time) {
  const D = ART.sheets.ognishche_desecrated, C1 = ART.sheets.ognishche_consecrate, C2 = ART.sheets.ognishche_consecrated, PR = ART.sheets.ognishche_progress;
  if (!D || !C1 || !C2) return false;
  if (p.cursed) {
    blitF(ctx, D, loopF(time, 10, 6), x, y);
    const H = ART.hold;
    if (PR && H && H.prop === p && H.t > 0) blitF(ctx, PR, Math.min(11, Math.floor(H.t / H.dur * 12)), x, y);
    return true;
  }
  const dt = p.doneAt != null ? time - p.doneAt : 99;
  if (dt >= 0 && dt < 0.6) blitF(ctx, C1, once(dt, 10, 6), x, y);
  else blitF(ctx, C2, loopF(Math.max(0, dt - 0.6), 10, 6), x, y);
  return true;
}

/** Идол Перуна: горит (петля) → гаснет (8 @8, один раз, со смерти Кривши) → дымится (петля). */
export function drawPerunArt(ctx, p, x, y, time) {
  const B = ART.sheets.idol_perun_burning, X = ART.sheets.idol_perun_extinguish, S = ART.sheets.idol_perun_smoking;
  if (!B || !X || !S) return false;
  if (p.burning) { blitF(ctx, B, loopF(time, 10, 6), x, y); return true; }
  const dt = p.outAt != null ? time - p.outAt : 99;
  if (dt >= 0 && dt < 1) blitF(ctx, X, once(dt, 8, 8), x, y);
  else blitF(ctx, S, loopF(Math.max(0, dt - 1), 8, 6), x, y);
  return true;
}

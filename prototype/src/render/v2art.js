// v2art: листы художника v2 (art/v2/, копии — assets/v2/): герой Ратибор 56 px и упырь ≈45 px в 8 направлениях
// (idle 4 кадра @4, атака героя 6 @12 c events.hit = 2, атака упыря 8 @12 c events.hit = 4; без зеркал), деревья,
// прясло тына, избы, ладья (ladya_u / ladya_v), маски окон бани / мастерской / лавки.
// v2 batch2 (INTEGRATION_v2_batch2.md): ходьба героя и упыря (8 @10, шаги на 0 и 4), «ранен» упыря, блок героя 56 px (5 анимаций,
// свои кадр и pivot), смерть героя, смерть и подъём упыря (яма в кадрах), избы 4×4 izba_small_tes / _sod, низкие деревья.
// Огонёк Небыли при гибели упыря — кодом.
import { poseUpyr } from './boss_art.js';
const DIR = 'assets/v2/';
export const V2_DIRS = ['s', 'sw', 'w', 'nw', 'n', 'ne', 'e', 'se'];   // dir прототипа 0..7 → вид листа
const CHARS = { hero: ['idle', 'attack', 'attack2', 'attack3', 'walk', 'death', 'block_raise', 'block_hold', 'block_walk', 'block_hit', 'block_break'], upyr: ['idle', 'attack', 'walk', 'hurt', 'death', 'rise'] };
const SINGLE = ['boulder_moss_a', 'boulder_moss_b', 'boulder_moss_c', 'tree_birch', 'tree_spruce', 'palisade_u4', 'izba_tes', 'izba_tes_windows', 'izba_sod', 'izba_sod_windows',
  'church_kletskaya', 'church_kletskaya_windows', 'ladya_u', 'ladya_v',
  'bld_banya_tes_windows', 'bld_banya_dern_windows', 'bld_masterskaya_windows', 'bld_lavka_windows',
  'izba_small_tes', 'izba_small_tes_windows', 'izba_small_sod', 'izba_small_sod_windows',
  'tree_spruce_h80', 'tree_spruce_h120', 'tree_birch_h96', 'tree_birch_h112'];
// v2 chars b1/b2 (INTEGRATION_v2_chars_b1/b2.md): NPC Ладоги и Залесья, idle 4 @4 / walk 8 @10 / run 6 @14, 8 видов; Соломенник
const NPCS = { vyshata: ['idle', 'walk'], priest: ['idle', 'walk'], milusha: ['idle', 'walk'], tverdyata: ['idle', 'walk'],
  mal: ['idle', 'walk', 'run'], villager_m: ['idle', 'walk', 'run'], villager_f: ['idle', 'walk', 'run'], villager_old: ['idle', 'walk', 'run'] };
SINGLE.push('dummy_idle_se', 'dummy_hit_se');
// v2 chars b3 (INTEGRATION_v2_chars_b3.md): анчутка, поджигатель, Огнея — те же слаги и анимации, 8 видов без зеркал
const ENEMIES3 = { anchutka: ['idle', 'walk', 'coal_throw', 'hurt', 'death'], arsonist: ['idle', 'walk', 'axe_strike', 'torch_throw', 'hurt', 'death'], mara: ['idle', 'walk', 'cast', 'heal', 'hurt', 'death'],
  // v2 chars b4: Кривша — 15 анимаций (обычная фаза 8, огненная fire_* 7), кадр по содержимому, pivot из JSON
  krivsha: ['idle', 'walk', 'claw', 'summon', 'leap', 'emerge', 'hurt', 'death', 'fire_idle', 'fire_walk', 'fire_claw', 'fire_summon', 'fire_emerge', 'fire_hurt', 'fire_death'] };
export const V2 = { sheets: {}, failed: [], ready: false, counters: {} };

// v2: листов ~1000 файлов — грузим не больше LOAD_PAR одновременно (иначе ERR_INSUFFICIENT_RESOURCES / отказ однопоточного сервера)
const LOAD_PAR = 12; let active = 0; const waitQ = [];
function load(name) {
  return new Promise((res) => { const go = () => { active++; load1(name).finally(() => { active--; res(); const n = waitQ.shift(); if (n) n(); }); }; if (active < LOAD_PAR) go(); else waitQ.push(go); });
}
function load1(name) {
  return Promise.all([
    fetch(DIR + name + '.json').then((r) => (r.ok ? r.json() : null)),
    new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = DIR + name + '.png'; }),
  ]).then(([meta, img]) => { if (meta && meta.frames && !meta.frame_count) meta.frame_count = meta.frames;   // v2: в JSON «frames» вместо frame_count
    if (img && meta) V2.sheets[name] = { meta, img }; else V2.failed.push(name); })
    .catch(() => { V2.failed.push(name); });
}
export function loadV2Art() {
  const jobs = SINGLE.map(load);
  for (const [slug, anims] of Object.entries(CHARS)) for (const a of anims) for (const d of V2_DIRS) jobs.push(load(`${slug}_${a}_${d}`));
  for (const [slug, anims] of Object.entries(ENEMIES3)) for (const a of anims) for (const d of V2_DIRS) jobs.push(load(`${slug}_${a}_${d}`));
  for (const [slug, anims] of Object.entries(NPCS)) for (const a of anims) for (const d of V2_DIRS) jobs.push(load(`npc_${slug}_${a}_${d}`));
  return Promise.all(jobs).then(() => { V2.ready = true; V2.counters.comboSheets = Object.keys(V2.sheets).filter((n) => /^hero_attack[23]_/.test(n)).sort(); if (V2.failed.length) console.info('v2art: missing sheets', V2.failed.join(', ')); });
}
export const v2 = (name) => V2.sheets[name] || null;
export const v2View = (dir) => V2_DIRS[((dir | 0) % 8 + 8) % 8];
const nFrames = (m) => m.frames || m.frame_count || 1;
const fsz = (m) => m.frame_size || m.size;

/** Кадр листа v2 по pivot в (x, y). o.flip — зеркало по x, o.alpha, o.flash — светлый силуэт поверх (вспышка попадания). */
export function v2Blit(ctx, sh, frame, x, y, o = {}) {
  const m = sh.meta, [fw, fh] = fsz(m), [px, py] = m.pivot, n = nFrames(m), fr = ((frame | 0) % n + n) % n;
  ctx.save();
  if (o.alpha != null) ctx.globalAlpha *= Math.max(0, o.alpha);
  ctx.translate(Math.round(x), Math.round(y)); if (o.flip) ctx.scale(-1, 1);
  ctx.drawImage(sh.img, fr * fw, 0, fw, fh, -px, -py, fw, fh);
  if (o.flash) { ctx.globalAlpha *= o.flashA || 0.28; ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(sh.img, fr * fw, 0, fw, fh, -px, -py, fw, fh); }
  ctx.restore();
}
const tintCache = new Map();
/** Силуэт кадра одним цветом (обводка под курсором / элита) — 4 сдвига на 1 px, рисуется до кадра. */
export function v2Outline(ctx, sh, frame, x, y, c) {
  const m = sh.meta, [fw, fh] = fsz(m), [px, py] = m.pivot, fr = (frame | 0) % nFrames(m), key = m.image + fr + c;
  let cv = tintCache.get(key);
  if (!cv) {
    cv = document.createElement('canvas'); cv.width = fw; cv.height = fh;
    const g = cv.getContext('2d'); g.drawImage(sh.img, fr * fw, 0, fw, fh, 0, 0, fw, fh);
    g.globalCompositeOperation = 'source-in'; g.fillStyle = c; g.fillRect(0, 0, fw, fh);
    tintCache.set(key, cv);
  }
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) ctx.drawImage(cv, Math.round(x) - px + dx, Math.round(y) - py + dy);
}
/** Только «угольки» глаз упыря (fire3) — поверх тинта матёрого / замедления. */
export function v2Eyes(ctx, sh, frame, x, y) {
  const m = sh.meta, [fw, fh] = fsz(m), [px, py] = m.pivot, fr = (frame | 0) % nFrames(m), key = m.image + fr + '_eyes';
  let cv = tintCache.get(key);
  if (!cv) {
    cv = document.createElement('canvas'); cv.width = fw; cv.height = fh;
    const g = cv.getContext('2d', { willReadFrequently: true }); g.drawImage(sh.img, fr * fw, 0, fw, fh, 0, 0, fw, fh);
    const id = g.getImageData(0, 0, fw, fh), d = id.data;
    for (let i = 0; i < d.length; i += 4) if (d[i + 3] < 200 || d[i] < 200 || d[i + 1] < 120 || d[i + 2] > 140) d[i + 3] = 0;
    g.putImageData(id, 0, 0); tintCache.set(key, cv);
  }
  ctx.drawImage(cv, Math.round(x) - px, Math.round(y) - py);
}

// --- позы. Игровые тайминги не трогаем: кадр удара листа ставится ровно на момент удара (hitAt), до него кадры растянуты.
const loopF = (t, fps, n) => Math.floor(t * fps) % n;
/** Кадр атаки: кадры 0..hit−1 растянуты на [0, hitAt), hit и дальше — @fps листа от hitAt. */
export function attackFrame(t, hitAt, sh, dur = null) {
  const m = sh.meta, n = nFrames(m), hit = (m.events && m.events.hit) ?? Math.floor(n / 2);
  // v2art4: кадры после удара должны уложиться в оставшееся время удара (dur − hitAt) — иначе fps поднимается (длительность удара не меняется)
  const fps = dur != null && dur > hitAt ? Math.max(m.fps || 12, (n - hit) / (dur - hitAt)) : (m.fps || 12);
  if (t < hitAt - 1e-9) return Math.min(hit - 1, Math.floor((t / Math.max(1e-6, hitAt)) * hit + 1e-6));
  return Math.min(n - 1, hit + Math.floor((t - hitAt) * fps + 1e-6));
}
/** Комбо из 3 ударов (v2art4): удар N берёт лист hero_attack{N}_<вид> (N = 2, 3; удар 1 — hero_attack_<вид>) в формате
 *  hero_attack: кадр events.hit листа ставится ровно на hitAt. Пока листов 2 и 3 нет — временные заглушки из hero_attack:
 *  удар 2 — кадры в обратном порядке (кадр удара — зеркальный индекс), удар 3 — зеркало по x. Листы перечислены в манифесте CHARS (hero: attack2, attack3); новые файлы с теми же именами подхватываются без правок кода. */
export function heroAttackPose(a, view) {
  const step = a.combo || 1, hitAt = a.hitAt ?? a.dur * 0.5;
  if (step > 1) { const own = v2('hero_attack' + step + '_' + view); if (own) return { name: 'hero_attack' + step + '_' + view, sheet: own, frame: attackFrame(a.t, hitAt, own, a.dur), bob: 0, step }; }
  const sh = v2('hero_attack_' + view);
  if (!sh) return null;
  if (step === 2) {
    const m = sh.meta, n = nFrames(m), hit = (m.events && m.events.hit) ?? Math.floor(n / 2);
    const f = attackFrame(a.t, hitAt, { meta: { ...m, events: { ...(m.events || {}), hit: n - 1 - hit } } });
    return { name: 'hero_attack2_' + view + '~rev', sheet: sh, frame: n - 1 - f, bob: 0, step };
  }
  if (step === 3) return { name: 'hero_attack3_' + view + '~flip', sheet: sh, frame: attackFrame(a.t, hitAt, sh), bob: 0, flip: true, step };
  return { name: 'hero_attack_' + view, sheet: sh, frame: attackFrame(a.t, hitAt, sh), bob: 0, step };
}
/** Поза героя v2: { sheet, frame, bob } или null (листа нет). Ходьбы в v2 нет — idle @8 с покачиванием на 1 px. */
export function poseHeroV2(h, time, dir = h.dir) {
  const view = v2View(dir), a = h.action;
  if (h.dead) { const sh = v2('hero_death_' + view); if (!sh) return null; const n = nFrames(sh.meta); return { name: 'hero_death_' + view, sheet: sh, frame: Math.min(n - 1, Math.floor(Math.max(0, time - (h.deathAt ?? time)) * (sh.meta.fps || 10) + 1e-6)), bob: 0 }; }
  if (a && a.type === 'attack') { const P = heroAttackPose(a, view); if (P) return P; }
  const sh = v2('hero_idle_' + view);
  if (!sh) return null;
  if (a && a.type === 'cast') { const at = v2('hero_attack_' + view); if (at) return { name: 'hero_attack_' + view, sheet: at, frame: Math.min(1, Math.floor(a.t * 10)), bob: 0 }; }
  if (h.moving) {
    const w = v2('hero_walk_' + view);   // v2b2: ходьба 8 кадров @10 (шаги — кадры 0 и 4)
    if (w) return { name: 'hero_walk_' + view, sheet: w, frame: loopF(time, w.meta.fps || 10, nFrames(w.meta)), bob: 0 };
    return { name: 'hero_idle_' + view, sheet: sh, frame: loopF(time, 8, nFrames(sh.meta)), bob: Math.round(Math.abs(Math.sin(h.walkPhase * 1.8))) };
  }
  return { name: 'hero_idle_' + view, sheet: sh, frame: loopF(time, sh.meta.fps || 4, nFrames(sh.meta)), bob: 0 };
}
/** Поза упыря v2 (batch2): тайминги — прежние (boss_art.poseUpyr: смерть 8 @10, подъём 6 за riseTime, «ранен» 2 @8, шаг 8 @10 / 13
 *  у «Прыткого»), кадр — из листа v2 того же вида; удар — кадр events.hit ровно на hitAt. null — листа нет (прежний лист). */
export function poseUpyrV2(e, time, dir = e.dir) {
  const P = poseUpyr(e, time), view = v2View(dir), name = P.anim + '_' + view, sh = v2(name);
  if (!sh) return null;
  const n = nFrames(sh.meta);
  let frame = Math.min(n - 1, P.frame);
  if (P.anim === 'upyr_attack') frame = attackFrame(e.t, e.hitAt != null ? e.hitAt : 0.6, sh);
  else if (P.anim === 'upyr_idle') frame = loopF(time + e.id * 0.09, sh.meta.fps || 4, n);
  return { name, sheet: sh, frame, bob: 0 };
}

/** Лист NPC v2: роль данных → слаг файлов (Милуша — id vedana → milusha; id и термины не меняются). */
export function npcSlug(n) {
  if (n.kind === 'mal' || n.role === 'mal') return 'mal';
  if (n.kind === 'villager') return n.old ? 'villager_old' : n.female ? 'villager_f' : 'villager_m';
  return { vyshata: 'vyshata', priest: 'priest', vedana: 'milusha', tverdyata: 'tverdyata' }[n.role] || null;
}
/** Поза NPC v2: idle / walk / run (бег — при скорости > runSpeed ≈ 1,3 тайла/с, если лист есть); null — листа нет (прежняя фигура). */
export function poseNpcV2(n, time, dir = n.dir) {
  const slug = npcSlug(n); if (!slug) return null;
  const view = v2View(dir), ph = time + ((n.x * 7 + n.y * 3) % 1);
  let anim = 'idle';
  if (n.moving) anim = (n.speed || 0) > 1.3 && v2(`npc_${slug}_run_${view}`) ? 'run' : 'walk';
  const name = `npc_${slug}_${anim}_${view}`, sh = v2(name);
  if (!sh) return null;
  return { name, sheet: sh, frame: loopF(ph, sh.meta.fps || 4, nFrames(sh.meta)) };
}
/** Соломенник v2: idle (1 кадр) / hit 4 @12 после удара (hitAt), один вид se. */
export function poseDummyV2(d, time) {
  const hs = v2('dummy_hit_se'), dt = d.hitAt != null ? time - d.hitAt : 1e9;
  if (hs && dt >= 0 && dt < nFrames(hs.meta) / (hs.meta.fps || 12)) return { name: 'dummy_hit_se', sheet: hs, frame: Math.floor(dt * (hs.meta.fps || 12) + 1e-6) };
  const sh = v2('dummy_idle_se'); return sh ? { name: 'dummy_idle_se', sheet: sh, frame: 0 } : null;
}

const once = (t, fps, n) => Math.min(n - 1, Math.max(0, Math.floor(t * fps + 1e-6)));
/** Поза поджигателя v2 (b3): «Поджог» — кадр выпуска 3 ровно на torch.windup (кадры 0–2 растянуты), удар топором — hit_frame 3
 *  на hitAt; ранен 2 @8; шаг 8 @10; idle 4 @5; гибель 8 @10 (последний кадр держится). null — листа нет (прежний грей-бокс). */
export function poseArsonistV2(e, time, dir = e.dir) {
  const view = v2View(dir), def = e.def || {}, tc = def.torch || {};
  let anim = 'idle', frame = 0;
  if (e.dead) { anim = 'death'; frame = once(e.corpseT || 0, 10, 8); }
  else if (e.state === 'torch') { const w = tc.windup ?? 0.5; anim = 'torch_throw'; frame = e.t < w ? Math.min(2, Math.floor(e.t / w * 3 + 1e-6)) : Math.min(4, 3 + Math.floor((e.t - w) * 10 + 1e-6)); }
  else if (e.state === 'attack' && !e.moving) { const h = e.hitAt != null ? e.hitAt : 0.5; anim = 'axe_strike'; frame = e.t < h ? Math.min(2, Math.floor(e.t / h * 3 + 1e-6)) : Math.min(5, 3 + Math.floor((e.t - h) * 12 + 1e-6)); }
  else if (e.lastHitT < 0.25 && !e.moving) { anim = 'hurt'; frame = once(e.lastHitT, 8, 2); }
  else if (e.moving) { anim = 'walk'; frame = loopF(time + (e.id || 0) * 0.13, 10, 8); }
  else frame = loopF(time + (e.id || 0) * 0.13, 5, 4);
  const name = 'arsonist_' + anim + '_' + view, sh = v2(name);
  return sh ? { name, sheet: sh, frame: Math.min(nFrames(sh.meta) - 1, frame), bob: 0 } : null;
}
/** Точка вылета снаряда из листа b3 (anchors_px[key] по кадрам: уголь анчутки, факел поджигателя, сгусток Огнеи) — последний
 *  кадр перед выпуском; [dx, высота] в пикселях экрана от pivot; null — листа нет. */
export function launchPt(e, anim, key, dir = e.dir) {
  const sh = v2(anim + '_' + v2View(dir)); if (!sh) return null;
  const A = ((sh.meta.anchors_px || {})[key]) || [], [px, py] = sh.meta.pivot;
  for (let i = A.length - 1; i >= 0; i--) if (A[i]) return { dx: A[i][0] - px, z: py - A[i][1], frame: i, sheet: anim + '_' + v2View(dir) };
  return null;
}

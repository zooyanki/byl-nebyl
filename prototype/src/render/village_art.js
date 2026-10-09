// Арт деревни художника (art/sprites/INTEGRATION_m1_village.md, v1.13.2): постройки Ладоги, ворота, указатель, дым,
// UI окна диалога, портреты, стрелка/маркер навигации, значки мини-карты. Копии — assets/bld/ и assets/ui/.
// Постройка ставится точкой proto_corner_px листа на toS(x0, y0); кадр — door_frames[door] (+y → 0, +x → 1).
// Сортировка — как map.js addProp: центр футпринта x0 + A/2 + y0 + B/2; сегменты ворот — как клетка тына x + y + 1.
const BLD = [
  'bld_church', 'bld_izba_small_dern', 'bld_izba_small_tes_kon', 'bld_izba_small_tes_prich', 'bld_izba_seni_tes', 'bld_izba_seni_dern',
  'bld_izba_podklet', 'bld_klet', 'bld_banya_dern', 'bld_banya_tes', 'bld_ambar', 'bld_ambar_pier_tes', 'bld_ambar_pier_dern', 'bld_hlev',
  'bld_masterskaya', 'bld_lavka', 'bld_ukazatel',
  'gate_e_open_A', 'gate_e_open_B', 'gate_s_open_A', 'gate_s_open_B', 'gate_n_open_A', 'gate_n_open_B', 'gate_w_open_A', 'gate_w_open_B',
  'gate_n_closed_A', 'gate_n_closed_B', 'gate_w_closed_A', 'gate_w_closed_B',
];
const UI = [
  'ui_dlg_frame', 'ui_dlg_frame_400x88', 'ui_dlg_more', 'ui_dlg_end', 'ui_nav_arrow', 'ui_nav_mark', 'ui_minimap_icons_v113',
  'portrait_ratibor', 'portrait_vyshata', 'portrait_milusha', 'portrait_tverdyata', 'portrait_mal', 'portrait_priest',
];
export const VA = { sheets: {}, ui: {}, ready: false, failed: [] };

/** Лист «вид + облик» → имя листа художника (§15: kind + variant). */
export const BLD_SHEET = {
  church: 'bld_church', izba: { dern: 'bld_izba_small_dern', tes_kon: 'bld_izba_small_tes_kon', tes_prich: 'bld_izba_small_tes_prich' },
  izba_seni: { tes: 'bld_izba_seni_tes', dern: 'bld_izba_seni_dern' }, izba_podklet: 'bld_izba_podklet', klet: 'bld_klet',
  banya: { dern: 'bld_banya_dern', tes: 'bld_banya_tes' }, ambar: 'bld_ambar', ambar_pier: { tes: 'bld_ambar_pier_tes', dern: 'bld_ambar_pier_dern' },
  hlev: 'bld_hlev', masterskaya: 'bld_masterskaya', lavka: 'bld_lavka', sign: 'bld_ukazatel',
};
export function sheetOf(p) {
  const s = BLD_SHEET[p.type];
  if (!s) return null;
  return typeof s === 'string' ? s : s[p.variant] || null;
}

function load(dir, name, into) {
  return Promise.all([
    fetch(dir + name + '.json').then((r) => r.json()),
    new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = dir + name + '.png'; }),
  ]).then(([meta, img]) => { if (img) into[name] = { meta, img }; else VA.failed.push(name); })
    .catch(() => { VA.failed.push(name); console.warn('asset failed', name); });
}
export function loadVillageArt() {
  return Promise.all([...BLD.map((n) => load('assets/bld/', n, VA.sheets)), ...UI.map((n) => load('assets/ui/', n, VA.ui))])
    .then(() => { VA.ready = true; });
}

/** Кадр постройки по стороне двери (door_frames из JSON листа). */
export function frameOf(meta, door) {
  const df = meta.door_frames;
  return df && typeof df === 'object' ? (df[door] ?? 0) : 0;
}
/** Запечь кадр листа в canvas: { c, ox, oy } в системе props.js (опора — toS(p.x, p.y)). */
export function bakeSheet(sh, frame) {
  const m = sh.meta, [fw, fh] = m.frame_size, c = document.createElement('canvas');
  c.width = fw; c.height = fh;
  c.getContext('2d').drawImage(sh.img, frame * fw, 0, fw, fh, 0, 0, fw, fh);
  return { c, ox: m.proto_corner_px[0], oy: m.proto_corner_px[1] };
}

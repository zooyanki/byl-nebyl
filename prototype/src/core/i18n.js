// Тексты из data/ru.json (сборка tools/export_ru.py из story/act1_texts.md). t('ключ', {n: 5}) подставляет {n}.
// Правила GDD v1.4 §10.1: серебро по числам НЕ склоняется (silverText), счётные слова — plural().
export const RU = {};
export function applyRu(json) { for (const k of Object.keys(RU)) delete RU[k]; Object.assign(RU, json); }

export function t(key, vars = null) {
  let s = RU[key];
  if (s == null) return key;
  if (typeof s === 'object') s = s.desc || s['Текст'] || s.name || key;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? fmtNum(vars[k]) : m));
  return s;
}
/** Объект строки (навыки: {name, branch, chant, desc}). */
export const tObj = (key) => (typeof RU[key] === 'object' ? RU[key] : null);

/** plural(n, 'зелье', 'зелья', 'зелий') или plural(n, 'plural.zelye'): one — n%10==1 && n%100!=11; few — n%10 2–4 и n%100 не 12–14; иначе many. */
export function plural(n, one, few, many) {
  if (few == null && RU[one]) [one, few, many] = RU[one];
  const a = Math.abs(n) % 100, b = a % 10;
  if (b === 1 && a !== 11) return one;
  if (b >= 2 && b <= 4 && (a < 12 || a > 14)) return few;
  return many;
}
/** «5 зелий», «21 очко». */
export const countText = (n, key) => n + ' ' + plural(n, key);

// числа в подписях: дробь через запятую (GDD §10.1 «0,4 с»)
export function fmtNum(v) { return typeof v === 'number' && !Number.isInteger(v) ? String(Math.round(v * 10) / 10).replace('.', ',') : String(v); }

/** Серебро без plural(): where = 'counter' («Серебро: N») | 'lost' («Потеряно серебра: N») | 'ground' («N сер.») | 'pickup' («+N сер.»). */
export function silverText(n, where = 'counter') {
  if (where === 'lost') return t('ui.death.penalty', { n });
  if (where === 'ground') return t('ui.ground.silver', { n });
  if (where === 'pickup') return t('ui.sys.silver_pickup', { n });
  return t('ui.gear.silver', { n });
}

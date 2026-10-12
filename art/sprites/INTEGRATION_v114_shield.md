# GDD v1.14 §12.1.8 — заказ «Щит» (H21–H23), интеграция

Дата: 10.10.2026, МСК. Прототип не менялся (только чтение). Старые PNG не перезаписаны — бэкапы не потребовались.
Сборка: `python3 art/sprites/src/make_v114_shield.py` (проверяет palette_v2 и альфу 0/255 у всех 27 PNG).

## H21 — блок Ратибора (P0)
Папка `art/sprites/hero/`. Кадр 64×64, pivot (32,56), рост 44 (поза покоя всех видов = 44; в движении 43–45, на «пробит» 41–46 — откидывание корпуса).
Файлы `hero_block_<anim>_<view>.png` + `.json` (горизонтальная полоса), манифест `hero_block.json`.

| anim  | кадров | fps | loop | события (JSON `events`) |
|-------|-------|-----|------|-------------------------|
| raise | 2 | 13 | нет | после последнего кадра блок активен (`block_active_after_last_frame`), `raised: 1`; опускание = обратный порядок |
| hold  | 2 | 4  | да  | `block_active: [0,1]` |
| walk  | 6 | 8  | да  | `block_active`: все; `footstep: [0,3]`; скорость ×0,5 (§4.7) |
| hit   | 3 | 12 | нет | `block_active: [0,1,2]`, `hit: 0`, `sparks: 0`, `recoil_px: 1` |
| break | 4 | 13 | нет | `block_active: []`, `break: 0`, `sparks: 0`, `shield_down: 3`; 13 fps: 4 кадра ≈ 0,3 с = оглушение §4.7 (решение дизайнера 10.10) |

17 кадров × 5 видов = 85. Виды: s, se, e, ne, n; зеркала: sw←se, w←e, nw←ne (flip по x = 32, pivot тот же).
Направления прототипа (dir 0–7): 0→s, 7→se, 6→e, 5→ne, 4→n, 1→se+flip, 2→e+flip, 3→ne+flip.
Якоря (`anchors`, по кадрам, px кадра): `shield_center`, `shield_rim` — точка контакта (верх-право кромки); для зеркала x → 63 − x.
Виды ne/n (правка 10.10, P1): щит закрыт корпусом, поэтому сбоку (сторона левой руки, экранно слева; в зеркале nw — справа) выведен край щита —
дуга 2 px (бронзовая кромка + дерево изнанки) + контур, блик bronze_hi/bronze_lt сверху. Есть во всех кадрах (raise, hold, walk, hit; в break следует за щитом).
В ne/n `shield_rim` = верх этой кромки (сдвинулся по сравнению с первой сдачей); `shield_center` — логический центр щита (за корпусом).
Щит: тот же рисунок `sprites_rus._shield` (8 секторов красный/береста, бронзовая кромка, умбон) — не перерисован.
Превью: `hero/preview/hero_block_all_x3.png`, `hero_block_all.gif`, по анимациям `hero_block_<anim>_x3.png/.gif`.

Подключение (Петр): `boss_art.js` грузит `<slug>_<anim>_<view>`; добавить в `SETS` `hero: ['block_raise','block_hold','block_walk','block_hit','block_break']`
(или читать `hero_block.json`) и расширить `viewOf` для героя на 5 видов по таблице выше (сейчас только se/ne у монстров).
Остальные анимации героя пока рисуются кодом (`sprites.js drawHero`) — переход между кодом и листом блока будет заметен: см. вопросы.

## H22 — иконка `ic_block` (P0)
`art/ui/hud/ic_block.png` (полоса 32×16: кадр 0 normal, кадр 1 broken) + `ic_block.json`. Непрозрачная, фон как у иконок навыков v2.
В слот 18×18 (509;342) рисовать в (510;343). Состояния hud.js: ready/raised → кадр 0 (raised + текущая обводка bronze_hi),
broken → кадр 1 + текущий `cooldownSector`.
**Состояние `none` (решение дизайнера 10.10): отдельного кадра нет — кадр 0, затемнённый так же, как недоступные навыки (`rect slate_dk`, globalAlpha 0.6, как в `skillIcon` hud.js).**
Подключение: либо в `UI_ATLAS` через `tools/export_ui.py` (ключ `ic_block`/`ic_block_broken`), либо отдельным PNG в `assets/ui/`; заменить `shieldIcon()` (hud.js:569).
Макет: `art/ui/hud/preview/mockup_hud_ic_block_{normal,broken}_native.png` / `_1920x1080.png`, крупно `mockup_hud_ic_block_slot_x4.png`
(основа — реальный кадр прототипа, только иконка вставлена поверх). Превью иконки `ic_block_x3.png`, `ic_block_x8.png`.

## H23 — искры блока `fx_block_sparks` (P1)
`art/sprites/fx_block_sparks/fx_block_sparks.png/.json`: 16×16, 3 кадра, 20 fps, без цикла; bronze_hi → bronze → bronze_dk (гаснет).
pivot (4,8) = точка удара; веер вправо. Враг слева от щита (экранно) → зеркалить, pivot (11,8). Ставить в `anchors.shield_rim` героя на событии `hit`/`break`
(на break — две пачки: обычная и зеркальная). Числа частиц из §4.7 (6/10) можно оставить кодом поверх, спрайт — «вспышка контакта».
Превью `fx_block_sparks/preview/fx_block_sparks_x3.png/.gif`.

## Ревью-сцена
`art/sprites/hero/review/`: `review_hero_block_vs_upyr.gif` (×3), `_native.png`, `_x3.png` (контакт-лист), `review_block_key_x3.png` (момент удара),
`review_hero_guard_break_vs_upyr.*` (пробитие). Герой se, упырь attack ne→зеркало nw, искры по `shield_rim`.
Виды сзади: `review_hero_block_back_ne_vs_upyr.*`, `review_hero_block_back_n_vs_upyr.*` (упырь впереди, искры от выведенной кромки — веер влево, зеркало).

## H24 — устье тропы (P2): не сделано (по времени), см. отчёт.
## Мелкие правки плана (a) Иоанн, (b) seni_sw, (c) дымовые якоря — не трогались, состояние прежнее (v1.13.2).

## Правка 10.10 (14:26 МСК)
ne/n — выведенная кромка щита; break 13 fps; `none` = затемнённый кадр 0. Бэкап прежней версии: `hero/_backup_v114_rim_1426/`.

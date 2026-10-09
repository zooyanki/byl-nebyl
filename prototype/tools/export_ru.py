"""Сборка data/ru.json из текстов сценариста (только чтение /workspace/game/story/act1_texts.md).
Запуск из папки prototype:  python3 tools/export_ru.py
Берутся все строки таблиц, где первая ячейка — `ключ`. Двухколоночные — строка; многоколоночные — объект
по заголовкам таблицы. Особые случаи: plural.* → [one, few, many]; skill.* → {name, branch, chant, desc}.
По GDD v1.4 §12.2.1: 15 лишних ключей ui.* вырезаются, ui.obj.rift добавляется, окна — «Витязь»/«Котомка»,
«к защите» в P04/P05, правки tip.09 и ui.death.penalty_none; ключи навыков skill.ved.* сопоставлены с id из skills.json."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "story", "act1_texts.md")
OUT = os.path.join(HERE, "..", "data", "ru.json")

SKIP = {"ui.hud.silver", "ui.hud.points", "ui.gear.bag", "ui.pause.resume", "ui.pause.settings", "ui.error.req_level",
        "ui.sys.yar1", "ui.sys.quest_updated", "ui.settings.damage_numbers", "ui.settings.item_labels", "ui.error.no_path",
        "ui.error.cooldown", "ui.error.no_stone", "ui.trade.respec_used", "ui.tip.shift_click"}
OVERRIDE = {   # GDD v1.4 §12.2.1
    "ui.obj.rift": "Вонзить меч (держи ЛКМ)",
    "ui.hud.btn.hero": "Витязь (C)", "ui.hero.title": "Витязь",
    "ui.hud.btn.gear": "Котомка (I)", "ui.gear.title": "Котомка",
    "ui.tut.bag": "I — котомка. Перетащи оружие в десницу.",
    "tip.09": "Серебро в ладье-сундуке не пропадёт. Падёшь — потеряешь часть серебра из котомки.",
    "ui.death.penalty_none": "Серебра в котомке не было. Терять нечего.",
}
SKILL_IDS = {"skill.ratnoe.sshibka": "sshibka", "skill.ratnoe.chur": "chur", "skill.ratnoe.stat": "stat", "skill.ratnoe.secha": "secha",
             "skill.ved.zmey": "zmey", "skill.ved.morozko": "morozko", "skill.ved.veshchee": "veshchee", "skill.ved.skok": "skok",
             "skill.dash": "dash", "skill.yar1": "yar1"}

# act1.md v1.1 (дословно; читаются из файла и сверяются ниже): название и цели М1 для трекера, брифинг, диалог Мала,
# «Грамота жреца». Шапка трекера «Задание · Акт I» — с макета HUD v2 (gameplay_hud_v2.QUEST).
ACT1 = os.path.join(HERE, "..", "..", "story", "act1.md")
M1_GOALS = {"reach": "Доберись до капища", "huts": "Спаси выживших", "hearths": "Отбей огнища у упырей",
            "krivsha": "Одолей Крившу", "arsonist": "Найди поджигателя"}
# Строки прототипа, которых нет у сценариста (заглушки вехи M1a — вопрос сценаристу/геймдизайнеру, см. README).
PROTO = {
    "proto.trail_locked": "Тропу покажет Мал. Он в избе у колодца.",
    "proto.kapishche_soon": "Капище Перуна откроется в следующей вехе.",
    "proto.exit.to": "Путь: {zone}",
    "proto.villager": "Селяне",
    "proto.priest_body": "Тело жреца",
    "proto.quest.arsonist_hint": "Черноярцы с факелами — люди Чернояра.",
    # веха M1b (капище, Мара, Кривша): заглушки прототипа, у сценариста строк нет
    "proto.respawn.krada": "Ратибор очнулся у костра.",
    "proto.respawn.chur": "Ратибор очнулся у путевого камня.",
    "proto.chur_respawn_hint": "Теперь, если падёшь, очнёшься здесь.",
    "proto.krivsha_body": "Тело Кривши",
    "proto.bylina_soon": "Былинные вещи — в следующей вехе.",
    "proto.reward_ladoga": "Награду выдаст Вышата в Ладоге.",
    "proto.idol_perun": "Идол Перуна",
    "proto.hearth": "Огнище",
    # веха M1c (береста возврата, былинные вещи): заглушки прототипа, у сценариста строк нет
    "proto.beresta.use": "ПКМ — прочитать",
    "proto.beresta.reading": "Читаешь бересту…",
    "proto.portal.closed": "Путевой проход закрылся",
    "proto.bylina.got": "Былинная вещь: {item}",
    # веха m1g (GDD v1.11 §8.2): плашка над головой былинного врага — «{name} · {level}», level = ui.hud.level
    "proto.nameplate": "{name} · {level}",
    # веха m1h (rename_map.md §3.3): видимые строки, раньше зашитые в код, — вынесены сюда (текст по таблице, прочие без изменений)
    "proto.zone.title": "{zone} · ур. нечисти {mlvl}",
    "proto.hero.res_full.hp": "Жизнь и так полна",
    "proto.hero.res_full.yar": "Удаль и так полна",
    "proto.belt.empty": "Ячейка {n} пуста",
    "proto.potion.both": "Мгновенно восполняет {pct}% жизни и Удали",
    "proto.potion.over_time": "+{amount} {res} за {dur} с",
    "proto.potion.res.hp": "к жизни",
    "proto.potion.res.yar": "к Удали",
    "proto.skills.lmb_basic": "На ЛКМ · без Удали — обычный удар",
    "proto.hero.attr.ene": "Дух: +2 к Удали, +1% к урону ведовства",
    "proto.help.rmb": "Огненный змей (Удали: {n})",
    "proto.labels.always": "Подписи добычи: всегда",
    "proto.labels.alt": "Подписи добычи: по Alt",
    # веха m1i (critics_m1f П.12–13, 15): столбец цены в торге, справка паузы и переключатели, главное меню — строки, раньше
    # зашитые в код, вынесены сюда без изменения текста; новые — «Пробел · рывок», «Цена», подпись слота без сохранения
    "proto.trade.price": "Цена",
    "proto.pause.sound": "Звук (N)",
    "proto.pause.labels": "Подписи (Z)",
    "proto.pause.minimap": "Мини-карта",
    "proto.toggle.on": "вкл",
    "proto.toggle.off": "выкл",
    "proto.pause.hint": "Пауза — Esc, чтобы продолжить",
    # веха m1j (GDD v1.13 §4.6, §10.5): переключатель «Тряска при ударе» (settings.shake), строка очка навыка на плашке «Награда»
    "proto.reward.skill": "{line} · T — навыки",
    "proto.help.move.key": "ЛКМ / зажать ЛКМ",
    "proto.help.move": "идти; по нечисти — бить",
    "proto.help.stand.key": "Shift + ЛКМ",
    "proto.help.stand": "бить на месте",
    "proto.help.pickup.key": "ЛКМ по подписи",
    "proto.help.pickup": "поднять добычу (серебро — само)",
    "proto.help.rmb.key": "ПКМ",
    "proto.help.dash": "рывок к курсору (Удаль не тратит)",
    "proto.help.belt.key": "1–4",
    "proto.help.belt": "выпить зелье из пояса",
    "proto.help.labels.key": "Alt (держать) / Z",
    "proto.help.labels": "подписи добычи / всегда",
    "proto.help.map.key": "Tab или M",
    "proto.help.map": "большая карта поверх мира",
    "proto.help.windows.key": "I или B / C",
    "proto.help.windows": "котомка / витязь",
    "proto.help.sound.key": "N",
    "proto.help.sound": "звук вкл/выкл",
    "proto.help.esc.key": "Esc",
    "proto.help.esc": "закрыть окна / пауза",
    # m1i follow-up: строки, которые были захардкожены в src/ (тексты дословно прежние)
    "proto.tip.drink": "ПКМ — выпить",
    "proto.tip.unique": "Былинная вещь",
    "proto.tip.aps": "Атак в секунду: {n}",
    "proto.tip.armor": "Броня: {n}",
    "proto.tip.shield_block": "Блок щитом: {n}%",
    "proto.tip.base_crit": "+{n}% к шансу удачного удара",
    "proto.tip.base_nechist": "+{n}% к урону по Нечисти",
    "proto.fx.invuln": "Неуязвим",
    "proto.log.drunk": "Выпито: {item}",
    "proto.fx.block": "Блок",
    "proto.sys.unreachable": "Не дотянуться",
    "proto.fx.xp": "+{n} опыта",
    "proto.fx.squeal": "И-и-и!",
    "proto.fx.level_up": "Новый уровень!",
    "proto.log.hero_fell": "Ратибор пал…",
    "proto.log.repopulated": "Нечисть снова собралась в округе: {n} {word}.",
    "proto.sys.soon": "{what} — в следующей итерации",
    "proto.sys.sound_off": "Звук выключен",
    "proto.sys.sound_on": "Звук включён",
    "proto.sys.lmb_set": "ЛКМ: {skill}",
    "proto.sys.lmb_basic": "обычный удар",
    "proto.sys.rmb_set": "ПКМ: {skill}",
    "proto.small_window": "Окно меньше 640×360 — текст будет нечётким. Увеличьте окно.",
    "proto.hud.silver_label": "Серебро:",
    "proto.hud.lvl": "ур.",
    "proto.hud.lmb": "ЛКМ",
    "proto.hud.rmb": "ПКМ",
    "proto.hud.muted": "Звук выключен (N)",
    "proto.hud.labels_always": "Подписи: всегда (Z)",
    "proto.hud.killed": "Убито {n}/{total}",
    "proto.hud.ctrl_hint": "ЛКМ — идти/бить · ПКМ — навык · F1–F6 — выбрать навык · Пробел — рывок · T — навыки · Alt — подписи · Tab — карта",
    "proto.hud.belt_slot": "{item} ×{n} — клавиша {key}",
    "proto.hud.belt_empty": "Пустая ячейка пояса",
    "proto.hud.skill_empty": "F{n}: пусто — наведи на навык в окне «Навыки» (T) и нажми F{n}",
    "proto.hud.lmb_tip": "Удар оружием — урон {min}–{max}",
    "proto.hud.no_weapon": "(без оружия)",
    "proto.btn.map": "Карта",
    "proto.btn.menu": "Меню",
    "proto.death.penalty_note": "(10% из котомки)",
    "proto.death.keep": "Опыт и снаряжение остаются при тебе.",
    "proto.plural.vrag_upokoen": ["враг упокоен", "врага упокоено", "врагов упокоено"],
    "proto.death.deaths": "Смертей: {n}",
    "proto.death.or_enter": "или Enter",
    "proto.log.def_buff": "{skill}: +{pct}% к защите на {dur} с",
    "proto.target.bylina": "Былинный враг",
    "proto.log.picked": "Подобрано: {item}",
    "proto.log.to_belt": "(пояс)",
    "proto.log.to_bag": "(котомка)",
    "proto.zone.kapishche": "Капище",
    "proto.log.got_kit": "Получено: {item} ×{n}, {silver} сер.",
    "proto.skills.tier_from": "с {n}-го уровня",
    "proto.skills.tier_start": "с начала",
    "proto.skills.soon": "появится позже",
    "proto.skills.passive": "пасс.",
    "proto.skills.hint": "ЛКМ по навыку — на ПКМ · F1–F6 над навыком — в ячейку",
    "proto.skills.not_impl": "Навык появится в следующих итерациях",
    "proto.skills.from_items": "(+{n} с вещей)",
    "proto.log.dropped": "Выброшено: {item}",
    "proto.sys.wrong_slot": "Сюда это не надеть",
    "proto.sys.need_level": "Требуется уровень {n}",
    "proto.log.equipped": "Надето: {item}",
    "proto.log.unequipped": "Снято: {item}",
    "proto.hero.xp": "Опыт",
    "proto.hero.max_level": "Предел уровней",
    "proto.hero.to_level": "До уровня {n}",
    "proto.hero.free_points": "Свободных очков",
    "proto.hero.dmg_lmb": "Урон ЛКМ",
    "proto.hero.dmg_rmb": "Урон ПКМ",
    "proto.hero.hit_chance": "Шанс попасть",
    "proto.hero.hint_points": "Жми [+], чтобы вложить свободные очки",
    "proto.hero.hint_nopoints": "Очки свойств даются за новый уровень (+5)",
    "proto.hero.str_tip": "Сила: +1% к физическому урону",
    "proto.hero.dex_tip1": "Ловкость: +5 к меткости, +0,1% к удачному удару,",
    "proto.hero.dex_tip2": "+1 к защите за каждые 4 очка",
    "proto.hero.vit_tip": "Живучесть: +2 к жизни",
    "proto.tip.equip_from": "Снарядить можно с {n}-го уровня",
    "proto.cmp.dps": "Урон в секунду",
    "proto.cmp.dps_n": "по нечисти",
    "proto.cmp.block": "Блок, %",
    "proto.cmp.rf": "Сопр. огню, %",
    "proto.cmp.rc": "Сопр. холоду, %",
    "proto.cmp.rp": "Сопр. яду, %",
    "proto.cmp.spell": "Сила чар, %",
    "proto.cmp.fire": "Урон огнём",
    "proto.cmp.cold": "Урон холодом",
    "proto.cmp.skl": "Ранги навыков",
    "proto.cmp.pot": "Сила зелий, %",
    "proto.cmp.ls": "Кража жизни, %",
    "proto.cmp.thorns": "Шипы",
    "proto.cmp.mf": "Удача в добыче, %",
    "proto.cmp.speed": "Скорость бега",
    "proto.cmp.each_skill": "Каждый выученный навык: {v}",
    "proto.cmp.slot_free": "Слот «{slot}» свободен",
    "proto.cmp.instead": "Вместо «{item}»:",
    "proto.cmp.vs_equipped": "Против надетого:",
    "proto.cmp.no_change": "без изменений",
}

def act1_strings():
    a = open(ACT1, encoding="utf-8").read()
    m1 = a.split("## Миссия 1. Огонь на капище", 1)[1].split("\n## ", 1)[0]
    out = {"quest.m1.title": "Огонь на капище", "quest.act": "Задание · Акт I"}
    for k, g in M1_GOALS.items():
        assert g in m1, g                       # цель должна быть в act1.md дословно
        out["quest.m1.obj." + k] = g
    out["quest.m1.brief"] = re.search(r"\*\*Брифинг для карты:\*\*\s*\n> (.+)", m1).group(1).strip()
    mal = a.split("### Мал, отрок из Залесья", 1)[1].split("###", 1)[0]
    out["dialog.m1.mal"] = [[clean(w), clean(t)] for w, t in re.findall(r"> \*\*(.+?):\*\* (.+)", mal)][:3]
    pr = re.search(r"\*\*Грамота жреца\*\*.*?\n\s*> «(.+?)»", a, re.S).group(1)
    out["letter.priest"] = {"name": "Грамота жреца", "text": pr}
    od = re.search(r"\*\*\\\*Приказ Чернояра\*\*.*?\n\s*> «(.+?)»", a, re.S).group(1)
    out["letter.order"] = {"name": "Приказ Чернояра", "text": od}
    # v1.11: подцель «Спаси выживших» — строка сценариста из act1.md (заменила временный ключ m1f)
    out["quest.m1.obj.mal"] = re.search(r"\(`quest\.m1\.obj\.mal`\): (.+)", m1).group(1).strip()
    out["npc.mal"] = "Мал"
    out["npc.ratibor"] = "Ратибор"
    return out


def clean(c):
    c = c.strip()
    c = re.sub(r"\*\*(.+?)\*\*", r"\1", c)
    c = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", c)
    return c.replace("`", "").strip()

def cells(line):
    return [c for c in line.strip().strip("|").split("|")]

out, header = {}, None
lines = open(SRC, encoding="utf-8").read().splitlines()
for i, ln in enumerate(lines):
    if not ln.startswith("|"):
        header = None; continue
    if i + 1 < len(lines) and re.match(r"^\|\s*:?-{3,}", lines[i + 1]):
        header = [clean(c) for c in cells(ln)]; continue
    if re.match(r"^\|\s*:?-{3,}", ln):
        continue
    cs = cells(ln)
    m = re.match(r"^\s*`([A-Za-z0-9_.]+)`\s*$", cs[0])   # m1k: ключи с заглавной (ui.settings.navArrow)
    if not m:
        continue
    key, vals = m.group(1), [clean(c) for c in cs[1:]]
    if key in SKIP or not key[0].isalpha() or "." not in key:     # m1j: §5.0 «Говорящие» — id ролей без точки, не строки
        continue
    if header and header[0] == "Ключ реплики" and len(vals) >= 4:      # m1j (v1.3): реплика окна диалога dlg.* — §5
        out[key] = {"dlg": vals[0], "n": int(vals[1]) if vals[1].strip().isdigit() else vals[1], "who": vals[2], "text": re.sub(r"\s*\[ACT1[^\]]*\]", "", vals[3]).strip()}   # m1k: пометка источника [ACT1] — не текст реплики
        continue
    if key.startswith("plural."):
        out[key] = vals[:3]
    elif key.startswith("skill.") and len(vals) >= 4:
        out[key] = {**out.get(key, {}), "id": SKILL_IDS.get(key, key), "name": vals[0], "branch": vals[1], "chant": vals[2], "desc": vals[3]}
    elif key.startswith("skill.") and header and header[-1] == "short":     # §18: короткие имена для ячеек (GDD v1.7 §3.6)
        out.setdefault(key, {})["short"] = vals[-1]
    elif len(vals) == 1:
        out[key] = vals[0]
    else:
        hd = header[1:] if header and len(header) == len(cs) else [str(k) for k in range(len(vals))]
        out[key] = {h: v for h, v in zip(hd, vals)}
# §9: генератор имён вожаков (А — прозвище и род, Б — примета м./ж.); §14: имена былинных вещей (U1…U9)
txt = open(SRC, encoding="utf-8").read()
g9 = txt.split("## 9. Генератор имён вожаков", 1)[1].split("\n## ", 1)[0]
rows = re.findall(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(м\.|ж\.)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", g9, re.M)
assert len(rows) == 20, len(rows)
rule = re.search(r"с шансом (\d+)% Б А", g9)
out["namegen.leader"] = {"a": [[r[1], "f" if r[2] == "ж." else "m"] for r in rows], "b": [[r[3], r[4]] for r in rows],
                         "swapPct": int(rule.group(1)) if rule else 25}
for uid, name in re.findall(r"^\|\s*(U\d)\s*\|\s*«([^»]+)»", txt, re.M):
    out.setdefault("item." + uid.lower() + ".name", name)
# веха M1c: §14 — имена всех девяти былинных вещей и присказки (item.uN.name / item.uN.lore)
g14 = txt.split("## 14. Былинные предметы: присказки", 1)[1].split("\n## ", 1)[0]
rows14 = re.findall(r"^\|\s*(U\d)\s*\|([^|]+)\|([^|]+)\|([^|]+)\|", g14, re.M)
assert len(rows14) == 9, len(rows14)
for uid, name, base, lore in rows14:
    nm = re.sub(r"\s*\(было.*?\)", "", clean(name)).strip().strip("«»")
    out.setdefault("item." + uid.lower() + ".name", nm)
    out["item." + uid.lower() + ".lore"] = clean(lore)
out.update(OVERRIDE)

def npc_dialogs():
    """Диалоги §5 act1_texts и реплики Вышаты из act1.md — дословно, без переписывания."""
    a = open(ACT1, encoding="utf-8").read()
    src = open(SRC, encoding="utf-8").read()
    out = {"npc.vyshata": "Вышата", "npc.vedana": "Милуша", "npc.tverdyata": "Твердята"}
    sec = a.split("### Вышата, посадник Ладоги", 1)[1].split("###", 1)[0]
    out["npc.vyshata.greet"] = re.search(r"Приветствие: «(.+?)»", sec).group(1)
    def quotes(block):
        return [[clean(w), clean(x)] for w, x in re.findall(r"> \*\*(.+?):\*\* (.+)", block)]
    out["npc.vyshata.s0"] = quotes(sec.split("Перед миссией 1:", 1)[1].split("- После", 1)[0])
    out["npc.vyshata.s1"] = quotes(sec.split("После миссии 1:", 1)[1].split("- После", 1)[0])
    s5 = src.split("## 5. Диалоги", 1)[1].split("\n## ", 1)[0]
    parts = re.split(r"\n### ", s5)
    # m1j: сценарист (act1_texts v1.3) добавил подраздел «5.0. Говорящие» — части ищем по заголовку, а не по номеру
    byname = lambda nm: next(p for p in parts if p.split("\n", 1)[0].find(nm) >= 0)
    for part, role in ((byname("Твердята"), "tverdyata"), (byname("Милуша"), "vedana")):
        g = re.search(r"«(.+?)»", part)
        out["npc." + role + ".greet"] = g.group(1)
        reps = re.search(r"Повторяющиеся \*\*\[ACT1\]\*\*: (.+)", part)
        if reps:
            out["npc." + role + ".rep"] = re.findall(r"«(.+?)»", reps.group(1))
        for key, block in re.findall(r"\*\*С\d · `([^`]+)`\*\*\n((?:>.*\n)+)", part):
            out[key] = quotes(block)
        for key, text in re.findall(r"`(npc\.[a-z0-9_.]+)` «(.+?)»", part):
            out[key] = text
    # m1k: короткие реплики окна по всему §5 — «`npc.x.y`: «…»» и «`npc.x.y` «…»» (npc.vyshata.idle_m1, npc.priest.greet, npc.sbyslav.*)
    for key, text in re.findall(r"`(npc\.[a-z0-9_]+\.[a-z0-9_.]+)`:? «(.+?)»", s5):
        out.setdefault(key, text)
    # m1k: §5.0 «Говорящие» — имена в окне (npc.ratibor, npc.sbyslav, …)
    for nk, name in re.findall(r"^\|\s*`[a-z]+`\s*\|\s*`(npc\.[a-z]+)`\s*\|\s*([^|]+?)\s*\|", s5, re.M):
        out.setdefault(nk, name)
    # Мал: приветствие и слухи С1 (в Ладоге со сдачи М1)
    mal = byname("Мал")                     # m1j: по заголовку (v1.3 добавил §5.0)
    mg = re.search(r"«(.+?)»", mal)
    if mg: out["npc.mal.greet"] = mg.group(1)
    mb = re.search(r"`npc\.mal\.s1`\*\*\n((?:>.*\n)+)", mal)
    if mb: out["npc.mal.s1"] = quotes(mb.group(1))
    # m1j: act1_texts v1.3 переводит диалоги на ключи dlg.* (окно диалога, GDD §10.4 — задача D6, не этой партии); пока код
    # читает старые массивы, недостающие старые ключи диалогов берутся из прежнего data/ru.json (тексты не меняются)
    try: prev = json.load(open(OUT, encoding="utf-8"))
    except Exception: prev = {}
    for k in ("npc.vyshata.s0", "npc.vyshata.s1", "npc.tverdyata.s0", "npc.tverdyata.s1", "npc.vedana.s0", "npc.vedana.s1", "npc.mal.s1", "npc.mal.greet", "dialog.m1.mal"):
        if not out.get(k) and prev.get(k):
            out[k] = prev[k]; print("  [m1j] старый ключ диалога из прежнего ru.json:", k)
    return out

import sys
PROTO_ONLY = "--proto-only" in sys.argv
if PROTO_ONLY:
    # m1j: act1_texts.md сейчас в работе у сценариста (v1.3: dlg.*, death.<место>.N — задачи D6/D14, не этой партии); полная
    # пересборка сняла бы death.line1–5 и старые массивы диалогов, которые ещё читает код. Режим --proto-only берёт текущий
    # data/ru.json как есть (тексты сценариста не трогает) и обновляет только словарь PROTO.
    prev = json.load(open(OUT, encoding="utf-8")); about = prev.pop("_about", "")
    out = prev
    out.update(PROTO)
    json.dump({"_about": about, **dict(sorted(out.items()))}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "ключей →", os.path.relpath(OUT), "(--proto-only)")
    sys.exit(0)
out.update(act1_strings())
out.update(npc_dialogs())
out.update(PROTO)
for k in SKIP:
    out.pop(k, None)
# m1k (D6, GDD v1.13.1): старые массивы диалогов npc.*.s0–s3 / npc.*.rep и dialog.m1.mal устарели — окно диалога читает только
# dlg.* (data/dialogues.json); код их больше не читает, в ru.json не выгружаем
OBSOLETE = re.compile(r"^(npc\.[a-z]+\.(s[0-3]|rep)|dialog\.m1\.mal)$")
for k in [k for k in out if OBSOLETE.match(k)]:
    out.pop(k)
# m1j (v1.3): ключи, которых в act1_texts больше нет (death.line1–5 → death.<место>.N, npc.*.s2/s3/rep → dlg.*), код ещё читает —
# сценарист разрешил держать их в ru.json до перехода на dialogues.json (§5, D6/D14). Переносим из прежнего ru.json как есть.
try: prev_all = json.load(open(OUT, encoding="utf-8"))
except Exception: prev_all = {}
legacy = sorted(k for k in prev_all if k != "_about" and k not in out and not k.startswith("proto.") and not OBSOLETE.match(k))
for k in legacy:
    out[k] = prev_all[k]
if legacy: print("  [m1j] устаревшие ключи сохранены из прежнего ru.json:", len(legacy))
doc = {"_about": "Тексты интерфейса и игры (источник — story/act1_texts.md v1.3, сборка tools/export_ru.py; правки GDD v1.4 §12.2.1). "
                 "Ключи quest.*, dialog.*, letter.*, npc.* — из act1.md v1.1 дословно; proto.* — заглушки прототипа (нет у сценариста). "
                 "Серебро по числам не склоняется («Серебро: N», «Потеряно серебра: N», «N сер.»), счётные слова — plural(n, one, few, many) (§10.1).",
       **dict(sorted(out.items()))}
json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "ключей →", os.path.relpath(OUT))

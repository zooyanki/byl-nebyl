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
    m = re.match(r"^\s*`([a-z0-9_.]+)`\s*$", cs[0])
    if not m:
        continue
    key, vals = m.group(1), [clean(c) for c in cs[1:]]
    if key in SKIP or not key[0].isalpha():
        continue
    if key.startswith("plural."):
        out[key] = vals[:3]
    elif key.startswith("skill.") and len(vals) >= 4:
        out[key] = {"id": SKILL_IDS.get(key, key), "name": vals[0], "branch": vals[1], "chant": vals[2], "desc": vals[3]}
    elif len(vals) == 1:
        out[key] = vals[0]
    else:
        hd = header[1:] if header and len(header) == len(cs) else [str(k) for k in range(len(vals))]
        out[key] = {h: v for h, v in zip(hd, vals)}
out.update(OVERRIDE)
for k in SKIP:
    out.pop(k, None)
doc = {"_about": "Тексты интерфейса и игры (источник — story/act1_texts.md v1.0, сборка tools/export_ru.py; правки GDD v1.4 §12.2.1). "
                 "Серебро по числам не склоняется («Серебро: N», «Потеряно серебра: N», «N сер.»), счётные слова — plural(n, one, few, many) (§10.1).",
       **dict(sorted(out.items()))}
json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "ключей →", os.path.relpath(OUT))

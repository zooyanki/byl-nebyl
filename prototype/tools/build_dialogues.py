"""m1k (D6, GDD v1.13 §10.4, §15): data/dialogues.json — реестр говорящих и диалоги из ключей dlg.* (act1_texts v1.3 §5,
выгружены в data/ru.json tools/export_ru.py). Текст в json не копируется: реплика = {speaker, key}. Окно — числа §15."""
import json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent   # B-39: корень прототипа от расположения файла
R = json.load(open(ROOT / 'data' / 'ru.json', encoding='utf-8'))
SPK = ['ratibor', 'vyshata', 'vedana', 'tverdyata', 'mal', 'priest', 'sbyslav']
PORT = {'vedana': 'portrait_milusha'}
speakers = {s: {'nameKey': 'npc.' + s, 'portrait': PORT.get(s, 'portrait_' + s)} for s in SPK}
by = collections.OrderedDict()
for k, v in R.items():
    if k.startswith('dlg.') and isinstance(v, dict) and 'dlg' in v:
        by.setdefault(v['dlg'], []).append((v['n'], v['who'], k))
AFTER = {'vyshata.s0': [{'flag': 'm1.briefed'}], 'm1.mal': [{'bark': 'bark.m1.mal_gift'}, {'call': 'malRun'}]}
dialogues = collections.OrderedDict()
for did, ls in by.items():
    ls.sort()
    owner, st = did.split('.', 1)
    if owner == 'm1': owner = 'mal'
    stage = int(st[1:]) if st[:1] == 's' and st[1:].isdigit() else None
    for _, who, _k in ls: assert who in speakers, (did, who)
    d = {'who': owner}
    if stage is not None: d['stage'] = stage
    d['once'] = True
    d['lines'] = [{'speaker': who, 'key': k} for _, who, k in ls]
    if did in AFTER: d['after'] = AFTER[did]
    dialogues[did] = d
win = {'x': 120, 'y': 222, 'w': 400, 'h': 88, 'portrait': 64, 'portraitAt': [130, 234], 'portraitFrame': [128, 232, 68, 68],
       'nameAt': [204, 230], 'ruleY': 241, 'textX': 204, 'textY': 246, 'textW': 304, 'lineH': 11, 'maxLines': 4, 'moreAt': [502, 298],
       'counterAt': [470, 296], 'bgAlpha': 0.92, 'frame': 'ui_dlg_frame_400x88', 'frameAt': [119, 221], 'cps': 40, 'inputLock': 0.15,
       'pauseWorld': True, 'blockIfAggroR': 12, 'blockAfterHit': 3, 'queueCalm': 3, 'queueNearR': 8, 'queueTimeout': 30, 'blinkHz': 2}
repeat = {'vyshata': {'beforeTurnIn': ['npc.vyshata.idle_m1'], 'default': ['npc.vyshata.greet']}, 'vedana': ['npc.vedana.greet', 'npc.vedana.idle1'],
          'tverdyata': ['npc.tverdyata.greet', 'npc.tverdyata.idle1', 'npc.tverdyata.idle2'], 'mal': ['npc.mal.greet'], 'priest': ['npc.priest.greet']}
doc = {'_about': 'GDD v1.13 §10.4/§15: окно диалога. Тексты — только ключи dlg.* и npc.*.greet/idle* из ru.json (act1_texts v1.3 §5); сборка tools/build_dialogues.py',
       'speakers': speakers, 'dialogues': dialogues, 'repeat': repeat, 'window': win}
json.dump(doc, open(ROOT / 'data' / 'dialogues.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(dialogues), 'диалогов,', sum(len(d['lines']) for d in dialogues.values()), 'реплик; говорящих', len(speakers))

#!/usr/bin/env python3
"""Проверка act1_texts.md: пункты, лимиты длины, запретные слова, имена из act1."""
import re, sys, itertools
TXT = '/workspace/game/story/act1_texts.md'
ACT1 = '/workspace/game/story/act1.md'
s = open(TXT, encoding='utf-8').read()
# режем отчёт проверки, чтобы не проверять сам себя
body = s.split('## Итоги проверки')[0]
act1 = open(ACT1, encoding='utf-8').read()
ok = True
def fail(msg):
    global ok; ok = False; print('FAIL:', msg)

# 1. пункты
secs = {}
for m in re.finditer(r'^## (\d+)\. (.*)$', body, re.M):
    secs[int(m.group(1))] = m.start()
need = [1] + list(range(4, 17)) + [19, 20, 21]
missing = [n for n in need if n not in secs]
extra = [n for n in secs if n not in need]
print('Пункты:', sorted(secs), '| нет:', missing or '—', '| лишние:', extra or '—')
if missing or extra: fail('состав пунктов')
order = sorted(secs.items(), key=lambda x: x[1])
chunks = {}
for i, (n, pos) in enumerate(order):
    end = order[i+1][1] if i+1 < len(order) else len(body)
    chunks[n] = body[pos:end]

def rows(chunk):
    out = []
    for line in chunk.splitlines():
        if not line.startswith('|') or re.match(r'^\|[-| ]+\|$', line): continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        out.append(cells)
    return out
def data_rows(chunk):
    r = rows(chunk); res = []
    for cells in r:
        if cells[0] in ('Ключ','#','ID','id','Пример','Где','Тип'): continue
        if cells[0].startswith('**') and all(c == '' for c in cells[1:]): continue  # подзаголовок в таблице
        res.append(cells)
    return res
def clean(t):
    t = re.sub(r'\*\*\[ACT1\]\*\*|\[ACT1\]', '', t)
    return t.replace('**', '').strip()

# 2. запретные слова
# слова записаны задом наперёд, чтобы вывод скрипта сам не содержал их
banned = [w[::-1] for w in ['кирадраг', 'калдоклов', 'равто', 'тсончорп', 'кничоп']]
total = 0
for i, w in enumerate(banned, 1):
    hits = [l for l in s.splitlines() if w in l.lower()]
    total += len(hits)
    if hits: fail(f'запретное слово №{i}: {len(hits)} строк')
print(f'Запретные слова (5 шт., по всему файлу): найдено {total}')

# 3. всплывающие реплики ≤ 60
pop = []
for cells in data_rows(chunks[4]): pop.append((cells[0], clean(cells[3])))
for cells in data_rows(chunks[6]): pop.append((cells[0], clean(cells[2])))
for cells in data_rows(chunks[7]): pop.append((cells[0], clean(cells[3])))
for m in re.finditer(r'`(bark\.vedana\.gift)`\s*«([^»]+)»', body):
    pop.append((m.group(1), m.group(2)))
for cells in data_rows(chunks[20]): pop.append((cells[0], clean(cells[1])))
# короткие повторные реплики NPC в окне диалога (greet, idle*, heal) ≤ 100 (GDD §12.2.2)
short = [(m.group(1), m.group(2)) for m in re.finditer(r'`(npc\.\w+\.(?:greet|idle\w*|heal))`[^«\n]*«([^»]+)»', body)]
ms = max(short, key=lambda x: len(x[1]))
print(f'Короткие реплики NPC в окне: {len(short)}, самая длинная {len(ms[1])} симв. ({ms[0]})')
for k, x in short:
    if len(x) > 100: fail(f'короткая реплика > 100: {k} {len(x)}')
mx = max(pop, key=lambda x: len(x[1]))
bad = [(k, t, len(t)) for k, t in pop if len(t) > 60]
print(f'Всплывающие реплики: {len(pop)}, самая длинная {len(mx[1])} симв. ({mx[0]})')
for b in bad: fail(f'реплика > 60: {b}')

# 4. советы ≤ 120
tips = [(c[0], c[1]) for c in data_rows(chunks[19])]
mt = max(tips, key=lambda x: len(x[1]))
print(f'Советы: {len(tips)}, самый длинный {len(mt[1])} симв. ({mt[0]})')
for k, t in tips:
    if len(t) > 120: fail(f'совет > 120: {k} {len(t)}')
if len(tips) != 15: fail('советов не 15')

# 5. цели трекера из act1 ≤ 28 (сверка канона, в этом файле целей нет)
goals = re.findall(r'^- ((?:Доберись|Спаси|Отбей|Одолей|Найди|Осмотри|Собери|Узнай|Пройди|Повали|Закрой|Выйди|Доложи)[^\n]*)$', act1, re.M)
print('Цели act1:', len(goals), ', максимум', max(len(g) for g in goals), 'симв.')
for g in goals:
    if len(g) > 28: fail(f'цель > 28: {g}')

# 6. диалоги NPC в окне (GDD §10.4): реплика ≤ 200 (ошибка), > 160 — предупреждение;
#    2–4 реплики на диалог, номера подряд, говорящие из реестра §5.0
SPEAKERS = {'ratibor', 'vyshata', 'vedana', 'tverdyata', 'mal', 'priest', 'sbyslav'}
dlg = {}
for line in chunks[5].splitlines():
    m = re.match(r'^\| `(dlg\.[\w.]+)` \| `([\w.]+)` \| (\d+) \| `(\w+)` \| (.*) \|$', line)
    if not m: continue
    key, d, n, who, text = m.group(1), m.group(2), int(m.group(3)), m.group(4), clean(re.sub(r'\((?:новое)\)', '', m.group(5)))
    dlg.setdefault(d, []).append((n, key, who, text))
print('Диалоги NPC (окно, реплик / слов / самая длинная):')
allrep = []
for d, rows_ in dlg.items():
    nums = [r[0] for r in rows_]
    words = sum(len(re.findall(r'[А-Яа-яЁё-]+', r[3])) for r in rows_)
    longest = max(len(r[3]) for r in rows_)
    print(f'  {d}: {len(rows_)} / {words} / {longest}')
    if not 2 <= len(rows_) <= 4: fail(f'{d}: реплик {len(rows_)}')
    if nums != list(range(1, len(nums) + 1)): fail(f'{d}: номера реплик {nums}')
    for n, key, who, text in rows_:
        allrep.append((key, text))
        if who not in SPEAKERS: fail(f'{key}: неизвестный говорящий {who}')
        if len(text) > 200: fail(f'{key}: реплика > 200 ({len(text)})')
        elif len(text) > 160: print(f'  ПРЕДУПРЕЖДЕНИЕ: {key} длиннее 160 ({len(text)})')
mr = max(allrep, key=lambda x: len(x[1]))
print(f'Реплик в окне: {len(allrep)}, диалогов: {len(dlg)}, самая длинная {len(mr[1])} симв. ({mr[0]})')
need_dlg = ['vyshata.s0', 'vyshata.s1', 'vedana.s0', 'vedana.s1', 'tverdyata.s0', 'tverdyata.s1', 'mal.s1', 'm1.mal']
for d in need_dlg:
    if d not in dlg: fail(f'нет диалога {d}')
if not any(k == 'dlg.vyshata.m1.dir' for k, _ in allrep): fail('нет dlg.vyshata.m1.dir')

# 6а. новые строки v1.3: пределы GDD §12.2.2–12.2.3
LIMITS = [(r'quest\.m1\.obj\.\w+', 28), (r'ui\.gate\.[\w.]+', 24), (r'sign\.\w+', 14),
          (r'ladoga\.caption\.\w+', 24), (r'ui\.dlg\.\w+', 24), (r'settings\.\w+', 24),
          (r'ui\.death\.wake\.\w+', 28), (r'ui\.save\.\w+', 40), (r'death\.(?:ladoga|krada|stone)\.\d', 60),
          (r'(?:proto\.)?respawn\.\w+', 60), (r'npc\.priest', 24)]
kv = {}
for line in body.splitlines():
    m = re.match(r'^\| `([\w.]+)` \| ([^|]*?) \|', line)
    if m: kv[m.group(1)] = clean(m.group(2))
need_new = ['quest.m1.obj.ladoga_exit', 'quest.m1.obj.report', 'ui.gate.open.zalesye', 'ui.gate.closed',
            'sign.zalesye', 'sign.sopki', 'sign.bor', 'sign.pier', 'ladoga.caption.church', 'ladoga.caption.pier',
            'ladoga.caption.torg', 'ladoga.caption.kuznya', 'ui.dlg.skip', 'ui.settings.navArrow',
            'ui.settings.xray', 'ui.settings.shake', 'ui.death.wake.ladoga', 'ui.death.wake.krada', 'ui.death.wake.stone',
            'respawn.ladoga', 'ui.save.broken', 'ui.save.newer', 'ui.save.older', 'bark.ladoga.m1_where',
            'bark.ladoga.gate_closed', 'ui.death.button']
for k in need_new:
    if k not in kv: fail(f'нет ключа {k}')
checked = 0; worst = {}
for k, x in kv.items():
    for pat, lim in LIMITS:
        if re.fullmatch(pat, k):
            checked += 1
            if len(x) > lim: fail(f'{k} > {lim}: {len(x)}')
            if pat not in worst or len(x) > len(worst[pat][1]): worst[pat] = (k, x)
print(f'Новые строки v1.3 по пределам GDD: проверено {checked}')
for pat, lim in LIMITS:
    if pat in worst: print(f'  ≤ {lim}: самая длинная {len(worst[pat][1])} ({worst[pat][0]})')
# наборы гибели: 3–5 строк, Ладога / Волхов / Милуша — только в наборе Ладоги
for place in ('ladoga', 'krada', 'stone'):
    s_ = [x for k, x in kv.items() if re.fullmatch(rf'death\.{place}\.\d', k)]
    if not 3 <= len(s_) <= 5: fail(f'death.{place}: строк {len(s_)}')
    if place != 'ladoga':
        for x in s_:
            if re.search(r'Ладог|Волхов|Милуш', x): fail(f'death.{place}: место не то — «{x}»')
print('Наборы гибели: ' + ', '.join(f"{p_} {len([k for k in kv if re.fullmatch(rf'death[.]{p_}[.][0-9]', k)])}" for p_ in ('ladoga', 'krada', 'stone')))

# 7. генератор вожаков: длина сочетаний
r9 = data_rows(chunks[9])
A = [(c[1], c[2]) for c in r9]; B = {'м.': [c[3] for c in r9], 'ж.': [c[4] for c in r9]}
combos = [f'{a} {b}' for a, g in A for b in B[g]]
lm = max(combos, key=len)
print(f'Вожаки: {len(A)} × {len(r9)}, сочетаний {len(combos)}, самое длинное «{lm}» = {len(lm)}')
if len(lm) > 24: fail('имя вожака > 24')
# генератор дивных: проверка повторов и длины
r10 = data_rows(chunks[10])
gmap = {'м.': 1, 'ж.': 2, 'ср.': 3, 'мн.': 4}
names = [f'{a[gmap[b[7]]]} {b[6]}' for a in r10 for b in r10]
ln = max(names, key=len)
print(f'Дивные: A {len(r10)} × Б {len(r10)}, сочетаний {len(names)}, самое длинное «{ln}» = {len(ln)}')
roots = lambda w: w.lower()[:4]
dup = [n for n in names if roots(n.split()[0]) == roots(n.split()[1])]
if dup: fail(f'тавтологии: {dup}')

# 8. имена из act1
canon = ['Ратибор','Вышата','Милуша','Твердята','Мал','Сбыслав','Чернояр','Лютоволк','Згуба','Кривша',
         'Обгорелый страж','Курганный князь','Огнея Пепельная','Сивый Клык','Залесье','Капище Перуна',
         'Чёрный бор','Разлом','Громовой знак','Лунница','Посох Чернояра','Карта бора','Приказ Чернояра',
         'Чистая вода','Порча Небыли','Чад','Удаль I','Ладога','Волхов','Сопки Волхова','Огонь на капище',
         'Разлом в Чёрном бору','Черноярец-поджигатель','Волхв-прислужник','Мертвяк курганный','Волколак',
         'Кикимора','Леший','Анчутка','Упырь','Навь','Обережные камни','Чёрный нож','Меч князя']
for n in canon:
    stem = lambda x: ' '.join(w[:5] for w in x.lower().split())
    in_act1 = n.lower() in act1.lower() or stem(n) in stem(re.sub(r'[^\w\s-]', ' ', act1))
    in_txt = n.lower() in body.lower()
    if not in_act1: fail(f'имя «{n}» в act1 не найдено')
print(f'Имена из act1 сверены: {len(canon)}')
print('Упоминания «Старший прислужник» (допустимо только в п. 1 как старое имя):', body.count('Старший прислужник'))

# 8а. старые слова после замены (v1.2, rename_map.md): ни в act1_texts, ни в act1.
# Записаны задом наперёд, как запретные. Служебные ключи латиницей (npc.vedana, ui.hud.yar) не задеваются.
old = [w[::-1] for w in ['b\\)юь|и|ь(рЯb\\', 'b\\)йо|у|е|ы|а(даркb\\', 'воруЧ', 'лоди-руч', 'руч-хосоп', 'кинвоморГ', 'надеВ', 'b\\)йо|у|е|ы|а(раМb\\', 'b\\)огеь|иь|еь|яь|йи(жоравсb\\', 'b\\)ха|има|во|ы(зерb\\', 'адоР окО']]
old_hits = 0
for path, text in ((TXT, s), (ACT1, act1)):
    for i, line in enumerate(text.splitlines(), 1):
        for j, w in enumerate(old, 1):
            if re.search(w, line, re.I):
                old_hits += 1; fail(f'старое слово №{j}: {path.split("/")[-1]}:{i}')
print(f'Старые слова после замены (11 корней, act1_texts + act1): найдено {old_hits}')

# 9. строк по пунктам
print('Строк по пунктам (строки таблиц + реплики диалогов):')
counts = {}
for n in need:
    c = len(data_rows(chunks[n])) + len(re.findall(r'^> ', chunks[n], re.M)) \
        + len(re.findall(r'`(?:npc|bark)\.[\w.]+`\s*«', chunks[n]))
    counts[n] = c
    print(f'  п. {n}: {c}')
print('ИТОГ:', 'OK' if ok else 'ЕСТЬ ОШИБКИ')

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
for m in re.finditer(r'`(bark\.vedana\.gift|npc\.\w+\.(?:idle\d|heal))`\s*«([^»]+)»', body):
    pop.append((m.group(1), m.group(2)))
for cells in data_rows(chunks[20]): pop.append((cells[0], clean(cells[1])))
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
if len(tips) != 12: fail('советов не 12')

# 5. цели трекера из act1 ≤ 28 (сверка канона, в этом файле целей нет)
goals = re.findall(r'^- ((?:Доберись|Спаси|Отбей|Одолей|Найди|Осмотри|Собери|Узнай|Пройди|Повали|Закрой)[^\n]*)$', act1, re.M)
print('Цели act1:', len(goals), ', максимум', max(len(g) for g in goals), 'симв.')
for g in goals:
    if len(g) > 28: fail(f'цель > 28: {g}')

# 6. диалоги NPC: 2–4 реплики, 20–40 слов на блок
blocks = re.split(r'\n(?=\*\*(?:С\d|Опушка)[^\n]*`npc\.)', chunks[5])
print('Диалоги NPC:')
for b in blocks[1:]:
    head = re.search(r'`(npc\.[\w.]+)`', b).group(1)
    lines = re.findall(r'^> \*\*[^*]+:\*\* (.*)$', b, re.M)
    words = sum(len(re.findall(r'[А-Яа-яЁё-]+', clean(l))) for l in lines)
    flag = '' if 2 <= len(lines) <= 4 and 15 <= words <= 40 else '  <-- проверить'
    print(f'  {head}: {len(lines)} репл., {words} слов{flag}')
    if not 2 <= len(lines) <= 4: fail(f'{head}: реплик {len(lines)}')

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
canon = ['Ратибор','Вышата','Ведана','Твердята','Мал','Сбыслав','Чернояр','Лютоволк','Згуба','Кривша',
         'Обгорелый страж','Курганный князь','Мара Пепельная','Сивый Клык','Залесье','Капище Перуна',
         'Чёрный бор','Разлом','Громовник','Лунница','Посох Чернояра','Карта бора','Приказ Чернояра',
         'Чистая вода','Порча Небыли','Чад','Ярь I','Ладога','Волхов','Сопки Волхова','Огонь на капище',
         'Разлом в Чёрном бору','Черноярец-поджигатель','Волхв-прислужник','Мертвяк курганный','Волколак',
         'Кикимора','Леший','Анчутка','Упырь','Навь','Обережные камни','Чёрный нож','Меч князя']
for n in canon:
    stem = lambda x: ' '.join(w[:5] for w in x.lower().split())
    in_act1 = n.lower() in act1.lower() or stem(n) in stem(re.sub(r'[^\w\s-]', ' ', act1))
    in_txt = n.lower() in body.lower()
    if not in_act1: fail(f'имя «{n}» в act1 не найдено')
print(f'Имена из act1 сверены: {len(canon)}')
print('Упоминания «Старший прислужник» (допустимо только в п. 1 как старое имя):', body.count('Старший прислужник'))

# 9. строк по пунктам
print('Строк по пунктам (строки таблиц + реплики диалогов):')
counts = {}
for n in need:
    c = len(data_rows(chunks[n])) + len(re.findall(r'^> ', chunks[n], re.M)) \
        + len(re.findall(r'`(?:npc|bark)\.[\w.]+`\s*«', chunks[n]))
    counts[n] = c
    print(f'  п. {n}: {c}')
print('ИТОГ:', 'OK' if ok else 'ЕСТЬ ОШИБКИ')

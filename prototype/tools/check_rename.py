"""Веха m1h: проверка замены терминов (story/rename_map.md v1.0). Запуск из любой папки:  python3 tools/check_rename.py [-v]
Ищет СТАРЫЕ формы во всём, что видит игрок:
  * data/ru.json — все строковые значения (кроме служебного _about); ключи не проверяются;
  * data/*.json, data/zones/*.json — строковые значения, кроме служебных полей (_*, *Note, note, gdd, about, comment) и ключей;
  * src/**/*.js — строковые литералы ('…', "…", `…`), комментарии вырезаются; id/ключи латиницей не совпадают с образцами;
  * index.html — текст страницы.
Разрешено (keep-list таблицы): «ярый/Ярый», «Чур-оберег», «Чур меня!», «огонь-Сварожич» (образцы их не задевают).
Выход 0 — совпадений нет; 1 — есть (печатаются файл, путь/строка, слово)."""
import glob, json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
W = r'(?![\w-])'           # конец слова (кириллица — \w в Python 3)
B = r'(?<![\w-])'          # начало слова
OLD = [
    ('Ярь',            B + r'[Яя]р(?:ь|и|ью|ей)' + W),                 # Ярь/Яри/Ярью/яри; «ярый», «ярость» не задевает
    ('Ярь I',          r'Ярь I'),
    ('родовая ярость', r'[Рр]одов(?:ая|ой|ую|ою) ярост'),
    ('Чуров*',         B + r'[Чч]уров\w*'),
    ('крада',          B + r'[Кк]рад(?:а|ы|е|у|ой|ою)' + W),
    ('Чур-идол*',      r'[Чч]ур-идол\w*'),
    ('Чур (как имя)',  B + r'[Чч]ур(?:а|у|ом|е|ы|ов)?' + r'(?![\w-])(?! меня!)'),   # «Чур прохода не откроет», «чуры»; «Чур меня!» — можно
    ('Посох-чур',      r'[Пп]осох-чур'),
    ('Громовник*',     r'[Гг]ромовник\w*'),
    ('Око Рода',       r'(?:Око|Ока|Оку|Оком) Рода'),
    ('Ведан*',         B + r'Ведан\w*'),
    ('Мара (имя)',     B + r'Мар(?:а|ы|е|у|ой|ою)' + W),
    ('Сварожий',       r'[Сс]варож(?!ич)\w*'),                          # Сварожий/-ья/-ье/-ьи/-ьего; «огонь-Сварожич» — можно
    ('Резы/рез',       B + r'[Рр]ез(?:ы|ов|ам|ами|ах)?' + W),
]
OLD_RE = [(n, re.compile(p)) for n, p in OLD]
SERVICE = re.compile(r'^(_.*|.*Note|note|gdd|about|comment)$')


def hits_in(text):
    return [(n, m.group(0)) for n, rx in OLD_RE for m in rx.finditer(text)]


def walk_json(v, path, out, service_ok):
    if isinstance(v, dict):
        for k, x in v.items():
            if service_ok and SERVICE.match(str(k)):
                continue
            walk_json(x, path + '.' + str(k), out, service_ok)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            walk_json(x, path + '[%d]' % i, out, service_ok)
    elif isinstance(v, str):
        out.append((path, v))


def js_strings(src):
    """Строковые литералы JS без комментариев (простой лексер; регулярки /…/ пропускаются эвристикой по предыдущему знаку)."""
    out, i, n, line = [], 0, len(src), 1
    prev = ''
    while i < n:
        c = src[i]
        if c == '\n':
            line += 1; i += 1; continue
        if src.startswith('//', i):
            j = src.find('\n', i); i = n if j < 0 else j; continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2); j = n if j < 0 else j + 2
            line += src.count('\n', i, j); i = j; continue
        if c in '\'"`':
            j, buf, l0 = i + 1, [], line
            while j < n and src[j] != c:
                if src[j] == '\\':
                    buf.append(src[j:j + 2]); j += 2; continue
                if src[j] == '\n':
                    line += 1
                buf.append(src[j]); j += 1
            out.append((l0, ''.join(buf))); i = j + 1; prev = c; continue
        if c == '/' and prev in '(,=:[!&|?{};+-*%<>~^' + '\n' or (c == '/' and prev == ''):
            j = i + 1; cls = False                      # литерал регулярного выражения
            while j < n and src[j] != '\n':
                if src[j] == '\\': j += 2; continue
                if src[j] == '[': cls = True
                elif src[j] == ']': cls = False
                elif src[j] == '/' and not cls: break
                j += 1
            i = j + 1; prev = '/'; continue
        if not c.isspace():
            prev = c
        i += 1
    return out


def scan():
    res, counted = [], {'ru.json': 0, 'data': 0, 'src': 0, 'html': 0}
    ru = json.load(open(os.path.join(ROOT, 'data', 'ru.json'), encoding='utf-8'))
    vals = []
    walk_json({k: v for k, v in ru.items() if k != '_about'}, 'ru', vals, False)
    counted['ru.json'] = len(vals)
    for p, s in vals:
        res += [('data/ru.json', p, w, word) for w, word in hits_in(s)]
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '*.json')) + glob.glob(os.path.join(ROOT, 'data', 'zones', '*.json'))):
        if f.endswith('ru.json'):
            continue
        vals = []
        walk_json(json.load(open(f, encoding='utf-8')), '', vals, True)
        counted['data'] += len(vals)
        rel = os.path.relpath(f, ROOT)
        res += [(rel, p, w, word) for p, s in vals for w, word in hits_in(s)]
    for f in sorted(glob.glob(os.path.join(ROOT, 'src', '**', '*.js'), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        for ln, s in js_strings(open(f, encoding='utf-8').read()):
            counted['src'] += 1
            res += [(rel, 'стр. %d' % ln, w, word) for w, word in hits_in(s)]
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    html = re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->', '', html, flags=re.S)
    counted['html'] = 1
    res += [('index.html', 'текст', w, word) for w, word in hits_in(re.sub(r'<[^>]+>', ' ', html))]
    return res, counted


def selftest():
    """Образцы ловят все старые формы из таблицы и не задевают keep-list."""
    bad = ['Ярь', 'Яри', 'Ярью', 'зелье яри', 'Ярь I', 'родовая ярость', 'Чуров камень', 'Чурова камня', 'Чуровых камней', 'крада', 'у крады',
           'краде', 'Крада', 'чур-идол', 'Чур-идолы', 'Посох-чур', 'Громовник', 'Громовника', 'Око Рода', 'Ведана', 'Веданы', 'Веданой',
           'Мара Пепельная', 'Мары', 'Маре', 'Мару', 'Марой', 'Сварожий', 'Сварожья', 'сварожьего огня', 'резы', 'с резами', 'кольцо рез',
           'Чур прохода не откроет']
    good = ['Ярый', 'ярый', 'ярость', 'Чур-оберег', 'Чур-оберега', 'Чур меня!', 'огонь-Сварожич', 'огня-Сварожича', 'Марфа', 'через', 'Удаль',
            'Милуша', 'Огнея', 'путевой камень', 'костёр', 'чёрный идол', 'Громовой знак', 'Жгучий', 'насечки', 'боевая ярость', 'украдкой', 'резать']
    miss = [s for s in bad if not hits_in(s)]
    false = [s for s in good if hits_in(s)]
    return miss, false


if __name__ == '__main__':
    miss, false = selftest()
    res, counted = scan()
    print('check_rename: строк просмотрено — ru.json %(ru.json)d, data %(data)d, src (литералы) %(src)d, index.html' % counted)
    print('самопроверка образцов: не пойманы %d, ложные %d' % (len(miss), len(false)), (miss, false) if miss or false else '')
    for f, p, w, word in res if '-v' in sys.argv or len(res) <= 40 else res[:40]:
        print('  %s  %s  [%s] «%s»' % (f, p, w, word))
    print('совпадений со старыми формами: %d' % len(res))
    sys.exit(1 if res or miss or false else 0)

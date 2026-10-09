"""m1i: в src/**/*.js не должно быть кириллицы в строковых литералах (вне комментариев) — все видимые игроку строки живут
в data/ru.json (tools/export_ru.py). Запуск из папки prototype: python3 tools/check_cyrillic.py  → «литералов с кириллицей: 0».
Разрешённые исключения — явный список ниже (не видны игроку как текст интерфейса)."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')

ALLOW_FILES = {
    'data/font_ru.js': 'таблица глифов растрового шрифта (сами буквы алфавита)',
    'data/ui_atlas.js': 'данные раскладки, сгенерированные tools/export_ui.py из арта; подписи кнопок берутся из ru.json (hud.js BTN_LABEL)',
}
ALLOW = {   # (файл, литерал): причина
    ('core/i18n.js', "'Текст'"): 'имя столбца таблицы act1_texts в объекте ru.json',
    ('entities/boss.js', "'Текст'"): 'имя столбца ru.json',
    ('data/items.js', "'Строка в тултипе'"): 'имя столбца ru.json (rarity.unique)',
    ('render/world.js', "'Имя'"): 'имя столбца ru.json (codex)',
    ('render/world.js', "'Плашка'"): 'имя столбца ru.json (codex)',
    ('systems/zones.js', "'Кто'"): 'имя столбца ru.json (bark)',
    ('systems/zones.js', "'Текст'"): 'имя столбца ru.json (bark)',
    ('systems/zones.js', "'Предмет'"): 'имя столбца ru.json (relic)',
    ('systems/zones.js', "'Описание'"): 'имя столбца ru.json (relic)',
    ('systems/zones.js', "'Название'"): 'имя столбца ru.json (zone)',
    ('systems/zones.js', "'Селянка'"): 'сравнение со значением столбца «Кто» из ru.json (выбор голоса)',
    ('systems/zones.js', "'Старик'"): 'сравнение со значением столбца «Кто» из ru.json (выбор голоса)',
    ('render/hud.js', "'Быль'"): 'сравнение со значением realm из monsters.json (цвет строки)',
    ('systems/combat.js', "'Нечисть'"): 'сравнение со значением family из monsters.json (правило урона)',
    ('data/config.js', "'Не загрузился конфиг '"): 'текст исключения загрузки (отладка)',
    ('data/config.js', "'Не загрузилась зона '"): 'текст исключения загрузки (отладка)',
    ('ui/assets.js', "'Не загрузился ассет'"): 'console.warn',
    ('render/rest_fx.js', "'Не загрузился ассет'"): 'console.warn',
    ('render/rest_fx.js', "'Не загрузился ассет fx_safe_ring'"): 'console.warn',
    ('render/boss_art.js', "'Не загрузился ассет'"): 'console.warn',
    ('render/boss_art.js', "'Не загрузились листы:'"): 'console.warn',
}
LIT = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`")
CYR = re.compile('[А-Яа-яЁё]')


def strip_comments(s):
    out, i, n, q = [], 0, len(s), None
    while i < n:
        c = s[i]
        if q:
            out.append(c)
            if c == '\\':
                out.append(s[i + 1:i + 2]); i += 2; continue
            if c == q:
                q = None
            i += 1; continue
        if c in '\'"`':
            q = c; out.append(c); i += 1; continue
        if s.startswith('//', i):
            j = s.find('\n', i); i = n if j < 0 else j; continue
        if s.startswith('/*', i):
            j = s.find('*/', i); seg = s[i:(n if j < 0 else j + 2)]; out.append('\n' * seg.count('\n')); i = n if j < 0 else j + 2; continue
        out.append(c); i += 1
    return ''.join(out)


def scan():
    hits, allowed = [], 0
    for dp, _, fs in os.walk(ROOT):
        for f in sorted(fs):
            if not f.endswith('.js'):
                continue
            p = os.path.join(dp, f); rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
            if rel in ALLOW_FILES:
                continue
            s = strip_comments(open(p, encoding='utf-8').read())
            for m in LIT.finditer(s):
                if CYR.search(m.group()):
                    if (rel, m.group()) in ALLOW:
                        allowed += 1; continue
                    hits.append((rel, s.count('\n', 0, m.start()) + 1, m.group()))
    return hits, allowed


def selftest():
    s = strip_comments("a('Да'); // 'Нет'\n/* 'Нет' */ b(\"ok\") `Тут ${x}`")
    found = [m.group() for m in LIT.finditer(s) if CYR.search(m.group())]
    return found == ["'Да'", '`Тут ${x}`']


if __name__ == '__main__':
    hits, allowed = scan()
    for h in hits[:20]:
        print(*h)
    print(f'самопроверка: {"ок" if selftest() else "СБОЙ"}; разрешено по списку: {allowed}; литералов с кириллицей: {len(hits)}')
    sys.exit(1 if hits or not selftest() else 0)

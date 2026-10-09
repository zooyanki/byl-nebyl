"""m1k: прогон /workspace/gamedesign/tools/ladoga_layout_v113.py по координатам из data/zones/ladoga.json (D7, §12.3 H).
Скрипт дизайнера не меняется: список B подменяется футпринтами из ladoga.json (props + крада), остальное — как есть.
Дополнительно сверяет id/клетки с таблицей скрипта и точку попа Иоанна из npcs."""
import json, re, sys, io, contextlib
SCRIPT = '/workspace/gamedesign/tools/ladoga_layout_v113.py'
Z = json.load(open('/workspace/game/prototype/data/zones/ladoga.json', encoding='utf-8'))
src = open(SCRIPT, encoding='utf-8').read()
ns = {}
exec(re.search(r"^B = \[.*?^\]", src, re.S | re.M).group(0), ns)
ref = {b[0]: b for b in ns['B']}
NAME = {'cart': lambda x, y: 'cart_w' if x < 24 else 'cart_e', 'anvil': lambda x, y: 'anvil', 'idol': lambda x, y: 'idol', 'churstone': lambda x, y: 'churstone'}
B = [("krada", "костёр", Z['krada'][0], Z['krada'][0] + 1, Z['krada'][1], Z['krada'][1] + 1)]
for kind, x, y, size, fp, *ex in Z['props']:
    e = ex[0] if ex else {}
    pid = e.get('id') or (NAME[kind](x, y) if kind in NAME else None)
    if not pid: continue
    pid = 'izba_milusha' if pid == 'milusha' else pid
    B.append((pid, kind, fp[0], fp[0] + fp[2] - 1, fp[1], fp[1] + fp[3] - 1))
mine = {b[0]: b for b in B}
diff = [k for k in ref if k not in mine or mine[k][2:] != ref[k][2:]] + [k for k in mine if k not in ref]
pr = next(n for n in Z['npcs'] if n.get('id') == 'priest')
pts = re.search(r'"поп Иоанн[^"]*":\((\d+\.\d+),(\d+\.\d+)\)', src)
src2 = re.sub(r"^B = \[.*?^\]", "B = " + repr(B), src, count=1, flags=re.S | re.M)
src2 = re.sub(r'("поп Иоанн[^"]*":)\(\d+\.\d+,\d+\.\d+\)', r'\g<1>(%s,%s)' % (pr['x'], pr['y']), src2)
buf = io.StringIO(); code = 0
with contextlib.redirect_stdout(buf):
    try: exec(compile(src2, SCRIPT, 'exec'), {'__name__': '__main__'})
    except SystemExit as e: code = e.code or 0
out = buf.getvalue()
print(out.splitlines()[0]); print(out.strip().splitlines()[-1] if code == 0 else out[out.find('ОШИБКИ'):])
print('сверка с таблицей скрипта:', 'совпадает' if not diff else diff, '| поп Иоанн', (pr['x'], pr['y']), 'в скрипте', pts.groups() if pts else None)
sys.exit(1 if code or diff else 0)

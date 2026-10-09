"""Before/after contact sheets for rename_map §5 (09.10). before = /workspace/scratch_rename/art_before."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
A = '/workspace/game/art/'; B = '/workspace/scratch_rename/art_before/'; OUT = A + 'rename_s5/'
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
BG = (24, 26, 30)

def regions(a, b, cell=12, pad=12, maxn=4):
    d = np.any(np.asarray(a.convert('RGBA'), int) != np.asarray(b.convert('RGBA'), int), axis=2)
    H, W = d.shape; gh, gw = (H + cell - 1) // cell, (W + cell - 1) // cell
    g = np.zeros((gh, gw), bool)
    ys, xs = np.nonzero(d); g[ys // cell, xs // cell] = True
    lab = -np.ones_like(g, int); n = 0; out = []
    for sy, sx in zip(*np.nonzero(g)):
        if lab[sy, sx] >= 0: continue
        st = [(sy, sx)]; lab[sy, sx] = n; cells = []
        while st:
            y, x = st.pop(); cells.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < gh and 0 <= xx < gw and g[yy, xx] and lab[yy, xx] < 0:
                        lab[yy, xx] = n; st.append((yy, xx))
        m = np.zeros_like(d); 
        for y, x in cells: m[y*cell:(y+1)*cell, x*cell:(x+1)*cell] = True
        yy, xx = np.nonzero(d & m)
        out.append((max(0, xx.min()-pad), max(0, yy.min()-pad), min(W, xx.max()+pad+1), min(H, yy.max()+pad+1)))
        n += 1
    out.sort(key=lambda r: -(r[2]-r[0])*(r[3]-r[1]))
    return out[:maxn]

def flat(im):
    bg = Image.new('RGBA', im.size, (52, 56, 62, 255)); bg.alpha_composite(im.convert('RGBA')); return bg.convert('RGB')

def pair(path, scale, box=None, maxn=4):
    a, b = Image.open(A + path), Image.open(B + path)
    boxes = [box] if box else regions(a, b, maxn=maxn)
    rows = []
    for bx in boxes:
        ca, cb = flat(b.crop(bx)), flat(a.crop(bx))
        w, h = ca.width * scale, ca.height * scale
        r = Image.new('RGB', (w * 2 + 12, h), BG)
        r.paste(ca.resize((w, h), Image.NEAREST), (0, 0)); r.paste(cb.resize((w, h), Image.NEAREST), (w + 12, 0))
        rows.append(r)
    return rows

def sheet(name, title, parts):
    rows = []
    for path, scale, box, maxn in parts:
        rows.append(('· ' + path + ('' if scale > 1 else '  (preview, already ×3)'), None))
        rows += [(None, r) for r in pair(path, scale, box, maxn)]
    W = max([620] + [r.width for _, r in rows if r is not None]) + 20
    H = 44 + sum((22 if t else r.height + 8) for t, r in rows)
    im = Image.new('RGB', (W, H), BG); dr = ImageDraw.Draw(im)
    dr.text((10, 6), title, font=F, fill=(240, 220, 170)); dr.text((10, 24), 'ДО  |  ПОСЛЕ', font=F, fill=(160, 170, 180))
    y = 44
    for t, r in rows:
        if t: dr.text((10, y + 2), t, font=F, fill=(150, 160, 170)); y += 22
        else: im.paste(r, (10, y)); y += r.height + 8
    im.save(OUT + name); return im

S = 'sprites/'
ITEMS = [
 ('01_veshchee_icon.png', '1. «Вещее слово»: руны → искры (тех же цветов)', [('ui/skill_icons_v2_x3.png', 2, None, 1)]),
 ('02_hud_orb_udal.png', '2. Шар HUD: «Ярь» → «Удаль» (+ иконка «Вещее слово» на панели)', [('ui/mockup_gameplay_hud_v2_native.png', 3, None, 3), ('ui/mockup_inventory_v2_native.png', 3, None, 3)]),
 ('03_character_udal.png', '3. Окно «Витязь»: «Ярь» → «Удаль»', [('ui/mockup_character_v2_native.png', 3, None, 2)]),
 ('04_act_map_reward.png', '4. Плашка награды М1: «Удаль I», «Амулет «Громовой знак»»', [('ui/mockup_act_map_v2_native.png', 3, None, 2)]),
 ('05_item_icons_label.png', '5. Лист иконок: «Посох-чур» → «Посох волхва»', [('ui/item_icons_v2_native.png', 3, None, 2)]),
 ('06_teaser_tracker.png', '6. Тизер: «Повали чёрные идолы», шар «Удаль»', [('teaser/hud_scene23_a_native.png', 3, None, 3)]),
 ('07_putevoy_kamen.png', '7. Путевой камень (fx_rest_churov): знаки → насечки', [(S+'fx_rest_churov/fx_rest_churov_idle.png', 3, (0, 0, 64, 56), 1), (S+'fx_rest_churov/fx_rest_churov_rest.png', 3, (0, 0, 64, 56), 1)]),
 ('08_putevoy_prohod.png', '8. Путевой проход (fx_chur_portal): знаки → насечки', [(S+'fx_chur_portal/fx_chur_portal_loop.png', 3, None, 1)]),
 ('09_koster_m3.png', '9. Костёр М3 (fx_rest_campfire): резы на камнях → насечки', [(S+'fx_rest_campfire/fx_rest_campfire_idle.png', 3, (0, 0, 96, 56), 1), (S+'fx_rest_campfire/fx_rest_campfire_rest.png', 3, (0, 0, 96, 56), 1)]),
 ('10_safe_ring.png', '10. Кольцо безопасной зоны: резы → насечки', [(S+'fx_safe_ring/fx_safe_ring_runes_lit.png', 3, None, 1), (S+'fx_safe_ring/fx_safe_ring_runes_dim.png', 3, None, 1)]),
 ('11_ognishche.png', '11. Огнища М1 (на решение): резы → насечки', [(S+'ognishche/ognishche_consecrated.png', 3, None, 1), (S+'ognishche/ognishche_desecrated.png', 3, None, 1)]),
 ('12_preview_captions.png', '12. Подписи превью: Крада → Костёр, Мара → Огнея, Резы → Насечки', [(S+'fx_rest_krada/preview/fx_rest_krada_x3.png', 1, None, 1), (S+'mara/preview/mara_idle_x3.png', 1, None, 1), (S+'fx_safe_ring/preview/fx_safe_ring_runes_x3.png', 1, None, 1)]),
]
if __name__ == '__main__':
    ims = []
    for n, t, p in ITEMS:
        im = sheet(n, t, p); ims.append(im); print(n, im.size)
    # overview: each sheet scaled to width 900
    th = [im.resize((900, max(1, int(im.height * 900 / im.width))), Image.NEAREST) if im.width > 900 else im for im in ims]
    cols = 2; colh = [0] * cols; place = []
    for im in th:
        c = colh.index(min(colh)); place.append((c, colh[c])); colh[c] += im.height + 10
    ov = Image.new('RGB', (cols * 910 + 10, max(colh) + 10), (12, 13, 15))
    for im, (c, y) in zip(th, place): ov.paste(im, (10 + c * 910, 10 + y))
    ov.save(OUT + 'before_after_overview.png'); print('overview', ov.size)

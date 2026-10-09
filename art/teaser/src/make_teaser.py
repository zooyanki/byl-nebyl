"""Build all teaser frames: python3 make_teaser.py  (writes ../*.png + ../teaser_report.json)."""
import json
from teaser_scenes import *          # noqa
from teaser_scenes import _r          # noqa
import teaser_hud as TH
from PIL import Image

OUTD = os.path.abspath(os.path.join(HERE, ".."))
PAL_RGB = {tuple(int(v) for v in c) for c in pk.RGB}
REPORT = dict(files=[], checks={})


def save_rgb(a, name, native_name=None):
    cv = Canvas(W, H); cv.a[:] = a
    nat = native_name or (name.replace("_nohud", "") + "_native")
    cv.save(os.path.join(OUTD, nat + ".png"))
    big = cv.save(os.path.join(OUTD, name + ".png"), scale=3)
    assert big.size == (1920, 1080) and big.mode == "RGB"
    cols = {tuple(c) for c in np.array(big).reshape(-1, 3)}
    assert cols <= PAL_RGB, "off-palette colour in " + name
    REPORT["files"] += [name + ".png", nat + ".png"]
    REPORT["checks"][name] = dict(colours=len(cols), palette_ok=True)
    return big


def save_layer(layer, name):
    alpha = np.where(layer == TH.TR, 0, 255).astype(np.uint8)
    idx = np.where(layer == TH.TR, 0, layer)
    rgba = np.dstack([pk.RGB[idx], alpha]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    im.save(os.path.join(OUTD, name + "_native.png"))
    big = im.resize((1920, 1080), Image.NEAREST)
    big.save(os.path.join(OUTD, name + ".png"))
    arr = np.array(big)
    assert set(np.unique(arr[..., 3])) <= {0, 255}
    cols = {tuple(c) for c in arr[arr[..., 3] == 255][:, :3]}
    assert cols <= PAL_RGB, "off-palette colour in " + name
    REPORT["files"] += [name + ".png", name + "_native.png"]
    REPORT["checks"][name] = dict(alpha_values=sorted(int(v) for v in np.unique(arr[..., 3])), palette_ok=True,
                                  opaque_share=round(float((alpha == 255).mean()), 3))


def check_composite(nohud_name, layer_name, hud_name):
    """Verify on the delivered 1920 files: nohud + layer (alpha over) == *_hud."""
    a = np.array(Image.open(os.path.join(OUTD, nohud_name + ".png")).convert("RGB")).astype(int)
    l = np.array(Image.open(os.path.join(OUTD, layer_name + ".png")))
    h = np.array(Image.open(os.path.join(OUTD, hud_name + ".png")).convert("RGB")).astype(int)
    m = l[..., 3] == 255
    a[m] = l[..., :3][m]
    ok = bool((a == h).all())
    REPORT["checks"]["composite " + hud_name] = ok
    assert ok, hud_name


SK_M3 = dict(lmb=("sword", False), rmb=("fire_serpent", True),
             f=(("fire_serpent", True), ("frost", False), ("shield_bash", False), ("obereg", False), ("perun", False),
                ("axe", False)), belt=("life", "life", "mana", "zhivaya"), dash=None)
Q_M3_T = dict(title="РАЗЛОМ В ЧЁРНОМ БОРУ", act="Задание · Акт I")
# goals verbatim per teaser.md 1.1 (act1 v1.1)
Q_M3_23 = dict(Q_M3_T, goals=(("— Пройди Чёрный бор", "", "slate_lt", True),
                              ("— Повали чёрные идолы", "1/3", "linen", False),
                              ("— Одолей Чернояра", "", "linen", False)))
Q_M3_4S = dict(Q_M3_T, goals=(("— Повали чёрные идолы", "3/3", "slate_lt", True),
                              ("— Одолей Чернояра", "", "linen", False),
                              ("— Закрой Разлом", "", "nebyl", False)))
Q_M3_4E = dict(Q_M3_T, goals=(("— Одолей Чернояра", "", "slate_lt", True),
                              ("— Закрой Разлом", "", "nebyl", False)))


def mm_s1():
    cx, cy = S1["idol"]
    ring = [(cx + math.cos(a) * 90, cy + math.sin(a) * 45) for a in np.linspace(0, math.tau, 25)]
    pal = [(x, pal_base(x)) for x in range(-200, 860, 40)]
    return [("forest", 12), ("poly", pal, "bronze_lt", True), ("poly", ring, "wood_lt", True),
            ("dot", S1["krada"], "ember", True), ("dot", S1["idol"], "flame", True),
            ("dot", S1["upyr1"], "red_lt"), ("dot", S1["upyr2"], "red_lt"), ("dot", S1["upyr3"], "red_lt"),
            ("quest", S1["hearth2"])]


def mm_s23():
    return [("forest", 84), ("rift", S2["rift"]), ("dot", S2["volk"], "red_lt", True), ("dot", S2["fallen"], "slate_lt"),
            ("quest", S2["idol"])]


def mm_s4(boss=True):
    m = [("forest", 84), ("rift", S4["rift"])] + [("dot", p, "slate_lt") for p in S4["idols"]]
    if boss:
        m.append(("dot", S4["boss"], "red_lt", True))
    m.append(("quest", S4["rift"]))
    return m


def main():
    os.makedirs(OUTD, exist_ok=True)
    # ---------------- scene 1
    a1, lit1, L1 = scene1()
    meas1 = dict(MEAS); MEAS.clear()
    save_rgb(a1, "scene1_start_nohud", "scene1_start_native")
    spec1 = dict(minimap=mm_s1(), zone=("Капище Перуна", "Акт I · Миссия 1 из 3"),
                 target=("Упырь", 0.58, "Нечисть · Небыль"),
                 quest=dict(title="ОГОНЬ НА КАПИЩЕ", act="Задание · Акт I",
                            goals=(("— Спаси выживших", "3/3", "slate_lt", True), ("— Отбей огнища у упырей", "1/3", "linen", False),
                                   ("— Одолей Крившу", "", "linen", False))),
                 hud=dict(level=4, life=(95, 102), yar=(50, 58), silver=284, free_points=5), xp=0.40,
                 skills=dict(lmb=("sword", False), rmb=("shield_bash", True),
                             f=(("shield_bash", True), ("fire_serpent", False), None, None, None, None),
                             belt=("life", "life", "mana", "zhivaya"), dash=None))
    lay1, qbox1 = TH.hud_layer(spec1, lit1, L1)
    save_layer(lay1, "hud_scene1")
    save_rgb(TH.composite(a1, lay1), "scene1_start_hud", "scene1_start_hud_native")
    check_composite("scene1_start_nohud", "hud_scene1", "scene1_start_hud")
    # ---------------- scenes 2 / 3
    a2, lit2, L2 = scene2()
    meas2 = dict(MEAS); MEAS.clear()
    a3, lit3, L3 = scene3()
    meas3 = dict(MEAS); MEAS.clear()
    save_rgb(a2, "scene2_start_nohud", "scene2_start_native")
    save_rgb(a3, "scene3_start_nohud", "scene3_start_native")
    base23 = dict(minimap=mm_s23(), zone=("Чёрный бор", "Акт I · Миссия 3 из 3"),
                  quest=Q_M3_23, hud=dict(level=12, life=(172, 186), yar=(113, 121), silver="3 140", free_points=0),
                  xp=0.30, skills=SK_M3)
    spec23a = dict(base23, target=("Волколак", 1.0, "Нечисть · Небыль"))
    spec23b = dict(base23, target=("Волколак", 0.35, "Нечисть · Небыль"),
                   hud=dict(base23["hud"], yar=(106, 121)))
    lay23a, qbox23 = TH.hud_layer(spec23a, lit2, L2)
    lay23b, _ = TH.hud_layer(spec23b, lit3, L3)
    # the minimap shows the darkened world under it; scenes 2 and 3 differ only
    # in characters -> use the scene-2 minimap in both layers for a static overlay
    mm = np.zeros((H, W), bool); mm[26:110, 506:634] = True
    lay23b[mm] = lay23a[mm]
    save_layer(lay23a, "hud_scene23_a")
    save_layer(lay23b, "hud_scene23_b")
    save_rgb(TH.composite(a2, lay23a), "scene2_start_hud", "scene2_start_hud_native")
    save_rgb(TH.composite(a3, lay23a), "scene3_start_hud", "scene3_start_hud_native")
    check_composite("scene2_start_nohud", "hud_scene23_a", "scene2_start_hud")
    check_composite("scene3_start_nohud", "hud_scene23_a", "scene3_start_hud")
    # ---------------- scene 4
    a4, lit4, L4 = scene4(False)
    meas4 = dict(MEAS); MEAS.clear()
    a4e, lit4e, L4e = scene4(True)
    meas4e = dict(MEAS); MEAS.clear()
    save_rgb(a4, "scene4_start_nohud", "scene4_start_native")
    save_rgb(a4e, "scene4_end_nohud", "scene4_end_native")
    d = a4 != a4e
    ys, xs = np.where(d)
    REPORT["checks"]["scene4_start_vs_end"] = dict(changed_px=int(d.sum()), share=round(float(d.mean()), 4),
                                                   bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
    # changed pixels must all lie inside the declared change zones
    zones = np.zeros((H, W), bool)
    for nm in ("hero_s4", "hero_s4_end"):
        x0, y0, x1, y1 = (meas4.get(nm) or meas4e.get(nm))["box"]; zones[y0 - 3:y1 + 2, x0 - 2:x1 + 3] = True
    for nm in ("boss_kneel", "prince_sword"):
        x0, y0, x1, y1 = meas4[nm]["box"]; zones[y0 - 2:y1 + 6, x0 - 31:x1 + 31] = True   # incl. shadow
    for nm in ("pelt", "staff", "prince_sword_end", "silver"):
        x0, y0, x1, y1 = meas4e[nm]["box"]; zones[y0:y1 + 1, x0:x1 + 1] = True
    zones[100:182, 400:470] = True          # ash wisp to the rift
    rr = meas4e["rift_s4"]; zones[rr["top"] - 2:rr["bottom"] + 2, rr["x0"] - 8:rr["x1"] + 8] = True
    REPORT["checks"]["scene4_changes_inside_zones"] = bool((~zones & d).sum() == 0)
    REPORT["checks"]["scene4_outside_zones_px"] = int((~zones & d).sum())
    spec4 = dict(minimap=mm_s4(True), zone=("Край Разлома", "Акт I · Миссия 3 из 3"),
                 target=("Чернояр · Лютоволк", 0.05, "Люди · Небыль"), quest=Q_M3_4S,
                 hud=dict(level=15, life=(64, 218), yar=(38, 139), silver="7 960", free_points=0), xp=0.92,
                 skills=dict(SK_M3, lmb=("sword", True), rmb=("fire_serpent", False),
                             f=(("fire_serpent", False),) + SK_M3["f"][1:]))
    spec4e = dict(spec4, target=None, xp=0.97, minimap=mm_s4(True), quest=Q_M3_4E)
    lay4, qbox4 = TH.hud_layer(spec4, lit4, L4)
    lay4e, _ = TH.hud_layer(spec4e, lit4, L4)          # same minimap pixels (start world) -> static overlay
    save_layer(lay4, "hud_scene4")
    save_layer(lay4e, "hud_scene4_end")
    loot, lboxes = TH.loot_layer((("Посох Чернояра", "bronze_lt", 398, 128), ("Меч князя", "ember", 432, 142),
                                  ("312 сер.", "linen", 414, 156)))
    save_layer(loot, "hud_scene4_loot")
    save_rgb(TH.composite(a4, lay4), "scene4_start_hud", "scene4_start_hud_native")
    check_composite("scene4_start_nohud", "hud_scene4", "scene4_start_hud")
    save_rgb(TH.composite(TH.composite(a4e, lay4e), loot), "scene4_end_hud", "scene4_end_hud_native")
    hb = meas4e["hero_s4_end"]["box"]
    REPORT["checks"]["loot_labels_clear_of_hero"] = all(b[0] > hb[2] or b[2] < hb[0] or b[1] > hb[3] or b[3] < hb[1]
                                                        for b in lboxes)
    items = np.zeros((H, W), bool)
    for nm in ("pelt", "staff", "prince_sword_end", "silver"):
        x0, y0, x1, y1 = meas4e[nm]["box"]; items[y0:y1 + 1, x0:x1 + 1] = True
    REPORT["checks"]["loot_labels_clear_of_items"] = bool(not ((loot != TH.TR) & items).any())
    REPORT["loot_label_boxes"] = lboxes
    REPORT["tracker_boxes"] = dict(s1=qbox1, s23=qbox23, s4=qbox4)
    REPORT["measure"] = dict(scene1=meas1, scene2=meas2, scene3=meas3, scene4_start=meas4, scene4_end=meas4e)
    # ---------------- title card (teaser §7.2): main-menu background, no menu, no «ГАРДАРИКИ»
    import main_menu_v2 as MM
    import theme_rus as T
    from fonts_ru import FONT_RU
    bg = Canvas(W, H)
    MM.background(bg)
    save_rgb(bg.a.copy(), "title_bg_nohud", "title_bg_native")
    tc = Canvas(W, H); tc.a[:] = bg.a
    lx, ly, lw, lh = MM.logo(tc, 118)
    sub = "Акт I · Ладога"
    sw_ = pk.text_width(sub, FONT_RU)
    tc.remap(W // 2 - sw_ // 2 - 6, ly + lh + 4, sw_ + 12, 13, pk.DARKEN3)
    T.text_ru(tc, W // 2 + 1, ly + lh + 7, sub, C["mist"], align="c")
    for sx in (W // 2 - sw_ // 2 - 52, W // 2 + sw_ // 2 + 10):
        T.interlace(tc, sx, ly + lh + 7, 42, 7, period=10, bg=C["ink"])
    T.text_ru(tc, W // 2 + 1, 343, "рабочее название · пре-альфа · браузерная экшен-RPG", C["slate_lt"], align="c",
              outline=False)
    save_rgb(tc.a, "title_card", "title_card_native")
    REPORT["title_logo_box"] = (lx, ly, lw, lh)
    with open(os.path.join(OUTD, "teaser_report.json"), "w") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=1, default=lambda o: int(o) if isinstance(o, np.integer)
                  else (float(o) if isinstance(o, np.floating) else str(o)))
    print(json.dumps(REPORT["checks"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

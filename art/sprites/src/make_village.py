"""GDD v1.13 §12.1.7 — Ладога/Залесье: постройки (H1–H4, H11–H15), ворота и указатель (H5–H6), след удара (H10).
python3 make_village.py   (also called from make_all.py)
Writes /workspace/game/art/sprites/buildings/<name>.png/.json + preview/<name>_x3.png.
Geometry = prototype src/core/iso.js: tile 32×16, w2s(x,y) = ((x−y)·16, (x+y)·8); u = world x (east), v = world y (south)."""
import os
import json
import numpy as np
import rig  # noqa: F401  (activates palette v2)
import export as X
import village as VL

ROOT = X.ROOT
BLD = os.path.join(ROOT, "buildings")

XRAY = {"rule": "scale.md 1.4 §4.4 / GDD v1.13 §10.3: if the sprite intersects the ellipse rx 56, ry 40 px centred at "
                "hero pivot − 22 px and the building sorts IN FRONT of the hero, draw the whole sprite at alpha 0.35 "
                "(0.2 s transition); hero gets a 1-px bronze_hi outline when ≥ 25% covered",
        "alpha": 0.35, "ellipse_px": [56, 40], "hero_center_offset_y": -22}
SORT = ("v1.13.2 fix (09.10): sort by the footprint CENTRE, exactly like prototype map.js addProp: depth = x0 + A/2 + y0 + B/2 "
        "(tiles); palisade / gate segments are 1×1 props → x + y + 1; hero, NPC, enemies → x + y. Do NOT use the front corner "
        "(x0+A)+(y0+B): buildings flush with the east palisade (seni_ne, ambar_se) then paint over the fence")
PLACE = ("place the sprite so that proto_corner_px lands on iso.js toS(p.x, p.y) (footprint min corner), "
         "equivalently pivot on the screen point of the footprint centre ((x0 + A/2), (y0 + B/2))")

# name, builder, (A, B), title, heights (px above ground), Ladoga ids using it, notes
BUILDINGS = [
    ("bld_church", VL.church, (6, 4), "Церковь клетская (Церковь Климента)",
     dict(chetverik_wall=88, chetverik_ridge=160, glavka_cross_top=184, prirub_wall=64, prirub_ridge=112, paperte=48, door=60),
     {"church": "+y (юг, к торгу) — frame 0"},
     "v1.13.2: дверь 56 + порог и паперть-навес (48 у края) на +y, к торгу; навес и ступени выходят за футпринт на +y на 1,3 тайла "
     "(y 13–14,3, на клетках улицы перед церковью; это перед зданием, сортировке не мешает). Варианта +x нет: на востоке алтарный "
     "прируб, дверей там не делают. Главка: сруб-барабан 6, шлемовидная главка в лемехе 8, крест 10 → 184. Окна тёплые — лампада. "
     "Прежний вариант (паперть на западе) — buildings/_backup_v1131/."),
    ("bld_izba_small_tes_kon", lambda: VL.izba_small("tes_kon"), (4, 4), "Малая изба — тёс, охлупень с конской головой",
     dict(wall=68, ridge=112, horse_top=124), {"izba_se": "+y → frame 0 (v1.13.2)"}, ""),
    ("bld_izba_small_dern", lambda: VL.izba_small("dern"), (4, 4), "Малая изба — дёрн по бересте, курная",
     dict(wall=68, ridge=112, vol_window="36–44"), {"izba_nw": "+y → frame 0", "milusha (v1.10 изба 17–20×26–29)": "+x → frame 1"},
     "Курная: только волоковые окошки, дым — fx_smoke_wisp в anchors_px.smoke"),
    ("bld_izba_small_tes_prich", lambda: VL.izba_small("tes_prich"), (4, 4), "Малая изба — светлый тёс, гладкий охлупень, причелины",
     dict(wall=68, ridge=112), {"izba_sw": "+x → frame 1 (v1.13.2)"}, "Окна с очельями-«кокошниками»; полотенце без знаков"),
    ("bld_izba_seni_tes", lambda: VL.izba_seni("tes"), (6, 4), "Изба с сенями — тёс",
     dict(wall=68, ridge=112, seni_wall=52, seni_ridge=84, seni_door=44), {"seni_ne": "+y → frame 0"},
     "Сени на восточном (+x) конце, ниже основного сруба, из серого старого леса; дверь в сени"),
    ("bld_izba_seni_dern", lambda: VL.izba_seni("dern"), (6, 4), "Изба с сенями — дёрн",
     dict(wall=68, ridge=112, seni_wall=52, seni_ridge=84, seni_door=44), {"seni_sw": "+x → frame 1"}, ""),
    ("bld_klet", VL.klet, (3, 3), "Клеть — без окон, дверь на засове с замком",
     dict(wall=60, ridge=96, door=56), {"klet_sw": "+x → frame 1"}, "Серый выветренный сруб"),
    ("bld_banya_dern", lambda: VL.banya("dern"), (3, 3), "Баня (мыльня) — дёрн, кадка у входа",
     dict(wall=60, ridge=96, door=53), {"banya_sw": "+x → frame 1 (v1.13.2)"}, "Тёмный закопчённый сруб, дым из волокового окна (anchors_px.smoke)"),
    ("bld_banya_tes", lambda: VL.banya("tes"), (3, 3), "Баня (мыльня) — тёс, кадка у входа",
     dict(wall=60, ridge=96, door=53), {"banya_se": "+y → frame 0"}, ""),
    ("bld_ambar", VL.ambar, (3, 3), "Амбар на камнях-стульях, мешки у двери",
     dict(stones=8, wall="8–60", ridge=96, door="12–56"), {"ambar_se": "+y → frame 0 (v1.13.2; +x упирается в тын x 39)"},
     "Стулья 8 px + сруб 52 → стена до 60 (как у клети); мешки и сходня у двери"),
]


P1 = [
    ("bld_izba_podklet", VL.izba_podklet, (5, 5), "Изба на подклете с крыльцом (H11)",
     dict(podklet=24, wall="24–88", ridge=132, horse_top=144, porch=26), {"podklet_nw": "+x (крыльцо к улице) — frame 0"},
     "Одна вариация: дверь верхнего яруса и крыльцо на +x, как в плане. Крыльцо и лестница выступают за футпринт на +x до ~0,9 тайла"),
    ("bld_hlev", VL.hlev, (4, 3), "Хлев с сенником (H12)", dict(wall=48, ridge=88), {"hlev_nw": "+x — frame 0"},
     "Дёрн, серый сруб, сено из-под кровли и на фронтоне, ворота для скота на +x. Плетень-загон — реквизит H18, отдельно (не сделан)"),
    ("bld_ambar_pier_tes", lambda: VL.ambar_pier("tes"), (4, 3), "Амбар у пристани — тёс (H13)",
     dict(piles=16, wall="17–57", ridge=88), {"ambar_p1": "+y — frame 0"}, "Сходни к воде выходят за футпринт на +y на 1,3 тайла"),
    ("bld_ambar_pier_dern", lambda: VL.ambar_pier("dern"), (4, 3), "Амбар у пристани — дёрн (H13)",
     dict(piles=16, wall="17–57", ridge=88), {"ambar_p2": "+y — frame 0"}, ""),
    ("bld_masterskaya", VL.masterskaya, (5, 4), "Мастерская косторезов (H14)",
     dict(wall=60, ridge=100, naves="54 у стены → 48 у столбов (52 по scale.md в среднем)", door=50), {"masterskaya": "+y (навес и дверь к камере) — frame 0"},
     "v1.13.2: сруб y+0..2,6, навес на столбах y 2,6..4 внутри футпринта (свес до 4,15), под навесом дверь, верстак, рога, "
     "корзина с гребнями. Прежний вариант (навес на −x) — buildings/_backup_v1131/."),
    ("bld_lavka", VL.lavka, (3, 2), "Лавка-навес (H15)", dict(posts=52, roof=64, counter=16), {"lavka_e": "+y (прилавок к торгу) — frame 0"},
     "Без стен. Конёк навеса 64 (навес 60 по scale.md — у карниза 50, конёк 64; в среднем ≈ 60)"),
]


def save_building(name, fn, AB, title, heights, ids, notes, MEAS):
    frames, meta = fn()
    A, B = AB
    n = len(frames)
    m = dict(object=title, footprint_tiles=[A, B], tile_px=[32, 16], heights_px=heights,
             pivot=meta["pivot"], pivot_rule="screen point of the footprint centre at z = 0 (scale.md §4.1)",
             proto_corner_px=meta["proto_corner_px"], footprint_px=meta["footprint_px"],
             front_corner_px=meta["front_corner_px"], placement=PLACE, sort=SORT, xray=XRAY,
             ridge_axis="world x (as prototype props.js izba)", anchors_px=meta["anchors_px"],
             ladoga_ids=ids, notes=notes, fps=0, loop=False)
    if n == 3 and name not in [p[0] for p in P1]:
        m["door_frames"] = {"+y": 0, "+x": 1}
        m["frame_2"] = "без видимой двери (задняя сторона); по GDD v1.13.2 двери только на +x/+y — для плана не использовать"
        m["frames"] = ["door on the +y wall (south, lit)", "door on the +x gable/wall (east)", "door on a hidden side (−x / −y): windows only"]
    elif name == "bld_church":
        m["door_frames"] = {"+y": 0}
    else:
        m["door_frames"] = "single frame, door as on the plan (see ladoga_ids)"
    X.save_sheet(frames, BLD, name, m)
    labels = ["дверь +y", "дверь +x", "дверь −x/−y"][:n]
    X.preview([[f] for f in frames], labels, os.path.join(BLD, "preview"), name, 1, True, meta["pivot"], title=title)
    MEAS[name] = dict(frame=[int(frames[0].shape[1]), int(frames[0].shape[0])], pivot=meta["pivot"], footprint=[A, B],
                      frames=n)
    return frames, meta


def fx(MEAS):
    out = os.path.join(ROOT, "fx_swing")
    rows = []
    for d in ("se", "ne", "s", "n"):
        fr = [VL.swing(d, i) for i in range(2)]
        X.save_sheet(fr, out, "fx_swing_%s" % d, dict(
            effect="«Сшибка»: след взмаха 120°, r 22 px (GDD v1.13 §12.1.7 H10)", direction=d,
            mirror_for={"se": "sw", "ne": "nw"}.get(d), pivot=list(VL.SW_PIV), fps=16, loop=False,
            timing="frame 0 on the hit frame of the strike, frame 1 next, then hide (≈ 0.12 s)",
            layer="S / SE: draw OVER the hero; N / NE: draw UNDER the hero (behind the body)",
            east_west="E uses SE, W uses SW (mirror of SE) — the arc is a ground ellipse, the 22° difference is not readable",
            arc="ellipse rx 22, ry 11 at 18 px above the feet (chest), band 0.42–1.0 of r (tapering to the tail); linen → birch → mist dither"))
        rows.append(fr)
    X.preview(rows + [[X.mirror(a) for a in rows[0]], [X.mirror(a) for a in rows[1]]], ["SE", "NE", "S", "N", "SW зерк.", "NW зерк."],
              os.path.join(out, "preview"), "fx_swing", 8, True, VL.SW_PIV, title="След «Сшибки» · 2 кадра")
    sm = [VL.smoke(i) for i in range(4)]
    out = os.path.join(ROOT, "fx_smoke_wisp")
    X.save_sheet(sm, out, "fx_smoke_wisp", dict(effect="дым из волокового окна / над баней (курная изба, бани)", pivot=list(VL.SM_PIV),
                 fps=5, loop=True, anchor="buildings' anchors_px.smoke (frame-specific); draw over the building, no ink outline"))
    X.preview([sm], ["цикл"], os.path.join(out, "preview"), "fx_smoke_wisp", 5, True, VL.SM_PIV, title="Дым · 4 кадра")
    MEAS["fx_swing"] = dict(frame=[VL.SW_W, VL.SW_H], pivot=list(VL.SW_PIV))


def gates(MEAS):
    import village_gates as G
    for side, state in (("e", "open"), ("s", "open"), ("n", "open"), ("n", "closed"), ("w", "open"), ("w", "closed")):
        out, meta = G.gate_sheets(side, state)
        axis, sin, (x0, y0) = G.GATES[side]
        name = "gate_%s_%s" % (side, state)
        common = dict(object="Ворота частокола Ладоги — %s, %s" % ({"e": "восточные (Залесье)", "s": "южные (пристань)",
                      "n": "северные (Сопки)", "w": "западные (Чёрный бор)"}[side], "открыты" if state == "open" else "закрыты"),
                      footprint_tiles=meta["footprint_tiles"], world_min_corner=[x0, y0], pivot=meta["pivot"],
                      proto_corner_px=meta["proto_corner_px"], footprint_px=meta["footprint_px"], front_corner_px=meta["front_corner_px"],
                      heights_px=dict(opening=72, posts=96, lintel="84–90", torches=48, bar=36 if state == "closed" else None),
                      replaces="the prototype palisade props of the 2 gatepost cells (a = 0 and a = 3 of the footprint) incl. "
                               "their torches and the lintel/disc drawn by the right gatepost",
                      anchors_px=meta["anchors_px"], torch_flame_px=meta["torch_flame_px"],
                      leaves=("open inward (toward the town, %s)" % ("−x" if side == "e" else "+x" if side == "w" else "+y" if side == "n" else "−y"))
                      if state == "open" else "closed in the wall plane, brus-засов on the inside face (camera side)",
                      sort="use the two segment sheets _A / _B, each sorted like a 1×1 palisade cell (scale.md §4.1: long objects in 1–2 tile segments); "
                           "the full sheet is for previews / static shots", segments=meta["segments"], xray=XRAY,
                      torch_light="code light r 3 tiles, flame colour, only when open", fps=8 if state == "open" else 0,
                      loop=state == "open", disc="plain bronze disc on the lintel, unchanged from the prototype (no rosette edits)")
        X.save_sheet(out["full"], BLD, name, common)
        for k in "AB":
            X.save_sheet(out[k], BLD, name + "_" + k, dict(common, segment=k, segment_info=meta["segments"][k]))
        X.preview([out["full"], out["A"], out["B"]], ["целиком", "сегмент A", "сегмент B"], os.path.join(BLD, "preview"), name,
                  8, True, meta["pivot"], title=common["object"])
        MEAS[name] = dict(frame=[int(out["full"][0].shape[1]), int(out["full"][0].shape[0])], pivot=meta["pivot"], frames=len(out["full"]))
    fr, meta = G.sign_frames()
    X.save_sheet(fr, BLD, "bld_ukazatel", dict(
        object="Указатель у торга (H6)", footprint_tiles=[1, 1], world_tile=[26, 18], pivot=meta["pivot"],
        proto_corner_px=meta["proto_corner_px"], footprint_px=meta["footprint_px"], front_corner_px=meta["front_corner_px"],
        heights_px=dict(post=56, boards="36–50 (E/W at 44–50, N/S at 36–42)"),
        frames=["M1: Залесье (+x) и Пристань (+y) светлые, Сопки (−y) и Бор (−x) тёмные", "после сдачи М1: + Сопки светлые",
                "после сдачи М2: все светлые"], frame_by_stage={"m1": 0, "m2.unlocked": 1, "m3.unlocked": 2},
        board_tips_px=meta["board_tips_px"], boards={"sign.zalesye": "+x", "sign.sopki": "−y", "sign.bor": "−x", "sign.pier": "+y"},
        captions="board labels are world captions by code (showRange 6), not baked", sort=SORT, fps=0, loop=False))
    X.preview([fr], ["М1 / М2 / М3"], os.path.join(BLD, "preview"), "bld_ukazatel", 1, True, meta["pivot"], title="Указатель")
    MEAS["bld_ukazatel"] = dict(frame=[int(fr[0].shape[1]), int(fr[0].shape[0])], pivot=meta["pivot"], frames=3)


def pavement(MEAS):
    tiles = [VL.pave_tile("x", 1), VL.pave_tile("x", 2), VL.pave_tile("y", 3), VL.pave_tile("y", 4)]
    edges = [VL.pave_tile("x", 5, "ne"), VL.pave_tile("x", 6, "sw"), VL.pave_tile("y", 7, "nw"), VL.pave_tile("y", 8, "se")]
    out = os.path.join(ROOT, "tiles")
    X.save_sheet(tiles, out, "tile_mostovaya", dict(object="мостовая из плах (H16)", frame_size=[32, 16], pivot=[16, 8],
                 frames=["road along x (W–E), var 1", "along x, var 2", "road along y (N–S), var 1", "along y, var 2"],
                 placement="same as prototype ground tiles: top vertex of the diamond at w2s(x, y)", fps=0, loop=False))
    X.save_sheet(edges, out, "tile_mostovaya_edge", dict(object="край мостовой: бревно-бордюр (H16)", frame_size=[32, 16], pivot=[16, 8],
                 frames=["along x, curb on the north side (−y)", "along x, curb on the south side (+y)",
                         "along y, curb on the west side (−x)", "along y, curb on the east side (+x)"],
                 placement="use on the outermost row of a pavement rect; GDD pavement rects [[22,23,4,18],[25,20,23,4]]", fps=0, loop=False))
    X.preview([tiles, edges], ["плахи", "края"], os.path.join(out, "preview"), "tile_mostovaya", 1, True, (16, 8), title="Мостовая")
    MEAS["tile_mostovaya"] = dict(frame=[32, 16], tiles=4, edges=4)


PROPS = [("prop_stog", VL.prop_stog, (1, 1), "Стог сена у шеста (H18)", dict(stack=40, pole=48)),
         ("prop_kadka", VL.prop_kadka, (1, 1), "Кадка у бани (H18), 12×16", dict(height=16)),
         ("prop_roga", VL.prop_roga, (1, 1), "Связка рогов у мастерской (H18)", dict(height=20)),
         ("prop_telega_broken", VL.prop_telega_broken, (3, 2), "Телега без колеса (H18)", dict(body="6–22", wheel=24))]


def props(MEAS):
    for name, fn, (A, B), title, hh in PROPS:
        frames, meta = fn()
        X.save_sheet(frames, BLD, name, dict(object=title, footprint_tiles=[A, B], heights_px=hh, pivot=meta["pivot"],
                     proto_corner_px=meta["proto_corner_px"], footprint_px=meta["footprint_px"], front_corner_px=meta["front_corner_px"],
                     placement=PLACE, sort=SORT, fps=0, loop=False, notes="yard prop, 2–4 per yard, not on roads (GDD §7.1.1)"))
        X.preview([frames], [title.split(" (")[0]], os.path.join(BLD, "preview"), name, 1, True, meta["pivot"], title=title)
        MEAS[name] = dict(frame=[int(frames[0].shape[1]), int(frames[0].shape[0])], pivot=meta["pivot"])


def run(MEAS):
    out = {}
    for b in BUILDINGS + P1:
        out[b[0]] = save_building(*b, MEAS)
    gates(MEAS)
    fx(MEAS)
    pavement(MEAS)
    props(MEAS)
    import npc_priest
    MEAS["npc_priest_idle"] = npc_priest.run()
    return out


if __name__ == "__main__":
    M = {}
    run(M)
    print(json.dumps(M, ensure_ascii=False, indent=0))

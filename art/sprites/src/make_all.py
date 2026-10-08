"""Build all sprites/effects: python3 make_all.py
Writes /workspace/game/art/sprites/<character|effect>/... + sprites_report.json"""
import os
import json
import numpy as np
import rig
import export as X
import arsonist as AR
import axeman as AX
import zguba as ZG
import effects as FX
import make_rest  # GDD v1.7 §12.1.5 rest fx (fx_rest_*, fx_safe_ring)
import make_m1b   # M1 milestone (b): krivsha, mara, ognishche, idol_perun, fx_krivsha_*, fx_mara_*

ROOT = X.ROOT
VIEWS = ("se", "ne")
MIRROR = {"se": "sw", "ne": "nw"}
MEAS = {}
RU = {"idle": "покой", "walk": "ходьба", "torch_throw": "бросок факела", "axe_strike": "удар топором", "hurt": "урон",
      "death": "гибель", "cast": "ведовство", "raise_fallen": "подъём павших"}


def char_set(slug, title, mod, kind_kw, body_fn, notes, extra_meta=None):
    out = os.path.join(ROOT, slug)
    MEAS[slug] = {}
    for (anim, n, fps, loop, fn) in mod.ANIMS:
        rows, labels = [], []
        per_view = {}
        for v in VIEWS:
            sprs = [mod.frame(fn, i, v, **kind_kw) for i in range(n)]
            idxs = [rig.to_index(s) for s in sprs]
            hs = [rig.height(a) for a in idxs]
            meta = dict(character=title, animation=anim, direction=v, mirror_for=MIRROR[v],
                        mirror_rule="flip horizontally around the frame centre line x = 32.0; pivot stays (32, 56)",
                        pivot=list(rig.PIVOT), fps=fps, loop=loop, visible_height_px=hs,
                        height_rule="pivot row (soles) to the top visible pixel, outline included", notes=notes)
            if extra_meta:
                meta.update(extra_meta(anim, sprs, v))
            X.save_sheet(idxs, out, "%s_%s_%s" % (slug, anim, v), meta)
            per_view[v] = idxs
            MEAS[slug]["%s_%s" % (anim, v)] = hs
        rows = [per_view["se"], per_view["ne"], [X.mirror(a) for a in per_view["se"]], [X.mirror(a) for a in per_view["ne"]]]
        labels = ["SE", "NE", "SW зерк.", "NW зерк."]
        X.preview(rows, labels, os.path.join(out, "preview"), "%s_%s" % (slug, anim), fps, loop, rig.PIVOT, shadow_w=18,
                  title="%s · %s · %d кадр. · %d кадр./с" % (title, RU[anim], n, fps))
    # body height without held items
    MEAS[slug]["body_only"] = body_fn()


def arsonist_meta(anim, sprs, v):
    m = dict(anchors=dict(torch_flame_root=[None if s["torch_root"] is None else [round(s["torch_root"][0], 1), round(s["torch_root"][1], 1)] for s in sprs]),
             torch_flame="baked into the frames (phase = frame % 6); for an independent 6-frame flame loop overlay "
                         "arsonist_torch_flame at anchors.torch_flame_root")
    if anim == "torch_throw":
        rr = sprs[AR.THROW_RELEASE - 1]["torch_root"]
        m["events"] = {"release_frame": AR.THROW_RELEASE,
                       "spawn_effect": "fx_torch_flight", "spawn_at_px": [round(rr[0], 1), round(rr[1], 1)],
                       "note": "torch leaves the hand between frames 2 and 3 (0-based); telegraph 0.8 s (red circle) per GDD E11"}
    if anim == "axe_strike":
        m["events"] = {"hit_frame": 3, "arc_deg": 90}
    if anim == "death":
        m["events"] = {"torch_drops_frame": 2, "torch_out_frame": 7}
    return m


def zguba_meta(anim, sprs, v):
    if anim == "cast":
        return {"events": {"release_frame": ZG.CAST_RELEASE, "spawn_effect": "зелёный огонь прислужника (GDD §12.1.5, not in this set)"}}
    if anim == "raise_fallen":
        return {"events": {"staff_strike_frame": 2, "raise_target_frame": 3}}
    return {}


def arsonist_body():
    r = {}
    for v in VIEWS:
        r[v] = rig.height(rig.to_index(AX.draw(AR.idle(0), v, "arsonist", with_torch=False)))
    # torch raised (throw frame 1) incl. the flame
    r["torch_raised_max"] = max(rig.height(rig.to_index(AR.frame(AR.throw, i, v))) for v in VIEWS for i in range(2))
    return r


def zguba_body():
    r = {}
    for v in VIEWS:
        p = ZG.idle(0); p["staff"] = None
        r[v] = rig.height(rig.to_index(ZG.draw(p, v, "zguba")))
        r["staff_" + v] = rig.height(rig.to_index(ZG.frame(ZG.idle, 0, v)))
    return r


def base_refs():
    """Reference stills of the two bases designed for this task (no sprites existed)."""
    out = os.path.join(ROOT, "base_ref")
    frames, labels = [], []
    meas = {}
    for v in VIEWS:
        a = rig.to_index(AX.draw(AR.idle(0), v, "axeman", with_torch=False)); frames.append(a)
        meas["axeman_" + v] = rig.height(a)
    for v in VIEWS:
        a = rig.to_index(ZG.frame(ZG.idle, 0, v, kind="servant")); frames.append(a)
        p = ZG.idle(0); p["staff"] = None
        meas["servant_" + v] = rig.height(a); meas["servant_body_" + v] = rig.height(rig.to_index(ZG.draw(p, v, "servant")))
    X.save_sheet(frames, out, "base_ref_axeman_servant",
                 dict(character="Черноярец-топорщик (2 кадра: se, ne) и Волхв-прислужник (2 кадра: se, ne)", animation="idle still",
                      pivot=list(rig.PIVOT), visible_height_px=[meas[k] for k in ("axeman_se", "axeman_ne", "servant_se", "servant_ne")],
                      notes="Bases designed for this task (no топорщик / прислужник sprite existed). "
                            "Топорщик: dark-grey shirt, steel accents (v2 recolour 08.10). Поджигатель = this топорщик recoloured (soot-grey, ember stripes) + torch; Згуба = this прислужник + wolf hood, beads, horse-skull staff."))
    X.preview([frames[:2], frames[2:]], ["Топорщик", "Прислужник"], os.path.join(out, "preview"), "base_ref", 1, True, rig.PIVOT,
              shadow_w=18, title="Базы · 46")
    MEAS["base_ref"] = meas


def flame_loop():
    """Separate 6-frame torch flame (16x24, root pivot (8,21)) for engine overlay."""
    import human as Hm
    fr = []
    for ph in range(6):
        P = rig.Painter()
        rig.flame(P, (0.0, -1.0), ph, h=9, w=5.2)
        idx = rig.to_index(rig.build(P, rig.BASE))
        fr.append(idx[56 - 22:56 + 2, 32 - 8:32 + 8])
    out = os.path.join(ROOT, "arsonist")
    X.save_sheet(fr, out, "arsonist_torch_flame", dict(character="Черноярец-поджигатель", animation="torch flame loop",
                 pivot=[8, 22], fps=10, loop=True, notes="optional overlay; root = pivot; matches the baked flame"))
    X.preview([fr], ["пламя"], os.path.join(out, "preview"), "arsonist_torch_flame", 10, True, (8, 22), title="Пламя факела · 6")


def effects():
    tf = FX.torch_flight()
    out = os.path.join(ROOT, "fx_torch_flight")
    X.save_sheet(tf, out, "fx_torch_flight", dict(effect="Поджигатель: полёт факела", direction="travels to +x (screen right)",
                 mirror_for="travel to -x", pivot=[16, 16], fps=12, loop=True,
                 notes="spins 90 deg per frame; flame streams back; draw the engine shadow on the ground under the arc"))
    X.preview([tf, [X.mirror(a) for a in tf]], ["→", "← зерк."], os.path.join(out, "preview"), "fx_torch_flight", 12, True, (16, 16),
              title="Полёт факела · 4")
    bg = FX.burning_ground()
    out = os.path.join(ROOT, "fx_burning_ground")
    tops = [int(np.where((a >= 0).any(1))[0].min()) for a in bg]
    X.save_sheet(bg, out, "fx_burning_ground", dict(effect="Поджигатель: горящая земля Ø 2 тайла", pivot=[32, 24], fps=10, loop=True,
                 footprint="ellipse 64x32 = circle of 2 tiles (tile 32x16), centre = pivot",
                 layer="ground decal, drawn under characters (scale.md §4.1)", duration_s=4,
                 flame_max_height_px=FX.BG_FLAME_MAX,
                 notes="telegraph 0.8 s before (red circle, GDD E11) is a separate effect"))
    X.preview([bg], ["цикл"], os.path.join(out, "preview"), "fx_burning_ground", 10, True, (32, 24), title="Горящая земля · 6")
    MEAS["fx_burning_ground"] = dict(flame_max=FX.BG_FLAME_MAX, frame=[64, 40], top_row=min(tops))
    sc = FX.rift_scar()
    out = os.path.join(ROOT, "fx_rift_scar")
    core = [(a == rig.pk.C["nebyl"]) | (a == rig.pk.C["linen"]) for a in sc]
    rows = np.where(core[0].any(1))[0]
    widths = [int(c.sum(1)[r]) for c in core[:1] for r in rows]
    X.save_sheet(sc, out, "fx_rift_scar", dict(effect="Шрам на месте Разлома (финал М3)", pivot=[48, 104], fps=8, loop=True,
                 notes="decor, passable; same 96x112 cell as the Разлом; glow nebyl, core 2-4 px"))
    X.preview([sc], ["цикл"], os.path.join(out, "preview"), "fx_rift_scar", 8, True, (48, 104), title="Шрам Разлома · 6")
    MEAS["fx_rift_scar"] = dict(scar_height=int(104 - rows.min() + 1), core_width_min=min(FX.SCAR_W), core_width_max=max(FX.SCAR_W))
    MEAS["fx_torch_flight"] = dict(frame=[32, 32])


if __name__ == "__main__":
    char_set("arsonist", "Черноярец-поджигатель", AR, {}, arsonist_body,
             "Recolour of the черноярец-топорщик (base designed here) + torch in the LEFT hand. Body 46, raised torch with flame <= 56. Colours (v2 recolour 08.10): soot-grey shirt with smouldering ember stripes; red is reserved for the hero (scale.md §4.4).",
             arsonist_meta)
    char_set("zguba", "Згуба", ZG, {}, zguba_body,
             "Based on the волхв-прислужник (designed here): wolf-skin hood (ears in the 46 px), bone beads, horse-skull staff "
             "(57 px: 58 does not fit a 64x64 frame with pivot y 56).", zguba_meta)
    flame_loop()
    base_refs()
    effects()
    make_rest.run(MEAS)
    make_m1b.run(MEAS)
    X.REPORT["measures"] = MEAS
    with open(os.path.join(ROOT, "sprites_report.json"), "w") as f:
        json.dump(X.REPORT, f, ensure_ascii=False, indent=1)
    print(json.dumps(MEAS, ensure_ascii=False)[:4000])

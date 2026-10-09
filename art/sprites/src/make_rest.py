"""Rest-in-safe-zone effects (GDD v1.7 §12.1.5) -> fx_rest_krada/, fx_rest_churov/,
fx_rest_campfire/, fx_rest_sparks/, fx_safe_ring/ + composite review preview.
Called from make_all.py (run(MEAS)); can also run alone: python3 make_rest.py"""
import os
import json
import numpy as np
from PIL import Image
import rig
import pixelkit as pk
from pixelkit import C
import export as X
import effects_rest as R

ROOT = X.ROOT
FIRE_IDX = {C["red"], C["red_lt"], C["ember"], C["flame"], C["linen"]}


def _top(frames, piv_y, only=None):
    tops = []
    for a in frames:
        m = a >= 0 if only is None else np.isin(a, list(only))
        rows = np.where(m.any(1))[0]
        tops.append(int(piv_y - rows.min() + 1) if len(rows) else 0)
    return tops


def _flame_heights(shape, cx, base_y, hw, h, piv_y, bright, seed=0.0):
    """Height from the ground of the flame body (no detached sparks), per frame."""
    out = []
    for i in range(6):
        f = R.fire_field(shape, cx, base_y, hw, h, i, bright=bright, seed=seed)
        body = np.isin(f, [C["ember"], C["flame"], C["linen"]])
        cols = body.sum(1)
        rows = np.where(cols >= 2)[0]                      # ignore 1-px licks
        out.append(int(piv_y - rows.min() + 1))
    return out


def two_state(folder, slug, title, idle, rest, pivot, fps, meta_common, extra_anchor=None):
    out = os.path.join(ROOT, folder)
    for st, frs in (("idle", idle), ("rest", rest)):
        meta = dict(meta_common)
        meta.update(state=st, pivot=list(pivot), fps=fps, loop=True,
                    states={"idle": slug + "_idle.png", "rest": slug + "_rest.png"},
                    state_switch="rest while the hero stands in the zone and Жизнь/Удаль regenerate "
                                 "(2 s without damage, GDD §4.5); both loops are phase-aligned, so switch at the "
                                 "same frame index without a pop; back to idle when regen stops")
        if extra_anchor:
            meta["anchors"] = extra_anchor
        X.save_sheet(frs, out, slug + "_" + st, meta)
    X.preview([idle, rest], ["покой", "отдых"], os.path.join(out, "preview"), slug, fps, True, pivot, title=title)


def ground(W, H, seed=0, lit=None):
    """Night earth of Залесье for the review images (palette indices)."""
    b = pk.bayer(H, W)
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    n = np.zeros((H, W))
    for k in range(6):
        fx, fy, ph = rng.uniform(0.01, 0.05), rng.uniform(0.02, 0.09), rng.uniform(0, 6.3)
        n += np.sin(xx * fx + yy * fy + ph)
    n /= 6
    g = np.full((H, W), C["wood_dk"], np.int16)
    g[(n > 0.15) & (b < 0.35)] = C["wood"]
    g[(n < -0.25) & (b < 0.5)] = C["night"]
    grass = (n > 0.42) & (b < 0.6)
    g[grass] = C["pine_dk"]
    g[grass & (b < 0.15)] = C["pine"]
    if lit is not None:                 # warm light pool around a fire (cx, cy, rx, ry)
        cx, cy, rx, ry = lit
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        g[(d < 1.0) & (b < 0.30) & (g == C["wood_dk"])] = C["wood"]
        g[(d < 0.45) & (b < 0.22)] = C["wood_md"]
        g[(d < 0.2) & (b < 0.10)] = C["bronze_dk"]
    return g


def _paste(dst, spr, x0, y0):
    h, w = spr.shape
    H, W = dst.shape
    ys, xs = slice(max(0, y0), min(H, y0 + h)), slice(max(0, x0), min(W, x0 + w))
    sub = spr[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]
    m = sub >= 0
    dst[ys, xs][m] = sub[m]


def _save_idx(arr, path, scale=3):
    im = Image.fromarray(X.rgba(arr)[..., :3], "RGB").resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.NEAREST)
    im.save(path)
    cols = {tuple(c) for c in np.array(im).reshape(-1, 3)}
    assert cols <= X.PAL, path
    return path


def _save_gif(frames, path, fps, scale=3):
    ims = []
    for a in frames:
        im = Image.fromarray(np.where(a >= 0, a, C["night"]).astype(np.uint8), "P")
        im.putpalette([int(v) for v in pk.RGB.reshape(-1)] + [0] * (768 - pk.RGB.size))
        ims.append(im.resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=int(round(1000 / fps)), loop=0, disposal=1, optimize=False)


def label(cv_arr, x, y, s):
    cv = pk.Canvas(cv_arr.shape[1], cv_arr.shape[0])
    cv.a[:] = cv_arr
    X.label(cv, x, y, s)
    cv_arr[:] = cv.a


def run(MEAS):
    # ---- 1. костёр ------------------------------------------------------------------
    ki, kr = R.krada("idle"), R.krada("rest")
    kp = R.KR_PIV
    fl_i = _flame_heights(ki[0].shape, kp[0] - 0.5, kp[1] - 22, 11.5, R.KR_FLAME["idle"], kp[1], 0.0)
    fl_r = _flame_heights(ki[0].shape, kp[0] - 0.5, kp[1] - 22, 13.5, R.KR_FLAME["rest"], kp[1], 0.8)
    two_state("fx_rest_krada", "fx_rest_krada", "Костёр · покой / отдых · 6+6", ki, kr, kp, 10, dict(
        effect="Костёр (обережный огонь Залесья, бывш. «крада»), безопасная зона r = 10 тайлов: покой и отдых героя",
        object="full object sprite (stone ring + log crib + flame); replaces the static костёр in the tileset",
        footprint="2x2 tiles (64x32 diamond), centre = pivot; stone ring r 20x10 px (scale.md §3.3, §5 п.7)",
        sizes_px=dict(log_crib=24, flame_idle_from_ground=max(fl_i), flame_rest_from_ground=max(fl_r),
                      sparks_rest_top_from_ground=max(_top(kr, kp[1]))),
        layer="sorted by pivot y like other objects (scale.md §4.1)",
        light_hint="engine light at the flame root, warm (flame/ember); radius idle ≈ 3 tiles, rest ≈ 4 tiles, +25% intensity",
        notes="idle: steady flame to 72 px; rest: higher (to 86), hotter core, ember sparks, fire-lit stone tops. "
              "The 96-px pillar of the ritual (scale.md) is not used for rest."),
        extra_anchor={"flame_root": [kp[0], kp[1] - 24], "sparks_origin": [kp[0], kp[1] - 50]})
    MEAS["fx_rest_krada"] = dict(frame=[R.KR_W, R.KR_H], pivot=list(kp), flame_idle=fl_i, flame_rest=fl_r,
                                 total_top_idle=_top(ki, kp[1]), total_top_rest=_top(kr, kp[1]))
    # ---- 2. Путевой камень ----------------------------------------------------------------
    ci, cr = R.churov("idle"), R.churov("rest")
    cp = R.CH_PIV
    stone_h = _top([np.where(np.isin(ci[0], [C["bronze"], C["bronze_dk"], C["bronze_lt"]]) | (ci[0] >= 0), ci[0], -1)], cp[1])[0]
    two_state("fx_rest_churov", "fx_rest_churov", "Путевой камень · покой / отдых · 6+6", ci, cr, cp, 8, dict(
        effect="Путевой камень, безопасная зона r = 6 тайлов: насечки тлеют (покой) и светятся (отдых)",
        object="full object sprite (stone + насечки); the same stone is the waystone (GDD §8.1)",
        footprint="1x1 tile (32x16 diamond), centre = pivot; stone 24x40 (scale.md §3.4)",
        sizes_px=dict(stone_height=stone_h, stone_width=24),
        runes="plain notches on the face (two long cuts, four short notches, one long cut; rename_map §5: no runes, no idol face); idle bronze_dk/bronze/bronze_lt wave, "
              "rest bronze_hi + linen flicker + bronze halo on the stone + rising bronze motes",
        light_hint="optional engine light: bronze_lt, radius 1.5 tiles, only in rest"),
        extra_anchor={"runes_centre": [cp[0], cp[1] - 22], "motes_origin": [cp[0], cp[1] - 34]})
    MEAS["fx_rest_churov"] = dict(frame=[R.CH_W, R.CH_H], pivot=list(cp), stone_height=stone_h,
                                  total_top_rest=_top(cr, cp[1]))
    # ---- 3. костёр М3 ----------------------------------------------------------------------
    fi, fr = R.campfire("idle"), R.campfire("rest")
    fp = R.CF_PIV
    cf_i = _flame_heights(fi[0].shape, fp[0] - 0.5, fp[1] - 6, 5.5, R.CF_FLAME["idle"], fp[1], 0.0, 1.0)
    cf_r = _flame_heights(fi[0].shape, fp[0] - 0.5, fp[1] - 6, 6.5, R.CF_FLAME["rest"], fp[1], 0.8, 1.0)
    two_state("fx_rest_campfire", "fx_rest_campfire", "Костёр М3 · покой / отдых · 6+6", fi, fr, fp, 10, dict(
        effect="Костёр у поваленного чёрного идола (М3), безопасная зона r = 6 тайлов",
        interpretation="GDD §8.4: the campfire «работает как путевой камень», and §12.1.5 groups it with the stone "
                       "(«насечки тлеют bronze»). So it is a small сторожевой костёр (scale.md §3.3: firewood 8, flame 20-24) "
                       "inside a ring of 8 stones with насечки; the насечки behave like the путевой камень and the fire "
                       "grows a little in rest (≈23 -> ≈30 px) with sparks",
        footprint="1x1 tile; stone ring r 18x9 px (stones 5x5), centre = pivot",
        sizes_px=dict(firewood=8, flame_idle_from_ground=max(cf_i), flame_rest_from_ground=max(cf_r)),
        light_hint="engine light warm, radius idle ≈ 2 tiles, rest ≈ 2.5 tiles"),
        extra_anchor={"flame_root": [fp[0], fp[1] - 8]})
    MEAS["fx_rest_campfire"] = dict(frame=[R.CF_W, R.CF_H], pivot=list(fp), flame_idle=cf_i, flame_rest=cf_r)
    # ---- 4. hero sparks --------------------------------------------------------------------
    hs = R.hero_sparks()
    out = os.path.join(ROOT, "fx_rest_sparks")
    X.save_sheet(hs, out, "fx_rest_sparks", dict(
        effect="Тёплые искры над героем, пока растёт Жизнь (отдых в безопасной зоне)",
        pivot=list(R.HS_PIV), fps=8, loop=True,
        anchors={"attach": "hero pivot (the frame is the hero's own 64x64 cell, pivot (32,56))"},
        colours="bronze, bronze_lt, bronze_hi, flame, linen only; no red/red_lt/red_dk/ember (red is the hero's accent, scale.md §4.4)",
        layer="drawn over the hero sprite; play only while Жизнь or Удаль is rising, stop (let the loop finish) when full",
        sparks_band_px=[14, 56]))
    X.preview([hs], ["цикл"], os.path.join(out, "preview"), "fx_rest_sparks", 8, True, R.HS_PIV, shadow_w=18,
              title="Искры отдыха над героем · 4")
    MEAS["fx_rest_sparks"] = dict(frame=[R.HS_W, R.HS_H], pivot=list(R.HS_PIV),
                                  colours_used=sorted({pk.PALETTE_NAMES[c] if hasattr(pk, "PALETTE_NAMES") else int(c)
                                                       for a in hs for c in np.unique(a) if c >= 0}))
    # ---- 5. zone ring ------------------------------------------------------------------------
    out = os.path.join(ROOT, "fx_safe_ring")
    for st in ("dim", "lit"):
        X.save_sheet(R.groove_pieces(st), out, "fx_safe_ring_grooves_" + st, dict(
            effect="Граница безопасной зоны: бороздка с двумя насечками", state=st, pivot=list(R.GR_PIV),
            frames_are="tangent directions: frame b = screen angle b*22.5 deg (counter-clockwise from +x, y down); 0 = horizontal",
            fps=0, loop=False, layer="ground decal under characters"))
        X.save_sheet(R.rune_pieces(st), out, "fx_safe_ring_runes_" + st, dict(
            effect="Граница безопасной зоны: насечка на земле (2:1)", state=st, pivot=list(R.RU_PIV),
            frames_are="4 notch-group variants (3, 2, 4, 2 wide), not rotated", fps=0, loop=False, layer="ground decal under characters"))
    lay10, per10 = R.ring_layout(10)
    lay6, per6 = R.ring_layout(6)
    master = dict(
        effect="Кольцо насечек на границе безопасной зоны (GDD §4.5, §12.1.5)",
        pieces={"groove": {"dim": "fx_safe_ring_grooves_dim.png", "lit": "fx_safe_ring_grooves_lit.png",
                           "frame_size": [R.GR_W, R.GR_H], "pivot": list(R.GR_PIV), "count": 8},
                "rune": {"dim": "fx_safe_ring_runes_dim.png", "lit": "fx_safe_ring_runes_lit.png",
                         "frame_size": [R.RU_W, R.RU_H], "pivot": list(R.RU_PIV), "count": 4}},
        states={"dim": "dark grooves, shown at 50% when the hero is within 3 tiles of the border", "lit": "bronze, while the hero rests inside"},
        placement=dict(
            centre="zone centre = pivot of the костёр Залесья / путевой камень / костёр М3 (ground point, screen px)",
            ellipse="ground circle of radius R tiles -> screen ellipse rx = R*16*sqrt(2) = R*22.627, ry = R*8*sqrt(2) = R*11.314 (scale.md §1: 22.6 / 11.3 px per tile)",
            algorithm=["sample the ellipse x = rx*cos(t), y = ry*sin(t); accumulate arc length; perimeter P",
                       "n = round(P / %g) pieces; piece k sits at arc length k*P/n" % R.SPACING_PX,
                       "k %% %d == 2 -> rune, index (k // %d) %% 4; otherwise groove" % (R.RUNE_EVERY, R.RUNE_EVERY),
                       "groove index b = round(((atan2(-dy/dt, dx/dt) in degrees) mod 180) / 22.5) mod 8, where (dx/dt, dy/dt) = (-rx*sin t, ry*cos t)",
                       "draw each piece with its pivot at (centre.x + round(x), centre.y + round(y))"],
            reference_impl="sprites/src/effects_rest.py: ring_layout(radius_tiles), assemble_ring()",
            spacing_px=R.SPACING_PX, rune_every=R.RUNE_EVERY),
        render_hint=dict(opacity=0.5,
                         visible_when="the hero is within 3 tiles of the border (inside or outside) OR is resting in the zone; "
                                      "otherwise hidden (GDD v1.7.1 §12.1.5 engine rule)",
                         state_rule="dim while visible; lit while the hero rests inside",
                         sort="ground decal layer, under characters and objects"),
        layouts={"R10": dict(radius_tiles=10, used_by="костёр / точка возрождения", perimeter_px=round(per10, 1),
                              count=len(lay10), pieces=lay10),
                 "R6": dict(radius_tiles=6, used_by="Путевой камень, костёр М3", perimeter_px=round(per6, 1),
                             count=len(lay6), pieces=lay6)},
        palette="palette_v2", alpha="0/255 only")
    with open(os.path.join(out, "fx_safe_ring.json"), "w") as f:
        json.dump(master, f, ensure_ascii=False, indent=1)
    X.preview([R.groove_pieces("dim"), R.groove_pieces("lit")], ["тускло", "отдых"], os.path.join(out, "preview"),
              "fx_safe_ring_grooves", 2, True, R.GR_PIV, title="Бороздки · 8 направлений")
    X.preview([R.rune_pieces("dim"), R.rune_pieces("lit")], ["тускло", "отдых"], os.path.join(out, "preview"),
              "fx_safe_ring_runes", 2, True, R.RU_PIV, title="Насечки · 4")
    # assembled ring R=6 on ground: dim | lit, and GIF toggling
    W6, H6 = int(2 * 6 * R.PX_PER_TILE_X) + 40, int(2 * 6 * R.PX_PER_TILE_Y) + 40
    asm = []
    for st in ("dim", "lit"):
        g = ground(W6, H6, seed=3)
        _paste(g, R.assemble_ring(6, st, (W6, H6), (W6 // 2, H6 // 2), lay6), 0, 0)
        _paste(g, ci[0] if st == "dim" else cr[0], W6 // 2 - cp[0], H6 // 2 - cp[1])
        asm.append(g)
    both = np.concatenate([asm[0], np.full((H6, 4), C["night"], np.int16), asm[1]], 1)
    _save_idx(both, os.path.join(out, "preview", "fx_safe_ring_R6_x3.png"))
    _save_gif(asm, os.path.join(out, "preview", "fx_safe_ring_R6.gif"), 1)
    MEAS["fx_safe_ring"] = dict(R10_count=len(lay10), R6_count=len(lay6), R10_rx_ry=[226.3, 113.1], R6_rx_ry=[135.8, 67.9])
    # ---- 6. composite review: костёр (rest) + hero + sparks + ring ----------------------------
    CW, CH = 480, 270
    kc = (240, 112)
    import sys as _sys
    _sys.path.insert(0, "/workspace/game/art/teaser/src")
    import teaser_sprites as _TS                      # hero idle pose (sword lowered), read-only import
    hero = pk.sprite_to_index(_TS.hero_pose("idle"))[:, ::-1].copy()   # mirrored: faces the костёр (left)
    hero_at = (300, 158)
    frames = []
    ring = R.assemble_ring(10, "lit", (CW, CH), kc, lay10)
    for i in range(12):
        g = ground(CW, CH, seed=1, lit=(kc[0], kc[1], 90, 45))
        _paste(g, ring, 0, 0)
        yy, xx = np.mgrid[0:CH, 0:CW]
        sh = (((xx - hero_at[0] + 0.5) / 9.0) ** 2 + ((yy - hero_at[1]) / 3.5) ** 2) <= 1
        g[sh] = C["night"]
        _paste(g, kr[i % 6], kc[0] - kp[0], kc[1] - kp[1])
        _paste(g, hero, hero_at[0] - 32, hero_at[1] - 56)
        _paste(g, hs[i % 4], hero_at[0] - R.HS_PIV[0], hero_at[1] - R.HS_PIV[1])
        frames.append(g)
    comp = frames[0].copy()
    label(comp, 4, 3, "Отдых у костра: костёр «отдых», герой 44 px, искры, кольцо r = 10 (насечки «отдых»)")
    cdir = os.path.join(ROOT, "fx_rest_krada", "preview")
    p = _save_idx(comp, os.path.join(cdir, "rest_composite_x3.png"))
    _save_gif(frames, os.path.join(cdir, "rest_composite.gif"), 10)
    MEAS["rest_composite"] = dict(path=os.path.relpath(p, ROOT), native=[CW, CH],
                                  hero_distance_tiles=round(np.hypot((hero_at[0] - kc[0]) / R.PX_PER_TILE_X,
                                                                     (hero_at[1] - kc[1]) / R.PX_PER_TILE_Y) , 2))
    return MEAS


if __name__ == "__main__":
    M = run({})
    print(json.dumps(M, ensure_ascii=False)[:3000])

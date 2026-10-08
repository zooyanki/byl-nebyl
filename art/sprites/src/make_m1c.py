"""Mission 1, milestone (c): the last grey boxes of the prototype —
Упырь (upyr/), Береста возврата (item_beresta/: bag icon + ground pickup), Чуров проход (fx_chur_portal/),
scene previews (m1c_scenes/). Called from make_all.py (run(MEAS)); can also run alone: python3 make_m1c.py"""
import os
import sys
import json
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
import export as X
import bigrig
import make_m1b as M
import upyr as UP
import beresta as BE
import chur_portal as CP
import fx_m1b as F
import krivsha as KV
from make_rest import ground, _paste, _save_idx, _save_gif, label

ROOT = X.ROOT
M.RU.update({"attack": "удар", "rise": "подъём из земли"})


def _hs(frames, py):
    return [bigrig.height(a, py) for a in frames]


def run(MEAS):
    # ================================================================ Упырь
    up_notes = ("Упырь (GDD §5.2 E2; act1: мертвец, вставший из могилы, медленный, бьёт больно, ходит толпой). One sprite for "
                "the Залесье packs, the ambush waves (rise from the ground) and Кривша's summons. Hunched grave-ghoul "
                "(concept: art/ui/src/sprites_rus.upyr): head pushed forward under the hump, grey-blue dead skin, ribs, sunken "
                "sockets with yellow embers, hanging jaw with fangs, long arms with bone claws, rotten brown shroud over the "
                "back + loin rag, rot (nebyl_dk), blood only red_dk. Body 37-39 hunched (scale.md 40, def.height 40), "
                "frame 64x64, pivot (32,56).")
    up_events = {
        "attack": {"hit_frame": UP.ATTACK_HIT, "telegraph_frames": [0, 2],
                   "sync": "attackTime 1.8 s, hitAt 0.6 s (monsters.json): 6 frames at 5 fps, frame 3 (the smash) starts at "
                           "exactly 0.6 s; the anim ends at 1.2 s, hold idle for the rest of attackTime. Heavy two-handed "
                           "overhead blow (GDD: «редкий тяжёлый удар»), dirt kicked up at the claws on frames 3-4"},
        "walk": {"note": "slow shamble (speed 2.5 tiles/s): 8 frames @10, 2 steps per cycle; raise fps with speed for "
                         "elites (Прыткий +30% -> 13 fps)"},
        "hurt": {"note": "2 frames, head snaps back; play over idle/walk"},
        "death": {"collapse_frames": [0, 3], "nebyl_wisp_frames": [4, 6],
                  "note": "recoils, buckles, falls on its face; the Небыль leaves the body as a small green wisp (4-6); "
                          "last frame holds (corpse, the engine fades it out)"},
        "rise": {"frames": "0 a clawed hand breaks the ground, 1 head and both hands, 2 head and shoulders, 3 waist-deep, "
                           "4 climbs out on one knee, 5 stands shaking the earth off (≈ idle 0)",
                 "sync": "riseTime 0.8 s (zones ambush.rise, Кривша summon): frame = min(5, floor(t / riseTime * 6)); "
                         "the grave (hole, soil, torn turf) is part of the frames, so DRAW IT AT THE PIVOT WITHOUT the "
                         "grey-box clip/slide (world.js 'rise'). Summoned by Кривша: fx_krivsha_summon frames 0-2 come "
                         "first (upyr_visible_from_frame 3): play rise over the remaining 0.5 s -> "
                         "frame = min(5, floor((t - 0.3) / 0.5 * 6)), nothing before t = 0.3"},
    }
    man, out = M.char_sheets("upyr", "Упырь", UP, [("upyr", None, None)], up_events, up_notes, MEAS)
    man["roles"] = ("Залесье packs (mlvl 1-2), ambush waves rising from the ground (zone.ambush), forest trail and "
                    "капище (mlvl 2-5), Кривша's summons (mlvl 4) — the same sprite everywhere; elite / champion tints "
                    "and outlines are the engine's")
    lo_se, hi_se = UP.body_height("se")
    lo_ne, hi_ne = UP.body_height("ne")
    man["height_for_engine"] = {"def.height": 40, "measured_body_px": "%d-%d (idle, walk; head top incl. outline)" % (min(lo_se, lo_ne), max(hi_se, hi_ne)),
                                "raised_claws_px": "attack wind-up up to 49, hurt 42 (not the body)", "r": 0.35}
    M.save_manifest(man, out, "upyr")
    MEAS["upyr"]["body"] = dict(se=[lo_se, hi_se], ne=[lo_ne, hi_ne])

    # ================================================================ Береста возврата
    out = os.path.join(ROOT, "item_beresta")
    ic = BE.icon()
    X.save_sheet([ic], out, "item_beresta_icon", dict(
        item="Береста возврата (item.beresta)", kind="bag icon (inventory 1x1, stack ×N drawn by the engine)",
        pivot=[ic.shape[1] // 2, ic.shape[0] // 2], fps=0, loop=False,
        size_note="%dx%d incl. ink outline; centred in the 24-px cell like every 1x1 icon (old beresta 20x18)" % (ic.shape[1], ic.shape[0]),
        atlas="art/ui/src/items_rus.build() key 'beresta' now returns this drawing (beresta_v2 -> sprites/src/beresta.py); "
              "re-run prototype/tools/export_ui.py to refresh assets/items.png + src/data/ui_atlas.js",
        notes="diagonal birch-bark roll, bronze wire, burning Чур rhomb (ember/flame); no red (old icon had a red cord)"))
    X.preview([[ic]], ["иконка"], os.path.join(out, "preview"), "item_beresta_icon", 1, True, (ic.shape[1] // 2, ic.shape[0] // 2),
              title="Береста возврата · иконка котомки")
    gr = BE.ground()
    gh, gw = gr[0].shape
    bottom = int(np.where((gr[0] >= 0).any(1))[0].max())
    gpiv = (gw // 2, bottom)
    X.save_sheet(gr, out, "item_beresta_ground", dict(
        item="Береста возврата on the ground (loot)", pivot=list(gpiv), fps=6, loop=True,
        draw="pivot = the item's ground point (where drawGroundItem gets x, y); keep the engine's ink shadow ellipse "
             "under it (7x3); frame 0 can be used as a static sprite; the 4-frame loop makes the Чур sign glint",
        size_note="%dx%d incl. outline (loot scale.md §3.4: серебро 14x7, щит 13x8)" % (gw, gh),
        layer="ground loot, under characters (scale.md §4.1)"))
    X.preview([gr], ["на земле"], os.path.join(out, "preview"), "item_beresta_ground", 6, True, gpiv, title="Береста на земле · 4")
    M.save_manifest(dict(item="Береста возврата", key="beresta", files=dict(icon="item_beresta_icon.png", ground="item_beresta_ground.png"),
                         icon_size=[ic.shape[1], ic.shape[0]], ground_frame=[gw, gh], ground_pivot=list(gpiv)), out, "item_beresta")
    MEAS["item_beresta"] = dict(icon=[ic.shape[1], ic.shape[0]], ground=[gw, gh], ground_pivot=list(gpiv),
                                ground_visible=[int((gr[0] >= 0).any(0).sum()), int((gr[0] >= 0).any(1).sum())])

    # ================================================================ Чуров проход
    out = os.path.join(ROOT, "fx_chur_portal")
    op, lp, fd, cl = CP.opening(), CP.open_loop(), CP.fading(), CP.closing()
    common = dict(object="Чуров проход (obj.chur_portal), the passage opened by «Береста возврата»; type 'portal' in the "
                         "prototype; both ends (field + town at the крада) use the same sheets",
                  frame_size=[CP.W, CP.H], pivot=list(CP.PIV),
                  sizes_px=dict(oval_top=CP.body_top(lp[0]), oval_width=int(2 * CP.OV_RX + 2),
                                ground_ring=[round(2 * CP.RING_RX, 1), round(2 * CP.RING_RY, 1)], ring_r_tiles=CP.RING_R,
                                sparks_to=max(CP.visible_height(a) for a in lp)),
                  hitbox_hint="objectAt box for 'portal': [14, -%d, 8] (half-width, top, bottom) instead of [14, -46, 6]" % CP.body_top(lp[0]),
                  layer="sorted by pivot y like the other objects (world.js k 6)",
                  light_hint="engine light: warm bronze, radius 2 tiles at y - 28")
    states = (("fx_chur_portal_open", op, 10, False, "one-shot when the passage appears (after the 1 s cast): ring lights, "
                                                      "a light slit rises and splits into the oval; last frame == loop frame 0"),
              ("fx_chur_portal_loop", lp, 10, True, "open: loop for the passage's life (GDD §12.1.5: 8 frames)"),
              ("fx_chur_portal_fading", fd, 10, True, "optional: the last 10 s of the 60 (prototype life < 0.17): gutters, "
                                                       "flicker baked in — use it INSTEAD of the alpha flicker in drawPortal"),
              ("fx_chur_portal_close", cl, 10, False, "one-shot when it closes (expired / used / replaced): the oval narrows "
                                                       "to a slit and sinks into the ring; then remove the object"))
    for name, frs, fps, loop, note in states:
        m = dict(common); m.update(state=name.replace("fx_chur_portal_", ""), notes=note,
                                   visible_height_px=_hs(frs, CP.PIV[1]), fps=fps, loop=loop)
        X.save_sheet(frs, out, name, m)
    X.preview([op, lp, fd, cl], ["открытие", "открыт", "угасает", "закрытие"],
              os.path.join(out, "preview"), "fx_chur_portal", 10, True, CP.PIV, title="Чуров проход · 6 / 8 / 8 / 6")
    M.save_manifest(dict(object="Чуров проход", key="obj.chur_portal", frame_size=[CP.W, CP.H], pivot=list(CP.PIV),
                         files={n: n + ".png" for n, *_ in states},
                         states="closed = no object (nothing drawn) -> open (6 @10 once) -> loop (8 @10) "
                                "[-> fading (8 @10 loop) for the last 10 s] -> close (6 @10 once) -> removed",
                         hitbox_hint=common["hitbox_hint"]), out, "fx_chur_portal")
    MEAS["fx_chur_portal"] = dict(frame=[CP.W, CP.H], pivot=list(CP.PIV), oval_top=CP.body_top(lp[0]),
                                  open_loop_top=_hs(lp, CP.PIV[1]), ring=[round(2 * CP.RING_RX, 1), round(2 * CP.RING_RY, 1)])

    scenes(MEAS, ic, gr, op, lp, cl)


def _hero():
    return M._hero()


def scenes(MEAS, ic, gr, op, lp, cl):
    out = os.path.join(ROOT, "m1c_scenes")
    os.makedirs(out, exist_ok=True)
    hero = _hero()
    hero_l = hero[:, ::-1].copy()
    paths = {}
    # ---- 1. упыри: an ambush wave rises, a pack shambles in, one smashes at the hero; Кривша's summon ----------
    W, H = 360, 120
    rise = [UP.frame(UP.rise, i, "se") for i in range(6)]
    walk = [UP.frame(UP.walk, i, "se") for i in range(8)]
    atk = [UP.frame(UP.attack, i, "se") for i in range(6)]
    idle = [UP.frame(UP.idle, i, "se") for i in range(4)]
    death = [UP.frame(UP.death, i, "se") for i in range(8)]
    summ = F.summon()
    frames = []
    for i in range(12):
        g = ground(W, H, seed=21)
        _paste(g, rise[min(5, i // 2)], 28 - UP.PIV[0], 76 - UP.PIV[1])                              # ambush wave
        _paste(g, rise[min(5, max(0, i - 3) // 2)], 52 - UP.PIV[0], 100 - UP.PIV[1])
        for k, (x, y) in enumerate(((104, 82), (126, 104))):
            M._shadow(g, x, y + 1, 9, 3.5)
            _paste(g, walk[(i + k * 3) % 8], x - UP.PIV[0], y - UP.PIV[1])
        M._shadow(g, 178, 94, 9, 3.5)
        _paste(g, atk[min(5, i // 2)], 178 - UP.PIV[0], 93 - UP.PIV[1])
        M._shadow(g, 214, 94, 9, 3.5)
        _paste(g, hero_l, 214 - 32, 93 - 56)
        _paste(g, death[min(7, i)], 262 - UP.PIV[0], 100 - UP.PIV[1])
        j = i % 12                                                                                   # summoned by Кривша
        if j < 8:
            _paste(g, summ[j], 330 - F.SU_PIV[0], 96 - F.SU_PIV[1])
        if j >= 3:
            _paste(g, rise[min(5, int((j - 3) / 5 * 6))], 330 - UP.PIV[0], 96 - UP.PIV[1])
        frames.append(g)
    comp = frames[6].copy()
    label(comp, 4, 3, "Упыри 40: из земли · толпа · удар · гибель · призыв Кривши · герой 44")
    paths["upyr"] = _save_idx(comp, os.path.join(out, "upyr_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "upyr_scene.gif"), 8)
    # ---- 2. Береста возврата: on the ground -> read -> the passage opens, loops, closes -----------------------------
    W, H = 260, 110
    frames = []
    seq = [("ground", 0)] * 4 + [("open", k) for k in range(6)] + [("loop", k) for k in range(16)] + [("close", k) for k in range(6)] + [("gone", 0)] * 3
    for n, (st, k) in enumerate(seq):
        g = ground(W, H, seed=23)
        _paste(g, gr[n % 4], 60 - gr[0].shape[1] // 2, 96 - int(np.where((gr[0] >= 0).any(1))[0].max()))
        M._shadow(g, 112, 94, 9, 3.5)
        _paste(g, hero, 112 - 32, 93 - 56)
        spr = {"open": op, "loop": lp, "close": cl}.get(st)
        if spr is not None:
            _paste(g, spr[k % len(spr)], 168 - CP.PIV[0], 92 - CP.PIV[1])
        # the bag icon in a 24-px cell, like the котомка
        g[6:30, 226:250] = C["slate_dk"]; g[6, 226:250] = C["ink"]; g[29, 226:250] = C["ink"]; g[6:30, 226] = C["ink"]; g[6:30, 249] = C["ink"]
        _paste(g, ic, 238 - ic.shape[1] // 2, 18 - ic.shape[0] // 2)
        frames.append(g)
    comp = np.concatenate([frames[2], frames[4 + 3], frames[12]], 1)
    label(comp, 4, 3, "Береста: на земле · открытие · Чуров проход (герой 44)")
    paths["portal"] = _save_idx(comp, os.path.join(out, "beresta_portal_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "beresta_portal_scene.gif"), 10)
    MEAS["m1c_scenes"] = {k: os.path.relpath(v, ROOT) for k, v in paths.items()}


if __name__ == "__main__":
    Mx = {}
    run(Mx)
    print(json.dumps(Mx, ensure_ascii=False)[:6000])

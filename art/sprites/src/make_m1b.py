"""Mission 1, milestone (b): Кривша (Обгорелый страж), Огнея Пепельная, огнище, Идол Перуна + ability fx.
Writes krivsha/, mara/, ognishche/, idol_perun/, fx_krivsha_*/, fx_mara_*/ and scene previews (m1b_scenes/).
Called from make_all.py (run(MEAS)); can also run alone: python3 make_m1b.py"""
import os
import sys
import json
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
import export as X
import bigrig
import krivsha as KV
import mara as MR
import kapishche as KP
import fx_m1b as F
import anchutka as AN
from make_rest import ground, _paste, _save_idx, _save_gif, label

ROOT = X.ROOT
VIEWS = ("se", "ne")
MIRROR = {"se": "sw", "ne": "nw"}
HEIGHT_RULE = "pivot row (ground under the feet) to the top visible pixel, outline included"
DIR_MAP = {
    "prototype_dirs": "0..7 (0 = towards the camera, 2 = left, 4 = away, 6 = right); BACK = {3,4,5}",
    "sheet": "dir in {3,4,5} -> *_ne, otherwise -> *_se",
    "flip": "draw mirrored (scale x = -1 around the pivot) when dirSide(dir, facing) < 0",
    "rule": "scale.md §4.1 / GDD §12.1.2: 2 drawn directions (SE, NE) + horizontal mirror (SW, NW); "
            "the 8 logical directions of the engine map onto these 4 views",
}
RU = {"idle": "покой", "walk": "ходьба", "claw": "удар когтями", "summon": "призыв упырей", "leap": "прыжок в огнище",
      "emerge": "выход из огня", "hurt": "урон", "death": "гибель", "cast": "огненный сгусток", "heal": "лечение",
      "coal_throw": "бросок угля"}

# ------------------------------------------------------------------ gameplay events per animation
KV_EVENTS = {
    "claw": {"hit_frame": KV.CLAW_HIT, "telegraph_frames": [0, 5], "arc": "front cone (bosses.json claw.halfAngleDeg)",
             "sync": "GDD v1.8: telegraph 0.6 s, every 2.4 s, same tempo in both phases. Frames 0-5 span the telegraph (10 fps = 0.6 s), "
                     "frame 6 is shown from the hit moment; if the engine waits after the telegraph (prototype: +0.25 s), hold frame 5",
             "overlay": "fire crescent baked into frame 6"},
    "summon": {"spawn_frame": KV.SUMMON_SPAWN, "spawn_effect": "fx_krivsha_summon (at every упырь spawn point, 8 frames @10 = riseTime 0.8 s); the summoned upyri use the normal упырь sprite and its rise from the ground",
               "note": "frames 0-3 raise the arms, 4-6 slam the ground (embers baked in 5-6). Spawn the upyri on frame 5 "
                       "(t = 0.5 s); if the engine keeps spawning instantly, start this anim 0.5 s before the summon timer fires"},
    "leap": {"arc_frames": [0, 5], "loop_frames": list(KV.LEAP_LOOP), "landing_frame": 6,
             "note": "frames 0-5 = the 0.6 s arc at 10 fps; the ENGINE moves the sprite along the arc and adds the "
                     "lift (sin * 40), the art has no baked height. On landing (frame 6) start fx_krivsha_leap_burst "
                     "on the огнище and loop frames 6-7 while invulnerable (2 s), then play krivsha_fire_emerge"},
    "emerge": {"note": "normal sheet = rising out of the burning idol at the start of the fight (rise 2 s: hold frame 0, "
                       "play the 6 frames over the last 0.75 s, or the whole sheet at 3 fps); "
                       "krivsha_fire_emerge = leaving the огнище at the start of the fire phase, together with fx_krivsha_feed "
                       "(«огнище питает», +15% HP on feed frame 6); then aura on"},
    "death": {"note": "last frame holds (charred heap with dying embers, frames 8-11); then idol_perun_extinguish"},
    "hurt": {"note": "2 frames, flinch back; play over any anim except leap / emerge"},
}
MR_EVENTS = {
    "cast": {"release_frame": MR.CAST_RELEASE, "spawn_effect": "fx_mara_bolt (flight), fx_mara_bolt_hit (impact)",
             "spawn_at_px_se": [MR.PIV[0] + 19, MR.PIV[1] - 38], "spawn_at_px_sw": [MR.W - (MR.PIV[0] + 19), MR.PIV[1] - 38],
             "sync": "attackTime 2.0 s, hitAt 0.7 s: start the 10 fps anim at t = 0.4 s so frame 3 is at 0.7 s"},
    "heal": {"apply_frame": MR.HEAL_APPLY, "note": "every 8 s (bosses.json heal.every); the nebyl wisps are in her hands, "
                                                  "the engine's area burst (radius 6) can stay"},
    "death": {"note": "collapses into an ash heap; last frame holds"},
}


def _hs(frames, py):
    return [bigrig.height(a, py) for a in frames]


def char_sheets(slug, title, mod, variants, events, notes, MEAS):
    """variants: list of (prefix, hot_flag or None, anim filter). Writes <prefix>_<anim>_<se|ne> + previews."""
    out = os.path.join(ROOT, slug)
    W, H = mod.W, mod.H
    piv = mod.PIV
    manifest = dict(character=title, folder=slug, frame_size=[W, H], pivot=list(piv), directions=DIR_MAP,
                    mirror_rule="flip horizontally around the frame centre line x = %.1f; pivot stays (%d, %d)" % (W / 2, piv[0], piv[1]),
                    animations={})
    MEAS[slug] = {}
    for (prefix, hot, allow) in variants:
        for (anim, n, fps, loop, fn) in mod.ANIMS:
            if allow and anim not in allow:
                continue
            per_view = {}
            for v in VIEWS:
                frs = [mod.frame(fn, i, v, hot) if hot is not None else mod.frame(fn, i, v) for i in range(n)]
                hs = _hs(frs, piv[1])
                meta = dict(character=title, animation=anim, variant=("fire_phase" if hot else "normal") if hot is not None else None,
                            direction=v, mirror_for=MIRROR[v], mirror_rule=manifest["mirror_rule"], pivot=list(piv),
                            fps=fps, loop=loop, visible_height_px=hs, height_rule=HEIGHT_RULE, notes=notes)
                if meta["variant"] is None:
                    del meta["variant"]
                if anim in events:
                    meta["events"] = events[anim]
                name = "%s_%s_%s" % (prefix, anim, v)
                X.save_sheet(frs, out, name, meta)
                per_view[v] = frs
                MEAS[slug][("fire_" if hot else "") + anim + "_" + v] = hs
            rows = [per_view["se"], per_view["ne"], [X.mirror(a) for a in per_view["se"]], [X.mirror(a) for a in per_view["ne"]]]
            X.preview(rows, ["SE", "NE", "SW зерк.", "NW зерк."], os.path.join(out, "preview"), "%s_%s" % (prefix, anim), fps, loop, piv,
                      shadow_w=36 if W > 64 else (18 if W >= 64 else 12),
                      title="%s%s · %s · %d кадр. · %d кадр./с" % (title, " (огненная фаза)" if hot else "", RU[anim], n, fps))
            manifest["animations"]["%s_%s" % (prefix, anim)] = dict(files={v: "%s_%s_%s.png" % (prefix, anim, v) for v in VIEWS},
                                                                   frames=n, fps=fps, loop=loop, events=events.get(anim, {}))
    return manifest, out


def save_manifest(manifest, out, name):
    with open(os.path.join(out, name + ".json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


def fx_sheet(folder, name, frames, pivot, fps, loop, meta, title, labels=("цикл",), rows=None):
    out = os.path.join(ROOT, folder)
    m = dict(meta); m.update(pivot=list(pivot), fps=fps, loop=loop)
    X.save_sheet(frames, out, name, m)
    X.preview(rows or [frames], list(labels), os.path.join(out, "preview"), name, fps, loop, pivot, title=title)
    return out


def run(MEAS):
    # ================================================================ Кривша
    kv_notes = ("Кривша, Обгорелый страж (boss M1; «Обгорелый страж» is his title, one character). Hunched keeper of the "
                "капище in a burnt sheepskin coat with a ring of bronze keys, ghoul-grey skin, long claws with burning tips, "
                "fire in the coat's cracks. Body 96 (scale.md: boss 96, fire halo to 112), frame 128x128, pivot (64,116).")
    man, out = char_sheets("krivsha", "Кривша, Обгорелый страж", KV,
                           [("krivsha", False, None), ("krivsha_fire", True, KV.FIRE_VARIANT)], KV_EVENTS, kv_notes, MEAS)
    man["phases"] = {
        "normal": "krivsha_* sheets. Abilities: claw (cone 2 tiles ±45°, telegraph 0.6 s, every 2.4 s), summon (2 upyri every 20 s, first after 8 s, max 4), fire trail (fx_krivsha_fire_trail).",
        "fire_phase": "at 50% HP: krivsha_leap (arc to the nearest not consecrated огнище) -> fx_krivsha_leap_burst on the "
                      "hearth + leap frames 6-7 loop for the 2 s of invulnerability -> krivsha_fire_emerge together with "
                      "fx_krivsha_feed_back / fx_krivsha_feed (on him) + fx_krivsha_feed_source (on the огнище), +15% HP on "
                      "feed frame 6 -> all krivsha_fire_* sheets + fx_krivsha_aura under him (r 1.5). GDD v1.8: NO attack "
                      "speed-up in the fire phase; krivsha_fire_* sheets have exactly the same frames, fps and events as the "
                      "normal ones (play them at the normal tempo, atkMul = 1). The fire variant is the same drawing with hotter "
                      "cracks, brighter eyes and taller flames (to ≤112).",
        "start": "rise from the burning idol: krivsha_emerge (normal).",
        "end": "krivsha_death (normal or fire variant, whichever phase he is in) -> idol_perun_extinguish -> idol_perun_smoking.",
    }
    man["fx"] = {"fire_trail": "fx_krivsha_fire_trail", "aura": "fx_krivsha_aura", "summon": "fx_krivsha_summon",
                 "leap": "fx_krivsha_leap_burst",
                 "feed": ["fx_krivsha_feed_back", "fx_krivsha_feed", "fx_krivsha_feed_source"]}
    save_manifest(man, out, "krivsha")

    # ================================================================ Огнея
    mr_notes = ("Огнея Пепельная (былинный враг M1, дух пожара): hovering ash shroud and hood, pale face, flame hair, "
                "smouldering hem and forearms. Hovers 2.5±1 px above the ground (pivot = ground point under her; keep the "
                "shadow on the ground). Body 48-50 incl. hover, flame hair ≤ 53, raised fire bolt ≤ 55 "
                "(scale.md: 48, flames to 54). Frame 64x64, pivot (32,56).")
    man, out = char_sheets("mara", "Огнея Пепельная", MR, [("mara", None, None)], MR_EVENTS, mr_notes, MEAS)
    man["retinue"] = ("4-6 анчуток mlvl 2 (bosses.json retinue.kind = anchutka): an existing monster type of the prototype; "
                      "there is no art sprite for the анчутка yet (grey box in the prototype). Not a new tinted variant.")
    man["fx"] = {"ash_trail": "fx_mara_ash_trail", "bolt": "fx_mara_bolt", "bolt_hit": "fx_mara_bolt_hit"}
    man["extra_animations"] = "walk (glide) and heal are not in GDD §12.1.2 (парение, ведовство, урон, гибель); added for the prototype's moves"
    save_manifest(man, out, "mara")

    # ================================================================ анчутка (стаи Залесья и свита Огнеи)
    an_notes = ("Анчутка (GDD §5.2 E1: мелкий бес-поджигатель, кидает угли и убегает; codex: водится у печей и пожарищ). "
                "One sprite for the Залесье packs and Огнея's retinue (GDD has no separate retinue variant). Hunched bald "
                "soot imp: big head, swept-back pointed ears, bone horn nubs, ember eyes, long arms with ash-dusted forearms, "
                "short legs, low tail with a smouldering tuft. Soot/ash greys + ember accents, no red (hero accent). "
                "Body 26-27 incl. ears (scale.md 24-28; def.height 26), frame 32x40, pivot (16,34).")
    an_events = {
        "coal_throw": {"release_frame": AN.THROW_RELEASE,
                       "spawn_at_px_se": [AN.PIV[0] + AN.THROW_SPAWN[0], AN.PIV[1] + AN.THROW_SPAWN[1]],
                       "spawn_at_px_sw": [AN.W - (AN.PIV[0] + AN.THROW_SPAWN[0]), AN.PIV[1] + AN.THROW_SPAWN[1]],
                       "spawn_height_px": -AN.THROW_SPAWN[1], "spawn_effect": "fx_anchutka_coal (flight)",
                       "sync": "attackTime 1.0 s, hitAt 0.45 s (monsters.json): 5 frames at 7 fps, frame 3 starts at 0.43 s "
                               "= the coal leaves the hand; the anim ends at 0.71 s, hold idle for the rest of attackTime"},
        "walk": {"note": "бег (GDD §12.1.2 «бег 6»): used for chase, retreat (keepMin / retreatDist) and the 3 s squealing flee "
                         "(fear); the scuttle reads fast at speed 4.0"},
        "hurt": {"note": "2 frames; the squeal mouth (ember gullet) is in frame 0"},
        "death": {"note": "squeals, topples, crumbles into a soot heap with dying embers; last frame holds (corpse)"},
    }
    man, out = char_sheets("anchutka", "Анчутка", AN, [("anchutka", None, None)], an_events, an_notes, MEAS)
    man["roles"] = ("Залесье packs (mlvl 1-2), forest trail and капище (mlvl 2-5), Огнея's retinue (4-6, mlvl 2), "
                    "Чернояр's summons in M3: the same sprite everywhere (elite / champion tints are the engine's)")
    man["height_for_engine"] = {"def.height": 26, "measured_body_px": "26-27 incl. ears (idle, walk, throw)", "r": 0.25}
    man["fx"] = {"coal": "fx_anchutka_coal"}
    save_manifest(man, out, "anchutka")
    cf = AN.coal_fx()
    fx_sheet("fx_anchutka_coal", "fx_anchutka_coal", cf, AN.CO_PIV, 12, True, dict(
        effect="Угли анчутки в полёте (GDD §12.1.5: 3 кадра)",
        draw="centre of the coal at the flight height (prototype: z = 14 + arc 8 px above the shadow); drawn flying +x "
             "(sparks trail to the left), flip when moving left on screen. Ember / flame / soot crust, no red."),
        "Угли анчутки · 3")
    MEAS["fx_anchutka_coal"] = dict(frame=[AN.CO_W, AN.CO_H], pivot=list(AN.CO_PIV))

    # ================================================================ огнище
    out = os.path.join(ROOT, "ognishche")
    og_d, og_c, og_t = KP.ognishche("desecrated"), KP.ognishche("consecrated"), KP.consecrate()
    og_p = KP.progress()
    common = dict(object="Огнище (M1, 3 around the Идол Перуна), full object sprite: 8 standing stones with насечки, log crib, flame",
                  footprint="2x2 tiles, like the костёр (stone ring r 21x10.5); pivot = centre of the footprint",
                  sizes_px=dict(log_crib=24, flame_from_ground=72, licks_sparks_above=True), layer="sorted by pivot y")
    for name, frs, fps, loop, note in (
            ("ognishche_desecrated", og_d, 10, True, "green (nebyl) flame, sooted stones, насечки dark with a green glint"),
            ("ognishche_consecrate", og_t, 10, False, "one-shot transition when the hold completes: green dies, bronze/linen "
                                                       "flash, warm flame grows; the last frame == ognishche_consecrated frame 0"),
            ("ognishche_consecrated", og_c, 10, True, "warm flame, насечки glow bronze")):
        m = dict(common); m.update(state=name.split("_")[1], notes=note,
                                   visible_height_px=_hs(frs, KP.OG_PIV[1]),
                                   state_machine="desecrated --(hero holds Interact 3 s)--> consecrate (6 f) --> consecrated")
        X.save_sheet(frs, out, name, dict(m, pivot=list(KP.OG_PIV), fps=fps, loop=loop))
    X.preview([og_d, og_t, og_c], ["оскверн.", "освящение", "освящено"], os.path.join(out, "preview"), "ognishche", 10, True,
              KP.OG_PIV, title="Огнище · осквернено / освящение / освящено · 6+6+6")
    X.save_sheet(og_p, out, "ognishche_progress", dict(
        object="Consecration progress overlay (draw OVER the desecrated огнище while the hero holds Interact)",
        pivot=list(KP.PR_PIV), fps=0, loop=False, indexing="by progress, not by time: frame = min(11, floor(holdT / 3.0 * 12))",
        notes="bronze ring on the ground fills clockwise from the front; the 8 насечки light up in order; a warm core grows "
              "inside the green flame; motes rise. Frame 72x124 (wider/taller than the hearth so the ring fits), "
              "align by pivot. On release before 3 s: hide (or run frames backwards).",
        visible_height_px=_hs(og_p, KP.PR_PIV[1])))
    base = [bigrig.over(np.pad(og_d[i % 6], ((0, KP.PR_PAD[1]), (KP.PR_PAD[0], KP.PR_PAD[0])), constant_values=-1), o)
            for i, o in enumerate(og_p)]
    X.preview([og_p, base], ["оверлей", "поверх огнища"], os.path.join(out, "preview"), "ognishche_progress", 6, True, KP.PR_PIV,
              title="Огнище · прогресс освящения (кадр = доля удержания 3 с) · 12")
    save_manifest(dict(object="Огнище", files=dict(desecrated="ognishche_desecrated.png", consecrate="ognishche_consecrate.png",
                                                   consecrated="ognishche_consecrated.png", progress="ognishche_progress.png"),
                       frame_size=[KP.OG_W, KP.OG_H], pivot=list(KP.OG_PIV),
                       progress_frame_size=[KP.PR_W, KP.PR_H], progress_pivot=list(KP.PR_PIV),
                       states={"desecrated": "loop 6 @10", "consecrating": "desecrated loop + ognishche_progress[floor(holdT/3*12)]",
                               "consecrate": "one-shot 6 @10 on completion", "consecrated": "loop 6 @10, same phase as frame 0"},
                       light_hint="engine light: desecrated nebyl (pine/nebyl) radius 2.5 tiles; consecrated warm radius 3 tiles"),
                  out, "ognishche")
    MEAS["ognishche"] = dict(frame=[KP.OG_W, KP.OG_H], pivot=list(KP.OG_PIV), desecrated=_hs(og_d, KP.OG_PIV[1]),
                             consecrated=_hs(og_c, KP.OG_PIV[1]), progress_frame=[KP.PR_W, KP.PR_H])

    # ================================================================ Идол Перуна
    out = os.path.join(ROOT, "idol_perun")
    ib, ie, ism = KP.idol("burning"), KP.idol("extinguish"), KP.idol("smoking")
    body_top = bigrig.height(KP._idol_frame(2, 0, 0)[0], KP.ID_PIV[1])
    flame_top = []
    for fr in ib:
        fire = np.isin(fr, [C["ember"], C["flame"], C["linen"]])
        rows = np.where(fire.sum(1) >= 2)[0]
        flame_top.append(int(KP.ID_PIV[1] - rows.min() + 1))
    common = dict(object="Идол Перуна (main idol of the капище, M1), full object sprite: stone plinth, carved oak pillar, "
                         "silver head with a gold moustache, thunder wheel; 2x2 tiles",
                  sizes_px=dict(body=body_top, flame_body_max=max(flame_top), note="sparks/smoke rise above"),
                  layer="sorted by pivot y; blocks movement (2x2)")
    for name, frs, fps, loop, note in (
            ("idol_perun_burning", ib, 10, True, "burns during the fight (Кривша rises out of it); blaze behind the pillar, crown "
                                                  "flame to 136, tongues on the sides; face stays readable"),
            ("idol_perun_extinguish", ie, 8, False, "one-shot after Кривша dies: flames die down, smoke builds; ends on smoking"),
            ("idol_perun_smoking", ism, 8, True, "after the fight: charred, ember crack, smoke")):
        m = dict(common); m.update(state=name.replace("idol_perun_", ""), notes=note, visible_height_px=_hs(frs, KP.ID_PIV[1]))
        X.save_sheet(frs, out, name, dict(m, pivot=list(KP.ID_PIV), fps=fps, loop=loop))
    X.preview([ib, ie, ism], ["горит", "гаснет", "дымит"], os.path.join(out, "preview"), "idol_perun", 8, True, KP.ID_PIV,
              title="Идол Перуна · горит 6 / гаснет 8 / дымит 6")
    save_manifest(dict(object="Идол Перуна", frame_size=[KP.ID_W, KP.ID_H], pivot=list(KP.ID_PIV),
                       files=dict(burning="idol_perun_burning.png", extinguish="idol_perun_extinguish.png", smoking="idol_perun_smoking.png"),
                       states="burning (loop, M1 until Кривша dies) -> extinguish (one-shot 8 @8) -> smoking (loop)",
                       light_hint="burning: warm light radius 5 tiles at the flame root (y - 70); smoking: none"),
                  out, "idol_perun")
    MEAS["idol_perun"] = dict(frame=[KP.ID_W, KP.ID_H], pivot=list(KP.ID_PIV), body=body_top, flame=flame_top,
                              burning_total=_hs(ib, KP.ID_PIV[1]))

    # ================================================================ fx
    fx_sheet("fx_krivsha_fire_trail", "fx_krivsha_fire_trail", F.trail("fire"), F.TR_PIV, 8, True, dict(
        effect="Огненный след Кривши (bosses.json fireTrail, r 0.6 tile)", radius_tiles=F.TR_R,
        draw="ground decal at the trail point, native size (no scale for r 0.6; scale = r / 0.6 otherwise); "
             "the engine's alpha fade-in/out stays; random start frame per patch"), "Огненный след Кривши · 4")
    fx_sheet("fx_krivsha_aura", "fx_krivsha_aura", F.aura(), F.AU_PIV, 10, True, dict(
        effect="Огненный ореол Кривши в огненной фазе (r 1.5 tile)", radius_tiles=F.AU_R,
        draw="ground decal centred on the boss pivot, BEFORE (under) the boss sprite; replaces the ellipse in drawKrivsha"),
        "Огненный ореол (фаза огня) · 6")
    fx_sheet("fx_krivsha_summon", "fx_krivsha_summon", F.summon(), F.SU_PIV, 10, False, dict(
        effect="Призыв упырей: земля трескается, жар, дымки небыли", events={"upyr_visible_from_frame": 3},
        draw="one per upyr spawn point; 8 frames @10 = the upyr riseTime 0.8 s; draw under the rising upyr"),
        "Призыв упыря · 8")
    lb = F.leap_burst()
    fx_sheet("fx_krivsha_leap_burst", "fx_krivsha_leap_burst", lb, F.LB_PIV, 10, False, dict(
        effect="Прыжок Кривши в огнище: вспышка пламени", events={"impact_frames": [0, 3], "loop_frames": [4, 7]},
        draw="over the огнище (same 64x120 cell, same pivot) from the landing; frames 0-3 once, then loop 4-7 while he "
             "is inside (2 s), then stop when krivsha_fire_emerge starts"), "Прыжок в огнище · 4 + петля 4")
    fx_sheet("fx_mara_ash_trail", "fx_mara_ash_trail", F.trail("ash"), F.TR_PIV, 6, True, dict(
        effect="Пепельный след Огнеи (bosses.json ashTrail, r 0.6 tile, burns 3 s)", radius_tiles=F.TR_R,
        draw="ground decal, native size; engine alpha fade stays"), "Пепельный след Огнеи · 4")
    fx_sheet("fx_mara_bolt", "fx_mara_bolt", F.bolt(), F.BO_PIV, 12, True, dict(
        effect="Огненный сгусток Огнеи в полёте", draw="drawn facing +x (right); flip when moving left; raise it to the "
                                                    "release height (38 px above the ground) and keep a 4x2 ink shadow on the ground"),
        "Сгусток Огнеи · 4")
    fx_sheet("fx_mara_bolt_hit", "fx_mara_bolt_hit", F.bolt_hit(), F.BH_PIV, 12, False, dict(
        effect="Попадание сгустка", draw="at the impact point (pivot on the ground)"), "Попадание · 5")
    # «огнище питает Крившу» (GDD v1.8 §5.4): three sheets, all 8 frames @10 = 0.8 s, heal on frame 6
    fb, ff = F.feed()
    fs = F.feed_source()
    feed_events = {"heal_frame": F.FE_HEAL, "stream_frames": [0, 5], "flash_frames": [6, 7],
                   "trigger": "start together with krivsha_fire_emerge frame 0 (prototype: jump state, t = invuln - 0.75 s); "
                              "apply +15% HP (hearthPhase.healPct) on frame 6 = 0.6 s after the start (≈0.15 s before the "
                              "invulnerability ends; healing exactly at the end of invuln is also fine)"}
    feed_meta = dict(effect="«Огнище питает Крившу»: fire-phase start, +15% HP while he leaves the огнище (GDD v1.8 §5.4)",
                     events=feed_events, frame_size_note="Кривша's own cell 128x128, pivot (64,116) = his pivot",
                     mirror="flip together with Кривша (dirSide < 0); the same sheet serves SE and NE",
                     chest_anchor=[F.FE_PIV[0] + F.FE_CHEST[0], F.FE_PIV[1] + F.FE_CHEST[1]],
                     colours="огнище green (nebyl_dk/nebyl/linen, like the desecrated огнище) turning into his fire "
                             "(ember/flame/linen); no red / red_lt (hero accent)")
    out = os.path.join(ROOT, "fx_krivsha_feed")
    X.save_sheet(fb, out, "fx_krivsha_feed_back", dict(feed_meta, pivot=list(F.FE_PIV), fps=F.FE_FPS, loop=False,
                 layer="draw BEFORE (under) the Кривша sprite: flame pillar behind him and the back halves of the strands"))
    X.save_sheet(ff, out, "fx_krivsha_feed", dict(feed_meta, pivot=list(F.FE_PIV), fps=F.FE_FPS, loop=False,
                 layer="draw AFTER (over) the Кривша sprite: front strands, chest glow, heal flash"))
    X.save_sheet(fs, out, "fx_krivsha_feed_source", dict(
        effect="«Огнище питает»: the огнище's green flame surges and is drawn off", pivot=list(F.FS_PIV), fps=F.FE_FPS,
        loop=False, events=feed_events, layer="over the огнище he jumped into (same 64x120 cell and pivot as ognishche_*); "
                                              "start at the same moment as fx_krivsha_feed; replaces fx_krivsha_leap_burst"))
    comp = []
    for i in range(F.FE_N):
        c = fb[i].copy()
        bigrig.over(c, KV.frame(KV.emerge, min(5, int(i * 0.8)), "se", True))      # emerge @8 vs feed @10
        comp.append(bigrig.over(c, ff[i]))
    X.preview([comp, ff, fb, [X.mirror(a) for a in comp]], ["с Крившей", "передний", "задний", "SW зерк."],
              os.path.join(out, "preview"), "fx_krivsha_feed", F.FE_FPS, False, F.FE_PIV, shadow_w=36,
              title="Огнище питает Крившу · 8 кадр. · 10 кадр./с · лечение на кадре 6")
    og0 = KP.ognishche("desecrated")
    X.preview([[bigrig.over(og0[i % 6].copy(), fs[i]) for i in range(F.FE_N)], fs], ["поверх огнища", "оверлей"],
              os.path.join(out, "preview"), "fx_krivsha_feed_source", F.FE_FPS, False, F.FS_PIV,
              title="Огнище отдаёт огонь · 8 кадр. · 10 кадр./с")
    MEAS["fx_krivsha_feed"] = dict(frame=[F.FE_W, F.FE_H], pivot=list(F.FE_PIV), frames=F.FE_N, fps=F.FE_FPS,
                                   heal_frame=F.FE_HEAL, duration_s=F.FE_N / F.FE_FPS,
                                   top_px=_hs([bigrig.over(a.copy(), b) for a, b in zip(fb, ff)], F.FE_PIV[1]))
    MEAS["fx_m1b"] = dict(trail=[F.TR_W, F.TR_H], aura=[F.AU_W, F.AU_H], summon=[F.SU_W, F.SU_H], leap_burst=[F.LB_W, F.LB_H],
                          bolt=[F.BO_W, F.BO_H], bolt_hit=[F.BH_W, F.BH_H])

    # ================================================================ scene previews (review only)
    scenes(og_d, og_c, og_p, ib, MEAS)


def _hero():
    sys.path.insert(0, "/workspace/game/art/teaser/src")
    import teaser_sprites as _TS                      # hero idle pose, read-only import
    return pk.sprite_to_index(_TS.hero_pose("idle"))


def _shadow(g, x, y, rx, ry):
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
    g[(((xx - x + 0.5) / rx) ** 2 + ((yy - y) / ry) ** 2) <= 1] = C["ink"]


def scenes(og_d, og_c, og_p, ib, MEAS):
    out = os.path.join(ROOT, "m1b_scenes")
    os.makedirs(out, exist_ok=True)
    hero = _hero()
    hero_l = hero[:, ::-1].copy()
    paths = {}
    # ---- 1. Кривша: rises from the idol (normal) / fire phase with aura + trail -----------------
    W, H = 440, 200
    kv_n = [KV.frame(KV.walk, i, "se") for i in range(8)]
    kv_f = [X.mirror(KV.frame(KV.idle, i % 4, "se", True)) for i in range(8)]     # SW: faces the hero
    aura, trail = F.aura(), F.trail("fire")
    frames = []
    for i in range(8):
        g = ground(W, H, seed=5, lit=(80, 170, 120, 60))
        _paste(g, ib[i % 6], 70 - KP.ID_PIV[0], 172 - KP.ID_PIV[1])
        _shadow(g, 170, 176, 18, 7)
        _paste(g, kv_n[i], 170 - KV.PIV[0], 176 - KV.PIV[1])
        _shadow(g, 262, 172, 9, 3.5)
        _paste(g, hero_l, 262 - 32, 172 - 56)
        for k, (tx, ty) in enumerate(((300, 186), (318, 178), (336, 186))):
            _paste(g, trail[(i + k) % 4], tx - F.TR_PIV[0], ty - F.TR_PIV[1])
        _paste(g, aura[i % 6], 380 - F.AU_PIV[0], 176 - F.AU_PIV[1])
        _paste(g, kv_f[i], 380 - (KV.W - KV.PIV[0]), 176 - KV.PIV[1])
        frames.append(g)
    comp = frames[0].copy()
    label(comp, 4, 3, "Идол горит · Кривша 96 · герой 44 · огн. фаза: ореол + след")
    paths["krivsha"] = _save_idx(comp, os.path.join(out, "krivsha_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "krivsha_scene.gif"), 8)
    # ---- 2. Огнея: glide with ash trail, cast, bolt, hit ---------------------------------------
    W, H = 300, 110
    walk = [MR.frame(MR.walk, i % 6, "se") for i in range(6)]
    cast = [MR.frame(MR.cast, i, "se") for i in range(6)]
    ash, bolt, hit = F.trail("ash"), F.bolt(), F.bolt_hit()
    frames = []
    for i in range(6):
        g = ground(W, H, seed=8)
        for k, tx in enumerate((20, 40, 60)):
            _paste(g, ash[(i + k) % 4], tx - F.TR_PIV[0], 92 - F.TR_PIV[1])
        _shadow(g, 84, 92, 9, 3.5)
        _paste(g, walk[i], 84 - MR.PIV[0], 92 - MR.PIV[1])
        _shadow(g, 140, 92, 9, 3.5)
        _paste(g, cast[i], 140 - MR.PIV[0], 92 - MR.PIV[1])
        bx = 175 + i * 12
        g[93, bx - 2:bx + 2] = C["ink"]
        _paste(g, bolt[i % 4], bx - F.BO_PIV[0], 92 - 38 - F.BO_PIV[1])
        _paste(g, hit[min(i, 4)], 252 - F.BH_PIV[0], 92 - F.BH_PIV[1])
        _shadow(g, 266, 92, 9, 3.5)
        _paste(g, hero_l, 266 - 32, 92 - 56)
        frames.append(g)
    comp = frames[3].copy()
    label(comp, 4, 3, "Огнея 48: пепел. след, сгусток · герой 44")
    paths["mara"] = _save_idx(comp, os.path.join(out, "mara_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "mara_scene.gif"), 8)
    # ---- 3. капище: idol + 3 огнища (desecrated / consecrating / consecrated) ---------------------
    W, H = 400, 220
    frames = []
    for i in range(12):
        g = ground(W, H, seed=11, lit=(200, 160, 160, 70))
        _paste(g, og_d[i % 6], 70 - KP.OG_PIV[0], 196 - KP.OG_PIV[1])
        _paste(g, ib[i % 6], 200 - KP.ID_PIV[0], 160 - KP.ID_PIV[1])
        _paste(g, og_d[i % 6], 200 - KP.OG_PIV[0], 210 - KP.OG_PIV[1])
        _paste(g, og_p[min(11, i)], 200 - KP.PR_PIV[0], 210 - KP.PR_PIV[1])
        _shadow(g, 238, 212, 9, 3.5)
        _paste(g, hero_l, 238 - 32, 212 - 56)
        _paste(g, og_c[i % 6], 330 - KP.OG_PIV[0], 196 - KP.OG_PIV[1])
        frames.append(g)
    comp = frames[6].copy()
    label(comp, 4, 3, "Огнища: осквернено · освящение · освящено")
    paths["kapishche"] = _save_idx(comp, os.path.join(out, "kapishche_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "kapishche_scene.gif"), 4)
    # ---- 4. «огнище питает»: Кривша leaves the desecrated огнище at the fire-phase start ---------------
    W, H = 240, 170
    fb, ff = F.feed()
    fs = F.feed_source()
    lb = F.leap_burst()
    hx, hy = 130, 120                                   # огнище; Кривша lands at (x, y + 1.1 tile): -17.6, +8.8 px
    kx, ky = hx - 18, hy + 9
    frames = []
    seq = [("burst", j) for j in range(4, 8)] + [("feed", j) for j in range(F.FE_N)] + [("after", j) for j in range(4)]
    for (st, j) in seq:
        g = ground(W, H, seed=12, lit=(hx, hy, 70, 35))
        _paste(g, og_d[j % 6], hx - KP.OG_PIV[0], hy - KP.OG_PIV[1])
        if st == "burst":
            _paste(g, lb[j], hx - F.LB_PIV[0], hy - F.LB_PIV[1])
            spr = KV.frame(KV.leap, 6 + j % 2, "se")
        elif st == "feed":
            _paste(g, fs[j], hx - F.FS_PIV[0], hy - F.FS_PIV[1])
            _paste(g, fb[j], kx - F.FE_PIV[0], ky - F.FE_PIV[1])
            spr = KV.frame(KV.emerge, min(5, int(j * 0.8)), "se", True)
        else:
            _paste(g, F.aura()[j % 6], kx - F.AU_PIV[0], ky - F.AU_PIV[1])
            spr = KV.frame(KV.idle, j % 4, "se", True)
        _paste(g, spr, kx - KV.PIV[0], ky - KV.PIV[1])
        if st == "feed":
            _paste(g, ff[j], kx - F.FE_PIV[0], ky - F.FE_PIV[1])
        frames.append(g)
    comp = np.concatenate([frames[4 + 2], frames[4 + 4], frames[4 + 6]], 1)
    label(comp, 4, 3, "Огнище питает: поток · поглощение · вспышка (+15%)")
    paths["feed"] = _save_idx(comp, os.path.join(out, "krivsha_feed_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "krivsha_feed_scene.gif"), 10)
    # ---- 5. анчутки: стая Залесья + свита Огнеи, рядом герой для масштаба -------------------------
    W, H = 300, 110
    an_w = [AN.frame(AN.walk, i, "se") for i in range(6)]
    an_i = [AN.frame(AN.idle, i, "se") for i in range(4)]
    an_t = [AN.frame(AN.coal_throw, i, "se") for i in range(5)]
    mr_w = [MR.frame(MR.walk, i, "se") for i in range(6)]
    coal = AN.coal_fx()
    frames = []
    for i in range(12):
        g = ground(W, H, seed=14)
        for k, (ax, ay) in enumerate(((22, 70), (40, 92), (58, 76))):           # retinue behind Огнея
            _shadow(g, ax, ay, 5, 2)
            _paste(g, an_w[(i + k * 2) % 6], ax - AN.PIV[0], ay - AN.PIV[1])
        _shadow(g, 92, 84, 9, 3.5)
        _paste(g, mr_w[i % 6], 92 - MR.PIV[0], 84 - MR.PIV[1])
        _shadow(g, 166, 80, 5, 2)
        _paste(g, an_i[i % 4], 166 - AN.PIV[0], 80 - AN.PIV[1])
        _shadow(g, 184, 96, 5, 2)
        _paste(g, an_t[min(4, i // 2)], 184 - AN.PIV[0], 96 - AN.PIV[1])
        if i >= 6:
            cx_ = 184 + AN.THROW_SPAWN[0] + (i - 6) * 9
            _paste(g, coal[i % 3], int(cx_) - AN.CO_PIV[0], int(96 + AN.THROW_SPAWN[1] - (i - 6) * 1) - AN.CO_PIV[1])
        _shadow(g, 268, 92, 9, 3.5)
        _paste(g, hero_l, 268 - 32, 92 - 56)
        frames.append(g)
    comp = frames[7].copy()
    label(comp, 4, 3, "Анчутки 26: свита Огнеи · стая · бросок угля · герой 44")
    paths["anchutka"] = _save_idx(comp, os.path.join(out, "anchutka_scene_x3.png"))
    _save_gif(frames, os.path.join(out, "anchutka_scene.gif"), 8)
    MEAS["m1b_scenes"] = {k: os.path.relpath(v, ROOT) for k, v in paths.items()}


if __name__ == "__main__":
    M = {}
    run(M)
    print(json.dumps(M, ensure_ascii=False)[:6000])

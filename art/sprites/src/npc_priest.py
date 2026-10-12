"""Поп Иоанн (npc.priest, H19 map sprite, GDD v1.13.2 §7.1.1): standing NPC of Ладога, idle loop.
scale.md §2 NPC row: frame 48×56, pivot (24, 50), visible height 44, footprint 1×1 / r 0.30.
§4.1: SE and NE drawn, SW/NW = horizontal mirror. Built on the shared 46-px human rig (rig.py / human.py),
then cropped from the rig's 64×64 / (32, 56) cell to 48×56 / (24, 50).
Look = the portrait: black скуфья, dark подрясник to the ground, grey-streaked long hair to the shoulders,
long narrow wedge beard, small copper cross. Hands loosely clasped at the belt. No halo, book or blessing gesture."""
import os
import numpy as np
import rig
from rig import Painter, build, legend, rot, add
from human import Skel, arm, pose
import pixelkit as pk
import export as X

OUT = os.path.join(X.ROOT, "npc_priest")
FRAME, PIVOT = (48, 56), (24, 50)
CROP = (rig.PIVOT[0] - PIVOT[0], rig.PIVOT[1] - PIVOT[1])          # (8, 6)
FPS = 3

SCHEME = legend(
    T=("stone", 2, True, False), t=("stone", 1, False, False),     # подрясник: slate_dk with night shade
    C=("stone", 1, True, False), c=("ink", 0, False, False),       # скуфья: night / ink
    G=("stone", 4, True, False), g=("stone", 3, False, False),     # grey strands (slate_lt / slate)
    B=("wood", 1, False, False), b=("stone", 2, False, False),     # dark strands, brows
    L=("wood", 1, True, False),                                     # narrow leather belt
    Z=("bronze", 3, False, False), z=("bronze", 2, False, False),  # copper cross (bronze / bronze_dk)
)


def head(P, S, view, ph):
    hc, ha = S.hc, S.head_ang
    R = lambda a, b: add(hc, rot(a, b, ha))
    sway = (0, 0.3, 0.5, 0.3)[ph]
    if view == "se":
        # long hair behind the head (screen-left = back), 3 strands to the shoulder, uneven ends
        for (a0, a1, b1, ch) in ((-3.0, -3.6 - sway, 7.5, "g"), (-2.0, -2.6 - sway, 9.0, "B"), (-1.0, -1.4 - sway, 8.0, "G")):
            P.line(R(a0, -1.5), R(a1, b1), ch, 1)
        P.ellipse(R(-1.4, -0.6), 2.6, 3.2, "B")
        P.line(R(-2.6, -2.0), R(-2.8, 2.4), "G")                    # grey streak on the dark mass
        P.ellipse(R(0.7, 0.2), 3.1, 3.9, "S")
        # beard: long narrow wedge, grey-streaked
        P.poly([R(0.0, 1.6), R(1.6, 2.6), R(3.8, 1.8), R(3.6, 4.0), R(2.6, 7.0), R(1.8, 9.6), R(0.8, 6.4), R(-0.2, 3.6)], "G")
        P.line(R(1.6, 3.4), R(1.8, 8.2), "B")
        P.line(R(2.8, 3.0), R(2.6, 6.0), "g")
        P.line(R(1.8, 1.9), R(3.7, 1.7), "g")                       # moustache
        P.px(R(4.0, 0.2), "S"); P.px(R(4.2, 0.5), "S")              # nose
        P.px(R(2.5, -0.5), "k")                                     # eye (calm, slightly lowered)
        P.line(R(1.6, -1.6), R(3.2, -1.4), "g")                     # grey brow
        P.line(R(-0.6, -0.4), R(-0.6, 3.6), "g")                    # side lock over the ear (hides the ear)
    else:
        for (a0, a1, b1, ch) in ((-2.6, -2.8 + sway, 8.0, "G"), (-1.2, -1.2 + sway, 9.4, "B"), (0.2, 0.4 + sway, 8.6, "g"),
                                 (1.6, 1.9 + sway, 7.2, "B")):
            P.line(R(a0, -1.0), R(a1, b1), ch, 1)
        P.ellipse(R(0.0, 0.0), 3.4, 3.8, "B")
        P.line(R(-1.6, -2.4), R(-1.8, 3.0), "G"); P.line(R(1.0, -2.4), R(1.2, 3.2), "g")
        P.ellipse(R(2.6, 1.2), 1.0, 2.0, "S")                        # cheek edge
        P.poly([R(2.0, 3.0), R(3.4, 2.4), R(3.0, 5.6), R(2.2, 6.6)], "G")   # beard edge seen past the cheek
    clip = lambda xx, yy: yy <= (hc[1] - 1.6)
    P.ellipse(R(0.2, -1.6), 3.9, 3.2, "C", clip=clip)                # low rounded скуфья
    P.line(R(-3.6, -1.8), R(3.8, -2.0), "c")


def body(P, S, view, ph, breath):
    flip = 1 if view == "se" else -1
    gy = -S.pel[1]                                                   # ground in the pelvis frame (hem stays on the ground)
    T = lambda pts, ch: P.shape(S.pel, S.tor, [(a, b) for a, b in pts], ch, flip=flip)
    # feet (toe caps) peeking under the hem
    if view == "se":
        P.poly([(0.0, -1.6), (3.6, -1.4), (4.2, 0.0), (0.0, 0.0)], "O")
        P.poly([(-3.4, -2.2), (-0.6, -2.0), (-0.2, -0.8), (-3.4, -0.8)], "o")
    # подрясник: shoulders to the ground, slight flare
    robe = [(-5.4, -13.4 + breath), (4.8, -13.8 + breath), (5.8, -9.0), (6.2, 0.0), (7.0, gy - 0.6), (3.0, gy), (-1.0, gy - 0.4),
            (-5.0, gy), (-7.2, gy - 0.6), (-6.4, 0.0), (-6.0, -9.5)]
    T(robe, "T")
    P.shape(S.pel, S.tor, [(2.4, -13.4 + breath), (4.8, -13.8 + breath), (5.8, -9.0), (6.2, 0.0), (7.0, gy - 0.6), (3.6, gy)], "t")
    for a in (-2.6, 1.2):                                            # long folds
        P.line(add(S.pel, rot(a * flip, 1.0, S.tor)), add(S.pel, rot((a * 1.15) * flip, gy - 1.0, S.tor)), "t")
    T([(-6.0, -2.2), (5.8, -2.4), (5.8, -1.2), (-6.0, -1.0)], "L")  # belt
    if view == "se":
        hc = S.hc
        cx, cy = hc[0] + 1.6, hc[1] + 11.0 + breath * 0.5           # small cross on the chest below the beard tip
        P.line((cx, cy), (cx, cy + 3), "Z")
        P.line((cx - 1, cy + 1), (cx + 1, cy + 1), "Z")
        P.px((cx + 0.6, cy + 2), "z")


def draw(view, ph):
    breath = (0.0, -0.5, -0.9, -0.5)[ph]
    p = pose(pel=(0.0, -18.0), tor=0.0, head=4.0 if view == "se" else 0.0,
             hn=(2.4, 0.2, -18.6), hf=(2.6, 0.6, -18.2), eyes="open")
    p["pel"] = (0.0, -18.0 + breath * 0.0)
    S = Skel(p, view)
    S.hc = (S.hc[0], S.hc[1] + 1.0 - (1.0 if ph in (1, 2) else 0.0))   # head bob 1 px with the breath
    S.neck = (S.neck[0], S.neck[1] + 1.0)
    P = Painter()
    arm(P, S.sh_f, S.ef, S.hf, sleeve="t", cuff="t")
    body(P, S, view, ph, breath)
    head(P, S, view, ph)
    if view == "se":
        arm(P, S.sh_n, S.en, S.hn, sleeve="T", cuff="T", w=4, fist=False)   # wide sleeve, hands clasped at the belt
        P.ellipse(S.hn, 1.5, 1.3, "S")
    else:                                                          # from behind: sleeve only, the hands are in front of the body
        arm(P, S.sh_n, S.en, (S.hn[0] - 1.2, S.hn[1]), sleeve="T", cuff="T", w=4, fist=False)
    spr = build(P, SCHEME)
    idx = rig.to_index(spr)
    return idx[CROP[1]:CROP[1] + FRAME[1], CROP[0]:CROP[0] + FRAME[0]]


def run():
    rows, labels = [], []
    for view in ("se", "ne"):
        frames = [draw(view, ph) for ph in range(4)]
        for f in frames:                                          # nothing must be cut by the 48×56 crop
            assert not (f[0] >= 0).any() and not (f[:, 0] >= 0).any() and not (f[:, -1] >= 0).any()
        hs = [int(PIVOT[1] - np.where((f >= 0).any(1))[0].min() + 1) for f in frames]
        X.save_sheet(frames, OUT, "npc_priest_idle_" + view, dict(
            character="Поп Иоанн (npc.priest, speaker id priest)", animation="idle", direction=view,
            mirror_for="sw" if view == "se" else "nw",
            mirror_rule="flip horizontally around the frame centre line x = 24.0; pivot stays (24, 50)",
            pivot=list(PIVOT), fps=FPS, loop=True, visible_height_px=hs,
            height_rule="pivot row (soles) to the top visible pixel, outline included",
            footprint_tiles=[1, 1], collision_r=0.30,
            stands_at="Ладога (27.0; 13.6), у южной паперти церкви Климента (GDD v1.13.2 §7.1.1)",
            notes="scale.md §2 NPC: кадр 48×56, pivot (24,50), рост 44. Стоит на месте, idle 4 кадра (дыхание: голова и плечи на 1 px, "
                  "пряди чуть качаются). Тёмный подрясник до земли, чёрная скуфья, длинные волосы с проседью до плеч, длинная узкая "
                  "борода клином, маленький медный крест. Без нимба, книги и благословляющего жеста. Красного нет (scale.md §4.4)."))
        rows.append(frames); labels.append(view.upper())
    X.preview(rows, labels, os.path.join(OUT, "preview"), "npc_priest_idle", FPS, True, PIVOT, shadow_w=14,
              title="Поп Иоанн — idle (SE, NE; SW/NW зеркалом)")
    return {r: [int(PIVOT[1] - np.where((f >= 0).any(1))[0].min() + 1) for f in fr] for r, fr in zip(labels, rows)}


if __name__ == "__main__":
    print(run())

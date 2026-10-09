"""«Горелый пень» — prop_stump_burnt (GDD v1.11, Залесье: края поляны Огнеи — горелые пни и пепел вместо елей).
No stump existed in art/ or in the prototype (props.js has no 'stump'; the teaser's stump() is a painted idol stump),
so this is the minimal one: 3 static variants in one strip (frame = variant, fps 0), palette v2, alpha 0/255,
1-px ink outline (make_sprite). Charcoal trunk (wood_dk / ink with the cracked char pattern), grey ash on the cut and
around the roots, no embers (decor must not read as Mara's burning ash trail, which does damage).

  frame 24x22, pivot (12,18) = ground point at the trunk centre (tile centre of the prop);
  0 — cut stump (low, ~9 px), 1 — broken snag (splintered top, ~15 px), 2 — wide low stump with a root plate (~7 px).
Footprint in the game: none (decor; fp 0x0 like the 'ash' prop)."""
import math
import numpy as np
import rig                       # palette v2
import pixelkit as pk

W, H = 22, 20                    # MatCanvas; make_sprite adds 1-px outline -> 24x22
PIVOT = (12, 18)                 # frame coords; material row 17 = ground line under the trunk
GX, GY = 11, 17                  # ground point in MatCanvas coords

LEG = {
    "c": ("wood", 1, False, False),          # charcoal trunk (wood_dk)
    "C": ("wood", 0, False, False),          # deep char cracks (ink)
    "d": ("wood", 2, False, False),          # char highlight (wood)
    "s": ("stone", 2, False, False),         # charred cut, dark (slate_dk)
    "a": ("stone", 4, False, False),         # ash (slate_lt)
    "A": ("stone", 5, False, False),         # light ash (mist)
    "g": ("stone", 3, False, False),         # ash shadow (slate)
}


def _trunk(m, x0, x1, ytop, ybot, ch="c"):
    m.rect(x0, ytop, x1 - x0 + 1, ybot - ytop + 1, ch)


def _cracks(m, x0, x1, ytop, ybot, seed):
    """irregular char cracks (alligatoring): short vertical runs that jog sideways, a few ink pits."""
    rnd = np.random.default_rng(40 + seed)
    for x in range(x0 + 1, x1, 2):
        if rnd.random() < 0.35:
            continue
        y, cx = ytop + int(rnd.integers(0, 3)), x
        n = int(rnd.integers(2, 5))
        for _ in range(n):
            if y > ybot - 1:
                break
            m.px(cx, y, "C")
            y += 1
            if rnd.random() < 0.3:
                cx = min(x1 - 1, max(x0 + 1, cx + int(rnd.choice((-1, 1)))))


def variant(i):
    m = pk.MatCanvas(W, H)
    if i == 0:                                               # cut stump
        for (a, b) in (((5, 17), (8, 15)), ((17, 18), (14, 15)), ((10, 19), (11, 16))):   # roots
            m.line(a[0], a[1], b[0], b[1], "c", w=2)
        _trunk(m, 8, 14, 9, 17)
        m.ellipse(11.0, 9.0, 3.6, 1.6, "s")                  # cut top
        m.px(9, 9, "a"); m.px(10, 8, "A"); m.px(13, 9, "a"); m.px(12, 10, "g")
        _cracks(m, 8, 14, 10, 16, 0)
        m.line(9, 10, 9, 15, "d")
    elif i == 1:                                             # broken snag
        for (a, b) in (((4, 17), (8, 15)), ((18, 17), (14, 14))):
            m.line(a[0], a[1], b[0], b[1], "c", w=2)
        _trunk(m, 8, 13, 6, 17)
        m.poly([(8, 7), (9, 2), (10, 5), (11, 0), (12, 4), (13, 3), (13, 7)], "c")       # splintered top
        m.line(11, 1, 11, 6, "d")
        _cracks(m, 8, 13, 6, 16, 1)
        m.line(9, 7, 9, 14, "d")
        m.px(9, 12, "a"); m.px(10, 12, "a")                  # ash caught on a check
    else:                                                    # wide low stump, root plate
        for (a, b) in (((2, 17), (7, 15)), ((20, 17), (15, 15)), ((6, 19), (9, 16)), ((15, 19), (13, 16))):
            m.line(a[0], a[1], b[0], b[1], "c", w=2)
        _trunk(m, 7, 15, 11, 17)
        m.ellipse(11.0, 11.0, 4.6, 1.8, "s")
        m.ellipse(11.0, 11.0, 2.2, 0.9, "C")                 # burnt-out heart
        m.px(8, 11, "A"); m.px(14, 10, "a"); m.px(13, 12, "a")
        _cracks(m, 7, 15, 12, 16, 2)
        m.line(8, 13, 8, 15, "d")
    spr = pk.make_sprite(m.rows(), LEG)
    return pk.sprite_to_index(spr)


def _ring_layer(i):
    """ash on the ground around the roots: no ink outline (it is a flat decal), irregular edge."""
    m = pk.MatCanvas(W + 2, H + 2)
    rx, ry = (9.0, 3.0, 8.0, 2.8, 10.0, 3.2)[i * 2:i * 2 + 2]
    cx, cy = GX + 1.5, GY + 2.0
    yy, xx = np.mgrid[0:H + 2, 0:W + 2]
    ang = np.arctan2((yy + 0.5 - cy) * 2.5, xx + 0.5 - cx)
    wob = 1.0 + 0.16 * np.sin(ang * 3 + i * 1.7) + 0.10 * np.sin(ang * 5 + 0.6 + i)
    d = np.hypot((xx + 0.5 - cx) / rx, (yy + 0.5 - cy) / ry) / wob
    m.a[d <= 1.0] = "g"
    m.a[(d <= 0.82)] = "a"
    m.a[(d > 0.82) & (d <= 1.0) & ((xx + yy) % 2 == 0)] = "a"
    for (dx, dy) in ((-rx * 0.6, 0.5), (rx * 0.45, -0.5), (rx * 0.75, 0.6)):
        x, y = int(round(cx + dx)), int(round(cy + dy))
        if m.a[y, x] == "a":
            m.a[y, x] = "A"
    spr = pk.make_sprite(m.rows(), LEG, outline=False)
    return pk.sprite_to_index(spr)


def frames():
    out = []
    for i in range(3):
        top = variant(i)
        ring = _ring_layer(i)
        f = ring.copy()
        f[top >= 0] = top[top >= 0]
        out.append(f)
    return out

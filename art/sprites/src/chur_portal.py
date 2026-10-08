"""Чуров проход (GDD §4.4: «Береста возврата открывает Чуров проход в Ладогу и обратно на 60 с»; §12.1.5:
«Чуров проход — 8 кадров», P0; act1_texts obj.chur_portal «Проход от бересты возврата»). Prototype: object type
'portal' (src/systems/portal.js, src/render/portal.js grey box «стоячий овал из бронзового огня с тёплым ядром и
искрами»): two ends (field + town at the крада), 60 s of game time, both ends look the same.

Look: a standing oval doorway ~1.2 hero heights tall (top 54 px, hero 44) framed in bronze Чур-fire (the same
bronze as the резы of the Чуров камень and the safe ring), deep sea/navy inside with a slow spiral and a warm
far-away core (the way home). On the ground a bronze ring (r 0.8 tile) with 4 Чур signs. Bronze / linen / sea /
ember sparks; no red, no nebyl (it is Быль's road, not Небыль's).

States (no "closed" sprite: when closed the passage does not exist — GDD §4.4, prototype closePortal removes it):
  fx_chur_portal_open    6 frames @10, once  — opening: ring lights, light slit rises, splits into the oval
  fx_chur_portal_loop    8 frames @10, loop  — open (GDD «8 кадров»)
  fx_chur_portal_fading  8 frames @10, loop  — optional: the last 10 s (flicker baked in; replaces the alpha flicker)
  fx_chur_portal_close   6 frames @10, once  — closing: oval narrows to a slit, sinks into the ring, ring dies
Frame 64x84, pivot (32,74) = the object's ground point (centre of the ring, bottom of the oval)."""
import math
import numpy as np
import rig                       # palette v2
import pixelkit as pk
from pixelkit import C

TAU = math.tau
W, H, PIV = 64, 84, (32, 74)
CX, CY = PIV
OV_C = -28.0                     # oval centre above the ground point
OV_RX, OV_RY = 12.5, 25.5        # outer rim -> top at -54 (outline -55)
RING_R = 0.8                     # tiles
RING_RX, RING_RY = RING_R * 22.63, RING_R * 11.31

_YY, _XX = np.mgrid[0:H, 0:W]
_X = _XX + 0.5 - CX
_Y = _YY + 0.5 - CY


def _hash(a, b, c=0):
    return (math.sin(a * 12.9898 + b * 78.233 + c * 37.719) * 43758.5453) % 1.0


def _put(out, x, y, c):
    x, y = int(round(CX + x)), int(round(CY + y))
    if 0 <= x < W and 0 <= y < H:
        out[y, x] = c


GLYPHS = {   # Чур signs (3x3 / 3x4), like the резы of the Чуров камень
    "arrow": ["010", "111", "010", "010"],
    "rhomb": ["010", "101", "010"],
    "fork": ["101", "010", "010"],
    "cross": ["010", "111", "010"],
}


def _glyph(out, name, x, y, c):
    rows = GLYPHS[name]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "1":
                _put(out, x - 1 + i, y - len(rows) + 1 + j, c)


def _ground(out, ph, lvl):
    """bronze ring with 4 signs; lvl 0..1 (0 = nothing). The back half is drawn now, the front half later."""
    if lvl <= 0:
        return
    rx, ry = RING_RX * min(1.0, 0.45 + 0.55 * lvl), RING_RY * min(1.0, 0.45 + 0.55 * lvl)
    e = (_X / rx) ** 2 + (_Y / ry) ** 2
    b = pk.bayer(H, W)
    glow = (e < 1.0) & (b < 0.22 * lvl)
    out[glow] = C["bronze_dk"]
    ring = (e < 1.0) & (e >= 0.8)
    out[ring] = C["bronze"] if lvl < 0.8 else C["bronze_lt"]
    # running highlight along the ring
    ang = np.arctan2(_Y / ry, _X / rx)
    hl = ring & (np.cos(ang - ph * TAU) > 0.92)
    out[hl] = C["bronze_hi"] if lvl >= 0.8 else C["bronze_lt"]


def _ground_signs(out, ph, lvl, front):
    if lvl <= 0.4:
        return
    for k, (a, name) in enumerate(((0.5 * math.pi, "arrow"), (math.pi, "rhomb"), (0.0, "fork"), (1.5 * math.pi, "cross"))):
        x, y = math.cos(a) * (RING_RX - 4.5), math.sin(a) * (RING_RY - 2.5) + 1
        if front != (y > -1.5):
            continue
        lit = (int(ph * 4) % 4) == k
        _glyph(out, name, x, y, C["linen"] if lit and lvl >= 0.9 else C["bronze_hi"] if lvl >= 0.8 else C["bronze_lt"])


def _oval_masks(sx, sy):
    """outer / rim / inner masks of the oval scaled by (sx, sy) and sitting on the ground."""
    rx, ry = max(OV_RX * sx, 0.6), max(OV_RY * sy, 0.6)
    cy = -ry - 2.5
    e = (_X / rx) ** 2 + ((_Y - cy) / ry) ** 2
    ei = (_X / max(rx - 2.2, 0.4)) ** 2 + ((_Y - cy) / max(ry - 2.2, 0.4)) ** 2
    return e, ei, rx, ry, cy


def _oval(out, ph, sx, sy, bright=1.0, swirl=1.0, core=1.0):
    e, ei, rx, ry, cy = _oval_masks(sx, sy)
    inner, rim = ei < 1.0, (e < 1.0) & (ei >= 1.0)
    # outline (1 px ink outside the rim)
    m = e < 1.0
    d = m.copy()
    d[1:, :] |= m[:-1, :]; d[:-1, :] |= m[1:, :]; d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
    out[d & ~m] = C["ink"]
    # interior: deep sea with a slow spiral
    r = np.sqrt((_X / max(rx, 1)) ** 2 + ((_Y - cy) / max(ry, 1)) ** 2)
    th = np.arctan2((_Y - cy) / max(ry, 1), _X / max(rx, 1))
    v = np.sin(2.0 * th + 7.0 * r - ph * TAU * 2.0 * swirl)
    col = np.full(out.shape, C["navy"])
    col[v > 0.35] = C["sea_dk"]
    col[(v > 0.8) & (r > 0.25)] = C["sea"]
    col[r > 0.82] = np.where(v[r > 0.82] > 0, C["bronze_dk"], C["sea_dk"])   # warm fringe inside the rim
    out[inner] = col[inner]
    # warm core: the far end of the road (a small hearth light)
    if core > 0 and rx > 3:
        cr = (_X / (2.2 * core)) ** 2 + ((_Y - (cy + ry * 0.15)) / (5.0 * core)) ** 2
        out[inner & (cr < 1.0)] = C["bronze"]
        out[inner & (cr < 0.45)] = C["bronze_lt"]
        out[inner & (cr < 0.15)] = C["linen"]
    # rim: bronze fire, flowing highlights
    flow = np.cos(3.0 * th - ph * TAU * 3.0)
    rc = np.full(out.shape, C["bronze_lt"] if bright >= 0.75 else C["bronze"])
    rc[flow > 0.55] = C["bronze_hi"] if bright >= 0.75 else C["bronze_lt"]
    rc[(flow > 0.92) & (bright >= 1.0)] = C["linen"]
    rc[(ei >= 1.0) & (ei < 1.25) & (flow < 0.2)] = C["bronze"] if bright >= 0.75 else C["bronze_dk"]   # inner edge
    out[rim] = rc[rim]
    return rx, ry, cy


def _tongues(out, ph, rx, ry, cy, n=12, amp=1.0, bright=1.0):
    """little bronze flame licks pointing out of the rim (lean upward)."""
    for k in range(n):
        a = (k + 0.5) / n * TAU
        if math.sin(a) > 0.85:                                   # none under the oval (it stands on the ground)
            continue
        h = amp * (1.5 + 1.8 * (0.5 + 0.5 * math.sin(ph * TAU * 2 + k * 2.3)))
        x0, y0 = math.cos(a) * rx, cy + math.sin(a) * ry
        nx, ny = math.cos(a) / rx, math.sin(a) / ry
        nn = math.hypot(nx, ny)
        nx, ny = nx / nn, ny / nn
        ny -= 0.6                                                # flames rise
        nn = math.hypot(nx, ny)
        nx, ny = nx / nn, ny / nn
        for j in range(int(round(h)) + 1):
            c = C["bronze_hi"] if j < h * 0.5 else C["bronze_lt"]
            if bright < 0.75:
                c = C["bronze_lt"] if j < h * 0.5 else C["bronze"]
            _put(out, x0 + nx * (j + 0.6), y0 + ny * (j + 0.6), c)


def _sparks(out, ph, rx, ry, cy, n=7, bright=1.0):
    for k in range(n):
        t = (ph + k / n) % 1.0
        a = (_hash(k, 3) * 0.8 + 0.1) * math.pi + math.pi        # start on the upper half of the rim
        x = math.cos(a) * rx + math.sin(t * TAU + k) * 1.5
        y = cy + math.sin(a) * ry - t * 12.0
        if t < 0.85:
            _put(out, x, y, (C["flame"] if k % 3 == 0 else C["bronze_hi"]) if bright >= 0.75 else C["bronze_lt"])


def _frame(ph, ring=1.0, sx=1.0, sy=1.0, bright=1.0, slit=None, flash=False, sparks=7, tongues=1.0, swirl=1.0, core=1.0):
    out = np.full((H, W), -1, np.int16)
    _ground(out, ph, ring)
    _ground_signs(out, ph, ring, front=False)
    if slit is not None:                                          # vertical light slit (opening / closing)
        sw, sh = slit
        if sh > 0:
            m = (np.abs(_X) <= sw / 2.0 + 0.01) & (_Y <= -1.0) & (_Y >= -1.0 - sh)
            out[m] = C["bronze_hi"]
            mc = (np.abs(_X) <= max(0.0, sw / 2.0 - 1.0) + 0.01) & (_Y <= -2.0) & (_Y >= -sh)
            out[mc] = C["linen"]
            edge = (np.abs(_X) <= sw / 2.0 + 1.01) & (np.abs(_X) > sw / 2.0 + 0.01) & (_Y <= -1.0) & (_Y >= -1.0 - sh)
            out[edge & (out < 0)] = C["bronze"]
    if sx > 0.05:
        rx, ry, cy = _oval(out, ph, sx, sy, bright, swirl, core)
        if tongues > 0:
            _tongues(out, ph, rx, ry, cy, amp=tongues, bright=bright)
        if sparks:
            _sparks(out, ph, rx, ry, cy, n=sparks, bright=bright)
        if flash:                                                 # opening flash: rim goes linen
            e, ei, *_ = _oval_masks(sx, sy)
            out[(e < 1.0) & (ei >= 1.0)] = C["linen"]
    _ground_signs(out, ph, ring, front=True)
    return out


def open_loop(n=8):
    return [_frame(i / n) for i in range(n)]


def fading(n=8):
    """last 10 s: the passage gutters — every other frame dim, the spiral slows, fewer sparks."""
    return [_frame(i / n, ring=0.8 if i % 2 else 1.0, bright=0.6 if i % 2 else 0.9, sparks=3, tongues=0.5 if i % 2 else 0.8,
                   core=0.7 if i % 2 else 0.9) for i in range(n)]


OPEN = [  # (ring, slit (w, h) or None, sx, sy, flash)
    dict(ring=0.5, slit=(1, 10), sx=0.0, sparks=0),
    dict(ring=0.8, slit=(2, 34), sx=0.0, sparks=0),
    dict(ring=1.0, slit=(2, 50), sx=0.25, sy=0.95, sparks=0, tongues=0.0),
    dict(ring=1.0, sx=0.6, sy=1.0, flash=True, sparks=3, tongues=0.5, core=0.5),
    dict(ring=1.0, sx=0.9, sy=1.0, sparks=5, tongues=1.4),
    dict(ring=1.0, sx=1.0, sy=1.0, sparks=7, tongues=1.2),
]
CLOSE = [
    dict(ring=1.0, sx=0.85, sy=1.0, bright=0.9, sparks=5, tongues=0.8),
    dict(ring=1.0, sx=0.5, sy=0.95, flash=True, sparks=3, tongues=0.5, core=0.5),
    dict(ring=0.9, sx=0.18, sy=0.85, slit=(2, 40), sparks=0, tongues=0.0),
    dict(ring=0.8, slit=(2, 22), sx=0.0, sparks=0),
    dict(ring=0.6, slit=(1, 8), sx=0.0, sparks=0),
    dict(ring=0.35, sx=0.0, sparks=0),
]


def opening():
    return [_frame(i / 8.0, **d) for i, d in enumerate(OPEN)]


def closing():
    fr = [_frame(i / 8.0, **d) for i, d in enumerate(CLOSE)]
    for i, f in enumerate(fr[3:], 3):                             # last puff of sparks rising from the ring
        for k in range(4 - (i - 3)):
            _put(f, -6 + k * 4 + (i % 2), -6 - (i - 3) * 6 - k * 2, C["bronze_hi"] if k % 2 else C["bronze_lt"])
    return fr


def visible_height(idx):
    rows = np.where((idx >= 0).any(1))[0]
    return int(PIV[1] - rows.min() + 1) if len(rows) else 0


def body_top(idx):
    """top of the oval incl. its ink outline (sparks / tongues excluded)."""
    rows = np.where((idx == C["ink"]).sum(1) >= 2)[0]
    return int(PIV[1] - rows.min() + 1) if len(rows) else 0

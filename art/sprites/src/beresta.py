"""«Береста возврата» (GDD §4.4: свиток портала — открывает Чуров проход в Ладогу и обратно на 60 с, каст 1 с,
цена 25, стопка до 20, 1x1 в котомке; «не путать с берестяными грамотами»). Prototype: item kind 'scroll',
scroll 'beresta', icon key 'beresta' (items.png atlas via tools/export_ui.py <- art/ui/src/items_rus.build()),
ground item drawn by drawGroundItem (grey box: 12x5 birch roll).

Look: a tight roll of white birch bark (dark lenticel dashes) tied with bronze wire, lying diagonally; the free end
is curled out showing the tan inner side with a burning Чур sign (ember rhomb) scratched into it — the same bronze /
ember language as the Чуров проход and the Чуров камень. The old icon (horizontal roll with a red cord) read like
the «Берестяная грамота» letter; this one is diagonal, compact, and has no red.

  icon:   20x20 (fits the 24-px 1x1 cell like the other 1x1 icons, e.g. old beresta 20x18), palette v2, ink outline
  ground: 18x12, pivot (9, bottom outline row), 4 frames @6 loop (the sign glints; frame 0 works as a static sprite)"""
import math
import numpy as np
import rig                       # palette v2
import pixelkit as pk
from pixelkit import C

LEG = {
    "p": ("birch", 4, True, False),              # outer bark (white)
    "P": ("birch", 3, False, False),             # bark in shade
    "Q": ("birch", 1, False, False),             # lenticel dashes
    "o": ("wood", 4, True, False),               # inner bark (tan)
    "O": ("wood", 3, False, False),              # spiral layers / flap shade
    "i": ("bronze", 3, False, False),            # bronze wire
    "I": ("bronze", 2, False, False),
    "k": ("ink", 0, False, False),
    "e": ("fire", 2, False, True),               # ember (sign)
    "f": ("fire", 3, False, True),               # flame (sign core / glint)
    "w": ("birch", 5, False, False),             # linen glint
}


def _rot_ellipse(m, c, a, b, ang, ch):
    """filled ellipse with semi-axes a (along ang) and b."""
    h, w = m.a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    dx, dy = xx + 0.5 - c[0], yy + 0.5 - c[1]
    ca, sa = math.cos(ang), math.sin(ang)
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    m.a[(u / a) ** 2 + (v / b) ** 2 <= 1.0] = ch


def _capsule(m, A, B, r, ch):
    h, w = m.a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    px, py = xx + 0.5, yy + 0.5
    ax, ay = B[0] - A[0], B[1] - A[1]
    L2 = ax * ax + ay * ay
    t = np.clip(((px - A[0]) * ax + (py - A[1]) * ay) / L2, 0, 1)
    d = np.hypot(px - (A[0] + ax * t), py - (A[1] + ay * t))
    m.a[d <= r] = ch


def _roll(m, A, B, r, sign_at, sign, glint=None, wire=(1.0,), lent=True, wire_t=0.34):
    ax, ay = B[0] - A[0], B[1] - A[1]
    L = math.hypot(ax, ay)
    ux, uy = ax / L, ay / L                       # roll axis
    nx, ny = uy * -1, ux                          # perpendicular
    if ny < 0:
        nx, ny = -nx, -ny                         # make it point downward (shade side)
    ang = math.atan2(uy, ux)
    _capsule(m, A, B, r, "p")
    # shade: lower edge of the roll
    h, w = m.a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    v = (xx + 0.5 - A[0]) * nx + (yy + 0.5 - A[1]) * ny
    m.a[(m.a == "p") & (v > r * 0.45)] = "P"
    if lent:                                      # lenticel dashes (across the roll)
        for t, off in ((0.55, -1.6), (0.88, 0.3), (0.50, 1.2)):
            cx, cy = A[0] + ax * t + nx * off, A[1] + ay * t + ny * off
            m.line(int(round(cx - ux * 0.5)), int(round(cy - uy * 0.5)), int(round(cx + ux * 0.8)), int(round(cy + uy * 0.8)), "Q")
    if wire:                                      # bronze wire band around the roll (near end)
        u = (xx + 0.5 - A[0]) * ux + (yy + 0.5 - A[1]) * uy
        u0 = L * wire_t
        inside = np.isin(m.a, ["p", "P", "Q"])
        band = inside & (np.abs(u - u0) <= wire[0])
        m.a[band] = "i"
        m.a[band & (v > r * 0.45)] = "I"
    # near end: rolled layers (tan inner bark, dark spiral)
    _rot_ellipse(m, A, max(1.1, r * 0.38), r, ang, "o")
    _rot_ellipse(m, A, max(0.6, r * 0.2), r * 0.55, ang, "O")
    m.px(int(A[0]), int(A[1]), "k")
    sx, sy = sign_at
    for (dx, dy) in sign:
        m.px(sx + dx, sy + dy, "e")
    m.px(sx, sy, "f")
    if glint:
        for (gx, gy, ch) in glint:
            m.px(gx, gy, ch)


RHOMB = ((0, -1), (-1, 0), (1, 0), (0, 1))


def icon_sprite():
    """make_sprite dict (what art/ui/src/items_rus.build() returns per key; used by prototype/tools/export_ui.py)."""
    m = pk.MatCanvas(18, 18)
    _roll(m, (4.0, 13.5), (13.8, 3.7), 3.6, sign_at=(11, 6), sign=RHOMB)
    return pk.make_sprite(m.rows(), LEG)


def icon():
    return pk.sprite_to_index(icon_sprite())


GLINT = [None, ((10, 2, "f"),), ((10, 2, "w"), (11, 1, "f")), None]


def ground(n=4):
    out = []
    for i in range(n):
        m = pk.MatCanvas(16, 10)
        _roll(m, (3.2, 6.0), (12.8, 3.6), 2.6, sign_at=(10, 4), sign=RHOMB if i in (1, 2) else RHOMB[1:3],
              glint=GLINT[i], lent=False, wire=(0.6,), wire_t=0.3)
        spr = pk.make_sprite(m.rows(), LEG)
        out.append(pk.sprite_to_index(spr))
    return out


IC_W, IC_H = 20, 20

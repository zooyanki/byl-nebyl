"""HUD layers for the teaser (teaser.md §6.2): RGBA, alpha 0/255.
Darkening overlays become a 50% ink checker on transparent pixels."""
from teaser_world import *          # noqa
from teaser_world import _r          # noqa
import theme_rus as T
import ui_rus as U
from fonts_ru import FONT_RU, FONT_USTAV

TR = 255


class HudCanvas(Canvas):
    """Canvas whose empty pixels are transparent (TR). remap() darkens opaque
    pixels as usual and turns transparent ones into a 50% ink checker; ink
    dithers only touch opaque pixels (the checker already is the dimming)."""

    def __init__(self):
        super().__init__(W, H, TR)

    def remap(self, x, y, w, h, lut):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        sub = self.a[y0:y1, x0:x1]
        tr = sub == TR
        lut = np.asarray(lut, dtype=np.uint8)
        sub[~tr] = lut[sub[~tr]]
        yy, xx = np.mgrid[y0:y1, x0:x1]
        sub[tr & ((xx + yy) % 2 == 0)] = C["ink"]

    def dither(self, x, y, w, h, c, density=0.5, ox=0, oy=0):
        if c != C["ink"]:
            return super().dither(x, y, w, h, c, density, ox, oy)
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        b = pk.bayer(y1 - y0, x1 - x0, x0 + ox, y0 + oy)
        sub = self.a[y0:y1, x0:x1]
        sub[(b < density) & (sub != TR)] = c


def tick(cv, x, y, c):
    pts = ((6, 0), (5, 1), (4, 2), (0, 2), (3, 3), (1, 3), (2, 4))
    for (dx, dy) in pts:                          # ink outline first
        for (ox, oy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            cv.px(x + dx + ox, y + dy + oy, C["ink"])
    for (dx, dy) in pts:
        cv.px(x + dx, y + dy, c)


def draw_quest_t(cv, x, y, title, act, goals, max_right=229):
    """Tracker as G.draw_quest, with done goals (slate_lt + tick) and an
    automatic two-line title if the frame would reach the target plate."""
    first, rest = title[0], title[1:]
    tw = pk.text_width(rest, FONT_USTAV)
    gw = max(pk.text_width(g, FONT_RU) + (pk.text_width(n, FONT_RU) + 8 if n else 0) + (10 if d else 0)
             for g, n, _, d in goals)
    w1 = max(186, 26 + 4 + tw + 6 + 14 + 4, gw + 16)
    lines = [rest]
    if x + w1 > max_right:
        a, b = rest.split(" ", 1)
        lines = [a, b]
        tw = max(pk.text_width(a, FONT_USTAV), pk.text_width(b, FONT_USTAV))
    w = max(186, 26 + 4 + tw + 6 + 14 + 4, gw + 16)
    lh = 12
    h = 80 + (len(lines) - 1) * lh
    assert x + w <= max_right, (w, title)
    ix, iy, iw, ih = U.carved_frame(cv, x, y, w, h, fill="dim")
    bw, bh = U.bukvitsa(cv, ix + 1, iy + 1, first)
    tx = ix + bw + 4
    T.text_ru(cv, tx, iy + 2, act, C["mist"])
    for i, ln in enumerate(lines):
        T.text_ru(cv, tx, iy + 15 - FONT_USTAV.get("top", 0) + i * lh, ln, C["bronze_hi"], font=FONT_USTAV)
    oy = max(iy + bh + 3, iy + 15 + len(lines) * lh + 1) if len(lines) > 1 else iy + bh + 3
    for i, (g, n, col, done) in enumerate(goals):
        T.text_ru(cv, ix + 3, oy + 10 * i, g, C[col])
        rx = ix + iw - 3
        if done:
            tick(cv, rx - 7, oy + 10 * i + 1, C["bronze_lt"])
            rx -= 10
        if n:
            T.text_ru(cv, rx, oy + 10 * i, n, C[col], align="r")
    return (x, y, w, h)


def draw_zone_t(cv, title, sub):
    w = max(pk.text_width(title, FONT_RU), pk.text_width(sub, FONT_RU)) + 12
    w = max(w, 110)
    cv.remap(W - w, 0, w, 24, pk.DARKEN2)
    cv.dither(W - w, 0, w, 24, C["ink"], 0.3)
    for k in range(0, w, 4):
        cv.px(W - w + k, 23, C["bronze"] if k % 8 else C["bronze_lt"])
    T.text_ru(cv, 633, 3, title, C["bronze_lt"], align="r")
    T.text_ru(cv, 633, 13, sub, C["mist"], align="r")


def draw_minimap_t(cv, dark, marks, x=506, y=26, w=128, h=84):
    """Opaque minimap rect: the scene darkened + map symbols (hero-centred,
    same 2.2 scale as gameplay_hud_v2)."""
    region = np.zeros((H, W), bool); region[y:y + h, x:x + w] = True
    cv.a[region] = dark[region]
    Canvas.dither(cv, x, y, w, h, C["ink"], 0.3)
    saved = cv.a.copy()
    cx, cy = x + w // 2, y + h // 2 + 6
    hu, hv = inv_proj(*HERO)
    k = 2.2

    def M(sx, sy):
        u, v = inv_proj(sx, sy)
        return (int(cx + (u - hu) * k - (v - hv) * k), int(cy + (u - hu) * k / 2 + (v - hv) * k / 2))
    for mk in marks:
        kind = mk[0]
        if kind == "poly":
            pts = [M(*p) for p in mk[1]]
            for (p, q) in zip(pts, pts[1:]):
                n = max(abs(q[0] - p[0]), abs(q[1] - p[1]), 1)
                for t in range(n + 1):
                    if not mk[3] or t % 2 == 0:
                        cv.px(p[0] + (q[0] - p[0]) * t // n, p[1] + (q[1] - p[1]) * t // n, C[mk[2]])
        elif kind == "dot":
            px_, py_ = M(*mk[1]); cv.px(px_, py_, C[mk[2]])
            if len(mk) > 3 and mk[3]:
                cv.px(px_ + 1, py_, C[mk[2]]); cv.px(px_, py_ + 1, C[mk[2]]); cv.px(px_ + 1, py_ + 1, C[mk[2]])
        elif kind == "rift":
            px_, py_ = M(*mk[1]); cv.line(px_ - 1, py_ - 5, px_ + 1, py_ + 3, C["nebyl"]); cv.px(px_ + 1, py_ - 2, C["nebyl"])
        elif kind == "forest":
            m = region & (pk.hash2(XX, YY, 3) < 0.11) & (YY < y + mk[1])
            cv.a[m] = C["pine"]
    cv.a[~region] = saved[~region]
    for mk in marks:
        if mk[0] == "quest":
            qx, qy = M(*mk[1])
            if x + 3 < qx < x + w - 3 and y + 3 < qy < y + h - 3:
                cv.disc(qx, qy, 3.5, C["ink"]); cv.disc(qx, qy, 2.6, C["bronze_lt"]); cv.px(qx, qy, C["ink"])
    cv.rect(cx - 2, cy, 5, 1, C["linen"]); cv.rect(cx, cy - 2, 1, 5, C["linen"]); cv.px(cx, cy, C["red_lt"])
    for (bx, by_, sx_, sy_) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        T.bronze_corner(cv, bx, by_, sx_, sy_, 7)
    for t in range(10, w - 10, 4):
        cv.px(x + t, y, C["wood_md"]); cv.px(x + t, y + h - 1, C["wood_md"])
    for t in range(10, h - 10, 4):
        cv.px(x, y + t, C["wood_md"]); cv.px(x + w - 1, y + t, C["wood_md"])


def hud_layer(spec, lit, L):
    cv = HudCanvas()
    dark = lit.flatten(L, extra=-2.4)
    draw_minimap_t(cv, dark, spec["minimap"])
    draw_zone_t(cv, *spec["zone"])
    G.draw_buttons(cv, 505, 114)
    if spec.get("target"):
        G.draw_target(cv, W // 2, 3, *spec["target"])
    q = spec["quest"]
    box = draw_quest_t(cv, 3, 3, q["title"], q["act"], q["goals"])
    G.HUD = dict(G.HUD, **spec["hud"])
    G.draw_bottom(cv, None, spec["skills"], xp_ratio=spec["xp"])
    return cv.a, box


def loot_layer(items):
    cv = HudCanvas()
    boxes = []
    for (text, col, x, y) in items:
        T.label_ru(cv, x, y, text, C[col])
        w = pk.text_width(text, FONT_RU) + 7
        boxes.append((x - w // 2, y, x - w // 2 + w - 1, y + 12))
    return cv.a, boxes


def composite(base, layer):
    out = base.copy()
    m = layer != TR
    out[m] = layer[m]
    return out

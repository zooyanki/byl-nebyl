"""
Window / menu widgets for the «Гардарики» theme (palette v2):
carved wood with triangle-notch резьба, forged iron, bronze fittings,
ustav titles, буквица initials. Call theme_rus.activate() first.
"""
import math
import numpy as np
import pixelkit as pk
from pixelkit import C, Canvas, FONT3x5
from fonts_ru import FONT_RU, FONT_USTAV
import theme_rus as T


def _sp(cv, x, y, c):
    cv.px(int(x), int(y), c)


# --------------------------------------------------------------------------
# буквица — decorated initial (manuscript style)
# --------------------------------------------------------------------------
def bukvitsa(cv, x, y, ch, scale=2, fg=None, hi=None, field=None, frame=True, vine=True):
    """Draw an ustav capital at `scale`, red with an ember highlight, in a small
    bronze-framed field with a curling vine. Returns (w, h) of the block."""
    fg = C["red_lt"] if fg is None else fg
    hi = C["ember"] if hi is None else hi
    g = FONT_USTAV["glyphs"][ch.upper()][1:12]           # cap rows only
    gs = np.kron(g, np.ones((scale, scale), bool))
    gh, gw = gs.shape
    pad = 4
    bw, bh = gw + pad * 2 + 2, gh + pad * 2
    if frame:
        cv.rect(x, y, bw, bh, C["ink"])
        cv.rect(x + 1, y + 1, bw - 2, bh - 2, field if field is not None else C["wood_dk"])
        cv.dither(x + 2, y + 2, bw - 4, bh - 4, C["red_dk"], 0.35)
        cv.frame(x + 1, y + 1, bw - 2, bh - 2, C["bronze"])
        cv.hline(x + 2, y + 1, bw - 4, C["bronze_lt"]); cv.vline(x + 1, y + 2, bh - 4, C["bronze_lt"])
        for (cx_, cy_) in ((x + 1, y + 1), (x + bw - 2, y + 1), (x + 1, y + bh - 2), (x + bw - 2, y + bh - 2)):
            cv.px(cx_, cy_, C["bronze_hi"])
    gx, gy = x + pad + 1, y + pad
    if vine:   # curling tendril behind the letter + leaves
        for k in range(40):
            t = k / 39
            vx = gx + gw * 0.5 + math.cos(t * 6.5) * (gw * 0.55) * (1 - t * 0.4)
            vy = gy + gh * (0.15 + t * 0.75) + math.sin(t * 6.5) * 2
            _sp(cv, vx, vy, C["moss_lt"] if k % 3 else C["moss"])
        for (lx, ly) in ((gx - 2, gy + 3), (gx + gw, gy + gh - 5)):
            cv.px(lx, ly, C["moss_lt"]); cv.px(lx + 1, ly, C["moss"]); cv.px(lx, ly + 1, C["moss"])
    # outline + fill + left highlight / right shade on every stem
    sub = cv.a[gy - 1:gy + gh + 1, gx - 1:gx + gw + 1]
    big = np.zeros((gh + 2, gw + 2), bool); big[1:-1, 1:-1] = gs
    ol = np.zeros_like(big)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ol |= np.roll(np.roll(big, dy, 0), dx, 1)
    sub[ol & ~big] = C["ink"]
    sub[big] = fg
    left = big & ~np.roll(big, 1, 1)
    right = big & ~np.roll(big, -1, 1)
    sub[left] = hi
    sub[right & ~left] = C["red"]
    return bw, bh


# --------------------------------------------------------------------------
# CARVED FRAMES
# --------------------------------------------------------------------------
def notch_band(cv, x, y, n, vertical=False, period=6):
    """6-px carved band: lit edge, wood body with triangle-notch резьба, dark edge."""
    for i in range(n):
        for r in range(6):
            if r == 0:
                c = C["wood_lt"]
            elif r == 5:
                c = C["wood_dk"]
            else:
                c = C["wood_md"]
                k = i % period
                # alternate up / down triangles (треугольно-выемчатая резьба)
                if 1 <= r <= 4:
                    if (i // period) % 2 == 0:
                        if abs(k - (period - 1) / 2) <= (r - 1) * 0.75 and r >= 2:
                            c = C["wood_dk"] if r > 2 else C["wood"]
                    else:
                        if abs(k - (period - 1) / 2) <= (4 - r) * 0.75 and r <= 3:
                            c = C["wood_dk"] if r < 3 else C["wood"]
                if k == 0 and r in (2, 3):
                    c = C["wood_lt"]
            if vertical:
                cv.px(x + r, y + i, c)
            else:
                cv.px(x + i, y + r, c)


def corner_plate(cv, x, y, s=9):
    cv.rect(x, y, s, s, C["ink"])
    cv.rect(x + 1, y + 1, s - 2, s - 2, C["bronze"])
    cv.hline(x + 1, y + 1, s - 2, C["bronze_lt"]); cv.vline(x + 1, y + 1, s - 2, C["bronze_lt"])
    cv.hline(x + 2, y + s - 2, s - 3, C["bronze_dk"]); cv.vline(x + s - 2, y + 2, s - 3, C["bronze_dk"])
    m = s // 2
    cv.px(x + m, y + m, C["ink"]); cv.px(x + m - 1, y + m - 1, C["bronze_hi"])
    for (dx, dy) in ((0, -2), (0, 2), (-2, 0), (2, 0)):
        cv.px(x + m + dx, y + m + dy, C["bronze_dk"])


def carved_frame(cv, x, y, w, h, fill="dim", corners=True, bw=6):
    """Carved wooden border (резьба) with bronze corner plates.
    fill: 'dim' (darkened see-through), 'planks' (dark wood), int colour, None."""
    ix, iy, iw, ih = x + bw + 1, y + bw + 1, w - 2 * bw - 2, h - 2 * bw - 2
    if fill == "dim":
        cv.remap(ix, iy, iw, ih, pk.DARKEN2)
        cv.dither(ix, iy, iw, ih, C["ink"], 0.45)
    elif fill == "planks":
        T.wood_planks(cv, ix, iy, iw, ih, seed=w + h, plank=14, dark=True)
        cv.remap(ix, iy, iw, ih, pk.DARKEN2)
        cv.dither(ix, iy, iw, ih, C["ink"], 0.25)
    elif fill is not None:
        cv.rect(ix, iy, iw, ih, fill)
    cv.frame(x, y, w, h, C["ink"])
    notch_band(cv, x + 1, y + 1, w - 2)
    notch_band(cv, x + 1, y + h - 7, w - 2)
    notch_band(cv, x + 1, y + 1, h - 2, vertical=True)
    notch_band(cv, x + w - 7, y + 1, h - 2, vertical=True)
    # mitre the corners: redraw the corner squares as end-grain blocks
    for (cx_, cy_) in ((x + 1, y + 1), (x + w - 7, y + 1), (x + 1, y + h - 7), (x + w - 7, y + h - 7)):
        cv.rect(cx_, cy_, 6, 6, C["wood"])
    cv.frame(x + bw, y + bw, w - 2 * bw, h - 2 * bw, C["ink"])
    cv.hline(x + bw + 1, y + h - bw - 1, w - 2 * bw - 2, C["wood_dk"])
    if corners:
        for (cx_, cy_) in ((x - 1, y - 1), (x + w - 8, y - 1), (x - 1, y + h - 8), (x + w - 8, y + h - 8)):
            corner_plate(cv, cx_, cy_, 9)
    return ix, iy, iw, ih


def iron_band(cv, x, y, w):
    """Forged iron strap with rivets (horizontal, 5 px)."""
    cv.rect(x, y, w, 5, C["ink"])
    cv.hline(x, y + 1, w, C["slate_lt"]); cv.hline(x, y + 2, w, C["slate"]); cv.hline(x, y + 3, w, C["slate_dk"])
    for k in range(4, w - 3, 14):
        cv.px(x + k, y + 1, C["mist"]); cv.px(x + k + 1, y + 2, C["ink"]); cv.px(x + k, y + 2, C["slate_lt"])


def close_button(cv, x, y, s=13, hover=False):
    """Forged iron plate with a bronze-edged X."""
    cv.rect(x, y, s, s, C["ink"])
    cv.rect(x + 1, y + 1, s - 2, s - 2, C["red_dk"] if hover else C["slate"])
    cv.hline(x + 1, y + 1, s - 2, C["red"] if hover else C["slate_lt"]); cv.vline(x + 1, y + 1, s - 2, C["red"] if hover else C["slate_lt"])
    cv.hline(x + 2, y + s - 2, s - 3, C["slate_dk"]); cv.vline(x + s - 2, y + 2, s - 3, C["slate_dk"])
    for i in range(s - 7):
        for c, o in ((C["ink"], 1), (C["flame"] if hover else C["bronze_lt"], 0)):
            cv.px(x + 3 + i + 0, y + 3 + i + o, c); cv.px(x + s - 4 - i, y + 3 + i + o, c)
    for (cx_, cy_) in ((x, y), (x + s - 1, y), (x, y + s - 1), (x + s - 1, y + s - 1)):
        cv.px(cx_, cy_, C["bronze_lt"])


def title_plate(cv, cx, y, title, font=FONT_USTAV, color=None):
    """Carved plaque with pointed (bracket) ends and an ustav title."""
    tw = pk.text_width(title, font)
    th = font.get("cap", font["h"])
    w, h = tw + 34, th + 9
    x = cx - w // 2
    pts = [(x, y + h // 2), (x + 8, y), (x + w - 9, y), (x + w - 1, y + h // 2), (x + w - 9, y + h - 1), (x + 8, y + h - 1)]
    m = cv.mask_poly(pts)
    tmp = Canvas(cv.w, cv.h)
    T.wood_planks(tmp, x, y, w, h, seed=tw, plank=h, dark=False)
    cv.a[m] = tmp.a[m]
    for i in range(len(pts)):
        (a, b), (c, d) = pts[i], pts[(i + 1) % len(pts)]
        cv.line(int(a), int(b), int(c), int(d), C["ink"])
    cv.line(x + 2, y + h // 2, x + 8, y + 2, C["bronze_lt"]); cv.hline(x + 8, y + 1, w - 17, C["bronze_lt"])
    cv.hline(x + 8, y + h - 2, w - 17, C["bronze_dk"])
    cv.line(x + 2, y + h // 2, x + 8, y + h - 3, C["bronze_dk"])
    cv.line(x + w - 3, y + h // 2, x + w - 9, y + 2, C["bronze"]); cv.line(x + w - 3, y + h // 2, x + w - 9, y + h - 3, C["bronze_dk"])
    for dx in (5, w - 6):
        cv.px(x + dx, y + h // 2, C["red_lt"]); cv.px(x + dx, y + h // 2 - 1, C["bronze_hi"])
    top = font.get("top", 0)
    T.text_ru(cv, cx + 1, y + 4 - top, title, color if color is not None else C["bronze_hi"], font=font, align="c")
    return x, w, h


def window(cv, x, y, w, h, title=None, close=True, close_hover=False, fill="planks"):
    """Carved-wood window. Returns inner content rect (x, y, w, h)."""
    ix, iy, iw, ih = carved_frame(cv, x, y, w, h, fill=fill)
    if title:
        title_plate(cv, x + w // 2, y - 2, title)
    if close:
        close_button(cv, x + w - 22, y + 9, hover=close_hover)
    return ix, iy, iw, ih


def recess(cv, x, y, w, h, fill=None):
    """Sunken dark field (for values, lists)."""
    cv.rect(x, y, w, h, C["night"] if fill is None else fill)
    cv.dither(x + 1, y + 1, w - 2, h - 2, C["wood_dk"], 0.25)
    cv.frame(x, y, w, h, C["ink"])
    cv.hline(x + 1, y + h - 1, w - 1, C["wood_md"]); cv.vline(x + w - 1, y + 1, h - 1, C["wood_md"])
    cv.hline(x + 1, y + 1, w - 2, C["ink"])


def section_title(cv, x, y, w, text, c=None, font=FONT_RU):
    """Centred caption with carved rule and rosette dots either side."""
    c = C["bronze_lt"] if c is None else c
    tw = pk.text_width(text, font)
    cx = x + w // 2
    T.text_ru(cv, cx + 1, y, text, c, font=font, align="c")
    ly = y + 4
    tl, tr = cx + 1 - tw // 2, cx + 1 - tw // 2 + tw
    for (a, b) in ((x, tl - 8), (tr + 8, x + w)):
        if b > a:
            cv.hline(a, ly, b - a, C["bronze_dk"]); cv.hline(a, ly + 1, b - a, C["ink"])
            for k in range(a, b, 6):
                cv.px(k, ly, C["bronze"])
    for sx in (tl - 5, tr + 4):
        cv.px(sx, ly - 1, C["bronze_lt"]); cv.px(sx, ly + 1, C["bronze_lt"])
        cv.px(sx - 1, ly, C["bronze_lt"]); cv.px(sx + 1, ly, C["bronze_lt"]); cv.px(sx, ly, C["red_lt"])


def button(cv, x, y, w, h, label, state="normal", font=FONT_RU, seed=5):
    """Carved wood button with bronze rim. state: normal | hover | pressed | disabled."""
    cv.rect(x, y, w, h, C["ink"])
    T.wood_planks(cv, x + 1, y + 1, w - 2, h - 2, seed=seed, plank=h - 2, dark=(state != "hover"))
    if state == "disabled":
        cv.remap(x + 1, y + 1, w - 2, h - 2, pk.DARKEN1)
    rim = {"hover": C["bronze_hi"], "disabled": C["slate"], "pressed": C["bronze"]}.get(state, C["bronze"])
    cv.frame(x + 1, y + 1, w - 2, h - 2, rim)
    cv.hline(x + 2, y + 2, w - 4, C["wood_lt"] if state != "pressed" else C["wood_dk"])
    cv.hline(x + 2, y + h - 3, w - 4, C["wood_dk"])
    if state == "hover":
        cv.frame(x + 2, y + 2, w - 4, h - 4, C["bronze_lt"])
        cv.dither(x + 3, y + h - 7, w - 6, 4, C["ember"], 0.22)
    for (cx_, cy_, sx, sy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        T.bronze_corner(cv, cx_, cy_, sx, sy, 4)
    tc = {"hover": C["bronze_hi"], "disabled": C["slate_lt"], "pressed": C["bronze_lt"]}.get(state, C["birch"])
    off = 1 if state == "pressed" else 0
    cap, top = font.get("cap", 7), font.get("top", 0)
    T.text_ru(cv, x + w // 2 + 1 + off, y + (h - cap) // 2 - top + off, label, tc, font=font, align="c")
    if state == "hover":   # bronze rosette studs either side
        for sx in (x - 9, x + w + 2):
            cy = y + h // 2
            cv.disc(sx + 3.5, cy, 4, C["ink"]); cv.disc(sx + 3.5, cy, 3, C["bronze"])
            cv.px(sx + 3, cy, C["flame"]); cv.px(sx + 2, cy - 1, C["bronze_hi"])


def plus_button(cv, x, y, s=11, active=True):
    cv.rect(x, y, s, s, C["ink"])
    cv.rect(x + 1, y + 1, s - 2, s - 2, C["red"] if active else C["slate_dk"])
    cv.hline(x + 1, y + 1, s - 2, C["red_lt"] if active else C["slate"]); cv.vline(x + 1, y + 1, s - 2, C["red_lt"] if active else C["slate"])
    cv.hline(x + 2, y + s - 2, s - 3, C["red_dk"] if active else C["night"])
    cv.frame(x, y, s, s, C["bronze_lt"] if active else C["slate"])
    c = C["bronze_hi"] if active else C["slate_lt"]
    m = s // 2
    cv.rect(x + 3, y + m, s - 6, 1, c); cv.rect(x + m, y + 3, 1, s - 6, c)
    cv.frame(x - 1, y - 1, s + 2, s + 2, C["ink"])


def tooltip(cv, x, y, lines, pad=5, gap=2, anchor="tl", min_w=0, sep_after=()):
    """Item tooltip: dark see-through plate, bronze-cornered frame, centred lines.
    lines: (text, colour[, font]). Returns rect."""
    fonts = [t[2] if len(t) > 2 else FONT_RU for t in lines]
    ws = [pk.text_width(t[0], f) if t[0] else 0 for t, f in zip(lines, fonts)]
    hs = [f.get("cap", f["h"]) + (2 if f is FONT_RU else 3) for f in fonts]
    w = max(max(ws) + pad * 2 + 2, min_w)
    h = sum(hs) + gap * (len(lines) - 1) + pad * 2 + 3 * len(sep_after)
    if anchor in ("tr", "br"):
        x -= w
    if anchor in ("bl", "br"):
        y -= h
    cv.remap(x, y, w, h, pk.DARKEN3)
    cv.dither(x, y, w, h, C["ink"], 0.55)
    cv.frame(x, y, w, h, C["ink"])
    cv.frame(x + 1, y + 1, w - 2, h - 2, C["wood_md"])
    for (cx_, cy_, sx, sy) in ((x + 1, y + 1, 1, 1), (x + w - 2, y + 1, -1, 1), (x + 1, y + h - 2, 1, -1), (x + w - 2, y + h - 2, -1, -1)):
        T.bronze_corner(cv, cx_, cy_, sx, sy, 4)
    yy = y + pad
    for i, (t, f, ww, hh) in enumerate(zip(lines, fonts, ws, hs)):
        if t[0]:
            T.text_ru(cv, x + (w - ww) // 2, yy - f.get("top", 0), t[0], t[1], font=f, outline=False)
        yy += hh + gap
        if i in sep_after:
            for k in range(x + 8, x + w - 8):
                if k % 2 == 0:
                    cv.px(k, yy, C["bronze_dk"])
            yy += 3
    return x, y, w, h


_CURSOR = [
    "kk..........",
    "kGk.........",
    "kGYk........",
    "kGYYk.......",
    "kGYyyk......",
    "kGYyyyk.....",
    "kGyyyyyk....",
    "kGyyyyggk...",
    "kGyyyggggk..",
    "kGyygkkkkkk.",
    "kGygk.......",
    "kGgk........",
    "kgk.........",
    "kk..........",
]


def cursor(cv, x, y):
    cv.stamp(_CURSOR, {"k": C["ink"], "G": C["bronze_hi"], "Y": C["bronze_lt"], "y": C["bronze"],
                       "g": C["bronze_dk"]}, x, y)


def silver_icon(cv, x, y):
    """Small stack of silver dirhams / hacksilver."""
    for (cx, cy) in ((3, 7), (6, 5), (2, 4), (5, 2)):
        cv.rect(x + cx - 2, y + cy, 6, 2, C["slate_lt"])
        cv.rect(x + cx - 2, y + cy - 1, 6, 1, C["birch"])
        cv.px(x + cx - 1, y + cy - 1, C["linen"])
        cv.px(x + cx + 3, y + cy, C["ink"])


def divider(cv, x, y, w):
    """Small interlace divider strip."""
    T.interlace(cv, x, y, w, 7, period=10)


def wrap(text, width, font=FONT_RU):
    """Greedy word wrap to a pixel width."""
    out, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if pk.text_width(t, font) <= width or not line:
            line = t
        else:
            out.append(line); line = word
    if line:
        out.append(line)
    return out

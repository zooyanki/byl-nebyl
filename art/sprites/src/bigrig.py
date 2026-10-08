"""Painter for frames of any size (bosses 128x128, objects 64x120 / 80x160).
Local coords: x right, y down, origin = pivot (ground point). make_sprite adds a 1-px
outline pad, so material (gx, gy) = pivot - 1. Same materials / outline rules as rig.py."""
import math
import numpy as np
import rig
import pixelkit as pk
from pixelkit import C
from rig import rot, add, ik, flame   # noqa: F401  (re-export)

TAU = math.tau


class Pn(rig.Painter):
    def __init__(self, W, H, piv):
        self.W, self.H, self.piv = W, H, tuple(piv)
        self.m = pk.MatCanvas(W - 2, H - 2)
        self.gx, self.gy = piv[0] - 1, piv[1] - 1

    def M(self, p):
        return (self.gx + p[0], self.gy + p[1])

    def ellipse(self, c, rx, ry, ch, clip=None):
        cx, cy = self.M(c)
        h, w = self.m.a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        msk = ((xx - cx) / max(rx, 0.5)) ** 2 + ((yy - cy) / max(ry, 0.5)) ** 2 <= 1.0
        if clip is not None:
            msk &= clip(xx - self.gx, yy - self.gy)
        self.m.a[msk] = ch

    def keep(self, ch_set, mask_fn):
        """Erase material chars (set) where mask_fn(x_local, y_local) is False."""
        h, w = self.m.a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        kill = np.isin(self.m.a, list(ch_set)) & ~mask_fn(xx - self.gx, yy - self.gy)
        self.m.a[kill] = "."

    def recolor(self, ch_from, ch_to, mask_fn=None):
        h, w = self.m.a.shape
        yy, xx = np.mgrid[0:h, 0:w]
        sel = self.m.a == ch_from
        if mask_fn is not None:
            sel &= mask_fn(xx - self.gx, yy - self.gy)
        self.m.a[sel] = ch_to


def build(P, leg):
    spr = rig.build(P, leg)
    spr["pivot"] = P.piv
    return rig.to_index(spr)


def height(idx, pivot_y):
    rows = np.where((idx >= 0).any(1))[0]
    return None if not len(rows) else int(pivot_y - rows.min() + 1)


def over(dst, src):
    m = src >= 0
    dst[m] = src[m]
    return dst


def tongue(P, base, h, w, ph, lean=0.0, chars=("q", "E", "e")):
    """Single flame tongue of height h (px) from base (local), phase ph (radians, loop-safe)."""
    if h < 1.5:
        return
    rows = int(math.ceil(h))
    for i in range(rows + 1):
        t = i / h
        if t > 1:
            break
        half = (w / 2.0) * (1 - t) ** 0.8 * (1 + 0.15 * math.sin(ph * 2 + i * 0.9))
        off = lean * t * h * 0.4 + 1.0 * math.sin(ph + t * 3.4) * t
        y = base[1] - i
        x0, x1 = base[0] + off - half, base[0] + off + half
        P.line((x0, y), (x1, y), chars[0])
        if half > 0.9 and t < 0.72:
            P.line((x0 + 0.8, y), (x1 - 0.8, y), chars[1])
        if t < 0.3 and half > 1.4:
            P.line((x0 + 1.5, y), (x1 - 1.5, y), chars[2])

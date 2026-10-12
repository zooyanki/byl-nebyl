"""iso3d — a tiny z-buffered renderer for buildings in the scene's 2:1 projection (scale.md §1, prototype src/core/iso.js).

World coordinates: u = tile x (west -> east), v = tile y (north -> south), z = height in native px (1 m = 24 px).
Screen: P(u, v, z) = (ox + (u - v) * 16, oy + (u + v) * 8 - z) — exactly w2s() of the prototype plus height, so a
footprint corner lands on the same pixel as the prototype's tile-diamond vertex.

Every face is a planar polygon in world space with a shader f(U, V, Z, a, b) -> palette index array; a per-pixel depth
d = (u + v) * 8 + z (larger = nearer to the camera, which sits at +u +v +z) resolves overlaps, and back faces are culled
with the view vector (1, 1, 16) (the line of sight that keeps a pixel fixed). Palette v2 only, alpha 0/255."""
import json
import numpy as np
from PIL import Image, ImageDraw
import rig                                  # noqa: F401  (activates palette v2)
import pixelkit as pk
from pixelkit import C

_PJ = json.load(open("/workspace/game/art/ui/palette_v2.json"))
RAMPS = {k: np.array([C[n] for n in v], np.int16) for k, v in _PJ["ramps"].items()}
VIEW = np.array([1.0, 1.0, 16.0])


def R(ramp, lvl):
    """palette index for ramp level (scalar or array, clipped to the ramp)."""
    r = RAMPS[ramp]
    return r[np.clip(np.asarray(lvl, int), 0, len(r) - 1)]


def H2(x, y, s=0):
    return pk.hash2(np.asarray(x, np.int64), np.asarray(y, np.int64), s)


class Iso:
    def __init__(self, W, H, ox, oy):
        self.W, self.H, self.ox, self.oy = W, H, ox, oy
        self.idx = np.full((H, W), -1, np.int16)
        self.dep = np.full((H, W), -1e9)
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(float)
        self.anchors = {}

    # ---------------------------------------------------------------- projection
    def P(self, u, v, z=0.0):
        return (self.ox + (u - v) * 16.0, self.oy + (u + v) * 8.0 - z)

    def depth(self, u, v, z=0.0):
        return (u + v) * 8.0 + z

    def mask(self, pts2):
        m = Image.new("L", (self.W, self.H), 0)
        ImageDraw.Draw(m).polygon([(round(x), round(y)) for x, y in pts2], fill=1)
        return np.array(m, dtype=bool)

    # ---------------------------------------------------------------- faces
    def face(self, pts3, shade, out=None, bias=0.0, cull=True, clip=None):
        """pts3: planar polygon (u, v, z). shade: f(U, V, Z, a, b) -> idx array or scalar idx.
        out: a world vector pointing out of the solid (orients the normal for culling)."""
        p = [np.array(q, float) for q in pts3]
        e1, e2 = p[1] - p[0], p[-1] - p[0]
        n = np.cross(e1, e2)
        if out is not None and np.dot(n, out) < 0:
            n = -n
        if cull and out is not None and np.dot(n, VIEW) <= 1e-9:
            return None
        pts2 = [self.P(*q) for q in p]
        m = self.mask(pts2)
        if clip is not None:
            m &= clip
        if not m.any():
            return None
        s0 = np.array(self.P(*p[0]))
        s1 = np.array(self.P(*p[1])) - s0
        s2 = np.array(self.P(*p[-1])) - s0
        det = s1[0] * s2[1] - s1[1] * s2[0]
        if abs(det) < 1e-9:
            return None
        ys, xs = np.nonzero(m)
        rx, ry = xs - s0[0], ys - s0[1]
        a = (rx * s2[1] - ry * s2[0]) / det
        b = (s1[0] * ry - s1[1] * rx) / det
        U = p[0][0] + a * e1[0] + b * e2[0]
        V = p[0][1] + a * e1[1] + b * e2[1]
        Z = p[0][2] + a * e1[2] + b * e2[2]
        d = (U + V) * 8.0 + Z + bias
        ok = d >= self.dep[ys, xs] - 1e-6
        col = shade(U, V, Z, a, b) if callable(shade) else np.full(len(ys), shade)
        col = np.broadcast_to(np.asarray(col, np.int16), (len(ys),))
        ys, xs, col, d = ys[ok], xs[ok], col[ok], d[ok]
        good = col >= 0
        self.idx[ys[good], xs[good]] = col[good]
        self.dep[ys[good], xs[good]] = d[good]
        return (ys, xs)

    def quad_u(self, u, v0, v1, z0, z1, shade, out=1, bias=0.0):
        """vertical face on the plane u = const, from v0..v1, z0..z1 (out = +1 faces +u)."""
        return self.face([(u, v0, z0), (u, v1, z0), (u, v1, z1), (u, v0, z1)], shade, out=(out, 0, 0), bias=bias)

    def quad_v(self, v, u0, u1, z0, z1, shade, out=1, bias=0.0):
        """vertical face on the plane v = const (out = +1 faces +v)."""
        return self.face([(u0, v, z0), (u1, v, z0), (u1, v, z1), (u0, v, z1)], shade, out=(0, out, 0), bias=bias)

    def top(self, u0, v0, u1, v1, z, shade, bias=0.0):
        return self.face([(u0, v0, z), (u1, v0, z), (u1, v1, z), (u0, v1, z)], shade, out=(0, 0, 1), bias=bias)

    def box(self, u0, v0, u1, v1, z0, z1, sh_u, sh_v, sh_top=None, bias=0.0):
        """axis-aligned box: visible faces only (+u, +v, top); sh_* shaders."""
        self.quad_v(v1, u0, u1, z0, z1, sh_v, 1, bias)
        self.quad_u(u1, v0, v1, z0, z1, sh_u, 1, bias)
        self.quad_v(v0, u0, u1, z0, z1, sh_v, -1, bias)
        self.quad_u(u0, v0, v1, z0, z1, sh_u, -1, bias)
        if sh_top is not None:
            self.top(u0, v0, u1, v1, z1, sh_top, bias)

    # ---------------------------------------------------------------- 2-D primitives with depth
    def put(self, ys, xs, col, d):
        ys, xs = np.asarray(ys), np.asarray(xs)
        col = np.broadcast_to(np.asarray(col, np.int16), ys.shape)
        d = np.broadcast_to(np.asarray(d, float), ys.shape)
        ok = (ys >= 0) & (ys < self.H) & (xs >= 0) & (xs < self.W)
        ys, xs, col, d = ys[ok], xs[ok], col[ok], d[ok]
        ok = (d >= self.dep[ys, xs] - 1e-6) & (col >= 0)
        self.idx[ys[ok], xs[ok]] = col[ok]
        self.dep[ys[ok], xs[ok]] = d[ok]

    def px(self, x, y, col, d):
        self.put(np.array([int(round(y))]), np.array([int(round(x))]), col, d)

    def rect2(self, x, y, w, h, col, d):
        yy, xx = np.mgrid[int(round(y)):int(round(y)) + h, int(round(x)):int(round(x)) + w]
        self.put(yy.ravel(), xx.ravel(), col, d)

    def blit(self, idx, x, y, d):
        """paste an index sprite (-1 transparent) with its top-left at (x, y)."""
        ys, xs = np.nonzero(idx >= 0)
        self.put(ys + int(round(y)), xs + int(round(x)), idx[ys, xs], d)

    def beam(self, p, q, w, ramp, levels, bias=0.5, cap=True):
        """round log / pole between world points p, q, w px thick; levels = (shadow, mid, light) ramp levels;
        light from the upper left (the half of the beam towards (-1,-1) on screen is lit)."""
        a, b = np.array(self.P(*p)), np.array(self.P(*q))
        dpa, dpb = self.depth(*p), self.depth(*q)
        dv = b - a
        L = max(np.hypot(*dv), 1e-6)
        t_ = dv / L
        nrm = np.array([-t_[1], t_[0]])
        if nrm @ np.array([-1.0, -1.0]) < 0:
            nrm = -nrm
        x0, x1 = int(min(a[0], b[0]) - w - 2), int(max(a[0], b[0]) + w + 2)
        y0, y1 = int(min(a[1], b[1]) - w - 2), int(max(a[1], b[1]) + w + 2)
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1].astype(float)
        rx, ry = xx - a[0], yy - a[1]
        s = (rx * t_[0] + ry * t_[1]) / L
        o = rx * nrm[0] + ry * nrm[1]
        lim = (s >= 0) & (s <= 1) if not cap else (s >= -0.5 / L) & (s <= 1 + 0.5 / L)
        hw = w / 2.0
        m = lim & (o > -hw - 1e-6) & (o <= hw + 1e-6) & (np.abs(o) <= hw)
        if not m.any():
            return
        f = o[m] / max(hw, 0.5)
        lv = np.where(f > 0.34, levels[2], np.where(f < -0.34, levels[0], levels[1]))
        d = dpa + (dpb - dpa) * np.clip(s[m], 0, 1) + bias
        self.put(yy[m].astype(int), xx[m].astype(int), R(ramp, lv), d)

    # ---------------------------------------------------------------- finishing
    def outline(self, col=None):
        """1-px ink outline around the outer silhouette (scale.md §4.4, environment: outer silhouette only)."""
        col = C["ink"] if col is None else col
        op = self.idx >= 0
        g = np.zeros_like(op)
        g[1:, :] |= op[:-1, :]; g[:-1, :] |= op[1:, :]; g[:, 1:] |= op[:, :-1]; g[:, :-1] |= op[:, 1:]
        ring = g & ~op
        self.idx[ring] = col
        self.dep[ring] = -1e8

    def crop(self, pad=0):
        """tight crop of opaque pixels; returns (idx, (x0, y0)) — subtract (x0, y0) from canvas coords."""
        ys, xs = np.nonzero(self.idx >= 0)
        y0, y1, x0, x1 = ys.min() - pad, ys.max() + 1 + pad, xs.min() - pad, xs.max() + 1 + pad
        return self.idx[y0:y1, x0:x1].copy(), (int(x0), int(y0))

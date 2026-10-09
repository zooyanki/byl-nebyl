"""Ворота частокола Ладоги (H5) и указатель у торга (H6) — GDD v1.13 §7.1.1/§10.2, scale.md 1.4 §3.1.
Same projection as iso3d / prototype iso.js. Gate local coords: a = along the palisade (0..4 over the 4 cells
gatepost, gap, gap, gatepost), n = across (0..1, palisade line at n = 0.5), z = height px."""
import numpy as np
import rig  # noqa: F401
import pixelkit as pk
from pixelkit import C
import iso3d as I
import village as VL

GATES = {   # name: (axis of the palisade, interior sign along n, world min corner of the 1×4 footprint)
    "e": ("y", -1, (39, 20)),
    "w": ("y", +1, (8, 20)),
    "n": ("x", +1, (22, 6)),
    "s": ("x", -1, (22, 37)),
}
POST_A = (0.78, 3.22)
LEAF_A = ((0.93, 2.0), (2.0, 3.07))


def W(axis, a, n, z):
    return (n, a, z) if axis == "y" else (a, n, z)


def wbox(S, axis, a0, a1, n0, n1, z0, z1, sh_lit, sh_sh, top=None, bias=0.0):
    u0, v0, _ = W(axis, a0, n0, 0)
    u1, v1, _ = W(axis, a1, n1, 0)
    S.box(min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1), z0, z1, sh_sh, sh_lit, top, bias)


def plank(face_axis_for_lit, wood="wood", width=3, seed=0):
    """returns (lit shader for +v faces, shade shader for +u faces) with vertical boards."""
    return VL.boards("lit", wood, width, seed, "u"), VL.boards("sh", wood, width, seed + 1, "v")


def stake(S, axis, a, h, seed):
    """palisade stake exactly as prototype props.js palisade(): 6 px log + pointed top."""
    u, v, _ = W(axis, a, 0.5, 0)
    x, y = S.P(u, v, 0)
    x, y = int(round(x)), int(round(y))
    d = S.depth(u, v, 0) + 0.2
    S.rect2(x - 3, y - h, 6, h, C["wood"], d)
    S.rect2(x - 3, y - h, 2, h, C["wood_md"], d + 0.01)
    S.rect2(x + 2, y - h, 1, h, C["wood_dk"], d + 0.01)
    for j in range(6):
        hw = max(0, 4 - (j * 4) // 5)
        for i in range(-hw, hw + 1):
            inner = abs(i) < hw and j < 5
            S.px(x + i, y - h - j, C["wood_lt"] if inner else C["ink"], d + 0.02)


def bands(S, axis, a0, a1, z):
    p = W(axis, a0, 0.5, z)
    q = W(axis, a1, 0.5, z)
    for t in np.linspace(0, 1, 40):
        u, v = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        x, y = S.P(u, v, z)
        S.rect2(int(round(x)), int(round(y)), 1, 2, C["wood_dk"], S.depth(u, v, z) + 0.3)


FLAME = [  # 4 frames, rows top→bottom, '.' empty, e ember, f flame, l linen
    ["..e..", ".eff.", ".efe.", "efffe", "eflfe", "eflfe", ".efe.", "..e.."],
    ["...e.", "..ee.", ".eff.", ".efe.", "efffe", "eflfe", "efffe", ".eee."],
    [".e...", ".ee..", ".efe.", "efffe", "eflfe", "efffe", ".eee."],
    ["..e..", "..e..", ".efe.", ".eff.", "efffe", "eflfe", "efffe", ".efe.", "..e.."],
]


def torch(S, axis, a, lit, phase):
    u, v, _ = W(axis, a, 0.68, 0)
    wbox(S, axis, a - 0.05, a + 0.05, 0.65, 0.76, 44, 50, VL.flat(C["wood_dk"]), VL.flat(C["wood_dk"]), VL.flat(C["wood"]), 0.3)
    x, y = S.P(*W(axis, a, 0.76, 50))
    x, y = int(round(x)), int(round(y))
    d = S.depth(*W(axis, a, 0.8, 50)) + 18     # flame rises ≤ 14 px above its root: keep it in front of its own post
    S.rect2(x - 1, y - 6, 3, 6, C["wood"], d)              # torch head (tow on a stick)
    S.rect2(x - 1, y - 6, 1, 6, C["wood_md"], d + 0.01)
    if lit:
        fr = FLAME[phase % 4]
        pal = {"e": C["ember"], "f": C["flame"], "l": C["linen"]}
        for j, r in enumerate(fr):
            for i, ch in enumerate(r):
                if ch in pal:
                    S.px(x - 2 + i, y - 6 - len(fr) + j + 1, pal[ch], d + 0.1)
        return (x, y - 9)
    S.rect2(x - 1, y - 7, 3, 2, C["ink"], d + 0.1)          # charred, unlit
    return (x, y - 7)


def leaf(S, axis, a0, a1, n0, n1, interior_face_n, seed):
    lit, sh = plank(None, "wood", 4, seed)
    wbox(S, axis, a0, a1, n0, n1, 2, 74, lit, sh, VL.flat(C["wood_lt"]), 0.1)
    # battens and a brace on the face that looks at the camera (+u / +v)
    if abs(a1 - a0) > abs(n1 - n0):     # closed: leaf spans a; batten on the +n face
        nn = n1 + 0.02
        for z in (12, 58):
            wbox(S, axis, a0 + 0.06, a1 - 0.06, n1, nn + 0.04, z, z + 5, VL.flat(C["wood_md"]), VL.flat(C["wood"]),
                 VL.flat(C["wood_lt"]), 0.2)
    else:                              # open: leaf spans n; battens on the +a face
        for z in (12, 58):
            nlo, nhi = min(n0, n1), max(n0, n1)
            wbox(S, axis, a1, a1 + 0.05, nlo + 0.06, nhi - 0.06, z, z + 5, VL.flat(C["wood_md"]), VL.flat(C["wood"]),
                 VL.flat(C["wood_lt"]), 0.2)


def gate(side, state, phase=0, parts=("A", "B"), S=None):
    axis, sin, _ = GATES[side]
    ex = {}
    lit_p, sh_p = plank(None, "wood", 3, 7)
    for k, pa in enumerate(POST_A):
        seg = "A" if k == 0 else "B"
        if seg not in parts:
            continue
        # neighbouring stakes of the gatepost cell (as the prototype's 3 stakes per cell, 2 remain beside the post)
        for t, sa in enumerate((0.17, 0.5) if k == 0 else (3.5, 3.83)):
            stake(S, axis, sa, 90 - 3 * t if k == 0 else 87 + 3 * t, t)
        bands(S, axis, 0.0 if k == 0 else 3.0, 1.0 if k == 0 else 4.0, 24)
        bands(S, axis, 0.0 if k == 0 else 3.0, 1.0 if k == 0 else 4.0, 64)
        wbox(S, axis, pa - 0.16, pa + 0.16, 0.34, 0.66, 0, 92, lit_p, sh_p, VL.flat(C["wood_lt"]), 0.4)
        wbox(S, axis, pa - 0.2, pa + 0.2, 0.3, 0.7, 92, 96, VL.flat(C["wood_md"]), VL.flat(C["wood"]), VL.flat(C["wood_lt"]), 0.5)
        ex["torch_" + seg] = torch(S, axis, pa, state == "open", phase + 2 * k)
        a0, a1 = LEAF_A[k]
        if state == "closed":
            leaf(S, axis, a0, a1, 0.46, 0.54, None, 20 + k)
        else:
            hinge = a0 if k == 0 else a1 - 0.08
            n_end = 0.5 + sin * 1.07
            leaf(S, axis, hinge, hinge + 0.08, min(0.5, n_end), max(0.5, n_end), None, 20 + k)
    if "B" in parts:
        # перекладина 84–90 over both posts + bronze disc (as in the prototype, unchanged)
        wbox(S, axis, 0.5, 3.5, 0.4, 0.6, 84, 90, VL.flat(C["wood_md"]), VL.flat(C["wood"]), VL.flat(C["wood_lt"]), 0.6)
        x, y = S.P(*W(axis, 2.0, 0.6, 87))
        d = S.depth(*W(axis, 2.0, 0.6, 87)) + 1
        yy, xx = np.mgrid[-6:7, -6:7]
        r = np.hypot(xx, yy)
        for rad, col in ((5, C["ink"]), (4, C["bronze"]), (1.5, C["bronze_hi"])):
            m = r <= rad
            S.put(yy[m] + int(round(y)), xx[m] + int(round(x)), col, d + (5 - rad) * 0.01)
        if state == "closed":
            # брус-засов на 36 across both leaves, on the INSIDE face (= camera side for N and W gates)
            nb = (0.55, 0.66) if sin > 0 else (0.34, 0.45)
            wbox(S, axis, 0.7, 3.3, nb[0], nb[1], 33, 39, VL.flat(C["wood_dk"]), VL.flat(C["wood_dk"]), VL.flat(C["wood"]), 0.7)
            for ba in (1.2, 2.8):
                wbox(S, axis, ba - 0.06, ba + 0.06, nb[0], nb[1] + 0.03, 31, 41, VL.flat(C["slate"]), VL.flat(C["slate_dk"]),
                     VL.flat(C["slate_lt"]), 0.8)
        ex["mark"] = S.P(*W(axis, 2.0, 0.5, 96))
        ex["caption"] = S.P(*W(axis, 2.0, 0.5, 100))
    return ex


def gate_sheets(side, state):
    """returns dict(full=frames, A=frames, B=frames, meta) — 4 torch frames when open, 1 when closed."""
    axis, sin, (x0, y0) = GATES[side]
    A_, B_ = (1, 4) if axis == "y" else (4, 1)
    nfr = 4 if state == "open" else 1
    mk = VL.new_canvas(A_, B_, 140)
    Ss = {"full": [], "A": [], "B": []}
    exs = []
    for ph in range(nfr):
        for key, parts in (("full", ("A", "B")), ("A", ("A",)), ("B", ("B",))):
            S = mk()
            ex = gate(side, state, ph, parts, S)
            S.outline()
            Ss[key].append(S)
            if key == "full":
                exs.append(ex)
    op = np.zeros_like(Ss["full"][0].idx, bool)
    for L in Ss.values():
        for S in L:
            op |= S.idx >= 0
    ys, xs = np.nonzero(op)
    cy0, cy1, cx0, cx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = {k: [S.idx[cy0:cy1, cx0:cx1].copy() for S in L] for k, L in Ss.items()}
    S = Ss["full"][0]
    tr = lambda p: [int(round(p[0] - cx0)), int(round(p[1] - cy0))]
    seg_tiles = {"A": W(axis, 0, 0, 0)[:2], "B": W(axis, 3, 0, 0)[:2]}
    meta = dict(pivot=tr(S.P(A_ / 2.0, B_ / 2.0, 0)), proto_corner_px=tr(S.P(0, 0, 0)),
                footprint_px=[tr(S.P(0, 0)), tr(S.P(A_, 0)), tr(S.P(A_, B_)), tr(S.P(0, B_))],
                front_corner_px=tr(S.P(A_, B_)), footprint_tiles=[A_, B_], world_min_corner=[x0, y0],
                segments={k: dict(tile_offset=[int(seg_tiles[k][0]), int(seg_tiles[k][1])],
                                  world_tile=[x0 + int(seg_tiles[k][0]), y0 + int(seg_tiles[k][1])],
                                  pivot=tr(S.P(seg_tiles[k][0] + 0.5, seg_tiles[k][1] + 0.5, 0))) for k in "AB"},
                anchors_px={k: tr(v) for k, v in exs[0].items()},
                torch_flame_px={k: [tr(e[k]) for e in exs] for k in ("torch_A", "torch_B")})
    return out, meta


# ------------------------------------------------------------------ H6: указатель
SIGN_DIRS = {"zalesye": (1, 0), "sopki": (0, -1), "bor": (-1, 0), "pier": (0, 1)}   # +x east, −y north, −x west, +y south
SIGN_Z = {"zalesye": 44, "bor": 44, "sopki": 36, "pier": 36}


def signpost(stage):
    """stage 0: M1 (Залесье, пристань open); 1: after M1 (+ Сопки); 2: after M2 (+ Бор)."""
    open_ = {"zalesye", "pier"} | ({"sopki"} if stage >= 1 else set()) | ({"bor"} if stage >= 2 else set())
    mk = lambda: I.Iso(120, 120, 60, 80)
    S = mk()
    # post 56: square hewn pole 0.2 tile, slightly darker top cap
    lit, sh = plank(None, "wood", 2, 3)
    S.box(0.4, 0.4, 0.6, 0.6, 0, 54, sh, lit, VL.flat(C["wood_lt"]))
    S.box(0.38, 0.38, 0.62, 0.62, 54, 56, VL.flat(C["wood"]), VL.flat(C["wood_md"]), VL.flat(C["wood_lt"]))
    for key, (du, dv) in SIGN_DIRS.items():
        z = SIGN_Z[key]
        L = 0.8
        lt = key in open_
        base = C["wood_lt"] if lt else C["wood_dk"]
        edge = C["birch"] if lt else C["wood"]
        # board in the vertical plane through the post centre along (du, dv), from the post to L, height 6
        c = 0.5
        if du:
            p0, p1 = c + du * 0.1, c + du * L
            pts = [(p0, c, z), (p1 - du * 0.12, c, z), (p1, c, z + 3), (p1 - du * 0.12, c, z + 6), (p0, c, z + 6)]
            o = (0, 1, 0)
        else:
            p0, p1 = c + dv * 0.1, c + dv * L
            pts = [(c, p0, z), (c, p1 - dv * 0.12, z), (c, p1, z + 3), (c, p1 - dv * 0.12, z + 6), (c, p0, z + 6)]
            o = (1, 0, 0)
        sh_ = (lambda base, edge: (lambda U, V, Z, a, b: np.where(Z > z + 4.5, edge, base).astype(np.int16)))(base, edge)
        S.face(pts, sh_, out=o, bias=0.5, cull=False)
    S.outline()
    return S


def sign_frames():
    Ss = [signpost(s) for s in range(3)]
    op = np.zeros_like(Ss[0].idx, bool)
    for S in Ss:
        op |= S.idx >= 0
    ys, xs = np.nonzero(op)
    cy0, cy1, cx0, cx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    S = Ss[0]
    tr = lambda p: [int(round(p[0] - cx0)), int(round(p[1] - cy0))]
    meta = dict(pivot=tr(S.P(0.5, 0.5, 0)), proto_corner_px=tr(S.P(0, 0, 0)),
                footprint_px=[tr(S.P(0, 0)), tr(S.P(1, 0)), tr(S.P(1, 1)), tr(S.P(0, 1))], front_corner_px=tr(S.P(1, 1)),
                board_tips_px={k: tr(S.P(0.5 + d[0] * 0.8, 0.5 + d[1] * 0.8, SIGN_Z[k] + 3)) for k, d in SIGN_DIRS.items()})
    return [S.idx[cy0:cy1, cx0:cx1].copy() for S in Ss], meta

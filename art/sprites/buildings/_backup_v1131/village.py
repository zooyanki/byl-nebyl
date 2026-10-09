"""Ладога buildings (GDD v1.13 §7.1.1, §12.1.7 H1–H4, H11–H15; scale.md 1.4 §3.1).

All buildings are rendered by iso3d in the scene's exact 2:1 projection (prototype w2s, tile 32x16), ridge along +u
(world x), gable end towards +u — the same convention as the prototype's izba() and the HUD v2 сруб: the camera sees the
+v (south, front-left, lit) and +u (east, front-right, shade) faces. Log courses are 4 px (venets), heights per scale.md.

Door variants: a building sheet has 3 frames, frame = where the door is: 0 — door on the +v (south) long wall,
1 — door on the +u (east) gable end, 2 — door on a hidden side (-u / -v): both visible walls get windows only.
JSON `door_frames` maps the plan's door side (GDD §7.1.1 «Дверь») to the frame."""
import numpy as np
import iso3d as I
from iso3d import R, H2
import pixelkit as pk
from pixelkit import C
import sprites_rus as SR

INK = C["ink"]

# ------------------------------------------------------------------ tone tables
# (seam, grain, base, highlight) per face; "grey" = weathered silvery logs (old клеть / амбар), mixed per course
TONES = {
    ("wood", "lit"): (C["wood_dk"], C["wood"], C["wood_md"], C["wood_lt"]),
    ("wood", "sh"): (C["wood_dk"], C["wood_dk"], C["wood"], C["wood_md"]),
    ("grey", "lit"): (C["slate_dk"], C["slate_lt"], C["slate_lt"], C["birch"]),     # silvered old wood (warm highlight)
    ("grey", "sh"): (C["night"], C["slate_dk"], C["slate"], C["mist"]),
    ("new", "lit"): (C["wood"], C["wood_md"], C["wood_lt"], C["birch"]),          # fresh light тёс
    ("new", "sh"): (C["wood_dk"], C["wood"], C["wood_md"], C["wood_lt"]),
    ("dark", "lit"): (C["wood_dk"], C["wood_dk"], C["wood"], C["wood_md"]),      # tarred / smoked (баня, кузня)
    ("dark", "sh"): (C["ink"], C["wood_dk"], C["wood_dk"], C["wood"]),
}


def logs(face, wood="wood", weather=0.0, z0=0.0, seed=0, axis="u", zshade=None):
    """log-wall shader: 4-px courses following z, highlight on top of each log, dark seam under it, grain flecks;
    weather > 0 mixes grey courses in (silvery weathered logs)."""
    def f(U, V, Z, a, b):
        al = (U if axis == "u" else V) * 16.0
        k = np.floor((Z - z0) / 4.0).astype(np.int64)
        r = (Z - z0) - k * 4.0
        grey = H2(k, np.zeros_like(k) + seed, 7) < weather
        out = np.empty(len(Z), np.int16)
        for g, ramp in ((False, wood), (True, "grey")):
            sel = grey == g
            if not sel.any():
                continue
            seam, grain, base, hi = TONES[(ramp, face)]
            c = np.full(sel.sum(), base, np.int16)
            rr, kk, aa = r[sel], k[sel], al[sel]
            gr = (H2(np.floor(aa / 6).astype(np.int64), kk, seed + 3) < 0.13) & (rr >= 1) & (rr < 3)
            c[gr] = grain
            c[rr >= 3] = hi
            c[rr < 1] = seam
            knot = (H2(np.floor(aa / 2).astype(np.int64), kk, seed + 9) < 0.012) & (rr >= 1) & (rr < 3)
            c[knot] = seam
            if zshade is not None:                                   # shadow under the eaves
                zz = Z[sel]
                c[(zz > zshade) & (c == hi)] = base
                c[(zz > zshade) & (c == base)] = grain
            out[sel] = c
        return out
    return f


def boards(face, wood="wood", width=3, seed=0, axis="u", vertical=True):
    """plank shader (vertical boards: gables of the church, doors, fences)."""
    def f(U, V, Z, a, b):
        al = (U if axis == "u" else V) * 16.0
        seam, grain, base, hi = TONES[(wood, face)]
        if vertical:
            i = np.floor(al / width).astype(np.int64)
            r = al - i * width
        else:
            i = np.floor(Z / width).astype(np.int64)
            r = Z - i * width
        c = np.where(H2(i, np.zeros_like(i), seed) < 0.35, grain, base).astype(np.int16)
        c = np.where(r < 1, seam, c)
        c = np.where((r >= width - 1) & (H2(i, i, seed + 1) < 0.5), hi, c)
        return c
    return f


def flat(col):
    return lambda U, V, Z, a, b: np.full(len(Z), col, np.int16)


# ------------------------------------------------------------------ roofs
def roof_shader(style, side, vm, ve, seed=0, wood="wood"):
    """side 'front' (lit, faces +v) or 'back'. s = 0 at the ridge, 1 at the eave."""
    span = abs(ve - vm)

    def f(U, V, Z, a, b):
        s = np.clip(np.abs(V - vm) / span, 0, 1)
        n = len(Z)
        if style == "tes":
            lit = side == "front"
            seam, grain, base, hi = TONES[(wood, "lit" if lit else "sh")]
            if wood == "grey":
                hi = C["mist"] if lit else hi
            pw = 0.17
            pi = np.floor(U / pw).astype(np.int64)
            fr = U / pw - pi
            c = np.where(H2(pi, np.zeros_like(pi), seed) < 0.3, grain, base).astype(np.int16)
            c = np.where(fr < 0.22, seam, c)
            c = np.where((fr > 0.78) & lit, hi, c)
            joint = (np.mod(s * 3 + H2(pi, pi, seed + 2) * 0.6, 1) < 0.07) & (s > 0.15) & (H2(pi, pi, seed + 4) < 0.5)
            c = np.where(joint, seam, c)
            c = np.where(s > 0.95, seam, c)                          # eave shadow line
            return c
        if style == "dern":
            lit = side == "front"
            x = np.floor(U * 16).astype(np.int64)
            y = np.floor(s * span * 11).astype(np.int64)
            nz = H2(x // 3, y // 2, seed) * 0.6 + H2(x, y, seed + 1) * 0.4
            lv = np.where(nz < 0.28, 2, np.where(nz > 0.8, 4, 3))
            if not lit:
                lv = lv - 1
            tuft = (H2(x, y, seed + 5) < 0.06)
            lv = np.where(tuft, lv + 1, lv)
            lv = np.where(s < 0.06, lv - 1, lv)                      # shade under the ridge log
            c = R("grass", lv)
            dry = H2(x // 4, y // 3, seed + 7) < 0.12                # dry straw-coloured patches
            c = np.where(dry & lit & (nz > 0.5), C["moss_lt"], c)
            return c
        if style == "lemeh":
            rows = np.floor(s * span * 16 / 3.0).astype(np.int64)
            off = (rows % 2) * 0.5
            col = U * 16 / 3.0 + off
            ci = np.floor(col).astype(np.int64)
            fr = col - ci
            rr = s * span * 16 / 3.0 - rows
            lit = side == "front"
            c = np.full(n, C["slate_lt"] if lit else C["slate"], np.int16)
            c = np.where(rr > 0.7, C["slate"] if lit else C["slate_dk"], c)
            c = np.where((rr < 0.3) & (fr > 0.3) & (fr < 0.7) & lit, C["mist"], c)
            c = np.where(fr < 0.12, C["slate_dk"], c)
            return c
        raise ValueError(style)
    return f


def cabin(S, u0, v0, u1, v1, wall, rise, z0=0.0, ov=0.3, og=0.3, roof="tes", wood="wood", weather=0.0,
          gable="logs", prich=False, ridge="horse", seed=0, corners=True, roof_wood=None):
    """сруб under a gable roof, ridge along u at vm (scale.md §3.1). Returns key points."""
    vm = (v0 + v1) / 2.0
    zw = z0 + wall
    k = rise / (vm - v0)                       # px of height per tile across the slope
    zr = zw + rise
    ze = zw - ov * k
    out = dict(vm=vm, zw=zw, zr=zr, ze=ze, k=k)
    # walls
    S.quad_v(v1, u0, u1, z0, zw, logs("lit", wood, weather, z0, seed, "u", ze - 5), 1)
    S.quad_u(u1, v0, v1, z0, zw, logs("sh", wood, weather, z0, seed + 1, "v"), 1)
    S.quad_v(v0, u0, u1, z0, zw, logs("sh", wood, weather, z0, seed, "u"), -1)
    S.quad_u(u0, v0, v1, z0, zw, logs("lit", wood, weather, z0, seed, "v"), -1)
    # gable triangle at +u (logs «самцы» or boards)
    gsh = logs("sh", wood, weather, z0, seed + 1, "v") if gable == "logs" else boards("sh", wood, 3, seed, "v")
    S.face([(u1, v1, zw), (u1, v0, zw), (u1, vm, zr)], gsh, out=(1, 0, 0))
    # protruding log ends at the three visible corners (every other course)
    if corners:
        for zc in np.arange(z0, zw - 1, 4):
            odd = int((zc - z0) // 4) % 2
            for (cu, cv, du, dv) in ((u1, v1, 0.2, 0), (u1, v1, 0, 0.2), (u0, v1, -0.2, 0), (u1, v0, 0, -0.2)):
                if (odd == 0) == (du != 0):
                    x, y = S.P(cu + du, cv + dv, zc + 2)
                    d = S.depth(cu + du, cv + dv, zc + 2) + 0.4
                    ring = np.array([[-1, 1, 1, -1], [1, 2, 3, 1], [1, 3, 3, 1], [-1, 1, 1, -1]])
                    lit_end = du == 0                                  # end grain facing +v (lit) or +u (shade)
                    pal = {"wood": ((C["wood_dk"], C["wood_lt"], C["birch"]), (C["wood_dk"], C["wood_md"], C["wood_lt"])),
                           "grey": ((C["slate_dk"], C["mist"], C["birch"]), (C["night"], C["slate_lt"], C["mist"])),
                           "dark": ((C["ink"], C["wood_md"], C["wood_lt"]), (C["ink"], C["wood"], C["wood_md"]))}[wood][0 if lit_end else 1]
                    tone = np.where(ring == 1, pal[0], np.where(ring == 2, pal[1], np.where(ring == 3, pal[2], -1)))
                    S.blit(tone.astype(np.int16), x - 2, y - 2, d)
    # roof slopes
    ue0, ue1 = u0 - og, u1 + og
    vf, vb = v1 + ov, v0 - ov
    S.face([(ue0, vm, zr), (ue1, vm, zr), (ue1, vf, ze), (ue0, vf, ze)], roof_shader(roof, "front", vm, vf, seed, roof_wood or wood),
           out=(0, 1, 1), bias=0.2)
    S.face([(ue0, vm, zr), (ue1, vm, zr), (ue1, vb, ze), (ue0, vb, ze)], roof_shader(roof, "back", vm, vb, seed, roof_wood or wood),
           out=(0, -1, 1), bias=0.2)
    th = {"tes": 2, "dern": 4, "lemeh": 2}[roof]
    # roof thickness at the gable end (+u) and along the front eave (+v)
    if roof == "dern":
        edge_g = lambda U, V, Z, a, b: np.where((Z - (zr + (ze - zr) * np.clip(np.abs(V - vm) / (vf - vm), 0, 1))) > -2,
                                               C["moss"], C["birch"]).astype(np.int16)
        edge_e = lambda U, V, Z, a, b: np.where(Z > ze - 2, C["moss"], np.where(H2(np.floor(U * 16).astype(np.int64), 0, 3) < 0.5, C["birch"], C["mist"])).astype(np.int16)
    else:
        rw = roof_wood or wood
        edge_g = flat({"grey": C["mist"], "new": C["birch"]}.get(rw, C["wood_lt"]))
        edge_e = flat({"grey": C["slate_lt"], "new": C["wood_lt"]}.get(rw, C["wood_md"]))
    S.face([(ue1, vm, zr), (ue1, vf, ze), (ue1, vf, ze - th), (ue1, vm, zr - th)], edge_g, out=(1, 0, 0), bias=0.3)
    S.face([(ue1, vm, zr), (ue1, vb, ze), (ue1, vb, ze - th), (ue1, vm, zr - th)], edge_g, out=(1, 0, 0), bias=0.3)
    S.face([(ue0, vf, ze), (ue1, vf, ze), (ue1, vf, ze - th), (ue0, vf, ze - th)], edge_e, out=(0, 1, 0), bias=0.3)
    if roof == "dern":
        # sod overhang: ragged grass fringe and the birch-bark layer showing at the eave
        for i, uu in enumerate(np.arange(ue0, ue1, 1 / 16)):
            hng = int(H2(i, 5, seed) * 3)
            for j in range(hng):
                x, y = S.P(uu, vf, ze - th - j)
                S.px(x, y, C["moss"] if j == 0 else C["pine"], S.depth(uu, vf, ze) + 0.5)
    if prich:
        # причелины: wide light bargeboards along both gable edges + полотенце (hanging board) under the ridge,
        # scalloped lower edge; plain carving (no signs)
        for vend in (vf, vb):
            n = 26
            for i in range(n + 1):
                t = i / n
                vv = vm + (vend - vm) * t
                zz = zr + (ze - zr) * t
                x, y = S.P(ue1 + 0.02, vv, zz)
                d = S.depth(ue1 + 0.02, vv, zz) + 0.6
                hh = 5 + (1 if (i % 3) == 1 else 0)
                for j in range(hh):
                    col = C["wood_lt"] if j < 2 else (C["wood_md"] if j < hh - 1 else C["wood"])
                    S.px(x, y + j, col, d)
                if i % 3 == 0:
                    S.px(x, y + 3, C["wood"], d + 0.01)                     # drilled hole
        x, y = S.P(ue1 + 0.02, vm, zr)
        d = S.depth(ue1 + 0.02, vm, zr) + 0.7
        S.rect2(x - 2, y + 1, 4, 18, C["wood_lt"], d)
        S.rect2(x - 1, y + 1, 1, 18, C["birch"], d + 0.01)
        S.rect2(x + 1, y + 1, 1, 18, C["wood_md"], d + 0.01)
        for j in (6, 11):
            S.rect2(x - 1, y + j, 2, 1, C["wood"], d + 0.02)
        S.rect2(x - 3, y + 19, 6, 2, C["wood_lt"], d)
        S.rect2(x - 2, y + 21, 4, 1, C["wood_md"], d)
        S.px(x - 1, y + 22, C["wood_md"], d)
    # ridge: охлупень log along the ridge
    if ridge in ("horse", "plain", "sod"):
        lv = (1, 3, 4) if (roof_wood or wood) != "grey" else (1, 2, 3)
        S.beam((ue0, vm, zr + 2), (ue1 + 0.05, vm, zr + 2), 5 if ridge == "sod" else 4, "wood", lv, bias=0.9)
    if ridge == "horse":
        hs = pk.sprite_to_index(SR.horse_head())
        x, y = S.P(ue1 + 0.05, vm, zr + 2)
        S.blit(hs, x - 4, y - 1 - hs.shape[0] + 3, S.depth(ue1, vm, zr) + 2)
        out["horse_top"] = zr + 2 + (hs.shape[0] - 3 + 1) - 2
    out.update(ue0=ue0, ue1=ue1, vf=vf, vb=vb)
    return out


# ------------------------------------------------------------------ openings
def wall_quad(S, face, c, a0, a1, z0, z1, shade, bias):
    if face == "v":
        return S.quad_v(c, a0, a1, z0, z1, shade, 1, bias)
    return S.quad_u(c, a0, a1, z0, z1, shade, 1, bias)


def door(S, face, c, a0, w=1.44, z0=4, h=56, bolt=False, lock=False, seed=0, open_=False, glow=False):
    """door on a visible wall (face 'v': plane v=c, a = u; face 'u': plane u=c, a = v).
    наличник +2 px, порог (threshold log) 0..4, plank leaf with two iron straps; bolt = засов (клеть)."""
    a1 = a0 + w
    pad = 2 / 16
    side = "lit" if face == "v" else "sh"
    wall_quad(S, face, c, a0 - pad, a1 + pad, z0 - 2, z0 + h + 2, flat(C["wood_lt"] if side == "lit" else C["wood_md"]), 0.3)
    wall_quad(S, face, c, a0 - pad * 1.6, a1 + pad * 1.6, z0 + h + 2, z0 + h + 4, flat(C["wood_md"] if side == "lit" else C["wood"]), 0.35)
    if open_:
        wall_quad(S, face, c, a0, a1, z0, z0 + h, flat(INK), 0.4)
        if glow:
            wall_quad(S, face, c, a0 + 0.3, a1 - 0.1, z0, z0 + 2, flat(C["ember"]), 0.45)
    else:
        ax = "u" if face == "v" else "v"
        sh = boards(side, "wood", 4, seed, ax)
        wall_quad(S, face, c, a0, a1, z0, z0 + h, sh, 0.4)
        for zz in (z0 + 10, z0 + h - 12):
            wall_quad(S, face, c, a0 + 0.05, a1 - 0.05, zz, zz + 2, flat(C["slate_dk"] if side == "sh" else C["slate"]), 0.45)
        # ring handle
        hx = a1 - 0.22
        wall_quad(S, face, c, hx, hx + 0.08, z0 + 26, z0 + 30, flat(C["slate_lt"]), 0.5)
        if bolt:   # засов: heavy bar across the leaf in two iron brackets
            wall_quad(S, face, c, a0 - 0.25, a1 + 0.25, z0 + 24, z0 + 28, flat(C["wood_dk"]), 0.6)
            wall_quad(S, face, c, a0 - 0.25, a1 + 0.25, z0 + 27, z0 + 28, flat(C["wood_md"]), 0.62)
            for bx in (a0 - 0.12, a1 + 0.02):
                wall_quad(S, face, c, bx, bx + 0.1, z0 + 22, z0 + 30, flat(C["slate"]), 0.65)
        if lock:   # висячий замок
            wall_quad(S, face, c, a1 - 0.12, a1 + 0.08, z0 + 20, z0 + 26, flat(C["slate_lt"]), 0.7)
    # threshold (окладной венец shows as a darker sill)
    wall_quad(S, face, c, a0 - pad * 2, a1 + pad * 2, z0 - 4, z0, flat(C["wood_md"] if side == "lit" else C["wood"]), 0.35)


def window(S, face, c, a0, z0=28, w=11 / 16, h=12, lit=True, shutters=True, kokoshnik=False):
    """«красное» окно 12×12 at 28–44 with frame (+2), optional shutters; lit = warm glow from inside (night)."""
    a1 = a0 + w
    side = "lit" if face == "v" else "sh"
    fr = C["wood_lt"] if side == "lit" else C["wood_md"]
    wall_quad(S, face, c, a0 - 0.13, a1 + 0.13, z0, z0 + h + 3, flat(fr), 0.3)
    glass = (C["flame"] if lit else C["night"])
    wall_quad(S, face, c, a0, a1, z0 + 2, z0 + h + 1, flat(glass), 0.4)
    if lit:
        wall_quad(S, face, c, a0, a1, z0 + 2, z0 + 5, flat(C["ember"]), 0.42)
    wall_quad(S, face, c, (a0 + a1) / 2 - 0.03, (a0 + a1) / 2 + 0.03, z0 + 2, z0 + h + 1, flat(C["wood"]), 0.45)
    wall_quad(S, face, c, a0, a1, z0 + 7, z0 + 8, flat(C["wood"]), 0.45)
    if shutters:
        sh = C["wood_md"] if side == "lit" else C["wood"]
        for (sa, sb) in ((a0 - 0.5, a0 - 0.13), (a1 + 0.13, a1 + 0.5)):
            wall_quad(S, face, c, sa, sb, z0, z0 + h + 3, flat(sh), 0.32)
            wall_quad(S, face, c, sa + 0.06, sb - 0.06, z0 + 2, z0 + 4, flat(C["wood_dk"]), 0.34)
            wall_quad(S, face, c, sa + 0.06, sb - 0.06, z0 + h - 2, z0 + h, flat(C["wood_dk"]), 0.34)
    if kokoshnik:
        m = (a0 + a1) / 2
        S.face([(m - 0.55, c, z0 + h + 3), (m + 0.55, c, z0 + h + 3), (m, c, z0 + h + 9)] if face == "v" else
               [(c, m - 0.55, z0 + h + 3), (c, m + 0.55, z0 + h + 3), (c, m, z0 + h + 9)],
               flat(fr), out=(0, 1, 0) if face == "v" else (1, 0, 0), bias=0.33)


def vol_window(S, face, c, am, z0=36, glow=False):
    """волоковое окошко 8×5 at 36–41 (smoke hole): dark slit in a light frame."""
    side = "lit" if face == "v" else "sh"
    wall_quad(S, face, c, am - 0.38, am + 0.38, z0 - 2, z0 + 7, flat(C["wood_md"] if side == "lit" else C["wood"]), 0.3)
    wall_quad(S, face, c, am - 0.25, am + 0.25, z0, z0 + 5, flat(C["ember"] if glow else INK), 0.4)
    return S.P(c if face == "u" else am, am if face == "u" else c, z0 + 5)


def finish(S, A, B, extra=None):
    """outline, crop, pivot = screen point of the footprint centre (scale.md §4.1)."""
    S.outline()
    idx, (x0, y0) = S.crop()
    px, py = S.P(A / 2.0, B / 2.0, 0)
    corner = S.P(0, 0, 0)
    fp = [S.P(0, 0), S.P(A, 0), S.P(A, B), S.P(0, B)]
    meta = dict(pivot=[int(round(px - x0)), int(round(py - y0))],
                proto_corner_px=[int(round(corner[0] - x0)), int(round(corner[1] - y0))],
                footprint_px=[[int(round(x - x0)), int(round(y - y0))] for x, y in fp],
                front_corner_px=[int(round(fp[2][0] - x0)), int(round(fp[2][1] - y0))])
    return idx, (x0, y0), meta


# ------------------------------------------------------------------ small props drawn into a building (2-D, with depth)
def kadka(S, u, v):
    """кадка (tub) 12×16 at ground point (u, v): staves, two hoops, water."""
    x, y = S.P(u, v, 0)
    d = S.depth(u, v, 0) + 16
    x, y = int(round(x)), int(round(y))
    rows = ["..kkkkkkkk..",
            ".kssssssssk.",
            "kwwwwwwwwwwk",
            "kWWwwwwwwwwk",
            ".kssssssssk.",
            ".kLLLlLLLlk.",
            ".kLLlLLLlLk.",
            ".kiiiiiiiik.",
            ".kLLlLLLlLk.",
            ".kLLlLLLlLk.",
            ".kLLlLLLlLk.",
            ".kiiiiiiiik.",
            ".kLLlLLLlLk.",
            "..kLlLLLlk..",
            "...kkkkkk..."]
    pal = {"k": C["ink"], "s": C["wood_md"], "w": C["sea"], "W": C["slate_lt"], "L": C["wood_md"], "l": C["wood"],
           "i": C["slate"]}
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                S.px(x - 6 + i, y - len(rows) + 1 + j, pal[ch], d)


def sacks(S, u, v, n=3, seed=0):
    """мешки (grain sacks) 10×12 each, birch ramp, tied tops."""
    rows = ["....kk....",
            "...kBbk...",
            "...kssk...",
            "..kBBBbk..",
            ".kBBBBBbk.",
            "kBBBBBBbbk",
            "kBBBBBbbbk",
            "kBBBBbbbbk",
            "kBBBBbbbbk",
            "kBBBbbbbbk",
            ".kBbbbbbk.",
            "..kkkkkk.."]
    pal = {"k": C["ink"], "b": C["wood_md"], "B": C["wood_lt"], "s": C["wood"]}   # burlap
    for t in range(n):
        uu, vv = u + 0.42 * t, v + (0.12 if t % 2 else 0)
        x, y = S.P(uu, vv, 0)
        d = S.depth(uu, vv, 0) + 12
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch in pal:
                    S.px(int(round(x)) - 5 + i, int(round(y)) - len(rows) + 1 + j, pal[ch], d)


def woodpile(S, u, v, length=1.6):
    """поленница along v: stacked logs, end grain facing +u, 20 px high."""
    for row in range(5):
        for t in np.arange(0, length, 0.19):
            vv = v + t + (0.09 if row % 2 else 0)
            if vv > v + length:
                continue
            x, y = S.P(u, vv, 2 + row * 4)
            d = S.depth(u, vv, 2 + row * 4) + 0.3
            ring = np.array([[-1, 1, 1, -1], [1, 2, 3, 1], [1, 3, 2, 1], [-1, 1, 1, -1]])
            tone = np.where(ring == 1, C["wood_dk"], np.where(ring == 2, C["wood_lt"], np.where(ring == 3, C["birch"], -1)))
            S.blit(tone.astype(np.int16), x - 2, y - 2, d)


# ------------------------------------------------------------------ sheet helpers
CANVAS_MARGIN = 70


def new_canvas(A, B, maxh=210):
    W = int((A + B) * 16 + CANVAS_MARGIN * 2)
    H = int(maxh + (A + B) * 8 + CANVAS_MARGIN)
    return lambda: I.Iso(W, H, B * 16 + CANVAS_MARGIN, maxh + 20)


def render_frames(A, B, fns, maxh=210):
    """render each fn(S) on identical canvases; crop all frames to the union box; returns (frames, meta)."""
    mk = new_canvas(A, B, maxh)
    Ss = []
    for fn in fns:
        S = mk()
        ex = fn(S) or {}
        S.outline()
        Ss.append((S, ex))
    op = np.zeros_like(Ss[0][0].idx, bool)
    for S, _ in Ss:
        op |= S.idx >= 0
    ys, xs = np.nonzero(op)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    frames = [S.idx[y0:y1, x0:x1].copy() for S, _ in Ss]
    S = Ss[0][0]
    tr = lambda p: [int(round(p[0] - x0)), int(round(p[1] - y0))]
    meta = dict(pivot=tr(S.P(A / 2.0, B / 2.0, 0)), proto_corner_px=tr(S.P(0, 0, 0)),
                footprint_px=[tr(S.P(0, 0)), tr(S.P(A, 0)), tr(S.P(A, B)), tr(S.P(0, B))],
                front_corner_px=tr(S.P(A, B)))
    anchors = {}
    for i, (Sx, ex) in enumerate(Ss):
        for k, v in ex.items():
            anchors.setdefault(k, {})[str(i)] = tr(v)
    meta["anchors_px"] = anchors
    return frames, meta


DOORS = ("v", "u", "hidden")
DOOR_FRAMES = {"+y": 0, "+x": 1, "-x": 2, "-y": 2}


# ------------------------------------------------------------------ H2: малая изба 4×4, 3 облика
def izba_small(look):
    A = B = 4

    def fn(door):
        def f(S):
            ex = {}
            if look == "tes_kon":
                k = cabin(S, 0, 0, 4, 4, 68, 44, roof="tes", ridge="horse", seed=1)
            elif look == "dern":
                k = cabin(S, 0, 0, 4, 4, 68, 44, roof="dern", ridge="sod", seed=2)
            else:   # tes_prich
                k = cabin(S, 0, 0, 4, 4, 68, 44, roof="tes", roof_wood="new", ridge="plain", prich=True, seed=3)
            kur = look == "dern"
            kok = look == "tes_prich"
            if door == "v":
                globals()["door"](S, "v", 4, 0.7, seed=5)
                if kur:
                    ex["smoke"] = vol_window(S, "v", 4, 3.0, 40, glow=True)
                else:
                    window(S, "v", 4, 2.85, lit=True, kokoshnik=kok)
            else:
                if kur:
                    vol_window(S, "v", 4, 1.2, 40)
                    ex["smoke"] = vol_window(S, "v", 4, 2.8, 40, glow=True)
                else:
                    window(S, "v", 4, 0.75, lit=door == "hidden", kokoshnik=kok)
                    window(S, "v", 4, 2.55, lit=True, kokoshnik=kok)
            if door == "u":
                globals()["door"](S, "u", 4, 1.28, seed=6)
            else:
                if kur:
                    vol_window(S, "u", 4, 2.0, 40)
                else:
                    window(S, "u", 4, 1.65, lit=look != "tes_kon", kokoshnik=kok)
            ex["gable_vent"] = vol_window(S, "u", 4, 2.0, 82) if not kur else S.P(4, 2, 82)
            ex["caption"] = S.P(2, 4, 64)
            return ex
        return f
    return render_frames(A, B, [fn(d) for d in DOORS], maxh=150)


# ------------------------------------------------------------------ H3: изба с сенями 6×4, 2 облика
def izba_seni(look):
    A, B = 6, 4

    def fn(door):
        def f(S):
            ex = {}
            roof = "tes" if look == "tes" else "dern"
            ridge_main = "horse" if look == "tes" else "sod"
            cabin(S, 0, 0, 4, 4, 68, 44, roof=roof, ridge=ridge_main, seed=11)
            # сени: lower, older logs, gable towards +u
            cabin(S, 4, 0, 6, 4, 52, 32, roof=roof, ridge="plain" if look == "tes" else "sod", wood="grey", seed=12,
                  og=0.25, roof_wood="grey" if look == "tes" else None)
            window(S, "v", 4, 0.7, lit=True)
            window(S, "v", 4, 2.45, lit=look == "tes")
            if door == "v":
                globals()["door"](S, "v", 4, 4.35, w=1.3, h=44, seed=7)
            else:
                window(S, "v", 4, 4.9, z0=26, w=8 / 16, h=9, lit=False, shutters=False)
            if door == "u":
                globals()["door"](S, "u", 6, 1.35, w=1.3, h=44, seed=8)
            else:
                vol_window(S, "u", 6, 2.0, 30)
            ex["smoke"] = S.P(4.0, 2.0, 112) if look == "dern" else S.P(2.0, 2.0, 114)
            ex["caption"] = S.P(3, 4, 64)
            return ex
        return f
    return render_frames(A, B, [fn(d) for d in DOORS], maxh=150)


# ------------------------------------------------------------------ H4: клеть, баня, амбар 3×3
def klet():
    A = B = 3

    def fn(door):
        def f(S):
            cabin(S, 0, 0, 3, 3, 60, 36, roof="tes", roof_wood="grey", wood="grey", ridge="plain", seed=21)
            if door == "v":
                globals()["door"](S, "v", 3, 0.9, w=1.25, h=52, bolt=True, lock=True, seed=9)
            if door == "u":
                globals()["door"](S, "u", 3, 0.9, w=1.25, h=52, bolt=True, lock=True, seed=10)
            return {"caption": S.P(1.5, 3, 56)}
        return f
    return render_frames(A, B, [fn(d) for d in DOORS], maxh=130)


def banya(look):
    A = B = 3

    def fn(door):
        def f(S):
            ex = {}
            cabin(S, 0, 0, 3, 3, 60, 36, roof="tes" if look == "tes" else "dern", wood="dark", weather=0.0,
                  ridge="plain" if look == "tes" else "sod", seed=31, roof_wood="grey" if look == "tes" else None)
            if door == "v":
                globals()["door"](S, "v", 3, 0.5, w=1.25, h=49, seed=11)
                ex["smoke"] = vol_window(S, "v", 3, 2.35, 38, glow=True)
                kadka(S, 2.35, 3.55)
            else:
                ex["smoke"] = vol_window(S, "v", 3, 1.5, 38, glow=True)
            if door == "u":
                globals()["door"](S, "u", 3, 0.6, w=1.25, h=49, seed=12)
                kadka(S, 3.55, 2.4)
            else:
                vol_window(S, "u", 3, 1.5, 38)
            if door == "hidden":
                kadka(S, 3.5, 3.4)
            ex["caption"] = S.P(1.5, 3, 56)
            return ex
        return f
    return render_frames(A, B, [fn(d) for d in DOORS], maxh=130)


def ambar():
    A = B = 3

    def fn(door):
        def f(S):
            # stone «стулья» under the corners and mid-sides (8 px)
            for (su, sv) in ((0.15, 2.85), (1.5, 2.85), (2.85, 2.85), (2.85, 1.5), (2.85, 0.15), (0.15, 0.15), (0.15, 1.5), (1.5, 0.15)):
                S.box(su - 0.18, sv - 0.18, su + 0.18, sv + 0.18, 0, 8,
                      lambda U, V, Z, a, b: np.where(H2(np.floor(V * 16).astype(np.int64), np.floor(Z).astype(np.int64), 2) < 0.3, C["slate_dk"], C["slate"]).astype(np.int16),
                      lambda U, V, Z, a, b: np.where(H2(np.floor(U * 16).astype(np.int64), np.floor(Z).astype(np.int64), 3) < 0.3, C["slate"], C["slate_lt"]).astype(np.int16),
                      flat(C["mist"]))
            cabin(S, 0, 0, 3, 3, 52, 36, z0=8, roof="tes", wood="wood", ridge="plain", seed=41)
            ex = {"caption": S.P(1.5, 3, 56)}
            if door == "v":
                globals()["door"](S, "v", 3, 0.9, w=1.25, h=44, z0=12, lock=True, seed=13)
                # ramp board to the door + sacks
                S.face([(0.85, 3.0, 12), (2.2, 3.0, 12), (2.2, 3.7, 0), (0.85, 3.7, 0)], boards("lit", "wood", 3, 4, "u"), out=(0, 1, 1), bias=0.5)
                sacks(S, 2.45, 3.5, 3)
            if door == "u":
                globals()["door"](S, "u", 3, 0.9, w=1.25, h=44, z0=12, lock=True, seed=14)
                S.face([(3.0, 0.85, 12), (3.0, 2.2, 12), (3.7, 2.2, 0), (3.7, 0.85, 0)], boards("sh", "wood", 3, 4, "v"), out=(1, 0, 1), bias=0.5)
                sacks(S, 3.45, 2.4, 2)
            if door == "hidden":
                sacks(S, 3.35, 3.3, 2)
            return ex
        return f
    return render_frames(A, B, [fn(d) for d in DOORS], maxh=130)


# ------------------------------------------------------------------ H1: клетская церковь 6×4
def glavka(S, u, v, z):
    """главка on the ridge: log drum 6, шлемовидный cap in осиновый лемех 8, simple cross 10 → top = z + 24.
    no onion, no tent, no other signs."""
    x, y = S.P(u, v, z)
    x, y = int(round(x)), int(round(y))
    d = S.depth(u, v, z) + 6
    # drum: 12 wide, 6 tall (two log courses), lit from the left
    for j in range(6):
        for i in range(-6, 6):
            c = C["wood_lt"] if i < -3 else (C["wood_md"] if i < 0 else (C["wood"] if i < 4 else C["wood_dk"]))
            if j % 3 == 0:
                c = C["wood_dk"] if i >= 0 else C["wood"]
            S.px(x + i, y - j, c, d)
    # cap: helmet profile 16 wide at the bottom, rounded shoulders, short point; лемех rows
    prof = [8, 8, 8, 7, 6, 5, 3, 1]
    yb = y - 6
    for j, hw in enumerate(prof):
        for i in range(-hw, hw):
            t = (i + hw) / (2.0 * hw)
            c = C["mist"] if t < 0.3 else (C["slate_lt"] if t < 0.62 else (C["slate"] if t < 0.88 else C["slate_dk"]))
            if j % 2 == 1 and (i + j // 2) % 3 == 0:
                c = {C["mist"]: C["slate_lt"], C["slate_lt"]: C["slate"], C["slate"]: C["slate_dk"]}.get(c, c)
            if j == 0:
                c = C["slate"] if t < 0.6 else C["slate_dk"]
            S.px(x + i, yb - j, c, d + 0.1)
    # cross: 10 tall, 2 px stem, bar 8 wide at row 7 (from the bottom)
    top = yb - len(prof)
    for j in range(10):
        S.px(x - 1, top - j, C["bronze_hi"], d + 0.2)
        S.px(x, top - j, C["bronze"], d + 0.2)
    for i in range(-4, 4):
        S.px(x + i, top - 7, C["bronze_hi"] if i < 0 else C["bronze_lt"], d + 0.2)
        S.px(x + i, top - 6, C["bronze_dk"] if i not in (-1, 0) else C["bronze"], d + 0.15)
    return (x, top - 9)


def church():
    A, B = 6, 4

    def f(S):
        ex = {}
        # паперть-навес on the west (−x, hidden side; overhangs the street x 25–26)
        for (pu, pv) in ((-1.05, 0.95), (-1.05, 3.05)):
            S.box(pu - 0.08, pv - 0.08, pu + 0.08, pv + 0.08, 0, 44, boards("sh", "wood", 3, 2, "v"), boards("lit", "wood", 3, 2, "u"),
                  flat(C["wood_md"]))
        S.face([(-1.25, 0.7, 44), (0, 0.7, 52), (0, 3.3, 52), (-1.25, 3.3, 44)], boards("lit", "grey", 3, 5, "v"),
               out=(-1, 0, 1), bias=0.2)
        S.face([(-1.25, 3.3, 44), (0, 3.3, 52), (0, 3.3, 50), (-1.25, 3.3, 42)], flat(C["slate_lt"]), out=(0, 1, 0), bias=0.25)
        # алтарный прируб 2×2 to the east, lower
        cabin(S, 4, 1, 6, 3, 64, 46, roof="tes", roof_wood="grey", gable="boards", ridge="plain", seed=52, og=0.25)
        # четверик 4×4: 22 венца
        k = cabin(S, 0, 0, 4, 4, 88, 70, roof="tes", roof_wood="grey", gable="boards", ridge="plain", seed=51)
        # окладной венец: darker, thicker bottom log
        S.quad_v(4.0 + 0.02, 0, 4, 0, 5, flat(C["wood"]), 1)
        S.quad_u(4.0 + 0.02, 0, 4, 0, 5, flat(C["wood_dk"]), 1)
        # south wall: 3 high narrow windows (no shutters), one on the прируб; east gable: small window above the прируб roof
        for a in (0.55, 1.75, 2.95):
            window(S, "v", 4, a, z0=46, w=8 / 16, h=16, lit=True, shutters=False)
        window(S, "v", 3, 4.75, z0=34, w=8 / 16, h=12, lit=False, shutters=False)
        window(S, "u", 6, 1.75, z0=34, w=8 / 16, h=12, lit=False, shutters=False)
        ex["cross_top"] = glavka(S, 2.0, 2.0, k["zr"] + 2)
        ex["caption"] = S.P(-0.5, 2.0, 64)               # над входом (паперть), GDD §7.1.1: подпись на высоте 64
        ex["bilo"] = S.P(-1.5, 3.5, 0)
        return ex
    return render_frames(A, B, [f], maxh=230)


# ------------------------------------------------------------------ H10: след взмаха «Сшибки»
SW_W, SW_H, SW_PIV = 48, 40, (24, 34)
SWING_DIRS = {"s": 90, "se": 45, "ne": -45, "n": -90}


def swing(dir_, frame):
    """120° arc in the ground plane at chest height (18 px above the feet): ellipse rx 22, ry 11, band r 0.62–1.0.
    frame 0: leading 70% of the sweep, bright head; frame 1: full arc fading, thinner. linen → birch → mist dither → gone."""
    a = np.full((SW_H, SW_W), -1, np.int16)
    yy, xx = np.mgrid[0:SW_H, 0:SW_W].astype(float)
    cx, cy = SW_PIV[0], SW_PIV[1] - 18
    ex, ey = (xx - cx + 0.5) / 22.0, (yy - cy + 0.5) / 11.0
    r = np.hypot(ex, ey)
    th = np.degrees(np.arctan2(ey, ex))
    c = SWING_DIRS[dir_]
    rel = (th - c + 180) % 360 - 180            # −180..180, swing goes from +60 (start) to −60 (end)
    t = (60 - rel) / 120.0                       # 0 at start, 1 at end of the sweep
    head = 0.72 if frame == 0 else 1.0
    inside = (t >= 0) & (t <= head)
    age = (head - t) / head                      # 0 at the head, 1 at the tail
    rin = 0.42 + 0.4 * age if frame == 0 else 0.52 + 0.38 * age
    band = inside & (r <= 1.0) & (r >= rin)
    bay = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    bm = bay[yy.astype(int) % 4, xx.astype(int) % 4]
    fade = age * 0.85 + (0.15 if frame == 1 else 0)
    col = np.where(fade < 0.4, C["linen"], np.where(fade < 0.7, C["birch"], C["mist"]))
    keep = band & ~((fade > 0.72) & (bm < (fade - 0.72) * 3.0))
    a[keep] = col[keep]
    return a


# ------------------------------------------------------------------ smoke wisp (курная изба, баня)
SM_W, SM_H, SM_PIV = 14, 28, (5, 27)


def smoke(frame):
    """4-frame looping wisp rising from an anchor (волоковое окно / roof), drifting right; slate_lt/mist, dithered."""
    a = np.full((SM_H, SM_W), -1, np.int16)
    for k in range(4):
        ph = (frame + k) % 4
        y = SM_PIV[1] - 3 - (ph * 6 + k * 0.0)
        x = SM_PIV[0] + ph * 1.3 + np.sin(ph * 1.7) * 1.0
        rad = 1.6 + ph * 0.7
        yy, xx = np.mgrid[0:SM_H, 0:SM_W]
        m = ((xx - x) ** 2 + (yy - y) ** 2) <= rad ** 2
        tone = C["mist"] if ph < 2 else C["slate_lt"]
        if ph == 3:
            m &= ((xx + yy) % 2 == 0)
        a[m] = tone
    return a


# ================================================================== P1 (H11–H15): single frame each, door as on the plan
def _barrel(S, u, v, z=0):
    x, y = S.P(u, v, z)
    x, y = int(round(x)), int(round(y))
    d = S.depth(u, v, z) + 12
    rows = [".kkkkkk.", "kwmmmmwk", "kwwwwwwk", "kmLLLlmk", "kiiiiiik", "kmLLLlmk", "kmLLLlmk", "kmLLLlmk",
            "kiiiiiik", "kmLLLlmk", ".kkkkkk."]
    pal = {"k": C["ink"], "w": C["wood_md"], "m": C["wood"], "L": C["wood_md"], "l": C["wood_lt"], "i": C["slate"]}
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                S.px(x - 4 + i, y - len(rows) + 1 + j, pal[ch], d)


def _bale(S, u, v, z=0):
    x, y = S.P(u, v, z)
    x, y = int(round(x)), int(round(y))
    d = S.depth(u, v, z) + 8
    rows = ["..kkkkkk..", ".kBBBBBbk.", "kBBsBBbbbk", "kBBsBbbbbk", "kbbsbbbbwk", ".kkkkkkkk."]
    pal = {"k": C["ink"], "B": C["birch"], "b": C["mist"], "s": C["wood_md"], "w": C["slate_lt"]}
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                S.px(x - 5 + i, y - len(rows) + 1 + j, pal[ch], d)


def izba_podklet():
    """H11 изба на подклете 5×5: подклет 24 (нижний ярус, тёмный, с волоковым продухом) + сруб 64 → 88, охлупень 132,
    конёк 144; наружная лестница-крыльцо к двери верхнего яруса на +x (к улице)."""
    def f(S):
        ex = {}
        # подклет (lower storey) — darker, heavier logs
        S.quad_v(5, 0, 5, 0, 24, logs("lit", "dark", 0, 0, 61, "u"), 1)
        S.quad_u(5, 0, 5, 0, 24, logs("sh", "dark", 0, 0, 62, "v"), 1)
        k = cabin(S, 0, 0, 5, 5, 64, 44, z0=24, roof="tes", ridge="horse", seed=63)
        vol_window(S, "v", 5, 1.2, 10)
        vol_window(S, "v", 5, 3.6, 10)
        S.quad_v(5.01, 0, 5, 23, 26, flat(C["wood_dk"]), 1, 0.3)       # окладной венец верхнего яруса (shadow line)
        S.quad_u(5.01, 0, 5, 23, 26, flat(C["ink"]), 1, 0.3)
        window(S, "v", 5, 0.8, z0=52, lit=True, kokoshnik=True)
        window(S, "v", 5, 2.3, z0=52, lit=True, kokoshnik=True)
        window(S, "v", 5, 3.8, z0=52, lit=False, kokoshnik=True)
        # door upstairs on +x
        door(S, "u", 5, 0.9, w=1.3, h=50, z0=28, seed=31)
        # крыльцо: landing on posts at z 26 + stair down along +v
        S.box(5.0, 0.6, 5.9, 2.4, 22, 26, boards("sh", "wood", 3, 4, "v"), boards("lit", "wood", 3, 4, "u"), flat(C["wood_lt"]), 0.2)
        for (pu, pv) in ((5.8, 0.7), (5.8, 2.3)):
            S.box(pu - 0.06, pv - 0.06, pu + 0.06, pv + 0.06, 0, 22, flat(C["wood"]), flat(C["wood_md"]), None, 0.2)
            S.box(pu - 0.05, pv - 0.05, pu + 0.05, pv + 0.05, 26, 40, flat(C["wood"]), flat(C["wood_md"]), flat(C["wood_lt"]), 0.3)
        S.box(5.8 - 0.04, 0.7, 5.8 + 0.04, 2.3, 38, 41, flat(C["wood"]), flat(C["wood_md"]), flat(C["wood_lt"]), 0.35)   # railing
        nst = 6
        for i in range(nst):
            v0 = 2.4 + i * 0.3
            z1 = 22 - i * 22 / nst
            S.box(5.05, v0, 5.85, v0 + 0.3, max(0, z1 - 4), z1, flat(C["wood"]), flat(C["wood_md"]), flat(C["wood_lt"]), 0.25)
        S.box(5.8, 2.4, 5.88, 4.2, 0, 4, flat(C["wood_dk"]), flat(C["wood"]), None, 0.3)   # stringer at the foot
        ex["caption"] = S.P(2.5, 5, 64)
        ex["smoke"] = S.P(2.5, 2.5, k["zr"] + 4)
        return ex
    return render_frames(5, 5, [f], maxh=190)


def hlev(look="dern"):
    """H12 хлев с сенником 4×3: низкий и широкий, стена 48, охлупень 88, сено торчит из-под кровли, ворота для скота +x."""
    def f(S):
        k = cabin(S, 0, 0, 4, 3, 48, 40, roof=look, ridge="sod" if look == "dern" else "plain", wood="grey", seed=71, og=0.35)
        # hay sticking out along the front eave and from the gable (сенник under the roof)
        for i, uu in enumerate(np.arange(-0.2, 4.3, 1 / 16)):
            h = int(H2(i, 2, 71) * 4)
            for j in range(h):
                x, y = S.P(uu, 3.18, k["ze"] - 3 - j)
                S.px(x, y, C["moss_lt"] if (i + j) % 3 else C["bronze_lt"], S.depth(uu, 3.18, k["ze"]) + 0.6)
        S.face([(4.02, 0.6, 50), (4.02, 2.4, 50), (4.02, 1.5, 74)], lambda U, V, Z, a, b: np.where(
            H2(np.floor(V * 16).astype(np.int64), np.floor(Z).astype(np.int64), 3) < 0.4, C["bronze_lt"], C["moss_lt"]).astype(np.int16),
            out=(1, 0, 0), bias=0.4)
        door(S, "u", 4, 0.75, w=1.5, h=40, seed=41)
        vol_window(S, "v", 3, 1.0, 30)
        vol_window(S, "v", 3, 3.0, 30)
        return {"caption": S.P(2, 3, 52)}
    return render_frames(4, 3, [f], maxh=130)


def ambar_pier(look):
    """H13 амбар у пристани 4×3 на сваях: столбы 16 + сруб 40 = 56, охлупень 88; сходни к воде (+y), бочки и тюки."""
    def f(S):
        for su in (0.2, 1.4, 2.6, 3.8):
            for sv in (0.2, 2.8):
                S.box(su - 0.1, sv - 0.1, su + 0.1, sv + 0.1, 0, 16, flat(C["wood"]), flat(C["wood_md"]), None, 0.1)
        S.box(-0.05, -0.05, 4.05, 3.05, 14, 17, flat(C["wood_dk"]), flat(C["wood"]), None, 0.15)
        cabin(S, 0, 0, 4, 3, 40, 32, z0=17, roof="tes" if look == "tes" else "dern", ridge="plain" if look == "tes" else "sod",
              wood="grey" if look == "tes" else "wood", roof_wood="new" if look == "tes" else None, seed=81 if look == "tes" else 82)
        door(S, "v", 3, 1.3, w=1.3, h=34, z0=19, lock=True, seed=51)
        # сходни: plank ramp from the door sill down to the ground towards +y
        S.face([(1.25, 3.0, 17), (2.65, 3.0, 17), (2.65, 4.3, 0), (1.25, 4.3, 0)], boards("lit", "wood", 3, 6, "u"), out=(0, 1, 1), bias=0.5)
        for t in (0.35, 0.7, 1.0):
            S.face([(1.25, 3.0 + 1.3 * t, 17 * (1 - t) + 1), (2.65, 3.0 + 1.3 * t, 17 * (1 - t) + 1),
                    (2.65, 3.0 + 1.3 * t, 17 * (1 - t) + 2), (1.25, 3.0 + 1.3 * t, 17 * (1 - t) + 2)], flat(C["wood_dk"]), out=(0, 1, 0), bias=0.6)
        _barrel(S, 3.4, 3.6)
        _barrel(S, 3.85, 3.3)
        _bale(S, 0.6, 3.7)
        return {"caption": S.P(2, 3, 52)}
    return render_frames(4, 3, [f], maxh=120)


def masterskaya():
    """H14 мастерская косторезов 5×4: сруб 3.5×4 (стена 60, охлупень 100) + навес на столбах 52 на запад (−x, к улице),
    под навесом верстак, связки рогов, корзина с гребнями."""
    def f(S):
        k = cabin(S, 1.5, 0, 5, 4, 60, 40, roof="tes", ridge="plain", seed=91, og=0.25)
        # lean-to навес over u 0..1.5, sloping from the wall (z 58) down to the posts (z 52)
        S.face([(-0.15, -0.1, 50), (1.5, -0.1, 58), (1.5, 4.25, 58), (-0.15, 4.25, 50)], boards("lit", "grey", 3, 92, "v"),
               out=(-1, 0, 1), bias=0.2)
        S.face([(-0.15, 4.25, 50), (1.5, 4.25, 58), (1.5, 4.25, 56), (-0.15, 4.25, 48)], flat(C["slate_lt"]), out=(0, 1, 0), bias=0.25)
        for pv in (0.15, 2.0, 3.85):
            S.box(0.05, pv - 0.07, 0.19, pv + 0.07, 0, 50, flat(C["wood"]), flat(C["wood_md"]), None, 0.2)
        # верстак
        S.box(0.4, 1.0, 1.0, 3.2, 14, 17, flat(C["wood_md"]), flat(C["wood_lt"]), flat(C["birch"]), 0.3)
        for pv in (1.1, 3.1):
            S.box(0.45, pv - 0.05, 0.55, pv + 0.05, 0, 14, flat(C["wood"]), flat(C["wood_md"]), None, 0.3)
        # bone / antler offcuts on the bench, antler bundles against the wall (birch, linen)
        for i, (bu, bv) in enumerate(((0.7, 1.4), (0.75, 2.1), (0.65, 2.7))):
            x, y = S.P(bu, bv, 18)
            S.rect2(int(x) - 1, int(y) - 1, 3, 1, C["birch"], S.depth(bu, bv, 18) + 1)
        for j, (bu, bv) in enumerate(((1.42, 0.6), (1.42, 3.6), (1.95, 4.12), (3.55, 4.12))):
            x, y = S.P(bu, bv, 0)
            d = S.depth(bu, bv, 0) + 24          # sprite rises 20 px: keep it in front of the wall it leans on
            for t in range(16):
                S.px(int(x) + (t % 3) - 1, int(y) - 4 - t, C["birch"] if t % 4 else C["mist"], d)
                if t % 5 == 2:
                    S.px(int(x) + 2, int(y) - 5 - t, C["birch"], d); S.px(int(x) - 2, int(y) - 4 - t, C["birch"], d)
            S.rect2(int(x) - 2, int(y) - 10, 5, 1, C["wood_dk"], d + 0.1)
        # basket with combs
        x, y = S.P(2.6, 4.3, 0)
        d = S.depth(2.6, 4.3, 0) + 10
        S.rect2(int(x) - 4, int(y) - 6, 8, 6, C["wood_md"], d)
        for i in range(-4, 4, 2):
            S.px(int(x) + i, int(y) - 4, C["wood"], d + 0.01)
        for i in range(-3, 3):
            S.px(int(x) + i, int(y) - 7, C["birch"], d + 0.02)
        door(S, "v", 4, 3.0, w=1.3, h=50, seed=61) if False else None
        window(S, "v", 4, 2.9, lit=True)
        window(S, "v", 4, 4.15, lit=False, shutters=False)
        window(S, "u", 5, 1.7, lit=True)
        return {"caption": S.P(0.7, 2.0, 64), "smoke": S.P(3.25, 2.0, k["zr"] + 4)}
    return render_frames(5, 4, [f], maxh=140)


def lavka():
    """H15 лавка-навес 3×2: столбы 52, двускатный навес до 60, прилавок 16 с товаром (горшки, свёртки полотна, меха)."""
    def f(S):
        for pu in (0.15, 2.85):
            for pv in (0.15, 1.85):
                S.box(pu - 0.07, pv - 0.07, pu + 0.07, pv + 0.07, 0, 52, flat(C["wood"]), flat(C["wood_md"]), flat(C["wood_lt"]), 0.1)
        S.face([(-0.25, 1.0, 64), (3.25, 1.0, 64), (3.25, 2.3, 50), (-0.25, 2.3, 50)], roof_shader("tes", "front", 1.0, 2.3, 101, "new"),
               out=(0, 1, 1), bias=0.2)
        S.face([(-0.25, 1.0, 64), (3.25, 1.0, 64), (3.25, -0.3, 50), (-0.25, -0.3, 50)], roof_shader("tes", "back", 1.0, -0.3, 101, "new"),
               out=(0, -1, 1), bias=0.2)
        S.face([(3.25, 1.0, 64), (3.25, 2.3, 50), (3.25, 2.3, 48), (3.25, 1.0, 62)], flat(C["birch"]), out=(1, 0, 0), bias=0.3)
        S.face([(-0.25, 2.3, 50), (3.25, 2.3, 50), (3.25, 2.3, 48), (-0.25, 2.3, 48)], flat(C["wood_lt"]), out=(0, 1, 0), bias=0.3)
        S.beam((-0.25, 1.0, 65), (3.3, 1.0, 65), 3, "wood", (1, 3, 4), bias=0.9)
        # прилавок along +y
        S.box(0.25, 1.4, 2.75, 1.95, 0, 16, boards("sh", "wood", 3, 8, "v"), boards("lit", "wood", 3, 8, "u"), flat(C["wood_lt"]), 0.2)
        goods = [(0.5, "pot"), (0.9, "pot2"), (1.35, "cloth"), (1.8, "fur"), (2.3, "cloth2")]
        for gu, kind in goods:
            x, y = S.P(gu, 1.65, 16)
            x, y = int(round(x)), int(round(y))
            d = S.depth(gu, 1.65, 16) + 1
            if kind.startswith("pot"):
                c = C["wood_md"] if kind == "pot" else C["slate_lt"]
                S.rect2(x - 2, y - 6, 5, 6, c, d); S.rect2(x - 1, y - 7, 3, 1, C["ink"], d)
                S.px(x - 2, y - 5, C["wood_lt"] if kind == "pot" else C["mist"], d + 0.01)
            elif kind.startswith("cloth"):
                c = C["birch"] if kind == "cloth" else C["sea"]
                S.rect2(x - 3, y - 4, 7, 4, c, d); S.rect2(x - 3, y - 4, 1, 4, C["linen"] if kind == "cloth" else C["slate_lt"], d + 0.01)
            else:
                S.rect2(x - 3, y - 3, 7, 3, C["wood"], d); S.rect2(x - 2, y - 4, 5, 1, C["wood_md"], d)
        return {"caption": S.P(1.5, 1.0, 72)}
    return render_frames(3, 2, [f], maxh=110)


# ------------------------------------------------------------------ H16: мостовая из плах (32×16 tiles + edges)
def pave_tile(axis, seed, edge=None):
    """diamond 32×16 (prototype tile, top vertex at (16, 0)); planks lie ACROSS the travel axis:
    axis 'x' = road runs along world x (W–E) → planks parallel to y; axis 'y' = road along y (N–S).
    edge: None or one of 'ne','nw','se','sw' — a log curb along that diamond side (where the plank road meets the ground)."""
    a = np.full((16, 32), -1, np.int16)
    yy, xx = np.mgrid[0:16, 0:32].astype(float) + 0.5
    inside = (np.abs(xx - 16) / 16 + np.abs(yy - 8) / 8) <= 1.0
    u = ((xx - 16) / 16 + yy / 8) / 2       # world x within the tile 0..1
    v = (yy / 8 - (xx - 16) / 16) / 2       # world y within the tile 0..1
    t = u if axis == "x" else v              # along the travel axis
    s = v if axis == "x" else u              # across
    k = np.floor(t * 5).astype(int)
    fr = t * 5 - k
    tone = np.where(H2(k, np.zeros_like(k) + seed, 3) < 0.5, C["wood_md"], C["wood_lt"])
    grain = (H2(k, np.floor(s * 12).astype(int), seed + 1) < 0.18)
    col = np.where(grain, C["wood"], tone)
    col = np.where(fr < 0.18, C["wood_dk"], col)                      # gap between planks
    col = np.where((fr > 0.82) & (tone == C["wood_lt"]), C["birch"], col)
    col = np.where((H2(k, np.floor(s * 3).astype(int), seed + 5) < 0.05) & (fr > 0.3) & (fr < 0.6), C["wood_dk"], col)  # knot / wear
    a[inside] = col[inside]
    if edge:
        side = {"ne": v < 0.16, "sw": v > 0.84, "nw": u < 0.16, "se": u > 0.84}[edge]
        m = inside & side
        a[m] = C["wood"]
        a[inside & side & ({"ne": v < 0.06, "sw": v > 0.94, "nw": u < 0.06, "se": u > 0.94}[edge])] = C["wood_dk"]
    return a


# ------------------------------------------------------------------ H18: реквизит дворов
def prop_stog():
    """стог сена 1×1 вокруг шеста: купол Ø ≈ 1,3 тайла, высота 40, шест +8."""
    def f(S):
        x, y = S.P(0.5, 0.5, 0)
        x, y = int(round(x)), int(round(y))
        d = S.depth(0.5, 0.5, 0) + 30
        for j in range(40):
            t = j / 40.0
            hw = int(round(16 * (1 - t ** 2.2) ** 0.5 if t < 1 else 0)) if j > 2 else 14
            for i in range(-hw, hw + 1):
                lit = (i - (-hw)) / max(1, 2 * hw) + t * 0.15 + (H2(i, j, 7) - 0.5) * 0.35
                c = C["bronze_lt"] if lit < 0.3 else (C["moss_lt"] if lit < 0.55 else (C["wood_lt"] if lit < 0.8 else C["wood_md"]))
                if H2(i, j // 2, 9) < 0.08:
                    c = C["wood"]
                S.px(x + i, y - j + 2, c, d)
        for j in range(40, 49):
            S.px(x, y - j + 2, C["wood"], d + 0.1); S.px(x - 1, y - j + 2, C["wood_md"], d + 0.1)
        return {}
    return render_frames(1, 1, [f], maxh=70)


def prop_kadka():
    def f(S):
        kadka(S, 0.5, 0.75)
        return {}
    return render_frames(1, 1, [f], maxh=40)


def prop_roga():
    """связка рогов (лосиные/оленьи обрезки для косторезов) у стены: 1×1, высота 20."""
    def f(S):
        x, y = S.P(0.5, 0.5, 0)
        x, y = int(round(x)), int(round(y))
        d = S.depth(0.5, 0.5, 0) + 24
        for b in (-4, 0, 4):
            for t in range(18):
                xx = x + b + int(round(np.sin(t * 0.35 + b) * 1.5))
                S.px(xx, y - t, C["birch"] if t % 5 else C["mist"], d)
                if t in (6, 11, 15):
                    S.px(xx + (1 if b >= 0 else -1), y - t - 1, C["birch"], d)
                    S.px(xx + (2 if b >= 0 else -2), y - t - 2, C["linen"], d)
        S.rect2(x - 6, y - 8, 13, 2, C["wood_dk"], d + 0.1)        # cord
        return {}
    return render_frames(1, 1, [f], maxh=40)


def prop_telega_broken():
    """телега без колеса 3×2: кузов осел на угол (−x, +y), одно колесо лежит рядом, оглобли на земле."""
    def f(S):
        # body tilted: z at the +x end 14, at the −x end 6
        z0, z1 = 6, 14
        zt = lambda u: z0 + (z1 - z0) * (u - 0.3) / 2.4
        S.face([(0.3, 0.5, zt(0.3)), (2.7, 0.5, zt(2.7)), (2.7, 1.5, zt(2.7)), (0.3, 1.5, zt(0.3))], boards("lit", "wood", 3, 2, "u"),
               out=(0, 0, 1), bias=0.1)
        S.face([(0.3, 1.5, zt(0.3)), (2.7, 1.5, zt(2.7)), (2.7, 1.5, zt(2.7) + 8), (0.3, 1.5, zt(0.3) + 8)], boards("lit", "wood", 3, 3, "u"),
               out=(0, 1, 0), bias=0.2)
        S.face([(2.7, 0.5, zt(2.7)), (2.7, 1.5, zt(2.7)), (2.7, 1.5, zt(2.7) + 8), (2.7, 0.5, zt(2.7) + 8)], boards("sh", "wood", 3, 4, "v"),
               out=(1, 0, 0), bias=0.2)
        # remaining wheel on the +x end (disc in the v-plane), fallen wheel flat on the ground
        for (wu, wv, flatw) in ((2.2, 1.55, False), (0.9, 1.9, True)):
            x, y = S.P(wu, wv, 0 if flatw else 11)
            x, y = int(round(x)), int(round(y))
            d = S.depth(wu, wv, 12) + 2
            yy, xx = np.mgrid[-12:13, -12:13]
            r = np.hypot(xx, yy * (2.0 if flatw else 1.0))
            ring = (r <= 11) & (r >= 9)
            spokes = (r < 9) & ((np.abs(xx) <= 0) | (np.abs(yy) <= 0) | (np.abs(xx - yy) <= 0) | (np.abs(xx + yy) <= 0))
            hub = r <= 2
            for m, c in ((ring, C["wood_md"]), (spokes, C["wood"]), (hub, C["wood_dk"])):
                ys, xs = np.nonzero(m)
                S.put(ys - 12 + y, xs - 12 + x, c, d)
        S.beam((-0.6, 1.0, 1), (0.3, 0.8, 6), 2, "wood", (1, 2, 3), bias=0.3)   # оглобли
        S.beam((-0.6, 1.3, 1), (0.3, 1.3, 6), 2, "wood", (1, 2, 3), bias=0.3)
        return {}
    return render_frames(3, 2, [f], maxh=60)

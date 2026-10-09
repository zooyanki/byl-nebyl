"""Review scenes for GDD v1.13 §12.1.7 (review only, not game assets):
  village_scenes/ladoga_v113_native.png  — the whole Ладога plan (§7.1.1) at native scale with the hero for scale
  village_scenes/view_*.png              — 640×360 frames (play field 640×314 + HUD strip), ×1 and ×2
  village_scenes/mockup_dialogue_*.png   — dialogue window (§10.4) with portrait, nav marker; nav arrow at the edge
Positions are read from the plan table; sprites from art/sprites/buildings, art/ui/{dialogue,nav,portraits}."""
import os
import sys
import json
import numpy as np
from PIL import Image
import rig  # noqa: F401
import pixelkit as pk
from pixelkit import C
import iso3d as I
import village as VL
import village_gates as G

ART = "/workspace/game/art"
BLD = ART + "/sprites/buildings"
OUT = ART + "/sprites/village_scenes"
ZONE = json.load(open("/workspace/game/prototype/data/zones/ladoga.json"))
MW, MH = ZONE["size"]
OX, OY = MH * 16 + 32, 230            # screen origin of world (0,0) on the big canvas
WIDTH, HEIGHT = (MW + MH) * 16 + 64, (MW + MH) * 8 + 260


def S2(x, y, z=0.0):
    return (OX + (x - y) * 16.0, OY + (x + y) * 8.0 - z)


def load(name):
    """index array strip + meta for a sheet in buildings/ (or any path)."""
    p = name if name.endswith(".png") else os.path.join(BLD, name + ".png")
    meta = json.load(open(p[:-4] + ".json"))
    rgba = np.array(Image.open(p).convert("RGBA"))
    lut = {tuple(c): i for i, c in enumerate(pk.RGB.tolist())}
    idx = np.full(rgba.shape[:2], -1, np.int16)
    m = rgba[..., 3] > 0
    idx[m] = [lut[tuple(c)] for c in rgba[m][:, :3].tolist()]
    fw, fh = meta.get("frame_size", [idx.shape[1], idx.shape[0]])
    frames = [idx[:, i * fw:(i + 1) * fw] for i in range(idx.shape[1] // fw)]
    return frames, meta


# ---------------------------------------------------------------- ground
def ground():
    g = np.full((HEIGHT, WIDTH), C["pine_dk"], np.int16)
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(float)
    X = ((xx - OX) / 16.0 + (yy - OY) / 8.0) / 2.0
    Y = ((yy - OY) / 8.0 - (xx - OX) / 16.0) / 2.0
    inside = (X >= 0) & (Y >= 0) & (X < MW) & (Y < MH)
    tx, ty = np.floor(X).astype(int), np.floor(Y).astype(int)
    h = pk.hash2(np.floor(X * 4).astype(np.int64), np.floor(Y * 4).astype(np.int64), 3)
    grass = np.where(h < 0.55, C["moss"], np.where(h < 0.85, C["pine"], C["moss_lt"]))
    col = grass.copy()
    ns, we = ZONE["roads"]["ns"], ZONE["roads"]["we"]
    road = ((tx >= ns[0]) & (tx <= ns[1]) & (ty >= ns[2]) & (ty <= ns[3])) | ((ty >= we[2]) & (ty <= we[3]) & (tx >= we[0]) & (tx <= we[1]))
    sand = (ty >= ZONE["sand"][0]) & (ty <= ZONE["sand"][1])
    water = ty >= ZONE["waterFromY"]
    px_, py_, pw_, ph_ = ZONE["pier"]
    pier = (tx >= px_) & (tx < px_ + pw_) & (ty >= py_) & (ty < py_ + ph_)
    col = np.where(road & ~water, np.where(h < 0.6, C["wood"], C["wood_md"]), col)
    col = np.where(sand & ~water, np.where(h < 0.6, C["wood_lt"], C["birch"]), col)
    col = np.where(water & ~pier, np.where(h < 0.7, C["sea_dk"], C["sea"]), col)
    col = np.where(pier, np.where((np.floor(X * 6) % 2) == 0, C["wood_md"], C["wood"]), col)
    # faint tile grid (alignment check)
    gx = np.abs(X - np.round(X)) < 0.02
    gy = np.abs(Y - np.round(Y)) < 0.02
    col = np.where((gx | gy) & ~water, np.where(road | sand, C["wood_dk"], C["pine"]), col)
    g[inside] = col[inside]
    # P1 мостовая (GDD §7.4 pavement rects) from tile_mostovaya / _edge
    tl, _ = load(ART + "/sprites/tiles/tile_mostovaya.png")
    ed, _ = load(ART + "/sprites/tiles/tile_mostovaya_edge.png")
    for (rx, ry, rw, rh) in ((22, 23, 4, 18), (25, 20, 23, 4)):
        along_x = rw > rh
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                if y >= ZONE["waterFromY"] or x > 39:
                    continue
                h = int(pk.hash2(np.int64(x), np.int64(y), 9) * 2)
                if along_x:
                    t = ed[0] if y == ry else ed[1] if y == ry + rh - 1 else tl[h]
                else:
                    t = ed[2] if x == rx else ed[3] if x == rx + rw - 1 else tl[2 + h]
                sx, sy = S2(x, y)
                ys, xs = np.nonzero(t >= 0)
                g[ys + int(sy), xs + int(sx) - 16] = t[ys, xs]
    return g


# ---------------------------------------------------------------- drawables
class Scene:
    def __init__(self):
        self.items = []    # (key, x, y, idx)

    def add(self, idx, sx, sy, key):
        self.items.append((key, int(round(sx)), int(round(sy)), idx))

    def sprite(self, frame, meta, x0, y0, key=None, A=None, B=None):
        pc = meta["proto_corner_px"]
        sx, sy = S2(x0, y0)
        A = A if A is not None else meta.get("footprint_tiles", [1, 1])[0]
        B = B if B is not None else meta.get("footprint_tiles", [1, 1])[1]
        self.add(frame, sx - pc[0], sy - pc[1], key if key is not None else (x0 + A / 2.0) + (y0 + B / 2.0))   # footprint centre, as prototype map.js

    def render(self, g):
        for key, x, y, idx in sorted(self.items, key=lambda t: t[0]):
            h, w = idx.shape
            ys, xs = np.nonzero(idx >= 0)
            Y, X = ys + y, xs + x
            ok = (Y >= 0) & (Y < g.shape[0]) & (X >= 0) & (X < g.shape[1])
            g[Y[ok], X[ok]] = idx[ys[ok], xs[ok]]
        return g


def palisade_cell(axis):
    S = I.Iso(64, 130, 32, 110)
    for t, a in enumerate((0.17, 0.5, 0.83)):
        G.stake(S, axis, a, 80 + (3, 0, 5)[t], t)
    G.bands(S, axis, 0, 1, 24)
    G.bands(S, axis, 0, 1, 64)
    S.outline()
    idx, (x0, y0) = S.crop()
    return idx, (int(round(S.P(0, 0)[0] - x0)), int(round(S.P(0, 0)[1] - y0)))


def greybox(sc, x0, y0, A, B, h, label=None, col="slate"):
    S = I.Iso((A + B) * 16 + 8, (A + B) * 8 + h + 8, B * 16 + 4, h + 4)
    S.box(0, 0, A, B, 0, h, VL.flat(C["slate"] if col == "slate" else C[col]), VL.flat(C["slate_lt"]), VL.flat(C["mist"]))
    S.outline()
    idx, (cx, cy) = S.crop()
    # placeholder look: 50 % checker so the grey box reads as «existing object, drawn by code», not as art
    yy, xx = np.mgrid[0:idx.shape[0], 0:idx.shape[1]]
    idx[((xx + yy) % 2 == 1) & (idx != C["ink"])] = -1
    pc = (S.P(0, 0)[0] - cx, S.P(0, 0)[1] - cy)
    sx, sy = S2(x0, y0)
    sc.add(idx, sx - pc[0], sy - pc[1], (x0 + A / 2.0) + (y0 + B / 2.0))


def npc_marker(sc, nx, ny):
    """NPC without a sprite: solid placeholder figure (dark robe post 36 + head 8), 0.5×0.5 tile, centred on the NPC point."""
    S = I.Iso(40, 72, 20, 60)
    S.box(-0.25, -0.25, 0.25, 0.25, 0, 36, VL.flat(C["night"]), VL.flat(C["slate_dk"]), VL.flat(C["slate"]))
    S.box(-0.13, -0.13, 0.13, 0.13, 36, 44, VL.flat(C["wood_md"]), VL.flat(C["wood_lt"]), VL.flat(C["slate_dk"]))
    S.outline()
    idx, (cx, cy) = S.crop()
    px_, py_ = S.P(0, 0)
    sx, sy = S2(nx, ny)
    sc.add(idx, int(round(sx - (px_ - cx))), int(round(sy - (py_ - cy))), nx + ny + 0.6)


PLAN_JSON = os.path.join(ART, "sprites", "village_scenes", "ladoga_plan_v1132.json")
PLAN = [(p["id"], p["sheet"], p["x0"], p["y0"], p["door"]) for p in json.load(open(PLAN_JSON))["buildings"]]
NPCS = json.load(open(PLAN_JSON)).get("npcs", [])


def build_scene(hero_at=(25.5, 19.5), extra=None):
    sc = Scene()
    smoke = load(ART + "/sprites/fx_smoke_wisp/fx_smoke_wisp.png")
    for pid, sheet, x0, y0, door in PLAN:
        frames, meta = load(sheet)
        df = meta.get("door_frames")
        fi = df.get(door, 0) if isinstance(df, dict) else 0
        sc.sprite(frames[fi], meta, x0, y0)
        sm = meta.get("anchors_px", {}).get("smoke")
        if sm and str(fi) in sm:
            ax, ay = sm[str(fi)]
            pc = meta["proto_corner_px"]
            sx, sy = S2(x0, y0)
            A, B = meta["footprint_tiles"]
            sc.add(smoke[0][1 % 4], sx - pc[0] + ax - smoke[1]["pivot"][0], sy - pc[1] + ay - smoke[1]["pivot"][1], (x0 + A / 2.0) + (y0 + B / 2.0) + 0.01)
    # existing v1.10 objects (code-drawn in the prototype) → grey boxes for context
    greybox(sc, 27, 26, 5, 4, 64)          # кузня
    greybox(sc, 33, 14, 5, 5, 152)         # терем
    greybox(sc, 20, 13, 2, 2, 24)          # колодец (сруб 24; журавль не рисую)
    greybox(sc, 37, 19, 1, 1, 60)          # идол у ворот
    greybox(sc, 27, 19, 1, 1, 32)          # путевой камень
    greybox(sc, 17, 16, 3, 2, 20)          # телеги
    greybox(sc, 28, 16, 3, 2, 20)
    for npc in NPCS:                       # NPC map sprite (npc_<id>_idle_se), else a placeholder post
        nx, ny = npc["at"]
        path = ART + "/sprites/npc_%s/npc_%s_idle_se.png" % (npc["id"], npc["id"])
        if os.path.exists(path):
            nf, nm = load(path)
            sx, sy = S2(nx, ny)
            key = nx + ny                          # dynamic: x + y, as prototype world.js
            sc.add(nf[0], int(sx) - nm["pivot"][0], int(sy) - nm["pivot"][1], key)
        else:
            npc_marker(sc, nx, ny)
    kr, km = load(ART + "/sprites/fx_rest_krada/fx_rest_krada_idle.png")
    kx, ky = ZONE["krada"]
    sx, sy = S2(kx + 1, ky + 1)
    sc.add(kr[0], sx - km["pivot"][0], sy - km["pivot"][1], kx + ky + 2)
    # palisade with gates (M1 state: E, S open; N, W closed)
    P = ZONE["palisade"]
    cells = {a: palisade_cell(a) for a in ("x", "y")}
    gate_cells = set()
    for side, state in (("e", "open"), ("s", "open"), ("n", "closed"), ("w", "closed")):
        axis, sin, (gx, gy) = G.GATES[side]
        for seg in "AB":
            fr, meta = load("gate_%s_%s_%s" % (side, state, seg))
            wt = meta["segment_info"]["world_tile"]
            sc.sprite(fr[1 % len(fr)], meta, gx, gy, key=wt[0] + wt[1] + 1.01)
        for k in range(4):
            gate_cells.add((gx, gy + k) if axis == "y" else (gx + k, gy))

    def gap(x, y):
        return any(x >= a and x < a + w and y >= b and y < b + h for a, b, w, h in P["gaps"])
    for y in range(P["y0"], P["y1"] + 1):
        for x in (P["x0"], P["x1"]):
            if not gap(x, y) and (x, y) not in gate_cells:
                idx, pc = cells["y"]
                sx, sy = S2(x, y)
                sc.add(idx, sx - pc[0], sy - pc[1], x + y + 1.01)
    for x in range(P["x0"], P["x1"] + 1):
        for y in (P["y0"], P["y1"]):
            if not gap(x, y) and (x, y) not in gate_cells:
                idx, pc = cells["x"]
                sx, sy = S2(x, y)
                sc.add(idx, sx - pc[0], sy - pc[1], x + y + 1.01)
    for name, x, y in (("prop_stog", 14, 15), ("prop_kadka", 35, 32), ("prop_roga", 32, 26), ("prop_telega_broken", 16, 28),
                       ("prop_stog", 12, 29), ("prop_kadka", 12, 34)):
        pf, pm = load(name)
        sc.sprite(pf[0], pm, x, y)
    sf, smeta = load("bld_ukazatel")
    sc.sprite(sf[0], smeta, 26, 18)
    sys.path.insert(0, ART + "/teaser/src")
    import teaser_sprites as TS
    hero = pk.sprite_to_index(TS.hero_pose("idle"))
    hx, hy = hero_at
    sx, sy = S2(hx, hy)
    sc.add(hero, sx - 32, sy - 56, hx + hy)
    for e in (extra or []):
        sc.add(*e)
    return sc, (hx, hy)


def to_img(a, scale=1):
    im = Image.fromarray(pk.RGB[a].astype(np.uint8))
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale > 1 else im


def view(g, cx, cy, w=640, h=314):
    x0, y0 = int(cx - w // 2), int(cy - h // 2)
    return g[y0:y0 + h, x0:x0 + w].copy(), (x0, y0)


# ---------------------------------------------------------------- UI overlays (index space)
def paste(cv, idx, x, y):
    ys, xs = np.nonzero(idx >= 0)
    cv[ys + y, xs + x] = idx[ys, xs]


def dialogue_mock(field, speaker, name, name_col, lines, page=None, end=False):
    import theme_rus as T
    import ui_rus as U
    from fonts_ru import FONT_RU
    full = np.full((360, 640), C["ink"], np.int16)
    full[:314] = field
    cv = pk.Canvas(640, 360)
    cv.a[:] = full
    # HUD strip placeholder (the real HUD v2 panel starts at y 314)
    cv.rect(0, 314, 640, 46, C["night"])
    T.text_ru(cv, 320, 332, "[панель HUD v2]", C["slate_lt"], align="c")
    # window 400×88 at (120, 222): night 0.92 (≈ opaque at this palette) + carved frame 9-slice
    cv.rect(120, 222, 400, 88, C["night"])
    fr, _ = load(ART + "/ui/dialogue/ui_dlg_frame_400x88.png")
    paste(cv.a, fr[0], 119, 221)
    # portrait frame 68×68 at (128, 232) — code-drawn (wood slot style), portrait at (130, 234)
    T.wood_slot(cv, 128, 232, 68, 68)
    por = np.array(Image.open(ART + "/ui/portraits/%s.png" % speaker).convert("RGB"))
    lut = {tuple(c): i for i, c in enumerate(pk.RGB.tolist())}
    cv.a[234:298, 130:194] = np.array([[lut[tuple(p)] for p in row] for row in por.tolist()])
    T.text_ru(cv, 204, 230, name, C[name_col])
    cv.hline(204, 241, 305, C["bronze_dk"])
    for i, ln in enumerate(lines):
        T.text_ru(cv, 204, 246 + 11 * i, ln, C["linen"])
    if page:
        T.text_ru(cv, 470, 296, page, C["mist"])
    g, _ = load(ART + "/ui/dialogue/%s.png" % ("ui_dlg_end" if end else "ui_dlg_more"))
    paste(cv.a, g[0], 502, 298)
    return cv.a


def contact_sheet():
    names = ["bld_church", "bld_izba_small_tes_kon", "bld_izba_small_dern", "bld_izba_small_tes_prich", "bld_izba_seni_tes",
             "bld_izba_seni_dern", "bld_klet", "bld_banya_dern", "bld_banya_tes", "bld_ambar", "bld_izba_podklet", "bld_hlev",
             "bld_ambar_pier_tes", "bld_ambar_pier_dern", "bld_masterskaya", "bld_lavka", "gate_e_open", "gate_n_closed",
             "bld_ukazatel", "prop_stog", "prop_kadka", "prop_roga", "prop_telega_broken"]
    tiles = []
    for n in names:
        fr, m = load(n)
        f = fr[0]
        h, w = f.shape
        t = np.full((h + 8, w + 8), C["moss"], np.int16)
        piv = m["pivot"]
        t[4 + piv[1], 4:4 + w] = C["pine"]
        ys, xs = np.nonzero(f >= 0)
        t[ys + 4, xs + 4] = f[ys, xs]
        tiles.append(t)
    rows, row, wsum = [], [], 0
    for t in tiles:
        if wsum + t.shape[1] > 1000 and row:
            rows.append(row); row, wsum = [], 0
        row.append(t); wsum += t.shape[1] + 4
    rows.append(row)
    H = sum(max(t.shape[0] for t in r) + 4 for r in rows)
    W = max(sum(t.shape[1] + 4 for t in r) for r in rows)
    out = np.full((H, W), C["night"], np.int16)
    y = 0
    for r in rows:
        rh = max(t.shape[0] for t in r)
        x = 0
        for t in r:
            out[y + rh - t.shape[0]:y + rh, x:x + t.shape[1]] = t
            x += t.shape[1] + 4
        y += rh + 4
    to_img(out).save(os.path.join(OUT, "buildings_sheet_native.png"))
    to_img(out, 2).save(os.path.join(OUT, "buildings_sheet_x2.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    contact_sheet()
    sc, hero = build_scene()
    g = sc.render(ground())
    to_img(g).save(os.path.join(OUT, "ladoga_v113_native.png"))
    # 640×314 views (play field), hero-centred where the camera would be
    views = {"torg_church": (27.0, 13.0, 70), "south_yards": (21.0, 31.5, 40), "east_gate": (35.0, 21.0, 40), "north_west": (14.0, 11.5, 50)}
    res = {}
    for k, (vx, vy, lift) in views.items():
        sx, sy = S2(vx, vy)
        f, _ = view(g, sx, sy - lift)
        to_img(f).save(os.path.join(OUT, "view_%s.png" % k))
        to_img(f, 2).save(os.path.join(OUT, "view_%s_x2.png" % k))
        res[k] = [vx, vy]
    # --- dialogue mockup: hero at Вышата's court (34.5, 19.5), marker over the east gate (target: «Выйди восточными воротами»)
    hx, hy = 33.6, 20.6
    sc2, _ = build_scene(hero_at=(hx, hy))
    g2 = sc2.render(ground())
    sx, sy = S2(hx, hy)
    f, (fx0, fy0) = view(g2, sx, sy - 22)
    mk, _ = load(ART + "/ui/nav/ui_nav_mark.png")
    gx, gy = S2(39.5, 22.0, 96)
    paste(f, mk[1], int(gx - fx0) - 4, int(gy - fy0) - 8)
    a = dialogue_mock(f, "portrait_vyshata", "Вышата", "bronze_hi",
                      ["Залесье — за восточными воротами. Поднимись к костру",
                       "и бери на восход, широкой улицей. Там люди горят."], page="4/4", end=True)
    to_img(a).save(os.path.join(OUT, "mockup_dialogue_vyshata.png"))
    to_img(a, 3).save(os.path.join(OUT, "mockup_dialogue_vyshata_x3.png"))
    # second mockup: Ратибор speaking (linen name), ▼ more, plus the priest portrait
    b = dialogue_mock(f, "portrait_ratibor", "Ратибор", "linen", ["Понял. Восточные ворота."], page="2/4")
    to_img(b, 3).save(os.path.join(OUT, "mockup_dialogue_ratibor_x3.png"))
    # third mockup (v1.13.2 portrait fix): поп Иоанн at the паперть, dlg.priest.s0.1
    hx, hy = 25.9, 14.7
    scp, _ = build_scene(hero_at=(hx, hy))
    gp = scp.render(ground())
    sx, sy = S2(hx, hy)
    fp, _ = view(gp, sx, sy - 22)
    c = dialogue_mock(fp, "portrait_priest", "Поп Иоанн", "bronze_hi",
                      ["С ладьи, дружинник? Видишь зарево? Дым оттуда",
                       "на всех один — и на Залесье, и на нас."], page="1/3")
    to_img(c).save(os.path.join(OUT, "mockup_dialogue_priest.png"))
    to_img(c, 3).save(os.path.join(OUT, "mockup_dialogue_priest_x3.png"))
    # close-up: поп Иоанн at the south паперть next to the hero, for scale (×3)
    sx, sy = S2(26.4, 14.1)
    fz, _ = view(gp, sx, sy - 40)
    cz = fz[110:250, 220:420]
    to_img(cz, 3).save(os.path.join(OUT, "scene_priest_paperte_x3.png"))
    # --- nav mockup: camera at the church, east gate off-screen → arrow on the right edge 14 px in, distance below
    hx, hy = 23.4, 14.2
    sc3, _ = build_scene(hero_at=(hx, hy))
    g3 = sc3.render(ground())
    sx, sy = S2(hx, hy)
    f, (fx0, fy0) = view(g3, sx, sy - 22)
    tx, ty = S2(39.5, 22.0)
    hxs, hys = 320, 157
    dx, dy = tx - fx0 - hxs, ty - fy0 - (hys - 22)
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    fi = int(round(ang / 45.0)) % 8
    t = min((320 - 14 - 6) / abs(dx) if dx else 1e9, (157 - 14 - 6) / abs(dy) if dy else 1e9)
    axp, ayp = int(hxs + dx * t), int(hys - 22 + dy * t)
    ar, _ = load(ART + "/ui/nav/ui_nav_arrow.png")
    cv = pk.Canvas(640, 360)
    cv.a[:] = C["ink"]
    cv.a[:314] = f
    paste(cv.a, ar[fi], axp - 6, ayp - 6)
    import theme_rus as T
    steps = int(round(np.hypot(39.5 - hx, 22.0 - hy)))
    T.text_ru(cv, axp, ayp + 8, str(steps), C["mist"], align="c")
    cv.rect(0, 314, 640, 46, C["night"])
    T.text_ru(cv, 320, 332, "[панель HUD v2]", C["slate_lt"], align="c")
    to_img(cv.a).save(os.path.join(OUT, "mockup_nav_arrow.png"))
    to_img(cv.a, 3).save(os.path.join(OUT, "mockup_nav_arrow_x3.png"))
    res["nav_arrow"] = dict(frame=fi, angle=round(float(ang), 1), at=[axp, ayp], steps=steps)
    return res


if __name__ == "__main__":
    print(main())

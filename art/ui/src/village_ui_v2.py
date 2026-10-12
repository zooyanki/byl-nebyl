"""UI for GDD v1.13 §10.2/§10.4 (H8 dialogue frame + ▼ ■, H9 nav arrow ×8 + marker, H17 minimap icons).
Indexed palette v2, -1 = transparent; PNG RGBA with alpha 0/255. New files only (old UI untouched):
/workspace/game/art/ui/dialogue/ and /workspace/game/art/ui/nav/."""
import os
import json
import numpy as np
from PIL import Image, ImageDraw
import pixelkit as pk
import theme_rus as T
import ui_rus as U

T.activate()
C = pk.C
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DLG = os.path.join(ROOT, "dialogue")
NAV = os.path.join(ROOT, "nav")


def rgba(idx):
    out = np.zeros(idx.shape + (4,), np.uint8)
    m = idx >= 0
    out[m, :3] = pk.RGB[idx[m]]
    out[m, 3] = 255
    return Image.fromarray(out, "RGBA")


def save(idx, folder, name, meta, scale_preview=3):
    os.makedirs(os.path.join(folder, "preview"), exist_ok=True)
    rgba(idx).save(os.path.join(folder, name + ".png"))
    big = np.where(idx >= 0, idx, C["slate_dk"])
    Image.fromarray(pk.RGB[big].astype(np.uint8)).resize((idx.shape[1] * scale_preview, idx.shape[0] * scale_preview),
                                                          Image.NEAREST).save(os.path.join(folder, "preview", name + "_x3.png"))
    meta = dict(meta, image=name + ".png", size=[int(idx.shape[1]), int(idx.shape[0])], palette="palette_v2", alpha="0/255 only")
    with open(os.path.join(folder, name + ".json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


KEY = None


def blank(w, h):
    """canvas filled with a key colour (nebyl: never used by the frame) → transparent on export."""
    return pk.Canvas(w, h, fill=C["nebyl"])


def unkey(cv):
    a = cv.a.astype(np.int16)
    a[a == C["nebyl"]] = -1
    return a


# ---------------------------------------------------------------- H8 dialogue frame
def frame_full(w=400, h=88):
    """carved_frame (same as quest tracker / HUD v2), interior transparent; +1 px all round for the corner plates."""
    cv = blank(w + 2, h + 2)
    U.carved_frame(cv, 1, 1, w, h, fill=None, corners=True)
    return unkey(cv)


def frame_9slice():
    """9-slice source 64×40: corners 8×8 (1 px plate overhang + 6 px band + inner ink line), edges 48 / 24 px =
    whole periods of the notch carving (12 px), centre transparent."""
    a = frame_full(62, 38)
    return a


GLYPH_V = ["kkkkkkk", "kHHHHBk", ".kHHBk.", "..kBk..", "...k..."]
GLYPH_SQ = [".kkkkk.", ".kHHBk.", ".kHBBk.", ".kBBBk.", ".kkkkk."]


def glyph(rows):
    pal = {"k": C["ink"], "H": C["bronze_hi"], "B": C["bronze_lt"]}
    a = np.full((5, 7), -1, np.int16)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                a[j, i] = pal[ch]
    return a


# ---------------------------------------------------------------- H9 nav arrow / marker
def raster(pts, n=12, ss=8):
    im = Image.new("L", (n * ss, n * ss), 0)
    ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    a = np.array(im.resize((n, n), Image.BOX)) > 100
    return a


def arrow(angle_deg):
    """notched arrowhead (➤) pointing at angle (0 = east, 90 = south, screen coords), fill bronze_hi, lower half
    bronze_lt, 1-px ink outline inside 12×12."""
    base = np.array([(5.0, 0.0), (-4.4, -4.4), (-2.2, 0.0), (-4.4, 4.4)]) * (0.92 if angle_deg % 90 else 1.0)
    t = np.deg2rad(angle_deg)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    pts = base @ R.T + 6.0
    if angle_deg == 45:      # hand-placed diagonal master: tip bottom-right, prongs and a shallow notch top-left
        pts = np.array([(10.9, 10.9), (1.0, 6.4), (3.6, 3.6), (6.4, 1.0)])
    m = raster([tuple(p) for p in pts])
    a = np.full((12, 12), -1, np.int16)
    a[m] = C["bronze_hi"]
    # shade: pixels on the side away from the upper-left light
    yy, xx = np.mgrid[0:12, 0:12]
    nrm = np.array([-np.sin(t), np.cos(t)])          # left normal of the direction
    side = (xx - 6) * nrm[0] + (yy - 6) * nrm[1]
    lightside = nrm @ np.array([-1, -1]) > 0
    dark = (side < -0.3) if lightside else (side > 0.3)
    a[m & dark] = C["bronze_lt"]
    g = m.copy()
    g[1:, :] |= m[:-1, :]; g[:-1, :] |= m[1:, :]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
    a[g & ~m] = C["ink"]
    return a


DIRS8 = [("e", 0), ("se", 45), ("s", 90), ("sw", 135), ("w", 180), ("nw", 225), ("n", 270), ("ne", 315)]


def mark(frame):
    rows = ["....k....", "...kHk...", "..kHHBk..", ".kHHHBBk.", "kHHHBBBBk", ".kHBBBBk.", "..kBBBk..", "...kBk...", "....k...."]
    pal = {"k": C["ink"], "H": C["bronze_hi"], "B": C["bronze_lt"]}
    a = np.full((9, 9), -1, np.int16)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch in pal:
                a[j, i] = pal[ch]
    if frame == 1:   # shine
        for (x, y) in ((3, 3), (4, 2), (3, 4), (2, 4)):
            a[y, x] = C["linen"]
    return a


# ---------------------------------------------------------------- H17 minimap icons 5×5
def mm_icons():
    open_ = np.full((5, 5), -1, np.int16)
    open_[:, 0] = C["bronze"]; open_[:, 4] = C["bronze"]; open_[0, :] = C["bronze_lt"]      # bronze opening 3 px
    closed = np.full((5, 5), -1, np.int16)
    closed[2, 0:5] = C["red_dk"]; closed[1, 0:5] = C["ink"]; closed[3, 0:5] = C["ink"]       # red_dk dash, ink edged
    church = np.full((5, 5), -1, np.int16)
    church[1:4, 1:4] = C["ink"]; church[2:4, 1:3] = C["linen"]                                 # linen dot 2×2, ink edge
    church[1:4, 1:4][church[1:4, 1:4] == C["ink"]] = C["ink"]
    return {"open_gate": open_, "closed_gate": closed, "church": church}


def main():
    a = frame_full()
    save(a, DLG, "ui_dlg_frame_400x88", dict(
        what="dialogue window frame, prebaked at window size 400×88 (GDD §10.4)", draw_at="window x − 1, y − 1 = (119, 221)",
        interior="transparent: engine fills the inside with night at alpha 0.92 before drawing the frame",
        inner_rect_in_image=[8, 8, 386, 74], style="ui_rus.carved_frame (quest tracker / HUD v2), notches unchanged"))
    s9 = frame_9slice()
    save(s9, DLG, "ui_dlg_frame", dict(
        what="9-slice source of the same frame", slice_px=dict(left=8, top=8, right=8, bottom=8),
        note="the GDD's 6-px border + 1-px inner ink line + 1-px overhang of the bronze corner plates = 8 px; draw the "
             "sliced frame at (x − 1, y − 1, w + 2, h + 2); edges are 48 / 24 px = whole 12-px notch periods → tile (repeat), "
             "a partial period at the far end is hidden under the corner", interior="transparent (night 0.92 by code)",
        also="ui_dlg_frame_400x88.png = this frame prebaked at 400×88"))
    save(glyph(GLYPH_V), DLG, "ui_dlg_more", dict(what="▼ 7×5 — more text / next line, at (502, 298); bob 1 px at 2 Hz by code optional"))
    save(glyph(GLYPH_SQ), DLG, "ui_dlg_end", dict(what="■ 7×5 — last line of the dialogue (same place as ▼)"))
    e, se = arrow(0), arrow(45)
    rot = lambda a, k: np.rot90(a, -k).copy()          # k quarter turns clockwise on screen
    by = {"e": e, "s": rot(e, 1), "w": rot(e, 2), "n": rot(e, 3), "se": se, "sw": rot(se, 1), "nw": rot(se, 2), "ne": rot(se, 3)}
    strip = np.concatenate([by[n] for n, _ in DIRS8], 1)
    save(strip, NAV, "ui_nav_arrow", dict(
        what="objective arrow 12×12, 8 directions (no engine rotation, scale.md §4.4)", frame_size=[12, 12], frame_count=8,
        layout="horizontal strip, left to right", frames=[n for n, _ in DIRS8],
        frame_angles_deg_screen=[d for _, d in DIRS8], pick="frame = round(atan2(dy, dx) / 45°) mod 8 (screen angle, y down, 0 = east)",
        pivot=[6, 6], usage="GDD §10.2: 14 px inside the play-field edge, alpha pulse 0.7↔1.0 at 1 Hz, 0.4 in combat; distance under it in mist"))
    ms = np.concatenate([mark(0), mark(1)], 1)
    save(ms, NAV, "ui_nav_mark", dict(what="target marker rhombus 9×9, 2 shine frames", frame_size=[9, 9], frame_count=2,
                                      layout="horizontal strip", pivot=[4, 8], fps=2,
                                      usage="40 px above the target (96 above gates, over NPC names), bob ±2 px at 1 Hz, fade 0.3 s within 3 tiles"))
    icons = mm_icons()
    st = np.concatenate([icons[k] for k in ("open_gate", "closed_gate", "church")], 1)
    save(st, NAV, "ui_minimap_icons_v113", dict(what="minimap icons 5×5 (H17)", frame_size=[5, 5], frame_count=3,
                                                 frames=["open_gate (bronze opening)", "closed_gate (red_dk dash)", "church (linen dot 2×2)"],
                                                 pivot=[2, 2], note="for gates on the N/S walls rotate by code is NOT needed: "
                                                 "use the same icon, it reads as a gap/dash in either wall; 2 px of the icon are the 3-px opening"))
    return dict(frame=a.shape, s9=s9.shape)


if __name__ == "__main__":
    print(main())

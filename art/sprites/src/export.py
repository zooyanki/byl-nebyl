"""Sheet / JSON / preview writer shared by all sprite generators."""
import os
import json
import numpy as np
from PIL import Image
import rig
import pixelkit as pk
from pixelkit import C
from fonts_ru import FONT_RU

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PAL = {tuple(int(v) for v in c) for c in pk.RGB}
REPORT = {"sheets": [], "checks": {}}
BG, GROUND, SHADOW, LABEL = C["slate_dk"], C["night"], C["night"], C["mist"]


def rgba(idx):
    a = np.where(idx >= 0, 255, 0).astype(np.uint8)
    rgb = pk.RGB[np.where(idx >= 0, idx, 0)]
    return np.dstack([rgb, a]).astype(np.uint8)


def check_png(path):
    arr = np.array(Image.open(path).convert("RGBA"))
    al = set(np.unique(arr[..., 3]).tolist())
    cols = {tuple(c) for c in arr[arr[..., 3] == 255][:, :3]}
    ok = al <= {0, 255} and cols <= PAL
    assert ok, path
    return ok


def save_sheet(frames, folder, name, meta):
    """frames: list of index arrays (H,W). Writes name.png (native strip) + name.json."""
    os.makedirs(folder, exist_ok=True)
    h, w = frames[0].shape
    strip = np.concatenate(frames, 1)
    png = os.path.join(folder, name + ".png")
    Image.fromarray(rgba(strip), "RGBA").save(png)
    check_png(png)
    meta = dict(meta)
    meta.update(image=name + ".png", frame_size=[w, h], frame_count=len(frames), layout="horizontal strip, left to right",
                palette="palette_v2 (32 colours, /workspace/game/art/ui/palette_v2.json)", alpha="0/255 only")
    with open(os.path.join(folder, name + ".json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    REPORT["sheets"].append(os.path.relpath(png, ROOT))
    REPORT["checks"][name] = dict(palette_ok=True, alpha_ok=True)
    return png


def _canvas_tile(idx, pivot, shadow_w=None, ground=True):
    h, w = idx.shape
    t = np.full((h, w), BG, np.int16)
    if ground:
        t[pivot[1], :] = GROUND
    if shadow_w:
        yy, xx = np.mgrid[0:h, 0:w]
        e = ((xx - pivot[0] + 0.5) / (shadow_w / 2.0)) ** 2 + ((yy - pivot[1]) / 3.2) ** 2 <= 1.0
        t[e] = SHADOW
    m = idx >= 0
    t[m] = idx[m]
    return t


def mirror(idx):
    return idx[:, ::-1].copy()


def label(cv, x, y, s, c=LABEL):
    cv.text(x, y, s, c, font=FONT_RU, shadow=C["ink"])


def preview(rows, row_labels, folder, name, fps, loop, pivot, shadow_w=None, title=""):
    """rows: list of frame lists (one per direction). Writes name_x3.png (all frames,
    labelled rows) and name.gif (directions side by side, animated, x3)."""
    os.makedirs(folder, exist_ok=True)
    h, w = rows[0][0].shape
    n = max(len(r) for r in rows)
    lw, th = 64, 14
    W_, H_ = lw + n * (w + 2), th + len(rows) * (h + 2)
    cv = pk.Canvas(W_, H_, fill=C["night"])
    label(cv, 3, 2, title)
    for r, (frs, lab) in enumerate(zip(rows, row_labels)):
        y = th + r * (h + 2)
        label(cv, 3, y + h // 2 - 4, lab)
        for i, fr in enumerate(frs):
            cv.a[y:y + h, lw + i * (w + 2):lw + i * (w + 2) + w] = _canvas_tile(fr, pivot, shadow_w)
    big = cv.save(os.path.join(folder, name + "_x3.png"), scale=3)
    # GIF: directions side by side
    gif_frames = []
    for i in range(n):
        strip = np.full((h + 4, len(rows) * (w + 4)), C["night"], np.int16)
        for r, frs in enumerate(rows):
            fr = frs[min(i, len(frs) - 1)]
            strip[2:2 + h, r * (w + 4) + 2:r * (w + 4) + 2 + w] = _canvas_tile(fr, pivot, shadow_w)
        im = Image.fromarray(strip.astype(np.uint8), "P")
        im.putpalette([int(v) for v in pk.RGB.reshape(-1)] + [0] * (768 - pk.RGB.size))
        im = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
        gif_frames.append(im)
    dur = [int(round(1000 / fps))] * n
    if not loop:
        dur[-1] = 700
    gif_frames[0].save(os.path.join(folder, name + ".gif"), save_all=True, append_images=gif_frames[1:],
                       duration=dur, loop=0, disposal=1, optimize=False)
    return big

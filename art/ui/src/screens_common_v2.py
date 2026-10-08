"""Shared helpers for the v2 («Гардарики») window screens."""
import numpy as np
import pixelkit as pk
import gameplay_hud_v2 as G          # activates palette v2 on import
from pixelkit import C, Canvas

W, H = G.W, G.H


def scene(shift=0, dim=1, hud=True, quest=False):
    """Gameplay frame behind an open window: world shifted horizontally so the
    hero stays centred in the free half, darkened, bottom HUD on top."""
    a, lit, L, S = G.render_world()
    if shift:
        a = np.roll(a, shift, axis=1)
    cv = Canvas(W, H); cv.a[:] = a
    if dim:
        cv.remap(0, 0, W, H, pk.DARKEN1)
        cv.dither(0, 0, W, H, C["ink"], 0.18 * dim)
    if quest:
        G.draw_quest(cv, 3, 3)
    if hud:
        G.draw_bottom(cv, S)
    return cv, S


export = G.export

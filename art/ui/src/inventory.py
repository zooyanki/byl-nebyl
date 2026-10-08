"""Inventory screen mockup: gameplay (camera shifted left, dimmed) + D2-style
inventory window on the right half. Run: python3 inventory.py"""
import numpy as np
import pixelkit as pk
from pixelkit import C, Canvas, FONT3x5, FONT5x7
import gameplay_hud as gh
import items as IT

CELL = 24


def ghost(cv, spr, x, y, w, h):
    """Empty-slot placeholder: item silhouette in dim stone."""
    idx = pk.sprite_to_index(spr)
    g = np.where(idx >= 0, C["stone_dk"], -1)
    g[idx == C["ink"]] = -1
    cv.blit(g, x + (w - spr["w"]) // 2, y + (h - spr["h"]) // 2)


def paper_doll(cv, cx, top):
    """Faint humanoid silhouette behind the equipment slots."""
    m = Canvas(cv.w, cv.h)
    m.disc(cx, top + 16, 13, 1)                                   # head
    m.rect(cx - 6, top + 26, 13, 10, 1)                           # neck
    m.poly([(cx - 40, top + 40), (cx + 40, top + 40), (cx + 30, top + 110), (cx - 30, top + 110)], 1)  # torso
    m.poly([(cx - 40, top + 40), (cx - 54, top + 44), (cx - 62, top + 120), (cx - 50, top + 122), (cx - 38, top + 70)], 1)
    m.poly([(cx + 40, top + 40), (cx + 54, top + 44), (cx + 62, top + 120), (cx + 50, top + 122), (cx + 38, top + 70)], 1)
    m.poly([(cx - 30, top + 108), (cx - 4, top + 108), (cx - 8, top + 172), (cx - 30, top + 172)], 1)
    m.poly([(cx + 30, top + 108), (cx + 4, top + 108), (cx + 8, top + 172), (cx + 30, top + 172)], 1)
    body = m.a == 1
    b = pk.bayer(cv.h, cv.w)
    cv.a[body & (b < 0.55)] = C["stone_dk"]
    cv.a[body & (b >= 0.55)] = C["shadow"]
    edge = body & ~(np.roll(body, 1, 0) & np.roll(body, -1, 0) & np.roll(body, 1, 1) & np.roll(body, -1, 1))
    cv.a[edge] = C["stone"]


def equip_slot(cv, x, y, cw, ch, spr=None, rarity=None, ghost_spr=None, label=None):
    w, h = cw * CELL, ch * CELL
    pk.slot(cv, x, y, w, h)
    if spr is not None:
        IT.draw_item(cv, spr, x + 2, y + 2, w - 4, h - 4, rarity, tint=0.3)
    elif ghost_spr is not None:
        ghost(cv, ghost_spr, x, y, w, h)
    if label:
        cv.text(x + 3, y + h - 7, label, C["stone_lt"], font=FONT3x5, shadow=C["ink"])


def backpack(cv, x, y, cols, rows, placed, hover=None):
    w, h = cols * CELL, rows * CELL
    cv.rect(x - 2, y - 2, w + 4, h + 4, C["ink"])
    cv.frame(x - 3, y - 3, w + 6, h + 6, C["iron"])
    cv.hline(x - 3, y - 3, w + 6, C["iron_lt"])
    pk.corner_studs(cv, x - 4, y - 4, w + 8, h + 8)
    for r in range(rows):
        for c in range(cols):
            cx, cy = x + c * CELL, y + r * CELL
            cv.rect(cx, cy, CELL, CELL, C["abyss"])
            cv.dither(cx + 1, cy + 1, CELL - 2, CELL - 2, C["shadow"], 0.25)
            cv.frame(cx, cy, CELL, CELL, C["ink"])
            cv.px(cx + 1, cy + 1, C["stone_dk"])
            cv.hline(cx + 1, cy + CELL - 2, CELL - 2, C["shadow"])
    for (c, r, cw, ch, spr, rar) in placed:
        px, py = x + c * CELL, y + r * CELL
        IT.draw_item(cv, spr, px + 1, py + 1, cw * CELL - 1, ch * CELL - 1, rar, tint=0.45)
    if hover:
        c, r, cw, ch = hover
        px, py = x + c * CELL, y + r * CELL
        cv.frame(px, py, cw * CELL + 1, ch * CELL + 1, C["gold_lt"])
        for (qx, qy) in ((px, py), (px + cw * CELL, py), (px, py + ch * CELL), (px + cw * CELL, py + ch * CELL)):
            cv.px(qx, qy, C["gold_hi"])


def main():
    cv = gh.compose(shift=-160, parts=("bottom",), dim=1)
    S = IT.build()
    WX, WY, WW, WH = 322, 4, 314, 310
    ix, iy, iw, ih = pk.window(cv, WX, WY, WW, WH, title="INVENTORY", seed=12)
    cx = WX + WW // 2
    paper_doll(cv, cx, 20)
    L, Cc, R = cx - 108, cx - 24, cx + 60          # column x
    RL, RR = cx - 54, cx + 30                       # ring x
    equip_slot(cv, Cc, 22, 2, 2, S["helm"], "rare")
    equip_slot(cv, RR, 34, 1, 1, S["amulet"], "magic")
    equip_slot(cv, L, 34, 2, 4, S["staff"], "unique")
    equip_slot(cv, R, 34, 2, 4, S["kite"], "magic")
    equip_slot(cv, Cc, 76, 2, 3, S["armor"], "normal")
    equip_slot(cv, L, 136, 2, 2, S["gloves"], "magic")
    equip_slot(cv, R, 136, 2, 2, S["boots"], "normal")
    equip_slot(cv, Cc, 154, 2, 1, S["belt"], "normal")
    equip_slot(cv, RL, 154, 1, 1, S["ring_ruby"], "rare")
    equip_slot(cv, RR, 154, 1, 1, None, ghost_spr=S["ring_sapph"])
    # weapon-swap tabs above the main hand (D2 I / II)
    for i, t in enumerate(("I", "II")):
        tx = L + i * 25
        cv.rect(tx, 22, 23, 10, C["ink"])
        cv.rect(tx + 1, 23, 21, 8, C["stone"] if i == 0 else C["shadow"])
        cv.hline(tx + 1, 23, 21, C["gold_lt"] if i == 0 else C["stone_dk"])
        cv.text_c(tx + 12, 24, t, C["gold_hi"] if i == 0 else C["stone_lt"], font=FONT3x5, shadow=C["ink"])
    # character name/level plaque under the helm area (left/right of helm)
    cv.text(L, 23 - 0, "", C["bone"])

    pot = IT.potion_fn
    placed = [
        (0, 0, 1, 3, S["sword"], "unique"),
        (1, 0, 2, 3, S["armor"], "normal"),
        (3, 0, 2, 2, S["buckler"], "magic"),
        (5, 0, 1, 1, pot("health"), None), (5, 1, 1, 1, pot("health"), None),
        (6, 0, 1, 1, pot("mana"), None), (6, 1, 1, 1, pot("mana"), None),
        (7, 0, 1, 1, pot("rejuv"), None),
        (8, 0, 1, 1, S["gem_ruby"], None), (9, 0, 1, 1, S["gem_sapphire"], None),
        (8, 1, 1, 1, S["gem_amethyst"], None), (9, 1, 1, 1, S["gem_topaz"], None),
        (3, 2, 1, 1, S["ring_sapph"], "magic"),
        (4, 2, 1, 1, S["scroll"], None), (4, 3, 1, 1, S["scroll"], None),
        (5, 2, 1, 2, S["tome"], "rare"),
        (6, 2, 1, 1, S["charm"], "magic"),
        (8, 2, 2, 2, S["gloves"], "rare"),
    ]
    BX, BY = cx - 5 * CELL, 196
    backpack(cv, BX, BY, 10, 4, placed, hover=(0, 0, 1, 3))
    # gold + capacity row
    gy = 296
    pk.inset(cv, BX - 3, gy - 2, 96, 13)
    pk.coin_icon(cv, BX, gy)
    cv.text(BX + 11, gy + 1, "GOLD", C["bone"], shadow=C["ink"])
    cv.text_r(BX + 90, gy + 1, "1284", C["gold_hi"], shadow=C["ink"])
    cv.text_r(BX + 243, gy + 2, "SPACE 22/40", C["stone_lt"], font=FONT3x5, shadow=C["ink"])
    # tooltip for hovered unique sword
    lines = [
        ("THE ASHEN OATH", C["gold_lt"]),
        ("LONG SWORD", C["gold_lt"]),
        ("ONE-HAND DAMAGE: 14 TO 33", C["parchment"]),
        ("DURABILITY: 38 OF 44", C["parchment"]),
        ("REQUIRED STRENGTH: 55", C["red_lt"]),
        ("REQUIRED LEVEL: 12", C["parchment"]),
        ("+65% ENHANCED DAMAGE", C["blue_lt"]),
        ("ADDS 6-14 FIRE DAMAGE", C["blue_lt"]),
        ("+2 TO FIRE SKILLS", C["blue_lt"]),
        ("+20% FIRE RESISTANCE", C["blue_lt"]),
        ("SOCKETED (1)", C["blue_lt"]),
    ]
    tx, ty, tw, th = pk.tooltip(cv, BX - 8, 112, lines, anchor="tr")
    # divider under the name block
    cv.hline(tx + 12, ty + 5 + 2 * 9 - 1, tw - 24, C["gold_dk"])
    pk.cursor(cv, BX + 14, BY + 34)
    gh.export(cv, "mockup_inventory")


if __name__ == "__main__":
    main()

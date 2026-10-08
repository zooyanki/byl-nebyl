import sys
sys.path.insert(0, "/workspace/game/art/ui/src")
import gameplay_hud_v2 as G
import pixelkit as pk, numpy as np
import teaser_sprites as TS
from pixelkit import C
sp = [TS.hero_pose(p) for p in ("swing", "guard", "cast", "over", "idle")]
sp += [TS.upyr_lunge(), TS.upyr_shamble(), TS.upyr_emerge(), TS.volkolak_leap(1.07), G.SR.volkolak(), TS.wolfdlak_kneel(),
       TS.prince_sword(), TS.staff(), TS.pelt()]
W = sum(s["w"] + 4 for s in sp) + 4; H = max(s["h"] for s in sp) + 8
cv = pk.Canvas(W, H, C["slate"])
x = 4
for s in sp:
    cv.blit(pk.sprite_to_index(s), x, 4)
    rows = np.where(s["mask"].any(1))[0]
    print(s["w"], s["h"], "visible", rows.max() - rows.min() + 1, "bottom", rows.max(), "pivot", s.get("pivot"))
    x += s["w"] + 4
cv.save(sys.argv[1], scale=3)

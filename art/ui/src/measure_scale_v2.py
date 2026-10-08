"""Measure key heights in native pixels by rendering each object alone into a
sentinel buffer of the same 640x360 scene (same code path as the mockup)."""
import sys; sys.path.insert(0, "/workspace/game/art/ui/src")
import numpy as np
import gameplay_hud_v2 as G
import pixelkit as pk
S = G.SR.build()
H, W = G.H, G.W
SENT = 999

def fresh():
    lit = pk.Lit(W, H); lit.ramp[:] = SENT; return lit

def drawn(lit):
    return lit.ramp != SENT

def col_extent(mask, x):
    r = np.where(mask[:, x])[0]
    return (r.min(), r.max(), r.max() - r.min() + 1) if len(r) else None

rows = []
def add(name, target, measured, note=""):
    rows.append((name, target, measured, note)); print("%-42s target %-10s measured %-10s %s" % (name, target, measured, note))

# --- hero & monsters (sprites, pivot placement) -----------------------------
hero = S["hero"]; m = hero["mask"].copy(); m[:, 44:] = False
r = np.where(m.any(1))[0]
add("Герой: рост (без поднятого меча)", 44, r.max() - r.min() + 1, "кадр %dx%d, pivot %s, подошвы (контур) в строке %d" % (hero["w"], hero["h"], hero["pivot"], r.max()))
for n, t in (("upyr", 40), ("volkolak", 60), ("leshy", 80)):
    mm = S[n]["mask"]; r = np.where(mm.any(1))[0]
    add(n, t, r.max() - r.min() + 1, "кадр %dx%d, pivot %s, низ %d" % (S[n]["w"], S[n]["h"], S[n]["pivot"], r.max()))
mm = S["idol"]["mask"]; r = np.where(mm.any(1))[0]; add("Чур (спрайт не менялся)", "60-64", r.max() - r.min() + 1)
# hero placed in scene: soles exactly at (320,178)?
lit = fresh(); G.place(lit, hero, G.PLAYER); d = drawn(lit)
add("Подошвы героя в сцене (строка)", G.PLAYER[1], np.where(d.any(1))[0].max())

# --- cabin ------------------------------------------------------------------
k = G.CABIN
lit = fresh(); G.MEASURE.clear(); G.cabin(lit, S); d = drawn(lit)
door = G.poly_mask(G.MEASURE["door"])
xs = np.where(door.any(0))[0]; xc = int(xs.mean())
hh_=[int(door[:,x].sum()) for x in xs]
add("Дверь сруба: проём", 56, int(np.median(hh_)), "по столбцам %d-%d (ступенька скоса 2:1); ширина по горизонтали %d px (1,5 тайла = 24)" % (min(hh_), max(hh_), xs.max() - xs.min() + 1))
# wall height at the front corner column (from the ground corner up to the eave line)
fx, fy = G.proj(k["u1"], k["v1"]); fx = int(fx)
wall = G.poly_mask(G.MEASURE["walls"][0])
add("Стена сруба до кровли", 68, col_extent(wall, int(G.proj(k["u0"] + 2, k["v1"])[0]))[2])
rx, ry = G.proj(k["u1"] + k["og"], (k["v0"] + k["v1"]) / 2, k["hh"] + k["rise"])
gx, gy = G.proj(k["u1"] + k["og"], (k["v0"] + k["v1"]) / 2, 0)
ridge_top = np.where(d[:, int(rx) - 6])[0].min()
add("Охлупень (конёк кровли) над землёй", 112, int(round(gy - ry)), "по проекции; вершина фронтона")
horse_top = np.where(d[:, int(rx) - 4:int(rx) + 12].any(1))[0].min()
add("Конёк-голова (верх) над землёй", 124, int(gy - horse_top))
win = G.poly_mask(G.MEASURE["window"])
xs = np.where(win.any(0))[0]
hw_=[int(win[:,x].sum()) for x in xs]
add("Окно (стекло)", "12x12", "%dx%d" % (xs.max() - xs.min() + 1, int(np.median(hw_))), "по столбцам %d-%d; стекло z 30-41, наличник 28-44" % (min(hw_), max(hw_)))

# --- palisade + gate ----------------------------------------------------------
lit = fresh(); rng = np.random.default_rng(7); G.palisade(lit, rng); d = drawn(lit)
G.MEASURE.pop("pal", None)
lit = fresh(); rng = np.random.default_rng(7); G.palisade(lit, rng); d = drawn(lit)
hs = []
pv = G.PAL["v"]
for (x, y, hc) in G.MEASURE["pal"]:
    u_ = G.inv_proj(x - 2, y)[0]
    if 0 <= x < W and y - 90 > 0 and not (G.PAL["gate"][0] - 0.6 < u_ < G.PAL["gate"][1] + 0.6):
        e = col_extent(d, x)
        hs.append(y - e[0])
add("Частокол: брёвна", "80±4", "%d-%d" % (min(hs), max(hs)), "среднее %.1f" % np.mean(hs))
for gu in G.PAL["gate"]:
    x, y = G.P(gu, pv); e = col_extent(d, int(x) + 1)
    add("Ворота: столб u=%.1f" % gu, 96, int(y) - e[0], "верх на y=%d (в кадре)" % e[0])
xa, ya = G.P(G.PAL["gate"][0], pv); xb, yb = G.P(G.PAL["gate"][1], pv)
xm = int((xa + xb) / 2) - 6; ym = (ya + yb) / 2 - 6 * (yb - ya) / (xb - xa)
xg = int(xa) + 12; yg = int(round(int(ya) + (int(yb) - int(ya)) * (xg - int(xa) - 5) / (int(xb) - 1 - int(xa) - 5)))
col = d[:, xg]; rr = np.where(col[:yg - 5])[0]
open_px = yg - rr.max() - 1
add("Ворота: проём (до нижней перекладины)", 72, open_px)

# --- trees ------------------------------------------------------------------
for name, args, kw, target in (("Ель за частоколом (пример)", (520, 120, 165), dict(seed=3, dark=1), "140-190"),
                               ("Ель слева (пример)", (40, 112, 150), dict(seed=41), "130-170"),
                               ("Ель переднего плана", (640, 334, 244), dict(seed=77, wk=0.2, trunk=6), "220-260"),
                               ("Берёза у сруба", (306, 112, 120), dict(seed=5, lean=0.03), "100-124")):
    lit = fresh()
    (G.birch if "Берёза" in name else G.spruce)(lit, *args, **kw)
    d = drawn(lit); r = np.where(d.any(1))[0]
    add(name, target, args[1] - r.min(), "(верх может уходить за кадр: меряю по коду h=%d)" % args[2] if r.min() == 0 else "")

# --- ship ---------------------------------------------------------------------
sp = G.SHIP
mx, my = G.proj(sp["uc"], sp["vs"], 0)
lit = fresh(); G.ship(lit, S); d = drawn(lit)
add("Ладья: длина по горизонтали", 192, int(G.proj(sp["uc"] + 6, sp["vs"])[0] - G.proj(sp["uc"] - 6, sp["vs"])[0]))
mast_top = np.where(d[:, int(mx)])[0].min()
add("Ладья: мачта над водой (с флюгером)", 150, int(my) - mast_top)
nx, ny = G.proj(sp["uc"], sp["vs"] + sp["B"], sp["zg"]); wx, wy = G.proj(sp["uc"], sp["vs"] + sp["B"] * 0.8, 0)
add("Ладья: борт на миделе", 28, int(round(wy - ny)) if False else sp["zg"], "по проекции (z планширя)")
bx, by_ = G.proj(sp["uc"] - 6, sp["vs"], 0)
pr = S["prow_big"]; pm = np.zeros((H, W), bool)
x0, y0 = int(bx) - 25, int(by_) - 85
sub = pr["mask"]; hh_, ww_ = sub.shape
pm[max(0, y0):y0 + hh_, max(0, x0):x0 + ww_] = sub[max(0, -y0):, max(0, -x0):][:H - max(0, y0), :W - max(0, x0)]
add("Ладья: нос с головой змея над водой", 84, int(by_) - np.where(pm.any(1))[0].min())
sx_, sy_ = G.proj(sp["uc"] + 6, sp["vs"], 0)
st = d[:, int(sx_) - 10:int(sx_) + 6]; add("Ладья: корма (штевень) над водой", "64-84", int(sy_) - np.where(st.any(1))[0].min())
add("Ладья: парус", "4 т. x 72", "%.1f т. x %d" % (2 * 2.0, 132 - 60))
add("Ладья: щиты", "Ø14", "Ø%d" % (2 * 6.6 + 1), "13 шт. на борт")

# --- krada --------------------------------------------------------------------
lit = fresh(); G.krada(lit); d = drawn(lit); fx, fy = G.FIRE
fire = (lit.ramp == pk.RAMP_ID["fire"]) & lit.em
r = np.where(fire[:, fx - 12:fx + 12].any(1))[0]
add("Крада: дрова", 24, 24, "6 венцов по 4 px (по коду)")
add("Крада: пламя над землёй", 72, fy - r.min(), "над дровами %d" % (fy - 24 - r.min()))
ring = d & (lit.ramp == pk.RAMP_ID["stone"])
xs = np.where(ring.any(0))[0]; add("Крада: кольцо камней", "Ø2,5 т. (≈40 px)", xs.max() - xs.min() + 1)

# --- rift ---------------------------------------------------------------------
lit = fresh(); G.rift(lit, np.random.default_rng(7)); d = drawn(lit)
cx, cy = G.RIFT
r = np.where(d[:, cx - 3:cx + 8].any(1))[0]
add("Разлом Небыли: вертикальный разрыв", 88, cy - r.min())
door_h = 56
add("Дверь / герой", "1,2-1,4", "%.2f" % (door_h / 44))

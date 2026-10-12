"""GDD v1.14 §12.1.8 — заказ «щит» (H21–H23) одной командой: python3 make_v114_shield.py
Старые PNG не трогает: пишет только hero/hero_block_*, fx_block_sparks/, hero/review/, art/ui/hud/ic_block*."""
import os, subprocess, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
for s in ("hero_block.py", "fx_block_sparks.py", "hero_block_scene.py"):
    subprocess.check_call([sys.executable, os.path.join(HERE, s)], cwd=HERE)
subprocess.check_call([sys.executable, os.path.join(HERE, "..", "..", "ui", "src", "ic_block.py")],
                      cwd=os.path.join(HERE, "..", "..", "ui", "src"))
sys.path.insert(0, HERE)
import export as X
pngs = glob.glob(os.path.join(X.ROOT, "hero", "hero_block_*.png")) + glob.glob(os.path.join(X.ROOT, "fx_block_sparks", "*.png")) \
    + [os.path.join(X.ROOT, "..", "ui", "hud", "ic_block.png")]
for p in pngs:
    X.check_png(p)
print("palette_v2 + alpha 0/255 ok:", len(pngs), "png")

import sys, json, numpy as np
sys.argv=['x']
import village_scene as V
P = V.ZONE["palisade"]
cells = {a: V.palisade_cell(a) for a in ("x","y")}
def gap(x,y): return any(x>=a and x<a+w and y>=b and y<b+h for a,b,w,h in P["gaps"])
gates=set()
for side,(axis,sin,(gx,gy)) in V.G.GATES.items():
    for k in range(4): gates.add((gx,gy+k) if axis=="y" else (gx+k,gy))
pal=[]
for y in range(P["y0"],P["y1"]+1):
    for x in (P["x0"],P["x1"]):
        if not gap(x,y) and (x,y) not in gates: pal.append((x,y,"y"))
for x in range(P["x0"],P["x1"]+1):
    for y in (P["y0"],P["y1"]):
        if not gap(x,y) and (x,y) not in gates: pal.append((x,y,"x"))
def mask(idx, ox, oy):
    ys,xs=np.nonzero(idx>=0); return set(zip((xs+ox).tolist(),(ys+oy).tolist()))
pm={}
for x,y,a in pal:
    idx,pc=cells[a]; sx,sy=V.S2(x,y); pm[(x,y)]=mask(idx,int(sx-pc[0]),int(sy-pc[1]))
bad={"front":[],"centre":[]}
for pid,sheet,x0,y0,door in V.PLAN:
    fr,m=V.load(sheet); A,B=m["footprint_tiles"]; df=m.get("door_frames"); fi=df.get(door,0) if isinstance(df,dict) else 0
    pc=m["proto_corner_px"]; sx,sy=V.S2(x0,y0); bm=mask(fr[fi],int(sx-pc[0]),int(sy-pc[1]))
    for (x,y),msk in pm.items():
        ov=len(bm & msk)
        if not ov: continue
        # truth: cell in front if it lies on +x/+y side of the footprint
        cell_front = x >= x0+A or y >= y0+B
        cell_behind = x+1 <= x0 or y+1 <= y0
        for rule,(kb,kp) in {"front":((x0+A)+(y0+B), x+y+2), "centre":(x0+A/2+y0+B/2, x+y+1.01)}.items():
            ok = (kp>kb) if cell_front else ((kp<kb) if cell_behind else None)
            if ok is False or (kp==kb): bad[rule].append((pid,(x,y),ov,kb,kp,"cell in front" if cell_front else "cell behind"))
for r,v in bad.items():
    print(r, len(v)); [print("  ",i) for i in v]

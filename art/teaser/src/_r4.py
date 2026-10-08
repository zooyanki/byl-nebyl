import sys, json
from teaser_scenes import *
a0, _, _ = scene4(False)
a1, _, _ = scene4(True)
for n, a in (("s", a0), ("e", a1)):
    cv = Canvas(W, H); cv.a[:] = a; cv.save("/tmp/t4%s_%s.png" % (n, sys.argv[1]), scale=2)
d = a0 != a1
ys, xs = np.where(d)
print("diff px", d.sum(), "bbox", xs.min(), ys.min(), xs.max(), ys.max())
print(json.dumps(MEAS, default=lambda o: int(o) if isinstance(o, np.integer) else str(o)))

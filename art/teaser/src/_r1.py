import sys
from teaser_scenes import *
name = sys.argv[1]
a, lit, L = {"1": scene1, "2": scene2, "3": scene3}[name]()
cv = Canvas(W, H); cv.a[:] = a
cv.save("/tmp/t%s_%s.png" % (name, sys.argv[2]), scale=2)
import json; print(json.dumps({k: (v if not isinstance(v, np.generic) else int(v)) for k, v in MEAS.items()}, default=lambda o: int(o) if isinstance(o, np.integer) else str(o)))

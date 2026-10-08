"""Черноярец-поджигатель (GDD §12.1.2 P0, scale.md §2): recolour of the
топорщик + torch in the LEFT hand. 64x64, pivot (32,56), body 46,
raised torch with flame up to 56. Views se/ne (+ mirrors sw/nw)."""
import math
import human as Hm
import axeman as AX

# rest grip: torch held out in front (left hand), axe resting on the right shoulder
TORCH_REST = dict(hf={"se": (5.0, 3.0, -26.0), "ne": (8.0, 0.5, -27.0)}, torch_ang={"se": -76, "ne": -84})
AXE_REST = dict(hn={"se": (-1.0, 5.0, -24.0), "ne": (1.0, 6.0, -23.0)}, axe_ang={"se": -108, "ne": 98}, axe_edge={"se": -1, "ne": -1})


def P(**kw):
    d = dict(TORCH_REST); d.update(AXE_REST); d.update(kw)
    return Hm.pose(**d)


def idle(i):
    b = [0, 0, 1, 1][i]
    return P(pel=(0.0, -19.0 + b), hn={"se": (-1.0, 5.0, -24.0 + b), "ne": (1.0, 6.0, -23.0 + b)},
             hf={"se": (5.0, 3.0, -26.0 + b * 0.5), "ne": (8.0, 0.5, -27.0 + b * 0.5)}, sway=[0, 0.3, 0.3, 0][i])


def walk(i):
    t = i / 8.0 * 2 * math.pi
    A = 3.4
    sn = math.sin(t)
    return P(pel=(0.6, -19.0 + round(abs(sn) * 0.9)), tor=4.0,
             fn=(A * sn, 2.2), ff=(-A * sn, 2.2),
             lift_n=max(0.0, 1.8 * math.cos(t)), lift_f=max(0.0, -1.8 * math.cos(t)),
             hn={"se": (-1.0 - 0.6 * sn, 5.0, -24.0 + round(abs(sn) * 0.9)), "ne": (1.0 - 1.2 * sn, 6.0, -23.0 + round(abs(sn) * 0.9))},
             hf={"se": (5.0 + 0.8 * sn, 3.0, -26.0 + round(abs(sn) * 0.9)), "ne": (8.0 + 0.8 * sn, 0.5, -27.0 + round(abs(sn) * 0.9))},
             sway=-0.7 * sn, flame_lean=-0.8)


THROW = [
    dict(pel=(-1.0, -18.5), tor=-8.0, hf=(-6.0, 2.0, -31.5), torch_ang=-120, flame_lean=0.8),
    dict(pel=(-0.6, -18.5), tor=-5.0, hf=(-3.0, 1.0, -34.0), torch_ang=-100, flame_lean=0.6),
    dict(pel=(1.4, -18.6), tor=9.0, hf=(9.0, 1.0, -31.0), torch_ang=-22, flame_lean=-1.2, fn=(2.6, 2.4), lift_f=0.6),
    dict(pel=(1.8, -18.4), tor=11.0, hf=(11.0, 0.0, -24.0), torch=None, fn=(2.6, 2.4)),
    dict(pel=(0.8, -19.0), tor=4.0, hf=(6.0, 3.0, -22.0), torch=None, fn=(1.2, 2.4)),
]
THROW_RELEASE = 3          # first frame without the torch: spawn the flight effect here


def throw(i):
    return P(**THROW[i])


def _smear(pts):
    return [(pts[k], pts[k + 1], "I") for k in range(len(pts) - 1)]


STRIKE = [
    dict(pel=(-0.8, -18.6), tor=-6.0, hn=(-5.0, 3.0, -34.0), axe_ang={"se": -150, "ne": -130}, axe_edge=-1, near_behind=True),
    dict(pel=(-1.0, -18.4), tor=-8.0, hn=(-3.0, 2.0, -38.0), axe_ang={"se": -120, "ne": -110}, axe_edge=-1, near_behind=True),
    dict(pel=(0.6, -18.6), tor=3.0, hn=(4.0, 1.0, -35.0), axe_ang=-45, axe_edge=1),
    dict(pel=(1.8, -18.2), tor=10.0, hn=(10.0, 0.0, -27.0), axe_ang=15, axe_edge=1, fn=(2.8, 2.4), mouth=True, smear_from=-100),
    dict(pel=(1.6, -18.2), tor=8.0, hn=(8.0, -1.0, -19.0), axe_ang=70, axe_edge=1, fn=(2.8, 2.4), smear_from=-10),
    dict(pel=(0.6, -19.0), tor=3.0, hn=(2.0, 4.0, -21.0), axe_ang={"se": 120, "ne": 100}, axe_edge=1, fn=(1.2, 2.4)),
]


def strike(i):
    d = dict(hf={"se": (4.0, 4.0, -22.0), "ne": (7.0, 1.0, -23.0)}, torch_ang=-70)
    d.update(STRIKE[i])
    return P(**d)


HURT = [
    dict(pel=(-2.0, -18.6), tor=-12.0, head=-10.0, hn=(-3.0, 6.0, -26.0), axe_ang={"se": -125, "ne": -95},
         hf=(1.0, 5.0, -30.0), torch_ang=-60, mouth=True, eyes="closed"),
    dict(pel=(-1.0, -18.8), tor=-6.0, head=-4.0, hn=(-2.0, 5.5, -25.0), hf=(2.0, 4.0, -28.0), torch_ang=-72),
]


def hurt(i):
    return P(**HURT[i])


def death(i):
    AXE_G = ("ground", (-27.0, 3.5), -4.0)
    lie = dict(axe=AXE_G, eyes="closed", fn_abs=(13.0, 3.0), ff_abs=(10.0, -2.0))
    fr = [
        dict(pel=(-2.0, -18.5), tor=-14.0, head=-12.0, hn=(-4.0, 7.0, -27.0), axe_ang={"se": -150, "ne": -110},
             hf=(3.0, 5.0, -32.0), torch_ang=-55, mouth=True, eyes="closed"),
        dict(pel=(-3.0, -15.0), tor=-20.0, head=-12.0, hn=(-5.0, 7.0, -22.0), axe_ang={"se": -170, "ne": -140},
             hf=(2.0, 6.0, -26.0), torch_ang=-40, mouth=True, eyes="closed"),
        dict(pel=(-3.5, -11.0), tor=-32.0, head=-10.0, hn=(-8.0, 6.0, -14.0), axe=AXE_G,
             hf=(3.0, 6.0, -16.0), torch=("ground", (12.0, 3.0), 14, 0.9), eyes="closed", mouth=True),
        dict(lie, pel=(-3.0, -8.5), tor=-44.0, head=-8.0, hn=(-14.0, -10.0), hf=(-4.0, -20.0),
             torch=("ground", (12.0, 3.0), 14, 0.8), fn_abs=(8.0, 2.0), ff_abs=(5.0, -1.0)),
        dict(lie, pel=(-2.5, -6.5), tor=-58.0, head=-4.0, hn=(-17.0, -4.0), hf=(-19.0, -17.0),
             torch=("ground", (12.0, 3.0), 14, 0.7)),
        dict(lie, pel=(-2.0, -5.5), tor=-64.0, head=-2.0, hn=(-16.0, -2.0), hf=(-22.0, -14.0),
             torch=("ground", (12.0, 3.0), 14, 0.6)),
        dict(lie, pel=(-2.0, -5.0), tor=-63.0, head=0.0, hn=(-16.0, -1.5), hf=(-22.0, -13.0),
             torch=("ground", (12.0, 3.0), 14, 0.35)),
        dict(lie, pel=(-2.0, -5.0), tor=-63.0, head=0.0, hn=(-16.0, -1.5), hf=(-22.0, -13.0),
             torch=("ground", (12.0, 3.0), 14, 0.0)),
    ][i]
    return P(**fr)


ANIMS = [  # name, frames, fps, loop, pose fn
    ("idle", 4, 5, True, idle),
    ("walk", 8, 10, True, walk),
    ("torch_throw", 5, 10, False, throw),
    ("axe_strike", 6, 12, False, strike),
    ("hurt", 2, 8, False, hurt),
    ("death", 8, 10, False, death),
]


def frame(anim_fn, i, view, scheme="arsonist", with_torch=None):
    return AX.draw(anim_fn(i), view, scheme, phase=i % 6, with_torch=with_torch)

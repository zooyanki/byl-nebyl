"""Декор (GDD v1.11, Залесье — тупик Огнеи): prop_stump_burnt (горелый пень, 3 варианта в одной ленте).
Раскладка и превью сцены — art/layout/ (tools/build_layout.py, check_layout.py, preview_ingame.py).
Called from make_all.py (run(MEAS)); can also run alone: python3 make_decor.py"""
import os
import export as X
import stump as ST

ROOT = X.ROOT


def run(MEAS=None):
    fr = ST.frames()
    out = os.path.join(ROOT, "prop_stump_burnt")
    X.save_sheet(fr, out, "prop_stump_burnt", {
        "prop": "Горелый пень (GDD v1.11 Залесье: края поляны Огнеи r 9 — горелые пни и пепел вместо елей)",
        "pivot": list(ST.PIVOT), "fps": 0, "loop": False,
        "variants": {"0": "срез (низкий, 10 px над опорой)", "1": "обломанный ствол (18 px)", "2": "широкий с корнями (8 px)"},
        "draw": "static prop: frame = variant (data maraDen.stumps[i][2]); pivot on the tile centre of the prop (x+0.5, y+0.5); "
                "no footprint (fp 0x0), depth like 'ash'; flip horizontally for more variety if wanted",
        "visible_height_px": [10, 18, 8]})
    X.preview([fr], ["варианты 0·1·2"], os.path.join(out, "preview"), "prop_stump_burnt", 1, True, ST.PIVOT,
              title="Горелый пень · prop_stump_burnt")
    if MEAS is not None:
        MEAS["prop_stump_burnt"] = {"frame": [fr[0].shape[1], fr[0].shape[0]], "pivot": list(ST.PIVOT)}
    return out


if __name__ == "__main__":
    print(run())

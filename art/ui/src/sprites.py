"""Material-letter sprite maps for the gameplay mockup (auto-shaded + outlined
by pixelkit.make_sprite). Letters = materials, '.' = transparent."""
from pixelkit import make_sprite

# letter -> (ramp, base level, autoshade, emissive)
MAT = {
    "H": ("iron", 4, True, False),    # helm / bright steel
    "A": ("iron", 3, True, False),    # armour
    "a": ("iron", 2, False, False),   # armour shadow
    "G": ("gold", 4, True, False),    # gold trim
    "C": ("red", 4, True, False),     # cloth / cape
    "c": ("red", 3, False, False),    # cloth shadow
    "L": ("earth", 3, True, False),   # leather
    "D": ("stone", 1, False, False),  # dark cavity
    "S": ("wood", 3, True, False),    # wood
    "O": ("fire", 4, True, True),     # glowing orb / flame
    "B": ("bone", 5, True, False),    # bone
    "b": ("bone", 4, False, False),   # bone shadow
    "E": ("fire", 2, False, True),    # glowing red eye
    "R": ("red", 4, True, False),     # demon skin
    "r": ("red", 3, False, False),    # demon skin shadow
    "T": ("iron", 4, True, False),    # blade
    "Y": ("gold", 5, False, False),   # gold highlight
    "M": ("stone", 4, True, False),   # stone
    "m": ("stone", 3, False, False),  # stone shadow
    "U": ("blue", 4, True, True),     # glowing blue
    "W": ("stone", 7, False, False),  # brightest
}

PLAYER = [
    "..........GG..........",
    ".........HGGH.....OO..",
    "........HHHHHH...OOOO.",
    ".......HHHHHHHa..OOOO.",
    ".......HHHHHHHa...OO..",
    ".......DDDDDDDD...SS..",
    ".......HHDHHDHa...SS..",
    "........HHHHHa....SS..",
    ".....AAAAGGGGAAAA.SS..",
    "....AAHAAAGGAAAHAASS..",
    "...AAHHAAAAAAAAHHAAS..",
    "...AAAACAAAAAAACAALLL.",
    "...AAACCAAAAAAACCALLL.",
    "...aAACCAAAAAAACCaSS..",
    "...aAACCAAAAAAAaCCSS..",
    "...LLCCCGGGYGGGaCCSS..",
    "...LLCCCAAGYGAaaCCSS..",
    "....CCCCAAAAAAaaCCSS..",
    "....CCCCAAAAAaaaCCSS..",
    "...CCCCcLLLLLLLcCCSS..",
    "...CCCccLLLcLLLcCCSS..",
    "..CCCCcLLLLcLLLLcCSS..",
    "..CCCcccLLLccLLLcCSS..",
    "..CCCcc.LLLccLLLcCCS..",
    "..CCcc..LLLc.cLLLcCS..",
    ".CCCcc..LLL...LLLcCS..",
    ".CCcc...AAA...AAAcCS..",
    ".CCc....AAA...AAA.CS..",
    ".Cc.....AAA...AAA..S..",
    ".......AAAA...AAAA.S..",
    "......AAAAA...AAAAAS..",
    "...................S..",
]

SKELETON = [
    "......BBBB........",
    ".....BBBBBB.......",
    "....BBBBBBBb......",
    "....BDEBBDEb......",
    "....BBBDBBBb......",
    ".....BWBWBb.......",
    "......bbbb........",
    "...BB..BB..BB.....",
    "..BB.BBBBBB.BB....",
    "..B..B.BB.B..B....",
    "..B..BBBBBB..B....",
    "..B..B.BB.B..BB...",
    ".BB...BBBB....B...",
    ".B.....BB.....BT..",
    "LLL....BB....TTT..",
    "LLLL..BBBB..TT.B..",
    "LLLL.BB..BBTT.....",
    "LLL..B....TT......",
    ".L...B...TTB......",
    ".....B..TT.B......",
    ".....B.GG..B......",
    ".....BGG...B......",
    "....BBG...BB......",
    "....B......B......",
    "...BB......BB.....",
]

FALLEN = [
    ".R.......R....",
    ".RR.....RR....",
    "..RRRRRRR.....",
    "..RREErEER....",
    "..RRRRRRRR....",
    "...RBrBrR.....",
    "....RRRR....T.",
    "..RRRRRRRR.TT.",
    ".RR.RRRR.RRS..",
    ".R..RRRR..SR..",
    ".R..LLLL.S....",
    "....LLLLS.....",
    "....RR.SR.....",
    "...RR.S.RR....",
    "...R.S...R....",
    "..RR.....RR...",
]

GARGOYLE = [
    "BB..........................BB",
    ".BB.........MMMMMM.........BB.",
    ".BBB......MMMMMMMMMM......BBB.",
    "..BBB....MMMMMMMMMMMM....BBB..",
    "...BBB.MMMMMMMMMMMMMMMM.BBB...",
    "....BBMMmDDDMMMMMMDDDmMMBB....",
    ".....MMmDEEDMMmmMMDEEDmMM.....",
    "MM...MMMmDDMMMmmMMMDDmMMM...MM",
    "MMMM.MMMMMMMMMmmMMMMMMMMM.MMMM",
    ".MMMMMMMMMMMMDDDDMMMMMMMMMMMM.",
    "..MMMMMMMMMWDWDDWDWMMMMMMMMM..",
    "...mmMMM.MMDDDDDDDDMM.MMMmm...",
    "....mmm...MMWDWWDWMM...mmm....",
    "...........MMMMMMMM...........",
    "............mmmmmm............",
]

TOMBSTONE = [
    "..MMMM..",
    ".MMMMMM.",
    "MMMMMMMM",
    "MMmMMmMM",
    "MMMmmMMM",
    "MMmMMmMM",
    "MMMMMMMm",
    "MMMMMMMm",
    "mmmmmmmm",
]

CROSS = [
    "..MM..",
    "..MM..",
    "MMMMMM",
    "mmMMmm",
    "..MM..",
    "..MM..",
    "..Mm..",
    "..Mm..",
    ".mmmm.",
]

GOLDPILE = [
    ".....GY.......",
    "...GGYGG.GY...",
    "..GYGGGGGYGG..",
    ".GGGGYGGGGGYG.",
    "GGYGGGGGYGGGGG",
]

SWORD_GROUND = [
    "...........TT",
    ".........TTT.",
    ".......TTT...",
    ".....TTT.....",
    "..GTTT.......",
    "..GG.........",
    ".LG.G........",
    "L............",
]

BONES = [
    "B.....B.",
    ".BBBBBB.",
    "B.....B.",
]

SKULL = [
    ".BBB.",
    "BDBDB",
    ".BBb.",
]

BRAZIER = [
    "GAAAAAAAAAG",
    ".AAAAAAAAA.",
    "..aAAAAAa..",
    "....aAa....",
    "....aAa....",
    "....aAa....",
    "...a.A.a...",
    "..a..A..a..",
    ".a...A...a.",
    "a....A....a",
]

LOGS = [
    "SS........SS",
    ".SSSS..SSSS.",
    "...SSSSSS...",
    ".SSSS..SSSS.",
    "SS........SS",
]


def build(mat=MAT):
    return {name: make_sprite(rows, mat) for name, rows in {
        "player": PLAYER, "skeleton": SKELETON, "fallen": FALLEN, "gargoyle": GARGOYLE,
        "tombstone": TOMBSTONE, "cross": CROSS, "goldpile": GOLDPILE, "sword": SWORD_GROUND,
        "bones": BONES, "skull": SKULL, "logs": LOGS, "brazier": BRAZIER}.items()}

# UI mockup generators (pixel art, native 640x360 -> x3 = 1920x1080)

    python3 gameplay_hud.py      # writes ../mockup_gameplay_hud_*.png, ../palette.png/.json

- pixelkit.py — reusable core: 32-colour PALETTE + material RAMPS, Canvas (palette-index
  drawing: rect/line/disc/poly/dither/remap/stamp/text), bitmap fonts FONT5x7 / FONT3x5,
  Lit (world buffers + banded/dithered lighting), make_sprite (material letters ->
  auto-shaded, outlined sprite), widgets (stone_fill, bevel, gold_trim, slot, bar, orb,
  label_box, menu_button, key_label), icons (SKILL_ICONS, MENU_ICONS, potion).
- sprites.py — material-letter sprite maps (player, skeleton, fallen, gargoyle, props).
- gameplay_hud.py — scene (iso ground, ruins, lights) + HUD layout; each draw_* takes
  a Canvas and coordinates so it can be reused for inventory / character / map / menu.
Rule: draw only palette indices; export with Canvas.save(path, scale=3) (NEAREST).

## v2 — theme «Гардарики» (gameplay screen only)

    python3 gameplay_hud_v2.py   # -> ../mockup_gameplay_hud_v2_{native,1920x1080}.png, ../palette_v2.{png,json}

| Module | Contents |
|---|---|
| `theme_rus.py` | 32-colour palette v2 (`PALETTE_V2`, `RAMPS_V2`, aliases so v1 widgets work), `activate()`, carved-wood/bronze widgets (wood_planks, rope, interlace, rosette, bronze_corner, wood_slot, label_ru), serpent orb frame (`orb_v2`, `serpent_head`), skill/menu icons, potions |
| `fonts_ru.py` | `FONT_RU` (Cyrillic upper+lower case, digits, punctuation, 9 px line) and `FONT_USTAV` (12 px heading font in the style of Old Russian устав) |
| `sprites_rus.py` | material-map sprites: druzhinnik hero, upyr, volkolak, leshy, idol, roof-ridge horse head, dragon prow, ground items |
| `gameplay_hud_v2.py` | scene (iso ground, forest, log cabin, palisade, krada fire, longship, Nebyl rift) + HUD, same layout as v1 |

Call `theme_rus.activate()` before using pixelkit, because it switches the palette in place. v1 scripts still use the v1 palette when they run in their own process.

## v2 stage 2: windows and menu (theme «Гардарики»)

    python3 gameplay_hud_v2.py   # gameplay screen (re-rendered; previous version kept as *_v2a_*)
    python3 inventory_v2.py      # -> ../mockup_inventory_v2_*.png
    python3 character_v2.py      # -> ../mockup_character_v2_*.png
    python3 act_map_v2.py        # -> ../mockup_act_map_v2_*.png
    python3 main_menu_v2.py      # -> ../mockup_main_menu_v2_*.png

| Module | Contents |
|---|---|
| `fonts_ru.py` | `FONT_USTAV` is now hand-drawn: устав capitals with 2-px stems, wedge serifs, Λ-shaped Л, Д with feet, plus digits and punctuation. Line height is 14 (accent row + 11-px caps + descenders). The old auto-generated font is kept as `FONT_USTAV_AUTO`. |
| `ui_rus.py` | `bukvitsa` (decorated initial), `carved_frame` (frame with triangle-notch carving), `window`, `title_plate`, `close_button`, `button` (normal/hover/pressed/disabled), `plus_button`, `recess`, `section_title`, `tooltip`, `cursor`, `silver_icon`, `divider`, `wrap` |
| `items_rus.py` | item icons: меч, топор, кольчуга, круглый щит, шелом, гривна, лунница/громовник, перстни, рукавицы, пояс, сапоги, берестяная грамота, самоцветы; `RARITY`, `draw_item` |
| `screens_common_v2.py` | `scene(shift, dim, hud)`: the gameplay frame shifted, dimmed and with the HUD, used behind open windows |
| `gameplay_hud_v2.py` | adds `proj(u,v,z)`, a face-culling iso helper. The сруб and the ладья are now built in true 2:1 iso. |

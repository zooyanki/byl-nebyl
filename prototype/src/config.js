// Глобальные константы прототипа. Всё, что касается масштаба/проекции, — здесь.
export const VIEW_W = 640;          // нативное разрешение
export const VIEW_H = 360;
export const SCALE = 3;             // 640x360 x3 = 1920x1080

// Псевдоизометрия 2:1: ромб тайла 32x16 нативных пикселей.
export const TILE_W = 32;
export const TILE_H = 16;
export const HALF_W = TILE_W / 2;
export const HALF_H = TILE_H / 2;

export const PANEL_Y = 314;         // верх нижней панели HUD (design/scale.md §1: игровое поле 640×314)
export const PLAYFIELD_CY = 178;    // подошвы героя в (320, 178): центр тела в центре поля (scale.md §1)

export const MAP_W = 48;
export const MAP_H = 48;
export const MAP_SEED = 1337;

const params = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
export const DEBUG = params.has('debug');

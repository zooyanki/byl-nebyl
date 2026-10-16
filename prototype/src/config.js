// Глобальные константы прототипа. Всё, что касается масштаба/проекции, — здесь.
export const VIEW_W = 960;          // v2art: внутреннее разрешение 960×540 (было 640×360)
export const VIEW_H = 540;
export const SCALE = 2;             // 960×540 ×2 = 1920×1080, целый множитель, без сглаживания
// v2art r2 (ответ Василия: текст не мельче прежнего): интерфейс и все надписи — отдельный слой 640×360 ×3
// (прежняя сетка и прежний физический размер текста при 1080p), мир — 960×540 ×2.
export const UI_W = 640;
export const UI_H = 360;
export const UI_SCALE = 3;
export const UI_PANEL_Y = 314;              // верх нижней панели HUD в слое интерфейса
export const UI_K = UI_W / VIEW_W;          // экран мира → слой интерфейса (2/3)

// Псевдоизометрия 2:1: ромб тайла 32x16 нативных пикселей.
export const TILE_W = 32;
export const TILE_H = 16;
export const HALF_W = TILE_W / 2;
export const HALF_H = TILE_H / 2;

export const PANEL_Y = 471;         // верх нижней панели HUD в пикселях мира (314 × 1,5; игровое поле 960×471)
export const PLAYFIELD_CY = 264;    // подошвы героя в (480, 264): центр тела (56 px) в центре поля 471 (235,5 + 28)

export const MAP_W = 48;
export const MAP_H = 48;
export const MAP_SEED = 1337;

const params = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
export const DEBUG = params.has('debug');

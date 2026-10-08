// Мышь и клавиатура. Координаты мыши — в нативных пикселях (640x360).
import { VIEW_W, VIEW_H } from '../config.js';

// F1–F6 — горячие клавиши навыков (как в D2), поэтому браузерные F1 (справка) и F5 (обновить) в игре гасятся; Ctrl+R работает
const PREVENT = new Set(['Digit1', 'Digit2', 'Digit3', 'Digit4', 'Tab', 'AltLeft', 'AltRight', 'Space', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'KeyZ']);

export class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.mx = VIEW_W / 2; this.my = VIEW_H / 2;
    this.left = false; this.right = false;                // зажаты сейчас
    this.leftPressed = false; this.rightPressed = false;  // нажаты в этом кадре
    this.leftReleased = false; this.rightReleased = false;
    this.keysPressed = new Set();
    this.keysDown = new Set();
    this.shift = false; this.alt = false; this.ctrl = false;
    this.gesture = false;                                 // был ли жест пользователя (для WebAudio)
    this.onGesture = null;

    window.addEventListener('contextmenu', (e) => e.preventDefault());      // и на чёрных полях вокруг холста (QA B-09)
    this.wheel = 0;
    canvas.addEventListener('wheel', (e) => { this.wheel += Math.sign(e.deltaY); e.preventDefault(); }, { passive: false });
    canvas.addEventListener('mousemove', (e) => this._pos(e));
    canvas.addEventListener('mousedown', (e) => {
      this._pos(e); this._mods(e); this._gesture();
      if (e.button === 0) { this.left = true; this.leftPressed = true; }
      if (e.button === 2) { this.right = true; this.rightPressed = true; }
      e.preventDefault();
    });
    window.addEventListener('mousemove', (e) => { this._pos(e); this._mods(e); });
    window.addEventListener('mouseup', (e) => {
      if (e.button === 0 && this.left) { this.left = false; this.leftReleased = true; }
      if (e.button === 2 && this.right) { this.right = false; this.rightReleased = true; }
    });
    window.addEventListener('keydown', (e) => {
      this._mods(e); this._gesture();
      if (!e.repeat) this.keysPressed.add(e.code);
      this.keysDown.add(e.code);
      if (PREVENT.has(e.code) || e.altKey) e.preventDefault();
    });
    window.addEventListener('keyup', (e) => { this._mods(e); this.keysDown.delete(e.code); if (e.code.startsWith('Alt')) e.preventDefault(); });
    window.addEventListener('blur', () => { this.left = this.right = false; this.keysDown.clear(); this.shift = this.alt = this.ctrl = false; });
  }

  _mods(e) {
    this.shift = !!e.shiftKey; this.ctrl = !!e.ctrlKey;
    this.alt = !!e.altKey || this.keysDown.has('AltLeft') || this.keysDown.has('AltRight');
  }
  _gesture() { if (!this.gesture) { this.gesture = true; if (this.onGesture) this.onGesture(); } else if (this.onGesture) this.onGesture(); }

  _pos(e) {
    const r = this.canvas.getBoundingClientRect();
    if (!r.width) return;
    this.mx = (e.clientX - r.left) * VIEW_W / r.width;
    this.my = (e.clientY - r.top) * VIEW_H / r.height;
  }

  pressed(code) { return this.keysPressed.has(code); }
  down(code) { return this.keysDown.has(code); }
  get altHeld() { return this.keysDown.has('AltLeft') || this.keysDown.has('AltRight'); }

  endFrame() {
    this.leftPressed = false; this.rightPressed = false; this.wheel = 0;
    this.leftReleased = false; this.rightReleased = false;
    this.keysPressed.clear();
  }
}

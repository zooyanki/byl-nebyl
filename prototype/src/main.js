// Точка входа: холст 640x360, масштабирование под окно (целый множитель, по умолчанию x3), игровой цикл.
import { VIEW_W, VIEW_H } from './config.js';
import { makeRng } from './core/rng.js';
import { Game } from './game.js';
import { loadAssets } from './ui/assets.js';

// ?seed=N — детерминированная случайность (бой, добыча) для отладки и автотестов.
const seedParam = new URLSearchParams(location.search).get('seed');
if (seedParam !== null) Math.random = makeRng(Number(seedParam) || 1);

const canvas = document.getElementById('game');
canvas.width = VIEW_W;
canvas.height = VIEW_H;

function fit() {
  const s = Math.min(window.innerWidth / VIEW_W, window.innerHeight / VIEW_H);
  const k = s >= 1 ? Math.floor(s) : s; // целочисленный масштаб для чётких пикселей
  canvas.style.width = VIEW_W * k + 'px';
  canvas.style.height = VIEW_H * k + 'px';
}
window.addEventListener('resize', fit);
fit();

await loadAssets();
const game = new Game(canvas);
window.__ready = true;
window.__game = game; // для отладки и автотестов

let last = performance.now();
function loop(now) {
  const dt = Math.min(0.05, Math.max(0, (now - last) / 1000));
  last = now;
  game.frame(dt);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

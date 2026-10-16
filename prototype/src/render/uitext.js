// v2art r2: надписи, которые рисуются из кода мира (спрайты), откладываются и выводятся в слое интерфейса
// (640×360 ×3 — текст прежнего физического размера). Координаты — в пикселях экрана мира (960×540).
export const UIQ = [];
export function queueText(ctx, x, y, s, color, opts) { if (ctx && ctx.canvas && ctx.canvas.id === 'game') UIQ.push([x, y, s, color, opts]); }

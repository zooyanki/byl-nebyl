#!/bin/sh
# Запуск прототипа: локальный статический сервер (ES-модули не грузятся по file://).
PORT="${1:-8000}"
cd "$(dirname "$0")" || exit 1
echo "Быль и Небыль — прототип: открой http://localhost:${PORT}/  (Ctrl+C — остановить)"
exec python3 -m http.server "$PORT"

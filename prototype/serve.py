#!/usr/bin/env python3
"""Локальный сервер прототипа с явными MIME-типами.

Зачем: `python -m http.server` на Windows берёт MIME из реестра, и там .js часто
записан как text/plain. Браузеры (Firefox, Chrome) отказываются грузить ES-модули
с таким типом — игра остаётся чёрным экраном. Здесь типы заданы явно.

Запуск (из папки prototype):  py serve.py        (Windows)
                               python3 serve.py   (Linux/macOS)
Порт по умолчанию 8000, можно указать: py serve.py 8765
"""
import http.server
import os
import sys

MIME = {
    '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.png': 'image/png',
    '.wasm': 'application/wasm',
}


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **MIME}

    def guess_type(self, path):
        ext = os.path.splitext(str(path))[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')  # не залипать на старых/битых ответах
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Быль и Небыль — прототип: открой http://localhost:{port}/  (Ctrl+C — остановить)')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

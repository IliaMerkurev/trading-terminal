"""Loopback-only browser adapter for the existing bounded research service.

This is a local single-user transport, not a network server or an authentication
boundary against other processes running as the same OS user.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import signal
import threading
import tomllib

from terminal.data import canonical
from terminal.paths import data_root
from terminal.service import AppService

MAX_BODY = 1024 * 1024
MAX_STATIC = 8 * 1024 * 1024
CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")


class BrowserServer(HTTPServer):
    # POSIX SO_REUSEADDR permits rebinding after our closed HTTP connections
    # enter TIME_WAIT. It does not permit a second active listener (no REUSEPORT).
    # Windows SO_REUSEADDR has different sharing semantics; keep it disabled.
    allow_reuse_address = os.name != 'nt'

    def __init__(self, root, dist, port=0):
        self.dist = Path(dist).resolve(strict=True)
        # Only a built asset inventory can be served, never arbitrary host paths.
        self.assets = {}
        for path in self.dist.rglob('*'):
            if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(self.dist):
                self.assets['/' + path.relative_to(self.dist).as_posix()] = path
        if '/index.html' not in self.assets:
            raise ValueError('Build the frontend before starting browser mode')
        self.token = secrets.token_urlsafe(32)
        self.exports = {}
        self.closing = False
        self.service = None
        super().__init__(('127.0.0.1', port), BrowserHandler)
        self.origin = f'http://127.0.0.1:{self.server_port}'
        try:
            self.service = AppService(root)
            manifest = Path(__file__).resolve().parents[1] / 'src-tauri/Cargo.toml'
            self.product_version = tomllib.loads(manifest.read_text())['package']['version']
        except BaseException:
            self.server_close()
            raise

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def request_shutdown(self):
        self.closing = True
        # HTTPServer.shutdown must run outside its serving thread.
        threading.Thread(target=self.shutdown, daemon=True).start()

    def server_close(self):
        try:
            if self.service is not None:
                self.service.close()
                self.service = None
        finally:
            super().server_close()


class BrowserHandler(BaseHTTPRequestHandler):
    server_version = 'TradingTerminal'
    sys_version = ''

    def log_message(self, *args):
        pass  # Never log headers, payloads, URLs or per-launch session material.

    def reply(self, status, body=b'', content_type='application/json', filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Connection', 'close')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def failure(self, status, message):
        self.reply(status, canonical({'error': message}))

    def boundary(self, api=False):
        host = f'127.0.0.1:{self.server.server_port}'
        if self.headers.get_all('Host') != [host]:
            self.failure(403, 'Invalid local host'); return False
        origins = self.headers.get_all('Origin')
        if origins is not None and origins != [self.server.origin]:
            self.failure(403, 'Cross-origin requests are unavailable'); return False
        sites = self.headers.get_all('Sec-Fetch-Site')
        if (api and sites != ['same-origin']) or (not api and sites not in (None, ['none'], ['same-origin'])):
            self.failure(403, 'Same-origin browser context required'); return False
        if self.server.closing:
            self.failure(503, 'Local service is stopping'); return False
        return True

    def authenticated(self):
        if not self.boundary(api=True): return False
        tokens = self.headers.get_all('X-Terminal-Session')
        if not tokens or len(tokens) != 1 or not secrets.compare_digest(tokens[0], self.server.token):
            self.failure(401, 'Local session expired. Reload the page.'); return False
        return True

    def do_GET(self):
        if self.path == '/api/session':
            if not self.boundary(api=True): return
            if self.headers.get_all('X-Terminal-Bootstrap') != ['1']:
                self.failure(403, 'Browser bootstrap header required'); return
            self.reply(200, canonical({'token': self.server.token, 'product_version': self.server.product_version}))
            return
        if not self.boundary(): return
        path = self.server.assets.get('/index.html' if self.path == '/' else self.path)
        if path is None or path.is_symlink() or not path.resolve().is_relative_to(self.server.dist):
            self.failure(404, 'Asset not found'); return
        if path.stat().st_size > MAX_STATIC:
            self.failure(413, 'Asset exceeds size budget'); return
        types = {'.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8',
                 '.css':'text/css; charset=utf-8', '.svg':'image/svg+xml', '.png':'image/png',
                 '.ico':'image/x-icon', '.woff2':'font/woff2'}
        self.reply(200, path.read_bytes(), types.get(path.suffix, 'application/octet-stream'))

    def do_POST(self):
        if not self.authenticated(): return
        if self.headers.get_all('Origin') != [self.server.origin]:
            self.failure(403, 'Same-origin Origin header required'); return
        lengths = self.headers.get_all('Content-Length')
        if self.headers.get('Transfer-Encoding') is not None or not lengths or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,8}', lengths[0]):
            self.failure(400, 'One bounded content length required'); return
        length = int(lengths[0])
        if length > MAX_BODY:
            self.failure(413, 'Request exceeds 1 MiB'); return
        if self.headers.get_all('Content-Type') != ['application/json']:
            self.failure(415, 'application/json required'); return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length: raise ValueError('Truncated request')
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            self.failure(400, 'Invalid JSON request'); return
        if self.path == '/api/request':
            response = self.server.service.handle(value)
            if isinstance(value, dict) and value.get('command') == 'archive_export' and response['type'] == 'result':
                exported = response['result']
                self.server.exports[exported['filename']] = (exported['bytes'], exported['sha256'])
            self.reply(200, canonical(response))
        elif self.path == '/api/export':
            if not isinstance(value, dict) or set(value) != {'filename'} or not isinstance(value['filename'], str) or not re.fullmatch(r'[a-f0-9]{32}\.ttproject\.zip', value['filename']):
                self.failure(400, 'Invalid export descriptor'); return
            name = value['filename']
            grant = self.server.exports.get(name)
            directory = self.server.service.store.root / 'exports'
            path = directory / name
            if grant is None or not path.is_file() or path.is_symlink() or path.resolve().parent != directory.resolve() or path.stat().st_size != grant[0]:
                self.failure(404, 'Export is not available in this session'); return
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != grant[1]:
                self.failure(409, 'Export changed after creation'); return
            self.reply(200, raw, 'application/zip', filename=name)
        elif self.path == '/api/shutdown' and value == {}:
            self.reply(200, canonical({'stopping': True}))
            self.server.request_shutdown()
        else:
            self.failure(404, 'Unknown local endpoint')

    def do_OPTIONS(self):
        self.failure(403, 'Cross-origin access is unavailable')


def main():
    parser = argparse.ArgumentParser(description='Local browser research service (loopback only)')
    parser.add_argument('--data-root', required=True, help='Absolute isolated workspace; never share with a running desktop')
    parser.add_argument('--port', type=int, default=8765)
    options = parser.parse_args()
    if not 0 <= options.port <= 65535: parser.error('Invalid port')
    dist = Path(__file__).resolve().parents[1] / 'dist'
    server = BrowserServer(data_root(options.data_root), dist, options.port)
    def stop(*_): server.request_shutdown()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(f'Local research service ready: {server.origin}', flush=True)
    print('Closing a browser tab does not stop workers. Use Stop local service or Ctrl+C.', flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()

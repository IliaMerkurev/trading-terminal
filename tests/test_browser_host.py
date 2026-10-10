import base64
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from terminal.browser_host import BrowserServer, MAX_BODY
from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


class BrowserHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        dist = self.root / 'dist'; dist.mkdir()
        (dist / 'index.html').write_text('<!doctype html><title>Fixture</title>')
        (dist / 'main.js').write_text('const fixture = true;')
        (dist / 'leak').symlink_to(self.root / 'private')
        (self.root / 'private').write_text('must not be served')
        self.server = BrowserServer(self.root / 'data', dist)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .02})
        self.thread.start()
        self.headers = {'Origin': self.server.origin, 'Sec-Fetch-Site':'same-origin', 'Content-Type':'application/json'}
        status, body, _ = self.request('/api/session', headers={'Sec-Fetch-Site':'same-origin', 'X-Terminal-Bootstrap':'1'})
        self.assertEqual(status, 200)
        self.headers['X-Terminal-Session'] = json.loads(body)['token']

    def tearDown(self):
        self.server.shutdown(); self.thread.join(5); self.server.server_close(); self.tmp.cleanup()

    def request(self, path, method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return result

    def call(self, command, params=None):
        status, body, _ = self.request('/api/request', 'POST', json.dumps({'version':1, 'id':'fixture', 'command':command, 'params':params or {}}), self.headers)
        self.assertEqual(status, 200)
        return json.loads(body)

    def test_host_origin_session_and_static_boundaries(self):
        for path in ('/../private', '/%2e%2e/private', '/leak', '/main.js?secret=x', '/api/request', '/data/terminal.sqlite'):
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request('/', headers={'Host':'evil.example'})[0], 403)
        self.assertEqual(self.request('/', headers={'Sec-Fetch-Site':'cross-site'})[0], 403)
        for headers in ({}, {'Sec-Fetch-Site':'same-origin'}, {'Sec-Fetch-Site':'cross-site','X-Terminal-Bootstrap':'1'}, {'Sec-Fetch-Site':'same-origin','X-Terminal-Bootstrap':'1','Origin':'null'}):
            self.assertEqual(self.request('/api/session', headers=headers)[0], 403)
        for change, expected in [({'X-Terminal-Session':'wrong'},401), ({'Origin':'http://evil.example'},403), ({'Sec-Fetch-Site':'same-site'},403)]:
            self.assertEqual(self.request('/api/request','POST','{}',{**self.headers,**change})[0],expected)
        self.assertEqual(self.request('/api/request','OPTIONS')[0],403)
        without_origin = {key:value for key,value in self.headers.items() if key != 'Origin'}
        self.assertEqual(self.request('/api/request','POST','{}',without_origin)[0],403)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.putrequest('GET','/')
        connection.putheader('Host',f'127.0.0.1:{self.server.server_port}')
        connection.endheaders()
        duplicate = connection.getresponse()
        self.assertEqual(duplicate.status,403); duplicate.read(); connection.close()
        _, _, headers = self.request('/')
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertNotIn('Access-Control-Allow-Origin',headers)

    @unittest.skipIf(__import__('os').name == 'nt', 'POSIX address reuse semantics')
    def test_immediate_same_port_restart_keeps_listener_exclusive(self):
        port = self.server.server_port
        old_token = self.server.token
        # An already running host must never be silently shadowed.
        with self.assertRaises(OSError):
            BrowserServer(self.root/'other-data', self.root/'dist', port)
        self.assertFalse((self.root/'other-data').exists())
        self.assertEqual(self.request('/')[0], 200)
        self.server.shutdown(); self.thread.join(5); self.server.server_close()
        restarted = BrowserServer(self.root/'data', self.root/'dist', port)
        restart_thread = threading.Thread(target=restarted.serve_forever, kwargs={'poll_interval': .02})
        restart_thread.start()
        try:
            self.assertEqual(restarted.server_port, port)
            self.assertNotEqual(restarted.token, old_token)
            payload = json.dumps({'version':1,'id':'restart','command':'list_runs','params':{}})
            self.assertEqual(self.request('/api/request','POST',payload,self.headers)[0],401)
            status, session, _ = self.request('/api/session',headers={'Sec-Fetch-Site':'same-origin','X-Terminal-Bootstrap':'1'})
            self.assertEqual(status,200)
            current_headers = {**self.headers,'X-Terminal-Session':json.loads(session)['token']}
            status, body, _ = self.request('/api/request','POST',payload,current_headers)
            self.assertEqual(status,200); self.assertEqual(json.loads(body)['type'],'result')
            with self.assertRaises(OSError):
                BrowserServer(self.root/'other-data', self.root/'dist', port)
        finally:
            restarted.shutdown(); restart_thread.join(5)
            restarted.server_close()

    def test_failed_service_close_remains_available_for_cleanup_retry(self):
        self.server.shutdown(); self.thread.join(5)
        service = self.server.service
        close = service.close
        attempts = 0
        def fail_once():
            nonlocal attempts
            attempts += 1
            if attempts == 1: raise RuntimeError('Synthetic incomplete cleanup')
            close()
        with patch.object(service, 'close', side_effect=fail_once):
            with self.assertRaisesRegex(RuntimeError, 'Synthetic incomplete cleanup'):
                self.server.server_close()
            self.assertIs(self.server.service, service)
            self.server.server_close()
        self.assertIsNone(self.server.service)
        self.assertEqual(attempts, 2)
        reopened = AppService(self.root/'data')
        reopened.close()

    def test_bounded_json_and_command_envelope(self):
        for payload, change, expected in [('{}',{'Content-Type':'text/plain'},415), ('{',{},400), ('{}',{'Content-Length':str(MAX_BODY+1)},413), ('{}',{'Transfer-Encoding':'chunked'},400)]:
            self.assertEqual(self.request('/api/request','POST',payload,{**self.headers,**change})[0],expected)
        self.assertEqual(self.call('not_a_command')['type'],'error')
        self.assertEqual(self.call('list_runs')['result'],[])
        self.assertEqual(self.call('platform_capabilities')['result']['platform'],__import__('sys').platform)
        with self.assertRaisesRegex(ValueError,'Another application instance'):
            AppService(self.root/'data')

    def test_archive_export_import_and_reload_session(self):
        profile = Profile().snapshot()
        strategy = {'name':'Browser fixture','kind':'graph','document':{'graph':example_graph(),'layout':{}}}
        result = self.call('archive_export',{'strategy':strategy,'profile':profile,'run_ids':[]})
        self.assertEqual(result['type'],'result',result)
        name = result['result']['filename']
        status, raw, headers = self.request('/api/export','POST',json.dumps({'filename':name}),self.headers)
        self.assertEqual(status,200); self.assertEqual(headers['Content-Type'],'application/zip')
        self.assertEqual(self.request('/api/export','POST',json.dumps({'filename':'../private'}),self.headers)[0],400)
        self.assertEqual(self.request('/api/export','POST',json.dumps({'filename':'0'*32+'.ttproject.zip'}),self.headers)[0],404)
        upload = self.call('archive_begin',{'size':len(raw)})['result']
        self.call('archive_append',{'upload_id':upload['upload_id'],'offset':0,'data':base64.b64encode(raw).decode()})
        imported = self.call('archive_finish',{'upload_id':upload['upload_id']})
        self.assertEqual(imported['type'],'result',imported)
        _, session, _ = self.request('/api/session',headers={'Sec-Fetch-Site':'same-origin','X-Terminal-Bootstrap':'1'})
        self.assertEqual(json.loads(session)['token'],self.headers['X-Terminal-Session'])
        self.assertEqual(len(self.call('list_strategies')['result']),1)
        (self.root/'data'/'exports'/name).write_bytes(b'changed')
        self.assertEqual(self.request('/api/export','POST',json.dumps({'filename':name}),self.headers)[0],404)

    def test_real_worker_cancel_and_shutdown_release(self):
        bars = [Candle(i*60,100,101,99,100,10) for i in range(120)]
        dataset = self.server.service.datasets.save('spot','BTCUSDT',0,7200,bars,[],{},metadata={},provenance=[])
        started = self.call('start_run',{'strategy':example_graph(),'profile':Profile().snapshot(),'dataset_id':dataset['id']})
        self.assertEqual(started['type'],'result',started)
        run_id = started['result']['run_id']
        self.assertEqual(self.call('cancel_run',{'run_id':run_id})['type'],'result')
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            status=self.call('run_status',{'run_id':run_id})['result']['status']
            if status in ('cancelled','completed','failed'): break
            time.sleep(.05)
        self.assertEqual(status,'cancelled')
        running = self.call('start_run',{'strategy':example_graph(),'profile':Profile().snapshot(),'dataset_id':dataset['id']})['result']['run_id']
        self.assertEqual(self.request('/api/shutdown','POST','{}',self.headers)[0],200)
        self.thread.join(5); self.assertFalse(self.thread.is_alive())
        self.server.server_close()
        service=AppService(self.root/'data')
        try:
            self.assertEqual(service.jobs.status(run_id)['status'],'cancelled')
            self.assertEqual(service.jobs.status(running)['status'],'cancelled')
            with service.store.connect() as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        finally: service.close()

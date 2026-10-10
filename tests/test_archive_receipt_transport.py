"""Real serialized HTTP finalization, lost reply and read-only recovery."""
import base64
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from terminal.browser_host import BrowserHandler,BrowserServer
from tests.archive_receipt_fixtures import archive


class ReceiptTransportTests(unittest.TestCase):
    def test_lost_reply_and_serialized_inflight_status_then_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);dist=root/'dist';dist.mkdir();(dist/'index.html').write_text('<title>Fixture</title>')
            server=BrowserServer(root/'workspace',dist);thread=threading.Thread(target=server.serve_forever);thread.start()
            def call(command,params,headers):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                try:
                    conn.request('POST','/api/request',json.dumps({'version':1,'id':command,'command':command,'params':params}),headers)
                    response=conn.getresponse();return json.loads(response.read())
                finally:conn.close()
            def session():
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                conn.request('GET','/api/session',headers={'Sec-Fetch-Site':'same-origin','X-Terminal-Bootstrap':'1'})
                token=json.loads(conn.getresponse().read())['token'];conn.close()
                return {'Origin':server.origin,'Sec-Fetch-Site':'same-origin','Content-Type':'application/json','X-Terminal-Session':token}
            entered=threading.Event();release=threading.Event();status_sent=threading.Event();status_done=threading.Event()
            finish_errors=[];status_results=[];original=server.service.archives.receipts.publish_run;original_reply=BrowserHandler.reply
            try:
                headers=session();raw,_,_=archive()
                op=call('archive_begin',{'size':len(raw)},headers)['result']['operation_id']
                call('archive_append',{'upload_id':op,'offset':0,'data':base64.b64encode(raw).decode()},headers)
                def barrier(*args):
                    if args[1]==0:entered.set();assert release.wait(10)
                    return original(*args)
                def drop(handler,status,body,*args,**kwargs):
                    parsed=json.loads(body) if handler.path=='/api/request' else {}
                    if parsed.get('id')=='archive_finish':handler.close_connection=True;handler.connection.shutdown(2);return
                    return original_reply(handler,status,body,*args,**kwargs)
                def finish():
                    try:call('archive_finish',{'upload_id':op},headers)
                    except (http.client.HTTPException,OSError) as error:finish_errors.append(type(error).__name__)
                def inspect():
                    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                    try:
                        conn.request('POST','/api/request',json.dumps({'version':1,'id':'inspect','command':'archive_import_status','params':{'operation_id':op}}),headers)
                        status_sent.set();status_results.append(json.loads(conn.getresponse().read()));status_done.set()
                    finally:conn.close()
                with patch.object(server.service.archives.receipts,'publish_run',side_effect=barrier),patch.object(BrowserHandler,'reply',drop):
                    finalizer=threading.Thread(target=finish);finalizer.start();self.assertTrue(entered.wait(10))
                    reader=threading.Thread(target=inspect);reader.start();self.assertTrue(status_sent.wait(10));self.assertFalse(status_done.is_set())
                    release.set();finalizer.join(10);reader.join(10)
                self.assertTrue(finish_errors);self.assertTrue(status_done.is_set());receipt=status_results[0]['result'];self.assertEqual(receipt['outcome'],'completed')
                mappings=[item['destination_id'] for item in receipt['items']]
                before=server.service.store.recent();server.shutdown();thread.join(10);server.server_close()
                server=BrowserServer(root/'workspace',dist);thread=threading.Thread(target=server.serve_forever);thread.start();headers=session()
                inspected=call('archive_import_status',{'operation_id':op},headers)['result']
                self.assertEqual([item['destination_id'] for item in inspected['items']],mappings);self.assertEqual(inspected['outcome'],'completed')
                self.assertEqual(server.service.store.recent(),before)
                self.assertEqual(call('archive_import_list',{'before':None,'limit':25},headers)['result']['rows'][0]['operation_id'],op)
            finally:
                release.set();server.shutdown();thread.join(10);server.server_close()

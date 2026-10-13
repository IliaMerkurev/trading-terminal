"""Synthetic owner-death fixture; paused owned supervisor before bootstrap."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch
import uuid
from terminal.service import AppService
from tests.archive_receipt_fixtures import documents

root=Path(sys.argv[1]);service=AppService(root);project,_=documents();spawn=subprocess.Popen;supervisor=None

def paused(*args,**kwargs):
    global supervisor
    process=spawn(*args,**kwargs);supervisor=process.pid;os.kill(supervisor,signal.SIGSTOP);return process

ident=uuid.uuid4().hex
with patch('terminal.archive_export.subprocess.Popen',side_effect=paused):service.exports.start(ident,project['strategy'],project['profile'],[])
(root/'probe-ready.json').write_text(json.dumps({'export_id':ident,'supervisor_pid':supervisor}))
while True:time.sleep(1)

"""Private subprocess fixture: crash owner while bootstrap is deliberately paused."""
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch
from terminal.archives import ArchiveManager
from terminal.jobs import JobManager
from tests.archive_receipt_fixtures import archive

root=Path(sys.argv[1]);jobs=JobManager(root);manager=ArchiveManager(jobs.store,jobs)
raw,_,_=archive();op=manager.begin(len(raw))['operation_id'];manager.append(op,0,base64.b64encode(raw).decode())
spawn=subprocess.Popen;supervisor=None
def paused(*args,**kwargs):
    global supervisor
    process=spawn(*args,**kwargs);supervisor=process.pid;os.kill(supervisor,signal.SIGSTOP)
    return process
with patch('terminal.archive_execution.subprocess.Popen',side_effect=paused):manager.start(op)
(root/'probe-ready.json').write_text(json.dumps({'operation_id':op,'supervisor_pid':supervisor}))
while True:time.sleep(1)

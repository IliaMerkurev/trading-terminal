"""Test-only managed finalizer fault process; never a production command."""
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    mode=sys.argv[1];control=Path(sys.argv[2])
    if sys.platform=='linux' and os.environ.get('_TRADING_TERMINAL_SUPERVISOR')=='1':
        from terminal import linux_worker
        original=subprocess.Popen
        def launch(args,**kwargs):
            return original([sys.executable,'-m','tests.finalization_worker_probe',mode,str(control)],**kwargs)
        linux_worker.subprocess.Popen=launch
        return linux_worker.supervise()
    from terminal import result_finalization as finalization
    from terminal import worker
    original=finalization.finalize
    def wrapped(store,ident,key):
        def checkpoint(phase):
            if mode in ('postcommit','marker_cancel') and phase=='committed':raise OSError('injected postcommit storage fault')
            if mode=='phase_gate' and phase=='artifact':
                (control/'ready').write_text('artifact_phase_without_write_lock')
                while not (control/'release').exists():time.sleep(.01)
            if mode=='write_stall' and phase=='batch:1':
                with store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    (control/'ready').write_text('write_owned')
                    while not (control/'release').exists():time.sleep(.01)
        return original(store,ident,key,checkpoint)
    finalization.finalize=wrapped
    result=worker.main()
    if mode=='marker_cancel':
        assert result==finalization.STORAGE_EXIT
        (control/'ready').write_text('durable_storage_marker')
        while not (control/'release').exists():time.sleep(.01)
    return result


if __name__=='__main__':raise SystemExit(main())

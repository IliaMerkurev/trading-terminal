"""Line-oriented local desktop IPC. Strategy output never enters this stream."""
from pathlib import Path
import argparse
import json
import sys


def main():
    parser=argparse.ArgumentParser(description='Local research IPC service')
    parser.add_argument('--data-root')
    options=parser.parse_args()
    from terminal.service import AppService
    from terminal.data import canonical
    from terminal.paths import data_root
    def send(value):
        sys.stdout.buffer.write(canonical(value)+b'\n');sys.stdout.buffer.flush()
    try:
        service=AppService(data_root(options.data_root))
    except Exception as error:
        send({'version':1,'id':'startup','type':'error','error':{'code':'STARTUP_FAILED','message':str(error)[:1000]}})
        return 1
    send({'version':1,'id':'startup','type':'ready'})
    try:
        while True:
            raw=sys.stdin.buffer.readline(1024*1024+1)
            if not raw: break
            if len(raw)>1024*1024:
                # Do not interpret the remainder as another request.
                response={"version":1,"id":None,"type":"error","error":{"code":"TOO_LARGE","message":"IPC line exceeds 1 MiB"}}
                sys.stdout.buffer.write(canonical(response)+b"\n");sys.stdout.buffer.flush()
                break
            try: response=service.handle(json.loads(raw))
            except (ValueError,UnicodeError):
                response={"version":1,"id":None,"type":"error","error":{"code":"INVALID_JSON","message":"Invalid JSON request"}}
            sys.stdout.buffer.write(canonical(response)+b"\n")
            sys.stdout.buffer.flush()
    finally:
        service.close()


if __name__=="__main__":
    raise SystemExit(main())

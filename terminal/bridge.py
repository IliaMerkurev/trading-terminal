"""Line-oriented local desktop IPC. Strategy output never enters this stream."""
from pathlib import Path
import json
import sys


def main():
    from terminal.service import AppService
    from terminal.data import canonical
    service=AppService(Path(__file__).resolve().parents[1]/".local-data")
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
    main()

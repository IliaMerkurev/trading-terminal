"""Linux graph/replay supervisor. Process groups are not a security sandbox.

Only stdlib imports occur before the parent's bounded bootstrap request. The
service's lifetime pipe and workspace lock are inherited through exec, so an
abrupt service exit cannot release ownership while the worker is still alive.
"""
import json
import os
import selectors
import signal
import subprocess
import sys


PREFIX = '_TRADING_TERMINAL_'


def _request(selector, lifetime_fd):
    data = bytearray()
    while True:
        for key, _ in selector.select():
            if key.fd == lifetime_fd:
                return None  # EOF (or unexpected input) revokes permission to run.
            chunk = os.read(sys.stdin.fileno(), 4096)
            if not chunk:
                return None
            data.extend(chunk)
            if len(data) > 1024 * 1024:
                raise ValueError('Worker input exceeds budget')
            if b'\n' in data:
                line, remainder = data.split(b'\n', 1)
                if remainder:
                    raise ValueError('Worker accepts exactly one bootstrap request')
                request = json.loads(line)
                if not isinstance(request, dict) or request.get('version') != 1 or request.get('command') not in ('run', 'replay', 'archive_import', 'archive_export', 'finalize_run', 'chart_read'):
                    raise ValueError('Invalid worker command')
                return bytes(line) + b'\n'


def _stop_group(process):
    # The group leader has not been reaped: its PID cannot be reused here.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()  # Retain workspace ownership until the worker is dead.


def supervise():
    lifetime_fd = int(os.environ['_TRADING_TERMINAL_LIFETIME_FD'])
    workspace_fd = int(os.environ['_TRADING_TERMINAL_WORKSPACE_FD'])
    process = None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(lifetime_fd, selectors.EVENT_READ)
            selector.register(sys.stdin.fileno(), selectors.EVENT_READ)
            payload = _request(selector, lifetime_fd)
            if payload is None:
                return 130
            selector.unregister(sys.stdin.fileno())
            # Check again before spawning; the service may have died at the gate.
            if selector.select(0):
                return 130
            environment = {key: value for key, value in os.environ.items()
                           if key not in (PREFIX + 'SUPERVISOR', PREFIX + 'LIFETIME_FD', PREFIX + 'WORKSPACE_FD')}
            process = subprocess.Popen([sys.executable, '-m', 'terminal.worker'],
                stdin=subprocess.PIPE, stdout=sys.stdout.buffer, stderr=subprocess.STDOUT,
                start_new_session=True, pass_fds=(workspace_fd,), env=environment)
            process.stdin.write(payload)
            process.stdin.close()
            while True:
                if selector.select(.05):
                    return 130
                # WNOWAIT reserves the leader's PID until group cleanup.
                exited = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if exited is not None:
                    return exited.si_status if exited.si_code == os.CLD_EXITED else 128 + exited.si_status
    finally:
        if process is not None:
            _stop_group(process)
        os.close(lifetime_fd)
        os.close(workspace_fd)

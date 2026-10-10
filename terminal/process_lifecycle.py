"""Platform-specific workspace ownership and worker lifetime, not a sandbox.

Linux supports application-owned graph/replay workers only. A process group
cannot contain arbitrary Python descendants which change their session/group.
Windows retains Job Object lifetime control for trusted native strategies.
"""
import os
import sys


NATIVE_UNAVAILABLE = ('Native Python execution is unavailable on this platform: '
                      'descendant lifetime containment has not been verified. '
                      'Preview and saved results remain available.')


def require_native_execution():
    if os.name != 'nt':
        raise ValueError(NATIVE_UNAVAILABLE)


def lock_workspace(stream):
    stream.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    elif sys.platform == 'linux':
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    else:
        raise OSError('Workspace ownership is unsupported on this platform')


def unlock_workspace(stream):
    stream.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class LinuxJob:
    """A supervisor observes pipe EOF on cancellation or service death.

    The workspace lock is inherited by supervisor and worker. The supervisor
    kills the worker group and waits before exiting and releasing ownership.
    No native/untrusted code is permitted in this Linux lifecycle contract.
    """
    def __init__(self, workspace_file):
        self.workspace_fd = workspace_file.fileno()
        self.reader, self.writer = os.pipe()
        self.process = None

    def popen_options(self):
        return {
            'start_new_session': True,
            'pass_fds': (self.reader, self.workspace_fd),
            'env': {**os.environ, '_TRADING_TERMINAL_SUPERVISOR': '1',
                    '_TRADING_TERMINAL_LIFETIME_FD': str(self.reader),
                    '_TRADING_TERMINAL_WORKSPACE_FD': str(self.workspace_fd)},
        }

    def assign(self, process):
        self.process = process
        os.close(self.reader)
        self.reader = None

    def terminate(self):
        if self.writer is not None:
            os.close(self.writer)
            self.writer = None

    def close(self):
        self.terminate()
        if self.reader is not None:
            os.close(self.reader)
            self.reader = None


def worker_job(workspace_file):
    if os.name == 'nt':
        from terminal.windows_job import WindowsJob
        return WindowsJob()
    if sys.platform == 'linux':
        return LinuxJob(workspace_file)
    raise OSError('Worker lifecycle is unsupported on this platform')


def worker_options(job):
    if os.name == 'nt':
        import subprocess
        return {'creationflags': subprocess.CREATE_NO_WINDOW}
    return job.popen_options()


def platform_capabilities():
    windows = os.name == 'nt'
    return {'platform': sys.platform,
            'native_execution': {'available': windows, 'reason': None if windows else NATIVE_UNAVAILABLE},
            'notifications': {name: {'available': windows,
                'reason': None if windows else ('Protected Telegram credential storage is unavailable on this platform' if name == 'telegram' else name.title() + ' notifications are unavailable on this platform')}
                for name in ('windows', 'sound', 'telegram')}}

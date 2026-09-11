"""Explicit process-local storage selection, never a renderer-supplied path."""
import os
from pathlib import Path


def data_root(override=None):
    configured=override if override is not None else os.environ.get('TRADING_TERMINAL_DATA_ROOT')
    if configured is None:
        return Path(__file__).resolve().parents[1]/'.local-data'
    if not isinstance(configured,str) or not configured.strip():
        raise ValueError('Data root must be a nonempty absolute directory')
    path=Path(configured)
    if not path.is_absolute():raise ValueError('Data root must be absolute')
    if path.exists() and not path.is_dir():raise ValueError('Data root is not a directory')
    return path.resolve()

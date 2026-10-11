"""Full-file verified, bounded-memory candle inspection; no historical hash cache."""
import os
import math
import stat
from terminal import source_limits


def file_identity(info):
    return [info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns]


def unchanged(path, expected):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or file_identity(info)!=expected:
        raise ValueError('Local history changed during verification; request the page again')


def candle_window(path, manifest, start, end, *, max_file_bytes=None, max_rows=None,
                  limit_message=source_limits.SOURCE_LIMIT, progress=lambda phase:None):
    """Hash and decode the same descriptor, validate every row and declared gap.

    Descriptor/path identity checks detect ordinary concurrent replacement and
    in-place modification; they supplement this operation's full cryptographic
    hash, never replace it or authorize a later operation.
    """
    source_limits.check_manifest(manifest)
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode):raise ValueError('Local history must be a regular file')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0))
    with os.fdopen(fd,'rb') as stream:
        identity=file_identity(os.fstat(stream.fileno()))
        if identity!=file_identity(before):raise ValueError('Local history changed while opening')
        progress('verifying')
        parquet,_=source_limits.checked_parquet(stream,'trade',manifest['files_sha256']['trade'],
            max_file_bytes=max_file_bytes,max_rows=max_rows,limit_message=limit_message,
            checksum_message='Local trade history checksum mismatch; source cannot be displayed')
        progress('decoding')
        step=manifest.get('interval_seconds',60);first,last=manifest['range']
        expected=manifest.get('coverage',{}).get('trade',{})
        declared=expected.get('gaps',[]);gap_index=0;next_time=first
        rows=[];count=0;actual_first=None;actual_last=None
        def gap(a,b):
            nonlocal gap_index
            if a<b:
                if gap_index>=len(declared) or declared[gap_index]!=[a,b]:
                    raise ValueError('Local history gap coverage differs from its manifest')
                gap_index+=1
        for batch in parquet.iter_batches(batch_size=256,columns=['time','open','high','low','close','volume']):
            for row in batch.to_pylist():
                t=row['time']
                if type(t) is not int or t%step or not first<=t<last or t<next_time:
                    raise ValueError('Local history contains invalid candle order or boundaries')
                if not all(type(row[k]) in (int,float) and math.isfinite(row[k]) for k in ('open','high','low','close','volume')):
                    raise ValueError('Local history contains invalid candle values')
                if row['low']>min(row['open'],row['close']) or row['high']<max(row['open'],row['close']) or row['low']<=0 or row['volume']<0:
                    raise ValueError('Local history contains invalid OHLC candles')
                gap(next_time,t);next_time=t+step
                if actual_first is None:actual_first=t
                actual_last=t+step;count+=1
                if start<=t<end:rows.append(row)
        gap(next_time,last)
        actual=dict(requested_start=first,requested_end=last,count=count,expected_count=(last-first)//step,
                    actual_start=actual_first,actual_end=actual_last,complete=gap_index==0)
        if gap_index!=len(declared) or any(expected.get(k)!=v for k,v in actual.items()):
            raise ValueError('Local history coverage differs from its manifest')
        if file_identity(os.fstat(stream.fileno()))!=identity:
            raise ValueError('Local history changed during verification')
        unchanged(path,identity)
    present={row['time'] for row in rows}
    return rows,[t for t in range(start,end,step) if t not in present],identity

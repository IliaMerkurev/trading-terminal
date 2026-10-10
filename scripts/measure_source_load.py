"""Bounded synthetic full-table load calibration; no strategy or exchange access."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--generate':
        from terminal.data import DatasetStore
        from terminal.series import Candle
        count=30000
        bars=[Candle(i*60,100,101,99,100,10) for i in range(count)]
        manifest=DatasetStore(sys.argv[2]).save('linear','BTCUSDT',0,count*60,bars,bars,
            {i*60:'0.0001' for i in range(0,count,480)},metadata={'instrument':{'fundingInterval':480}},provenance=[])
        print(manifest['id'])
        return
    if len(sys.argv)>1:
        import resource
        from terminal.data import DatasetStore
        before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        started=time.perf_counter()
        manifest,trade,marks,funding=DatasetStore(sys.argv[1]).load(sys.argv[2])
        print(json.dumps(dict(trade_rows=len(trade),mark_rows=len(marks),funding_rows=len(funding),
            seconds=round(time.perf_counter()-started,4),process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            pre_load_high_water_rss_kib=before,scope='Linux subprocess high-water RSS, imports included; fixture generation excluded')))
        return
    # Generation and measurement are siblings, so the measured process does not
    # inherit a Python generator's high-water memory usage through fork/exec.
    with tempfile.TemporaryDirectory(prefix='source-load-calibration-') as temp:
        ident=subprocess.check_output([sys.executable,__file__,'--generate',temp],text=True).strip()
        subprocess.run([sys.executable,__file__,temp,ident],check=True)


if __name__=='__main__':main()

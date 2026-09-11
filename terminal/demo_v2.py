"""Bounded synthetic 0.2 demonstration, using a separate default data directory."""
import argparse
import ctypes
from ctypes import wintypes
from decimal import Decimal
import json
from pathlib import Path
import time

from terminal.data import canonical,digest,runtime_snapshot,write_new
from terminal.graph import example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.service import AppService


class MemoryCounters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]


def working_set(handle):
    counters=MemoryCounters();counters.cb=ctypes.sizeof(counters)
    read=ctypes.WinDLL('psapi').GetProcessMemoryInfo
    read.argtypes=[wintypes.HANDLE,ctypes.POINTER(MemoryCounters),wintypes.DWORD];read.restype=wintypes.BOOL
    if not read(handle,ctypes.byref(counters),counters.cb):raise ctypes.WinError()
    return counters.WorkingSetSize


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-root',type=Path)
    args=parser.parse_args();root=(args.data_root or Path(__file__).resolve().parents[1]/'.local-data/v2-demo').resolve()
    record=root/'demos'/('v2-'+digest(runtime_snapshot())+'.json')
    if record.exists():print(record.read_text(encoding='utf-8'));return
    service=AppService(root);started=time.perf_counter();peak=0
    get_current=ctypes.WinDLL('kernel32').GetCurrentProcess;get_current.restype=wintypes.HANDLE
    def wait(predicate):
        nonlocal peak
        deadline=time.monotonic()+120
        while not predicate():
            current=working_set(get_current())
            with service.jobs.lock:
                if service.jobs.active:
                    try:current+=working_set(int(service.jobs.active['process']._handle))
                    except OSError:pass
            peak=max(peak,current)
            if time.monotonic()>deadline:raise RuntimeError('Demonstration exceeded its 120-second phase budget')
            time.sleep(.03)
    try:
        # Deliberately independent, small candle fixtures; no downloaded history.
        start=1735689600
        bars=[Candle(start+i*60,100+i%12,103+i%12,97+i%12,100+i%12,100) for i in range(240)]
        dataset=service.datasets.save('spot','BTCUSDT',start,start+240*60,bars,[],{},metadata={},provenance=[],source='Synthetic 0.2 parameter experiment')
        graph=example_graph();profile=Profile(version=2,primary_minutes=1,fee_rate='.001').snapshot()
        strategy=service.store.save_strategy('Synthetic 0.2: fixed grid and later validation','graph',{'graph':graph,'layout':{}},None,profile=profile)
        experiment=service.experiments.start(strategy_id=strategy,dataset_id=dataset['id'],profile=profile,is_range=[start+30*60,start+150*60],oos_range=[start+180*60,start+240*60],axes=[{'key':'node.mean.period','values':[2,3,4,5]},{'key':'profile.stop_loss','values':['0','.02','.04','.06']}])['experiment_id']
        wait(lambda:service.experiments.active is None)
        report=service.experiments.get(experiment)
        if report['status']!='completed' or any(r['status']!='completed' for r in report['rows']):raise RuntimeError('A demonstration combination failed')
        # Ordinal zero is chosen in advance. No holdout result is consulted.
        frozen=service.experiments.freeze(experiment,0)
        service.experiments.validate(frozen['validation_id']);wait(lambda:service.experiments.active is None)
        validation=service.experiments.get(experiment)['validations'][0]
        if validation['status']!='completed':raise RuntimeError('Demonstration validation failed')
        manifest=service.store.get(validation['run_id'])['manifest']
        single=service.jobs.start(manifest['strategy'],manifest['profile'],dataset['id'],research={'window':manifest['research']['window']})
        wait(lambda:service.jobs.active is None)
        expected=service.store.result(single);actual=service.store.result(validation['run_id'])
        for field in ('metrics','fills','trades','indicators','equity'):
            if expected[field]!=actual[field]:raise RuntimeError('Standalone validation differs: '+field)
        result={'source':'Synthetic fixtures; no exchange history','strategy_id':strategy,'experiment_id':experiment,'combinations':16,'completed':report['finished'],'predeclared_candidate_ordinal':0,'validation_id':frozen['validation_id'],'validation_run_id':validation['run_id'],'standalone_run_id':single,'standalone_equivalence':'passed','in_sample_metrics':report['rows'][0]['summary']['metrics'],'out_of_sample_metrics':actual['metrics'],'elapsed_seconds':round(time.perf_counter()-started,3),'sampled_combined_working_set_mib':round(peak/1024**2,1)}
        write_new(record,canonical(result));print(json.dumps(result,indent=2))
    finally:service.close()


if __name__=='__main__':main()

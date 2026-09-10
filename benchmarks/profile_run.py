"""Bounded synthetic Windows runtime/memory measurement, not market research."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
import math
import time

from terminal.graph import GraphEvaluator,example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


class Memory(c.Structure):
    _fields_ = [("cb",w.DWORD),("faults",w.DWORD)] + [(name,c.c_size_t) for name in
        ("peak_working_set","working_set","peak_paged","paged","peak_nonpaged","nonpaged","pagefile","peak_pagefile")]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--minutes",type=int,default=1440)
    args=parser.parse_args()
    if not 120 <= args.minutes <= 10080:
        parser.error("Benchmark fixture must be 120–10080 minutes")
    bars=[]
    for i in range(args.minutes):
        price=round(100+5*math.sin(i/200),2)
        bars.append(Candle(i*60,price,price+1,price-1,price,100))
    start=time.perf_counter()
    result=run_backtest(bars,Profile(evaluation="intrabar"),GraphEvaluator(example_graph()))
    seconds=time.perf_counter()-start
    api=c.WinDLL("kernel32")
    api.GetCurrentProcess.restype=w.HANDLE
    psapi=c.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.POINTER(Memory),w.DWORD]
    psapi.GetProcessMemoryInfo.restype=w.BOOL
    memory=Memory(); memory.cb=c.sizeof(memory)
    if not psapi.GetProcessMemoryInfo(api.GetCurrentProcess(),c.byref(memory),memory.cb):
        raise c.WinError()
    print(json.dumps({"minutes":len(bars),"seconds":round(seconds,3),
        "peak_working_set_mib":round(memory.peak_working_set/1024**2,1),
        "normalized_json_mib":round(len(json.dumps(result).encode())/1024**2,2),
        "trades":result["metrics"]["trade_count"]}))


if __name__=="__main__":
    main()

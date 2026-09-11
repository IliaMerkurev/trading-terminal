"""Credential-free Bybit history, immutable Parquet snapshots and coverage."""
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import threading
import time
import uuid
from urllib import request,parse,error

import pyarrow as pa
import pyarrow.parquet as pq

from terminal.profile import dec
from terminal.series import Candle

BASE="https://api.bybit.com"
ENDPOINTS={"/v5/market/time","/v5/market/kline","/v5/market/mark-price-kline",
           "/v5/market/funding/history","/v5/market/instruments-info","/v5/market/risk-limit"}


class DataError(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_new(path,data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data: raise DataError("Immutable content already exists with different bytes")
        return
    temporary=path.with_name(path.name+"."+uuid.uuid4().hex+".partial")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Windows rename is atomic and refuses to overwrite an existing file.
        os.rename(temporary,path)
    except FileExistsError:
        if path.read_bytes()!=data: raise DataError("Immutable content already exists with different bytes")
        temporary.unlink()  # Only this call's completed duplicate temporary file.


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise DataError("Unexpected redirect from the public market endpoint")


class BybitClient:
    def __init__(self,cache_dir,*,offline=False,cancel=None,transport=None):
        self.cache_dir=Path(cache_dir)
        self.offline=offline
        self.cancel=cancel or threading.Event()
        self.transport=transport or self._http
        self.requests=[]
        self.last_request=0.0

    def _http(self,path,params):
        # This client deliberately has no authentication parameters or headers.
        url=BASE+path+"?"+parse.urlencode(params)
        opener=request.build_opener(NoRedirect)
        for attempt in range(3):
            if self.cancel.is_set(): raise DataError("Download cancelled")
            wait=max(0,0.25-(time.monotonic()-self.last_request))
            if self.cancel.wait(wait): raise DataError("Download cancelled")
            self.last_request=time.monotonic()
            try:
                with opener.open(request.Request(url,headers={"User-Agent":"TradingTerminal/0.1 historical-research"}),timeout=20) as response:
                    raw=response.read(4*1024*1024+1)
                if len(raw)>4*1024*1024: raise DataError("Market response exceeds the page size budget")
                payload=json.loads(raw)
                if payload.get("retCode") in (10006,10016):
                    raise DataError("Transient market API rate/server limit")
                return payload
            except (error.URLError,TimeoutError,DataError) as exc:
                retryable=not isinstance(exc,DataError) or "Transient" in str(exc)
                if isinstance(exc,error.HTTPError) and exc.code not in (429,500,502,503,504): retryable=False
                if not retryable or attempt==2:
                    raise DataError(f"Public market request failed: {type(exc).__name__}") from exc
                if self.cancel.wait(0.5*(attempt+1)): raise DataError("Download cancelled")

    def get(self,path,params=None,*,cache=True):
        if path not in ENDPOINTS: raise DataError("Unsupported public endpoint")
        params=params or {}
        if self.cancel.is_set(): raise DataError("Download cancelled")
        key=digest({"endpoint":path,"params":params})
        file=self.cache_dir/(key+".json")
        if cache and file.exists():
            envelope=json.loads(file.read_bytes())
            if digest(envelope["payload"])!=envelope["sha256"]: raise DataError("Cached response checksum mismatch")
        else:
            if self.offline: raise DataError("Requested history is not available in the offline cache")
            payload=self.transport(path,params)
            if not isinstance(payload,dict) or payload.get("retCode")!=0:
                raise DataError(f"Market API returned error code {payload.get('retCode') if isinstance(payload,dict) else 'invalid response'}")
            envelope={"payload":payload,"sha256":digest(payload),"retrieved_at":datetime.now(timezone.utc).isoformat()}
            if cache: write_new(file,canonical(envelope))
        self.requests.append({"endpoint":path,"params":params,"response_sha256":envelope["sha256"],"retrieved_at":envelope["retrieved_at"],
                              "provider_time_ms":envelope["payload"].get("time")})
        return envelope["payload"].get("result",{})

    def instruments(self,market,symbol=None):
        if market not in ("spot","linear"): raise DataError("Unsupported market")
        params={"category":market}
        if symbol:
            validate_symbol(symbol)
            params["symbol"]=symbol
        elif market=="linear": params["limit"]=1000
        output=[]; seen=set()
        while True:
            result=self.get("/v5/market/instruments-info",params,cache=False)
            output.extend(item for item in result.get("list",[]) if item.get("quoteCoin")=="USDT" and
                (market=="spot" or item.get("contractType")=="LinearPerpetual"))
            cursor=result.get("nextPageCursor")
            if not cursor: break
            if cursor in seen: raise DataError("Instrument pagination did not advance")
            seen.add(cursor); params={**params,"cursor":cursor}
        return output

    def candles(self,market,symbol,start,end,*,mark=False):
        validate_range(market,symbol,start,end)
        if mark and market!="linear": raise DataError("Mark candles require linear perpetuals")
        endpoint="/v5/market/mark-price-kline" if mark else "/v5/market/kline"
        cursor=end*1000-1; rows={}
        while cursor>=start*1000:
            result=self.get(endpoint,{"category":market,"symbol":symbol,"interval":"1","start":start*1000,"end":cursor,"limit":1000})
            page=result.get("list",[])
            if not page: break
            oldest=min(int(row[0]) for row in page)
            if oldest>cursor: raise DataError("Candle pagination did not advance")
            for row in page:
                timestamp=int(row[0])
                if timestamp%60000: raise DataError("Candle timestamp is not minute-aligned")
                timestamp//=1000
                if start<=timestamp<end:
                    provider_time=self.requests[-1].get("provider_time_ms")
                    if provider_time is not None and (timestamp+60)*1000>int(provider_time):
                        continue  # Never store a provider's still-forming minute.
                    candle=Candle(timestamp,*map(float,row[1:5]),0.0 if mark else float(row[5]))
                    if timestamp in rows and rows[timestamp]!=candle: raise DataError("Conflicting duplicate market candle")
                    rows[timestamp]=candle
            cursor=oldest-1
        return [rows[t] for t in sorted(rows)]

    def funding(self,symbol,start,end):
        validate_range("linear",symbol,start,end)
        cursor=end*1000-1; rows={}
        while cursor>=start*1000:
            result=self.get("/v5/market/funding/history",{"category":"linear","symbol":symbol,"startTime":start*1000,"endTime":cursor,"limit":200})
            page=result.get("list",[])
            if not page: break
            oldest=min(int(row["fundingRateTimestamp"]) for row in page)
            if oldest>cursor: raise DataError("Funding pagination did not advance")
            for row in page:
                timestamp=int(row["fundingRateTimestamp"])
                if timestamp%60000 or row.get("symbol")!=symbol: raise DataError("Unsupported funding timestamp or symbol")
                timestamp//=1000
                if start<=timestamp<end:
                    rate=str(dec(row["fundingRate"]))
                    if timestamp in rows and rows[timestamp]!=rate: raise DataError("Conflicting funding events")
                    rows[timestamp]=rate
            cursor=oldest-1
        return {t:rows[t] for t in sorted(rows)}


def validate_symbol(symbol):
    if not isinstance(symbol,str) or not re.fullmatch(r"[A-Z0-9]{1,24}USDT",symbol):
        raise DataError("Expected an uppercase USDT symbol")


def validate_range(market,symbol,start,end):
    validate_symbol(symbol)
    if market not in ("spot","linear") or type(start) is not int or type(end) is not int or start<0 or start%60 or end%60 or end<=start:
        raise DataError("Expected a positive UTC minute-aligned [start,end) range")
    if end>int(time.time())//60*60:
        raise DataError("The requested range includes an unclosed or future minute")


def coverage(candles,start,end):
    missing=[]; next_time=start
    for candle in candles:
        if candle.time>next_time: missing.append([next_time,candle.time])
        next_time=candle.time+60
    if next_time<end: missing.append([next_time,end])
    return {"requested_start":start,"requested_end":end,"count":len(candles),"expected_count":(end-start)//60,
            "actual_start":candles[0].time if candles else None,"actual_end":candles[-1].time+60 if candles else None,
            "gaps":missing,"complete":not missing}


class DatasetStore:
    def __init__(self,root):
        self.root=Path(root)

    def save(self,market,symbol,start,end,trade,marks,funding,*,metadata,provenance):
        validate_range(market,symbol,start,end)
        def normalized(candles):
            return [{"time":c.time,**{key:float(getattr(c,key)) for key in ("open","high","low","close","volume")}} for c in candles]
        content={"trade":normalized(trade),"mark":normalized(marks),
                 "funding":[{"time":t,"rate":str(dec(funding[t]))} for t in sorted(funding)]}
        interval=int(metadata.get("instrument",{}).get("fundingInterval",0))*60
        expected=list(range(((start+interval-1)//interval)*interval,end,interval)) if interval else []
        funding_missing=[t for t in expected if t not in funding]
        manifest={"schema_version":1,"source":"Bybit public API","market":market,"symbol":symbol,
            "interval_seconds":60,"range":[start,end],"content_sha256":digest(content),
            "coverage":{"trade":coverage(trade,start,end),"mark":coverage(marks,start,end) if market=="linear" else None,
                "funding":{"count":len(funding),"expected_using_current_interval":len(expected),"missing_expected":funding_missing,
                    "complete_against_current_interval":bool(interval) and not funding_missing,
                    "assumption":"Current funding interval projected over range; historical interval changes are not independently verified"}},
            "metadata":metadata,"provenance":provenance,"storage":{"format":"parquet","pyarrow":importlib.metadata.version("pyarrow")}}
        dataset_id=digest(manifest)
        directory=self.root/dataset_id
        directory.mkdir(parents=True,exist_ok=True)
        hashes={}
        for name,rows in content.items():
            schema=pa.schema([("time",pa.int64()),("rate",pa.string())]) if name=="funding" else pa.schema(
                [("time",pa.int64())]+[(key,pa.float64()) for key in ("open","high","low","close","volume")])
            sink=pa.BufferOutputStream()
            pq.write_table(pa.Table.from_pylist(rows,schema=schema),sink,compression="zstd")
            raw=sink.getvalue().to_pybytes()
            write_new(directory/(name+".parquet"),raw)
            hashes[name]=hashlib.sha256(raw).hexdigest()
        manifest={**manifest,"id":dataset_id,"files_sha256":hashes}
        write_new(directory/"manifest.json",canonical(manifest))
        return manifest

    def load(self,dataset_id):
        if not re.fullmatch(r"[a-f0-9]{64}",dataset_id): raise DataError("Invalid dataset ID")
        directory=self.root/dataset_id
        manifest=json.loads((directory/"manifest.json").read_bytes())
        payload={k:v for k,v in manifest.items() if k not in ("id","files_sha256")}
        if digest(payload)!=dataset_id: raise DataError("Dataset manifest checksum mismatch")
        content={}
        for name in ("trade","mark","funding"):
            raw=(directory/(name+".parquet")).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=manifest["files_sha256"][name]: raise DataError("Dataset file checksum mismatch")
            content[name]=pq.read_table(pa.BufferReader(raw)).to_pylist()
        if digest(content)!=manifest["content_sha256"]: raise DataError("Normalized dataset checksum mismatch")
        return manifest,[Candle(**c) for c in content["trade"]],{c["time"]:Candle(**c) for c in content["mark"]},{c["time"]:c["rate"] for c in content["funding"]}

    def list(self):
        if not self.root.exists(): return []
        return [json.loads(p.read_bytes()) for p in self.root.glob("*/manifest.json")]

    def for_run(self,dataset_id,profile):
        manifest,trade,marks,funding=self.load(dataset_id)
        if manifest["market"]!=profile.market or manifest["symbol"]!=profile.symbol:
            raise DataError("Dataset market/instrument differs from the run profile")
        if not manifest["coverage"]["trade"]["complete"] and (profile.evaluation=="intrabar" or profile.gap_policy=="reject"):
            raise DataError("Trade coverage is incomplete for the requested range")
        if profile.market=="linear":
            if profile.mark_mode=="history" and not manifest["coverage"]["mark"]["complete"]:
                raise DataError("Mark coverage is incomplete")
            if profile.funding_mode=="history" and not manifest["coverage"]["funding"]["complete_against_current_interval"]:
                raise DataError("Funding coverage cannot be verified against the declared interval; choose an explicit cost assumption")
        return manifest,trade,marks,funding


def prepare_dataset(client,store,market,symbol,start,end,progress=lambda *_:None):
    validate_range(market,symbol,start,end)
    items=client.instruments(market,symbol)
    if len(items)!=1: raise DataError("Instrument is unavailable or ambiguous in current exchange metadata")
    instrument=items[0]
    progress("trade",0.1)
    trade=client.candles(market,symbol,start,end)
    if not trade: raise DataError("No trade history returned for the requested range")
    marks=[]; funding={}; risks=[]
    if market=="linear":
        progress("mark",0.5)
        marks=client.candles(market,symbol,start,end,mark=True)
        progress("funding",0.8)
        funding=client.funding(symbol,start,end)
        risks=client.get("/v5/market/risk-limit",{"category":"linear","symbol":symbol},cache=False).get("list",[])
    manifest=store.save(market,symbol,start,end,trade,marks,funding,
        metadata={"instrument":instrument,"current_risk_tiers":risks,
                  "historical_warning":"Current metadata is not historical precision, size limits or risk-tier evidence"},provenance=client.requests[:])
    progress("saved",1.0)
    return manifest


def runtime_snapshot():
    modules={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in Path(__file__).parent.glob("*.py")}
    packages={distribution.metadata["Name"].lower().replace("-","_"):distribution.version
              for distribution in importlib.metadata.distributions()}
    return {"python":platform.python_version(),"platform":platform.system(),"machine":platform.machine(),
            "packages":packages,"implementation_sha256":digest(modules)}


def run_manifest(strategy,profile,dataset):
    # Canonical copies keep the manifest independent of subsequent editor changes.
    payload=json.loads(canonical({"schema_version":1,"strategy":strategy,"profile":profile.snapshot(),
        "dataset":{"id":dataset["id"],"content_sha256":dataset["content_sha256"],"coverage":dataset["coverage"],
                   "source":dataset["source"],"range":dataset["range"]},"runtime":runtime_snapshot()}))
    return {**payload,"snapshot_sha256":digest(payload)}


def metadata_profile_fields(manifest):
    """Explicit current-metadata assumptions; never claim historical precision."""
    item=manifest["metadata"]["instrument"]
    lot=item["lotSizeFilter"]
    fields={"market":manifest["market"],"symbol":manifest["symbol"],"tick_size":item["priceFilter"]["tickSize"],
            "min_quantity":lot["minOrderQty"],"tier_assumption":"Current exchange metadata projected over the historical run; historical changes are unknown"}
    if manifest["market"]=="linear":
        fields.update(quantity_step=lot["qtyStep"],min_notional=lot["minNotionalValue"],max_quantity=lot["maxMktOrderQty"])
        tiers=manifest["metadata"]["current_risk_tiers"]
        tier=next((t for t in tiers if int(t["isLowestRisk"])==1),None)
        if tier is None: raise DataError("No lowest risk tier in current metadata")
        fields.update(maintenance_rate=str(tier["maintenanceMargin"]),max_notional=str(tier["riskLimitValue"]))
    else:
        fields.update(quantity_step=lot["basePrecision"],min_notional=lot["minOrderAmt"],
                      max_quantity=lot.get("maxMarketOrderQty",lot["maxOrderQty"]),max_notional=lot["maxOrderAmt"])
    return fields

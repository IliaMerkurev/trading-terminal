"""One cancellable public-data preparation task; never blocks IPC dispatch."""
import threading
from terminal.data import BybitClient,DatasetStore,prepare_dataset,validate_range


class DownloadManager:
    def __init__(self,root,client_factory=BybitClient):
        self.root=root
        self.client_factory=client_factory
        self.lock=threading.RLock()
        self.thread=None
        self.cancel_event=threading.Event()
        self.state={"status":"idle","stage":"","fraction":0}

    def start(self,market,symbol,start,end):
        validate_range(market,symbol,start,end)
        with self.lock:
            if self.thread and self.thread.is_alive(): raise ValueError("One historical download is already active")
            self.cancel_event=threading.Event()
            self.state={"status":"running","stage":"metadata","fraction":0,
                        "market":market,"symbol":symbol,"range":[start,end]}
            self.thread=threading.Thread(target=self._run,args=(market,symbol,start,end),daemon=True)
            self.thread.start()
            return dict(self.state)

    def _run(self,market,symbol,start,end):
        try:
            client=self.client_factory(self.root/"http-cache",cancel=self.cancel_event)
            result=prepare_dataset(client,DatasetStore(self.root/"datasets"),market,symbol,start,end,self._progress)
            with self.lock:
                self.state.update(status="cancelled" if self.cancel_event.is_set() else "completed",dataset_id=result["id"])
        except Exception as exc:
            with self.lock:
                self.state.update(status="cancelled" if self.cancel_event.is_set() else "failed",error=str(exc)[:1000])

    def _progress(self,stage,fraction):
        with self.lock: self.state.update(stage=stage,fraction=fraction)

    def status(self):
        with self.lock: return dict(self.state)

    def cancel(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                self.cancel_event.set()
                self.state["status"]="cancel_requested"
            return dict(self.state)

    def close(self):
        self.cancel()
        if self.thread: self.thread.join(timeout=25)

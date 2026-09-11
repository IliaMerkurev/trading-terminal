"""Versioned application IPC dispatch; no arbitrary methods, paths or code."""
from terminal.data import DatasetStore,canonical
from terminal.graph import validate_graph
from terminal.jobs import JobManager


class AppService:
    def __init__(self,root):
        self.jobs=JobManager(root)
        self.store=self.jobs.store
        self.datasets=DatasetStore(self.store.root/"datasets")

    def handle(self,message):
        request_id=message.get("id") if isinstance(message,dict) else None
        try:
            if not isinstance(message,dict) or set(message)!={"version","id","command","params"} or type(message["version"]) is not int or message["version"]!=1:
                raise ValueError("Invalid IPC version or envelope")
            if not isinstance(request_id,str) or len(request_id)>80 or not isinstance(message["params"],dict):
                raise ValueError("Invalid IPC identifier or parameters")
            if len(canonical(message))>1024*1024: raise ValueError("IPC request exceeds 1 MiB")
            p=message["params"]; command=message["command"]
            fields={"list_runs":set(),"run_status":{"run_id"},"result_page":{"run_id","kind","offset","limit"},
                "start_run":{"strategy","profile","dataset_id"},"cancel_run":{"run_id"},
                "list_strategies":set(),"save_graph":{"name","graph","layout","strategy_id"},
                "get_strategy":{"strategy_id"},"list_datasets":set(),"run_manifest":{"run_id"},
                "preview_native":{"document"},"save_native":{"name","document","strategy_id"},
                "trust_native":{"document","expected_sha256","acknowledge_user_permissions"}}
            if not isinstance(command,str) or command not in fields or set(p)!=fields[command]:
                raise ValueError("Unknown command or unexpected parameters")
            if command=="list_runs": result=self.store.recent()
            elif command=="run_status": result=self.jobs.status(p["run_id"])
            elif command=="run_manifest": result=self.store.get(p["run_id"])["manifest"]
            elif command=="result_page": result=self.store.page(**p)
            elif command=="start_run": result={"run_id":self.jobs.start(p["strategy"],p["profile"],p["dataset_id"])}
            elif command=="cancel_run": result=self.jobs.cancel(p["run_id"])
            elif command=="list_strategies": result=self.store.strategies()
            elif command=="get_strategy": result=self.store.strategy(p["strategy_id"])
            elif command=="save_graph":
                validate_graph(p["graph"])
                result={"strategy_id":self.store.save_strategy(p["name"],"graph",{"graph":p["graph"],"layout":p["layout"]},p["strategy_id"])}
            elif command in ("preview_native","save_native","trust_native"):
                from terminal.native import preview
                result=preview(p["document"])
                if command=="save_native":
                    result["strategy_id"]=self.store.save_strategy(p["name"],"native",p["document"],p["strategy_id"])
                elif command=="trust_native":
                    if p["acknowledge_user_permissions"] is not True or p["expected_sha256"]!=result["trust_sha256"]:
                        raise ValueError("Explicit confirmation must match the previewed Python source")
                    self.store.trust_native(result["trust_sha256"])
                result["trusted"]=self.store.is_trusted(result["trust_sha256"])
            elif command=="list_datasets":
                result=[{k:m[k] for k in ("id","market","symbol","range","coverage")} for m in self.datasets.list()]
            response={"version":1,"id":request_id,"type":"result","result":result}
            if len(canonical(response))>1024*1024: raise ValueError("Response exceeds IPC budget; request a smaller page")
            return response
        except Exception as exc:
            return {"version":1,"id":request_id,"type":"error","error":{"code":"REQUEST_FAILED","message":str(exc)[:2000]}}

    def close(self):
        self.jobs.close()

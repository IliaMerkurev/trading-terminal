"""Versioned application IPC dispatch; no arbitrary methods, paths or code."""
from terminal.data import DatasetStore,canonical,metadata_profile_fields
from terminal.downloads import DownloadManager
from terminal.archives import ArchiveManager
from terminal.comparison import compare_runs
from terminal.graph import validate_graph
from terminal.jobs import JobManager
from terminal.profile import Profile


class AppService:
    def __init__(self,root):
        self.jobs=JobManager(root)
        self.store=self.jobs.store
        self.datasets=DatasetStore(self.store.root/"datasets")
        self.downloads=DownloadManager(self.store.root)
        self.archives=ArchiveManager(self.store)
        from terminal.experiments import ExperimentManager
        self.experiments=ExperimentManager(self.jobs)
        from terminal.library_batches import LibraryBatchManager
        self.library_batches=LibraryBatchManager(self.jobs)
        from terminal.live import LiveManager
        self.live=LiveManager(self.store)

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
                "list_strategies":set(),"save_graph":{"name","graph","layout","strategy_id","profile"},
                "get_strategy":{"strategy_id"},"list_datasets":set(),"run_manifest":{"run_id"},
                "preview_native":{"document"},"save_native":{"name","document","strategy_id","profile"},
                "trust_native":{"document","expected_sha256","acknowledge_user_permissions"},
                "dataset_profile":{"dataset_id"},"download_start":{"market","symbol","start","end"},
                "download_status":set(),"download_cancel":set(),"chart_window":{"run_id","start","minutes"},"run_logs":{"run_id"},
                "compare_runs":{"run_ids"},"archive_export":{"strategy","profile","run_ids"},"archive_begin":{"size"},
                "archive_append":{"upload_id","offset","data"},"archive_finish":{"upload_id"},"archive_cancel":set()}
            experiment_fields={'strategy_id','dataset_id','profile','is_range','oos_range','axes'}
            fields.update(experiment_fields={'strategy_id'},experiment_preview=experiment_fields,experiment_start=experiment_fields,
                list_experiments=set(),experiment_status={'experiment_id'},experiment_cancel={'active_id'},
                experiment_freeze={'experiment_id','ordinal'},experiment_copy={'experiment_id','ordinal'},experiment_validate={'validation_id'},
                start_window_run={'strategy','profile','dataset_id','window'})
            fields.update(live_start={'strategy_id','profile','paper','channels'},live_status=set(),live_pause=set(),
                          live_resume={'session_id','revalidate_paper'},live_replay={'session_id'},live_select={'session_id'},
                          notification_test={'channel'},telegram_configure={'token','chat_id'},telegram_clear=set())
            fields.update(live_start_terminal={'strategy_id','profile','paper','channels','execution_source'},
                          live_chart={'session_id'},paper_manual={'session_id','action','request_id'})
            fields.update(market_open={'market','symbol'},market_close=set(),market_chart={'market','symbol','minutes','before'})
            fields.update(managed_experiment_fields={'strategy_id','profile'})
            fields.update(paper_start_manual={'profile'})
            fields.update(paper_lifecycle={'session_id','before','limit'})
            fields.update(run_history={'before','limit'})
            fields.update(replay_status={'replay_id'},replay_cancel={'replay_id'})
            fields.update(library_catalog=set(), library_copy={'entry_id','version','minutes','parameters'})
            library_fields={'selections','dataset_id','profile','start','end','interval','spot_dataset_id'}
            fields.update(library_batch_preview=library_fields,library_batch_start=library_fields|{'expected_contract'},
                          library_batch_status={'batch_id'},library_batch_resume={'batch_id'},
                          library_batch_cancel={'active_id'},library_batches=set())
            fields.update(library_batch_equity={'batch_id','ordinal'},library_validation_freeze={'batch_id','ordinal','dataset_id','start','end','spot_dataset_id'},library_validation_start={'batch_id'})
            if not isinstance(command,str) or command not in fields or set(p)!=fields[command]:
                raise ValueError("Unknown command or unexpected parameters")
            if command in ('live_start','live_start_terminal'):result=self.live.start(**p)
            elif command=='market_open':result=self.live.market_open(**p)
            elif command=='market_close':result=self.live.market_close()
            elif command=='market_chart':result=self.live.chart_history.request(**p)
            elif command=='live_chart':result=self.live.journal.chart(**p)
            elif command=='paper_manual':result=self.live.manual(**p)
            elif command=='paper_start_manual':result=self.live.start_manual(**p)
            elif command=='paper_lifecycle':result=self.live.journal.paper_lifecycle(**p)
            elif command=='live_status':result=self.live.status()
            elif command=='live_pause':result=self.live.pause()
            elif command=='live_select':result=self.live.select(**p)
            elif command=='live_resume':result=self.live.resume(**p)
            elif command=='live_replay':result=self.jobs.start_replay(**p)
            elif command=='replay_status':result=self.jobs.replay_status(**p)
            elif command=='replay_cancel':result=self.jobs.cancel_replay(**p)
            elif command=='notification_test':result=self.live.test_notification(**p)
            elif command=='telegram_configure':
                self.live.telegram.credentials.save(p['token'],p['chat_id']);result=self.live.telegram.status()
            elif command=='telegram_clear':
                self.live.telegram.credentials.clear();result=self.live.telegram.status()
            elif command=='library_catalog':
                from terminal.library import catalog
                result=catalog()
            elif command=='library_copy':
                from terminal.library import create_copy
                result=create_copy(self.store,**p)
            elif command=='library_batch_preview':result=self.library_batches.preview(**p)
            elif command=='library_batch_start':result=self.library_batches.start(**p)
            elif command=='library_batch_status':result=self.library_batches.get(**p)
            elif command=='library_batch_resume':result=self.library_batches.resume(**p)
            elif command=='library_batch_cancel':result=self.library_batches.cancel(**p)
            elif command=='library_batches':result=self.library_batches.recent()
            elif command=='library_validation_freeze':result=self.library_batches.freeze_validation(**p)
            elif command=='library_validation_start':result=self.library_batches.start_validation(**p)
            elif command=='library_batch_equity':result=self.library_batches.equity(**p)
            elif command=="list_runs": result=self.store.recent()
            elif command=='run_history':result=self.store.history_page(**p)
            elif command=="run_status": result=self.jobs.status(p["run_id"])
            elif command=="run_logs": result=self.jobs.logs(p["run_id"])
            elif command=="run_manifest": result=self.store.get(p["run_id"])["manifest"]
            elif command=="result_page": result=self.store.page(**p)
            elif command=="chart_window": result=self.store.chart_window(**p)
            elif command=="start_run": result={"run_id":self.jobs.start(p["strategy"],p["profile"],p["dataset_id"])}
            elif command=="cancel_run": result=self.jobs.cancel(p["run_id"])
            elif command=="list_strategies": result=self.store.strategies()
            elif command=="get_strategy": result=self.store.strategy(p["strategy_id"])
            elif command=="save_graph":
                validate_graph(p["graph"],allow_incomplete=True)
                profile=Profile(**p['profile']).snapshot()
                result={"strategy_id":self.store.save_strategy(p["name"],"graph",{"graph":p["graph"],"layout":p["layout"]},p["strategy_id"],profile=profile)}
            elif command in ("preview_native","save_native","trust_native"):
                from terminal.native import preview
                result=preview(p["document"])
                if command=="save_native":
                    profile=Profile(**p['profile']).snapshot()
                    result["strategy_id"]=self.store.save_strategy(p["name"],"native",p["document"],p["strategy_id"],profile=profile)
                elif command=="trust_native":
                    if p["acknowledge_user_permissions"] is not True or p["expected_sha256"]!=result["trust_sha256"]:
                        raise ValueError("Explicit confirmation must match the previewed Python source")
                    self.store.trust_native(result["trust_sha256"])
                result["trusted"]=self.store.is_trusted(result["trust_sha256"])
            elif command=="list_datasets":
                result=[{k:m[k] for k in ("id","market","symbol","range","coverage","source")} for m in self.datasets.list()]
            elif command=="dataset_profile": result=metadata_profile_fields(self.datasets.describe(p["dataset_id"]))
            elif command=="download_start": result=self.downloads.start(**p)
            elif command=="download_status": result=self.downloads.status()
            elif command=="download_cancel": result=self.downloads.cancel()
            elif command=="compare_runs": result=compare_runs(self.store,p['run_ids'])
            elif command=="archive_export": result=self.archives.export(**p)
            elif command=="archive_begin": result=self.archives.begin(**p)
            elif command=="archive_append": result=self.archives.append(**p)
            elif command=="archive_finish": result=self.archives.finish(**p)
            elif command=="archive_cancel": result=self.archives.cancel()
            elif command in ('experiment_fields','managed_experiment_fields'):result=self.experiments.fields(**p)
            elif command=='experiment_preview':result=self.experiments.preview(**p)
            elif command=='experiment_start':result=self.experiments.start(**p)
            elif command=='list_experiments':result=self.experiments.recent()
            elif command=='experiment_status':result=self.experiments.get(**p)
            elif command=='experiment_cancel':result=self.experiments.cancel(**p)
            elif command=='experiment_freeze':result=self.experiments.freeze(**p)
            elif command=='experiment_copy':result=self.experiments.copy_candidate(**p)
            elif command=='experiment_validate':result=self.experiments.validate(**p)
            elif command=='start_window_run':
                from terminal.experiments import validate_range
                window=p['window'];manifest=self.datasets.describe(p['dataset_id'])
                if not isinstance(window,dict) or set(window)!={'start','end','warmup_start'}:raise ValueError('Invalid window fields')
                validate_range([window['start'],window['end']],manifest['range'],'Trading window')
                if type(window['warmup_start']) is not int or window['warmup_start']%60 or not manifest['range'][0]<=window['warmup_start']<=window['start']:raise ValueError('Invalid warmup range')
                strategy=p['strategy']
                if strategy.get('engine'):
                    from terminal.library import native_window_document
                    strategy=native_window_document(strategy,window['start'])
                result={'run_id':self.jobs.start(strategy,p['profile'],p['dataset_id'],research={'window':window})}
            response={"version":1,"id":request_id,"type":"result","result":result}
            if len(canonical(response))>1024*1024: raise ValueError("Response exceeds IPC budget; request a smaller page")
            return response
        except Exception as exc:
            return {"version":1,"id":request_id,"type":"error","error":{"code":"REQUEST_FAILED","message":str(exc)[:2000]}}

    def close(self):
        self.live.close()
        self.library_batches.close()
        self.experiments.close()
        self.jobs.close()
        self.downloads.close()

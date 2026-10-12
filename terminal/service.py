"""Versioned application IPC dispatch; no arbitrary methods, paths or code."""
from terminal.data import DatasetStore,canonical,metadata_profile_fields
from terminal.downloads import DownloadManager
from terminal.archives import ArchiveManager
from terminal.comparison import compare_runs
from terminal.graph import validate_graph
from terminal.jobs import JobManager
from terminal.profile import Profile
from terminal.storage import identifier


class AppService:
    def __init__(self,root):
        self.jobs=JobManager(root)
        self.store=self.jobs.store
        self.datasets=DatasetStore(self.store.root/"datasets")
        self.downloads=DownloadManager(self.store.root)
        self.archives=ArchiveManager(self.store,self.jobs)
        from terminal.archive_export import ExportManager
        self.exports=ExportManager(self.jobs)
        from terminal.experiments import ExperimentManager
        self.experiments=ExperimentManager(self.jobs)
        from terminal.library_batches import LibraryBatchManager
        self.library_batches=LibraryBatchManager(self.jobs)
        from terminal.observations import Observations
        self.observations=Observations(self.store,self.datasets)
        from terminal.chart_reads import ChartReads
        self.chart_reads=ChartReads(self)
        from terminal.live import LiveManager
        self.live=LiveManager(self.store)
        from terminal.display_indicators import DisplayIndicators
        self.display_indicators=DisplayIndicators(self.live.chart_history)
        from terminal.indicator_transport import IndicatorTransport
        self.indicator_transport=IndicatorTransport()
        from terminal.chart_drawings import ChartDrawings
        self.chart_drawings=ChartDrawings(self.store)
        from terminal.chart_presets import ChartPresets
        self.chart_presets=ChartPresets(self.display_indicators)
        from terminal.indicator_alert_runtime import IndicatorAlertRuntime
        self.indicator_alerts=IndicatorAlertRuntime(self.display_indicators)
        from terminal.indicator_alert_history import IndicatorAlertHistory
        self.indicator_history=IndicatorAlertHistory(self.indicator_alerts.store)

    def handle(self,message):
        request_id=message.get("id") if isinstance(message,dict) else None
        try:
            if not isinstance(message,dict) or set(message)!={"version","id","command","params"} or type(message["version"]) is not int or message["version"]!=1:
                raise ValueError("Invalid IPC version or envelope")
            if not isinstance(request_id,str) or len(request_id)>80 or not isinstance(message["params"],dict):
                raise ValueError("Invalid IPC identifier or parameters")
            if len(canonical(message))>1024*1024: raise ValueError("IPC request exceeds 1 MiB")
            p=message["params"]; command=message["command"]
            fields={"scheduler_status":set(),"platform_capabilities":set(),"list_runs":set(),"run_status":{"run_id"},"result_page":{"run_id","kind","offset","limit"},
                "start_run":{"strategy","profile","dataset_id"},"cancel_run":{"run_id"},
                "list_strategies":set(),"save_graph":{"name","graph","layout","strategy_id","profile"},
                "get_strategy":{"strategy_id"},"list_datasets":set(),"run_manifest":{"run_id"},
                "preview_native":{"document"},"save_native":{"name","document","strategy_id","profile"},
                "trust_native":{"document","expected_sha256","acknowledge_user_permissions"},
                "dataset_profile":{"dataset_id"},"download_start":{"market","symbol","start","end"},
                "download_status":set(),"download_cancel":set(),"run_logs":{"run_id"},
                "compare_runs":{"run_ids"},"archive_export_start":{"request_id","strategy","profile","run_ids"},"archive_export_status":{"export_id"},"archive_export_cancel":{"export_id"},"archive_export_list":set(),"archive_begin":{"size"},
                "archive_import_status":{"operation_id"},"archive_import_list":{"before","limit"},"archive_import_cancel":{"operation_id"},
                "archive_append":{"upload_id","offset","data"},"archive_finish":{"upload_id"},"archive_cancel":set()}
            fields.update(archive_recovery_begin={'operation_id','size'},archive_recovery_finish={'upload_id'},archive_recovery_cancel={'upload_id'})
            fields.update(archive_import_start={'operation_id'},archive_import_resume={'operation_id','expected_revision','attempt_key'})
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
            fields.update(chart_drawing_settings={'market','symbol','source'},chart_drawing_save={'market','symbol','source','drawings','revision'})
            fields.update(chart_preset_list={'trashed'},chart_preset_get={'preset_id','revision'},
                          chart_preset_save_current={'name','source','market','symbol','revision'},
                          chart_preset_duplicate={'preset_id','revision','name'},chart_preset_rename={'preset_id','revision','name'},
                          chart_preset_trash={'preset_id','revision'},chart_preset_restore={'preset_id','revision'})
            fields.update(chart_indicator_page={'snapshot_id','index'}, chart_indicator_upload_begin={'size','sha256'}, chart_indicator_upload_append={'upload_id','offset','text'}, chart_indicator_upload_finish={'upload_id'})
            fields.update(chart_indicator_settings={'market','symbol','source'},chart_indicator_save={'market','symbol','instances','revision','source'},chart_indicator_read={'market','symbol','minutes','start','end','revision','reanchor','source'})
            fields.update(market_preferences=set(),market_open={'market','symbol','source'},market_close=set(),market_chart={'market','symbol','minutes','before','source'})
            fields.update(managed_experiment_fields={'strategy_id','profile'})
            fields.update(paper_start_manual={'profile'})
            fields.update(paper_lifecycle={'session_id','before','limit'})
            fields.update(run_history={'before','limit'})
            fields.update(history_prepare={'market','symbol','start','end','minutes'})
            fields.update(replay_status={'replay_id'},replay_cancel={'replay_id'})
            fields.update(library_catalog=set(), library_copy={'entry_id','version','minutes','parameters'})
            fields.update(library_warmup={'selections','dataset_id'},library_batch_history={'before'})
            library_fields={'selections','dataset_id','profile','start','end','interval','spot_dataset_id'}
            fields.update(library_batch_preview=library_fields,library_batch_start=library_fields|{'expected_contract'},
                          library_batch_status={'batch_id'},library_batch_resume={'batch_id'},
                          library_batch_cancel={'active_id'},library_batches=set())
            fields.update(library_batch_equity={'batch_id','ordinal'},library_validation_freeze={'batch_id','ordinal','dataset_id','start','end','spot_dataset_id'},library_validation_start={'batch_id'})
            fields.update(observation_history={'before'},
                          observation_get={'observation_id','revision'},
                          observation_save_start={'request_id','expected_source','observation_id','expected_revision','dataset_id','start','end','hypothesis','falsification'})
            fields.update(chart_read_start={'request_id','view_id','generation','surface','query'},chart_read_status={'request_id'},chart_read_cancel={'request_id'},chart_read_activity=set(),observation_save_history=set())
            alert_fields = {
                'alert_history_preview': ({'rule_id','revision'}, set()),
                'alert_history_start': ({'request_id','rule_id','revision','definition_hash','start','end'}, set()),
                'alert_history_request': ({'request_id'}, set()),
                'alert_history_get': ({'run_id'}, set()),
                'alert_history_cancel': ({'run_id'}, set()),
                'alert_history_list': (set(), {'after','limit'}),
                'alert_history_matches': ({'run_id'}, {'after','limit'}),
                'alert_history_chart': ({'run_id'}, {'start_index','limit','target_confirmed_at'}),
                'alert_history_row': ({'run_id'}, {'confirmed_at','raw_open_time'}),
                'alert_event_evidence': ({'event_id'}, {'before','after'}),
                'alert_catalog': (set(), set()),
                'alert_request': ({'request_id'}, set()),
                'alert_session_init': ({'session_id'}, set()),
                'alert_context': ({'session_id','context_revision','source','market','symbol','minutes','visible'}, set()),
                'alert_preview': ({'source','market','symbol','minutes','settings_revision','conditions'}, {'combine'}),
                'alert_create': ({'request_id','name','definition','definition_hash','settings_revision'}, set()),
                'alert_list': (set(), {'trashed','after','limit'}),
                'alert_get': ({'rule_id'}, {'revision'}),
                'alert_rebind': ({'rule_id','revision','definition','definition_hash','settings_revision'}, set()),
                'alert_rename': ({'rule_id','revision','name'}, set()),
                'alert_archive': ({'rule_id','revision'}, set()),
                'alert_restore': ({'rule_id','revision'}, set()),
                'alert_arm': ({'request_id','rule_id','revision','definition_hash','session_id','context_revision','reviewed'}, set()),
                'alert_status': (set(), {'rule_id'}), 'alert_pause': (set(), {'rule_id'}),
                'alert_events': (set(), {'after','limit','unread_only'}),
                'alert_event': ({'event_id'}, set()),
                'alert_mark_read': ({'event_id'}, {'is_read'}),
                'alert_claim_banner': ({'event_id'}, set()),
            }
            # Optional fields stay optional under the strict exact-key envelope.
            if isinstance(command, str) and command in alert_fields:
                required, optional = alert_fields[command]
                fields[command] = required | (optional & set(p))
            if command=='chart_indicator_read' and 'price_style' in p:fields[command].add('price_style')
            if command=='chart_indicator_save' and 'pane_layout' in p:fields[command].add('pane_layout')
            if command=='archive_import_cancel' and 'attempt_key' in p:fields[command].add('attempt_key')
            if command in ('library_batch_preview','library_batch_start') and 'spot_benchmark' in p:fields[command]=fields[command]|{'spot_benchmark'}
            if command=='library_batch_start' and 'observation' in p:fields[command].add('observation')
            fields['research_display_incomplete']=set()
            fields['research_displayed']={'presentation_id','reference','viewport'}
            fields['research_evidence_preview']={'dataset_id','start','end'}
            fields.update(library_batch_metadata={'batch_id'},library_batch_save_metadata={'batch_id','name','notes','expected_revision'})
            if command=='library_batch_history' and 'query' in p:fields[command].add('query')
            if command=='library_copy' and 'profile' in p:fields['library_copy'].add('profile')
            if command in ('market_open','market_chart','chart_indicator_settings','chart_indicator_save','chart_indicator_read','chart_drawing_settings','chart_drawing_save') and 'source' not in p:
                fields[command].discard('source')
            if not isinstance(command,str) or command not in fields or set(p)!=fields[command]:
                raise ValueError("Unknown command or unexpected parameters")
            if command in ('library_validation_freeze','experiment_freeze'):
                from terminal.displayed_evidence import persist_warning
                persist_warning(self.store)
            if command=='platform_capabilities':
                from terminal.process_lifecycle import platform_capabilities
                result=platform_capabilities()
            elif command=='scheduler_status':result={**self.jobs.scheduler_status(),'verified_reads':self.chart_reads.activity()}
            elif command in ('live_start','live_start_terminal'):result=self.live.start(**p)
            elif command in alert_fields:
                methods = {
                    'alert_history_preview': self.indicator_history.preview,
                    'alert_history_start': self.indicator_history.start,
                    'alert_history_request': self.indicator_history.request,
                    'alert_history_get': self.indicator_history.get,
                    'alert_history_cancel': self.indicator_history.cancel,
                    'alert_history_list': self.indicator_history.list,
                    'alert_history_matches': self.indicator_history.matches,
                    'alert_history_chart': self.indicator_history.chart,
                    'alert_history_row': self.indicator_history.row,
                    'alert_event_evidence': self.indicator_history.event_evidence,
                    'alert_catalog': self.indicator_alerts.catalog,
                    'alert_request': self.indicator_alerts.request,
                    'alert_session_init': self.indicator_alerts.session_init,
                    'alert_context': self.indicator_alerts.register_context,
                    'alert_preview': self.indicator_alerts.preview,
                    'alert_create': self.indicator_alerts.create,
                    'alert_list': self.indicator_alerts.list,
                    'alert_get': self.indicator_alerts.get,
                    'alert_rebind': self.indicator_alerts.rebind,
                    'alert_rename': self.indicator_alerts.rename,
                    'alert_archive': self.indicator_alerts.archive,
                    'alert_restore': self.indicator_alerts.restore,
                    'alert_arm': self.indicator_alerts.arm,
                    'alert_status': self.indicator_alerts.status,
                    'alert_pause': self.indicator_alerts.pause,
                    'alert_events': self.indicator_alerts.store.events,
                    'alert_event': self.indicator_alerts.store.event,
                    'alert_mark_read': self.indicator_alerts.store.mark_read,
                    'alert_claim_banner': lambda event_id: dict(claimed=self.indicator_alerts.store.claim_banner(event_id)),
                }
                result = methods[command](**p)
            elif command=='market_preferences':result=self.live.market_preferences()
            elif command=='market_open':result=self.live.market_open(**p)
            elif command=='market_close':
                self.indicator_alerts.pause()
                result=self.live.market_close()
            elif command=='chart_drawing_settings':result=self.chart_drawings.settings(**p)
            elif command=='chart_drawing_save':result=self.chart_drawings.save(**p)
            elif command=='chart_preset_list':result=self.chart_presets.list(**p)
            elif command=='chart_preset_get':result=self.chart_presets.get(**p)
            elif command=='chart_preset_save_current':result=self.chart_presets.save_current(**p)
            elif command=='chart_preset_duplicate':result=self.chart_presets.duplicate(**p)
            elif command=='chart_preset_rename':result=self.chart_presets.rename(**p)
            elif command=='chart_preset_trash':result=self.chart_presets.trash(**p)
            elif command=='chart_preset_restore':result=self.chart_presets.restore(**p)
            elif command=='chart_indicator_settings':result=self.display_indicators.settings(**p)
            elif command=='chart_indicator_save':result=self.indicator_alerts.save_settings(**p)
            elif command=='chart_indicator_read':result=self.display_indicators.read(**p)
            elif command=='chart_indicator_page':result=self.indicator_transport.page(**p)
            elif command=='chart_indicator_upload_begin':result=self.indicator_transport.upload_begin(**p)
            elif command=='chart_indicator_upload_append':result=self.indicator_transport.upload_append(**p)
            elif command=='chart_indicator_upload_finish':result=self.indicator_alerts.save_settings(**self.indicator_transport.upload_finish(**p))
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

            elif command=='observation_history':result=self.observations.history(**p)
            elif command=='observation_get':result=self.observations.get(**p)
            elif command=='chart_read_start':result=self.chart_reads.start(**p)
            elif command=='chart_read_status':result=self.chart_reads.status(**p)
            elif command=='chart_read_cancel':result=self.chart_reads.cancel(**p)
            elif command=='chart_read_activity':result=self.chart_reads.activity()
            elif command=='observation_save_history':result=self.chart_reads.save_history()
            elif command=='observation_save_start':result=self.chart_reads.save(**p)
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
            elif command=='library_batch_metadata':result=self.library_batches.metadata(**p)
            elif command=='library_batch_save_metadata':result=self.library_batches.save_metadata(**p)
            elif command=='library_batch_history':result=self.library_batches.history_page(**p)
            elif command=='library_validation_freeze':result=self.library_batches.freeze_validation(**p)
            elif command=='library_validation_start':result=self.library_batches.start_validation(**p)
            elif command=='library_batch_equity':result=self.library_batches.equity(**p)
            elif command=="list_runs": result=self.store.recent()
            elif command=='run_history':result=self.store.history_page(**p)
            elif command=="run_status": result=self.jobs.status(p["run_id"])
            elif command=="run_logs": result=self.jobs.logs(p["run_id"])
            elif command=="run_manifest": result=self.store.get(p["run_id"])["manifest"]
            elif command=="result_page": result=self.store.page(**p)

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
                result=[{**{k:m[k] for k in ("id","market","symbol","range","coverage","source")},'interval_seconds':m.get('interval_seconds',60)} for m in self.datasets.list()]
            elif command=="dataset_profile": result=metadata_profile_fields(self.datasets.describe(p["dataset_id"]))
            elif command=='library_warmup': result=self.library_batches.warmup(**p)
            elif command in ("download_start","history_prepare"): result=self.downloads.start(**p)
            elif command=="download_status": result=self.downloads.status()
            elif command=="download_cancel": result=self.downloads.cancel()
            elif command=="compare_runs": result=compare_runs(self.store,p['run_ids'])
            elif command=="archive_export_start": result=self.exports.start(**p)
            elif command=="archive_export_status": result=self.exports.status(**p)
            elif command=="archive_export_cancel": result=self.exports.cancel(**p)
            elif command=="archive_export_list": result=self.exports.recent()
            elif command=="archive_begin": result=self.archives.begin(**p)
            elif command=="archive_append": result=self.archives.append(**p)
            elif command=='archive_recovery_begin':result=self.archives.recovery_begin(**p)
            elif command=='archive_recovery_cancel':result=self.archives.recovery_cancel(**p)
            elif command=='archive_recovery_finish':result=self.archives.recovery_finish(**p)
            elif command=='archive_import_start':result=self.archives.start(**p)
            elif command=='archive_import_resume':result=self.archives.resume(**p)
            elif command=="archive_finish": result=self.archives.finish(**p)
            elif command=="archive_cancel": result=self.archives.cancel()
            elif command=="archive_import_cancel": result=self.archives.cancel(identifier(p["operation_id"]),p.get("attempt_key"))
            elif command=="archive_import_status": result=self.archives.status(**p)
            elif command=="archive_import_list": result=self.archives.recent(**p)
            elif command in ('experiment_fields','managed_experiment_fields'):result=self.experiments.fields(**p)
            elif command=='research_display_incomplete':
                from terminal.displayed_evidence import mark_incomplete,persist_warning
                mark_incomplete(self.store);persist_warning(self.store);result={'recorded':True}
            elif command=='research_displayed':
                from terminal.displayed_evidence import record
                result=record(self,**p)
            elif command=='research_evidence_preview':
                from terminal.research_evidence import preview
                result=preview(self.jobs,**p)
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
            if command in ('chart_indicator_settings','chart_indicator_save','chart_indicator_read','chart_indicator_upload_finish','chart_preset_list','chart_preset_get'):
                result=self.indicator_transport.pack(result)
            response={"version":1,"id":request_id,"type":"result","result":result}
            if len(canonical(response))>1024*1024: raise ValueError("Response exceeds IPC budget; request a smaller page")
            return response
        except Exception as exc:
            return {"version":1,"id":request_id,"type":"error","error":{"code":"REQUEST_FAILED","message":str(exc)[:2000]}}

    def close(self):
        errors=[]
        def attempt(action):
            try:action()
            except Exception as exc:errors.append(exc)
        # A still-running alert replay retains all dependencies and workspace
        # ownership. Do not close its database/history under a timed-out worker.
        self.indicator_history.close()
        self.indicator_alerts.close()
        attempt(self.live.close)
        attempt(self.library_batches.close)
        attempt(self.experiments.close)
        # The calculation process is only one workspace owner. Defer unlocking
        # until live/history/download threads have also actually stopped.
        attempt(self.display_indicators.close)
        attempt(self.indicator_transport.close)
        attempt(self.chart_reads.close)
        attempt(self.exports.close)
        attempt(self.archives.close)
        attempt(lambda:self.jobs.close(release_workspace=False))
        attempt(self.downloads.close)
        threads=(self.display_indicators.thread,self.live.thread,self.live.warmup_thread,self.live.hub.thread,self.live.chart_history.thread,
                 self.live.delivery_thread,self.downloads.thread)
        if self.chart_reads.active or self.exports.active or self.archives.worker.active or self.jobs.active or self.library_batches.active or self.experiments.active or any(t and t.is_alive() for t in threads):
            errors.append(RuntimeError('Service shutdown is incomplete; workspace ownership is retained'))
        else:attempt(self.jobs.close)
        if errors:raise ExceptionGroup('Service shutdown cleanup failed',errors)

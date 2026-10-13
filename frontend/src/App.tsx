import {RuleStrategyProvider} from './RuleStrategyConversion';
import FrozenRuleDetails from './FrozenRuleDetails';
import {AlertResearchProvider} from './AlertResearch';
import {AlertSessionProvider} from './AlertSession';
import {RunProgress} from './RunProgress';
import {DisplayedMetrics,DisplayTrackingNotice} from './DisplayedEvidence';
import Observations,{type HistoryRequest,type ObservationContext} from './Observations';
import { useEffect, useRef, useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { invoke } from '@tauri-apps/api/core';
import { api, transportCapabilities, productVersion as getProductVersion } from './api';
import BrowserServiceControls, {hasActiveWork} from './BrowserServiceControls';
import GraphEditor from './GraphEditor';
import DownloadPanel from './DownloadPanel';
import TradeReview from './TradeReview';
import RunLogs from './RunLogs';
import ComparisonPanel from './ComparisonPanel';
import ProjectTransfer from './ProjectTransfer';
import RunSnapshot from './RunSnapshot';
import Experiments from './Experiments';
import Live from './Live';
import {poll} from './poll';
import {useRunHistory} from './useRunHistory';
import {createNode,graphProblems,isTextEditing,shortcutKey} from './editor';
import {useStrategyDraft,type StrategyDraft,type DraftIntent} from './useStrategyDraft';
import StrategyDraftPrompt from './StrategyDraftPrompt';
import { catalog, defaultProfile, exampleGraph, labels, type Graph, type Layout, type NodeKind, type Profile } from './model';
import PositionSettings from './PositionSettings';
import StrategyLibrary from './StrategyLibrary';
import './research.css';
import './market-workspace.css';
import HistoryWorkspace from './HistoryWorkspace';
import BacktestHistory from './BacktestHistory';
import {historyMatchesProfile} from './historyCompatibility';
import StorageFailureNotice from './StorageFailureNotice';
import {storageFailureReleased} from './storageSafety';

const nativeExample=()=>({version:1,engine:'nautilus_trader',engine_version:'1.231.0',
  source:'from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig\n',
  class_name:'EMACross',config_class:'EMACrossConfig',config:{instrument_id:'$instrument',bar_type:'$bar:1',trade_size:'0.001',fast_ema_period:10,slow_ema_period:20,request_bars:false,subscribe_trade_ticks:false,close_positions_on_stop:true},
  bar_minutes:[1],dependencies:{nautilus_trader:'1.231.0'},provenance:'Installed official NautilusTrader EMACross example (LGPLv3); imported without copying its source.'});

export function savedRunDate(selectedRun:any,runs:any[]):string|null{
  const value=[selectedRun?.created_at,runs.find(run=>run.id===selectedRun?.id)?.created_at]
    .find(value=>typeof value==='string'&&Number.isFinite(Date.parse(value)));
  return value?new Date(value).toLocaleString():null;
}

export default function App(){return <AlertSessionProvider><AlertResearchProvider><AppContent/></AlertResearchProvider></AlertSessionProvider>;}

function AppContent(){
  const transport=transportCapabilities();
  const [serviceStopped,setServiceStopped]=useState(false);
  const [productVersion,setProductVersion]=useState('');
  const [platformCapabilities,setPlatformCapabilities]=useState<any>(null);
  useEffect(()=>{if(transport.localService)api('platform_capabilities').then(setPlatformCapabilities).catch(()=>{});},[]);
  const nativeUnavailable=platformCapabilities?.native_execution?.available===false;
  useEffect(()=>{if(transport.localService)getProductVersion().then(v=>setProductVersion(v.replace(/\.0-dev$/,'-dev'))).catch(()=>{});},[]);
  const [tab,setTab]=useState('Library'),[left,setLeft]=useState(true),[right,setRight]=useState(true);
  const mode=['Strategy','Backtest','Experiments'].includes(tab)?'pro':'research';
  const [researchProfile,setResearchProfile]=useState<Profile>({...defaultProfile,sizing:'percent',allocation:'95',slippage:'0.0005',execution_minutes:60});
  const [researchDataset,setResearchDataset]=useState<HistoryRequest>({id:'',request:0});
  const [historyOrigin,setHistoryOrigin]=useState('Library'),[historyContext,setHistoryContext]=useState<Profile|null>(null),[historyLater,setHistoryLater]=useState(false);
  const draft=useStrategyDraft(()=>({name:'SMA research example',strategyId:null,kind:'graph',graph:exampleGraph(),layout:{close:{x:30,y:90},mean:{x:280,y:230},above:{x:550,y:50},below:{x:550,y:320}},profile:{...defaultProfile},native:nativeExample(),nativeConfig:JSON.stringify(nativeExample().config,null,2),nativeDependencies:JSON.stringify(nativeExample().dependencies,null,2)}),async snapshot=>{
    const {name,kind,graph,layout,strategyId,profile,native,nativeConfig,nativeDependencies}=snapshot;
    const result=kind==='graph'?await api<any>('save_graph',{name,graph,layout,strategy_id:strategyId,profile}):await api<any>('save_native',{name,document:{...native,config:JSON.parse(nativeConfig),dependencies:JSON.parse(nativeDependencies)},strategy_id:strategyId,profile});
    if(typeof result?.strategy_id!=='string'||!result.strategy_id)throw Error('The save response did not identify a saved strategy.');
    void refresh().catch(e=>setError('Strategy saved, but the library could not refresh. '+String(e)));
    return result.strategy_id;
  });
  const {editor}=draft,{name,strategyId,kind,profile,native,nativeConfig,nativeDependencies}=draft.draft;
  const setName=(value:string)=>draft.set('name',value),setNative=(value:any)=>draft.set('native',value),setNativeConfig=(value:string)=>draft.set('nativeConfig',value),setNativeDependencies=(value:string)=>draft.set('nativeDependencies',value);
  const setProfile=(value:Profile|((previous:Profile)=>Profile))=>draft.set('profile',value);
  const {graph,layout}=editor;
  const [locate,setLocate]=useState<{id:string;request:number}|null>(null);
  const problems=graphProblems(graph);
  const [selectedNode,setSelectedNode]=useState<string|null>(null),[addType,setAddType]=useState<NodeKind>('ema');
  const [marketProfile,setMarketProfile]=useState<Profile>({...defaultProfile});
  const [marketVisited,setMarketVisited]=useState(false),[marketView,setMarketView]=useState<'live'|'saved'>('live'),[observationsVisited,setObservationsVisited]=useState(false);
  const [marketFocus,setMarketFocus]=useState(false);
  const marketVisible=tab==='Live'&&marketView==='live';
  const marketFocused=marketVisible&&marketFocus;
  useEffect(()=>{if(!marketVisible)setMarketFocus(false);},[marketVisible]);
  const [observationRequest,setObservationRequest]=useState<{dataset?:string;id?:string;revision?:number;request:number}>({request:0});
  const [preferredBatch,setPreferredBatch]=useState({id:'',request:0});
  function observe(id:string,revision?:number,dataset?:string){setObservationsVisited(true);setMarketView('saved');setObservationRequest(v=>({id:id||undefined,revision,dataset,request:v.request+1}));setTab('Live');}
  function testObservation(o:ObservationContext){const minutes=o.source.interval_seconds/60;
    // The shared profile is validated before each selected card supplies its own timeframe.
    setResearchProfile(p=>({...p,market:o.source.market,symbol:o.source.symbol,execution_minutes:minutes,
      primary_minutes:p.primary_minutes%minutes===0?p.primary_minutes:minutes}));setResearchDataset(v=>({id:o.source.id,request:v.request+1,observation:o}));setTab('Library');}
  function navigate(destination:string){if(destination==='Live'&&marketView==='live')setMarketVisited(true);if(destination==='History'){setHistoryContext(null);setHistoryLater(false);setHistoryOrigin(['Strategy','Backtest','Experiments'].includes(tab)?'Backtest':tab==='Comparisons'?'Comparisons':'Library');}setTab(destination);}
  const [preview,setPreview]=useState<any>(null),[trust,setTrust]=useState(false);
  const [strategies,setStrategies]=useState<any[]>([]),[datasets,setDatasets]=useState<any[]>([]),[datasetId,setDatasetId]=useState('');
  const datasetSelection=useRef(0),listRefresh=useRef(0);
  function chooseDataset(id:string){datasetSelection.current++;setDatasetId(id);}
  const history=useRunHistory(),runs=history.runs;
  const [activeId,setActiveId]=useState<string|null>(null),[status,setStatus]=useState<any>(null),[selectedRun,setSelectedRun]=useState<any>(null),[trades,setTrades]=useState<any>(null),[tradeOffset,setTradeOffset]=useState(0);
  const [tradeRetry,setTradeRetry]=useState(0);
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[closePrompt,setClosePrompt]=useState(false),[busy,setBusy]=useState(false);
  const [selectedRuns,setSelectedRuns]=useState<string[]>([]);
  const reportRequest=useRef(0),tradePages=useRef<number[]>([]);
  useEffect(()=>{reportRequest.current++;},[tab]);
  function selectReport(run:any){reportRequest.current++;tradePages.current=[];setSelectedRun(run);setTradeOffset(0);}
  async function openRunReport(id:string){
    const request=++reportRequest.current;
    try{
      await refresh();if(request!==reportRequest.current)return;
      const run=await api('run_status',{run_id:id});
      if(request!==reportRequest.current)return;
      selectReport(run);setTab('Results');
    }catch(error){if(request===reportRequest.current)throw error;}
  }
  const [libraryActive,setLibraryActive]=useState<string|null>(null);
  const libraryRef=useRef<string|null>(null);libraryRef.current=libraryActive;
  const [experimentActive,setExperimentActive]=useState<string|null>(null);
  const experimentRef=useRef<string|null>(null);experimentRef.current=experimentActive;
  const [download,setDownload]=useState<any>(null),[historyStart,setHistoryStart]=useState(new Date(Date.now()-86400000).toISOString().slice(0,10)+'T00:00'),[historyEnd,setHistoryEnd]=useState(new Date().toISOString().slice(0,10)+'T00:00');
  const downloading=['running','cancel_requested'].includes(download?.status);
  const downloadingRef=useRef(false);downloadingRef.current=downloading;
  const replayRef=useRef<string|null>(null);
  const activeRef=useRef<string|null>(null);activeRef.current=activeId;
  const currentNode=graph.nodes.find(n=>n.id===selectedNode);
  useEffect(()=>{const shortcut=(e:KeyboardEvent)=>{if(draft.prompt||tab!=='Strategy'||kind!=='graph'||isTextEditing(e.target)||!(e.ctrlKey||e.metaKey))return;if(shortcutKey(e)==='z'){e.preventDefault();e.shiftKey?editor.redo():editor.undo();}else if(shortcutKey(e)==='y'){e.preventDefault();editor.redo();}};document.addEventListener('keydown',shortcut,true);return()=>document.removeEventListener('keydown',shortcut,true);});
  const selectedDataset=datasets.find(d=>d.id===datasetId&&historyMatchesProfile(d,profile));
  useEffect(()=>{
    if(datasetId&&!selectedDataset){chooseDataset('');setNotice('The selected history is no longer compatible or available. Choose history matching the current market, instrument and execution resolution.');}
  },[datasetId,datasets,profile.market,profile.symbol,profile.execution_minutes]);
  function change(key:string,value:string|number){setProfile(p=>({...p,[key]:value}));}
  async function refresh(){const request=++listRefresh.current;const [s,d]=await Promise.all([api<any[]>('list_strategies'),api<any[]>('list_datasets'),history.refresh()]);if(request!==listRefresh.current)return null;setStrategies(s);setDatasets(d);return d;}
  async function refreshAfterImport(){const request=++listRefresh.current;const [s,d]=await Promise.all([api<any[]>('list_strategies'),api<any[]>('list_datasets'),history.refreshStrict()]);if(request!==listRefresh.current)return;setStrategies(s);setDatasets(d);}
  async function action(work:()=>Promise<void>){setError('');setNotice('');setBusy(true);try{await work();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
  useEffect(()=>{if(transport.localService)refresh().catch(e=>setError(e.message));},[]);
  useEffect(()=>{
    if(transport.mode!=='browser'||serviceStopped)return;
    let current=true;
    Promise.all([api<any[]>('list_runs'),api('download_status')]).then(([savedRuns,savedDownload])=>{
      if(!current)return;
      const running=savedRuns.find(hasActiveWork);
      if(running){setActiveId(running.id);setStatus(running);}
      setDownload(savedDownload);
    }).catch(e=>{if(current)setError(String(e));});
    return()=>{current=false;};
  },[serviceStopped]);
  useEffect(()=>{
    if(!transport.nativeWindow)return;
    let unlisten:(()=>void)|undefined,disposed=false;
    getCurrentWindow().onCloseRequested(event=>{event.preventDefault();void (async()=>{
      const scheduler=await api<any>('scheduler_status');
      const released=storageFailureReleased(scheduler);
      if(scheduler?.verified_reads?.length||scheduler?.reservation?.startsWith('archive:')||scheduler?.reservation?.startsWith('export:')){setClosePrompt(true);return;}
      if(released){if(downloadingRef.current)setClosePrompt(true);else await invoke('close_application');return;}
      if(activeRef.current||downloadingRef.current||experimentRef.current||libraryRef.current)setClosePrompt(true);
      else {const job=await api<any>('replay_status',{replay_id:null});if(job&&(job.worker_active??['running','cancel_requested'].includes(job.status))){replayRef.current=job.id;setClosePrompt(true);}else await invoke('close_application');}
    })().catch(e=>setError(String(e)));}).then(fn=>{if(disposed)fn();else unlisten=fn;}).catch(e=>setError(String(e)));
    return ()=>{disposed=true;unlisten?.();};
  },[]);
  useEffect(()=>{
    if(!downloading)return;
    return poll(()=>api<any>('download_status'),s=>{setDownload(s);if(s.status==='completed'){const selection=datasetSelection.current;refresh().then(rows=>{if(selection===datasetSelection.current&&rows?.some(d=>d.id===s.dataset_id&&historyMatchesProfile(d,draft.current.profile)))chooseDataset(s.dataset_id);}).catch(e=>setError(e.message));}},e=>setError(String(e)),800);
  },[downloading]);
  useEffect(()=>{
    if(!activeId)return;
    return poll(()=>api<any>('run_status',{run_id:activeId}),s=>{
      setStatus(s);
      if(['completed','cancelled','failed','interrupted'].includes(s.status)&&!s.worker_active){
        setActiveId(null);refresh().catch(e=>setError(e.message));
        if(s.status==='completed'){selectReport(s);setTab('Results');}
        else if(s.error)setError(s.error);
      }
    },e=>setError(String(e)),500);
  },[activeId]);
  useEffect(()=>{
    let current=true;setTrades(null);
    if(selectedRun?.id&&selectedRun.status==='completed')api('result_page',{run_id:selectedRun.id,kind:'trades',offset:tradeOffset,limit:100,review:true}).then(value=>{if(current)setTrades({...value as any,ownerRun:selectedRun.id,ownerOffset:tradeOffset});}).catch(e=>{if(current)setTrades({ownerRun:selectedRun.id,ownerOffset:tradeOffset,rows:[],error:e.message});});
    return()=>{current=false;};
  },[selectedRun?.id,selectedRun?.status,tradeOffset,tradeRetry]);
  function nativeDocument(){return {...native,config:JSON.parse(nativeConfig),dependencies:JSON.parse(nativeDependencies)};}
  async function save(){await draft.save();}
  function afterReplacement(){setSelectedNode(null);setPreview(null);setTrust(false);setTab('Strategy');}
  async function loadSavedStrategy(id:string,isCurrent:()=>boolean=()=>true,ticket?:DraftIntent){
    const opened=await draft.replace('Opening a saved strategy',async()=>{
      const saved=await api<any>('get_strategy',{strategy_id:id});
      const next:StrategyDraft={...draft.current,strategyId:id,name:saved.name,kind:saved.kind,profile:saved.profile??draft.current.profile};
      if(saved.kind==='graph'){next.graph=saved.document.graph;next.layout=saved.document.layout??{};}
      else if(saved.kind==='native'){next.native=saved.document;next.nativeDependencies=JSON.stringify(saved.document.dependencies,null,2);next.nativeConfig=JSON.stringify(saved.document.config,null,2);next.profile={...next.profile,evaluation:'closed',stop_loss:'0',take_profit:'0',version:1,position_management:undefined};}
      else throw Error('Unsupported saved strategy format.');
      return next;
    },isCurrent,false,ticket);
    if(opened)afterReplacement();return opened;
  }
  async function openStrategy(id:string){try{await loadSavedStrategy(id);}catch{/* The shared draft boundary shows the retained-draft error. */}}
  function prepareStrategyOpen(converted=false){const ticket=draft.prepare();return async(id:string,isCurrent:()=>boolean=()=>true)=>{if(await loadSavedStrategy(id,isCurrent,ticket)&&converted){setRight(true);setLeft(true);chooseDataset('');}void refresh().catch(e=>setError(String(e)));};}
  async function openImportedReport(id:string,isCurrent:()=>boolean){
    const request=++reportRequest.current;
    const saved=await api<any>('run_status',{run_id:id});
    if(!isCurrent()||request!==reportRequest.current)return;
    if(saved.status!=='completed')throw Error('The saved report is not completed.');
    selectReport(saved);setTab('Results');
  }
  async function newStrategy(format:'graph'|'native'){
    const opened=await draft.replace('Creating a new strategy',()=>{
      const next:StrategyDraft={...draft.current,strategyId:null,name:format==='graph'?'Untitled visual strategy':'Native Python strategy',kind:format};
      if(format==='graph'){next.graph=exampleGraph();next.layout={};}
      else{next.native=nativeExample();next.nativeDependencies=JSON.stringify(next.native.dependencies,null,2);next.nativeConfig=JSON.stringify(next.native.config,null,2);next.profile={...next.profile,evaluation:'closed',stop_loss:'0',take_profit:'0',version:1,position_management:undefined};}
      return next;
    });if(opened)afterReplacement();
  }
  async function run(){await action(async()=>{
    if(kind==='native'&&nativeUnavailable)throw new Error(platformCapabilities.native_execution.reason);
    if(kind==='graph'&&problems.length){setTab('Strategy');throw new Error('Fix the highlighted graph problems before running.');}
    if(!datasetId||!historyMatchesProfile(selectedDataset,profile))throw new Error('Choose a prepared dataset matching this market, instrument and execution resolution.');
    const result=await api<any>('start_run',{strategy:kind==='graph'?graph:nativeDocument(),profile,dataset_id:datasetId});
    setActiveId(result.run_id);setStatus({status:'running',progress:null});setTab('Backtest');
  });}
  function addNode(type:NodeKind=addType,position={x:60,y:70}){if(type==='frozen_rule')return;if(graph.nodes.length>=128){setError('Graph limit: 128 nodes');return;}const node=createNode(type);editor.change({...graph,nodes:[...graph.nodes,node]},{...layout,[node.id]:position});setSelectedNode(node.id);setRight(true);}
  function parameter(key:string,value:string|number){if(currentNode?.type==='frozen_rule')return;editor.change({...graph,nodes:graph.nodes.map(n=>n.id===selectedNode?{...n,params:{...n.params,[key]:value}}:n)},layout);}
  async function copyStrategy(){
    if(await draft.replace('Creating an independent copy',()=>({...draft.current,strategyId:null,name:`${draft.current.name} copy`}),undefined,true)){afterReplacement();setNotice('Independent draft copy. Save it to create a new strategy; previous results remain unchanged.');}
  }
  const field=(key:string,label:string,options?:string[],disabled=false)=><label className="field" key={key}><span>{label}</span>{options?<select aria-label={label} value={String(profile[key]??'')} disabled={disabled} onChange={e=>{change(key,e.target.value);if(key==='market'&&e.target.value==='spot')change('leverage','1');}}>{options.map(v=><option key={v} value={v}>{v}</option>)}</select>:<input aria-label={label} value={String(profile[key]??'')} disabled={disabled} onChange={e=>change(key,e.target.value)}/>}</label>;
  const rate=(key:string,label:string,disabled=false)=><label className="field" key={key}><span>{label} (%)</span><input type="number" step="any" disabled={disabled} aria-label={`${label} (%)`} value={Number(profile[key])*100} onChange={e=>change(key,String(Number(e.target.value)/100))}/></label>;
  if(serviceStopped)return <div className="content"><h1>Local service stopped</h1><p>Saved results are retained. Restart the browser launcher and reopen its address to continue.</p></div>;
  return <RuleStrategyProvider onPrepareOpen={()=>prepareStrategyOpen(true)} onRefresh={async()=>setStrategies(await api<any[]>('list_strategies'))} onOpenStrategy={async(id,isCurrent)=>{if(await loadSavedStrategy(id,isCurrent)){setRight(true);setLeft(true);chooseDataset('');}}}><div className={`app ${mode==='research'?'research-mode':'pro-mode'}${marketFocused?' market-chart-focused':''}`}>
    <a className="skip-link" href="#main-workspace">Skip to workspace</a><header><div className="brand"><span className="brand-mark">T</span><div><strong>Trading Terminal</strong><small>Strategy research workspace</small></div></div><div className="local-badge"><span/> Local workspace · {productVersion||'development'}</div>{['Strategy','Backtest'].includes(tab)&&<button className="primary" disabled={busy||!!activeId||!!experimentActive||!!libraryActive||!transport.localService||(kind==='native'&&nativeUnavailable)} onClick={run}>Run backtest <span>↗</span></button>}</header>
    {transport.stopService&&<BrowserServiceControls active={!!activeId||downloading||!!experimentActive||!!libraryActive} onStopped={()=>{setServiceStopped(true);setActiveId(null);setDownload(null);}}/>}
    {platformCapabilities?.platform==='linux'&&<details className="capability-note"><summary>Linux preview · graph research available · native Python unavailable</summary><p>Visual graph backtests and saved reports are available. Native Python execution, Windows notifications, sound and Telegram credential storage are unavailable on this platform. Windows desktop acceptance is separate.</p></details>}
    <div className="workspace">
      {mode==='pro'&&left&&tab!=='Library'&&tab!=='History'&&<aside className="library"><div className="section-heading">STRATEGIES <span>{strategies.length}</span></div><button onClick={()=>newStrategy('graph')}>＋ Visual strategy</button><button onClick={()=>newStrategy('native')}>＋ Native Python</button><div className="strategy-list">{strategies.map(s=><button className={s.id===strategyId?'active':''} onClick={()=>openStrategy(s.id)} key={s.id}><span>{s.kind==='graph'?'◇':'Py'}</span><div>{s.name}<small>{s.kind==='graph'?'Visual graph':'Native Python'}</small></div></button>)}{!strategies.length&&<p className="muted">Save a strategy to add it to this workspace.</p>}</div><div className="library-foot">One instrument.<br/>One position.<br/>Reproducible runs.</div></aside>}
      <main id="main-workspace" tabIndex={-1}>{mode==='pro'&&<div className="toolbar"><button className="icon-button" title="Toggle strategy list" onClick={()=>setLeft(!left)}>☷</button><input className="strategy-title" aria-label="Strategy name" value={name} onChange={e=>setName(e.target.value)}/><span className="format-tag">{kind==='graph'?'VISUAL':'PYTHON'}</span><span className="strategy-draft-state" role="status">{draft.saving?'Saving strategy…':draft.loading?'Opening strategy…':draft.dirty?'Unsaved changes':strategyId?'Saved strategy':'New draft'}</span><button disabled={busy||draft.saving||!transport.localService} onClick={save}>Save</button><button onClick={copyStrategy}>Copy strategy</button><button className="icon-button" title="Toggle settings" onClick={()=>setRight(!right)}>⚙</button></div>}
        <nav aria-label="Workspace"><div className="primary-navigation">{[['Live','Market'],['Library','Lab'],['Comparisons','Saved tests'],['History','Data'],['Strategy','Strategy editor']].map(([t,label])=><button key={t} aria-current={tab===t||t==='Comparisons'&&tab==='Results'?'page':undefined} className={tab===t||t==='Comparisons'&&tab==='Results'?'active':''} onClick={()=>navigate(t)}>{label}</button>)}</div><details className="advanced-navigation"><summary>More tools</summary><div>{[['Backtest','Custom backtest'],['Experiments','Parameter experiments']].map(([t,label])=><button key={t} onClick={e=>{setTab(t);e.currentTarget.closest('details')?.removeAttribute('open');}}>{label}</button>)}</div></details>{(activeId||libraryActive)&&<button className="running-link" onClick={()=>setTab(libraryActive?'Comparisons':'Backtest')}>Test running</button>}</nav>
        <div className="experiment-host" hidden={!['Library','Comparisons'].includes(tab)}><StrategyLibrary onPrepareOpen={()=>prepareStrategyOpen()} onObservation={(id,revision)=>observe(id,revision)} preferredBatch={preferredBatch} suspendSetup={closePrompt||!['Library','Comparisons'].includes(tab)} view={tab==='Comparisons'?'saved':'catalog'} onSaved={()=>setTab('Comparisons')} onCatalog={()=>setTab('Library')} onRunHistory={()=>setTab('Results')} datasets={datasets} profile={researchProfile} editorProfile={profile} onProfile={setResearchProfile} onHistory={(origin,context)=>{setHistoryLater(origin==='later');setHistoryContext(context??null);setHistoryOrigin(origin==='later'?'Comparisons':'Library');setTab('History');}} preferredDataset={researchDataset} onActive={setLibraryActive} onOpenRun={id=>action(()=>openRunReport(id))} onCopy={async id=>{await openStrategy(id);refresh().catch(e=>setError(String(e)));}}/></div>
        <StorageFailureNotice connected={transport.localService&&!serviceStopped} onReleased={()=>{setActiveId(null);activeRef.current=null;setLibraryActive(null);libraryRef.current=null;setExperimentActive(null);experimentRef.current=null;replayRef.current=null;}}/>
        {draft.prompt&&<StrategyDraftPrompt label={draft.prompt.label} saving={draft.saving} onChoice={draft.choose}/>}
        {draft.error&&<div role="alert" className="banner error">{draft.error}</div>}{draft.notice&&<div className="banner info">{draft.notice}</div>}
        {error&&<div role="alert" className="banner error">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}>×</button></div>}{notice&&<div className="banner info">{notice}</div>}
        {tab==='History'&&<HistoryWorkspace onObserve={d=>observe('',undefined,d.id)} datasets={datasets} profile={historyContext??(historyOrigin==='Backtest'?profile:researchProfile)} onBack={()=>setTab(historyOrigin)} returnLabel={historyOrigin==='Backtest'?'Back to custom backtest':historyOrigin==='Comparisons'?'Back to saved tests':'Back to Lab setup'} status={download} disabled={busy||!transport.localService} onPrepare={params=>action(async()=>setDownload(await api('history_prepare',params)))} onCancel={()=>action(async()=>setDownload(await api('download_cancel')))} onUse={d=>{if(historyOrigin==='Backtest'){if(!historyMatchesProfile(d,profile)){setError('Choose history matching the custom backtest market, instrument and execution resolution, or change its settings first.');return;}chooseDataset(d.id);}else setResearchDataset(v=>({id:d.id,request:v.request+1,target:historyLater?'later':undefined}));setTab(historyOrigin==='Backtest'?'Backtest':historyLater?'Comparisons':'Library');}}/>}
        {tab==='Strategy'&&kind==='graph'&&<><div className="graph-tools"><select aria-label="Node type" value={addType} onChange={e=>setAddType(e.target.value as NodeKind)}>{Object.keys(catalog).filter(k=>k!=='frozen_rule').map(k=><option key={k} value={k}>{labels[k]}</option>)}</select><button onClick={()=>addNode()}>Add node</button><button disabled={!editor.canUndo} onClick={editor.undo}>Undo</button><button disabled={!editor.canRedo} onClick={editor.redo}>Redo</button><span>Connect typed ports · Select a node to edit · Delete to remove</span></div><div className="graph-canvas"><GraphEditor graph={graph} layout={layout} selected={selectedNode} locate={locate} onBegin={editor.begin} onEnd={editor.end} onCreate={addNode} onSelect={id=>{setSelectedNode(id);if(id)setRight(true);}} onChange={editor.change}/></div><div className="canvas-foot">One primary timeframe · Shared indicators across four outputs · Right-click to search nodes · Ctrl+Z / Ctrl+Y · Ctrl+D</div>{problems.length>0&&<div className="graph-problems" role="status"><strong>{problems.length} graph problem(s)</strong>{problems.map((p,i)=><button key={i} onClick={()=>{setSelectedNode(p.node);setRight(true);setLocate({id:p.node,request:Date.now()});}}>{p.node} {p.field}: {p.message}</button>)}</div>}</>}
        {tab==='Strategy'&&kind==='native'&&<section className="content native-editor"><h2>Native Python strategy</h2><p>Choose a compatible NautilusTrader module. Selection and preview do not execute it.</p><input aria-label="Python source file" type="file" accept=".py" onChange={e=>action(async()=>{const file=e.target.files?.[0];if(!file)return;if(file.size>512*1024)throw new Error('Python source exceeds 512 KiB');const revision=draft.revision,source=await file.text();if(!draft.isCurrent(revision))return;setNative({...native,source,provenance:`User-selected module: ${file.name}; confirm its provenance and license before execution.`});setPreview(null);setTrust(false);})}/><textarea className="source-preview" aria-label="Python source preview" value={native.source} readOnly spellCheck={false}/>
          <div className="two-columns"><label className="field"><span>Strategy class</span><input value={native.class_name} onChange={e=>setNative({...native,class_name:e.target.value})}/></label><label className="field"><span>Config class</span><input value={native.config_class} onChange={e=>setNative({...native,config_class:e.target.value})}/></label></div>
          <label className="field"><span>Native config (JSON)</span><textarea value={nativeConfig} onChange={e=>setNativeConfig(e.target.value)} spellCheck={false}/></label><label className="field"><span>Declared bar minutes (comma-separated)</span><input value={native.bar_minutes.join(',')} onChange={e=>setNative({...native,bar_minutes:e.target.value.split(',').map(Number)})}/></label><label className="field"><span>Source / dependency provenance and license</span><textarea value={native.provenance} onChange={e=>setNative({...native,provenance:e.target.value})}/></label>
          <label className="field"><span>Required installed dependencies (exact versions, JSON)</span><textarea aria-label="Native dependency versions" value={nativeDependencies} onChange={e=>setNativeDependencies(e.target.value)} spellCheck={false}/></label>
          <button onClick={()=>action(async()=>{setPreview(await api('preview_native',{document:nativeDocument()}));setTrust(false);})}>Inspect compatibility and trust</button>
          {preview&&<div className="trust-box"><strong>{preview.trusted?'This source has recorded consent.':'Execution requires your explicit trust.'}</strong><p>{preview.warning}</p>{preview.dependency_problems.length>0&&<pre>{JSON.stringify(preview.dependency_problems,null,2)}</pre>}<label><input type="checkbox" checked={trust} onChange={e=>setTrust(e.target.checked)}/> I reviewed this source and allow it to execute with my user permissions.</label><button disabled={!trust||preview.dependency_problems.length>0} onClick={()=>action(async()=>{const result=await api('trust_native',{document:nativeDocument(),expected_sha256:preview.trust_sha256,acknowledge_user_permissions:trust});setPreview(result);setNotice('Consent saved. The module will load only when you start a run.');})}>Trust this source</button></div>}
        </section>}
        {tab==='Backtest'&&<section className="content backtest"><div className="eyebrow">IMMUTABLE INPUTS · MANAGED WORKER</div><h2>Prepare a reproducible run</h2><p>Choose local history, review the simulation assumptions, then run. The editor stays available while the worker calculates.</p><BacktestHistory datasets={datasets} profile={profile} datasetId={datasetId} onChange={chooseDataset}/>
          {selectedDataset?.source==='Bybit public API'&&<button onClick={()=>action(async()=>{const revision=draft.revision;const fields=await api<any>('dataset_profile',{dataset_id:datasetId});if(!draft.isCurrent(revision))return;setProfile(p=>({...p,...fields}));setNotice('Applied current exchange precision and lowest risk tier as explicit historical assumptions. Review costs separately.');})}>Use dataset instrument constraints</button>}
          <div className="assumption"><strong>Simulation assumptions</strong><p>{profile.market==='linear'?'Single-position cross margin. ': 'Unborrowed spot. '}Minute path: {profile.path}. Protection model {String(profile.version)}: {Number(profile.version)===2?'continuous intraminute crossing; gaps use first available price':'discrete observed path points'}, with configured costs. Historical risk/precision changes may be unknown.</p>{selectedDataset?.market==='linear'&&<p>{selectedDataset.coverage?.funding?.assumption}</p>}</div>
          <div className="run-actions"><button className="primary" disabled={!!activeId||!!experimentActive||!!libraryActive||busy||!selectedDataset||!transport.localService||(kind==='native'&&nativeUnavailable)} onClick={run}>Run immutable snapshot</button>{activeId&&<button className="danger" onClick={()=>action(async()=>{await api('cancel_run',{run_id:activeId});})}>Cancel run</button>}</div>
          {status&&<div className="run-status"><strong>{status.status}</strong><p><small><RunProgress status={status}/> · Cancelled or partial work is never a successful result.</small></p></div>}
          {(activeId||status?.id)&&<RunLogs runId={activeId||status.id}/>}
          <DownloadPanel start={historyStart} end={historyEnd} setStart={setHistoryStart} setEnd={setHistoryEnd} status={download} disabled={busy||!transport.localService} onStart={()=>action(async()=>{const start=Date.parse(historyStart+'Z')/1000,end=Date.parse(historyEnd+'Z')/1000;if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)throw Error('Choose a valid increasing UTC range.');setDownload(await api('download_start',{market:profile.market,symbol:profile.symbol,start,end}));})} onCancel={()=>action(async()=>{setDownload(await api('download_cancel'));})}/>

        </section>}
        <div className="experiment-host" hidden={tab!=='Experiments'}><Experiments onPrepareOpen={()=>prepareStrategyOpen()} strategies={strategies} datasets={datasets} profile={profile} onActive={setExperimentActive} onOpenRun={id=>action(()=>openRunReport(id))} onCopy={async id=>{await openStrategy(id);refresh().catch(e=>setError(String(e)));}}/></div>
        {tab==='Live'&&<div className="market-source-nav" aria-label="Market source"><button aria-pressed={marketView==='live'} onClick={()=>{setMarketVisited(true);setMarketView('live');}}>Live market</button><button aria-pressed={marketView==='saved'} onClick={()=>{setObservationsVisited(true);setMarketView('saved');}}>Saved history · local</button></div>}
        {observationsVisited&&<div className="experiment-host observation-host" hidden={tab!=='Live'||marketView!=='saved'}><Observations datasets={datasets} request={observationRequest} onTest={testObservation} onBatch={id=>{setPreferredBatch(v=>({id,request:v.request+1}));setTab('Comparisons');}}/></div>}
        {marketVisited&&<div className="experiment-host market-host" hidden={tab!=='Live'||marketView!=='live'}><Live visible={marketVisible} focused={marketFocused} onFocusChange={setMarketFocus} strategyId={strategyId} profile={marketProfile} onProfileChange={setMarketProfile}/></div>}
        {tab==='Results'&&<section className="content results"><button onClick={()=>setTab('Comparisons')}>Back to saved tests</button><details className="saved-run-history" key={selectedRun?.id??'history'} open={!selectedRun}><summary>Run history · {runs.length} loaded{history.next?' · more available':''}</summary><div className="results-heading"><h2>Run history</h2><button disabled={history.loading} onClick={()=>action(async()=>{await refresh();})}>Refresh</button></div>{history.loading&&<p role="status">Loading run history…</p>}{history.error&&<p role="alert">Run history: {history.error} <button onClick={()=>history.loadMore()}>Retry run history</button></p>}{history.loaded&&!history.loading&&!history.error&&!runs.length&&<p>No saved runs.</p>}<div className="run-list">{runs.map(r=><button key={r.id} className={selectedRun?.id===r.id?'active':''} onClick={()=>{if(hasActiveWork(r)){setStatus(r);setActiveId(r.id);setTab('Backtest');return;}selectReport(r);}}><span>{r.summary?.origin==='imported'?'IMPORTED REPORT':r.status}</span><strong>{r.summary?.profile.symbol??'Backtest'}</strong><small>{new Date(r.created_at).toLocaleString()}</small>{r.summary&&<b className={Number(r.summary.metrics.net_pnl)>=0?'positive':'negative'}>{Number(r.summary.metrics.net_pnl).toFixed(2)} USDT</b>}</button>)}</div>{history.next&&<button disabled={history.loading} onClick={()=>history.loadMore()}>Load older runs</button>}{history.loaded&&!history.loading&&!history.error&&runs.length>0&&!history.next&&<p>End of saved run history.</p>}</details>
          {selectedRun?.summary&&<><div className="selected-report-heading"><h2>Saved report · {selectedRun.summary.profile.symbol}</h2><p>{savedRunDate(selectedRun,runs)??'Creation date unavailable'} · Run {selectedRun.id.slice(0,8)} · {selectedRun.status}</p></div>{selectedRun.summary.origin==='imported'&&<p className="assumption">Imported report: saved archive values, not locally verified calculations. Raw candle history is omitted. Artifact files have not been verified.</p>}<p className="assumption">Instrument assumptions: {selectedRun.summary.profile.tier_assumption}</p><DisplayTrackingNotice/><DisplayedMetrics key={`metrics:${selectedRun.id}`} reference={{surface:'run_metrics',run_id:selectedRun.id}}><div className="metrics">{[['Net PnL',`${Number(selectedRun.summary.metrics.net_pnl).toFixed(2)} USDT`],['Max drawdown',`${(Number(selectedRun.summary.metrics.max_drawdown)*100).toFixed(2)}%`],['Trades',selectedRun.summary.metrics.trade_count],['Win rate',selectedRun.summary.metrics.win_rate===null?'—':`${(selectedRun.summary.metrics.win_rate*100).toFixed(1)}%`],['Fees',Number(selectedRun.summary.metrics.fees).toFixed(4)],['Funding',Number(selectedRun.summary.metrics.funding).toFixed(4)]].map(([label,value])=><div key={String(label)}><span>{label}</span><strong data-metric={value!=='—'?true:undefined}>{value}</strong></div>)}</div></DisplayedMetrics><TradeReview key={`review:${selectedRun.id}`} runId={selectedRun.id} page={trades?.ownerRun===selectedRun.id&&trades?.ownerOffset===tradeOffset?trades:null} offset={tradeOffset} onPage={setTradeOffset} pageHistory={tradePages} onRetry={()=>setTradeRetry(value=>value+1)}/><RunSnapshot runId={selectedRun.id}/><RunLogs runId={selectedRun.id}/><details><summary>Metric definitions</summary><p>Net PnL = final equity − initial capital. Fees are deducted execution commissions. Funding is signed account cashflow (positive means received). Max drawdown is the largest peak-to-trough equity fraction, including unrealized PnL at modeled source-candle price points. Win rate counts completed trades with positive net PnL after fees and funding. No-trade win rate is undefined.</p></details></>}
          <ComparisonPanel key={`comparison:${selectedRun?.id??"history"}`} runs={runs} selected={selectedRuns} onSelect={setSelectedRuns}/><ProjectTransfer onPrepareImport={()=>{const ticket=draft.prepare();return async(result,isCurrent)=>{await refreshAfterImport();if(await loadSavedStrategy(result.strategy_id,isCurrent,ticket))setNotice(result.note);};}} strategy={()=>({name,kind,document:kind==='graph'?{graph,layout}:nativeDocument()})} profile={profile} runIds={selectedRuns} onImported={async(result,isCurrent)=>{if(await loadSavedStrategy(result.strategy_id,isCurrent))setNotice(result.note);await refreshAfterImport();}} onOpenReport={openImportedReport} onOpenStrategy={async(id,isCurrent)=>{await loadSavedStrategy(id,isCurrent);}}/>
          {history.loaded&&!history.loading&&!history.error&&!runs.length&&<div className="empty-state"><span>⌁</span><h3>Your research history starts here</h3><p>Run a strategy to inspect immutable results, costs and execution assumptions.</p></div>}
        </section>}
      </main>
      {mode==='pro'&&right&&tab!=='Live'&&tab!=='Library'&&tab!=='History'&&<aside className="settings"><div className="section-heading">{currentNode&&tab==='Strategy'?'NODE PARAMETERS':'SIMULATION SETTINGS'}</div>{tab==='Results'&&selectedRun?.summary?<><h3>Saved run settings</h3><p className="muted">Read-only snapshot. Editor changes do not alter this result.</p>{selectedRun.summary.origin==='imported'&&<p className="assumption">Imported report; calculations have not been verified here. Raw candle history is absent.</p>}<PositionSettings profile={selectedRun.summary.profile} onChange={()=>{}} disabled/>{Object.entries(selectedRun.summary.profile).filter(([key])=>key!=='position_management').map(([key,value])=><div className="snapshot-field" key={key}><small>{key}</small><span>{String(value)}</span></div>)}</>:currentNode&&tab==='Strategy'&&kind==='graph'?<><h3>{labels[currentNode.type]}</h3><small className="muted">{currentNode.id}</small>{currentNode.type==='frozen_rule'?<FrozenRuleDetails node={currentNode}/>:Object.entries(currentNode.params).map(([key,value])=><label className="field" key={key}><span>{key}</span>{key==='field'||key==='operator'?<select value={value} onChange={e=>parameter(key,e.target.value)}>{(key==='field'?['open','high','low','close','volume']:['>','>=','<','<=','==','!=']).map(o=><option key={o}>{o}</option>)}</select>:<input type="number" step="any" value={value} onChange={e=>parameter(key,Number(e.target.value))}/>}</label>)}<button onClick={()=>setSelectedNode(null)}>Back to simulation</button></>:<>
        {field('market','Market',['spot','linear'])}{field('symbol','Instrument')}{field('capital','Initial capital (USDT)')}{field('leverage','Leverage',undefined,profile.market==='spot')}
        <label className="field"><span>Primary timeframe</span><select aria-label="Primary timeframe" disabled={kind==='native'} value={profile.primary_minutes} onChange={e=>change('primary_minutes',Number(e.target.value))}>{[1,3,5,15,30,60,120,240,360,720,1440].map(n=><option key={n} value={n}>{n<60?`${n}m`:n<1440?`${n/60}h`:'1d'}</option>)}</select></label>
        {field('evaluation','Condition evaluation',['closed','intrabar'],kind==='native')}{field('sizing','Allocation mode',['fixed','percent'],kind==='native')}{field('allocation',profile.sizing==='percent'?'Capital allocation (%)':'Allocated margin (USDT)',undefined,kind==='native')}{rate('stop_loss','Stop loss',kind==='native')}{rate('take_profit','Take profit',kind==='native')}
        {kind==='native'&&<p className="muted">Native config controls sizing, signals, timeframes and exits. Graph controls are unavailable.</p>}
        <PositionSettings profile={profile} onChange={setProfile} disabled={kind==='native'}/>
        <details><summary>Costs and execution</summary>{rate('fee_rate','Fee rate')}{rate('slippage','Slippage')}<label className="field"><span>Execution model</span><select aria-label="Execution model" disabled={kind==='native'} value={profile.version} onChange={e=>change('version',Number(e.target.value))}><option value={2}>Profile 2: continuous segment protection</option><option value={1}>Profile 1: discrete observations</option></select></label>{field('path','Minute path',['OLHC','OHLC'])}{field('gap_policy','Missing minute policy',['reject','skip'])}{profile.market==='linear'&&<>{field('mark_mode','Mark source',['history','last_proxy'])}{field('funding_mode','Funding source',['history','assumed_zero'])}{rate('maintenance_rate','Maintenance margin')}</>}</details>
        <details><summary>Precision and risk limits</summary>{field('tick_size','Price tick')}{field('quantity_step','Quantity step')}{field('min_quantity','Minimum quantity')}{field('max_quantity','Maximum market quantity')}{field('min_notional','Minimum notional (USDT)')}{field('max_notional','Tier maximum notional (USDT)')}<label className="field"><span>Historical tier assumption</span><textarea value={profile.tier_assumption} onChange={e=>change('tier_assumption',e.target.value)}/></label></details><p className="muted">Values are editable modeling assumptions. Check source coverage and instrument constraints before interpreting a result.</p>
      </>}</aside>}
    </div><footer><span>{activeId?'Worker active · minimizing continues the run':'Local research and paper · no real orders'}</span><span>NautilusTrader 1.231.0</span></footer>
    {closePrompt&&<div className="modal-backdrop"><div className="modal" role="dialog" aria-label="Close during active run"><h2>A test is still running</h2><p>Return to keep it running, or cancel active work and exit. Partial work will not be marked successful.</p><button onClick={()=>setClosePrompt(false)}>Return to application</button><button className="danger" onClick={()=>action(async()=>{const scheduler=await api<any>('scheduler_status');const released=storageFailureReleased(scheduler);for(const read of scheduler?.verified_reads??[])await api('chart_read_cancel',{request_id:read.request_id});if(scheduler?.reservation?.startsWith('export:'))await api('archive_export_cancel',{export_id:scheduler.reservation.slice(7)});if(scheduler?.reservation?.startsWith('archive:')){const operation_id=scheduler.reservation.slice(8);const receipt=await api<any>('archive_import_status',{operation_id});if(receipt.execution)await api('archive_import_cancel',{operation_id,attempt_key:receipt.execution.attempt_key});}if(!released){if(replayRef.current){const replay=await api<any>('replay_status',{replay_id:replayRef.current});if(replay?.status==='running')await api('replay_cancel',{replay_id:replayRef.current});}if(activeRef.current)await api('cancel_run',{run_id:activeRef.current});if(libraryRef.current)await api('library_batch_cancel',{active_id:libraryRef.current});if(experimentRef.current)await api('experiment_cancel',{active_id:experimentRef.current});}if(downloadingRef.current)await api('download_cancel');await invoke('close_application');})}>Cancel run and exit</button></div></div>}
  </div></RuleStrategyProvider>;
}

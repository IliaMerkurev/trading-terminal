import { useEffect, useRef, useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { invoke } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';
import { api, isDesktop } from './api';
import GraphEditor from './GraphEditor';
import DownloadPanel from './DownloadPanel';
import RunChart from './RunChart';
import RunLogs from './RunLogs';
import ComparisonPanel from './ComparisonPanel';
import ProjectTransfer from './ProjectTransfer';
import RunSnapshot from './RunSnapshot';
import Experiments from './Experiments';
import Live from './Live';
import {poll} from './poll';
import {useRunHistory} from './useRunHistory';
import {createNode,graphProblems,isTextEditing,shortcutKey} from './editor';
import {useGraphHistory} from './useGraphHistory';
import { catalog, defaultProfile, exampleGraph, labels, type Graph, type Layout, type NodeKind, type Profile } from './model';
import PositionSettings from './PositionSettings';
import PositionLifecycle from './PositionLifecycle';
import StrategyLibrary from './StrategyLibrary';

const nativeExample=()=>({version:1,engine:'nautilus_trader',engine_version:'1.231.0',
  source:'from nautilus_trader.examples.strategies.ema_cross import EMACross, EMACrossConfig\n',
  class_name:'EMACross',config_class:'EMACrossConfig',config:{instrument_id:'$instrument',bar_type:'$bar:1',trade_size:'0.001',fast_ema_period:10,slow_ema_period:20,request_bars:false,subscribe_trade_ticks:false,close_positions_on_stop:true},
  bar_minutes:[1],dependencies:{nautilus_trader:'1.231.0'},provenance:'Installed official NautilusTrader EMACross example (LGPLv3); imported without copying its source.'});

export default function App(){
  const [productVersion,setProductVersion]=useState('');
  useEffect(()=>{if(isDesktop())getVersion().then(v=>setProductVersion(v.replace(/\.0-dev$/,'-dev'))).catch(()=>{});},[]);
  const [tab,setTab]=useState('Strategy'),[left,setLeft]=useState(true),[right,setRight]=useState(true);
  const editor=useGraphHistory(()=>({graph:exampleGraph(),layout:{close:{x:30,y:90},mean:{x:280,y:230},above:{x:550,y:50},below:{x:550,y:320}}}));
  const {graph,layout}=editor;
  const [locate,setLocate]=useState<{id:string;request:number}|null>(null);
  const problems=graphProblems(graph);
  const [selectedNode,setSelectedNode]=useState<string|null>(null),[addType,setAddType]=useState<NodeKind>('ema');
  const [profile,setProfile]=useState<Profile>({...defaultProfile});
  const [name,setName]=useState('SMA research example'),[strategyId,setStrategyId]=useState<string|null>(null),[kind,setKind]=useState<'graph'|'native'>('graph');
  const [native,setNative]=useState<any>(nativeExample),[nativeConfig,setNativeConfig]=useState(JSON.stringify(nativeExample().config,null,2)),[preview,setPreview]=useState<any>(null),[trust,setTrust]=useState(false);
  const [strategies,setStrategies]=useState<any[]>([]),[datasets,setDatasets]=useState<any[]>([]),[datasetId,setDatasetId]=useState('');
  const history=useRunHistory(),runs=history.runs;
  const [activeId,setActiveId]=useState<string|null>(null),[status,setStatus]=useState<any>(null),[selectedRun,setSelectedRun]=useState<any>(null),[trades,setTrades]=useState<any>(null),[tradeOffset,setTradeOffset]=useState(0);
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[closePrompt,setClosePrompt]=useState(false),[busy,setBusy]=useState(false);
  const [nativeDependencies,setNativeDependencies]=useState(JSON.stringify(nativeExample().dependencies,null,2));
  const [selectedRuns,setSelectedRuns]=useState<string[]>([]);
  const [experimentActive,setExperimentActive]=useState<string|null>(null);
  const experimentRef=useRef<string|null>(null);experimentRef.current=experimentActive;
  const [chartFocus,setChartFocus]=useState<{time:number;request:number}|null>(null);
  const [download,setDownload]=useState<any>(null),[historyStart,setHistoryStart]=useState(new Date(Date.now()-86400000).toISOString().slice(0,10)+'T00:00'),[historyEnd,setHistoryEnd]=useState(new Date().toISOString().slice(0,10)+'T00:00');
  const downloading=['running','cancel_requested'].includes(download?.status);
  const downloadingRef=useRef(false);downloadingRef.current=downloading;
  const replayRef=useRef<string|null>(null);
  const activeRef=useRef<string|null>(null);activeRef.current=activeId;
  const currentNode=graph.nodes.find(n=>n.id===selectedNode);
  useEffect(()=>{const shortcut=(e:KeyboardEvent)=>{if(tab!=='Strategy'||kind!=='graph'||isTextEditing(e.target)||!(e.ctrlKey||e.metaKey))return;if(shortcutKey(e)==='z'){e.preventDefault();e.shiftKey?editor.redo():editor.undo();}else if(shortcutKey(e)==='y'){e.preventDefault();editor.redo();}};document.addEventListener('keydown',shortcut,true);return()=>document.removeEventListener('keydown',shortcut,true);});
  const selectedDataset=datasets.find(d=>d.id===datasetId);
  const compatibleDatasets=datasets.filter(d=>d.market===profile.market&&d.symbol===profile.symbol);
  function change(key:string,value:string|number){setProfile(p=>({...p,[key]:value}));}
  async function refresh(){const [s,d]=await Promise.all([api<any[]>('list_strategies'),api<any[]>('list_datasets'),history.refresh()]);setStrategies(s);setDatasets(d);}
  async function action(work:()=>Promise<void>){setError('');setNotice('');setBusy(true);try{await work();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
  useEffect(()=>{if(isDesktop())refresh().catch(e=>setError(e.message));else setNotice('Browser layout preview. Run the Windows desktop app to connect to local data and workers.');},[]);
  useEffect(()=>{
    if(!isDesktop())return;
    let unlisten:(()=>void)|undefined,disposed=false;
    getCurrentWindow().onCloseRequested(event=>{event.preventDefault();if(activeRef.current||downloadingRef.current||experimentRef.current)setClosePrompt(true);else api<any>('replay_status',{replay_id:null}).then(job=>{if(job&&['running','cancel_requested'].includes(job.status)){replayRef.current=job.id;setClosePrompt(true);}else return invoke('close_application');}).catch(e=>setError(String(e)));}).then(fn=>{if(disposed)fn();else unlisten=fn;}).catch(e=>setError(String(e)));
    return ()=>{disposed=true;unlisten?.();};
  },[]);
  useEffect(()=>{
    if(!downloading)return;
    return poll(()=>api<any>('download_status'),s=>{setDownload(s);if(s.status==='completed'){setDatasetId(s.dataset_id);refresh().catch(e=>setError(e.message));}},e=>setError(String(e)),800);
  },[downloading]);
  useEffect(()=>{
    if(!activeId)return;
    return poll(()=>api<any>('run_status',{run_id:activeId}),s=>{
      setStatus(s);
      if(['completed','cancelled','failed','interrupted'].includes(s.status)){
        setActiveId(null);refresh().catch(e=>setError(e.message));
        if(s.status==='completed'){setSelectedRun(s);setTradeOffset(0);setTab('Results');}
        else if(s.error)setError(s.error);
      }
    },e=>setError(String(e)),500);
  },[activeId]);
  useEffect(()=>{
    if(selectedRun?.id&&selectedRun.status==='completed')api('result_page',{run_id:selectedRun.id,kind:'trades',offset:tradeOffset,limit:100}).then(setTrades).catch(e=>setError(e.message));
    else setTrades(null);
  },[selectedRun?.id,tradeOffset]);
  function nativeDocument(){return {...native,config:JSON.parse(nativeConfig),dependencies:JSON.parse(nativeDependencies)};}
  async function save(){await action(async()=>{
    const result=kind==='graph'?await api<any>('save_graph',{name,graph,layout,strategy_id:strategyId,profile}):await api<any>('save_native',{name,document:nativeDocument(),strategy_id:strategyId,profile});
    setStrategyId(result.strategy_id);await refresh();setNotice('Strategy saved. Existing run snapshots are unchanged.');
  });}
  async function openStrategy(id:string){await action(async()=>{
    const s=await api<any>('get_strategy',{strategy_id:id});setStrategyId(id);setName(s.name);setKind(s.kind);setSelectedNode(null);if(s.profile)setProfile(s.profile);
    if(s.kind==='graph'){editor.reset(s.document.graph,s.document.layout??{});}else{setNative(s.document);setNativeDependencies(JSON.stringify(s.document.dependencies,null,2));setNativeConfig(JSON.stringify(s.document.config,null,2));setPreview(null);setTrust(false);setProfile(p=>({...p,evaluation:'closed',stop_loss:'0',take_profit:'0',version:1,position_management:undefined}));}
    setTab('Strategy');
  });}
  function newStrategy(format:'graph'|'native'){
    setStrategyId(null);setName(format==='graph'?'Untitled visual strategy':'Native Python strategy');setKind(format);setSelectedNode(null);setPreview(null);setTrust(false);
    if(format==='graph'){editor.reset(exampleGraph(),{});}else{setNative(nativeExample());setNativeDependencies(JSON.stringify(nativeExample().dependencies,null,2));setNativeConfig(JSON.stringify(nativeExample().config,null,2));setProfile(p=>({...p,evaluation:'closed',stop_loss:'0',take_profit:'0',version:1,position_management:undefined}));}
    setTab('Strategy');
  }
  async function run(){await action(async()=>{
    if(kind==='graph'&&problems.length){setTab('Strategy');throw new Error('Fix the highlighted graph problems before running.');}
    if(!datasetId||!selectedDataset||selectedDataset.market!==profile.market||selectedDataset.symbol!==profile.symbol)throw new Error('Choose a prepared dataset matching this market and instrument.');
    const result=await api<any>('start_run',{strategy:kind==='graph'?graph:nativeDocument(),profile,dataset_id:datasetId});
    setActiveId(result.run_id);setStatus({status:'running',progress:null});setTab('Backtest');
  });}
  function addNode(type:NodeKind=addType,position={x:60,y:70}){if(graph.nodes.length>=128){setError('Graph limit: 128 nodes');return;}const node=createNode(type);editor.change({...graph,nodes:[...graph.nodes,node]},{...layout,[node.id]:position});setSelectedNode(node.id);setRight(true);}
  function parameter(key:string,value:string|number){editor.change({...graph,nodes:graph.nodes.map(n=>n.id===selectedNode?{...n,params:{...n.params,[key]:value}}:n)},layout);}
  function copyStrategy(){setStrategyId(null);setName(`${name} copy`);editor.reset(graph,layout);setPreview(null);setTrust(false);setNotice('Independent draft copy. Save it to create a new strategy; previous results remain unchanged.');}
  const field=(key:string,label:string,options?:string[],disabled=false)=><label className="field" key={key}><span>{label}</span>{options?<select aria-label={label} value={String(profile[key]??'')} disabled={disabled} onChange={e=>{change(key,e.target.value);if(key==='market'&&e.target.value==='spot')change('leverage','1');}}>{options.map(v=><option key={v} value={v}>{v}</option>)}</select>:<input aria-label={label} value={String(profile[key]??'')} disabled={disabled} onChange={e=>change(key,e.target.value)}/>}</label>;
  const rate=(key:string,label:string,disabled=false)=><label className="field" key={key}><span>{label} (%)</span><input type="number" step="any" disabled={disabled} aria-label={`${label} (%)`} value={Number(profile[key])*100} onChange={e=>change(key,String(Number(e.target.value)/100))}/></label>;
  return <div className="app">
    <header><div className="brand"><span className="brand-mark">T</span><div><strong>Trading Terminal</strong><small>Research and live monitoring</small></div></div><div className="local-badge"><span/> Local · no live orders</div><button className="primary" disabled={busy||!!activeId||!!experimentActive||!isDesktop()} onClick={run}>Run backtest <span>↗</span></button></header>
    <div className="workspace">
      {left&&<aside className="library"><div className="section-heading">STRATEGIES <span>{strategies.length}</span></div><button onClick={()=>newStrategy('graph')}>＋ Visual strategy</button><button onClick={()=>newStrategy('native')}>＋ Native Python</button><div className="strategy-list">{strategies.map(s=><button className={s.id===strategyId?'active':''} onClick={()=>openStrategy(s.id)} key={s.id}><span>{s.kind==='graph'?'◇':'Py'}</span><div>{s.name}<small>{s.kind==='graph'?'Visual graph':'Native Python'}</small></div></button>)}{!strategies.length&&<p className="muted">Save a strategy to add it to this workspace.</p>}</div><div className="library-foot">One instrument.<br/>One position.<br/>Reproducible runs.</div></aside>}
      <main><div className="toolbar"><button className="icon-button" title="Toggle strategy list" onClick={()=>setLeft(!left)}>☷</button><input className="strategy-title" aria-label="Strategy name" value={name} onChange={e=>setName(e.target.value)}/><span className="format-tag">{kind==='graph'?'VISUAL':'PYTHON'}</span><button disabled={busy||!isDesktop()} onClick={save}>Save</button><button onClick={copyStrategy}>Copy strategy</button><button className="icon-button" title="Toggle settings" onClick={()=>setRight(!right)}>⚙</button></div>
        <nav>{['Strategy','Library','Backtest','Experiments','Live','Results'].map(t=><button key={t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t}</button>)}<span>{activeId?'● RUNNING':('RESEARCH'+(productVersion?' '+productVersion:''))}</span></nav>
        {tab==='Library'&&<StrategyLibrary onCopy={async id=>{await refresh();await openStrategy(id);}}/>}
        {error&&<div role="alert" className="banner error">{error}<button onClick={()=>setError('')}>×</button></div>}{notice&&<div className="banner info">{notice}</div>}
        {tab==='Strategy'&&kind==='graph'&&<><div className="graph-tools"><select aria-label="Node type" value={addType} onChange={e=>setAddType(e.target.value as NodeKind)}>{Object.keys(catalog).map(k=><option key={k} value={k}>{labels[k]}</option>)}</select><button onClick={()=>addNode()}>Add node</button><button disabled={!editor.canUndo} onClick={editor.undo}>Undo</button><button disabled={!editor.canRedo} onClick={editor.redo}>Redo</button><span>Connect typed ports · Select a node to edit · Delete to remove</span></div><div className="graph-canvas"><GraphEditor graph={graph} layout={layout} selected={selectedNode} locate={locate} onBegin={editor.begin} onEnd={editor.end} onCreate={addNode} onSelect={id=>{setSelectedNode(id);if(id)setRight(true);}} onChange={editor.change}/></div><div className="canvas-foot">One primary timeframe · Shared indicators across four outputs · Right-click to search nodes · Ctrl+Z / Ctrl+Y · Ctrl+D</div>{problems.length>0&&<div className="graph-problems" role="status"><strong>{problems.length} graph problem(s)</strong>{problems.map((p,i)=><button key={i} onClick={()=>{setSelectedNode(p.node);setRight(true);setLocate({id:p.node,request:Date.now()});}}>{p.node} {p.field}: {p.message}</button>)}</div>}</>}
        {tab==='Strategy'&&kind==='native'&&<section className="content native-editor"><h2>Native Python strategy</h2><p>Choose a compatible NautilusTrader module. Selection and preview do not execute it.</p><input aria-label="Python source file" type="file" accept=".py" onChange={e=>action(async()=>{const file=e.target.files?.[0];if(!file)return;if(file.size>512*1024)throw new Error('Python source exceeds 512 KiB');setNative({...native,source:await file.text(),provenance:`User-selected module: ${file.name}; confirm its provenance and license before execution.`});setPreview(null);setTrust(false);})}/><textarea className="source-preview" aria-label="Python source preview" value={native.source} readOnly spellCheck={false}/>
          <div className="two-columns"><label className="field"><span>Strategy class</span><input value={native.class_name} onChange={e=>setNative({...native,class_name:e.target.value})}/></label><label className="field"><span>Config class</span><input value={native.config_class} onChange={e=>setNative({...native,config_class:e.target.value})}/></label></div>
          <label className="field"><span>Native config (JSON)</span><textarea value={nativeConfig} onChange={e=>setNativeConfig(e.target.value)} spellCheck={false}/></label><label className="field"><span>Declared bar minutes (comma-separated)</span><input value={native.bar_minutes.join(',')} onChange={e=>setNative({...native,bar_minutes:e.target.value.split(',').map(Number)})}/></label><label className="field"><span>Source / dependency provenance and license</span><textarea value={native.provenance} onChange={e=>setNative({...native,provenance:e.target.value})}/></label>
          <label className="field"><span>Required installed dependencies (exact versions, JSON)</span><textarea aria-label="Native dependency versions" value={nativeDependencies} onChange={e=>setNativeDependencies(e.target.value)} spellCheck={false}/></label>
          <button onClick={()=>action(async()=>{setPreview(await api('preview_native',{document:nativeDocument()}));setTrust(false);})}>Inspect compatibility and trust</button>
          {preview&&<div className="trust-box"><strong>{preview.trusted?'This source has recorded consent.':'Execution requires your explicit trust.'}</strong><p>{preview.warning}</p>{preview.dependency_problems.length>0&&<pre>{JSON.stringify(preview.dependency_problems,null,2)}</pre>}<label><input type="checkbox" checked={trust} onChange={e=>setTrust(e.target.checked)}/> I reviewed this source and allow it to execute with my user permissions.</label><button disabled={!trust||preview.dependency_problems.length>0} onClick={()=>action(async()=>{const result=await api('trust_native',{document:nativeDocument(),expected_sha256:preview.trust_sha256,acknowledge_user_permissions:trust});setPreview(result);setNotice('Consent saved. The module will load only when you start a run.');})}>Trust this source</button></div>}
        </section>}
        {tab==='Backtest'&&<section className="content backtest"><div className="eyebrow">IMMUTABLE INPUTS · MANAGED WORKER</div><h2>Prepare a reproducible run</h2><p>Choose local history, review the simulation assumptions, then run. The editor stays available while the worker calculates.</p><label className="field"><span>Prepared dataset</span><select aria-label="Prepared dataset" value={datasetId} onChange={e=>setDatasetId(e.target.value)}><option value="">Select matching history</option>{compatibleDatasets.map(d=><option key={d.id} value={d.id}>{d.source} · {d.symbol} · {d.market} · {new Date(d.range[0]*1000).toISOString().slice(0,10)} · {d.coverage.trade.count.toLocaleString()} minutes</option>)}</select></label>
          {selectedDataset&&<p className="muted">Source: {selectedDataset.source}</p>}
          {selectedDataset?.source==='Bybit public API'&&<button onClick={()=>action(async()=>{const fields=await api<any>('dataset_profile',{dataset_id:datasetId});setProfile(p=>({...p,...fields}));setNotice('Applied current exchange precision and lowest risk tier as explicit historical assumptions. Review costs separately.');})}>Use dataset instrument constraints</button>}
          {selectedDataset&&<div className="coverage"><div><span>Trade candles</span><strong>{selectedDataset.coverage.trade.count.toLocaleString()}</strong><small>{selectedDataset.coverage.trade.complete?'Complete requested coverage':'Gaps present'}</small></div>{selectedDataset.market==='linear'&&<><div><span>Mark candles</span><strong>{selectedDataset.coverage.mark.count.toLocaleString()}</strong><small>{selectedDataset.coverage.mark.complete?'Complete requested coverage':'Gaps present'}</small></div><div><span>Funding events</span><strong>{selectedDataset.coverage.funding.count}</strong><small>{selectedDataset.coverage.funding.complete_against_current_interval?'Matches declared interval':'Coverage not verified'}</small></div></>}</div>}
          <div className="assumption"><strong>Simulation assumptions</strong><p>{profile.market==='linear'?'Single-position cross margin. ': 'Unborrowed spot. '}Minute path: {profile.path}. Protection model {String(profile.version)}: {Number(profile.version)===2?'continuous intraminute crossing; gaps use first available price':'discrete observed path points'}, with configured costs. Historical risk/precision changes may be unknown.</p>{selectedDataset?.market==='linear'&&<p>{selectedDataset.coverage.funding.assumption}</p>}</div>
          <div className="run-actions"><button className="primary" disabled={!!activeId||!!experimentActive||busy||!datasetId||!isDesktop()} onClick={run}>Run immutable snapshot</button>{activeId&&<button className="danger" onClick={()=>action(async()=>{await api('cancel_run',{run_id:activeId});})}>Cancel run</button>}</div>
          {status&&<div className="run-status"><strong>{status.status}</strong><div className="progress"><div style={{width:`${Math.min(100,(status.progress?.fraction??0)*100)}%`}}/></div><small>{status.progress?`${Math.round(status.progress.fraction*100)}% processed`:'Worker preparation'} · Cancelled or partial work is never a successful result.</small></div>}
          {(activeId||status?.id)&&<RunLogs runId={activeId||status.id}/>}
          <DownloadPanel start={historyStart} end={historyEnd} setStart={setHistoryStart} setEnd={setHistoryEnd} status={download} disabled={busy||!isDesktop()} onStart={()=>action(async()=>{const start=Date.parse(historyStart+'Z')/1000,end=Date.parse(historyEnd+'Z')/1000;if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)throw Error('Choose a valid increasing UTC range.');setDownload(await api('download_start',{market:profile.market,symbol:profile.symbol,start,end}));})} onCancel={()=>action(async()=>{setDownload(await api('download_cancel'));})}/>

        </section>}
        <div className="experiment-host" hidden={tab!=='Experiments'}><Experiments strategies={strategies} datasets={datasets} profile={profile} onActive={setExperimentActive} onOpenRun={id=>action(async()=>{await refresh();setSelectedRun(await api('run_status',{run_id:id}));setTradeOffset(0);setChartFocus(null);setTab('Results');})} onCopy={id=>action(async()=>{await refresh();await openStrategy(id);})}/></div>
        {tab==='Live'&&<Live strategyId={strategyId} profile={profile} onProfileChange={setProfile}/>}
        {tab==='Results'&&<section className="content results"><ComparisonPanel runs={runs} selected={selectedRuns} onSelect={setSelectedRuns}/><ProjectTransfer strategy={()=>({name,kind,document:kind==='graph'?{graph,layout}:nativeDocument()})} profile={profile} runIds={selectedRuns} onImported={async result=>{await refresh();await openStrategy(result.strategy_id);setNotice(result.note);}}/><div className="results-heading"><h2>Run history</h2><button disabled={history.loading} onClick={()=>action(refresh)}>Refresh</button></div>{history.loading&&<p role="status">Loading run history…</p>}{history.error&&<p role="alert">Run history: {history.error} <button onClick={()=>history.loadMore()}>Retry run history</button></p>}{history.loaded&&!history.loading&&!history.error&&!runs.length&&<p>No saved runs.</p>}<div className="run-list">{runs.map(r=><button key={r.id} className={selectedRun?.id===r.id?'active':''} onClick={()=>{setSelectedRun(r);setTradeOffset(0);setChartFocus(null);}}><span>{r.summary?.origin==='imported'?'IMPORTED REPORT':r.status}</span><strong>{r.summary?.profile.symbol??'Backtest'}</strong><small>{new Date(r.created_at).toLocaleString()}</small>{r.summary&&<b className={Number(r.summary.metrics.net_pnl)>=0?'positive':'negative'}>{Number(r.summary.metrics.net_pnl).toFixed(2)} USDT</b>}</button>)}</div>{history.next&&<button disabled={history.loading} onClick={()=>history.loadMore()}>Load older runs</button>}{history.loaded&&!history.loading&&!history.error&&runs.length>0&&!history.next&&<p>End of saved run history.</p>}
          {selectedRun?.summary&&<><div className="metrics">{[['Net PnL',`${Number(selectedRun.summary.metrics.net_pnl).toFixed(2)} USDT`],['Max drawdown',`${(Number(selectedRun.summary.metrics.max_drawdown)*100).toFixed(2)}%`],['Trades',selectedRun.summary.metrics.trade_count],['Win rate',selectedRun.summary.metrics.win_rate===null?'—':`${(selectedRun.summary.metrics.win_rate*100).toFixed(1)}%`],['Fees',Number(selectedRun.summary.metrics.fees).toFixed(4)],['Funding',Number(selectedRun.summary.metrics.funding).toFixed(4)]].map(([label,value])=><div key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}</div><RunChart runId={selectedRun.id} focus={chartFocus}/><PositionLifecycle trades={trades?.rows??[]}/><RunSnapshot runId={selectedRun.id}/><RunLogs runId={selectedRun.id}/><details><summary>Metric definitions</summary><p>Net PnL = final equity − initial capital. Fees are deducted execution commissions. Funding is signed account cashflow (positive means received). Max drawdown is the largest peak-to-trough equity fraction, including unrealized PnL at modeled intraminute points. Win rate counts completed trades with positive net PnL after fees and funding. No-trade win rate is undefined.</p></details><h3>Trades · select a row to inspect its chart region</h3><div className="table-scroll"><table><thead><tr><th>Direction</th><th>Entry (UTC)</th><th>Entry price</th><th>Exit price</th><th>Quantity</th><th>Net PnL</th><th>Exit reason</th></tr></thead><tbody>{trades?.rows.map((t:any,i:number)=><tr key={i} tabIndex={0} onClick={()=>setChartFocus({time:Math.floor(t.entry.time_ns/1e9),request:Date.now()})} onKeyDown={e=>{if(e.key==='Enter')setChartFocus({time:Math.floor(t.entry.time_ns/1e9),request:Date.now()});}}><td>{t.entry.side==='buy'?'Long':'Short'}</td><td>{new Date(t.entry.time_ns/1e6).toISOString().slice(0,19)}</td><td>{t.entry.price}</td><td>{t.exit.price}</td><td>{t.entry.quantity}</td><td className={Number(t.net_pnl)>=0?'positive':'negative'}>{Number(t.net_pnl).toFixed(4)}</td><td>{t.exit.reason}</td></tr>)}</tbody></table></div>{trades&&<div className="pagination"><button disabled={tradeOffset===0} onClick={()=>setTradeOffset(Math.max(0,tradeOffset-100))}>Previous</button><span>{tradeOffset+1}–{tradeOffset+trades.rows.length} of {trades.total}</span><button disabled={trades.next===null} onClick={()=>setTradeOffset(trades.next)}>Next</button></div>}</>}
          {history.loaded&&!history.loading&&!history.error&&!runs.length&&<div className="empty-state"><span>⌁</span><h3>Your research history starts here</h3><p>Run a strategy to inspect immutable results, costs and execution assumptions.</p></div>}
        </section>}
      </main>
      {right&&tab!=='Live'&&<aside className="settings"><div className="section-heading">{currentNode&&tab==='Strategy'?'NODE PARAMETERS':'SIMULATION SETTINGS'}</div>{tab==='Results'&&selectedRun?.summary?<><h3>Saved run settings</h3><p className="muted">Read-only snapshot. Editor changes do not alter this result.</p>{selectedRun.summary.origin==='imported'&&<p className="assumption">Imported report; calculations have not been verified here. Raw candle history is absent.</p>}<PositionSettings profile={selectedRun.summary.profile} onChange={()=>{}} disabled/>{Object.entries(selectedRun.summary.profile).filter(([key])=>key!=='position_management').map(([key,value])=><div className="snapshot-field" key={key}><small>{key}</small><span>{String(value)}</span></div>)}</>:currentNode&&tab==='Strategy'&&kind==='graph'?<><h3>{labels[currentNode.type]}</h3><small className="muted">{currentNode.id}</small>{Object.entries(currentNode.params).map(([key,value])=><label className="field" key={key}><span>{key}</span>{key==='field'||key==='operator'?<select value={value} onChange={e=>parameter(key,e.target.value)}>{(key==='field'?['open','high','low','close','volume']:['>','>=','<','<=','==','!=']).map(o=><option key={o}>{o}</option>)}</select>:<input type="number" step="any" value={value} onChange={e=>parameter(key,Number(e.target.value))}/>}</label>)}<button onClick={()=>setSelectedNode(null)}>Back to simulation</button></>:<>
        {field('market','Market',['spot','linear'])}{field('symbol','Instrument')}{field('capital','Initial capital (USDT)')}{field('leverage','Leverage',undefined,profile.market==='spot')}
        <label className="field"><span>Primary timeframe</span><select aria-label="Primary timeframe" disabled={kind==='native'} value={profile.primary_minutes} onChange={e=>change('primary_minutes',Number(e.target.value))}>{[1,3,5,15,30,60,120,240,360,720,1440].map(n=><option key={n} value={n}>{n<60?`${n}m`:n<1440?`${n/60}h`:'1d'}</option>)}</select></label>
        {field('evaluation','Condition evaluation',['closed','intrabar'],kind==='native')}{field('sizing','Allocation mode',['fixed','percent'],kind==='native')}{field('allocation',profile.sizing==='percent'?'Capital allocation (%)':'Allocated margin (USDT)',undefined,kind==='native')}{rate('stop_loss','Stop loss',kind==='native')}{rate('take_profit','Take profit',kind==='native')}
        {kind==='native'&&<p className="muted">Native config controls sizing, signals, timeframes and exits. Graph controls are unavailable.</p>}
        <PositionSettings profile={profile} onChange={setProfile} disabled={kind==='native'}/>
        <details><summary>Costs and execution</summary>{rate('fee_rate','Fee rate')}{rate('slippage','Slippage')}<label className="field"><span>Execution model</span><select aria-label="Execution model" disabled={kind==='native'} value={profile.version} onChange={e=>change('version',Number(e.target.value))}><option value={2}>Profile 2: continuous segment protection</option><option value={1}>Profile 1: discrete observations</option></select></label>{field('path','Minute path',['OLHC','OHLC'])}{field('gap_policy','Missing minute policy',['reject','skip'])}{profile.market==='linear'&&<>{field('mark_mode','Mark source',['history','last_proxy'])}{field('funding_mode','Funding source',['history','assumed_zero'])}{rate('maintenance_rate','Maintenance margin')}</>}</details>
        <details><summary>Precision and risk limits</summary>{field('tick_size','Price tick')}{field('quantity_step','Quantity step')}{field('min_quantity','Minimum quantity')}{field('max_quantity','Maximum market quantity')}{field('min_notional','Minimum notional (USDT)')}{field('max_notional','Tier maximum notional (USDT)')}<label className="field"><span>Historical tier assumption</span><textarea value={profile.tier_assumption} onChange={e=>change('tier_assumption',e.target.value)}/></label></details><p className="muted">Values are editable modeling assumptions. Check source coverage and instrument constraints before interpreting a result.</p>
      </>}</aside>}
    </div><footer><span>{activeId?'Worker active · minimizing continues the run':'Local research and paper · no real orders'}</span><span>NautilusTrader 1.231.0</span></footer>
    {closePrompt&&<div className="modal-backdrop"><div className="modal" role="dialog" aria-label="Close during active run"><h2>Research work is still running</h2><p>Return to keep it running, or cancel active work and exit. Partial work will not be marked successful.</p><button onClick={()=>setClosePrompt(false)}>Return to application</button><button className="danger" onClick={()=>action(async()=>{if(replayRef.current){const replay=await api<any>('replay_status',{replay_id:replayRef.current});if(replay?.status==='running')await api('replay_cancel',{replay_id:replayRef.current});}if(activeRef.current)await api('cancel_run',{run_id:activeRef.current});if(experimentRef.current)await api('experiment_cancel',{active_id:experimentRef.current});if(downloadingRef.current)await api('download_cancel');await invoke('close_application');})}>Cancel run and exit</button></div></div>}
  </div>;
}

import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {invoke} from '@tauri-apps/api/core';
import {getVersion} from '@tauri-apps/api/app';

vi.mock('@tauri-apps/api/core',()=>({invoke:vi.fn()}));
vi.mock('@tauri-apps/api/app',()=>({getVersion:vi.fn(async()=>'0.6.0-dev')}));
const json=(value:unknown,status=200)=>({ok:status>=200&&status<300,status,json:async()=>value}) as Response;
const envelope=(init:RequestInit,result:unknown)=>json({...JSON.parse(String(init.body)),type:'result',result});

beforeEach(()=>{vi.resetModules();vi.clearAllMocks();delete (window as any).__TAURI_INTERNALS__;});
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks();vi.useRealTimers();});

describe('local service transports',()=>{
  it('preserves desktop IPC and native version lookup without HTTP',async()=>{
    (window as any).__TAURI_INTERNALS__={};
    const fetch=vi.fn();vi.stubGlobal('fetch',fetch);vi.mocked(invoke).mockResolvedValue({type:'result',result:['saved']});
    const {api,productVersion,transportCapabilities}=await import('./api');
    expect(await api('list_strategies')).toEqual(['saved']);
    expect(invoke).toHaveBeenCalledWith('research_request',{message:{version:1,id:expect.any(String),command:'list_strategies',params:{}}});
    expect(await productVersion()).toBe('0.6.0-dev');expect(getVersion).toHaveBeenCalled();
    expect(transportCapabilities()).toMatchObject({mode:'desktop',nativeWindow:true,openExportsFolder:true,downloadArchives:false});
    expect(fetch).not.toHaveBeenCalled();
  });

  it('bounds stalled POSTs without replaying an operation whose outcome is unknown',async()=>{
    vi.useFakeTimers();
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'}))
      .mockImplementationOnce((_path,init)=>new Promise((_resolve,reject)=>init.signal.addEventListener('abort',()=>reject(new Error('aborted')))));
    vi.stubGlobal('fetch',fetch);const {api}=await import('./api');
    const result=expect(api('start_run')).rejects.toThrow('Check current status and saved results');
    await vi.advanceTimersByTimeAsync(60000);await result;expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('reports a broken response body as an unknown outcome without repeating the POST',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'}))
      .mockResolvedValueOnce({ok:true,status:200,json:async()=>{throw new SyntaxError('Partial body');}});
    vi.stubGlobal('fetch',fetch);const {api}=await import('./api');
    await expect(api('save_graph')).rejects.toThrow('request may have completed');expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('keeps the deadline active through response body consumption',async()=>{
    vi.useFakeTimers();
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'}))
      .mockResolvedValueOnce({ok:true,status:200,json:()=>new Promise(()=>{})});
    vi.stubGlobal('fetch',fetch);const {api}=await import('./api');
    const result=expect(api('start_run')).rejects.toThrow('request may have completed');
    await vi.advanceTimersByTimeAsync(60000);await result;expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('shares one in-memory bootstrap and sends same-origin authenticated bounded envelopes',async()=>{
    const storage=vi.spyOn(Storage.prototype,'setItem');
    const fetch=vi.fn(async(path:string,init:RequestInit)=>path==='/api/session'
      ?json({token:'synthetic-session-value',product_version:'0.6.0-dev'})
      :envelope(init,{ok:true}));vi.stubGlobal('fetch',fetch);
    const {api,productVersion,transportCapabilities}=await import('./api');
    const [first,second,version]=await Promise.all([api('list_runs'),api('save_graph',{name:'Example'}),productVersion()]);
    expect([first,second,version]).toEqual([{ok:true},{ok:true},'0.6.0-dev']);
    expect(fetch.mock.calls.filter(([path])=>path==='/api/session')).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith('/api/session',expect.objectContaining({method:'GET',headers:{'X-Terminal-Bootstrap':'1'},mode:'same-origin',cache:'no-store',redirect:'error'}));
    const posts=fetch.mock.calls.filter(([path])=>path==='/api/request');
    expect(posts).toHaveLength(2);
    for(const [,init] of posts){
      expect(init).toMatchObject({method:'POST',headers:{'Content-Type':'application/json','X-Terminal-Session':'synthetic-session-value'},credentials:'same-origin',mode:'same-origin',redirect:'error'});
      expect(JSON.parse(String(init.body))).toMatchObject({version:1,id:expect.any(String),command:expect.any(String),params:expect.any(Object)});
    }
    expect(storage).not.toHaveBeenCalled();expect(window.location.search).toBe('');
    expect(transportCapabilities()).toMatchObject({mode:'browser',localService:true,nativeWindow:false,openExportsFolder:false,downloadArchives:true,stopService:true});
    expect(invoke).not.toHaveBeenCalled();
  });

  it('does not repeat an action or bootstrap after an uncertain POST or rejected token',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'}))
      .mockRejectedValueOnce(new TypeError('Connection lost')).mockResolvedValueOnce(json({},403));vi.stubGlobal('fetch',fetch);
    const {api}=await import('./api');
    await expect(api('start_run')).rejects.toThrow('request may have completed');expect(fetch).toHaveBeenCalledTimes(2);
    await expect(api('cancel_run',{run_id:'run'})).rejects.toThrow('access was rejected');expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls.filter(([path])=>path==='/api/session')).toHaveLength(1);
  });

  it('rejects malformed bootstraps, mismatched replies and backend errors visibly',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(json({product_version:'0.6.0-dev'}));vi.stubGlobal('fetch',fetch);
    const {api}=await import('./api');
    await expect(api('list_runs')).rejects.toThrow('Invalid local service session');
    fetch.mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'})).mockResolvedValueOnce(json({version:1,id:'wrong',type:'result',result:[]}));
    await expect(api('list_runs')).rejects.toThrow('does not match');
    fetch.mockImplementationOnce(async(_path,init)=>json({...JSON.parse(init.body),type:'error',error:{message:'Unsupported command'}}));
    await expect(api('unsupported')).rejects.toThrow('Unsupported command');
  });

  it('bootstraps again after page/module reload instead of persisting the token',async()=>{
    const fetch=vi.fn(async(path:string,init:RequestInit)=>path==='/api/session'?json({token:'synthetic-session-value',product_version:'0.6.0-dev'}):envelope(init,[]));vi.stubGlobal('fetch',fetch);
    await (await import('./api')).api('list_runs');
    vi.resetModules();await (await import('./api')).api('list_runs');
    expect(fetch.mock.calls.filter(([path])=>path==='/api/session')).toHaveLength(2);
  });

  it('downloads authenticated verified chunks and releases the object URL',async()=>{
    // @ts-expect-error Node builtin is used only by this Vitest test; app types exclude Node.
    const {webcrypto}=await import('node:crypto');vi.stubGlobal('crypto',webcrypto);
    const bytes=new TextEncoder().encode('synthetic zip bytes');
    const hash=Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    const descriptor={export_id:'a'.repeat(32),filename:'a'.repeat(32)+'.ttproject.zip',bytes:bytes.length,sha256:hash,chunk_bytes:262144,chunk_sha256:[hash],history_included:false as const,note:''};
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'}))
      .mockResolvedValueOnce({ok:true,status:200,arrayBuffer:async()=>bytes.buffer});vi.stubGlobal('fetch',fetch);
    const create=vi.fn(()=>'blob:synthetic-download'),revoke=vi.fn();
    vi.stubGlobal('URL',class extends URL{static createObjectURL=create;static revokeObjectURL=revoke;});
    const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(function(this:HTMLAnchorElement){expect(this.download).toBe(descriptor.filename);});
    const {downloadArchive}=await import('./api');
    await expect(downloadArchive({...descriptor,filename:'../report.zip'})).rejects.toThrow('Invalid archive descriptor');expect(fetch).not.toHaveBeenCalled();
    vi.useFakeTimers();await downloadArchive(descriptor);
    expect(fetch).toHaveBeenLastCalledWith('/api/export/chunk',expect.objectContaining({body:JSON.stringify({export_id:descriptor.export_id,filename:descriptor.filename,offset:0,size:bytes.length}),headers:expect.objectContaining({'X-Terminal-Session':'synthetic-session-value'})}));
    expect(create).toHaveBeenCalledOnce();expect(click).toHaveBeenCalledOnce();expect(document.querySelector('a[download]')).toBeNull();
    await vi.advanceTimersByTimeAsync(1000);expect(revoke).toHaveBeenCalledWith('blob:synthetic-download');
  });

  it.each(['length','chunk','final','obsolete'])('withholds Blob download after %s verification failure',async(kind)=>{
    // @ts-expect-error Node builtin is used only by this Vitest test; app types exclude Node.
    const {webcrypto}=await import('node:crypto');vi.stubGlobal('crypto',webcrypto);
    const bytes=new Uint8Array([1,2,3]),hash=Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    const descriptor={export_id:'b'.repeat(32),filename:'b'.repeat(32)+'.ttproject.zip',bytes:3,sha256:kind==='final'?'f'.repeat(64):hash,chunk_bytes:262144,chunk_sha256:[kind==='chunk'?'f'.repeat(64):hash],history_included:false as const,note:''};
    let current=true;const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'})).mockImplementationOnce(async()=>({ok:true,arrayBuffer:async()=>{if(kind==='obsolete')current=false;return kind==='length'?new Uint8Array([1,2]).buffer:bytes.buffer;}}));vi.stubGlobal('fetch',fetch);
    const create=vi.fn();vi.stubGlobal('URL',class extends URL{static createObjectURL=create;});
    await expect((await import('./api')).downloadArchive(descriptor,()=>current)).rejects.toThrow();expect(create).not.toHaveBeenCalled();
  });

  it('stops only through an authenticated POST and prevents further requests after success',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'})).mockResolvedValueOnce(json({status:'stopping'}));vi.stubGlobal('fetch',fetch);
    const {stopLocalService,api,transportCapabilities}=await import('./api');
    await stopLocalService();expect(fetch).toHaveBeenLastCalledWith('/api/shutdown',expect.objectContaining({method:'POST',body:'{}'}));
    expect(transportCapabilities().localService).toBe(false);
    await expect(api('list_runs')).rejects.toThrow('Local service stopped');expect(fetch).toHaveBeenCalledTimes(2);
  });
});

it('aborts a pending archive transfer instead of keeping reconstruction memory alive',async()=>{
  const controller=new AbortController(),create=vi.fn();vi.stubGlobal('URL',class extends URL{static createObjectURL=create;});
  let sent=false;vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'})).mockImplementationOnce(async()=>{sent=true;return new Promise(()=>{});}));
  const d={export_id:'a'.repeat(32),filename:'a'.repeat(32)+'.ttproject.zip',bytes:3,sha256:'a'.repeat(64),chunk_bytes:262144,chunk_sha256:['a'.repeat(64)],history_included:false as const,note:''};
  const pending=(await import('./api')).downloadArchive(d,()=>true,()=>{},controller.signal);const rejected=expect(pending).rejects.toThrow();
  while(!sent)await new Promise(resolve=>setTimeout(resolve,0));controller.abort();await rejected;expect(create).not.toHaveBeenCalled();
});

it('requests multiple chunks in order and validates the final joined checksum',async()=>{
  // @ts-expect-error Node builtin is used only by this Vitest test; app types exclude Node.
  const {webcrypto}=await import('node:crypto');vi.stubGlobal('crypto',webcrypto);
  const bytes=new Uint8Array(262145);for(let i=0;i<bytes.length;i++)bytes[i]=i%251;
  const sha=async(value:Uint8Array)=>Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256',value)),v=>v.toString(16).padStart(2,'0')).join('');
  const d={export_id:'c'.repeat(32),filename:'c'.repeat(32)+'.ttproject.zip',bytes:bytes.length,sha256:await sha(bytes),chunk_bytes:262144,chunk_sha256:[await sha(bytes.slice(0,262144)),await sha(bytes.slice(262144))],history_included:false as const,note:''};
  const offsets:number[]=[];vi.stubGlobal('fetch',vi.fn(async(path,init)=>{if(path==='/api/session')return json({token:'synthetic-session-value',product_version:'0.6.0-dev'});const p=JSON.parse(init.body);offsets.push(p.offset);return {ok:true,arrayBuffer:async()=>bytes.slice(p.offset,p.offset+p.size).buffer};}));
  const create=vi.fn(()=>'blob:verified');vi.stubGlobal('URL',class extends URL{static createObjectURL=create;static revokeObjectURL=vi.fn();});vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
  await (await import('./api')).downloadArchive(d);expect(offsets).toEqual([0,262144]);expect(create).toHaveBeenCalledOnce();
});

it('moves both chart aliases onto observable bounded requests and polls exact identity',async()=>{
 const commands:string[]=[];let polls=0;
 vi.stubGlobal('fetch',vi.fn(async(path:string,init:RequestInit)=>{
  if(path==='/api/session')return json({token:'synthetic-session-value',product_version:'0.6.0-dev'});
  const message=JSON.parse(String(init.body));commands.push(message.command);
  const request_id=message.params.request_id;
  return envelope(init,{request_id,status:message.command==='chart_read_start'?'running':++polls>0?'ready':'running',phase:'verifying',result:{candles:[{time:60}]}});
 }));
 const {api}=await import('./api');
 for(const command of ['local_history_window','chart_window'])expect(await api(command,{start:0})).toEqual({candles:[{time:60}]});
 expect(commands).toEqual(['chart_read_start','chart_read_status','chart_read_start','chart_read_status']);
});

it('cancels an obsolete chart request and ignores a late success',async()=>{
 let release:(value:Response)=>void=()=>{};let id='';let startInit:RequestInit={};const commands:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(path:string,init:RequestInit)=>{
  if(path==='/api/session')return json({token:'synthetic-session-value',product_version:'0.6.0-dev'});
  const message=JSON.parse(String(init.body));commands.push(message.command);id=message.params.request_id;
  if(message.command==='chart_read_start'){startInit=init;return new Promise<Response>(r=>{release=r;});}
  return envelope(init,{request_id:id,status:'cancelled'});
 }));
 const {api}=await import('./api');const controller=new AbortController();
 const task=api('local_history_window',{start:0},{signal:controller.signal});const outcome=expect(task).rejects.toThrow('cancelled');
 await vi.waitFor(()=>expect(commands).toContain('chart_read_start'));controller.abort();
 release(envelope(startInit,{request_id:id,status:'ready',result:{candles:[{time:99}]}}));await outcome;
 expect(commands.filter(c=>c==='chart_read_start')).toHaveLength(1);expect(commands).toContain('chart_read_cancel');
});

it('distinguishes rejected note admission from a lost save acknowledgement without retrying intent',async()=>{
 let reject=true;const commands:string[]=[];let saveId='';
 vi.stubGlobal('fetch',vi.fn(async(path:string,init:RequestInit)=>{
  if(path==='/api/session')return json({token:'synthetic-session-value',product_version:'0.6.0-dev'});
  const message=JSON.parse(String(init.body));commands.push(message.command);saveId=message.params.request_id;
  if(reject)return json({version:1,id:message.id,type:'error',error:{message:'Invalid note'}});
  throw new TypeError('Lost acknowledgement');
 }));
 const {api}=await import('./api');
 await expect(api('observation_save',{})).rejects.toMatchObject({saveOutcome:'not_started'});
 reject=false;
 await expect(api('observation_save',{})).rejects.toMatchObject({saveOutcome:'unknown'});
 expect(saveId).toMatch(/^[a-f0-9]{32}$/);expect(commands).toEqual(['observation_save_start','observation_save_start']);
});
it('reasserts explicit chart cancellation after start admission before waiting for a page',async()=>{
 const commands:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(path:string,init:RequestInit)=>{
  if(path==='/api/session')return json({token:'synthetic-session-value',product_version:'0.6.0-dev'});
  const message=JSON.parse(String(init.body));commands.push(message.command);
  return envelope(init,{request_id:message.params.request_id,status:message.command==='chart_read_start'?'running':'cancelled',phase:'terminal'});
 }));
 const {api}=await import('./api');
 await expect(api('local_history_window',{start:0},{cancelRequested:()=>true})).rejects.toMatchObject({saveOutcome:'cancelled'});
 expect(commands.slice(0,2)).toEqual(['chart_read_start','chart_read_cancel']);
});

describe('indicator snapshot transport',()=>{
 async function fixture(){
  const {webcrypto,createHash}=await vi.importActual<any>('node:crypto');vi.stubGlobal('crypto',webcrypto);
  (window as any).__TAURI_INTERNALS__={};
  const result={status:'ready',columns:{one:{value:Array.from({length:1800},(_,i)=>i)}},padding:'x'.repeat(850000)};
  const text=JSON.stringify(result);
  const d={status:'paged',snapshot_id:'a'.repeat(32),sha256:createHash('sha256').update(text).digest('hex'),bytes:new TextEncoder().encode(text).length,pages:Math.ceil(text.length/65536)};
  const page=(index:number)=>({...d,index,text:text.slice(index*65536,(index+1)*65536)});
  return {result,d,page};
 }
 it('publishes only the complete verified snapshot',async()=>{
  const {result,d,page}=await fixture();
  vi.mocked(invoke).mockImplementation(async(_command,args:any)=>({type:'result',result:args.message.command==='chart_indicator_page'?page(args.message.params.index):d}));
  const {api}=await import('./api');expect(await api('chart_indicator_read')).toEqual(result);
  expect(invoke).toHaveBeenCalledTimes(d.pages+1);
 });
 it.each(['chart_preset_list','chart_preset_get'])('verifies complete preset snapshots for %s',async(command)=>{
  const {result,d,page}=await fixture();
  vi.mocked(invoke).mockImplementation(async(_command,args:any)=>({type:'result',result:args.message.command==='chart_indicator_page'?page(args.message.params.index):d}));
  const {api}=await import('./api');expect(await api(command)).toEqual(result);
  expect(invoke).toHaveBeenCalledTimes(d.pages+1);
 });
 it('rejects mixed, corrupted, and cancelled pages instead of partial results',async()=>{
  const {d,page}=await fixture();const {api}=await import('./api');
  vi.mocked(invoke).mockImplementation(async(_command,args:any)=>({type:'result',result:args.message.command==='chart_indicator_page'?{...page(args.message.params.index),snapshot_id:'b'.repeat(32)}:d}));
  await expect(api('chart_indicator_read')).rejects.toThrow('page mismatch');
  vi.mocked(invoke).mockImplementation(async(_command,args:any)=>({type:'result',result:args.message.command==='chart_indicator_page'?{...page(args.message.params.index),text:page(args.message.params.index).text.replace('x','y')}:d}));
  await expect(api('chart_indicator_read')).rejects.toThrow('checksum');
  const controller=new AbortController();
  vi.mocked(invoke).mockImplementation(async()=>{controller.abort();return {type:'result',result:d};});
  await expect(api('chart_indicator_read',{}, {signal:controller.signal})).rejects.toThrow('cancelled');
 });
 it('uploads large settings in ordered chunks and commits exactly once',async()=>{
  const {webcrypto}=await vi.importActual<any>('node:crypto');vi.stubGlobal('crypto',webcrypto);(window as any).__TAURI_INTERNALS__={};
  const chunks:string[]=[];const ident='c'.repeat(32);let offset=0;let finish=0;
  vi.mocked(invoke).mockImplementation(async(_command,args:any)=>{
   const {command,params}=args.message;
   if(command==='chart_indicator_upload_begin')return {type:'result',result:{upload_id:ident}};
   if(command==='chart_indicator_upload_append'){expect(params.offset).toBe(offset);chunks.push(params.text);offset+=new TextEncoder().encode(params.text).length;return {type:'result',result:{upload_id:ident,offset}};}
   if(command==='chart_indicator_upload_finish'){finish++;return {type:'result',result:{version:1,revision:1,instances:[]}};}
   throw new Error('Unexpected direct save');
  });
  const instances=Array.from({length:10000},(_,i)=>({id:'i'+i,type:'ema',params:{period:20},color:'#abcdef',visible:false}));
  const {api}=await import('./api');await api('chart_indicator_save',{market:'spot',symbol:'BTCUSDT',revision:0,instances});
  expect(finish).toBe(1);expect(JSON.parse(chunks.join('')).instances).toEqual(instances);
 });
});

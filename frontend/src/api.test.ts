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

  it('downloads authenticated archive bytes with a basename and releases the object URL',async()=>{
    vi.useFakeTimers();
    const blob=new Blob(['synthetic zip bytes'],{type:'application/zip'});
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'}))
      .mockResolvedValueOnce({ok:true,status:200,blob:async()=>blob});vi.stubGlobal('fetch',fetch);
    const create=vi.fn(()=>'blob:synthetic-download'),revoke=vi.fn();
    vi.stubGlobal('URL',class extends URL{static createObjectURL=create;static revokeObjectURL=revoke;});
    const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(function(this:HTMLAnchorElement){expect(this.download).toBe('report.zip');expect(this.href).toBe('blob:synthetic-download');});
    const {downloadArchive}=await import('./api');
    await expect(downloadArchive('../report.zip')).rejects.toThrow('Invalid archive filename');expect(fetch).not.toHaveBeenCalled();
    await downloadArchive('report.zip');
    expect(fetch).toHaveBeenLastCalledWith('/api/export',expect.objectContaining({body:'{"filename":"report.zip"}',headers:expect.objectContaining({'X-Terminal-Session':'synthetic-session-value'})}));
    expect(create).toHaveBeenCalledWith(blob);expect(click).toHaveBeenCalledOnce();expect(document.querySelector('a[download]')).toBeNull();
    await vi.advanceTimersByTimeAsync(1000);expect(revoke).toHaveBeenCalledWith('blob:synthetic-download');
  });

  it('stops only through an authenticated POST and prevents further requests after success',async()=>{
    const fetch=vi.fn().mockResolvedValueOnce(json({token:'synthetic-session-value',product_version:'0.6.0-dev'})).mockResolvedValueOnce(json({status:'stopping'}));vi.stubGlobal('fetch',fetch);
    const {stopLocalService,api,transportCapabilities}=await import('./api');
    await stopLocalService();expect(fetch).toHaveBeenLastCalledWith('/api/shutdown',expect.objectContaining({method:'POST',body:'{}'}));
    expect(transportCapabilities().localService).toBe(false);
    await expect(api('list_runs')).rejects.toThrow('Local service stopped');expect(fetch).toHaveBeenCalledTimes(2);
  });
});

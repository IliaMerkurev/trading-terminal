import { invoke } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';

export const isDesktop = () => '__TAURI_INTERNALS__' in window;

// Transport features are separate from the backend's execution/platform limits.
export function transportCapabilities() {
  const desktop = isDesktop();
  return {mode: desktop ? 'desktop' : 'browser', localService: !stopped,
    nativeWindow: desktop, openExportsFolder: desktop, downloadArchives: !desktop,
    stopService: !desktop} as const;
}

type BrowserSession = {token: string; product_version: string};
let session: Promise<BrowserSession> | undefined;
let stopped = false;

class LocalHttpError extends Error {}

async function localFetch<T>(path: string, init: RequestInit, read: (response: Response) => Promise<T>, bootstrap = false): Promise<T> {
  const controller = new AbortController();
  let timeout: ReturnType<typeof setTimeout> | undefined;
  let aborted: (()=>void) | undefined;
  const cancelled = new Promise<never>((_resolve,reject)=>{
    aborted=()=>{controller.abort();reject(new Error('Local request cancelled'));};
    if(init.signal?.aborted)aborted();else init.signal?.addEventListener('abort',aborted,{once:true});
  });
  const deadline = new Promise<never>((_resolve,reject) => {
    timeout = setTimeout(() => {controller.abort();reject(new Error('Local response timeout'));}, bootstrap ? 10000 : 60000);
  });
  const exchange = async () => {
    const response = await fetch(path, {...init, signal: controller.signal});
    if (!response.ok) throw new LocalHttpError(response.status === 401 || response.status === 403
      ? 'Local service access was rejected. Reopen the address printed by the browser launcher.'
      : `Local service request failed (HTTP ${response.status}).`);
    return read(response);
  };
  try {return await Promise.race([exchange(),deadline,cancelled]);}
  catch (error) {
    if (error instanceof LocalHttpError) throw error;
    throw new Error(bootstrap
      ? 'Could not reach the local service. Start the browser launcher and use the address it prints.'
      : 'The local service response was lost or timed out. The request may have completed. Check current status and saved results before trying again.');
  } finally {clearTimeout(timeout);if(aborted)init.signal?.removeEventListener('abort',aborted);}
}

function browserSession(): Promise<BrowserSession> {
  if (stopped) return Promise.reject(new Error('Local service stopped. Restart the browser launcher to reconnect.'));
  // Keep the token only in this module's memory, never in URLs or browser storage.
  if (!session) session = localFetch('/api/session', {
    method: 'GET', headers: {'X-Terminal-Bootstrap': '1'},
    credentials: 'same-origin', mode: 'same-origin', cache: 'no-store', redirect: 'error',
  }, response => response.json(), true).then(value => {
    if (typeof value?.token !== 'string' || !value.token || typeof value.product_version !== 'string') {
      throw new Error('Invalid local service session response.');
    }
    return {token: value.token, product_version: value.product_version};
  }).catch(error => {session = undefined; throw error;});
  return session;
}

async function browserPost<T = any>(path: string, body: unknown, read: (response: Response) => Promise<T> = response => response.json(), signal?:AbortSignal): Promise<T> {
  const {token} = await browserSession();
  // Never retry a POST: a disconnected response does not mean an action failed.
  return localFetch(path, {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Terminal-Session': token},
    body: JSON.stringify(body), signal, credentials: 'same-origin', mode: 'same-origin',
    cache: 'no-store', redirect: 'error',
  }, read);
}

export async function productVersion(): Promise<string> {
  return isDesktop() ? getVersion() : (await browserSession()).product_version;
}

export type VerifiedOptions={signal?:AbortSignal;viewId?:string;generation?:number;onPhase?:(phase:string)=>void;onRequest?:(id:string)=>void;cancelRequested?:()=>boolean};
const requestIdentity=()=>crypto.randomUUID().replaceAll('-','');

export async function api<T = any>(command: string, params: Record<string, unknown> = {}, options:VerifiedOptions={}): Promise<T> {
  if(command==='chart_window'||command==='local_history_window'||command==='observation_save'){
    const request_id=requestIdentity(),saving=command==='observation_save';
    options.onRequest?.(request_id);
    const current=()=>!options.signal?.aborted;
    const cancel=()=>{void api('chart_read_cancel',{request_id}).catch(()=>{});};
    if(!current())throw new Error('Verified read cancelled');
    // Aborting a viewport cancels its read; a save requires its explicit cancel button.
    if(!saving)options.signal?.addEventListener('abort',cancel,{once:true});
    let accepted=false,cancelAccepted=false;
    try{
      let operation:any=await api(saving?'observation_save_start':'chart_read_start',saving?{request_id,...params}:{
        request_id,view_id:options.viewId??requestIdentity(),generation:options.generation??1,
        surface:command==='chart_window'?'run':'observation',query:params});
      accepted=true;
      while(true){
        if(!current()){if(!saving)cancel();throw new Error('Verified read cancelled');}
        if(operation?.request_id!==request_id)throw new Error('Verified response identity mismatch');
        if(!saving&&options.cancelRequested?.()&&!cancelAccepted&&!['ready','failed','cancelled','superseded','interrupted'].includes(operation.status)){
          operation=await api('chart_read_cancel',{request_id});cancelAccepted=true;continue;
        }
        options.onPhase?.(operation.phase);
        if(operation.status===(saving?'completed':'ready'))return operation.result as T;
        if(['failed','cancelled','superseded','interrupted'].includes(operation.status))throw Object.assign(new Error(operation.error??(saving?'Note was not saved.':'Verified chart request was cancelled.')),{saveOutcome:operation.status});
        await new Promise(resolve=>setTimeout(resolve,100));
        if(!current())continue;
        operation=await api('chart_read_status',{request_id});
      }
    }catch(error){
      if(!saving)cancel();
      const outcome=(error as any)?.saveOutcome??(!accepted&&(error as any)?.definiteRejection?'not_started':'unknown');
      throw Object.assign(new Error(`${error instanceof Error?error.message:String(error)}${saving&&outcome==='unknown'?` Save request: ${request_id}. Inspect this request before saving again.`:''}`),{saveOutcome:outcome});
    }finally{if(!saving)options.signal?.removeEventListener('abort',cancel);}
  }

  if (command === 'chart_indicator_save') {
    const text = JSON.stringify({source: 'bybit', ...params});
    if (new TextEncoder().encode(text).length > 800 * 1024) return await uploadIndicatorSettings<T>(text, options);
  }
  const message = {version: 1, id: crypto.randomUUID(), command, params};
  const response = isDesktop()
    ? await invoke<any>('research_request', {message})
    : await browserPost('/api/request', message, response => response.json(), options.signal);
  if (!response || typeof response !== 'object') throw new Error('Invalid local service response.');
  if (!isDesktop() && (response.version !== message.version || response.id !== message.id)) {
    throw new Error('Local service response does not match this request.');
  }
  if (response.type !== 'result') throw Object.assign(new Error(response.error?.message ?? 'Research service failed'),{definiteRejection:true});
  if (['chart_indicator_read','chart_indicator_settings','chart_indicator_save','chart_indicator_upload_finish','chart_preset_list','chart_preset_get'].includes(command) && response.result?.status === 'paged') {
    return await readIndicatorSnapshot<T>(response.result, options);
  }
  return response.result as T;
}

export type ExportDescriptor = {export_id:string;filename:string;bytes:number;sha256:string;chunk_bytes:number;chunk_sha256:string[];history_included:false;note:string};
const checksum = async (bytes:Uint8Array<ArrayBuffer>) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),value=>value.toString(16).padStart(2,'0')).join('');

export async function downloadArchive(descriptor: ExportDescriptor, isCurrent:()=>boolean = ()=>true, progress:(bytes:number)=>void = ()=>{}, signal?:AbortSignal): Promise<void> {
  if (!transportCapabilities().downloadArchives) throw new Error('Archive downloads require browser mode.');
  const d=descriptor,hash=/^[a-f0-9]{64}$/;
  if (!d||!/^[a-f0-9]{32}$/.test(d.export_id)||d.filename!==`${d.export_id}.ttproject.zip`||!Number.isSafeInteger(d.bytes)||d.bytes<1||d.bytes>64*1024*1024||d.chunk_bytes!==256*1024||!hash.test(d.sha256)||!Array.isArray(d.chunk_sha256)||d.chunk_sha256.length!==Math.ceil(d.bytes/d.chunk_bytes)||d.chunk_sha256.some(value=>!hash.test(value))) {
    throw new Error('Invalid archive descriptor.');
  }
  const check=()=>{if(signal?.aborted||!isCurrent())throw new Error('Archive download stopped. The completed export is retained.');};
  check();const bytes=new Uint8Array(d.bytes);
  for(let offset=0;offset<d.bytes;offset+=d.chunk_bytes){
    // Sequential chunks yield the event loop and serialized service to other
    // status/cancel/write requests. No automatic replay after a lost response.
    if(offset)await new Promise(resolve=>setTimeout(resolve,0));
    check();const size=Math.min(d.chunk_bytes,d.bytes-offset);
    const part=new Uint8Array(await browserPost('/api/export/chunk',{export_id:d.export_id,filename:d.filename,offset,size},response=>response.arrayBuffer(),signal));
    check();if(part.length!==size||await checksum(part)!==d.chunk_sha256[offset/d.chunk_bytes])throw new Error('Archive chunk checksum or length mismatch. No download was presented.');
    check();bytes.set(part,offset);progress(offset+part.length);
  }
  if(await checksum(bytes)!==d.sha256)throw new Error('Archive final checksum mismatch. No download was presented.');
  check();const blob=new Blob([bytes],{type:'application/zip'}),url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download=d.filename;
  document.body.appendChild(link);
  try{link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
}

export async function stopLocalService(): Promise<void> {
  if (!transportCapabilities().stopService) throw new Error('Use the desktop window to close the application.');
  await browserPost('/api/shutdown', {});
  stopped = true;
  session = undefined;
}

// Publish only a complete verified snapshot: partial pages never reach a chart.
async function readIndicatorSnapshot<T>(descriptor: any, options: VerifiedOptions): Promise<T> {
  const d = descriptor;
  if (!/^[a-f0-9]{32}$/.test(d.snapshot_id) || !/^[a-f0-9]{64}$/.test(d.sha256) ||
      !Number.isSafeInteger(d.bytes) || d.bytes < 1 || d.bytes > 64 * 1024 * 1024 || !Number.isSafeInteger(d.pages) || d.pages < 1 || d.pages > d.bytes) {
    throw new Error('Invalid indicator snapshot descriptor');
  }
  const check = () => {if (options.signal?.aborted) throw new Error('Indicator read cancelled');};
  const chunks: string[] = [];
  let bytes = 0;
  for (let index = 0; index < d.pages; index++) {
    check();
    const page = await api<any>('chart_indicator_page', {snapshot_id: d.snapshot_id, index}, options);
    check();
    if (page?.snapshot_id !== d.snapshot_id || page.sha256 !== d.sha256 || page.bytes !== d.bytes ||
        page.pages !== d.pages || page.index !== index || typeof page.text !== 'string' || !page.text.length || page.text.length > 65536) {
      throw new Error('Indicator snapshot page mismatch');
    }
    // Canonical backend JSON escapes non-ASCII, so page boundaries are ASCII-safe.
    bytes += new TextEncoder().encode(page.text).length;
    if (bytes > d.bytes) throw new Error('Indicator snapshot length mismatch');
    chunks.push(page.text);
  }
  const text = chunks.join('');
  if (bytes !== d.bytes || await checksum(new TextEncoder().encode(text)) !== d.sha256) {
    throw new Error('Indicator snapshot checksum or length mismatch');
  }
  check();
  return JSON.parse(text) as T;
}

async function uploadIndicatorSettings<T>(text: string, options: VerifiedOptions): Promise<T> {
  const bytes = new TextEncoder().encode(text);
  const upload = await api<any>('chart_indicator_upload_begin', {size: bytes.length, sha256: await checksum(bytes)}, options);
  if (!/^[a-f0-9]{32}$/.test(upload?.upload_id)) throw new Error('Invalid indicator settings upload');
  let offset = 0;
  // Settings strings have validated ASCII identifiers/colors/types. Use code-point
  // boundaries anyway so a rejected malformed input cannot split a surrogate pair.
  for (let position = 0; position < text.length;) {
    if (options.signal?.aborted) throw new Error('Indicator settings upload cancelled');
    let end = Math.min(position + 65536, text.length);
    if (end < text.length && /[\uD800-\uDBFF]/.test(text[end - 1])) end--;
    const chunk = text.slice(position, end);
    const expected = offset + new TextEncoder().encode(chunk).length;
    const response = await api<any>('chart_indicator_upload_append', {upload_id: upload.upload_id, offset, text: chunk}, options);
    if (response?.upload_id !== upload.upload_id || response.offset !== expected) throw new Error('Indicator settings upload offset mismatch');
    offset = expected;
    position = end;
  }
  if (options.signal?.aborted) throw new Error('Indicator settings upload cancelled');
  return await api<T>('chart_indicator_upload_finish', {upload_id: upload.upload_id}, options);
}

import {useEffect,useRef,useState,type SetStateAction} from 'react';
import type {Graph,Layout,Profile} from './model';
import {GraphHistory} from './useGraphHistory';

export type StrategyDraft={name:string;strategyId:string|null;kind:'graph'|'native';graph:Graph;layout:Layout;profile:Profile;native:any;nativeConfig:string;nativeDependencies:string};
export type DraftIntent={intent:number;revision:number};
export type PrepareStrategyOpen=()=> (id:string,isCurrent?:()=>boolean)=>Promise<void>;
type Choice='save'|'discard'|'cancel';
type Prompt={label:string;resolve:(choice:Choice)=>void};
const content=(draft:StrategyDraft)=>JSON.stringify({name:draft.name,kind:draft.kind,profile:draft.profile,
  ...(draft.kind==='graph'?{graph:draft.graph,layout:draft.layout}:{native:draft.native,nativeConfig:draft.nativeConfig,nativeDependencies:draft.nativeDependencies})});
const message=(error:unknown)=>error instanceof Error?error.message:String(error);

/** One mounted draft. Replacements alone reset history; edits fence pending I/O synchronously. */
export function useStrategyDraft(initial:()=>StrategyDraft,persist:(draft:StrategyDraft)=>Promise<string>){
  const state=useRef<{
    draft:StrategyDraft;history:GraphHistory;baseline:string|null;revision:number;intent:number;generation:number;
    prompt:Prompt|null;saving:boolean;loading:boolean;alive:boolean;error:string;notice:string;
  }|null>(null);
  if(!state.current){const draft=initial();state.current={draft,history:new GraphHistory({graph:draft.graph,layout:draft.layout}),baseline:content(draft),revision:0,intent:0,generation:0,prompt:null,saving:false,loading:false,alive:true,error:'',notice:''};}
  const s=state.current;
  const [,render]=useState(0),callbacks=useRef(persist);callbacks.current=persist;
  const changed=()=>{if(s.alive)render(n=>n+1);};
  useEffect(()=>{s.alive=true;return()=>{s.alive=false;s.intent++;s.prompt?.resolve('cancel');s.prompt=null;};},[]);
  function set<K extends keyof StrategyDraft>(key:K,value:SetStateAction<StrategyDraft[K]>){
    const next=typeof value==='function'?(value as (old:StrategyDraft[K])=>StrategyDraft[K])(s.draft[key]):value;
    if(JSON.stringify(next)===JSON.stringify(s.draft[key]))return;
    s.draft={...s.draft,[key]:next};s.revision++;s.error='';s.notice='';changed();
  }
  function graphUpdate(work:()=>void){
    const before=s.history.current;work();
    if(before!==s.history.current){s.draft={...s.draft,...s.history.current};s.revision++;s.error='';s.notice='';}
    changed();
  }
  function beginIntent(){s.prompt?.resolve('cancel');s.prompt=null;s.loading=false;s.error='';s.notice='';return ++s.intent;}
  async function saveExact(current:()=>boolean){
    if(s.saving){if(current())s.error='A strategy save is still pending. Keep this draft until its outcome is known.';changed();return false;}
    const draft=structuredClone(s.draft),revision=s.revision,generation=s.generation;
    // Until acknowledgement, the persisted baseline may already have changed.
    s.baseline=null;s.saving=true;changed();
    try{
      const id=await callbacks.current(draft);
      if(typeof id!=='string'||!id)throw Error('The save response did not identify a saved strategy.');
      // Acknowledged disk content supersedes the old baseline even if edits or
      // a cancelled newer intent made this save ineligible to continue opening.
      if(s.alive&&s.generation===generation)s.baseline=content(draft);
      if(!current()||s.revision!==revision)return false;
      s.draft={...s.draft,strategyId:id};
      s.notice='Strategy saved. Existing run snapshots are unchanged.';return true;
    }catch(error){
      if(s.alive&&s.generation===generation){s.baseline=null;s.error='Save failed or its outcome is unknown. Your draft and Undo/Redo are retained. Check saved strategies before retrying. '+message(error);}
      return false;
    }finally{s.saving=false;changed();}
  }
  async function save(){const intent=beginIntent(),revision=s.revision;changed();return saveExact(()=>s.alive&&s.intent===intent&&s.revision===revision);}
  async function replace(label:string,load:()=>Promise<StrategyDraft>|StrategyDraft,isSourceCurrent:()=>boolean=()=>true,unsaved=false,ticket?:DraftIntent){
    if(ticket&&(ticket.intent!==s.intent||ticket.revision!==s.revision||!isSourceCurrent()))return false;
    const {intent,revision}=ticket??{intent:beginIntent(),revision:s.revision};
    const current=()=>s.alive&&s.intent===intent&&s.revision===revision&&isSourceCurrent();
    if(!current()){changed();return false;}
    if(content(s.draft)!==s.baseline){
      const choice=await new Promise<Choice>(resolve=>{s.prompt={label,resolve};changed();});
      if(!current()||choice==='cancel')return false;
      if(choice==='save'&&!await saveExact(current))return false;
    }
    if(!current())return false;
    s.loading=true;changed();
    try{
      const draft=await load();if(!current())return false;
      s.draft=structuredClone(draft);s.history.reset({graph:draft.graph,layout:draft.layout});s.revision++;s.generation++;
      s.baseline=unsaved?null:content(draft);s.notice='';return true;
    }catch(error){if(current()){s.error='Could not replace the strategy. Your draft and Undo/Redo are retained. '+message(error);throw error;}return false;}
    finally{if(s.intent===intent)s.loading=false;changed();}
  }
  function choose(choice:Choice){const prompt=s.prompt;s.prompt=null;prompt?.resolve(choice);changed();}
  return {draft:s.draft,get current(){return s.draft;},revision:s.revision,isCurrent:(revision:number)=>s.alive&&s.revision===revision,
    prepare:()=>{const ticket={intent:beginIntent(),revision:s.revision};changed();return ticket;},
    set,save,replace,choose,prompt:s.prompt,dirty:content(s.draft)!==s.baseline,saving:s.saving,loading:s.loading,error:s.error,notice:s.notice,
    editor:{graph:s.draft.graph,layout:s.draft.layout,canUndo:!!s.history.past.length,canRedo:!!s.history.future.length,
      change:(graph:Graph,layout:Layout)=>graphUpdate(()=>s.history.change({graph,layout})),
      begin:()=>s.history.begin(),end:()=>graphUpdate(()=>s.history.end()),undo:()=>graphUpdate(()=>s.history.undo()),redo:()=>graphUpdate(()=>s.history.redo())}};
}

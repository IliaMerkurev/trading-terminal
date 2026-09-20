import {useCallback,useEffect,useRef,useState} from 'react';
import {api} from './api';

type Cursor={created_at:string;id:string};
export type SavedRun={id:string;created_at:string;status:string;error?:string;summary?:any};
type Page={rows:SavedRun[];next:Cursor|null};

export function useRunHistory(){
 const [runs,setRuns]=useState<SavedRun[]>([]),[loading,setLoading]=useState(false);
 const [error,setError]=useState(''),[loaded,setLoaded]=useState(false),[next,setNext]=useState<Cursor|null>(null);
 const cursor=useRef<Cursor|null>(null),generation=useRef(0),pending=useRef(false);
 useEffect(()=>()=>{generation.current++;},[]);
 const load=useCallback(async(reset=false)=>{
  if(pending.current&&!reset)return;
  const version=++generation.current;pending.current=true;setLoading(true);setError('');
  try{
   const page=await api<Page>('run_history',{before:reset?null:cursor.current,limit:50});
   if(version!==generation.current)return;
   setRuns(previous=>{
    const unique=new Map((reset?[]:previous).map(row=>[row.id,row]));
    page.rows.forEach(row=>unique.set(row.id,row));
    return [...unique.values()].sort((a,b)=>b.created_at.localeCompare(a.created_at)||b.id.localeCompare(a.id));
   });
   cursor.current=page.next;setNext(page.next);setLoaded(true);
  }catch(e){if(version===generation.current)setError(String(e instanceof Error?e.message:e));}
  finally{if(version===generation.current){pending.current=false;setLoading(false);}}
 },[]);
 return {runs,loading,error,loaded,next,refresh:useCallback(()=>load(true),[load]),loadMore:useCallback(()=>load(false),[load])};
}

// One in-flight request per subscription, with no updates after disposal.
export function poll<T>(read:()=>Promise<T>, receive:(value:T)=>void, fail:(error:unknown)=>void, delay:number){
  let stopped=false,timer:ReturnType<typeof setTimeout>|undefined;
  async function update(){
    try{const value=await read();if(!stopped)receive(value);}
    catch(error){if(!stopped)fail(error);}
    finally{if(!stopped)timer=setTimeout(update,delay);}
  }
  void update();
  return ()=>{stopped=true;clearTimeout(timer);};
}

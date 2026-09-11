#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde_json::Value;
use std::{io::{BufRead,BufReader,Write}, path::PathBuf, process::{Child,ChildStdin,Command,Stdio}, sync::{Arc,Mutex,mpsc}, time::Duration};
use std::os::windows::process::CommandExt;
use tauri::{WebviewUrl,WebviewWindowBuilder};

struct Exchange { input: Option<ChildStdin>, responses: mpsc::Receiver<Result<Value,String>>, failed: bool }
struct Backend { exchange: Mutex<Exchange>, process: Mutex<Child>, startup_error: Option<String> }
impl Backend {
    fn start(root: &PathBuf) -> Result<Self,String> {
        let python=std::env::var_os("TRADING_TERMINAL_PYTHON").map(PathBuf::from).unwrap_or_else(||root.join(".venv/Scripts/python.exe"));
        let mut child=Command::new(python).args(["-m","terminal.bridge"]).arg("--data-root").arg(storage_root(root)?).current_dir(root)
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).creation_flags(0x08000000)
            .spawn().map_err(|e|format!("Cannot start project Python service: {e}"))?;
        let input=child.stdin.take().ok_or("Python stdin unavailable")?;
        let output=child.stdout.take().ok_or("Python stdout unavailable")?;
        let (tx,rx)=mpsc::channel::<Result<Value,String>>();
        std::thread::spawn(move || {
            let mut reader=BufReader::new(output);
            loop {
                let mut line=Vec::new();
                let mut limited=(&mut reader).take(1024*1024+1);
                use std::io::Read;
                let result=limited.read_until(b'\n',&mut line);
                match result {
                    Ok(0)=>break,
                    Ok(_) if line.len()<=1024*1024 => { if tx.send(serde_json::from_slice(&line).map_err(|e|e.to_string())).is_err(){break;} }
                    _=>{let _=tx.send(Err("Invalid or oversized service response".into()));break;}
                }
            }
        });
        let startup_error=match rx.recv_timeout(Duration::from_secs(30)){
            Ok(Ok(message)) if message.get("version").and_then(Value::as_i64)==Some(1) && message.get("type").and_then(Value::as_str)==Some("ready") && message.get("id").and_then(Value::as_str)==Some("startup")=>None,
            Ok(Ok(message))=>Some(message.pointer("/error/message").and_then(Value::as_str).unwrap_or("Invalid service startup response").to_string()),
            _=>Some("Python service did not become ready. Check the selected project environment and data directory.".into()),
        };
        Ok(Self{exchange:Mutex::new(Exchange{input:Some(input),responses:rx,failed:false}),process:Mutex::new(child),startup_error})
    }
    fn request(&self,message:Value)->Result<Value,String> {
        if let Some(error)=&self.startup_error{return Err(error.clone());}
        let raw=serde_json::to_vec(&message).map_err(|e|e.to_string())?;
        if raw.len()>1024*1024{return Err("Request exceeds 1 MiB".into());}
        let mut exchange=self.exchange.lock().map_err(|_|"Service lock failed")?;
        if exchange.failed{return Err("Service connection failed. Restart the application and inspect saved history before retrying a write.".into());}
        let input=exchange.input.as_mut().ok_or("Service is closed")?;
        input.write_all(&raw).and_then(|_|input.write_all(b"\n")).and_then(|_|input.flush()).map_err(|e|e.to_string())?;
        let response=match exchange.responses.recv_timeout(Duration::from_secs(30)){
            Ok(Ok(value))=>value,
            _=>{exchange.failed=true;return Err("Research service response failed or exceeded 30 seconds. The operation may have completed; restart and inspect saved history before retrying.".into());}
        };
        if response.get("id")!=message.get("id"){exchange.failed=true;return Err("Service response identifier mismatch; restart the application".into());}
        Ok(response)
    }
    fn shutdown(&self) {
        if let Ok(mut exchange)=self.exchange.lock(){exchange.input.take();}
        if let Ok(mut child)=self.process.lock(){
            for _ in 0..100 { if child.try_wait().ok().flatten().is_some(){return;} std::thread::sleep(Duration::from_millis(100)); }
            let _=child.kill();let _=child.wait();
        }
    }
}
fn storage_root(root:&PathBuf)->Result<PathBuf,String>{
    let path=std::env::var_os("TRADING_TERMINAL_DATA_ROOT").map(PathBuf::from).unwrap_or_else(||root.join(".local-data"));
    if !path.is_absolute(){return Err("Data root must be absolute".into());}
    Ok(path)
}
#[tauri::command]
async fn research_request(state:tauri::State<'_,Arc<Backend>>,message:Value)->Result<Value,String>{
    let backend=Arc::clone(state.inner());
    tauri::async_runtime::spawn_blocking(move || backend.request(message)).await.map_err(|e|e.to_string())?
}
#[tauri::command]
async fn close_application(app:tauri::AppHandle,state:tauri::State<'_,Arc<Backend>>)->Result<(),String>{
    let backend=Arc::clone(state.inner());
    tauri::async_runtime::spawn_blocking(move || backend.shutdown()).await.map_err(|e|e.to_string())?;
    app.exit(0);Ok(())
}
#[tauri::command]
fn open_exports()->Result<(),String>{
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
    let folder=storage_root(&root)?.join("exports");
    std::fs::create_dir_all(&folder).map_err(|e|e.to_string())?;
    Command::new("explorer.exe").arg(folder).spawn().map_err(|e|e.to_string())?;
    Ok(())
}
fn main(){
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
    let backend=Arc::new(Backend::start(&root).expect("Local research service failed to start"));
    let exit_backend=Arc::clone(&backend);
    let application=tauri::Builder::default().manage(backend)
        .invoke_handler(tauri::generate_handler![research_request,close_application,open_exports])
        .setup(move |app|{
            WebviewWindowBuilder::new(app,"main",WebviewUrl::App("index.html".into()))
                .title("Trading Terminal V2").inner_size(1440.0,940.0).min_inner_size(1000.0,700.0)
                .data_directory(storage_root(&root).map_err(std::io::Error::other)?.join("webview")).build()?;
            Ok(())
        }).build(tauri::generate_context!()).expect("Desktop host failed to build");
    application.run(move |_,event|{if matches!(event,tauri::RunEvent::Exit){exit_backend.shutdown();}});
}

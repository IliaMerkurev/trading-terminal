"""One local live session with bounded transport, journal and notification work."""
from collections import deque
from dataclasses import asdict
import json
import queue
import threading
import time

from terminal.data import canonical
from terminal.experiments import warmup_bars
from terminal.live_data import LiveHistory, PublicStream, reconnect_delay
from terminal.live_store import LiveStore, LiveSession, RecoveryRequired
from terminal.notifications import Telegram, TelegramDeliveryError, WindowsCredentials, play_sound, windows_notification
from terminal.paper_journal import PaperJournal, PaperRecordingError, FundingLookup
from terminal.profile import Profile
from terminal.series import Candle
from terminal.market_state import MarketState
from terminal.storage import identifier


class PendingSignals:
    """Orders require a quote observed after the signal became available."""
    def __init__(self):self.pending=None

    def offer(self,result,observed_ms):
        self.pending=(result['signals'],observed_ms,result['time']*1000)

    def take(self,price):
        if self.pending is None:return None
        signals,observed_ms,boundary=self.pending
        if price['observed_ms']<observed_ms or price['provider_ms']<boundary:return None
        self.pending=None
        return signals


class LiveManager:
    def __init__(self,store,*,stream_factory=PublicStream,history_factory=LiveHistory):
        self.store=store
        self.journal=LiveStore(store)
        self.stream_factory,self.history_factory=stream_factory,history_factory
        self.thread=None;self.stop=threading.Event();self.lock=threading.RLock()
        self.session_id=None;self.view={};self.log=deque(maxlen=200)
        self.market=MarketState();self.manual_pending=None
        self.telegram=Telegram(WindowsCredentials(store.root))
        self.delivery_queue=queue.Queue(maxsize=32)
        self.delivery_stop=threading.Event()
        self.delivery_thread=threading.Thread(target=self._deliver,daemon=True)
        self.delivery_thread.start()
        self.paper_revalidate=threading.Event()
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS live_options(session_id TEXT PRIMARY KEY,options TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS paper_observations(session_id TEXT NOT NULL,sequence INTEGER NOT NULL,
                    observation TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(session_id,sequence));
                CREATE TABLE IF NOT EXISTS manual_paper_requests(id TEXT PRIMARY KEY,session_id TEXT NOT NULL,
                    action TEXT NOT NULL,status TEXT NOT NULL,created_ms INTEGER NOT NULL,sequence INTEGER);
                CREATE TABLE IF NOT EXISTS paper_terminal_summary(session_id TEXT PRIMARY KEY,summary TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS paper_filled_observations ON paper_observations(session_id,sequence)
                    WHERE json_array_length(json_extract(result,'$.fills'))>0;
            ''')
            db.execute("UPDATE manual_paper_requests SET status='cancelled_restart' WHERE status='queued'")
            db.execute("UPDATE live_sessions SET status='PAUSED',detail='Application restarted; recovery and paper revalidation required'")
            row=db.execute('SELECT id FROM live_sessions ORDER BY rowid DESC LIMIT 1').fetchone()
            if row:self.session_id=row['id']

    def _log(self,message):
        with self.lock:self.log.append({'time':int(time.time()*1000),'message':message})

    def _set(self,**values):
        with self.lock:self.view.update(values)
        if 'paper' in values and self.session_id:
            with self.store.connect() as db:db.execute('INSERT OR REPLACE INTO paper_terminal_summary VALUES(?,?)',(self.session_id,canonical(values['paper']).decode()))

    def start(self,strategy_id,profile,paper,channels,execution_source='strategy'):
        if self.thread and self.thread.is_alive():raise ValueError('Only one live session may run at a time')
        if type(paper) is not bool or not isinstance(channels,list) or len(set(channels))!=len(channels) or any(c not in ('windows','sound','telegram') for c in channels):
            raise ValueError('Invalid paper mode or notification channels')
        strategy=self.store.strategy(strategy_id)
        if strategy['kind']!='graph':raise ValueError('Live currently requires a visual Strategy IR; native source is never converted or executed here')
        profile=Profile(**profile)
        if execution_source not in ('strategy','manual'):raise ValueError('Invalid paper execution source')
        graph=strategy['document']['graph']
        required=max(100,warmup_bars(graph)+2)*profile.primary_minutes
        if required>200000:raise ValueError('Initial live warmup exceeds 200,000 minutes; use a shorter primary timeframe or graph warmup')
        sid=self.journal.create(graph,profile,strategy_id,strategy['name'])
        options={'paper':paper,'channels':channels,'warmup_minutes':max(1440,required),'execution_source':execution_source}
        with self.store.connect() as db:db.execute('INSERT INTO live_options VALUES(?,?)',(sid,canonical(options).decode()))
        self.session_id=sid
        self.resume(sid,False)
        return {'session_id':sid}

    def resume(self,session_id,revalidate_paper):
        if type(revalidate_paper) is not bool:raise ValueError('Paper revalidation acknowledgement must be explicit')
        if self.thread and self.thread.is_alive():
            if session_id!=self.session_id:raise ValueError('Another live session is active')
            if revalidate_paper:self.paper_revalidate.set()
            return {'session_id':session_id}
        self.journal.get(session_id)
        self.session_id=session_id;self.stop.clear();self.paper_revalidate.clear()
        if revalidate_paper:self.paper_revalidate.set()
        self.view={};self.log.clear()
        self.market=MarketState()
        self.thread=threading.Thread(target=self._run,args=(session_id,),daemon=True)
        self.thread.start()
        return {'session_id':session_id}

    def pause(self):
        self.stop.set()
        self._cancel_manual('cancelled_pause')
        if self.session_id:self.journal.state(self.session_id,'PAUSED','Monitoring paused; paper state is preserved')
        return {'stopping':bool(self.thread and self.thread.is_alive())}

    def select(self,session_id):
        if self.thread and self.thread.is_alive():raise ValueError('Pause the active session before selecting saved history')
        self.journal.get(session_id)
        self.session_id=session_id;self.view={};self.log.clear()
        self.market=MarketState()
        return {'session_id':session_id}

    def status(self):
        with self.lock:view={**self.view,'log':list(self.log)}
        with self.store.connect() as db:
            view['sessions']=[dict(row) for row in db.execute("SELECT id,status,json_extract(snapshot,'$.strategy_name') AS name FROM live_sessions ORDER BY rowid DESC LIMIT 100")]
        if self.session_id:
            view.update(session=self.journal.get(self.session_id),events=self.journal.events(self.session_id))
            with self.store.connect() as db:
                row=db.execute('SELECT options FROM live_options WHERE session_id=?',(self.session_id,)).fetchone()
                view['options']=json.loads(row['options']) if row else {}
                if 'paper' not in view:
                    latest=db.execute('SELECT result FROM paper_observations WHERE session_id=? ORDER BY sequence DESC LIMIT 1',(self.session_id,)).fetchone()
                    view['paper']=json.loads(latest['result']) if latest else None
                    summary=db.execute('SELECT summary FROM paper_terminal_summary WHERE session_id=?',(self.session_id,)).fetchone()
                    if summary:view['paper']=json.loads(summary['summary'])
                trades=db.execute("SELECT result FROM paper_observations WHERE session_id=? AND json_array_length(json_extract(result,'$.fills'))>0 ORDER BY sequence DESC LIMIT 50",(self.session_id,)).fetchall()
                view['paper_history']=[json.loads(r['result']) for r in trades]
        view['active']=bool(self.thread and self.thread.is_alive() and not self.stop.is_set())
        view['market']=self.market.snapshot()
        status=view.get('session',{}).get('status','PAUSED')
        view['terminal_state']='DEGRADED' if status=='CONNECTED' and not view['market']['fresh'] else status
        with self.store.connect() as db:
            view['manual_requests']=[dict(row) for row in db.execute('SELECT id,action,status FROM manual_paper_requests WHERE session_id=? ORDER BY created_ms DESC LIMIT 10',(self.session_id,))]
        view['telegram']=self.telegram.status()
        return view

    def manual(self,session_id,action,request_id):
        identifier(request_id)
        if action not in ('buy','sell','close'):raise ValueError('Unsupported PAPER action')
        with self.lock, self.store.connect() as db:
            previous=db.execute('SELECT * FROM manual_paper_requests WHERE id=?',(request_id,)).fetchone()
            if previous:
                if previous['session_id']!=session_id or previous['action']!=action:raise ValueError('Request identity conflicts with earlier action')
                return {'request_id':request_id,'status':previous['status']}
            if session_id!=self.session_id or not self.thread or not self.thread.is_alive() or self.stop.is_set():raise ValueError('PAPER requires an active session')
            session=self.journal.get(session_id)
            options=json.loads(db.execute('SELECT options FROM live_options WHERE session_id=?',(session_id,)).fetchone()[0])
            paper=self.view.get('paper',{})
            if not options['paper'] or options.get('execution_source','strategy')!='manual':raise ValueError('Select Manual PAPER source in a new session')
            if session['status']!='CONNECTED' or not self.market.snapshot()['fresh'] or self.view.get('paper_paused') or paper.get('pending_observations',0):raise ValueError('PAPER unavailable until market and account are synchronized')
            if action=='sell' and session['snapshot']['profile']['market']=='spot':raise ValueError('Spot PAPER cannot open a short position')
            if (action=='close') != bool(paper.get('position')):raise ValueError('PAPER action conflicts with the one-position rule')
            if self.manual_pending:raise ValueError('A PAPER action is already awaiting the next quote')
            created=int(time.time()*1000)
            db.execute('INSERT INTO manual_paper_requests VALUES(?,?,?,?,?,NULL)',(request_id,session_id,action,'queued',created))
            self.manual_pending={'id':request_id,'action':action,'created_ms':created}
        return {'request_id':request_id,'status':'queued'}

    def _cancel_manual(self,status):
        with self.lock:
            if self.manual_pending:
                with self.store.connect() as db:db.execute('UPDATE manual_paper_requests SET status=? WHERE id=? AND status=?',(status,self.manual_pending['id'],'queued'))
                self.manual_pending=None

    def _take_manual(self,price):
        with self.lock:
            request=self.manual_pending
            if request is None:return None,None
            if price['observed_ms']-request['created_ms']>5000:
                self._cancel_manual('expired');return None,None
            if price['observed_ms']<=request['created_ms'] or price['provider_ms']<request['created_ms']:return None,None
            self.manual_pending=None
            signals={'entry_long':request['action']=='buy','entry_short':request['action']=='sell',
                     'exit_long':request['action']=='close','exit_short':request['action']=='close'}
            return signals,request['id']

    def replay(self,session_id):
        # Reconstruction must not mutate or pause an active session.
        session=object.__new__(LiveSession)
        session.store=self.journal;session.id=session_id
        session.snapshot=self.journal.get(session_id)['snapshot'];session.profile=Profile(**session.snapshot['profile'])
        return session.verify_replay()

    def test_notification(self,channel):
        if channel not in ('windows','sound','telegram'):raise ValueError('Unsupported notification channel')
        self.delivery_queue.put_nowait((None,[channel],'Trading Terminal: notification test'))
        return {'queued':True}

    def _deliver(self):
        while not self.delivery_stop.is_set():
            try:event,channels,text=self.delivery_queue.get(timeout=.25)
            except queue.Empty:continue
            success=True
            for channel in channels:
                try:
                    if channel=='telegram':self.telegram.send(text)
                    elif channel=='windows':windows_notification(text)
                    elif channel=='sound':play_sound()
                    self._log(f'{channel.title()} notification dispatched')
                except TelegramDeliveryError as error:
                    success=False;self._log(f'Telegram test/delivery failed: {error.safe_message} Evaluation continues.')
                except Exception:
                    success=False;self._log(f'{channel.title()} delivery failed; evaluation continues')
            if event:self.journal.delivery(event,success)
            self.delivery_queue.task_done()

    def _notify(self,event,channels):
        if not channels:
            with self.store.connect() as db:db.execute("UPDATE live_signals SET delivery='disabled' WHERE id=? AND delivery='pending'",(event['id'],))
            return
        if not self.journal.claim(event['id']):return
        text=f"{event['instrument']} — {event['type'].replace('_',' ').title()} — {event['timeframe']}m ({event['evaluation']})"
        try:self.delivery_queue.put_nowait((event['id'],channels,text))
        except queue.Full:
            self.journal.delivery(event['id'],False);self._log('Notification queue full; event retained without retry')

    def _run(self,sid):
        paper=None;stream=None
        try:
            session=LiveSession(self.journal,sid)
            with self.store.connect() as db:options=json.loads(db.execute('SELECT options FROM live_options WHERE session_id=?',(sid,)).fetchone()[0])
            history=self.history_factory(self.store.root/'live-http-cache',cancel=self.stop)
            paper_paused=False;sequence=0
            if options['paper']:
                def funding_rate(boundary):
                    client=self.history_factory(self.store.root/'live-funding-cache',cancel=self.stop)
                    result=client.get('/v5/market/funding/history',{'category':'linear','symbol':session.profile.symbol,'limit':200},cache=False)
                    for row in result.get('list',[]):
                        if row.get('symbol')==session.profile.symbol and int(row['fundingRateTimestamp'])==boundary:return row['fundingRate']
                    return None
                paper=PaperJournal(self.store,sid,session.profile,FundingLookup(funding_rate))
                paper_paused=paper.sequence>0
                self._set(paper=paper.snapshot(),paper_paused=paper_paused)
            end=int(time.time())//60*60
            if session.last is None:
                width=session.profile.primary_minutes*60
                start=end//width*width-options['warmup_minutes']*60
                history.recover(session,end,warmup_start=start)
            self._set(evaluation=session.latest)
            attempts=0;latest_price=None;last_price_at=0;pending=PendingSignals()
            while not self.stop.is_set():
                try:
                    stream=self.stream_factory(session.profile.market,session.profile.symbol)
                    stream.state=self.market
                    stream.open()
                    connected_at=time.monotonic();latest_price=None;last_price_at=connected_at
                    end=int(time.time())//60*60
                    recovered=history.recover(session,end)
                    self._log(f'Recovered {recovered} missing candles; waiting for fresh market data')
                    self.journal.state(sid,'RECOVERING DATA','Waiting for fresh subscribed public data')
                    while not self.stop.is_set():
                        events=stream.read()
                        for event in events:
                            if self.stop.is_set():break
                            if event['kind']=='price':
                                latest_price=event;last_price_at=time.monotonic()
                                self._set(price=event['price'],mark=event['mark'],price_time=event['provider_ms'])
                                if stream.subscribed and session.last is not None:
                                    expected=int(time.time())//60*60-60
                                    if session.last>=expected:self.journal.state(sid,'CONNECTED','Public data synchronized')
                                    else:self.journal.state(sid,'RECOVERING DATA','Waiting for the next confirmed minute before new signals')
                                if paper and self.paper_revalidate.is_set():
                                    self.paper_revalidate.clear();paper_paused=False;self._log('Paper continuity revalidated; missing ticks are not reconstructed')
                                if paper and not paper_paused:
                                    synchronized=self.journal.get(sid)['status']=='CONNECTED'
                                    signals,manual_id=(self._take_manual(event) if synchronized else (None,None)) if options.get('execution_source','strategy')=='manual' else (pending.take(event) if synchronized else None,None)
                                    paper.append(event,signals,manual_id=manual_id)
                                    for result in paper.process():
                                        for fill in result['fills']:self._log('Paper position '+('opened' if fill['reason']=='entry' else 'closed: '+fill['reason']))
                                    self._set(paper=paper.snapshot())
                                self._set(paper_paused=paper_paused)
                            elif event['kind']=='forming':self._set(forming=event['candle'])
                            elif event['kind']=='candle':
                                candle=Candle(**event['candle'])
                                previous=session.last
                                if session.last is not None and candle.time>session.last+60:
                                    if paper:paper_paused=True
                                    pending=PendingSignals()
                                    self._cancel_manual('cancelled_recovery')
                                    self._log('Connection gap; recovering missing candles')
                                    history.recover(session,candle.time)
                                elif stream.subscribed and latest_price and time.monotonic()-last_price_at<10 and candle.time>=int(time.time())//60*60-60:
                                    self.journal.state(sid,'CONNECTED','Confirmed minute and observed public price synchronized')
                                signals=session.ingest(candle,event['observed_ms'])
                                if previous is not None and candle.time<=previous:continue
                                self._set(evaluation=session.latest,last_candle=asdict(candle))
                                self._log('Candle closed')
                                for signal in signals:
                                    self._log(signal['type'].replace('_',' ').title()+' became TRUE')
                                    self._notify(signal,options['channels'])
                                if paper and not paper_paused and latest_price and time.monotonic()-last_price_at<10 and session.latest and session.latest['time']==candle.time+60:
                                    pending.offer(session.latest,event['observed_ms'])
                        if time.monotonic()-last_price_at>30:
                            raise RecoveryRequired('Observed market price is stale')
                        if session.last is not None and session.last<int(time.time())//60*60-120:
                            raise RecoveryRequired('Confirmed minute stream is stale')
                        # One packet does not prove that a flapping connection recovered.
                        if time.monotonic()-connected_at>=60 and self.journal.get(sid)['status']=='CONNECTED':attempts=0
                except PaperRecordingError:
                    self.journal.state(sid,'ERROR','Paper recording failed; restore committed observations before continuing')
                    self._log('Paper stopped to preserve journal consistency')
                    return
                except Exception:
                    if self.stop.is_set():break
                    paper_paused=bool(paper);self._set(paper_paused=paper_paused)
                    self._cancel_manual('cancelled_recovery');self.market.reset()
                    pending=PendingSignals()
                    self.journal.state(sid,'RECONNECTING','Public connection interrupted; history recovery required')
                    self._log('Connection lost; paper paused and notifications suppressed')
                    if self.stop.wait(reconnect_delay(attempts)):break
                    attempts+=1
                    if attempts>=8:
                        self.journal.state(sid,'ERROR','Reconnect attempts exhausted; verify connectivity and recover manually')
                        return
                finally:
                    if stream:stream.close();stream=None
            self.journal.state(sid,'PAUSED','Monitoring stopped; paper position preserved')
        except Exception:
            if self.stop.is_set():self.journal.state(sid,'PAUSED','Monitoring stopped during initialization; recover before continuation')
            else:
                self.journal.state(sid,'ERROR','Live initialization failed; verify history, graph and public connectivity')
                self._log('Initialization failed; no automatic paper continuation')
        finally:
            if paper:paper.close()

    def close(self):
        self.pause()
        if self.thread:self.thread.join(timeout=4)
        self.delivery_stop.set();self.delivery_thread.join(timeout=1)

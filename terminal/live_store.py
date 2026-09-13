"""Additive live journals. No credentials, user source execution or order API."""
from dataclasses import asdict
import hashlib
import json
import uuid

from terminal.data import canonical
from terminal.graph import GraphEvaluator, POSITION_FIELDS
from terminal.profile import Profile
from terminal.series import Candle
from terminal.signals import SignalStream
from terminal.storage import identifier


class RecoveryRequired(ValueError):
    pass


class LiveStore:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS live_sessions(
                    id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, status TEXT NOT NULL,
                    last_minute INTEGER, last_observed_ms INTEGER, detail TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS live_candles(
                    session_id TEXT NOT NULL, time INTEGER NOT NULL, candle TEXT NOT NULL,
                    source TEXT NOT NULL, observed_ms INTEGER NOT NULL,
                    PRIMARY KEY(session_id,time));
                CREATE TABLE IF NOT EXISTS live_signals(
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, time INTEGER NOT NULL,
                    event TEXT NOT NULL, delivery TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS live_signal_time ON live_signals(session_id,time);
                CREATE TABLE IF NOT EXISTS live_evaluations(session_id TEXT NOT NULL,time INTEGER NOT NULL,
                    evaluation TEXT NOT NULL,PRIMARY KEY(session_id,time));
                CREATE TABLE IF NOT EXISTS live_position_contexts(session_id TEXT NOT NULL,time INTEGER NOT NULL,
                    context TEXT NOT NULL,PRIMARY KEY(session_id,time));
            ''')

    def create(self, graph, profile, strategy_id, strategy_name):
        GraphEvaluator(graph)
        if not isinstance(profile, Profile):
            profile = Profile(**profile)
        if not isinstance(strategy_id, str) or not isinstance(strategy_name, str) or len(strategy_name)>200:
            raise ValueError('Invalid strategy identity')
        session_id = uuid.uuid4().hex
        snapshot = {'version':1, 'strategy_id':strategy_id, 'strategy_name':strategy_name,
                    'graph':graph, 'profile':profile.snapshot(), 'signal_contract':1}
        snapshot['strategy_sha256'] = hashlib.sha256(canonical(graph)).hexdigest()
        with self.store.connect() as db:
            db.execute('INSERT INTO live_sessions VALUES(?,?,?,NULL,NULL,?)',
                       (session_id, canonical(snapshot).decode(), 'PAUSED', 'History initialization required'))
        return session_id

    def get(self, session_id):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM live_sessions WHERE id=?',(identifier(session_id),)).fetchone()
        if row is None:
            raise ValueError('Unknown live session')
        return {**dict(row), 'snapshot':json.loads(row['snapshot'])}

    def state(self, session_id, status, detail):
        if status not in ('CONNECTED','RECONNECTING','RECOVERING DATA','PAUSED','ERROR'):
            raise ValueError('Invalid live connection state')
        # Callers supply fixed diagnostics, never raw provider errors/credentials.
        with self.store.connect() as db:
            db.execute('UPDATE live_sessions SET status=?,detail=? WHERE id=?',
                       (status, detail[:300], identifier(session_id)))

    def candles(self, session_id):
        with self.store.connect() as db:
            cursor = db.execute('SELECT candle FROM live_candles WHERE session_id=? ORDER BY time', (identifier(session_id),))
            for row in cursor:
                yield Candle(**json.loads(row['candle']))

    def events(self, session_id, limit=100):
        if type(limit) is not int or not 1<=limit<=200:
            raise ValueError('Live event page limit must be 1–200')
        with self.store.connect() as db:
            rows = db.execute('SELECT event,delivery FROM live_signals WHERE session_id=? ORDER BY time DESC,id LIMIT ?',
                              (identifier(session_id),limit)).fetchall()
        return [{**json.loads(row['event']), 'delivery':row['delivery']} for row in rows]

    def claim(self, event_id):
        """Durable at-most-once attempt. A crash after claim must not resend it."""
        with self.store.connect() as db:
            return db.execute("UPDATE live_signals SET delivery='claimed' WHERE id=? AND delivery='pending'",(event_id,)).rowcount == 1

    def chart(self,session_id):
        """A bounded presentation window; interval selection never reaches the IR."""
        sid=identifier(session_id)
        self.get(sid)
        with self.store.connect() as db:
            rows=db.execute('SELECT candle FROM live_candles WHERE session_id=? ORDER BY time DESC LIMIT 2880',(sid,)).fetchall()
            candles=[json.loads(row['candle']) for row in reversed(rows)]
            start=candles[0]['time'] if candles else 0
            evaluations=[json.loads(row['evaluation']) for row in db.execute('SELECT evaluation FROM live_evaluations WHERE session_id=? AND time>=? ORDER BY time LIMIT 2881',(sid,start))]
            signals=[json.loads(row['event']) for row in db.execute('SELECT event FROM live_signals WHERE session_id=? AND time>=? ORDER BY time DESC LIMIT 200',(sid,start))]
            fills=[]
            # Use the filled-observation index, not a narrow recent-tick window.
            results=db.execute("SELECT result FROM paper_observations WHERE session_id=? AND json_array_length(json_extract(result,'$.fills'))>0 ORDER BY sequence DESC LIMIT 200",(sid,)).fetchall()
            for row in reversed(results):fills.extend(json.loads(row['result']).get('fills',[]))
        return {'session_id':sid,'candles':candles,'evaluations':evaluations,'signals':signals,'fills':fills[-200:],
                'note':'Up to 2,880 recorded minutes. Indicator samples retain their IR availability timestamps; no indicator recomputation.'}

    def delivery(self, event_id, success):
        with self.store.connect() as db:
            db.execute("UPDATE live_signals SET delivery=? WHERE id=? AND delivery='claimed'",('sent' if success else 'failed',event_id))

    def paper_lifecycle(self,session_id,before=None,limit=50):
        sid=identifier(session_id);self.get(sid)
        if type(limit) is not int or not 1<=limit<=100:raise ValueError('Lifecycle page limit must be 1–100')
        if before is not None and (not isinstance(before,list) or len(before)!=2 or any(type(v) is not int or v<0 for v in before)):
            raise ValueError('Invalid lifecycle cursor')
        sequence,index=before if before is not None else (250001,1000000)
        with self.store.connect() as db:
            rows=db.execute("""SELECT p.sequence,j.key,j.value FROM paper_observations p,
                json_each(p.result,'$.lifecycle_events') j WHERE p.session_id=? AND p.sequence<=?
                AND (p.sequence<? OR CAST(j.key AS INTEGER)<?)
                ORDER BY p.sequence DESC,CAST(j.key AS INTEGER) DESC LIMIT ?""",(sid,sequence,sequence,index,limit+1)).fetchall()
        selected=rows[:limit]
        return {'rows':[json.loads(row['value']) for row in selected],
                'next':[selected[-1]['sequence'],int(selected[-1]['key'])] if len(rows)>limit else None}


class LiveSession:
    """Confirmed-minute journal and shared IR state; transport controls recovery.

    Construction always reconstructs silently and remains PAUSED. This is not
    auto-resume and cannot manufacture observed paper ticks lost while offline.
    """
    def __init__(self, store, session_id):
        self.store, self.id = store, identifier(session_id)
        self.snapshot = store.get(session_id)['snapshot']
        self.profile = Profile(**self.snapshot['profile'])
        self.uses_position = any(node['type'] in POSITION_FIELDS for node in self.snapshot['graph']['nodes'])
        self.position_provider = None
        self.last = None
        self.latest = None
        self._restore()
        store.state(self.id, 'PAUSED', 'Resume requires current history recovery and paper revalidation')

    def _restore(self):
        self.stream = SignalStream(GraphEvaluator(self.snapshot['graph']),self.profile.primary_minutes,self.profile.evaluation)
        self.last = None
        self.latest = None
        self.atr_manager = None
        if self.profile.position_management is not None:
            from terminal.position_management import PositionManager
            self.atr_manager = PositionManager(self.profile)
        with self.store.store.connect() as db:
            for row in db.execute('SELECT c.candle,p.context FROM live_candles c LEFT JOIN live_position_contexts p ON p.session_id=c.session_id AND p.time=c.time WHERE c.session_id=? ORDER BY c.time',(self.id,)):
                candle = Candle(**json.loads(row['candle']))
                context = json.loads(row['context']) if row['context'] is not None else None
                if self.uses_position and context is None: raise RecoveryRequired('Recorded position context is missing')
                self.latest = self.evaluate(candle,context) or self.latest
                self.last = candle.time

    def evaluate(self,candle,context):
        atr = self.atr_manager.observe_candle(candle) if self.atr_manager else None
        result = self.stream.update(candle,context)
        if result and self.atr_manager:
            result['values']['position_management.atr'] = float(atr) if atr is not None else None
        if result and self.uses_position: result['position_context'] = context
        return result

    def ingest(self, candle, observed_ms, source='live'):
        if source not in ('live','recovered','warmup') or type(observed_ms) is not int or observed_ms<(candle.time+60)*1000:
            raise ValueError('Only closed candles with valid observation times may be evaluated')
        normalized=asdict(candle)
        normalized.update({key:float(normalized[key]) for key in ('open','high','low','close','volume')})
        raw = canonical(normalized).decode()
        if self.last is not None and candle.time<=self.last:
            with self.store.store.connect() as db:
                existing = db.execute('SELECT candle FROM live_candles WHERE session_id=? AND time=?',(self.id,candle.time)).fetchone()
            if existing and existing['candle']==raw:
                return []
            self.store.state(self.id,'ERROR','Conflicting previously recorded candle; revalidation required')
            raise RecoveryRequired('Conflicting or out-of-order candle')
        if self.last is not None and candle.time!=self.last+60:
            self.store.state(self.id,'RECOVERING DATA','Missing confirmed minute history')
            raise RecoveryRequired(f'Missing minute range {self.last+60}..{candle.time}')
        events=[]
        try:
            from terminal.position_management import position_context
            context = (self.position_provider(candle) if self.position_provider and source!='warmup' else position_context()) if self.uses_position else None
            result=self.evaluate(candle,context)
            with self.store.store.connect() as db:
                db.execute('INSERT INTO live_candles VALUES(?,?,?,?,?)',(self.id,candle.time,raw,source,observed_ms))
                if self.uses_position: db.execute('INSERT INTO live_position_contexts VALUES(?,?,?)',(self.id,candle.time,canonical(context).decode()))
                if result:db.execute('INSERT INTO live_evaluations VALUES(?,?,?)',(self.id,result['time'],canonical(result).decode()))
                for kind in result['transitions'] if result else []:
                    if source=='warmup':
                        continue
                    identity=hashlib.sha256(f'{self.id}:{result["time"]}:{kind}'.encode()).hexdigest()
                    event={'id':identity,'session_id':self.id,'strategy_id':self.snapshot['strategy_id'],
                           'strategy_sha256':self.snapshot['strategy_sha256'],'instrument':self.profile.symbol,
                           'market':self.profile.market,'timeframe':self.profile.primary_minutes,
                           'evaluation':self.profile.evaluation,'type':kind,'time':result['time'],
                           'observed_ms':observed_ms,'price':str(candle.close),'values':result['values'],'source':source}
                    pending=source=='live' and self.store.get(self.id)['status']=='CONNECTED'
                    db.execute('INSERT INTO live_signals VALUES(?,?,?,?,?)',
                               (identity,self.id,result['time'],canonical(event).decode(),'pending' if pending else 'suppressed'))
                    events.append(event)
                db.execute('UPDATE live_sessions SET last_minute=?,last_observed_ms=? WHERE id=?',(candle.time,observed_ms,self.id))
            self.last=candle.time
            self.latest=result or self.latest
            return events
        except Exception:
            self._restore()
            raise

    def verify_replay(self):
        """Compare recorded signal identity/time against fresh causal evaluation."""
        stream=SignalStream(GraphEvaluator(self.snapshot['graph']),self.profile.primary_minutes,self.profile.evaluation)
        atr_manager=None
        if self.profile.position_management is not None:
            from terminal.position_management import PositionManager
            atr_manager=PositionManager(self.profile)
        count=0
        with self.store.store.connect() as db:
            for row in db.execute('SELECT c.candle,c.source,p.context FROM live_candles c LEFT JOIN live_position_contexts p ON p.session_id=c.session_id AND p.time=c.time WHERE c.session_id=? ORDER BY c.time',(self.id,)):
                context = json.loads(row['context']) if row['context'] is not None else None
                candle=Candle(**json.loads(row['candle']))
                atr=atr_manager.observe_candle(candle) if atr_manager else None
                result=stream.update(candle,context)
                if result and atr_manager:result['values']['position_management.atr']=float(atr) if atr is not None else None
                if result:
                    saved=db.execute('SELECT evaluation FROM live_evaluations WHERE session_id=? AND time=?',(self.id,result['time'])).fetchone()
                    if saved is None or json.loads(saved['evaluation'])['values']!=result['values']:
                        return {'match':False,'time':result['time'],'checked_events':count}
                expected=set(result['transitions']) if result and row['source']!='warmup' else set()
                time=result['time'] if result else -1
                recorded={json.loads(r['event'])['type'] for r in db.execute('SELECT event FROM live_signals WHERE session_id=? AND time=?',(self.id,time))}
                if expected!=recorded:
                    return {'match':False,'time':time,'checked_events':count}
                count+=len(expected)
        return {'match':True,'checked_events':count}

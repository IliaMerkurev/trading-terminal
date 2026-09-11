"""Additive live journals. No credentials, user source execution or order API."""
from dataclasses import asdict
import hashlib
import json
import uuid

from terminal.data import canonical
from terminal.graph import GraphEvaluator
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

    def delivery(self, event_id, success):
        with self.store.connect() as db:
            db.execute("UPDATE live_signals SET delivery=? WHERE id=? AND delivery='claimed'",('sent' if success else 'failed',event_id))


class LiveSession:
    """Confirmed-minute journal and shared IR state; transport controls recovery.

    Construction always reconstructs silently and remains PAUSED. This is not
    auto-resume and cannot manufacture observed paper ticks lost while offline.
    """
    def __init__(self, store, session_id):
        self.store, self.id = store, identifier(session_id)
        self.snapshot = store.get(session_id)['snapshot']
        self.profile = Profile(**self.snapshot['profile'])
        self.last = None
        self.latest = None
        self._restore()
        store.state(self.id, 'PAUSED', 'Resume requires current history recovery and paper revalidation')

    def _restore(self):
        self.stream = SignalStream(GraphEvaluator(self.snapshot['graph']),self.profile.primary_minutes,self.profile.evaluation)
        self.last = None
        self.latest = None
        for candle in self.store.candles(self.id):
            self.latest = self.stream.update(candle) or self.latest
            self.last = candle.time

    def ingest(self, candle, observed_ms, source='live'):
        if source not in ('live','recovered','warmup') or type(observed_ms) is not int or observed_ms<(candle.time+60)*1000:
            raise ValueError('Only closed candles with valid observation times may be evaluated')
        raw = canonical(asdict(candle)).decode()
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
            result=self.stream.update(candle)
            with self.store.store.connect() as db:
                db.execute('INSERT INTO live_candles VALUES(?,?,?,?,?)',(self.id,candle.time,raw,source,observed_ms))
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
        count=0
        with self.store.store.connect() as db:
            for row in db.execute('SELECT candle,source FROM live_candles WHERE session_id=? ORDER BY time',(self.id,)):
                result=stream.update(Candle(**json.loads(row['candle'])))
                expected=set(result['transitions']) if result and row['source']!='warmup' else set()
                time=result['time'] if result else -1
                recorded={json.loads(r['event'])['type'] for r in db.execute('SELECT event FROM live_signals WHERE session_id=? AND time=?',(self.id,time))}
                if expected!=recorded:
                    return {'match':False,'time':time,'checked_events':count}
                count+=len(expected)
        return {'match':True,'checked_events':count}

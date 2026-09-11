"""Durable observed-price queue with asynchronous confirmed funding lookup.

When settlement publication is delayed, retain real observations and delay the
paper account. Never substitute an estimated/zero rate or stop live IR ingestion.
"""
import json
import threading
import time

from terminal.data import canonical
from terminal.paper import PaperEngine
from terminal.profile import dec


class PaperRecordingError(RuntimeError):
    pass


class FundingLookup:
    def __init__(self,fetch):
        self.fetch=fetch;self.lock=threading.Lock();self.values={};self.running=set();self.last={};self.attempts={}

    def get(self,boundary):
        with self.lock:
            if boundary in self.values:return self.values[boundary]
            if self.attempts.get(boundary,0)>=12:raise PaperRecordingError('Confirmed funding unavailable after bounded retries; review and recover')
            if boundary in self.running or time.monotonic()-self.last.get(boundary,-100)<10:return None
            self.running.add(boundary);self.last[boundary]=time.monotonic()
            self.attempts[boundary]=self.attempts.get(boundary,0)+1
            for old in list(self.last):
                if old<boundary and old not in self.running:
                    self.last.pop(old,None);self.values.pop(old,None);self.attempts.pop(old,None)
        def work():
            value=None
            try:value=self.fetch(boundary)
            except Exception:pass  # Fixed pending diagnostic only; never provider text.
            with self.lock:
                if value is not None:self.values[boundary]=str(dec(value))
                self.running.discard(boundary)
        threading.Thread(target=work,daemon=True).start()
        return None


class PaperJournal:
    MAX_OBSERVATIONS=250000

    def __init__(self,store,session_id,profile,funding_lookup):
        self.store,self.id,self.profile=store,session_id,profile
        self.lookup=funding_lookup
        self.engine=PaperEngine(profile)
        self.sequence=0;self.processed=0;self.previous_ns=None;self.next_funding=None
        self.waiting_funding=False
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS paper_inputs(session_id TEXT NOT NULL,sequence INTEGER NOT NULL,
                observation TEXT NOT NULL,funding_boundary INTEGER,next_funding INTEGER,PRIMARY KEY(session_id,sequence))''')
            try:
                for row in db.execute('SELECT sequence,observation,result FROM paper_observations WHERE session_id=? ORDER BY sequence',(session_id,)):
                    result=self.engine.observe(**json.loads(row['observation']))
                    if canonical(result)!=canonical(json.loads(row['result'])):
                        raise PaperRecordingError('Paper reconstruction differs from committed result')
                    self.processed=row['sequence']+1
                last=db.execute('SELECT * FROM paper_inputs WHERE session_id=? ORDER BY sequence DESC LIMIT 1',(session_id,)).fetchone()
                if last:
                    self.sequence=last['sequence']+1
                    self.previous_ns=json.loads(last['observation'])['time_ns']
                    self.next_funding=last['next_funding']
                else:
                    # Older 0.3 development journals have only completed inputs.
                    self.sequence=self.processed;self.previous_ns=self.engine.last_ns
            except Exception:
                self.engine.close();raise

    def append(self,price,signals=None):
        if self.sequence>=self.MAX_OBSERVATIONS:
            raise PaperRecordingError('Paper observation budget reached; pause and review')
        timestamp=max(price['observed_ms']*1000000,(self.previous_ns or 0)+1)
        boundary=None
        upcoming=price.get('next_funding_ms')
        if self.profile.market=='linear' and self.profile.funding_mode=='history':
            if not price.get('mark') or type(upcoming) is not int:
                raise PaperRecordingError('Separate mark and funding schedule required for perpetual paper')
            if self.next_funding is not None and price['provider_ms']>=self.next_funding:
                if price['provider_ms']-self.next_funding>60000:
                    raise PaperRecordingError('Funding boundary was not observed continuously; historical revalidation required')
                boundary=self.next_funding
                self.next_funding=None
            if upcoming>price['provider_ms']:
                self.next_funding=upcoming
        observation={'time_ns':timestamp,'price':price['price'],'mark':price['mark'],'signals':signals}
        try:
            with self.store.connect() as db:
                db.execute('INSERT INTO paper_inputs VALUES(?,?,?,?,?)',(self.id,self.sequence,canonical(observation).decode(),boundary,self.next_funding))
        except Exception:
            raise PaperRecordingError('Paper input could not be recorded') from None
        self.previous_ns=timestamp;self.sequence+=1

    def process(self,max_items=32):
        results=[]
        for _ in range(max_items):
            with self.store.connect() as db:
                row=db.execute('SELECT * FROM paper_inputs WHERE session_id=? AND sequence=?',(self.id,self.processed)).fetchone()
            if row is None:break
            observation=json.loads(row['observation'])
            boundary=row['funding_boundary']
            if boundary is not None:
                rate=self.lookup.get(boundary)
                if rate is None:
                    self.waiting_funding=True
                    return results
                observation['funding_rate']=rate
            try:
                result=self.engine.observe(**observation)
                with self.store.connect() as db:
                    db.execute('INSERT INTO paper_observations VALUES(?,?,?,?)',
                               (self.id,self.processed,canonical(observation).decode(),canonical(result).decode()))
            except Exception:
                self.engine.close()
                raise PaperRecordingError('Paper result could not be committed; reconstruct before continuing') from None
            self.processed+=1;self.waiting_funding=False;results.append(result)
        return results

    def snapshot(self):
        return {**self.engine.snapshot(),'pending_observations':self.sequence-self.processed,'waiting_funding':self.waiting_funding}

    def close(self):self.engine.close()

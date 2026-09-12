"""Bounded public-market presentation state; never evaluates strategies or orders."""
from collections import deque
from decimal import Decimal, InvalidOperation
import threading
import time


def number(value, *, zero=False):
    if not isinstance(value, str) or len(value)>64:
        raise ValueError('Invalid public numeric field')
    try: result=Decimal(value)
    except InvalidOperation: raise ValueError('Invalid public numeric field') from None
    if not result.is_finite() or result<0 or (not zero and result==0):
        raise ValueError('Invalid public numeric range')
    return result


class OrderBook:
    """Depth-50 snapshot/delta state. Update IDs are monotonic, not contiguous."""
    def __init__(self):self.reset()

    def reset(self):
        self.bids={};self.asks={};self.valid=False
        self.update_id=-1;self.sequence=-1;self.timestamp=-1

    def apply(self,kind,data,timestamp):
        update,sequence=data.get('u'),data.get('seq')
        if kind not in ('snapshot','delta') or type(update) is not int or type(sequence) is not int:
            raise ValueError('Invalid book envelope')
        if update<1 or sequence<0:raise ValueError('Invalid book sequence')
        if kind=='delta' and (not self.valid or update==1):
            self.reset();raise ValueError('Order book requires a fresh snapshot')
        if self.valid and (timestamp<self.timestamp or (update!=1 and (update<=self.update_id or sequence<self.sequence))):
            return False
        # Validate the complete update before publishing any changed levels.
        sides=[]
        for field,previous in (('b',self.bids),('a',self.asks)):
            rows=data.get(field)
            if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Invalid book depth')
            levels={} if kind=='snapshot' else previous.copy()
            for row in rows:
                if not isinstance(row,list) or len(row)!=2:raise ValueError('Invalid book level')
                price,size=number(row[0]),number(row[1],zero=True)
                if size==0:levels.pop(price,None)
                else:levels[price]=size
            # Store only the subscribed depth, never an unbounded price map.
            sides.append(dict(sorted(levels.items(),reverse=field=='b')[:50]))
        bids,asks=sides
        if not bids or not asks or max(bids)>=min(asks):
            self.reset();raise ValueError('Invalid or crossed order book')
        self.bids,self.asks=bids,asks
        self.update_id,self.sequence,self.timestamp=update,sequence,timestamp
        self.valid=True
        return True

    def snapshot(self):
        return {'valid':self.valid,'time':self.timestamp,
                'bids':[[str(p),str(q)] for p,q in sorted(self.bids.items(),reverse=True)[:15]],
                'asks':[[str(p),str(q)] for p,q in sorted(self.asks.items())[:15]]}


class MarketState:
    TAPE_LIMIT=100
    def __init__(self):
        self.lock=threading.RLock()
        self.counts={key:0 for key in ('connections','ticker','forming','candles','book','trades')}
        self.reset()

    def reset(self):
        with self.lock:
            self.book=OrderBook();self.ticker={};self.ticker_at=None;self.book_at=None
            self.trades=deque(maxlen=self.TAPE_LIMIT);self.trade_ids=deque(maxlen=2048);self.seen=set()
            self.trade_at=None;self.generation=self.counts['connections']

    def connected(self):
        self.reset()
        with self.lock:self.counts['connections']+=1;self.generation=self.counts['connections']

    def ticker_update(self,values,timestamp):
        with self.lock:
            self.ticker={**values,'time':timestamp};self.ticker_at=time.monotonic();self.counts['ticker']+=1

    def book_update(self,kind,data,timestamp):
        with self.lock:
            if self.book.apply(kind,data,timestamp):
                self.book_at=time.monotonic();self.counts['book']+=1

    def trade_update(self,rows,symbol,observed_ms):
        if not isinstance(rows,list) or len(rows)>1024:raise ValueError('Invalid trade batch')
        normalized=[]
        for row in rows:
            if row.get('s')!=symbol or row.get('S') not in ('Buy','Sell'):
                raise ValueError('Invalid trade instrument or side')
            identity,timestamp=row.get('i'),row.get('T')
            if not isinstance(identity,str) or not 1<=len(identity)<=128 or type(timestamp) is not int:
                raise ValueError('Invalid trade identity')
            if timestamp>observed_ms+5000 or timestamp<observed_ms-90000:continue
            normalized.append({'id':identity,'time':timestamp,'price':str(number(row.get('p'))),
                               'size':str(number(row.get('v'))),'side':row['S']})
        with self.lock:
            accepted=[]
            for row in normalized:
                if row['id'] in self.seen:continue
                if len(self.trade_ids)==self.trade_ids.maxlen:self.seen.discard(self.trade_ids[0])
                self.trade_ids.append(row['id']);self.seen.add(row['id']);accepted.append(row)
            if accepted:
                self.trades=deque(sorted([*self.trades,*accepted],key=lambda r:(r['time'],r['id']))[-self.TAPE_LIMIT:],maxlen=self.TAPE_LIMIT)
                self.trade_at=time.monotonic();self.counts['trades']+=len(accepted)

    def count(self,key):
        with self.lock:self.counts[key]+=1

    def snapshot(self):
        with self.lock:
            now=time.monotonic()
            age=lambda at:None if at is None else round(max(0,now-at),2)
            ticker_age,book_age=age(self.ticker_at),age(self.book_at)
            return {'ticker':self.ticker.copy(),'book':self.book.snapshot(),'trades':list(reversed(self.trades)),
                    'ticker_age':ticker_age,'book_age':book_age,'trade_age':age(self.trade_at),
                    'fresh':ticker_age is not None and ticker_age<=15 and book_age is not None and book_age<=15 and self.book.valid,
                    'counts':self.counts.copy(),'generation':self.generation,
                    'tape_note':'Recent observed trades only; missed tape is not recovered.'}

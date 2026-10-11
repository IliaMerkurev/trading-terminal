"""Workspace-local, bounded chart annotations; never strategy or execution data."""
import copy
import json
import math
import re
import threading
from terminal.data import canonical, validate_symbol
from terminal.market_sources import cache_market

KINDS = {'horizontal', 'vertical', 'trend', 'ray', 'rectangle', 'fib', 'text'}
MAX_DRAWINGS = 100


def validate_drawings(items):
    if not isinstance(items, list) or len(items) > MAX_DRAWINGS:
        raise ValueError('Use at most 100 drawings')
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {'id', 'kind', 'anchors', 'color', 'width', 'style', 'text', 'visible', 'locked'}:
            raise ValueError('Invalid drawing fields')
        if not isinstance(item['id'], str) or not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,63}', item['id']) or item['id'] in seen:
            raise ValueError('Drawing IDs must be unique')
        seen.add(item['id'])
        if not isinstance(item['kind'], str) or item['kind'] not in KINDS:
            raise ValueError('Invalid drawing kind')
        count = 1 if item['kind'] in ('horizontal', 'vertical', 'text') else 2
        if not isinstance(item['anchors'], list) or len(item['anchors']) != count:
            raise ValueError('Invalid drawing anchors')
        for anchor in item['anchors']:
            if not isinstance(anchor, dict) or set(anchor) != {'time', 'price'}:
                raise ValueError('Invalid anchor fields')
            for key, limit in (('time', 253402300799), ('price', 1e15)):
                value = anchor[key]
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= limit:
                    raise ValueError('Invalid anchor coordinate')
        if not isinstance(item['color'], str) or not re.fullmatch('#[0-9a-fA-F]{6}', item['color']):
            raise ValueError('Invalid drawing color')
        if type(item['width']) is not int or not 1 <= item['width'] <= 4 or item['style'] not in ('solid', 'dashed', 'dotted'):
            raise ValueError('Invalid drawing stroke')
        if type(item['visible']) is not bool or type(item['locked']) is not bool:
            raise ValueError('Invalid drawing visibility or lock')
        if not isinstance(item['text'], str) or len(item['text']) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in item['text']):
            raise ValueError('Use up to 200 printable characters for annotation text')
    return copy.deepcopy(items)


class ChartDrawings:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS chart_drawings_v1(market TEXT NOT NULL,symbol TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(market,symbol))')

    def key(self, market, symbol, source):
        if market not in ('spot', 'linear'):
            raise ValueError('Unsupported chart market')
        validate_symbol(symbol)
        return cache_market(market, source), symbol

    def settings(self, market, symbol, source='bybit'):
        key = self.key(market, symbol, source)
        with self.store.connect() as db:
            row = db.execute('SELECT document FROM chart_drawings_v1 WHERE market=? AND symbol=?', key).fetchone()
        if not row:
            return dict(version=1, revision=0, drawings=[])
        doc = json.loads(row[0])
        if set(doc) != {'version', 'revision', 'drawings'} or type(doc['version']) is not int or doc['version'] != 1 or type(doc['revision']) is not int or doc['revision'] < 0:
            raise ValueError('Saved drawings are invalid; existing data was preserved')
        validate_drawings(doc['drawings'])
        return doc

    def save(self, market, symbol, drawings, revision, source='bybit'):
        key = self.key(market, symbol, source)
        valid = validate_drawings(drawings)
        if type(revision) is not int or revision < 0:
            raise ValueError('Invalid drawings revision')
        with self.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT document FROM chart_drawings_v1 WHERE market=? AND symbol=?', key).fetchone()
            previous = json.loads(row[0]) if row else {'revision': 0}
            if previous.get('revision') != revision:
                raise ValueError('Drawings changed elsewhere; reload drawings before editing')
            doc = dict(version=1, revision=revision + 1, drawings=valid)
            db.execute('INSERT OR REPLACE INTO chart_drawings_v1 VALUES(?,?,?)', (*key, canonical(doc).decode()))
        return doc

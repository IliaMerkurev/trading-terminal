"""Typed, bounded Strategy IR and causal native-indicator evaluation."""
import copy
import math
import re

from nautilus_trader.indicators import (SimpleMovingAverage, ExponentialMovingAverage,
    RelativeStrengthIndex, BollingerBands, MovingAverageConvergenceDivergence,
    AverageTrueRange, MovingAverageType)

OUTPUTS = ("entry_long", "exit_long", "entry_short", "exit_short")
NUMBER = "number"
BOOLEAN = "boolean"
PORTS = {
    "price":{"value":NUMBER}, "constant":{"value":NUMBER},
    "sma":{"value":NUMBER}, "ema":{"value":NUMBER}, "rsi":{"value":NUMBER},
    "bb":{"upper":NUMBER,"middle":NUMBER,"lower":NUMBER},
    "macd":{"macd":NUMBER,"signal":NUMBER,"histogram":NUMBER}, "atr":{"value":NUMBER},
    **{k:{"value":BOOLEAN} for k in ("compare","cross_above","cross_below","and","or","not")},
}
INPUTS = {k:{} for k in ("price","constant","atr")}
INPUTS.update({k:{"source":NUMBER} for k in ("sma","ema","rsi","bb","macd")})
INPUTS.update({k:{"left":NUMBER,"right":NUMBER} for k in ("compare","cross_above","cross_below")})
INPUTS.update({k:{"left":BOOLEAN,"right":BOOLEAN} for k in ("and","or")})
INPUTS["not"] = {"source":BOOLEAN}
PARAMS = {"price":{"field"}, "constant":{"value"}, "compare":{"operator"},
          "bb":{"period","deviations"}, "macd":{"fast","slow","signal"},
          **{k:{"period"} for k in ("sma","ema","rsi","atr")},
          **{k:set() for k in ("cross_above","cross_below","and","or","not")}}


class GraphError(ValueError):
    pass


def number(value):
    try:
        valid = not isinstance(value,bool) and isinstance(value,(float,int)) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise GraphError("Expected a finite numeric graph parameter")
    return value


def validate_graph(graph,allow_incomplete=False):
    if not isinstance(graph,dict) or set(graph) != {"version","nodes","outputs"} or type(graph["version"]) is not int or graph["version"] != 1:
        raise GraphError("Expected Strategy IR version 1; layout is stored separately")
    if not isinstance(graph["nodes"],list) or not (0 if allow_incomplete else 1) <= len(graph["nodes"]) <= 128:
        raise GraphError("Graph must contain 1–128 nodes")
    nodes = {}
    for node in graph["nodes"]:
        if not isinstance(node,dict) or set(node) != {"id","type","inputs","params"}:
            raise GraphError("Invalid node fields")
        ident = node["id"]
        if not isinstance(ident,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}",ident) or ident in nodes:
            raise GraphError("Node IDs must be unique stable identifiers")
        kind = node["type"]
        if not isinstance(kind,str) or kind not in PORTS or not isinstance(node["inputs"],dict) or set(node["inputs"]) != set(INPUTS[kind]):
            raise GraphError("Unsupported node type or input ports")
        params = node["params"]
        if not isinstance(params,dict) or set(params) != PARAMS[kind]:
            raise GraphError(f"Invalid parameters for {kind}")
        for key in ("period","fast","slow","signal"):
            if key in params and (type(params[key]) is not int or not 1 <= params[key] <= 10000):
                raise GraphError("Indicator periods must be integers from 1 to 10000")
        if kind == "macd" and params["fast"] >= params["slow"]:
            raise GraphError("MACD fast period must be below slow period")
        if kind == "constant":
            number(params["value"])
        if kind == "bb" and not 0 < number(params["deviations"]) <= 10:
            raise GraphError("Bollinger deviations must be in (0, 10]")
        if kind == "price" and params["field"] not in ("open","high","low","close","volume"):
            raise GraphError("Unsupported OHLCV field")
        if kind == "compare" and params["operator"] not in (">",">=","<","<=","==","!="):
            raise GraphError("Unsupported comparison")
        nodes[ident] = node
    def reference(ref, expected):
        if not isinstance(ref,str) or ref.count(".") != 1:
            raise GraphError("References must identify node.output")
        ident, port = ref.split(".")
        if ident not in nodes or PORTS[nodes[ident]["type"]].get(port) != expected:
            raise GraphError(f"Unknown reference or incompatible port: {ref}")
        return ident
    dependencies = {}
    for ident,node in nodes.items():
        dependencies[ident] = [reference(ref,INPUTS[node["type"]][port]) for port,ref in node["inputs"].items() if not (allow_incomplete and ref=='')]
    if not isinstance(graph["outputs"],dict) or set(graph["outputs"]) != set(OUTPUTS):
        raise GraphError("Graph must define all four output blocks (unused blocks may be null)")
    for ref in graph["outputs"].values():
        if ref is not None:
            reference(ref,BOOLEAN)
    order, visiting, visited = [],set(),set()
    def visit(ident):
        if ident in visiting:
            raise GraphError("Graph cycles are forbidden")
        if ident in visited:
            return
        visiting.add(ident)
        for dependency in dependencies[ident]:
            visit(dependency)
        visiting.remove(ident)
        visited.add(ident)
        order.append(ident)
    for ident in nodes:
        visit(ident)
    return order


def indicator_for(node):
    p, kind = node["params"], node["type"]
    if kind == "sma": return SimpleMovingAverage(p["period"])
    if kind == "ema": return ExponentialMovingAverage(p["period"])
    if kind == "rsi": return RelativeStrengthIndex(p["period"],MovingAverageType.WILDER)
    if kind == "bb": return BollingerBands(p["period"],p["deviations"])
    if kind == "atr": return AverageTrueRange(p["period"],MovingAverageType.WILDER)
    if kind == "macd":
        return (MovingAverageConvergenceDivergence(p["fast"],p["slow"]),ExponentialMovingAverage(p["signal"]))
    return None


class GraphEvaluator:
    """Clone committed primary-bar indicator state for each forming update.

    Commit only a completed primary bar; keep cross history per evaluation step.
    Thus repeated H1 partials do not advance the H1 EMA/RSI recurrence repeatedly.
    """
    def __init__(self, graph):
        self.graph = copy.deepcopy(graph)
        self.order = validate_graph(self.graph)
        self.nodes = {node["id"]:node for node in self.graph["nodes"]}
        self.states = {ident:indicator_for(node) for ident,node in self.nodes.items()}
        self.previous = {}
        self.last_time = None
        self.last_commit = None

    def __call__(self, bars, time, complete):
        if self.last_time is not None and time <= self.last_time:
            raise GraphError("Evaluation timestamps must increase")
        self.last_time = time
        if not bars:
            return {"values":{}, "signals":{k:False for k in OUTPUTS}}
        candle = bars[-1]
        if complete and self.last_commit == candle.time:
            raise GraphError("A primary bar cannot be committed twice")
        values = {}
        states = {}
        for ident in self.order:
            node = self.nodes[ident]
            kind,params = node["type"],node["params"]
            inputs = {port:values[ref] for port,ref in node["inputs"].items()}
            result = {port:None for port in PORTS[kind]}
            state = copy.deepcopy(self.states[ident])
            if kind == "price":
                result["value"] = getattr(candle,params["field"])
            elif kind == "constant":
                result["value"] = params["value"]
            elif kind in ("sma","ema","rsi","bb","macd","atr"):
                source = inputs.get("source")
                if kind == "atr":
                    state.update_raw(candle.high,candle.low,candle.close)
                elif source is not None:
                    if kind == "bb": state.update_raw(source,source,source)
                    elif kind == "macd":
                        line,signal = state
                        line.update_raw(source)
                        if line.initialized: signal.update_raw(line.value)
                    else: state.update_raw(source)
                if kind == "macd":
                    line,signal = state
                    if line.initialized and source is not None:
                        result["macd"] = line.value
                        if signal.initialized:
                            result["signal"],result["histogram"] = signal.value,line.value-signal.value
                elif state.initialized and (source is not None or kind == "atr"):
                    if kind == "bb": result = {"upper":state.upper,"middle":state.middle,"lower":state.lower}
                    else: result["value"] = state.value * (100 if kind == "rsi" else 1)
                states[ident] = state
            elif kind == "not":
                result["value"] = None if inputs["source"] is None else not inputs["source"]
            elif kind in ("and","or"):
                a,b = inputs["left"],inputs["right"]
                if kind == "and": result["value"] = False if a is False or b is False else (None if a is None or b is None else True)
                else: result["value"] = True if a is True or b is True else (None if a is None or b is None else False)
            elif all(v is not None for v in inputs.values()):
                a,b = inputs["left"],inputs["right"]
                if kind == "compare":
                    result["value"] = {">":a>b,">=":a>=b,"<":a<b,"<=":a<=b,"==":a==b,"!=":a!=b}[params["operator"]]
                else:
                    pa = self.previous.get(node["inputs"]["left"])
                    pb = self.previous.get(node["inputs"]["right"])
                    result["value"] = False if pa is None or pb is None else (pa <= pb and a > b if kind == "cross_above" else pa >= pb and a < b)
            for port,value in result.items():
                if isinstance(value,float) and not math.isfinite(value):
                    raise GraphError("Indicator produced a non-finite value")
                values[f"{ident}.{port}"] = value
        if complete:
            self.states.update(states)
            self.last_commit = candle.time
        self.previous = values
        return {"values":values,"signals":{key:values.get(ref) is True for key,ref in self.graph["outputs"].items()}}


def example_graph():
    """Synthetic demonstration only: close relative to a two-primary-bar SMA."""
    return {"version":1,"nodes":[
        {"id":"close","type":"price","inputs":{},"params":{"field":"close"}},
        {"id":"mean","type":"sma","inputs":{"source":"close.value"},"params":{"period":2}},
        {"id":"above","type":"compare","inputs":{"left":"close.value","right":"mean.value"},"params":{"operator":">"}},
        {"id":"below","type":"compare","inputs":{"left":"close.value","right":"mean.value"},"params":{"operator":"<"}},
    ],"outputs":{"entry_long":"above.value","exit_long":"below.value","entry_short":None,"exit_short":None}}

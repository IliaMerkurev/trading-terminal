import copy
from dataclasses import replace
from decimal import Decimal
import unittest

from terminal.graph import GraphEvaluator, GraphError, OUTPUTS, validate_graph, example_graph
from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


def node(ident,kind,inputs=None,**params):
    return {"id":ident,"type":kind,"inputs":inputs or {},"params":params}


def graph(nodes, **outputs):
    return {"version":1,"nodes":nodes,"outputs":{k:outputs.get(k) for k in OUTPUTS}}


def run_values(ir,prices):
    evaluator=GraphEvaluator(ir)
    bars=[]
    results=[]
    for i,price in enumerate(prices):
        bars.append(Candle(i*60,price,price,price,price,1))
        results.append(evaluator(bars,(i+1)*60,True))
    return results


class GraphTests(unittest.TestCase):
    def test_native_indicator_values_match_independent_arithmetic(self):
        ir=graph([node("p","price",field="close"),
            node("sma","sma",{"source":"p.value"},period=3),
            node("ema","ema",{"source":"p.value"},period=3),
            node("bb","bb",{"source":"p.value"},period=2,deviations=2)])
        values=run_values(ir,[10,12,14])[-1]["values"]
        self.assertEqual(values["sma.value"],12)
        self.assertEqual(values["ema.value"],12.5)
        self.assertEqual(values["bb.middle"],13)
        self.assertEqual(values["bb.upper"],15)
        self.assertEqual(values["bb.lower"],11)

    def test_wilder_rsi_initialization_and_scale_are_explicit(self):
        ir=graph([node("p","price",field="close"),node("r","rsi",{"source":"p.value"},period=2)])
        results=run_values(ir,[10,12,11])
        self.assertIsNone(results[0]["values"]["r.value"])
        # Native Wilder gain/loss recurrence seeded at zero: gain=.5, loss=.5.
        self.assertEqual(results[-1]["values"]["r.value"],50)

    def test_wilder_atr_uses_previous_close(self):
        evaluator=GraphEvaluator(graph([node("a","atr",period=2)]))
        bars=[Candle(0,10,12,8,10,1),Candle(60,12,15,10,12,1),Candle(120,11,13,9,11,1)]
        values=[evaluator(bars[:i+1],(i+1)*60,True)["values"]["a.value"] for i in range(3)]
        self.assertEqual(values,[None,4.5,4.25])

    def test_macd_signal_and_histogram_are_distinct_outputs(self):
        ir=graph([node("p","price",field="close"),node("m","macd",{"source":"p.value"},fast=2,slow=3,signal=2)])
        results=run_values(ir,[10,12,14,16])
        self.assertAlmostEqual(results[2]["values"]["m.macd"],11/18)
        self.assertIsNone(results[2]["values"]["m.signal"])
        self.assertAlmostEqual(results[3]["values"]["m.macd"],85/108)
        self.assertAlmostEqual(results[3]["values"]["m.signal"],59/81)
        self.assertAlmostEqual(results[3]["values"]["m.histogram"],19/324)

    def test_crosses_use_previous_evaluation_and_equality_boundary(self):
        ir=graph([node("p","price",field="close"),node("k","constant",value=10),
            node("a","cross_above",{"left":"p.value","right":"k.value"}),
            node("b","cross_below",{"left":"p.value","right":"k.value"})],entry_long="a.value",entry_short="b.value")
        results=run_values(ir,[9,10,11,12,10,9])
        self.assertEqual([r["signals"]["entry_long"] for r in results],[False,False,True,False,False,False])
        self.assertEqual([r["signals"]["entry_short"] for r in results],[False,False,False,False,False,True])

    def test_boolean_logic_does_not_invert_unknown_warmup_into_entry(self):
        ir=graph([node("p","price",field="close"),node("s","sma",{"source":"p.value"},period=3),
            node("c","compare",{"left":"p.value","right":"s.value"},operator=">"),
            node("n","not",{"source":"c.value"}),
            node("a","and",{"left":"c.value","right":"n.value"}),
            node("o","or",{"left":"c.value","right":"n.value"})],entry_long="n.value",exit_long="o.value")
        results=run_values(ir,[10,12,14])
        self.assertIsNone(results[0]["values"]["n.value"])
        self.assertFalse(results[0]["signals"]["entry_long"])
        self.assertFalse(results[2]["values"]["a.value"])
        self.assertTrue(results[2]["values"]["o.value"])

    def test_partial_ema_is_recomputed_from_committed_state(self):
        ir=graph([node("p","price",field="close"),node("e","ema",{"source":"p.value"},period=2)])
        evaluator=GraphEvaluator(ir)
        first=Candle(0,100,100,100,100,60)
        evaluator([first],3600,True)
        partial=Candle(3600,130,130,130,130,1)
        a=evaluator([first,partial],3660,False)["values"]["e.value"]
        b=evaluator([first,partial],3720,False)["values"]["e.value"]
        self.assertAlmostEqual(a,120)
        self.assertEqual(a,b)
        final=Candle(3600,130,130,90,90,60)
        self.assertAlmostEqual(evaluator([first,final],7200,True)["values"]["e.value"],280/3)

    def test_intrabar_signal_disappears_and_actual_engine_modes_differ(self):
        ir=graph([node("p","price",field="close"),node("s","sma",{"source":"p.value"},period=2),
            node("k","constant",value=110),
            node("a","compare",{"left":"s.value","right":"k.value"},operator=">"),
            node("b","compare",{"left":"s.value","right":"k.value"},operator="<")],entry_long="a.value",exit_long="b.value")
        data=[Candle(i*60,p,p,p,p,100) for i,p in enumerate([100]*60+[130]*30+[90]*30)]
        profile=Profile(evaluation="intrabar",fee_rate="0")
        result=run_backtest(data,profile,GraphEvaluator(ir))
        closed=run_backtest(data,replace(profile,evaluation="closed"),GraphEvaluator(ir))
        self.assertEqual(result["metrics"]["trade_count"],1)
        self.assertEqual(closed["metrics"]["trade_count"],0)
        self.assertEqual(Decimal(result["metrics"]["net_pnl"]),Decimal("-30.760"))
        self.assertEqual(result["indicators"][60]["values"]["s.value"],115)
        self.assertEqual(result["indicators"][-1]["values"]["s.value"],95)
        changed=data[:90]+[Candle(i*60,999,999,999,999,100) for i in range(90,120)]
        future=run_backtest(changed,profile,GraphEvaluator(ir))
        self.assertEqual(result["indicators"][:90],future["indicators"][:90])
        cutoff=90*60*1_000_000_000
        self.assertEqual([f for f in result["fills"] if f["time_ns"]<cutoff],
                         [f for f in future["fills"] if f["time_ns"]<cutoff])

    def test_validation_rejects_cycles_bad_types_and_executable_nodes(self):
        valid=example_graph()
        malformed=[]
        bad=copy.deepcopy(valid); bad["nodes"][1]["inputs"]["source"]="mean.value"; malformed.append(bad)
        bad=copy.deepcopy(valid); bad["nodes"][1]["inputs"]["source"]="above.value"; malformed.append(bad)
        bad=copy.deepcopy(valid); bad["nodes"][0]["type"]="eval"; malformed.append(bad)
        bad=copy.deepcopy(valid); bad["nodes"].append(copy.deepcopy(bad["nodes"][0])); malformed.append(bad)
        bad=copy.deepcopy(valid); bad["outputs"]["entry_long"]="close.value"; malformed.append(bad)
        bad=copy.deepcopy(valid); bad["layout"]={}; malformed.append(bad)
        for ir in malformed:
            with self.assertRaises(GraphError): validate_graph(ir)

    def test_snapshot_is_independent_of_live_editor_changes(self):
        ir=example_graph()
        evaluator=GraphEvaluator(ir)
        ir["nodes"][1]["params"]["period"]=999
        self.assertEqual(evaluator.graph["nodes"][1]["params"]["period"],2)

    def test_dependent_indicator_waits_for_its_source(self):
        ir=graph([node("p","price",field="close"),node("s","sma",{"source":"p.value"},period=2),
                  node("e","ema",{"source":"s.value"},period=2)])
        results=run_values(ir,[10,12,14])
        self.assertIsNone(results[1]["values"]["e.value"])
        self.assertAlmostEqual(results[2]["values"]["e.value"],37/3)

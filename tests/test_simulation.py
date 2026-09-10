from dataclasses import replace
from decimal import Decimal
import unittest

from terminal.profile import Profile
from terminal.series import Candle
from terminal.simulation import run_backtest


def flat(prices):
    return [Candle(i*60,p,p,p,p,100) for i,p in enumerate(prices)]


def signal_map(mapping):
    return lambda bars, time, complete: {"signals":mapping.get(time, {}), "values":{}}


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(primary_minutes=1, allocation="100", fee_rate="0")
        self.signals = signal_map({60:{"entry_long":True},180:{"exit_long":True}})

    def test_spot_independent_balance_and_trade_metrics(self):
        result = run_backtest(flat([100,100,110]), replace(self.profile,fee_rate="0.001"), self.signals)
        self.assertEqual(Decimal(result["metrics"]["final_equity"]),Decimal("1009.79"))
        self.assertEqual(result["metrics"]["trade_count"],1)
        self.assertEqual(Decimal(result["trades"][0]["net_pnl"]),Decimal("9.79"))

    def test_futures_leverage_changes_quantity_not_pnl_formula(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10")
        data = flat([100,100,110])
        for short, expected in [(False,"1010"),(True,"990")]:
            name = "short" if short else "long"
            result = run_backtest(data,profile,signal_map({60:{f"entry_{name}":True},180:{f"exit_{name}":True}}),
                                  marks={c.time:c for c in data},funding={})
            self.assertEqual(Decimal(result["metrics"]["final_equity"]),Decimal(expected))
            self.assertEqual(Decimal(result["fills"][0]["quantity"]),Decimal(1))

    def test_funding_at_boundary_is_charged_once_to_held_position(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10")
        data = flat([100,100,100])
        for short, expected in [(False,"999"),(True,"1001")]:
            name = "short" if short else "long"
            result = run_backtest(data,profile,signal_map({60:{f"entry_{name}":True},180:{f"exit_{name}":True}}),
                                  marks={c.time:c for c in data},funding={60:"0.01"})
            self.assertEqual(Decimal(result["metrics"]["final_equity"]),Decimal(expected))
            self.assertEqual(len(result["events"]),1)

    def test_mark_liquidation_precedes_protection_for_both_sides(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",capital="20",maintenance_rate="0.05",stop_loss="0.05")
        data = flat([100,100,100])
        for short, mark in [(False,80),(True,120)]:
            marks = {c.time:c for c in flat([100,mark,mark])}
            name = "short" if short else "long"
            result = run_backtest(data,profile,signal_map({60:{f"entry_{name}":True}}),marks=marks,funding={})
            self.assertEqual(result["fills"][1]["reason"],"liquidation")
            self.assertEqual(Decimal(result["metrics"]["final_equity"]),Decimal(20))
            self.assertEqual(result["metrics"]["trade_count"],1)

    def test_spot_100_percent_reserves_fee_without_borrowing(self):
        profile = replace(self.profile,sizing="percent",allocation="100",fee_rate="0.001")
        result = run_backtest(flat([100,100]),profile,signal_map({60:{"entry_long":True}}))
        self.assertEqual(Decimal(result["fills"][0]["quantity"]),Decimal("9.99"))
        self.assertTrue(all(Decimal(p["cash"])>=0 for p in result["equity"]))
        self.assertEqual(Decimal(result["metrics"]["final_equity"]),Decimal("998.002"))

    def test_repeated_or_opposite_entries_do_not_scale_or_reverse(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",mark_mode="last_proxy",funding_mode="assumed_zero")
        result = run_backtest(flat([100,101,102,103]),profile,signal_map({
            60:{"entry_long":True},120:{"entry_long":True},180:{"entry_short":True},240:{"exit_long":True,"entry_short":True}}))
        self.assertEqual(len(result["fills"]),2)
        self.assertEqual(result["fills"][1]["reason"],"signal")

    def test_simultaneous_flat_entries_skip_and_log(self):
        result = run_backtest(flat([100,110]),self.profile,signal_map({60:{"entry_long":True,"entry_short":True}}))
        self.assertEqual(result["fills"],[])
        self.assertIn("Simultaneous",result["diagnostics"][0]["message"])

    def test_bar_path_determines_first_stop_or_take_sample(self):
        data = [Candle(0,100,100,100,100,100),Candle(60,100,120,80,100,100)]
        for path,reason,price in [("OLHC","stop_loss",80),("OHLC","take_profit",120)]:
            profile = replace(self.profile,path=path,stop_loss="0.05",take_profit="0.05")
            result = run_backtest(data,profile,signal_map({60:{"entry_long":True}}))
            self.assertEqual(result["fills"][1]["reason"],reason)
            self.assertEqual(Decimal(result["fills"][1]["price"]),price)

    def test_gap_exit_uses_observed_open_not_unavailable_stop_price(self):
        data = [Candle(0,100,100,100,100,100),Candle(180,80,80,80,80,100)]
        profile = replace(self.profile,gap_policy="skip",stop_loss="0.05")
        result = run_backtest(data,profile,signal_map({60:{"entry_long":True}}))
        self.assertEqual(result["gaps"],[(60,180)])
        self.assertEqual(Decimal(result["fills"][1]["price"]),80)
        with self.assertRaisesRegex(ValueError,"Missing minute"):
            run_backtest(data,replace(profile,evaluation="intrabar"),self.signals)

    def test_profile_slippage_changes_executable_prices(self):
        result = run_backtest(flat([100,100,110]),replace(self.profile,slippage="0.01"),self.signals)
        self.assertEqual(Decimal(result["fills"][0]["price"]),101)
        self.assertEqual(Decimal(result["fills"][1]["price"]),Decimal("108.90"))
        self.assertEqual(Decimal(result["fills"][0]["quantity"]),Decimal("0.990"))
        self.assertEqual(Decimal(result["metrics"]["net_pnl"]),Decimal("7.821"))

    def test_missing_cost_or_mark_history_fails_visibly(self):
        profile = replace(self.profile,market="linear")
        data = flat([100,100])
        with self.assertRaisesRegex(ValueError,"mark history"):
            run_backtest(data,profile,self.signals)
        with self.assertRaisesRegex(ValueError,"Funding history"):
            run_backtest(data,profile,self.signals,marks={c.time:c for c in data})

    def test_identical_snapshots_produce_identical_normalized_results(self):
        a = run_backtest(flat([100,100,110]),self.profile,self.signals)
        b = run_backtest(flat([100,100,110]),self.profile,self.signals)
        self.assertEqual(a,b)

    def test_rounding_minimums_and_allocation_rejection(self):
        profile = replace(self.profile,quantity_step="0.03",min_quantity="0.03")
        self.assertEqual(profile.size(1000,110),Decimal("0.90"))
        self.assertEqual(profile.size(50,100),Decimal(0))
        self.assertEqual(replace(profile,min_notional="200").size(1000,100),Decimal(0))

    def test_invalid_profile_values_are_not_silently_coerced(self):
        for change in ({"capital":"NaN"},{"leverage":"2"},{"slippage":"-1"},{"sizing":"percent","allocation":"101"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                replace(self.profile,**change)

    def test_margin_and_available_equity_are_explicit(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",capital="20",maintenance_rate="0.05",mark_mode="last_proxy",funding_mode="assumed_zero")
        result = run_backtest(flat([100,102,104]),profile,self.signals)
        entry = next(p for p in result["equity"] if p["time_ns"]==60_000_000_000-1)
        self.assertEqual(Decimal(entry["initial_margin"]),10)
        self.assertEqual(Decimal(entry["maintenance_margin"]),5)
        self.assertEqual(Decimal(entry["available"]),10)
        self.assertEqual(Decimal(entry["equity"]),20)

    def test_end_of_run_is_full_close_and_costs_count(self):
        result = run_backtest(flat([100,110]),replace(self.profile,fee_rate="0.001"),signal_map({60:{"entry_long":True}}))
        self.assertEqual(result["fills"][1]["reason"],"end_of_run")
        self.assertEqual(Decimal(result["metrics"]["net_pnl"]),Decimal("9.79"))
        self.assertEqual(result["equity"][-1]["initial_margin"],"0")

    def test_stop_percentage_is_price_move_not_leveraged_return(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",stop_loss="0.05",mark_mode="last_proxy",funding_mode="assumed_zero")
        result = run_backtest(flat([100,99,96,94]),profile,signal_map({60:{"entry_long":True}}))
        self.assertEqual(result["fills"][1]["reason"],"stop_loss")
        self.assertEqual(Decimal(result["fills"][1]["price"]),94)

    def test_funding_can_trigger_liquidation(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",capital="10",maintenance_rate="0.05")
        data = flat([100,100])
        result = run_backtest(data,profile,signal_map({60:{"entry_long":True}}),marks={c.time:c for c in data},funding={60:"0.06"})
        self.assertEqual([e["type"] for e in result["events"]],["funding","liquidation"])
        self.assertEqual(Decimal(result["metrics"]["final_equity"]),4)

    def test_tier_limits_fail_instead_of_changing_size_or_claiming_coverage(self):
        profile = replace(self.profile,max_notional="90")
        self.assertEqual(profile.size(1000,100),0)
        from terminal.risk_gateway import ProfileViolation
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",max_notional="105",mark_mode="last_proxy",funding_mode="assumed_zero")
        with self.assertRaisesRegex(ProfileViolation,"constant risk tier"):
            run_backtest(flat([100,110]),profile,signal_map({60:{"entry_long":True}}))

    def test_drawdown_is_measured_from_marked_equity_peak(self):
        result = run_backtest(flat([100,110,90,100]),self.profile,signal_map({60:{"entry_long":True}}))
        # One unit: equities 1000,1010,990,1000. Drawdown=20/1010.
        self.assertEqual(Decimal(result["metrics"]["max_drawdown"]),Decimal(20)/Decimal(1010))
        self.assertEqual(result["metrics"]["win_rate"],0)

    def test_multi_trade_net_reconciles_with_final_engine_balance(self):
        profile = replace(self.profile,market="linear",leverage="10",allocation="10",fee_rate="0.001")
        data = flat([100,100,110,100,90])
        result = run_backtest(data,profile,signal_map({60:{"entry_long":True},180:{"exit_long":True},240:{"entry_short":True}}),
                              marks={c.time:c for c in data},funding={60:"0.01",240:"0.01"})
        # Long +10 -0.21 -1 = 8.79; short +10 -0.19 +0.90 = 10.71.
        self.assertEqual([Decimal(t["net_pnl"]) for t in result["trades"]],[Decimal("8.79"),Decimal("10.71")])
        self.assertEqual(Decimal(result["metrics"]["net_pnl"]),Decimal("19.50"))

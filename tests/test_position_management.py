"""Independent Decimal examples, then reconciliation against actual engine fills."""
from dataclasses import replace
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING
import unittest

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.accounting.margin_models import StandardMarginModel
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig, StrategyConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy

from terminal.profile import Profile
from terminal.position_management import PositionConfig, PositionLedger, PositionManager, addition_rejection, rounded_reduction
from terminal.risk_gateway import RiskGateway
from terminal.simulation import make_instrument, VENUE


class FillProbe(Strategy):
    def __init__(self, asset, profile, actions):
        super().__init__(StrategyConfig(order_id_tag='001'))
        self.asset, self.actions = asset, actions
        self.ledger = PositionLedger(profile)
        self.points = []
        self.index = 0

    def on_start(self): self.subscribe_quote_ticks(self.asset.id)

    def on_quote_tick(self, tick):
        side, quantity = self.actions[self.index]
        self.index += 1
        self.submit_order(self.order_factory.market(self.asset.id, OrderSide.BUY if side == 'buy' else OrderSide.SELL,
                                                   Quantity.from_str(quantity)))
        positions = self.cache.positions_open(instrument_id=self.asset.id)
        cash = self.cache.account_for_venue(VENUE).balance_total(USDT).as_decimal()
        point = {'cash':cash, 'quantity':positions[0].quantity.as_decimal() if positions else D(0),
                 'entry':D(str(positions[0].avg_px_open)) if positions else None}
        self.points.append(point)

    def on_order_filled(self, event):
        self.ledger.fill('buy' if event.order_side == OrderSide.BUY else 'sell', str(event.last_qty),
                         str(event.last_px), str(event.commission.as_decimal()), event.ts_event, 'fixture')


def engine_fixture(profile, prices, actions):
    asset = make_instrument(profile)
    engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(bypass_logging=True)))
    engine.add_venue(VENUE, OmsType.NETTING, AccountType.MARGIN if profile.market == 'linear' else AccountType.CASH,
                     [Money(profile.capital, USDT)], base_currency=USDT if profile.market == 'linear' else None,
                     default_leverage=D(profile.leverage), margin_model=StandardMarginModel(), use_message_queue=False)
    engine.add_instrument(asset)
    probe = FillProbe(asset, profile, actions)
    config = PositionConfig(max_entries=8)
    guard = RiskGateway(engine, asset, perpetual=profile.market == 'linear', leverage=D(profile.leverage),
                        position_policy=(profile, config, probe.ledger))
    engine.add_strategy(probe)
    quotes = [QuoteTick(asset.id, Price.from_str(p), Price.from_str(p), Quantity.from_str('100.000'),
                        Quantity.from_str('100.000'), (i+1)*10**9, (i+1)*10**9) for i,p in enumerate(prices)]
    engine.add_data(quotes)
    try:
        engine.run()
        guard.assert_supported()
        return probe.points, probe.ledger.completed, guard.denials
    finally:
        engine.dispose()


class PositionFoundationTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(market='linear', leverage='10', primary_minutes=1,
                               mark_mode='last_proxy', funding_mode='assumed_zero')

    def test_weighted_long_partial_cost_attribution_and_final_reconciliation(self):
        ledger = PositionLedger(self.profile)
        ledger.fill('buy', 2, 100, '.2', 1, 'entry')
        ledger.fill('buy', 3, 80, '.24', 2, 'scale')
        # 200 + 240 = 440 cost, five units => entry 88, initial margin 44.
        self.assertEqual(ledger.entry, D(88))
        self.assertEqual(D(ledger.snapshot(80)['initial_margin']), D(44))
        self.assertEqual(D(ledger.snapshot(80)['maintenance_margin']), D(2))
        ledger.funding_cashflow('-5', 3)
        reduction = ledger.fill('sell', 1, 110, '.11', 4, 'partial_take')
        self.assertEqual(D(reduction['gross_pnl']), D(22))
        self.assertEqual(D(reduction['allocated_entry_fee']), D('.088'))
        self.assertEqual(D(reduction['allocated_funding']), D(-1))
        state = ledger.snapshot(110)
        self.assertEqual(D(state['initial_margin']), D('35.2'))
        self.assertEqual(D(state['maintenance_margin']), D('2.2'))
        self.assertEqual(D(state['unrealized_pnl']), D(88))
        self.assertEqual(D(state['net_pnl']), D('104.45'))
        ledger.fill('sell', 4, 120, '.48', 5, 'end_of_run')
        self.assertEqual(len(ledger.completed), 1)
        summary = ledger.completed[0]
        self.assertEqual(D(summary['gross_pnl']), D(150))
        self.assertEqual(D(summary['fees']), D('1.03'))
        self.assertEqual(D(summary['net_pnl']), D('143.97'))
        self.assertEqual({e['position_id'] for e in summary['events']}, {1})

    def test_short_costs_funding_and_partial_exit(self):
        ledger = PositionLedger(self.profile)
        ledger.fill('sell', 2, 100, '.2', 1, 'entry')
        ledger.fill('sell', 3, 120, '.36', 2, 'scale')
        self.assertEqual(ledger.entry, D(112))
        ledger.funding_cashflow('5', 3)
        ledger.fill('buy', 1, 90, '.09', 4, 'partial_take')
        self.assertEqual(D(ledger.snapshot(90)['unrealized_pnl']), D(88))
        ledger.fill('buy', 4, 80, '.32', 5, 'end_of_run')
        self.assertEqual(D(ledger.completed[0]['net_pnl']), D('154.03'))

    def test_real_engine_long_and_short_cash_match_independent_numbers(self):
        for market, short, expected in [('spot', False, '1148.97'), ('linear', False, '1148.97'), ('linear', True, '1149.03')]:
            with self.subTest(market=market, short=short):
                profile = replace(self.profile, market=market, leverage='10' if market == 'linear' else '1')
                prices = ['100.00','120.00','90.00','80.00'] if short else ['100.00','80.00','110.00','120.00']
                entry, exit_side = ('sell','buy') if short else ('buy','sell')
                points, completed, denials = engine_fixture(profile, prices, [(entry,'2.000'),(entry,'3.000'),(exit_side,'1.000'),(exit_side,'4.000')])
                self.assertEqual(denials, [])
                self.assertEqual(points[1]['entry'], D(112 if short else 88))
                self.assertEqual(points[2]['quantity'], D(4))
                self.assertEqual(points[-1]['quantity'], D(0))
                self.assertEqual(points[-1]['cash'], D(expected))
                self.assertEqual(D(completed[0]['net_pnl']), D(expected)-1000)

    def test_add_after_reduction_uses_remaining_cost_basis_in_engine(self):
        profile = replace(self.profile, fee_rate='0')
        points, completed, denials = engine_fixture(profile, ['100.00','80.00','110.00','70.00','100.00'],
            [('buy','2.000'),('buy','2.000'),('sell','2.000'),('buy','2.000'),('sell','4.000')])
        self.assertEqual(denials, [])
        self.assertEqual(points[3]['entry'], D(80))
        # Two units realize 40; four remaining units then realize 80.
        self.assertEqual(points[-1]['cash'], D(1120))
        self.assertEqual(D(completed[0]['net_pnl']), D(120))

    def test_fee_aware_break_even_includes_remaining_funding_and_slippage(self):
        for short, expected in [(False, '100.52'), (True, '99.50')]:
            ledger = PositionLedger(replace(self.profile, slippage='.001'))
            ledger.fill('sell' if short else 'buy', 2, 100, '.2', 1, 'entry')
            ledger.funding_cashflow('-.4', 2)
            # Costs/unit = .1 commission + .2 funding. Exit commission .1%,
            # slippage .1%, then favorable trigger rounding to the cent.
            self.assertEqual(ledger.break_even_price(), D(expected))
            quote = ledger.break_even_price()
            execution = (quote*(D('1.001') if short else D('.999'))/D('.01')).to_integral_value(rounding=ROUND_CEILING if short else ROUND_FLOOR)*D('.01')
            gross = (100-execution if short else execution-100)*2
            self.assertGreaterEqual(gross-D('.2')-D('.4')-execution*2*D('.001'), 0)

    def test_limits_are_explicit_and_do_not_modify_position(self):
        ledger = PositionLedger(self.profile)
        ledger.fill('buy', 5, 100, '.5', 1, 'entry')
        cases = [(PositionConfig(max_entries=1), 1, 'maximum entry count'),
                 (PositionConfig(max_entries=3, max_position_notional='550'), 1, 'maximum position notional'),
                 (PositionConfig(max_entries=3, max_allocation_percent='5'), 1, 'maximum position allocation'),
                 (PositionConfig(max_entries=3), 1, 'insufficient initial margin')]
        for config, quantity, reason in cases:
            self.assertIn(reason, addition_rejection(self.profile, config, ledger, quantity, 100, 20, 20))
        self.assertEqual(ledger.quantity, D(5))
        self.assertIsNone(addition_rejection(self.profile, PositionConfig(max_entries=3), ledger, 1, 100, 1000, 1000))

    def test_reduction_rounding_and_dust_are_not_silently_resized(self):
        profile = replace(self.profile, quantity_step='.03', min_quantity='.03')
        self.assertEqual(rounded_reduction(profile, '.99', '.25'), D('.24'))
        self.assertEqual(rounded_reduction(profile, '.03', '.25'), D(0))
        self.assertEqual(rounded_reduction(profile, '.03', 1), D('.03'))

    def test_profile_legacy_shape_and_versioned_config_validation(self):
        self.assertNotIn('position_management', Profile().snapshot())
        supplied = {'max_entries':4, 'dca':[{'distance':'.02', 'allocation_percent':'20'}]}
        profile = replace(self.profile, position_management=supplied)
        supplied['dca'][0]['distance'] = '.8'
        self.assertEqual(profile.position_management['dca'][0]['distance'], '0.02')
        self.assertEqual(Profile(**profile.snapshot()).snapshot(), profile.snapshot())
        for config in ({'max_entries':100}, {'version':2}, {'dca':[{'distance':'.02','allocation_percent':'101'}]},
                       {'partial_take':[{'distance':'.03','fraction':'.6'},{'distance':'.06','fraction':'.6'}]}):
            with self.subTest(config=config), self.assertRaises(ValueError): PositionConfig(**config)


class PositionDecisionTests(unittest.TestCase):
    def manager(self, **config):
        return PositionManager(Profile(market='linear', leverage='2', capital='1000', allocation='100', fee_rate='0',
                                       position_management={'max_entries':5, **config}))

    def fill(self, manager, action, price, time):
        self.assertIsNotNone(action)
        manager.fill(action.side, action.quantity, price, 0, time, action.reason)

    def test_repeated_entries_require_new_true_transition_and_stop_at_limit(self):
        manager = self.manager(repeated_entry='scale', max_entries=2)
        self.fill(manager, manager.signals({'entry_long':True},100,100,1000,1000,1),100,1)
        self.assertIsNone(manager.signals({'entry_long':True},100,100,1000,1000,2))
        manager.signals({'entry_long':False},100,100,1000,1000,3)
        self.fill(manager, manager.signals({'entry_long':True},100,100,1000,1000,4),100,4)
        self.assertEqual(manager.ledger.quantity, D(4))
        manager.signals({'entry_long':False},100,100,1000,1000,5)
        self.assertIsNone(manager.signals({'entry_long':True},100,100,1000,1000,6))
        self.assertIn('maximum entry count', manager.diagnostics[-1]['message'])

    def test_dca_uses_initial_anchor_once_and_is_mirrored_for_short(self):
        for short in (False,True):
            manager = self.manager(dca=[{'distance':'.02','allocation_percent':'10'},{'distance':'.04','allocation_percent':'10'}])
            manager.fill('sell' if short else 'buy',2,100,0,1,'entry')
            price = 102 if short else 98
            action = manager.dca_action(price,price,price,1000,1000,2)
            self.fill(manager,action,price,2)
            self.assertEqual(action.reason, 'dca_1')
            self.assertIsNone(manager.dca_action(price,price,price,1000,1000,3))
            price = 104 if short else 96
            action = manager.dca_action(price,price,price,1000,1000,4)
            self.assertEqual(action.reason, 'dca_2')
            self.assertEqual(manager.ledger.anchor, D(100))

    def test_partial_take_schedule_is_one_lifecycle_25_25_remaining(self):
        manager = self.manager(partial_take=[{'distance':'.03','fraction':'.25'},
                                            {'distance':'.06','fraction':'.25'}, {'distance':'.1','fraction':'.5'}])
        manager.fill('buy',4,100,0,1,'entry')
        for time, price, quantity in [(2,103,1),(3,106,1),(4,110,2)]:
            action = manager.protective_action(price,price,1000,time)
            self.assertEqual(action.quantity, D(quantity))
            self.fill(manager,action,price,time)
            self.assertIsNone(manager.dca_action(90,90,90,1000,1000,time))
        self.assertEqual(len(manager.ledger.completed), 1)
        self.assertEqual(D(manager.ledger.completed[0]['net_pnl']), D(29))

    def test_trailing_is_causal_monotonic_and_mirrored(self):
        for short, favorable, level, retreat in [(False,110,'108.35',108),(True,90,'91.35',92)]:
            manager = self.manager(trailing_activation='.03', trailing_distance='.015')
            manager.fill('sell' if short else 'buy',1,100,0,1,'entry')
            self.assertIsNone(manager.stop)
            self.assertIsNone(manager.protective_action(favorable,favorable,1000,2))
            self.assertEqual(manager.stop, D(level))
            prior = manager.stop
            action = manager.protective_action(retreat,retreat,1000,3)
            self.assertEqual(action.reason, 'trailing_stop')
            self.assertEqual(manager.stop, prior)

    def test_atr_stop_uses_entry_atr_and_trailing_never_loosens(self):
        manager = self.manager(atr_stop_multiplier='2', atr_trailing_multiplier='2')
        self.assertIsNone(manager.signals({'entry_long':True},100,100,1000,1000,1))
        self.assertIn('ATR is not ready',manager.diagnostics[-1]['message'])
        manager.atr = D(2)
        manager.fill('buy',1,100,0,2,'entry')
        self.assertEqual(manager.stop, D(96))
        manager.protective_action(110,110,1000,3)
        self.assertEqual(manager.stop, D(106))
        manager.atr = D(4)
        manager.protective_action(111,111,1000,4)
        self.assertEqual(manager.stop, D(106))
        self.assertEqual(manager.protective_action(105,105,1000,5).reason,'atr_trailing')

    def test_liquidation_precedes_take_and_strategy_exit(self):
        manager = self.manager(partial_take=[{'distance':'.03','fraction':'.25'}])
        manager.fill('buy',4,100,0,1,'entry')
        # Last is profitable but mark/equity breach maintenance (4*80*.005=1.6).
        action = manager.protective_action(110,80,1,2)
        self.assertEqual(action.reason, 'liquidation')
        self.fill(manager,action,110,2)
        self.assertIsNone(manager.signals({'entry_long':True,'exit_long':True},110,110,1000,1000,2))

    def test_manual_partial_add_and_close_share_policy_and_limits(self):
        manager = self.manager()
        self.fill(manager,manager.manual('buy',100,100,1000,1000,1),100,1)
        self.fill(manager,manager.manual('add',100,100,1000,1000,2),100,2)
        self.assertEqual(manager.ledger.quantity, D(4))
        self.fill(manager,manager.manual('reduce_25',110,110,1000,1000,3),110,3)
        self.assertEqual(manager.ledger.quantity, D(3))
        self.fill(manager,manager.manual('reduce_50',110,110,1000,1000,4),110,4)
        self.assertEqual(manager.ledger.quantity, D('1.5'))
        self.fill(manager,manager.manual('close',110,110,1000,1000,5),110,5)
        self.assertEqual(D(manager.ledger.completed[0]['net_pnl']), D(40))

    def test_future_quote_cannot_rewrite_earlier_stop_events(self):
        manager = self.manager(trailing_distance='.02')
        manager.fill('buy',1,100,0,1,'entry')
        manager.protective_action(110,110,1000,2)
        before = [dict(event) for event in manager.ledger.events]
        manager.protective_action(150,150,1000,3)
        self.assertEqual(manager.ledger.events[:len(before)], before)


if __name__ == '__main__': unittest.main()

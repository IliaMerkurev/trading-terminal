"""Shared causal minute-to-IR contract for historical, live and recorded replay.

Forming primary bars advance on confirmed minute closes, exactly as in product
0.2. Live price ticks do not silently introduce a different indicator cadence.
"""
from terminal.graph import GraphEvaluator, OUTPUTS
from terminal.series import PartialBars


class SignalStream:
    def __init__(self, evaluator, primary_minutes, evaluation):
        if evaluation not in ('closed', 'intrabar'):
            raise ValueError('Unsupported signal evaluation mode')
        self.evaluator, self.evaluation = evaluator, evaluation
        # Native indicator state is incremental. Legacy custom probe callables
        # retain their full-bar input contract; production IR needs only the tail.
        self.frames = PartialBars(primary_minutes, 2 if isinstance(evaluator, GraphEvaluator) else None)
        self.states = {key: False for key in OUTPUTS}

    def update(self, candle):
        _, complete = self.frames.update(candle)
        if not self.frames.count or (self.evaluation == 'closed' and not complete):
            return None
        result = self.evaluator(self.frames.snapshot(), candle.time + 60, complete)
        states = {key: result.get('signals', {}).get(key) is True for key in OUTPUTS}
        transitions = [key for key in OUTPUTS if states[key] and not self.states[key]]
        self.states = states
        return {**result, 'signals': states, 'transitions': transitions, 'time': candle.time + 60}


def replay_signals(graph, primary_minutes, evaluation, candles):
    """Yield bounded results; callers persist/page the journal rather than grow RAM."""
    stream = SignalStream(GraphEvaluator(graph), primary_minutes, evaluation)
    for candle in candles:
        result = stream.update(candle)
        if result is not None:
            yield result

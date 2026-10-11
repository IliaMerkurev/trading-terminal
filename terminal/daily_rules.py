"""Project-authored bounded rule specifications, not upstream article snapshots.

SHA256 uses each RULES value's exact UTF-8 bytes (including final newline).
Referenced prose retains its authors' rights; no article or external code is copied.
"""
RULES = {
    'C12': (
        'C12 terminal rule summary v1\n'
        'Daily spot long/flat. Entry: close[t] > SMA(close, trend_period)[t] AND '
        'close[t] == min(close[t-window+1:t+1]). Exit: '
        'close[t] == max(close[t-window+1:t+1]). Extrema include today; ties qualify.\n'
        'Source settings: trend_period=200, window=7. Local editable bounds are not source recommendations.\n'
        'Local execution: terminal profile v2 observed close, configured sizing/costs/protection; '
        'no pyramiding or shorts. This is not an ETF portfolio replication or next-open experiment.\n'
    ),
    'C13': (
        'C13 terminal rule summary v1\n'
        'Daily spot long/flat. Entry: close[t] > SMA(close, trend_period)[t] AND '
        'RSI[t-2] < first_threshold AND RSI[t-1] < RSI[t-2] AND RSI[t] < RSI[t-1]. '
        'Exit: RSI[t] > exit_threshold. All comparisons are strict. No extra RSI<5 rule.\n'
        'Source settings: trend_period=200, rsi_period=2, first_threshold=65, exit_threshold=75. '
        'Local editable bounds are not source recommendations.\n'
        'Local adaptation: entry-day trend filter, existing Nautilus zero-difference-seeded Wilder RSI '
        'on 0-100 scale, completed-primary-bar lags, terminal profile v2 observed close and configured '
        'sizing/costs/protection. No pyramiding or shorts; not SPX/derivatives or source-platform parity.\n'
    ),
}

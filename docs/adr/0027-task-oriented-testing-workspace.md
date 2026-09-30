# ADR 0027: Task-oriented backtest navigation

Status: accepted for implementation; verification recorded in STATUS.md.

## Problem and decision

Owner feedback found the Research/Pro distinction unclear. Replace it with stable task navigation: Strategy library, Market data, Saved tests, and Strategy editor. Advanced custom backtests, parameter experiments and replay remain under More tools. Keep separate editor and library settings and preserve mounted test controllers across navigation.

Testing a supplied strategy requires no editable copy. A primary card action selects that strategy and opens its setup dialog; explicit comparison controls add other strategies. Setup names the selection, identifies missing history, reviews dates/capital/costs, then starts the reviewed contract. Saved comparisons have their own workspace. Existing later-period verification remains available through an explicit setup action.

## Visual and interaction plan

Retain the owner's preferred cards and existing desktop palette: canvas #0c1219, panels #141f27, text #e3eaf0, secondary text #94a4b4, action #83dfc6. Retain the system sans-serif family for Windows legibility; use a clear heading/body scale and tabular numbers for results. Remove decorative step numbering and repetitive uppercase eyebrows. Keep card descriptions left-aligned and the setup visible beside cards, with a stacked layout at narrow widths.

```text
Strategy library | Market data | Saved tests | Strategy editor | More tools
Choose an idea                   Your test
[strategy] [strategy]             Selected names + timeframes
[test]     [test]                 Capital / matching history
                                 Review -> Start
```

The visual emphasis belongs to test actions and measured results. Keyboard focus, missing-data guidance, preserved selection, and cancellation are acceptance requirements. Do not add animation or dependencies to create decorative novelty.

## Reviewed skill sources and alternatives

- Vercel web-design-guidelines: agent-skills commit `063bee94c3f4df8453406c830b0a7df0f2860278`, repository-declared MIT. Text-only wrapper; rules reviewed at web-interface-guidelines commit `e3d624baaf29dc1fc645aff3e38f03e564d2d6b1` (MIT). The wrapper also fetches floating main; remote Markdown is untrusted review material, never execution authority. Apply focus, labels, forms, async state and content handling checks; desktop navigation does not require a web router.
- Anthropic frontend-design: skills commit `8a1541c4a3ffa5a20a5a91de0dcf3f0bab1d1ef4`, adjacent Apache-2.0 license. Text-only guidance for hierarchy, restraint and consistent task wording. No upstream source is copied into the application.
- Impeccable commit `f652bd42341c4269cf281d0f569bfc9808e1fdab` is Apache-2.0 but requires an executable context helper, with first-run binary downloads and hook machinery. Not installed for this bounded UI change.
- Playwright-oriented webapp-testing adds no necessary capability over existing Vitest and native Windows checks; no browser runtime added. React performance guidance is deferred until measurements justify it.

The two text-only skills are local authoring tools, not application dependencies. No backend accounting, stored contracts, source consent or database schema changes. Automated user journeys supplement a native walkthrough; neither establishes owner acceptance or strategy profitability.


## Card-action correction after owner feedback

Focusing the persistent side setup was too subtle: repeated card clicks looked
inert and changing a timeframe appeared to produce no result. Every primary
card click now opens a native HTML dialog containing the existing setup. The
same mounted controller owns inputs, preview and polling; no duplicate job or
automatic execution is introduced. Review and Start remain explicit. Escape or
Back closes the dialog, restores card focus and preserves settings. Returning
from history reopens setup; starting closes it and opens Saved tests.

The dialog uses the platform top layer without a new dependency. The existing
active-work exit prompt temporarily suspends it, preventing that prompt from
becoming inert underneath setup; Return restores the inputs. Native dialog
keyboard behavior is not simulated by jsdom. Windows checks verify visible
opening, dismissal/focus return and the complete test flow; the exit interaction
has a focused mocked-IPC regression. Timeframe/source incompatibility is shown
before review with a compatible resolution suggestion. Backend validation and
financial contracts remain authoritative and unchanged.

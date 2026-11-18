# Trade analyst call log

Every call the trade analyst's paper portfolios make, published nightly, so its scorecard can't
be quietly edited after the fact.

A call says a stock will beat (or trail) a benchmark, SPY or its sector fund, over a number of
trading days counted from the first close after the call's day, with the chance the agent gave
it being right when it gave one. Calls come from:

- the daily call sheet: each night code picks five stocks, up to three with fresh signals (House
  members' disclosed trades, insider buys, top funds' buys) and the rest drawn at random, and
  the agent must call every one;
- the live paper portfolios' trades: each stock bought is a call that it beats SPY, each stock
  sold as a bearish view a call that it trails.

## Files

- `calls.jsonl`: every call as stored, in order. Each row's fingerprint is the SHA-256 of the row
  before it and its own text, so changing or removing a call breaks every fingerprint after it.
  A call's reason is kept private (it may quote licensed prices); its SHA-256 is in the text.
- `heads.txt`: the newest fingerprint and call count each night they changed. Lines are only
  ever added.
- `sheet_runs.jsonl`: every call-sheet attempt and its status, including refused and failed
  nights.
- `pools.jsonl`: the stocks each sheet's random picks were drawn from.
- `verify.py`: the checker.

## Checking it

    git clone https://github.com/pdfinnigan/trade-analyst-calls
    cd trade-analyst-calls && python3 verify.py

(Python 3.11+ and git, nothing to install.) It checks the chain, that every fingerprint in
heads.txt is still in it at its count, that no earlier version of heads.txt in the git history
was ever rewritten, and redraws each sheet's random picks. Keep your clone, then pull and run
it again later: it remembers the heads.txt it last passed (in .git/verified-heads), so if the
history were ever rewritten it fails, even after you reset to the new history. Commit times are
ours to set, so the dates in heads.txt are our word; your own clone's pull times are not.

## What the redraw shows, and what it doesn't

It shows each night's random picks follow from that night's published stock list and a seed
anyone can compute from the date. It doesn't show the list was fair: the list is the stocks we
had prices for that night, which you can't see, so a list shaped to land on certain stocks would
still redraw cleanly. Watch for odd jumps in its size from night to night.

Results are scored from market prices on the project's site; the prices themselves are licensed
and not published here.

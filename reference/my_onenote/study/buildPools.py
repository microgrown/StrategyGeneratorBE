"""Assemble pools.json for the own-rules platinum-validation study.

    python buildPools.py            write pools.json from grids/*.json + the Brooks pools

Inputs:
  - grids/A..D.json: per-rule setup clusters and grids (pane-1 families) and the
    own pane-2 conditions (familyGrid for their own family, pinned for draws);
  - ../../brooks/study/pools.json: the stop, exit and switch pools, reused
    unchanged so both arms meet the same exits (Brian, 2026-11-05);
  - the additions below: the two Entry & Exit Confessions exits Brian added
    back for this arm and AdxRisingExit, plus the classic filters and the
    classic pane-1 entries.

Nothing here draws; drawOwnStudy.py consumes pools.json.
"""

import copy
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BROOKS_POOLS = os.path.normpath(os.path.join(HERE, "..", "..", "brooks", "study", "pools.json"))


def pin(v):
    return {"start": str(v), "stop": "", "step": ""}


def grid(a, b, s):
    return {"start": str(a), "stop": str(b), "step": str(s)}


def placement(name, params, flipped=False, negated=False):
    return {"name": name, "flipped": flipped, "negated": negated, "params": params}


EXTRA_EXITS = [
    {"id": "CalendarBoundaryExit", "category": "time", "intradayOnly": False, "iterations": 1,
     "optimizedInputs": 0, "brooks": False,
     "placement": placement("CalendarBoundaryExit", {"exitMonth": pin(7), "priorMonth": pin(6)}),
     "note": "EEC X4 (Davey), added back for this arm (Brian, 2026-11-06); fires twice a year"},
    {"id": "ClosePercentileExit", "category": "pattern-structural", "intradayOnly": False, "iterations": 4,
     "optimizedInputs": 1, "brooks": False,
     "placement": placement("ClosePercentileExit", {"exitPercentile": pin(0.5), "lookback": grid(5, 20, 5)}),
     "note": "EEC X5 (Davey), added back for this arm (Brian, 2026-11-06); median of N closes"},
    {"id": "AdxRisingExit", "category": "pattern-structural", "intradayOnly": False, "iterations": 4,
     "optimizedInputs": 1, "brooks": False,
     "placement": placement("AdxRisingExit", {"adxLength": pin(14), "compareBars": grid(5, 20, 5)}),
     "note": "Brian's notes (ON-55-b); general, reads no position state"},
]

# Classic pane-2 filters for the pane-1 families (all pinned). "trend" filters
# are oriented like the own trend conditions; "regime" ones are same-sided.
CLASSIC_FILTERS = [
    {"id": "DaveyMomentum", "kind": "trend", "sides": "mirrored",
     "placement": placement("Momentum", {"lookback": pin(50)}),
     "note": "close above the close 50 bars ago; Davey momentum, pane 2 only (Brian)"},
    {"id": "CloseAboveSma", "kind": "trend", "sides": "mirrored",
     "placement": placement("CloseAboveAverage", {"lookback": pin(100)}),
     "note": "close above its 100-bar SMA"},
    {"id": "AdxTrending", "kind": "regime", "sides": "same",
     "placement": placement("AdxBelowThreshold", {"lookback": pin(14), "threshold": pin(25)}, negated=True),
     "note": "ADX(14) at or above 25 (negated AdxBelowThreshold)"},
    {"id": "AdxQuiet", "kind": "regime", "sides": "same",
     "placement": placement("AdxBelowThreshold", {"lookback": pin(14), "threshold": pin(20)}),
     "note": "ADX(14) below 20"},
    {"id": "AtrExpanding", "kind": "regime", "sides": "same",
     "placement": placement("AtrAboveAverage", {"atrLookback": pin(15), "lookback": pin(20)}),
     "note": "ATR(15) above its 20-bar average"},
]

# Classic pane-1 entries for the pane-2 families: one trend-following and one
# mean-reversion entry per family, each with its reverse (Brian, 2026-11-06).
CLASSIC_ENTRIES = {
    "trend": [
        {"id": "Donchian20", "placement": placement("HighestHighBreakout", {"lookback": pin(20)}),
         "note": "high at or above the 20-bar high"},
        {"id": "MaCross10x30", "placement": placement("MovingAverageCross", {"fastLength": pin(10), "slowLength": pin(30)}),
         "note": "10-bar SMA crosses the 30-bar SMA"},
    ],
    "meanReversion": [
        {"id": "BollingerCross", "placement": placement("BollingerBandCross", {"length": pin(20), "numDevs": pin(2)}),
         "note": "close crosses back over the lower 20/2 Bollinger band (EEC E25's term)"},
        {"id": "KeltnerCross", "placement": placement("KeltnerChannelCross", {"length": pin(20), "numAtrs": pin(2)}),
         "note": "close crosses back over the lower 20/2 Keltner band (EEC E26's term)"},
        {"id": "RsiExtreme", "placement": placement("RsiBelowThreshold", {"lookback": pin(14), "threshold": pin(30)}),
         "note": "RSI(14) below 30 / above 70"},
    ],
}


def loadGrids():
    setups, conditions = [], []
    for path in sorted(glob.glob(os.path.join(HERE, "grids", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        setups.extend(d.get("setups", []))
        conditions.extend(d.get("conditions", []))
    return setups, conditions


def conditionPlacement(c, params):
    name = c["rule"]
    base = c.get("basePlacement", {})
    return placement(name, params, base.get("flipped", False), base.get("negated", False))


def main():
    with open(BROOKS_POOLS, encoding="utf-8") as fh:
        brooks = json.load(fh)
    setups, conditions = loadGrids()
    if len(setups) != 50 or len(conditions) != 14:
        print(f"buildPools: expected 50 setups and 14 conditions, got {len(setups)} and {len(conditions)}",
              file=sys.stderr)
        return 2

    pane2Own = []
    condFamilies = []
    for c in conditions:
        pane2Own.append({"id": c["id"], "kind": c["kind"], "sides": c["sides"],
                         "maxBarsBack": int(c.get("maxBarsBack", 250)),
                         "placement": conditionPlacement(c, c["pinned"]),
                         "note": c.get("rationale", "")})
        condFamilies.append({"condition": c["id"], "kind": c["kind"], "sides": c["sides"],
                             "maxBarsBack": int(c.get("maxBarsBack", 250)),
                             "placement": conditionPlacement(c, c["familyGrid"]),
                             "iterations": c["iterations"], "rationale": c.get("rationale", "")})

    setupFamilies = []
    for s in setups:
        setupFamilies.append({"rule": s["rule"], "setupType": s["setupType"],
                              "setupFlipped": bool(s.get("setupFlipped", False)),
                              "setup": s["cluster"], "iterations": s["iterations"],
                              "optimizedInputs": s["optimizedInputs"],
                              "maxBarsBack": int(s.get("maxBarsBack", 250)),
                              "pane2Conflicts": s.get("pane2Conflicts", []),
                              "estM1440": s.get("estM1440", ""), "rationale": s.get("rationale", "")})

    exitPool = copy.deepcopy(brooks["exitPool"]) + EXTRA_EXITS
    pools = {
        "study": "Own-rules platinum validation: families and pools",
        "version": 1,
        "seed": 20261106,
        "maxBarsBack": "250",
        "dates": brooks["dates"],
        "timeframes": brooks["timeframes"]["any"],
        "budget": {"maxOptimizedInputs": 3, "maxIterations": 100,
                   "rule": "setup or tested condition <= 2 optimized inputs and <= 25 iterations; "
                           "everything else in panes 1-2 pinned; each pane-4 exit <= 1 optimized input "
                           "and <= 4 values; worst = 25 x 4"},
        "setupFamilies": setupFamilies,
        "conditionFamilies": condFamilies,
        "pane2Own": pane2Own,
        "classicFilters": CLASSIC_FILTERS,
        "classicEntries": CLASSIC_ENTRIES,
        "stopPool": copy.deepcopy(brooks["stopPool"]),
        "exitPool": exitPool,
        "switchPool": copy.deepcopy(brooks["switchPool"]),
        "drawConstraints": {
            "noDuplicateWithinFamily": True,
            "pane2NotInSetup": "a pane-2 condition may not use a rule already placed in the family's pane 1",
            "pane2Conflicts": "a setup's pane2Conflicts are never drawn into its pane 2",
            "orientation": "trend conditions as authored for with-trend/breakout setups, flipped for "
                           "reversal/range; reversal-context conditions the other way round",
            "stopPane": "one stop-money/volatility + one stop-structural",
            "exitPane": "4 distinct exits from >= 3 distinct categories",
            "intradayCap": "at most 1 intraday-only member across panes 3+4 and at most 1 "
                           "intraday-effective switch per family",
            "switchKinds": "at most one equity-profit and at most one equity-loss switch per family",
            "switchBySetupType": brooks["drawConstraints"]["switchBySetupType"],
            "classicEntries": "pane-2 families: one trend-following and one mean-reversion classic entry",
            "balance": "least-used-first per pool with seeded random tie-breaks; the best of 200 seeded "
                       "attempts by total count spread is kept",
        },
    }
    out = os.path.join(HERE, "pools.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(pools, fh, indent=1)
        fh.write("\n")
    print(f"wrote {out}: {len(setupFamilies)} setup families, {len(condFamilies)} condition families, "
          f"{len(exitPool)} exits, {len(pools['stopPool'])} stops, {len(pools['switchPool'])} switches")
    return 0


if __name__ == "__main__":
    sys.exit(main())

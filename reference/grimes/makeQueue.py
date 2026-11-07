"""Build the Grimes authoring queue: A rules from merged/*.json, split by register blockage,
then sliced by family into author/slices/NN_<family>.json plus author/A_KEYS.md.

    python reference/grimes/makeQueue.py

Slice assignment is by bucket with a few explicit overrides so that suspected near-neighbour
clusters land in ONE slice (the same agent decides whether they are one rule).
"""
import glob
import json
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import lintElFeatures  # noqa: E402
import featureTriage  # noqa: E402  (reference/grimes copy; normalize())

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--list", default="A", choices=["A", "B"], help="A = priority A; B = priorities B and C")
ARGS = ap.parse_args()
LIST = ARGS.list
PRIORITIES = {"A": {"A"}, "B": {"B", "C"}}[LIST]
AUTHOR = os.path.join(HERE, "author")
SLICES = os.path.join(AUTHOR, "slices" if LIST == "A" else "slicesB")
KEYS_MD = os.path.join(AUTHOR, "A_KEYS.md" if LIST == "A" else "B_KEYS.md")
QUEUE_JSON = os.path.join(AUTHOR, "A_QUEUE.json" if LIST == "A" else "B_QUEUE.json")
os.makedirs(SLICES, exist_ok=True)

# bucket -> slice name
FAMILY = {
    "indicators_bands": "01_oscillator",        # overridden below for the Keltner rules
    "exits_stops": "03_exits",
    "exits_targets": "03_exits",
    "pullbacks_continuation": "04_pullbacks",
    "swing_structure": "04_pullbacks",           # MicroTrendLineBreak; the trail goes to exits
    "ranges_levels_tests": "05_ranges",
    "bar_anatomy": "05_ranges",
    "context_regime": "05_ranges",
    "breakouts": "06_breakouts_climax",
    "climax_termination": "06_breakouts_climax",
}
OVERRIDE = {
    # Keltner family together, apart from the oscillator family
    "FreeBarOutsideKeltnerBand": "02_keltner",
    "FreeBarCountInWindow": "02_keltner",
    "ClosesOutsideKeltnerBandCount": "02_keltner",
    "RidingKeltnerBandBlocksEntries": "02_keltner",
    "SpikeThroughBothKeltnerBands": "02_keltner",
    "ChesterKeltnerTypicalPriceChannel": "02_keltner",
    # an Exit from swing_structure
    "SwingTrailCappedAtMaxRisk": "03_exits",
    # suspected near-neighbour clusters: same slice
    "HigherSwingLowRun": "04_pullbacks",          # with RisingSwingLowCount (both on HigherSwingLow)
    "LowTouchesRecentRangeLow": "06_breakouts_climax",  # with LowTouchesRecentLow
    "TrendRateAcceleration": "06_breakouts_climax",     # with AcceleratingLegsClimax (both vs ParabolicAccelerationExit)
    "MomentumBeyondAtrMultiple": "05_ranges",           # with PriorLegDirection: one agent amends Momentum
    "StalledPositionExit": "03_exits",                  # with NumBarsIfBelowProfitThreshold / FlatTradeScratchExit (all vs NumBarsIfLosing)
}

# B/C list: every key assigned explicitly (27 rules, three slices; templates after their parts)
OVERRIDE_B = {
    # B01: pivot-scan structure rules (swing legs, leg counts, trend lines, three pushes, triangle)
    "UpLegsLongerThanDownLegs": "B01_swing_legs", "SwingTrendHigherHighsAndLows": "B01_swing_legs",
    "SwingLegExceedsAverageLeg": "B01_swing_legs", "MicroTrendLineReclaim": "B01_swing_legs",
    "TrendLineBreakConfirmedExit": "B01_swing_legs", "TrendLegCountAboveMax": "B01_swing_legs",
    "OppositeLegsSimilarLength": "B01_swing_legs", "ExtensionLegExceedsSetupLeg": "B01_swing_legs",
    "ThreePushSymmetry": "B01_swing_legs", "AscendingTriangleIntoLevel": "B01_swing_legs",
    # B02: named templates and their remaining parts (run after B01)
    "Pullback": "B02_templates", "PullbackLowerTimeframeBreakout": "B02_templates",
    "ComplexPullback": "B02_templates", "Anti": "B02_templates", "FailureTest": "B02_templates",
    "BreakoutBaseEntryTemplate": "B02_templates", "FailedBreakoutTemplate": "B02_templates",
    "NoSustainedPriorPenetration": "B02_templates",
    # B03: oscillator divergence, stochastic Anti, exits, switch
    "MomentumDivergenceAtSwingExtreme": "B03_indicators_exits", "NoMomentumDivergenceInWindow": "B03_indicators_exits",
    "OscillatorArtifactWindowBlock": "B03_indicators_exits", "AntiStochasticSlopeDisagreement": "B03_indicators_exits",
    "ParabolicSarTrailingStop": "B03_indicators_exits", "BreakevenStopAfterFavorableCloseRun": "B03_indicators_exits",
    "TimeDecayStopTightening": "B03_indicators_exits", "GapAgainstPositionOpeningRangeBreakExit": "B03_indicators_exits",
    "DailyLossLimit": "B03_indicators_exits",
}
# the `stochastic` register row (VERIFIED) covers FastK/SlowK; StochasticCross is the working port
SYNONYM_TOKENS = {"fastk": "stochastic", "slowk": "stochastic", "fastd": "stochastic", "slowd": "stochastic"}

registry = lintElFeatures.loadRegistry()
OK = {"VERIFIED", "ACCEPTED"}

rules = []
for f in sorted(glob.glob(os.path.join(HERE, "merged", "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for r in d["rules"]:
        if r.get("priority") not in PRIORITIES:
            continue
        r = dict(r)
        r["bucket"] = d["bucket"]
        rules.append(r)

unblocked, blocked = [], []
for r in rules:
    words = r.get("el_words_needed") or r.get("el_words") or []
    toks = []
    for w in words:
        t = featureTriage.normalize(w)
        if isinstance(t, tuple):
            t = t[0]
        t = SYNONYM_TOKENS.get(t, t)
        if t:
            toks.append(t)
    missing = sorted({t for t in toks if registry.get(t, "MISSING") not in OK})
    r["el_words"] = words
    if missing:
        r["blocked_on"] = missing
        blocked.append(r)
    else:
        unblocked.append(r)

on_disk = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(REPO, "rules", "*.json"))}
collisions = [r["key"] for r in unblocked if r["key"] in on_disk]

json.dump({"generated": "2026-09-21", "unblocked": [r["key"] for r in unblocked],
           "blocked": [{"key": r["key"], "on": r["blocked_on"]} for r in blocked],
           "key_collisions_with_rules_dir": collisions},
          open(QUEUE_JSON, "w", encoding="utf-8"), indent=1)

slices = OrderedDict()
for r in unblocked:
    if LIST == "B":
        name = OVERRIDE_B[r["key"]]
    else:
        name = OVERRIDE.get(r["key"], FAMILY[r["bucket"]])
    slices.setdefault(name, []).append(r)

for name in sorted(slices):
    json.dump({"slice": name, "rules": slices[name]},
              open(os.path.join(SLICES, name + ".json"), "w", encoding="utf-8"), indent=1)

lines = [f"# Unblocked {LIST}-list keys (all slices)", "",
         "Check for behavioural duplicates against these as well as against rules/CATALOG.md; "
         "a sibling slice may be authoring the same behaviour under another key.", "",
         "| key | role | priority | bucket | slice | catalog_match | depends_on_keys | description |", "|---|---|---|---|---|---|---|---|"]
for name in sorted(slices):
    for r in slices[name]:
        cm = r["catalog_match"]
        rel = cm["relation"] + (f" of {cm['rule']}" if cm.get("rule") else "")
        lines.append(f"| {r['key']} | {r['role']} | {r['priority']} | {r['bucket']} | {name.split('_')[0]} | {rel} | "
                     f"{', '.join(r.get('depends_on_keys') or [])} | {r['description'].replace('|', '/')} |")
open(KEYS_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")

print(f"{LIST} rules {len(rules)}: unblocked {len(unblocked)}, blocked {len(blocked)} "
      f"{[(b['key'], b['blocked_on']) for b in blocked]}")
print(f"collisions with rules/: {collisions}")
for name in sorted(slices):
    par = sum(1 for r in slices[name] if r["catalog_match"]["relation"] == "parameterization")
    print(f"  {name:<22}{len(slices[name]):>3} rules ({par} parameterizations)")

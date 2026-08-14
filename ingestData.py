"""Ingest wrapper: snapshot the affected symbol, then run the engine tool.

    python ingestData.py ingest --file <export> --symbol AD [engine args...]
    python ingestData.py resample --symbol AD [engine args...]

bt_ingest and bt_resample destructively rewrite a symbol's timeframe
directory (the store keeps no history), which would silently orphan any run
whose raw results were pruned on the promise of exact regeneration. This
wrapper makes the safety step impossible to forget: before handing the
arguments to the engine binary it snapshots the symbol's current store state
via snapshotData.py (skipped only when the symbol has no data yet — a first
ingest has nothing to lose). All arguments after the tool name are passed to
the engine unchanged, so any bt_ingest/bt_resample invocation works here by
inserting `python ingestData.py` in front and dropping the bt_/exe.
"""

import argparse
import os
import subprocess
import sys

import config
import snapshotData
from strategyWriter import GenerationError

TOOLS = {"ingest": "bt_ingest.exe", "resample": "bt_resample.exe"}
BINARY_SUBDIR = os.path.join("build", "release")


def symbolFromArgs(engineArgs):
    for i, arg in enumerate(engineArgs):
        if arg == "--symbol" and i + 1 < len(engineArgs):
            return engineArgs[i + 1]
        if arg.startswith("--symbol="):
            return arg.split("=", 1)[1]
    return None


def run(tool, engineArgs, cfg, runner=subprocess.run, echo=print):
    engineDir = snapshotData._engineDir(cfg)
    binary = os.path.join(engineDir, BINARY_SUBDIR, TOOLS[tool])
    if not os.path.isfile(binary):
        raise GenerationError(f"{TOOLS[tool]} not found at {binary}; build the engine first.")

    symbol = symbolFromArgs(engineArgs)
    if symbol is None:
        raise GenerationError(
            "no --symbol argument found; the wrapper needs it to snapshot the "
            "right store directory before the engine rewrites it.")

    symbolDir = os.path.join(snapshotData.dataDir(cfg), symbol)
    if os.path.isdir(symbolDir):
        echo(f"Snapshotting {symbol} before {tool}...")
        snapshotData.snapshot([symbol], cfg,
                              note=f"pre-{tool} snapshot ({' '.join(engineArgs)})",
                              echo=echo)
    else:
        echo(f"{symbol} has no store data yet; nothing to snapshot.")

    proc = runner([binary] + list(engineArgs), cwd=engineDir)
    return proc.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Snapshot the affected symbol, then run bt_ingest/bt_resample.")
    parser.add_argument("tool", choices=sorted(TOOLS))
    parser.add_argument("engineArgs", nargs=argparse.REMAINDER,
                        help="arguments passed to the engine tool unchanged")
    args = parser.parse_args(argv)
    try:
        return run(args.tool, args.engineArgs, config.load())
    except GenerationError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

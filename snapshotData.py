"""Versioned snapshots of the engine's bar-data store ("data epochs").

    python snapshotData.py --snapshot [SYMBOL ...] [--note TEXT]
    python snapshotData.py --verify [SYMBOL ...]
    python snapshotData.py --restore EPOCH SYMBOL
    python snapshotData.py --list

The engine's ingest destructively rewrites a symbol's timeframe directory, so
without snapshots an old run's exact input data is unrecoverable and a pruned
(deleted) result can never be regenerated bit-identically. Each snapshot zips
the affected data/<SYMBOL> directories into <engine>/data_epochs/<epoch>/ and
records every chunk's content hashes in data_epochs/registry.json. --verify
compares the live store against the latest recorded epoch (drift detector);
--restore brings back the exact bytes a run was computed from, snapshotting
the current state first so a restore can itself be undone.

Hashes mirror the engine's: each chunk's FNV-1a source_hash comes straight out
of the store's index.json / .btck headers, and combinedSourceHash() reproduces
bt::series_source_hash (FNV-1a over the in-range chunks' hashes in first_day
order) so a run manifest's recorded source_hash can be checked against any
epoch without invoking the engine.

Run ingest through ingestData.py and the pre-ingest snapshot cannot be
forgotten. Like all pruning/retention tooling here, this is only ever run by
hand.
"""

import argparse
import json
import os
import shutil
import struct
import sys
import zipfile
from datetime import datetime, timezone

from datetime import date

import config
from strategyWriter import GenerationError

EPOCHS_SUBDIR = "data_epochs"
DATA_SUBDIR = "data"
REGISTRY_JSON = "registry.json"

_CHUNK_HEADER = struct.Struct("<4sI16sIIQqqQQ")  # matches bt::ChunkHeader (72 bytes)
_FNV_OFFSET = 14695981039346656037
_FNV_PRIME = 1099511628211
_U64 = 1 << 64


def _echo(*args):
    print(*args, flush=True)


def _engineDir(cfg):
    engineDir = (cfg.get("engineDir") or "").strip()
    if not engineDir:
        raise GenerationError("No BacktestEngine root is configured.")
    return engineDir


def dataDir(cfg):
    return os.path.join(_engineDir(cfg), DATA_SUBDIR)


def epochsDir(cfg):
    return os.path.join(_engineDir(cfg), EPOCHS_SUBDIR)


# --- hashing (mirrors bt/core/hash.h) ----------------------------------------

def fnv1aBytes(data, seed=_FNV_OFFSET):
    h = seed
    for b in data:
        h = ((h ^ b) * _FNV_PRIME) % _U64
    return h


def combinedSourceHash(chunks, timeframeMinutes, firstDay=None, lastDay=None):
    """bt::series_source_hash over `chunks` (list of chunk dicts as recorded in
    the registry): FNV-1a over each in-range chunk's source_hash (as 8 LE
    bytes), ordered by first_day — byte-for-byte what a v4 run manifest
    records for its date range."""
    selected = [c for c in chunks
                if c["timeframe_minutes"] == timeframeMinutes
                and (lastDay is None or c["first_day"] <= lastDay)
                and (firstDay is None or c["last_day"] >= firstDay)]
    selected.sort(key=lambda c: c["first_day"])
    h = _FNV_OFFSET
    for c in selected:
        h = fnv1aBytes(struct.pack("<Q", c["source_hash"]), h)
    return h


def readChunkSessionHash(path):
    with open(path, "rb") as f:
        header = f.read(_CHUNK_HEADER.size)
    if len(header) < _CHUNK_HEADER.size:
        raise GenerationError(f"{path}: truncated chunk header")
    fields = _CHUNK_HEADER.unpack(header)
    if fields[0] != b"BTCK":
        raise GenerationError(f"{path}: not a chunk file (bad magic)")
    return fields[9]


def _chunkDay(value):
    """The engine's index.json writes first_day/last_day as ISO dates
    ("2007-01-02"); normalize to the day serial everything here computes on.
    Already-numeric values (a normalized registry) pass through."""
    if isinstance(value, str):
        return (date.fromisoformat(value) - _EPOCH_DATE).days
    return value


def _chunkHash(value):
    """index.json writes source_hash as a 16-digit hex string; run manifests
    and this module's registry use the integer."""
    if isinstance(value, str):
        return int(value, 16)
    return value


_EPOCH_DATE = date(1970, 1, 1)


def symbolFingerprint(dataRoot, symbol):
    """Every chunk of one symbol with its hashes: index.json supplies the
    structure and source_hash, the .btck header supplies session_hash. Values
    are normalized (day serials, integer hashes) so they compare directly
    against run-manifest fingerprints."""
    symbolDir = os.path.join(dataRoot, symbol)
    indexPath = os.path.join(symbolDir, "index.json")
    try:
        with open(indexPath, encoding="utf-8-sig") as f:
            index = json.load(f)
    except (OSError, ValueError) as exc:
        raise GenerationError(f"cannot read {indexPath}: {exc}")
    chunks = []
    for entry in index.get("chunks", []):
        chunkPath = os.path.join(symbolDir, *entry["path"].split("/"))
        derived = (entry["source"] == "derived" if "source" in entry
                   else entry.get("derived", False))
        chunks.append({
            "path": entry["path"],
            "timeframe_minutes": entry["timeframe_minutes"],
            "first_day": _chunkDay(entry["first_day"]),
            "last_day": _chunkDay(entry["last_day"]),
            "derived": derived,
            "source_hash": _chunkHash(entry["source_hash"]),
            "session_hash": readChunkSessionHash(chunkPath),
        })
    return chunks


# --- registry ----------------------------------------------------------------

def registryPath(cfg):
    return os.path.join(epochsDir(cfg), REGISTRY_JSON)


def loadRegistry(cfg):
    try:
        with open(registryPath(cfg), encoding="utf-8-sig") as f:
            registry = json.load(f)
    except OSError:
        return {"epochs": []}
    except ValueError as exc:
        raise GenerationError(f"corrupt {registryPath(cfg)}: {exc}")
    # Registries written before value normalization carry the index.json raw
    # forms (ISO dates, hex-string hashes); normalize on load so every consumer
    # compares like with like, and the next save persists the normalized form.
    for epoch in registry.get("epochs", []):
        for entry in epoch.get("symbols", {}).values():
            for chunk in entry.get("chunks", []):
                chunk["first_day"] = _chunkDay(chunk["first_day"])
                chunk["last_day"] = _chunkDay(chunk["last_day"])
                chunk["source_hash"] = _chunkHash(chunk["source_hash"])
    return registry


def saveRegistry(cfg, registry):
    os.makedirs(epochsDir(cfg), exist_ok=True)
    path = registryPath(cfg)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def latestEpochFor(registry, symbol):
    for epoch in reversed(registry["epochs"]):
        if symbol in epoch["symbols"]:
            return epoch
    return None


def nextEpochId(registry, stamp):
    """Timestamp-based id, disambiguated when two epochs land in one second
    (a restore snapshots a backup and then records itself)."""
    base = stamp.strftime("%Y%m%d-%H%M%S")
    taken = {e["id"] for e in registry["epochs"]}
    epochId, n = base, 2
    while epochId in taken:
        epochId = f"{base}-{n}"
        n += 1
    return epochId


# --- snapshot ----------------------------------------------------------------

def storeSymbols(dataRoot):
    if not os.path.isdir(dataRoot):
        return []
    return sorted(e for e in os.listdir(dataRoot)
                  if os.path.isfile(os.path.join(dataRoot, e, "index.json")))


def snapshot(symbols, cfg, note="", echo=_echo):
    """Archive the named symbols (default: the whole store) into a new epoch
    and record their fingerprints. Returns the epoch id."""
    dataRoot = dataDir(cfg)
    symbols = list(symbols) or storeSymbols(dataRoot)
    if not symbols:
        raise GenerationError(f"nothing to snapshot: no symbols under {dataRoot}")

    registry = loadRegistry(cfg)
    epochId = nextEpochId(registry, datetime.now(timezone.utc))
    epochDir = os.path.join(epochsDir(cfg), epochId)
    os.makedirs(epochDir, exist_ok=True)

    entry = {"id": epochId,
             "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
             "note": note,
             "symbols": {}}
    for symbol in symbols:
        symbolDir = os.path.join(dataRoot, symbol)
        if not os.path.isdir(symbolDir):
            raise GenerationError(f"no store data for symbol '{symbol}' at {symbolDir}")
        chunks = symbolFingerprint(dataRoot, symbol)
        archive = os.path.join(epochDir, f"{symbol}.zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for root, _dirs, names in os.walk(symbolDir):
                for name in names:
                    full = os.path.join(root, name)
                    z.write(full, os.path.relpath(full, symbolDir))
        size = os.path.getsize(archive)
        entry["symbols"][symbol] = {"archive": f"{epochId}/{symbol}.zip",
                                    "chunks": chunks}
        echo(f"  {symbol}: {len(chunks)} chunk(s) -> {archive} ({size / 2**20:.1f} MB)")

    registry["epochs"].append(entry)
    saveRegistry(cfg, registry)
    echo(f"Epoch {epochId}: {len(symbols)} symbol(s) recorded in {registryPath(cfg)}")
    return epochId


# --- verify ------------------------------------------------------------------

def verify(symbols, cfg, echo=_echo):
    """Compare the live store against each symbol's latest recorded epoch.
    Returns the number of drifted or unrecorded symbols (0 = all clean)."""
    dataRoot = dataDir(cfg)
    registry = loadRegistry(cfg)
    symbols = list(symbols) or storeSymbols(dataRoot)
    if not symbols:
        raise GenerationError(f"nothing to verify: no symbols under {dataRoot}")
    problems = 0
    for symbol in symbols:
        epoch = latestEpochFor(registry, symbol)
        if epoch is None:
            echo(f"  {symbol}: NEVER SNAPSHOTTED")
            problems += 1
            continue
        recorded = {c["path"]: (c["source_hash"], c["session_hash"])
                    for c in epoch["symbols"][symbol]["chunks"]}
        current = {c["path"]: (c["source_hash"], c["session_hash"])
                   for c in symbolFingerprint(dataRoot, symbol)}
        if recorded == current:
            echo(f"  {symbol}: matches epoch {epoch['id']}")
        else:
            changed = sorted(p for p in recorded.keys() & current.keys()
                             if recorded[p] != current[p])
            gone = sorted(recorded.keys() - current.keys())
            new = sorted(current.keys() - recorded.keys())
            detail = "; ".join(part for part in (
                f"changed: {', '.join(changed)}" if changed else "",
                f"missing: {', '.join(gone)}" if gone else "",
                f"new: {', '.join(new)}" if new else "") if part)
            echo(f"  {symbol}: DRIFTED from epoch {epoch['id']} ({detail})")
            problems += 1
    return problems


# --- restore -----------------------------------------------------------------

def restore(epochId, symbol, cfg, echo=_echo):
    """Bring data/<symbol> back to exactly what `epochId` archived. The current
    state is snapshotted first, so a restore is always reversible."""
    registry = loadRegistry(cfg)
    epoch = next((e for e in registry["epochs"] if e["id"] == epochId), None)
    if epoch is None:
        known = ", ".join(e["id"] for e in registry["epochs"]) or "none"
        raise GenerationError(f"no epoch '{epochId}' in the registry (known: {known})")
    if symbol not in epoch["symbols"]:
        raise GenerationError(f"epoch {epochId} has no archive for '{symbol}'")
    archive = os.path.join(epochsDir(cfg), *epoch["symbols"][symbol]["archive"].split("/"))
    if not os.path.isfile(archive):
        raise GenerationError(f"archive missing on disk: {archive}")

    symbolDir = os.path.join(dataDir(cfg), symbol)
    if os.path.isdir(symbolDir):
        echo(f"Snapshotting current {symbol} before restoring...")
        snapshot([symbol], cfg, note=f"pre-restore backup before restoring {epochId}",
                 echo=echo)
        shutil.rmtree(symbolDir)
    os.makedirs(symbolDir, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        z.extractall(symbolDir)

    # Record the restore as the symbol's newest epoch (pointing at the original
    # archive, no re-zip): the latest registry entry always describes what the
    # store is supposed to hold, so --verify stays meaningful after a restore.
    registry = loadRegistry(cfg)
    stamp = datetime.now(timezone.utc)
    registry["epochs"].append({
        "id": nextEpochId(registry, stamp),
        "created_utc": stamp.strftime("%Y-%m-%d %H:%M:%S"),
        "note": f"restored {symbol} from epoch {epochId}",
        "symbols": {symbol: epoch["symbols"][symbol]},
    })
    saveRegistry(cfg, registry)
    echo(f"Restored {symbol} from epoch {epochId}.")


# --- entry point -------------------------------------------------------------

def listEpochs(cfg, echo=_echo):
    registry = loadRegistry(cfg)
    if not registry["epochs"]:
        echo("No epochs recorded.")
        return
    for epoch in registry["epochs"]:
        note = f" — {epoch['note']}" if epoch.get("note") else ""
        echo(f"  {epoch['id']}  {epoch['created_utc']}  "
             f"{len(epoch['symbols'])} symbol(s){note}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Snapshot, verify, and restore the engine's bar-data store.")
    parser.add_argument("args", nargs="*", help="symbols (or EPOCH SYMBOL for --restore)")
    parser.add_argument("--snapshot", action="store_true",
                        help="archive the named symbols (default: all) as a new epoch")
    parser.add_argument("--note", default="", help="reason recorded with --snapshot")
    parser.add_argument("--verify", action="store_true",
                        help="compare the live store against the latest epoch")
    parser.add_argument("--restore", action="store_true",
                        help="restore one symbol from an epoch: --restore EPOCH SYMBOL")
    parser.add_argument("--list", action="store_true", help="list recorded epochs")
    args = parser.parse_args(argv)

    modes = [args.snapshot, args.verify, args.restore, args.list]
    if sum(modes) != 1:
        parser.error("choose exactly one of --snapshot, --verify, --restore, --list")
    cfg = config.load()
    try:
        if args.snapshot:
            snapshot(args.args, cfg, note=args.note)
        elif args.verify:
            return 1 if verify(args.args, cfg) else 0
        elif args.list:
            listEpochs(cfg)
        else:
            if len(args.args) != 2:
                parser.error("--restore takes exactly: EPOCH SYMBOL")
            restore(args.args[0], args.args[1], cfg)
    except GenerationError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
import os
import struct
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ingestData
import snapshotData as sd
from strategyWriter import GenerationError


def quiet(*_args, **_kwargs):
    pass


def writeChunk(path, sourceHash, sessionHash, symbol=b"AD"):
    """A minimal .btck: valid 72-byte header, no records."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = sd._CHUNK_HEADER.pack(b"BTCK", 3, symbol.ljust(16, b"\0"), 60, 5,
                                   0, 0, 0, sourceHash, sessionHash)
    with open(path, "wb") as f:
        f.write(header)


def isoDay(serial):
    return (date(1970, 1, 1) + timedelta(days=serial)).isoformat()


def writeSymbol(dataRoot, symbol, chunks):
    """chunks: [(relPath, timeframe, firstDay, lastDay, sourceHash, sessionHash)]
    (days as serials, hashes as ints). The index.json is written in the
    ENGINE's real on-disk forms — ISO date strings, 16-digit hex source_hash,
    a "source" key — because reading those correctly is exactly what these
    tests must prove (a fixture of convenient ints once hid a crash on the
    real store)."""
    symbolDir = os.path.join(dataRoot, symbol)
    index = {"symbol": symbol, "chunks": []}
    for rel, tf, first, last, source, session in chunks:
        writeChunk(os.path.join(symbolDir, *rel.split("/")), source, session)
        index["chunks"].append({"path": rel, "timeframe_minutes": tf,
                                "first_day": isoDay(first),
                                "last_day": isoDay(last),
                                "record_count": 0, "source": "imported",
                                "source_hash": f"{source:016x}"})
    os.makedirs(symbolDir, exist_ok=True)
    with open(os.path.join(symbolDir, "index.json"), "w") as f:
        json.dump(index, f)


DEFAULT_CHUNKS = [("M60/2021.btck", 60, 18628, 18992, 0x111, 0xAAA),
                  ("M60/2022.btck", 60, 18993, 19357, 0x222, 0xAAA)]


class HashTest(unittest.TestCase):
    def testFnv1aMatchesKnownVector(self):
        # FNV-1a 64 of empty input is the offset basis; of "a" is a published
        # constant — guards against transcription errors in prime/offset.
        self.assertEqual(sd.fnv1aBytes(b""), 14695981039346656037)
        self.assertEqual(sd.fnv1aBytes(b"a"), 0xaf63dc4c8601ec8c)

    def testCombinedHashOrdersAndFilters(self):
        chunks = [{"timeframe_minutes": 60, "first_day": 200, "last_day": 299,
                   "source_hash": 2},
                  {"timeframe_minutes": 60, "first_day": 100, "last_day": 199,
                   "source_hash": 1},
                  {"timeframe_minutes": 1440, "first_day": 100, "last_day": 299,
                   "source_hash": 3}]
        # Ordered by first_day regardless of listing order, other timeframes
        # excluded — matches bt::series_source_hash.
        h = sd.fnv1aBytes(struct.pack("<Q", 1))
        h = sd.fnv1aBytes(struct.pack("<Q", 2), h)
        self.assertEqual(sd.combinedSourceHash(chunks, 60), h)
        # Range selection keeps only overlapping chunks: appending a future
        # year must not change the in-range hash.
        self.assertEqual(sd.combinedSourceHash(chunks, 60, 100, 150),
                         sd.fnv1aBytes(struct.pack("<Q", 1)))
        more = chunks + [{"timeframe_minutes": 60, "first_day": 300,
                          "last_day": 399, "source_hash": 9}]
        self.assertEqual(sd.combinedSourceHash(more, 60, 100, 299),
                         sd.combinedSourceHash(chunks, 60, 100, 299))


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"engineDir": self.tmp.name}
        self.dataRoot = os.path.join(self.tmp.name, sd.DATA_SUBDIR)
        writeSymbol(self.dataRoot, "AD", DEFAULT_CHUNKS)

    def testSnapshotRecordsFingerprintAndArchive(self):
        epochId = sd.snapshot(["AD"], self.cfg, note="test", echo=quiet)
        registry = sd.loadRegistry(self.cfg)
        self.assertEqual(len(registry["epochs"]), 1)
        entry = registry["epochs"][0]["symbols"]["AD"]
        self.assertEqual([c["source_hash"] for c in entry["chunks"]], [0x111, 0x222])
        self.assertEqual([c["session_hash"] for c in entry["chunks"]], [0xAAA, 0xAAA])
        archive = os.path.join(sd.epochsDir(self.cfg), epochId, "AD.zip")
        self.assertTrue(os.path.isfile(archive))

    def testVerifyCleanAndDrifted(self):
        sd.snapshot(["AD"], self.cfg, echo=quiet)
        self.assertEqual(sd.verify(["AD"], self.cfg, echo=quiet), 0)
        # Simulate a re-ingest that changed 2021's data.
        drifted = [("M60/2021.btck", 60, 18628, 18992, 0x999, 0xAAA),
                   DEFAULT_CHUNKS[1]]
        writeSymbol(self.dataRoot, "AD", drifted)
        self.assertEqual(sd.verify(["AD"], self.cfg, echo=quiet), 1)

    def testVerifyFlagsUnsnapshottedSymbol(self):
        writeSymbol(self.dataRoot, "CL", DEFAULT_CHUNKS)
        sd.snapshot(["AD"], self.cfg, echo=quiet)
        self.assertEqual(sd.verify(["AD", "CL"], self.cfg, echo=quiet), 1)

    def testRestoreRoundTripAndBackup(self):
        epochId = sd.snapshot(["AD"], self.cfg, echo=quiet)
        writeSymbol(self.dataRoot, "AD",
                    [("M60/2021.btck", 60, 18628, 18992, 0x999, 0xAAA)])
        self.assertEqual(sd.verify(["AD"], self.cfg, echo=quiet), 1)
        sd.restore(epochId, "AD", self.cfg, echo=quiet)
        # Bytes are back and match the epoch again.
        self.assertEqual(sd.verify(["AD"], self.cfg, echo=quiet), 0)
        chunks = sd.symbolFingerprint(self.dataRoot, "AD")
        self.assertEqual([c["source_hash"] for c in chunks], [0x111, 0x222])
        # The pre-restore state was snapshotted (reversible), and the restore
        # itself became the newest epoch so --verify compares against it.
        registry = sd.loadRegistry(self.cfg)
        self.assertEqual(len(registry["epochs"]), 3)
        self.assertIn("pre-restore", registry["epochs"][1]["note"])
        self.assertIn("restored", registry["epochs"][2]["note"])

    def testRestoreUnknownEpochErrors(self):
        with self.assertRaises(GenerationError):
            sd.restore("nope", "AD", self.cfg, echo=quiet)

    def testFingerprintNormalizesEngineIndexForms(self):
        # Straight off the real index.json shapes: ISO dates -> serials,
        # hex source_hash -> int, "source" -> derived flag.
        chunks = sd.symbolFingerprint(self.dataRoot, "AD")
        self.assertEqual(chunks[0]["first_day"], 18628)
        self.assertEqual(chunks[0]["last_day"], 18992)
        self.assertEqual(chunks[0]["source_hash"], 0x111)
        self.assertFalse(chunks[0]["derived"])

    def testLoadRegistryNormalizesLegacyRawEntries(self):
        # A registry written before normalization carries the raw index forms;
        # loading it must make them comparable to manifest fingerprints.
        rawChunk = {"path": "M60/2021.btck", "timeframe_minutes": 60,
                    "first_day": "2021-01-01", "last_day": "2021-12-31",
                    "derived": False, "source_hash": "0000000000000111",
                    "session_hash": 0xAAA}
        sd.saveRegistry(self.cfg, {"epochs": [
            {"id": "x", "created_utc": "", "note": "",
             "symbols": {"AD": {"archive": "x/AD.zip", "chunks": [rawChunk]}}}]})
        registry = sd.loadRegistry(self.cfg)
        chunk = registry["epochs"][0]["symbols"]["AD"]["chunks"][0]
        self.assertEqual(chunk["first_day"], 18628)
        self.assertEqual(chunk["source_hash"], 0x111)
        self.assertEqual(
            sd.combinedSourceHash(registry["epochs"][0]["symbols"]["AD"]["chunks"],
                                  60, 18628, 18992),
            sd.fnv1aBytes(struct.pack("<Q", 0x111)))

    def testBadMagicRejected(self):
        with open(os.path.join(self.dataRoot, "AD", "M60", "2021.btck"), "wb") as f:
            f.write(b"JUNK" + b"\0" * 68)
        with self.assertRaises(GenerationError):
            sd.symbolFingerprint(self.dataRoot, "AD")


class IngestWrapperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"engineDir": self.tmp.name}
        self.dataRoot = os.path.join(self.tmp.name, sd.DATA_SUBDIR)
        binDir = os.path.join(self.tmp.name, ingestData.BINARY_SUBDIR)
        os.makedirs(binDir)
        open(os.path.join(binDir, "bt_ingest.exe"), "w").close()
        self.calls = []

    def fakeRunner(self, cmd, cwd=None):
        self.calls.append((cmd, cwd))
        class Proc:
            returncode = 0
        return Proc()

    def testSnapshotsExistingSymbolBeforeRunning(self):
        writeSymbol(self.dataRoot, "AD", DEFAULT_CHUNKS)
        code = ingestData.run("ingest", ["--file", "x.txt", "--symbol", "AD"],
                              self.cfg, runner=self.fakeRunner, echo=quiet)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.calls), 1)  # the engine ran
        registry = sd.loadRegistry(self.cfg)
        self.assertEqual(len(registry["epochs"]), 1)  # after a snapshot
        self.assertIn("AD", registry["epochs"][0]["symbols"])

    def testFirstIngestSkipsSnapshot(self):
        code = ingestData.run("ingest", ["--symbol=NEW", "--file", "x.txt"],
                              self.cfg, runner=self.fakeRunner, echo=quiet)
        self.assertEqual(code, 0)
        self.assertEqual(sd.loadRegistry(self.cfg)["epochs"], [])

    def testMissingSymbolArgErrors(self):
        with self.assertRaises(GenerationError):
            ingestData.run("ingest", ["--file", "x.txt"], self.cfg,
                           runner=self.fakeRunner, echo=quiet)
        self.assertEqual(self.calls, [])  # the engine must not run unprotected


if __name__ == "__main__":
    unittest.main()

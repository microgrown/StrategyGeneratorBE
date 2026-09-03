import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rerunSymbols as rs
from strategyWriter import GenerationError

FILTERS = [{"type": "most_average"}, {"type": "trade_count", "min_trades": 30}]
HEADER = ["symbol", "timeframe_minutes", "selected_schedules", "most_average", "trade_count",
          "tradeable", "rejected_by"]


def cand(sym, tf, tradeable=False, tag="old"):
    return {"symbol": sym, "timeframe_minutes": tf, "tradeable": tradeable,
            "rejected_by": "" if tradeable else "trade_count",
            "surviving_schedules": ["252-126"] if tradeable else [], "outcomes": [],
            "wf_results": f"{sym}_M{tf}/wf_results.json", "metrics": {"tag": tag}}


def trad(sym, tf, sched="252-126", tag="old"):
    return {"symbol": sym, "timeframe_minutes": tf, "schedule": sched, "strategy": "S V1",
            "metrics": {"tag": tag}}


def row(sym, tf, tradeable=False, tag="old"):
    return {"symbol": sym, "timeframe_minutes": str(tf), "selected_schedules": "252-126" if tradeable else "",
            "most_average": "pass", "trade_count": "pass" if tradeable else "fail",
            "tradeable": "true" if tradeable else "false",
            "rejected_by": "" if tradeable else "trade_count"}


def report(cands, trads, fmt=1):
    return {"format_version": fmt, "spec": "s_v1", "created_utc": "x", "filters": FILTERS,
            "candidates": cands, "tradeable": trads}


class TestPureSplice(unittest.TestCase):
    def test_narrowedSpec(self):
        spec = {"name": "s_v3", "symbols": ["AD", "ETH", "GC", "BTC"], "timeframes": [60],
                "selection": {"filters": FILTERS}}
        n = rs.narrowedSpec(spec, {"ETH", "BTC", "MET"})
        self.assertEqual(n["name"], "s_v3__rerun")
        self.assertEqual(n["symbols"], ["ETH", "BTC"])
        self.assertEqual(n["timeframes"], [60])
        self.assertEqual(spec["symbols"], ["AD", "ETH", "GC", "BTC"])  # untouched
        self.assertIsNone(rs.narrowedSpec({"name": "s", "symbols": ["AD"]}, {"ETH"}))

    def test_spliceReportReplacesInPlace(self):
        old = report([cand("AD", 60), cand("ETH", 60, True), cand("ETH", 120), cand("GC", 60, True)],
                     [trad("ETH", 60), trad("GC", 60)])
        new = report([cand("ETH", 60, tag="new"), cand("ETH", 120, True, tag="new")],
                     [trad("ETH", 120, tag="new")])
        out = rs.spliceReport(old, new, {"ETH"})
        self.assertEqual([(c["symbol"], c["timeframe_minutes"], c["metrics"]["tag"]) for c in out["candidates"]],
                         [("AD", 60, "old"), ("ETH", 60, "new"), ("ETH", 120, "new"), ("GC", 60, "old")])
        self.assertEqual([(t["symbol"], t["timeframe_minutes"], t["metrics"]["tag"]) for t in out["tradeable"]],
                         [("ETH", 120, "new"), ("GC", 60, "old")])
        self.assertEqual(out["spec"], "s_v1")
        self.assertEqual(old["candidates"][1]["metrics"]["tag"], "old")  # input untouched

    def test_spliceAppendsWhenOldHadNone(self):
        old = report([cand("AD", 60)], [])
        new = report([cand("ETH", 60, True, tag="new")], [trad("ETH", 60, tag="new")])
        out = rs.spliceReport(old, new, {"ETH"})
        self.assertEqual([c["symbol"] for c in out["candidates"]], ["AD", "ETH"])
        self.assertEqual([t["symbol"] for t in out["tradeable"]], ["ETH"])

    def test_spliceRefusesDifferentFiltersOrFormat(self):
        old = report([cand("ETH", 60)], [])
        new = report([cand("ETH", 60)], [])
        new["filters"] = [{"type": "most_average"}]
        with self.assertRaises(GenerationError):
            rs.spliceReport(old, new, {"ETH"})
        new["filters"] = FILTERS
        new["format_version"] = 3
        with self.assertRaises(GenerationError):
            rs.spliceReport(old, new, {"ETH"})

    def test_downgradeFormat2(self):
        crit = {"AvgDrawdown": 1.5, "MaxDrawdown": 2.0, "ModifiedSharpe": 0.1, "NetProfit": 3.0,
                "NetProfitOverAvgDD": 2.0, "NetProfitOverMaxDD": 1.5}
        seg = lambda: {"annual_net_profit": 1.0, "criteria": dict(crit), "days": 9, "first": "2020-01-01",
                       "first_day": 1, "last": "2020-02-01", "last_day": 9, "net_profit": 3.0,
                       "stats": {"SQN": 1.0}, "trades": 4, "windows": 2}
        m2 = [{"full_curve": seg(), "incubation": seg(), "schedule": "252-126", "wf_range": seg()}]
        c2 = dict(cand("ETH", 60), incubation_end="2026-02-01", incubation_end_day=5,
                  wf_end="2025-05-01", wf_end_day=4, metrics=m2)
        c2t = dict(cand("ETH", 120, True), wf_end="2025-05-01", wf_end_day=4, metrics=m2)
        t2 = dict(trad("ETH", 120), metrics={"full_curve": seg(), "incubation": seg(), "wf_range": seg()})
        r2 = dict(report([c2, c2t], [t2], fmt=2))
        r1 = rs.downgradeReport(r2)
        self.assertEqual(r1["format_version"], 1)
        c1, c1t = r1["candidates"]
        self.assertEqual(set(c1), set(cand("ETH", 60)))
        self.assertEqual(c1["metrics"], [{"full_curve": crit, "schedule": "252-126", "wf_range": crit}])
        self.assertEqual(set(c1t), set(cand("ETH", 120)) - {"metrics"})  # tradeable: no metrics in format 1
        self.assertEqual(r1["tradeable"][0]["metrics"], {"full_curve": crit, "wf_range": crit})
        self.assertEqual(r2["format_version"], 2)  # input untouched
        self.assertIn("incubation", r2["candidates"][0]["metrics"][0])
        # a format-2 narrowed run splices into a format-1 family
        old = report([cand("AD", 60), cand("ETH", 60)], [])
        out = rs.spliceReport(old, r2, {"ETH"})
        self.assertEqual(out["format_version"], 1)
        self.assertEqual(out["candidates"][1]["metrics"][0]["wf_range"], crit)
        self.assertIs(rs.downgradeReport(old), old)

    def test_spliceCsvRows(self):
        oldRows = [row("AD", 60), row("ETH", 60, True), row("GC", 60)]
        newRows = [row("ETH", 60), row("ETH", 120, True)]
        out = rs.spliceCsvRows(HEADER, oldRows, HEADER, newRows, {"ETH"}, ("symbol", "timeframe_minutes"))
        self.assertEqual([(r["symbol"], r["timeframe_minutes"], r["tradeable"]) for r in out],
                         [("AD", "60", "false"), ("ETH", "60", "false"), ("ETH", "120", "true"), ("GC", "60", "false")])
        with self.assertRaises(GenerationError):
            rs.spliceCsvRows(HEADER, oldRows, HEADER[:-1], newRows, {"ETH"}, ("symbol",))

    def test_spliceLedger(self):
        ledger = {"format": "pruneRuns-ledger-1", "units": {
            "AD_M60": {"symbol": "AD"}, "ETH_M60": {"symbol": "ETH"}, "BTC_M5": {"symbol": "BTC"}}}
        out = rs.spliceLedger(ledger, {"ETH", "BTC"})
        self.assertEqual(list(out["units"]), ["AD_M60"])
        self.assertEqual(len(ledger["units"]), 3)


class TestSpliceVersion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.runDir = os.path.join(self.tmp, "s_v1")
        self.narrowDir = os.path.join(self.tmp, "s_v1__rerun")
        self._writeRun(self.runDir,
                       [cand("AD", 60), cand("ETH", 60, True), cand("ETH", 120), cand("GC", 60, True)],
                       [trad("ETH", 60), trad("GC", 60)],
                       [row("AD", 60), row("ETH", 60, True), row("ETH", 120), row("GC", 60, True)],
                       units=["ETH_M60", "GC_M60"],
                       ledger={"AD_M60": {"symbol": "AD"}, "ETH_M120": {"symbol": "ETH"}})
        self._writeRun(self.narrowDir,
                       [cand("ETH", 60, tag="new"), cand("ETH", 120, True, tag="new")],
                       [trad("ETH", 120, tag="new")],
                       [row("ETH", 60), row("ETH", 120, True)],
                       units=["ETH_M60", "ETH_M120"])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _writeRun(self, d, cands, trads, rows, units=(), ledger=None):
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, rs.REPORT_JSON), "w") as f:
            json.dump(report(cands, trads), f)
        with open(os.path.join(d, rs.SUMMARY_CSV), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADER)
            w.writeheader()
            w.writerows(rows)
        for u in units:
            os.makedirs(os.path.join(d, u))
            with open(os.path.join(d, u, "wf_results.json"), "w") as f:
                f.write("{}")
        if ledger is not None:
            with open(os.path.join(d, rs.pruneRuns.PRUNE_LEDGER), "w") as f:
                json.dump({"format": "pruneRuns-ledger-1", "units": ledger}, f)

    def test_endToEnd(self):
        before, after = rs.spliceVersion(self.runDir, self.narrowDir, {"ETH"}, echo=lambda *a: None)
        self.assertEqual(before, [("ETH", 60, "252-126")])
        self.assertEqual(after, [("ETH", 120, "252-126")])
        rep = json.load(open(os.path.join(self.runDir, rs.REPORT_JSON)))
        self.assertEqual([c["metrics"]["tag"] for c in rep["candidates"]], ["old", "new", "new", "old"])
        self.assertTrue(os.path.isfile(os.path.join(self.runDir, rs.PRE_RERUN_REPORT)))
        rows = list(csv.DictReader(open(os.path.join(self.runDir, rs.SUMMARY_CSV))))
        self.assertEqual([(r["symbol"], r["timeframe_minutes"], r["tradeable"]) for r in rows],
                         [("AD", "60", "false"), ("ETH", "60", "false"), ("ETH", "120", "true"), ("GC", "60", "true")])
        self.assertEqual(sorted(e for e in os.listdir(self.runDir) if "_M" in e), ["ETH_M120", "ETH_M60", "GC_M60"])
        self.assertFalse(os.path.isdir(os.path.join(self.narrowDir, "ETH_M60")))
        ledger = json.load(open(os.path.join(self.runDir, rs.pruneRuns.PRUNE_LEDGER)))
        self.assertEqual(list(ledger["units"]), ["AD_M60"])
        marker = json.load(open(os.path.join(self.runDir, rs.RERUN_MARKER)))
        self.assertEqual(marker["symbols"], ["ETH"])
        self.assertEqual(marker["units_moved"], 2)
        self.assertTrue(rs.alreadyDone(self.runDir, {"ETH"}))
        self.assertFalse(rs.alreadyDone(self.runDir, {"ETH", "BTC"}))

    def test_preRerunReportKeptOnlyOnce(self):
        rs.spliceVersion(self.runDir, self.narrowDir, {"ETH"}, echo=lambda *a: None)
        pre = open(os.path.join(self.runDir, rs.PRE_RERUN_REPORT)).read()
        # a second splice (with a re-made narrowed run) must not overwrite the original
        self._writeRun(self.narrowDir, [cand("ETH", 60, tag="newer"), cand("ETH", 120, tag="newer")], [],
                       [row("ETH", 60), row("ETH", 120)], units=["ETH_M60", "ETH_M120"])
        rs.spliceVersion(self.runDir, self.narrowDir, {"ETH"}, echo=lambda *a: None)
        self.assertEqual(open(os.path.join(self.runDir, rs.PRE_RERUN_REPORT)).read(), pre)
        rep = json.load(open(os.path.join(self.runDir, rs.REPORT_JSON)))
        self.assertEqual(rep["tradeable"], [trad("GC", 60)])


class TestRerunFamily(unittest.TestCase):
    """rerunFamily with a fake engine: the runner fabricates the narrowed run."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.engine = os.path.join(self.tmp, "engine")
        os.makedirs(os.path.join(self.engine, "build", "release"))
        open(os.path.join(self.engine, rs.WALKFORWARD_EXE), "w").close()
        self.cfg = {"engineDir": self.engine, "specOutputSubdir": "specs/generated"}
        self.specDir = os.path.join(self.engine, "specs", "generated")
        self.runs = os.path.join(self.engine, "runs")
        os.makedirs(self.specDir)
        for v in (1, 2):
            with open(os.path.join(self.specDir, f"fam_v{v}.json"), "w") as f:
                json.dump({"name": f"fam_v{v}", "strategy": f"F V{v}", "symbols": ["AD", "ETH"],
                           "timeframes": [60], "selection": {"filters": FILTERS}}, f)
            d = os.path.join(self.runs, f"fam_v{v}")
            os.makedirs(d)
            with open(os.path.join(d, rs.REPORT_JSON), "w") as f:
                json.dump(report([cand("AD", 60, v == 1), cand("ETH", 60, True)], [trad("ETH", 60)]), f)
            with open(os.path.join(d, rs.SUMMARY_CSV), "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=HEADER)
                w.writeheader()
                w.writerows([row("AD", 60, v == 1), row("ETH", 60, True)])
            os.makedirs(os.path.join(d, "ETH_M60"))
        self.calls = []

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fakeRunner(self, cmd, cwd=None, **kw):
        self.calls.append(cmd)
        specPath = cmd[cmd.index("--spec") + 1]
        spec = json.load(open(specPath))
        self.assertEqual(spec["symbols"], ["ETH"])
        d = os.path.join(self.runs, spec["name"])
        os.makedirs(d)
        tradeable = spec["name"].startswith("fam_v1")
        with open(os.path.join(d, rs.REPORT_JSON), "w") as f:
            json.dump(report([cand("ETH", 60, tradeable, tag="new")],
                             [trad("ETH", 60, tag="new")] if tradeable else []), f)
        with open(os.path.join(d, rs.SUMMARY_CSV), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADER)
            w.writeheader()
            w.writerows([row("ETH", 60, tradeable)])
        os.makedirs(os.path.join(d, "ETH_M60"))
        open(os.path.join(d, "run.log"), "w").close()

        class P:
            returncode = 0
        return P()

    def test_familyRunSplicesAndAggregates(self):
        out = rs.rerunFamily("fam", {"ETH"}, self.cfg, runner=self.fakeRunner, echo=lambda *a: None)
        self.assertEqual(out["reran"], [1, 2])
        self.assertEqual(len(self.calls), 2)
        self.assertIn("--quiet", self.calls[0])
        # v2 lost its ETH tradeable, v1 kept it
        self.assertEqual(out["deltas"][2], ([("ETH", 60, "252-126")], []))
        self.assertEqual(out["deltas"][1], ([("ETH", 60, "252-126")], [("ETH", 60, "252-126")]))
        # narrowed run dirs and specs are gone, the aggregate exists
        self.assertFalse(os.path.exists(os.path.join(self.runs, "fam_v1__rerun")))
        self.assertFalse(os.path.exists(os.path.join(self.specDir, "fam_v1__rerun.json")))
        agg = os.path.join(self.runs, "fam", rs.SUMMARY_CSV)
        rows = list(csv.DictReader(open(agg)))
        self.assertEqual([(r["run"], r["symbol"], r["tradeable"]) for r in rows],
                         [("fam_v1", "AD", "true"), ("fam_v1", "ETH", "true"),
                          ("fam_v2", "AD", "false"), ("fam_v2", "ETH", "false")])
        # a second invocation skips both
        self.calls.clear()
        out = rs.rerunFamily("fam", {"ETH"}, self.cfg, runner=self.fakeRunner, echo=lambda *a: None)
        self.assertEqual(out["skipped"], [1, 2])
        self.assertEqual(self.calls, [])

    def test_versionsFilterAndDryRun(self):
        out = rs.rerunFamily("fam", {"ETH"}, self.cfg, versions={2}, dryRun=True,
                             runner=self.fakeRunner, echo=lambda *a: None)
        self.assertEqual(self.calls, [])
        self.assertEqual(out["reran"], [])
        with self.assertRaises(GenerationError):
            rs.rerunFamily("fam", {"ETH"}, self.cfg, versions={9}, runner=self.fakeRunner,
                           echo=lambda *a: None)

    def test_symbolAbsentFromSpecIsNoOp(self):
        out = rs.rerunFamily("fam", {"MET"}, self.cfg, runner=self.fakeRunner, echo=lambda *a: None)
        self.assertEqual(self.calls, [])
        self.assertEqual(out["deltas"], {})


if __name__ == "__main__":
    unittest.main()

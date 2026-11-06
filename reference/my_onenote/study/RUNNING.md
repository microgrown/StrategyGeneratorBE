# Running the own-rules platinum validation (OWN-01..64)

These are instructions for running the 64 own-rules families on a second machine while the
Brooks study (BRK-01..50) runs on the first. They also cover splitting the remaining
families between the two machines if Brooks finishes first.

- **What a run is:** each family is one `runBatch.py <stem>_platinum_validation --prune`,
  which means 360 versions, 45 symbols and 9 timeframes, each a full walkforward.
- **Dates:**
  - WF 2007-01-01 -> 2019-04-01
  - incubation -> 2020-01-01
  - held-out OOS -> 2023-01-01
- **Time:** on the first machine a BRK family takes 1.2-4 hours, 2.5 on average. Budget about a week for all 64 on one machine.

## 0. Prerequisites on the second machine

- **Repos:** `BacktestEngine` and `StrategyGeneratorBE`, both up to date (`git pull`).
  `StrategyGeneratorTS` is not needed to run.
- **Python** (the same 3.x as the first machine).
- **Visual Studio** with the C++ x64 toolset and the "C++ CMake tools" component.
  - The committed `BacktestEngine/scripts/build.ps1` hardcodes the VS 18 BuildTools and Community paths.
  - The first machine's working copy has an uncommitted `vswhere` version that finds any install.
  - If the build cannot find `vcvarsall.bat`, copy that `build.ps1` over (or commit it first).
- **`StrategyGeneratorBE/config.json`** is committed with this machine's absolute paths
  (`C:\Users\brian\source\repos\...`).
  - If the second machine's repos live elsewhere, edit `engineDir` and `specTemplate` there.
  - Do not commit that edit.
- **Identical bar data:**
  - `BacktestEngine/data/` is not in git (about 34 GB). Copy the whole folder from the first machine.
  - Also copy `BacktestEngine/data_epochs/registry.json`, the registry only and not the epoch zips. That lets you prove the data is byte-identical:

    ```
    cd StrategyGeneratorBE
    python snapshotData.py --verify
    ```

    Every symbol must print `matches epoch ...`. Any `DRIFTED` or `NEVER SNAPSHOTTED`
    means the data differs from what the BAS and BRK runs used. Stop and fix that first; the
    study compares arms, so they must see the same bars.
  - Then record an epoch on this machine. `--prune` refuses to start without one:

    ```
    python snapshotData.py --snapshot --note "own-rules study, second machine"
    ```

## 1. Generate the 64 families (specs; headers come from git)

The C++ headers, `registry.inc`, `headers.inc` and `manifest.json` for OWN-01..64 are
committed in BacktestEngine. The walkforward specs (`BacktestEngine/specs/generated/`) are
gitignored, so each machine writes its own. `makeStrategy.py` writes both. Re-writing the
committed headers is the determinism check:

```
cd StrategyGeneratorBE
for /L %i in (1,1,9) do python makeStrategy.py "202611 OWN-0%i" --no-save-template
for /L %i in (10,1,64) do python makeStrategy.py "202611 OWN-%i" --no-save-template
```

(Use `%%i` inside a .cmd file.)

Then check two things:
- `git -C ..\BacktestEngine status --short src/bt/strategies/generated` prints **nothing**. A diff means the second machine generated something different; stop and compare.
- `BacktestEngine\specs\generated` holds `s_202611_own_01_v1.json` .. `s_202611_own_64_v360.json` (23,040 files).

The spec template is `BacktestEngine/specs/Futures_Swing.json` (config.json's `specTemplate`), the same one the BAS and BRK families were generated from. `--no-save-template` keeps the committed `templates/202611 OWN-*.json` untouched.

## 2. Build the engine

```
cd BacktestEngine
.\scripts\build.ps1 -Config Release
```

This compiles every generated family (BAS, BRK and OWN), so it is a long build.
`build\release\bt_walkforward.exe` must exist afterwards.

## 3. Run

```
cd StrategyGeneratorBE
runPlatinumStudy.cmd --kind own
```

What it does:
1. **Clones the twins:** `clonePlatinumSpecs.py --kind own` writes `s_202611_own_NN_platinum_validation_vK.json` next to each generated spec. Each is re-dated (WF to 2019-04-01, incubation to 2020-01-01, `oos_end` 2023-01-01), drops ETH and BTC, and gets the standard chain plus `trade_count` (min 30) and the record-only `monte_carlo` stage.
2. **Runs each family in order** with `runBatch.py ... --prune`.

Check the clone against `sample_s_202611_own_01_platinum_validation_v1.json` in this folder. It is what the first machine wrote for OWN-01 V1:

```
fc /n ..\BacktestEngine\specs\generated\s_202611_own_01_platinum_validation_v1.json reference\my_onenote\study\sample_s_202611_own_01_platinum_validation_v1.json
```

Every OWN spec has this shape. Only `name`, `strategy` and `max_bars_back` (250 or 500) vary.

- **Log:** `StrategyGeneratorBE\temp\runPlatinumStudy_kind_own.log`.
- **Results:** `BacktestEngine\runs\s_202611_own_NN_platinum_validation\` (the `selection_report.json` and `candidate_metrics.csv` the analysis reads).
- **Resumable:** after a crash, reboot or Ctrl+C, run the same command again. `runBatch` skips every version that already has a selection report, and the clone step leaves existing twins alone.

## 4. Splitting the remaining work (if Brooks finishes first)

The first machine already has the OWN specs (they were generated there for the commit).
Before it can run OWN families, it needs one thing:

```
cd BacktestEngine
.\scripts\build.ps1 -Config Release      (only after the BRK batch has finished)
```

To split the work:

1. On the second machine, find the family it is on: the last `===== ... start` line in its log.
   Say that is OWN-k.
2. Stop it with Ctrl+C. Answer `Y` to "Terminate batch job".
3. Pick a split point M between k and 64. The second machine has its own pace, so split by
   remaining time, not by count.
4. Restart the second machine on k..M. OWN-k resumes where it stopped:

   ```
   runPlatinumStudy.cmd --kind own --range k-M
   ```

5. Start the first machine on the rest:

   ```
   runPlatinumStudy.cmd --kind own --range M+1-64     (write the number, e.g. --range 41-64)
   ```

Never run the same family on both machines. The two would write separate `runs/` folders
and you would have to pick one.

## 5. Bringing the results together

When the second machine is done, copy each `BacktestEngine\runs\s_202611_own_*_platinum_validation\`
folder it produced to the first machine's `BacktestEngine\runs\`. Families split by
`--range` never overlap, so nothing is overwritten. The IS-vs-OOS analysis scripts read
those folders.

## Reference

- `SELECTION.md`: the families, pools, draw and Brian's decisions.
- `assignment.json`: what each family drew.
- `../../../clonePlatinumSpecs.py`: the platinum twin rules (dates, dropped symbols, chain).
- `../../../runPlatinumFamilies.cmd`: the unfiltered runner (every family on the machine, BAS and BRK included). Use `runPlatinumStudy.cmd --kind own` for this study.

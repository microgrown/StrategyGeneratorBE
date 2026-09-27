@echo off
rem Run every calendar-period twin family (<stem>_cal, made by cloneCalendarSpecs.py)
rem with runBatch --prune, one after another, logging to temp\runCalendarFamilies.log.
rem
rem   python cloneCalendarSpecs.py        first, on this machine (specs\generated is not in git)
rem   runCalendarFamilies.cmd             then this, detached (Task Scheduler or Start-Process)
rem
rem Resumable: runBatch skips every version that already has a selection report, so
rem re-running this file after a crash or reboot continues where it stopped. No
rem --rerun-before here -- the twins are new families, nothing is stale. --prune needs a
rem data epoch (python snapshotData.py --snapshot); the batch refuses to start without one.
rem Same family order as the 2026-09-13 full re-run (temp\rerun_all_20260913.cmd).
cd /d "%~dp0"
if not exist temp mkdir temp
set LOG=%~dp0temp\runCalendarFamilies.log
echo ===== BATCH START %date% %time% >> "%LOG%"
for %%F in (s_202608_bas_1_cal s_202608_bas_2_cal s_202608_bas_3_cal s_202608_bas_12_cal s_202608_bas_13_cal s_202608_bas_14_cal s_202607_bas_1_cal s_202607_bas_2_cal s_202607_bas_3_cal s_202607_bas_4_cal s_202606_bas_1_cal s_202606_bas_2_cal) do (
  echo ===== %%F start %date% %time% >> "%LOG%"
  python runBatch.py %%F --prune >> "%LOG%" 2>&1
  call echo ===== %%F exit %%errorlevel%% >> "%LOG%"
)
echo ALL FAMILIES DONE %date% %time% >> "%LOG%"

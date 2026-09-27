@echo off
setlocal EnableDelayedExpansion
rem Run every calendar-period twin family (<stem>_cal) with runBatch --prune, one
rem after another, logging to temp\runCalendarFamilies.log.
rem
rem Nothing is hardcoded: the file first runs cloneCalendarSpecs.py (idempotent --
rem it writes whatever twins are missing and leaves the rest alone), then loops over
rem "cloneCalendarSpecs.py --list", the twin stems that exist in specs\generated on
rem THIS machine. So it works unchanged wherever specs\generated has been synced.
rem
rem Resumable: runBatch skips every version that already has a selection report, so
rem re-running this file after a crash or reboot continues where it stopped. No
rem --rerun-before -- the twins are new families, nothing is stale. --prune needs a
rem data epoch (python snapshotData.py --snapshot); the batch refuses to start without one.
cd /d "%~dp0"
if not exist temp mkdir temp
set "LOG=%~dp0temp\runCalendarFamilies.log"
echo ===== BATCH START %date% %time% >> "%LOG%"
echo ===== cloneCalendarSpecs >> "%LOG%"
python cloneCalendarSpecs.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo cloneCalendarSpecs.py failed; see "%LOG%"
    echo ===== cloneCalendarSpecs FAILED, batch not started >> "%LOG%"
    exit /b 2
)
set /a n=0
for /f "usebackq delims=" %%F in (`python cloneCalendarSpecs.py --list`) do (
    set /a n+=1
    echo ===== %%F start !date! !time! >> "%LOG%"
    python runBatch.py %%F --prune >> "%LOG%" 2>&1
    call echo ===== %%F exit %%errorlevel%% >> "%LOG%"
)
echo ALL FAMILIES DONE %date% %time% ^(%n% families^) >> "%LOG%"
endlocal

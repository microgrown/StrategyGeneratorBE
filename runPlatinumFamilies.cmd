@echo off
setlocal EnableDelayedExpansion
rem Run every platinum-validation twin family (<stem>_platinum_validation) with
rem runBatch --prune, one after another, logging to temp\runPlatinumFamilies.log.
rem
rem Nothing is hardcoded: the file first runs clonePlatinumSpecs.py (idempotent --
rem it writes whatever twins are missing and leaves the rest alone), then loops over
rem "clonePlatinumSpecs.py --list", the twin stems that exist in specs\generated on
rem THIS machine.
rem
rem No OOS step: the specs carry oos_end, so bt_walkforward records the held-out
rem segment's metrics for every candidate before --prune removes the rejects.
rem
rem Resumable: runBatch skips every version that already has a selection report, so
rem re-running this file after a crash or reboot continues where it stopped. --prune
rem needs a data epoch (python snapshotData.py --snapshot); the batch refuses to
rem start without one.
cd /d "%~dp0"
if not exist temp mkdir temp
set "LOG=%~dp0temp\runPlatinumFamilies.log"
echo ===== BATCH START %date% %time% >> "%LOG%"
echo ===== clonePlatinumSpecs >> "%LOG%"
python clonePlatinumSpecs.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo clonePlatinumSpecs.py failed; see "%LOG%"
    echo ===== clonePlatinumSpecs FAILED, batch not started >> "%LOG%"
    exit /b 2
)
set /a n=0
for /f "usebackq delims=" %%F in (`python clonePlatinumSpecs.py --list`) do (
    set /a n+=1
    echo ===== %%F start !date! !time! >> "%LOG%"
    python runBatch.py %%F --prune >> "%LOG%" 2>&1
    call echo ===== %%F exit %%errorlevel%% >> "%LOG%"
)
echo ALL FAMILIES DONE %date% %time% ^(%n% families^) >> "%LOG%"
endlocal

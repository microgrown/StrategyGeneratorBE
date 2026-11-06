@echo off
setlocal EnableDelayedExpansion
rem Run a SELECTION of platinum-validation twin families with runBatch --prune,
rem one after another. runPlatinumFamilies.cmd with a filter: every argument is
rem passed to clonePlatinumSpecs.py, both to write the missing twins and to list
rem the stems to run.
rem
rem   runPlatinumStudy.cmd --kind own                 the own-rules study, OWN-01..64
rem   runPlatinumStudy.cmd --kind own --range 33-64   only families 33..64 of it
rem   runPlatinumStudy.cmd s_202611_own_07            one family
rem
rem Log: temp\runPlatinumStudy_<arguments>.log, so two selections on one machine
rem never share a log. Resumable exactly like runPlatinumFamilies.cmd: runBatch
rem skips every version that already has a selection report. --prune needs a data
rem epoch (python snapshotData.py --snapshot).
cd /d "%~dp0"
if "%~1"=="" (
    echo usage: runPlatinumStudy.cmd --kind own [--range LO-HI]  ^|  runPlatinumStudy.cmd STEM ...
    exit /b 2
)
if not exist temp mkdir temp
set "TAG=%*"
set "TAG=%TAG:--=%"
set "TAG=%TAG: =_%"
set "LOG=%~dp0temp\runPlatinumStudy_%TAG%.log"
echo ===== BATCH START %date% %time% (%*) >> "%LOG%"
echo ===== clonePlatinumSpecs %* >> "%LOG%"
python clonePlatinumSpecs.py %* >> "%LOG%" 2>&1
if errorlevel 1 (
    echo clonePlatinumSpecs.py failed; see "%LOG%"
    echo ===== clonePlatinumSpecs FAILED, batch not started >> "%LOG%"
    exit /b 2
)
set /a n=0
for /f "usebackq delims=" %%F in (`python clonePlatinumSpecs.py %* --list`) do (
    set /a n+=1
    echo ===== %%F start !date! !time! >> "%LOG%"
    python runBatch.py %%F --prune >> "%LOG%" 2>&1
    call echo ===== %%F exit %%errorlevel%% >> "%LOG%"
)
echo ALL FAMILIES DONE %date% %time% ^(%n% families^) >> "%LOG%"
endlocal

@echo off
REM wrapper temporar pt diagnostic - capturez tot output-ul ETL intr-un fisier de log
REM ca sa-l scot: pun inapoi actiunea task-ului pe python.exe direct si sterg acest fisier + folderul logs

setlocal

set "PROJECT_DIR=D:\Proiecte\test_web1"
set "PYTHON=%PROJECT_DIR%\etl\.venv\Scripts\python.exe"
set "LOGDIR=%PROJECT_DIR%\etl\logs"

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM iau timestamp ISO prin PowerShell ca sa nu depind de formatul de data locale (RO vs EN)
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set "TS=%%i"

set "LOGFILE=%LOGDIR%\etl_%TS%.log"

cd /d "%PROJECT_DIR%"

REM -u = unbuffered, ca sa vad output-ul incremental in log, nu doar la final
"%PYTHON%" -u -m etl.main > "%LOGFILE%" 2>&1

endlocal

@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

where g++ >nul 2>nul || (echo g++ not found. See How_to_run_everything.txt for the Windows install steps. & exit /b 1)

set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul || (echo Python not found. See How_to_run_everything.txt for the Windows install steps. & exit /b 1)

%PY% -m pip install pandas openpyxl || exit /b 1
g++ -o error_detector.exe error_detector.cpp -std=c++17 || exit /b 1
error_detector.exe > errors_raw.csv || exit /b 1
%PY% generate_report.py || exit /b 1
%PY% fix_errors.py || exit /b 1

copy /y students.csv students_original.csv >nul
copy /y students_corrected.csv students.csv >nul
%PY% roomateMatcher.py
set MATCHER_EXIT=%errorlevel%
copy /y students_original.csv students.csv >nul
del students_original.csv
exit /b %MATCHER_EXIT%

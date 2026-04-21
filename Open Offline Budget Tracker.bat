@echo off
setlocal

set "APP_ROOT=%~dp0"
set "INSTALLED_EXE=%LocalAppData%\Programs\Student Budget Tracker\StudentBudgetTracker.exe"
set "INSTALLED_EXE_FALLBACK=%LocalAppData%\Programs\Student Budget Tracker\Student Budget Tracker.exe"
set "RELEASE_EXE=%APP_ROOT%src-tauri\target\release\StudentBudgetTracker.exe"
set "RELEASE_EXE_FALLBACK=%APP_ROOT%src-tauri\target\release\student-budget-tracker.exe"
set "DEBUG_EXE=%APP_ROOT%src-tauri\target\debug\StudentBudgetTracker.exe"
set "DEBUG_EXE_FALLBACK=%APP_ROOT%src-tauri\target\debug\student-budget-tracker.exe"

if exist "%INSTALLED_EXE%" (
    start "" "%INSTALLED_EXE%"
    exit /b 0
)

if exist "%INSTALLED_EXE_FALLBACK%" (
    start "" "%INSTALLED_EXE_FALLBACK%"
    exit /b 0
)

if exist "%RELEASE_EXE%" (
    start "" "%RELEASE_EXE%"
    exit /b 0
)

if exist "%RELEASE_EXE_FALLBACK%" (
    start "" "%RELEASE_EXE_FALLBACK%"
    exit /b 0
)

if exist "%DEBUG_EXE%" (
    start "" "%DEBUG_EXE%"
    exit /b 0
)

if exist "%DEBUG_EXE_FALLBACK%" (
    start "" "%DEBUG_EXE_FALLBACK%"
    exit /b 0
)

echo.
echo Could not find a built or installed Student Budget Tracker desktop app.
echo Build it with build_windows.ps1 or run "pnpm tauri:dev" from the repo root.
pause

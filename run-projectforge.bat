@echo off
setlocal EnableExtensions

REM ProjectForge one-click Windows launcher.
REM Usage:
REM   run-projectforge.bat "C:\path\to\venv\Scripts\Activate.ps1" "C:\Program Files\nodejs\npm.cmd"

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "PROJECTFORGE_ACTIVATE=%~f1"
set "PROJECTFORGE_NPM=%~f2"
set "PROJECTFORGE_ROOT=%~dp0"

if not exist "%PROJECTFORGE_ACTIVATE%" (
  echo ERROR: Python virtual environment activation script not found:
  echo   "%PROJECTFORGE_ACTIVATE%"
  exit /b 2
)
if not exist "%PROJECTFORGE_NPM%" (
  echo ERROR: npm executable not found:
  echo   "%PROJECTFORGE_NPM%"
  exit /b 2
)
if not exist "%PROJECTFORGE_ROOT%backend\main.py" (
  echo ERROR: backend\main.py was not found. Run this BAT from the extracted ProjectForge folder.
  exit /b 2
)
if not exist "%PROJECTFORGE_ROOT%frontend\package.json" (
  echo ERROR: frontend\package.json was not found. Run this BAT from the extracted ProjectForge folder.
  exit /b 2
)

REM Keep the secret stable for the lifetime of this launch. Set a persistent
REM PROJECTFORGE_SECRET in your environment for a stable secret between runs.
if not defined PROJECTFORGE_SECRET set "PROJECTFORGE_SECRET=ProjectForge-dev-%RANDOM%-%RANDOM%-%RANDOM%"

 echo Starting ProjectForge API and frontend in separate terminal windows...
start "ProjectForge API" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; . $env:PROJECTFORGE_ACTIVATE; Set-Location (Join-Path $env:PROJECTFORGE_ROOT 'backend'); $null = python -c 'import fastapi,uvicorn,multipart' 2>$null; if ($LASTEXITCODE -ne 0) { Write-Host 'Installing Python dependencies...'; python -m pip install -r requirements.txt }; $env:PROJECTFORGE_SECRET=$env:PROJECTFORGE_SECRET; python -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM Use PowerShell for the frontend command to avoid cmd.exe nested-quote parsing errors.
start "ProjectForge Frontend" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $npm=$env:PROJECTFORGE_NPM; Set-Location (Join-Path $env:PROJECTFORGE_ROOT 'frontend'); if (-not (Test-Path 'node_modules')) { Write-Host 'Installing frontend dependencies...'; & $npm install; if ($LASTEXITCODE -ne 0) { throw 'npm install failed' } }; & $npm run dev"

echo.
echo ProjectForge is starting. Wait for both terminal windows to report ready.
echo Frontend: http://localhost:5173
echo API docs: http://127.0.0.1:8000/docs
echo Demo login: admin / ChangeMe123!
echo.
echo This is a development launcher. Change the demo password and configure a strong
 echo PROJECTFORGE_SECRET before using real or sensitive data.
exit /b 0

:usage
echo ProjectForge one-click launcher
 echo.
echo Usage:
echo   %~nx0 "C:\path\to\venv\Scripts\Activate.ps1" "C:\Program Files\nodejs\npm.cmd"
echo.
echo Parameter 1: Full path to the Python venv Activate.ps1 file
echo Parameter 2: Full path to npm.cmd (or compatible npm executable)
exit /b 1

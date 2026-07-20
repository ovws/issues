@echo off
setlocal
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "POWERSHELL_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%POWERSHELL_EXE%" (
    echo [ERROR] Windows PowerShell 5.1 is not available.
    exit /b 1
)

"%POWERSHELL_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\start-ai-api.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not defined AI_API_NO_PAUSE pause
exit /b %EXIT_CODE%
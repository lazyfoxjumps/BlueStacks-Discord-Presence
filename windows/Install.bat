@echo off
rem Double-click to install BlueStacks Discord Presence for the current user.
rem It starts right away and at every login. Safe to run again: it updates in place.
setlocal

set "NAME=bluestacks-discord-presence"
set "APP_DIR=%LOCALAPPDATA%\%NAME%"
set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BlueStacks Discord Presence.lnk"
set "SRC=%~dp0"

rem Find a windowless Python: the py launcher's pyw first, then pythonw on PATH.
set "PYW="
for %%P in (pyw.exe pythonw.exe) do if not defined PYW for /f "delims=" %%F in ('where %%P 2^>nul') do if not defined PYW set "PYW=%%F"
if not defined PYW (
    echo Python 3.8+ was not found.
    echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this again.
    pause
    exit /b 1
)

rem Stop a running copy before replacing it.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bluestacks_discord_presence.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
copy /y "%SRC%bluestacks_discord_presence.py" "%APP_DIR%\" >nul
rem Offline copy of Discord's game list, used until the first daily download succeeds.
if exist "%SRC%games-seed.json.gz" copy /y "%SRC%games-seed.json.gz" "%APP_DIR%\" >nul
rem Keep an existing config.json (fallback app ID) across reinstalls.
if not exist "%APP_DIR%\config.json" if exist "%SRC%config.json" copy /y "%SRC%config.json" "%APP_DIR%\" >nul

rem Start at every login through a Startup folder shortcut (no admin needed, no console window).
powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:SHORTCUT); $s.TargetPath = $env:PYW; $s.Arguments = '\"' + $env:APP_DIR + '\bluestacks_discord_presence.py\"'; $s.WorkingDirectory = $env:APP_DIR; $s.Save()"

start "" "%PYW%" "%APP_DIR%\bluestacks_discord_presence.py"

echo BlueStacks Discord Presence is installed and running.
echo Log: %APP_DIR%\bluestacks-discord-presence.log
echo.
pause

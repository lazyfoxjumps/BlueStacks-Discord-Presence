@echo off
rem Double-click to stop BlueStacks Discord Presence and remove everything Install.bat created.
setlocal

set "APP_DIR=%LOCALAPPDATA%\bluestacks-discord-presence"
set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BlueStacks Discord Presence.lnk"

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bluestacks_discord_presence.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
if exist "%SHORTCUT%" del /q "%SHORTCUT%"
if exist "%APP_DIR%" rmdir /s /q "%APP_DIR%"

echo BlueStacks Discord Presence is uninstalled.
echo.
pause

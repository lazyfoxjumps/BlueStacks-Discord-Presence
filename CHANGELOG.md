# Changelog

All notable changes to BlueStacks Discord Presence are listed here.
This project follows [Keep a Changelog](https://keepachangelog.com/), and versions aim for
[Semantic Versioning](https://semver.org/).

## [0.1 beta] - 2026-10-29

The first public beta. 🎉 Android games you play in BlueStacks now show up on your Discord
profile, on both macOS and Windows.

### Added

**Discord status for BlueStacks games**
- Follows BlueStacks' log to see which Android app is on screen, and sets your Discord status to
  "Playing [game]", with the game's official name, icon and elapsed timer.
- Clears your status when you go back to the BlueStacks home screen or quit BlueStacks.
- Ignores short system pop-ups (permission prompts, Play Store, Google services), so your status
  doesn't flicker.
- Reconnects on its own if Discord is restarted while you play.
- Backup detection through BlueStacks' own ADB, for setups where the log doesn't show app switches.

**Game recognition**
- Matches the game's Play Store package name against the ~1,660 games Discord links to Google Play.
- Matches the game's name against every game name and alias Discord knows.
- Optional fallback app for games Discord doesn't know, set in `config.json`.

**macOS and Windows**
- macOS: works with BlueStacks Air, and starts at login as a LaunchAgent that macOS restarts if it
  ever crashes.
- Windows: works with BlueStacks 5, and starts at login from a Startup-folder shortcut, with no
  console window and no admin rights needed. It restarts itself after a crash.
- Talks to Discord through a Unix socket on macOS and a named pipe on Windows.

**Keeps working**
- Downloads Discord's game list once a day, so new games work without reinstalling.
- Includes an offline copy of the game list for the first launch.
- Picks up where it left off if BlueStacks starts a fresh log.

**Install and uninstall**
- macOS: double-click `Install.command` (or run `sh install.sh`), and `Uninstall.command` to remove.
- Windows: double-click `Install.bat`, and `Uninstall.bat` to remove.
- The installers find a suitable Python on their own and explain how to get one if it's missing.
- Running an installer again updates in place and keeps your `config.json`.
- Runs side by side with MacOS Crossover Discord Presence without conflicts.

### Known issues

- The Windows version hasn't been tested on a real Windows PC yet. If BlueStacks 5's log doesn't
  record app switches the way BlueStacks Air does, turn on ADB in BlueStacks settings so the backup
  detection can take over.
- On your own screen, Discord redraws the timer less often while it's in the background. Friends
  see it ticking normally.
- Only one BlueStacks game shows at a time, since BlueStacks shows one app at a time.

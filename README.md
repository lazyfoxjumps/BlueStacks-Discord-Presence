# BlueStacks Discord Presence 📱

Show **"Playing [game]"** on your Discord profile for Android games you play in BlueStacks, on **macOS** and **Windows**.

## 🤔 What is this?

BlueStacks lets you play Android games on your computer, but it doesn't tell Discord what you're playing. So you can grind for hours and your profile just sits there, blank.

This is a small script that runs quietly in the background and fixes that. BlueStacks writes down every app you open in its log, so the script reads along, spots which game is on screen, and tells the Discord app on your computer. Your profile then shows the game's official name, its icon and the elapsed timer.

## ✨ Features

- 🎯 **Automatic.** Open a game in BlueStacks, and within about 10 seconds your status updates. Go back to the home screen or quit, and it clears.
- 🏷️ **Official names and icons.** It uses each game's real Discord listing, not a generic "BlueStacks" label.
- 🙈 **No flickering.** Quick system pop-ups, like permission prompts or the Play Store, don't interrupt your status.
- 🆕 **New games just work.** It downloads Discord's game list once a day, so nothing needs reinstalling when you add games.
- ✈️ **Works offline.** A copy of the game list is included, so it works on first launch even without internet.
- 🔒 **Doesn't touch your account.** No login, no token, no password. It only talks to the Discord app running on your computer.
- 🪶 **Nothing to set up in BlueStacks.** It reads the log BlueStacks already writes. (On Windows there's an optional backup, see below.)

## ⬇️ Installation

### 🍎 macOS

1. Download **[`BlueStacks-Discord-Presence-0.1-beta-macOS.zip`](https://github.com/lazyfoxjumps/BlueStacks-Discord-Presence/releases/download/v0.1-beta/BlueStacks-Discord-Presence-0.1-beta-macOS.zip)** and unzip it. (Or grab it from the [Releases page](https://github.com/lazyfoxjumps/BlueStacks-Discord-Presence/releases).)
2. Double-click **`Install.command`**.
3. Open a game in BlueStacks and check your Discord profile. 🎉

Prefer Terminal? Run `sh install.sh` from the unzipped folder instead.

**"Install.command can't be opened"?** macOS is cautious about scripts downloaded from the internet. Right-click **`Install.command`**, choose **Open**, then click **Open** again. You only need to do this once.

### 🪟 Windows

1. Download **[`BlueStacks-Discord-Presence-0.1-beta-Windows.zip`](https://github.com/lazyfoxjumps/BlueStacks-Discord-Presence/releases/download/v0.1-beta/BlueStacks-Discord-Presence-0.1-beta-Windows.zip)** and unzip it. (Or grab it from the [Releases page](https://github.com/lazyfoxjumps/BlueStacks-Discord-Presence/releases).)
2. Double-click **`Install.bat`**.
3. Open a game in BlueStacks and check your Discord profile. 🎉

**"Windows protected your PC"?** That's SmartScreen being careful with a downloaded script. Click **More info**, then **Run anyway**.

That's it on either system. It's now running, and it starts automatically every time you log in.

### Requirements

- **BlueStacks**: BlueStacks Air on macOS, BlueStacks 5 on Windows.
- **Python 3.8 or newer.**
  - macOS: if the installer says Python is missing, run `xcode-select --install`, let it finish, then run the installer again.
  - Windows: get it from [python.org](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"** during setup.
- **The Discord desktop app**, open while you play.
- **Activity sharing turned on** in Discord: Settings → Activity Privacy → "Share your detected activities with others".

## 🕵️ How it recognizes your game

It checks these in order, and stops at the first match:

1. **The game's Play Store package name** (like `com.robtopx.geometryjump`), against the ~1,660 games Discord links to Google Play.
2. **The game's name**, as BlueStacks shows it, against every game name Discord knows. Lots of popular mobile games also have a PC or console version, so this catches a ton of them.
3. **A fallback** for games Discord has never heard of (optional, see below).

### 🔌 Backup: ADB

If BlueStacks' log doesn't show app switches on your setup, the script can ask BlueStacks directly which app is on screen, through BlueStacks' own Android Debug Bridge (ADB). To turn it on: BlueStacks **Settings → Advanced → Android Debug Bridge (ADB)**. The script finds it on its own, nothing else to set up. This route can't read game titles, so it matches by package name only.

## 🧩 Optional: show games Discord doesn't know

Discord needs an app listing to show any game. Plenty of mobile-only games don't have one, so you can create a stand-in:

1. Create a free application in the [Discord Developer Portal](https://discord.com/developers/applications). Name it what you'd like your status to say, for example **"a game on BlueStacks"**.
2. Copy its **Application ID** into a file named `config.json`, in the same folder as the installer:

   ```json
   { "fallback_app_id": "123456789012345678" }
   ```

3. Run the installer again.

Unknown games will then show as **Playing a game on BlueStacks**, with the real game name underneath. The ID isn't secret, so it's fine to share with friends.

## 🛠️ Troubleshooting

**My game doesn't show up.**
1. Make sure the Discord app is open and activity sharing is on (see Requirements).
2. Check the log. Every game it detects gets a `playing:` line.
   - macOS: `~/Library/Logs/bluestacks-discord-presence.log`
   - Windows: `%LOCALAPPDATA%\bluestacks-discord-presence\bluestacks-discord-presence.log`
3. Still nothing? Discord may not know that game, or knows it under a slightly different name. The fallback above will cover it. On Windows, also try turning on ADB (see Backup: ADB).

**The timer on my own screen freezes and jumps.**
That's Discord, not this script. When Discord isn't the app in front, it saves battery by redrawing less often. Click into Discord and it catches up. Your friends see the timer ticking normally. ⏱️

**I also use MacOS Crossover Discord Presence.**
No problem, they're separate and don't step on each other. One handles your CrossOver games, this one handles BlueStacks.

## 👋 Uninstall

- macOS: double-click **`Uninstall.command`**, or run `sh uninstall.sh`.
- Windows: double-click **`Uninstall.bat`**.

It stops the script and removes all of its files, its cache and its log.

## 🧑‍💻 For developers

```bash
python3 bluestacks_discord_presence.py   # run in the foreground and watch the output
python3 scripts/update-seed.py           # refresh the bundled offline game list
sh scripts/package.sh                    # build both release zips into dist/
```

How it works: BlueStacks logs each app switch to `Player.log` (macOS: `/Users/Shared/Library/Application Support/BlueStacks/Logs/`, Windows: `C:\ProgramData\BlueStacks*\Logs\`), with the Android package name and the app's title. The script follows that file like `tail -f`, keeps track of which app is in front, and matches it to Discord's game list. It then connects to the Discord app's local IPC (a Unix socket on macOS, a named pipe on Windows) using that game's Discord app ID, and sets the activity.

It starts at login as a user LaunchAgent on macOS (`~/Library/LaunchAgents/com.lazyfoxjumps.bluestacks-discord-presence.plist`), and as a Startup-folder shortcut on Windows that runs it with `pythonw`, so no console window.

## 📜 License

[MIT](LICENSE). Use it, share it, change it. Have fun. 💛

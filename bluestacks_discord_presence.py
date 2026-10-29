#!/usr/bin/env python3
"""BlueStacks Discord Presence

Show Discord "Playing ..." status for Android games you play in BlueStacks, on macOS
and Windows.

BlueStacks doesn't tell Discord what you're playing. It does write every app switch
to its log, though, so this follows that log to see which Android app is on screen,
identifies the game, and sets presence over Discord's local IPC connection with the
game's real Discord application ID, so the name and icon are the official ones.
If the log doesn't say, it can also ask BlueStacks directly over ADB.

A game is identified by, in order:
  1. its Play Store package name, against the games Discord links to Google Play
  2. its name, against every game name Discord knows
  3. a fallback Discord app (optional, see FALLBACK_APP_ID) for games Discord doesn't know

Discord's list refreshes daily, so new games work without reinstalling. Uses only
the Python standard library.
"""

import glob
import gzip
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import traceback
import urllib.request
import uuid

WINDOWS = sys.platform == "win32"

DETECTABLE_URL = "https://discord.com/api/v9/applications/detectable"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE = os.path.join(APP_DIR, "games-seed.json.gz")  # offline copy shipped with the installer
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
if WINDOWS:
    DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "bluestacks-discord-presence")
    CACHE_DIR = DATA_DIR
    LOG_FILE = os.path.join(DATA_DIR, "bluestacks-discord-presence.log")
else:
    CACHE_DIR = os.path.expanduser("~/Library/Caches/bluestacks-discord-presence")
    LOG_FILE = None  # launchd sends stdout to ~/Library/Logs/bluestacks-discord-presence.log
CACHE_FILE = os.path.join(CACHE_DIR, "games-v1.json")
CACHE_MAX_AGE = 24 * 60 * 60
POLL_SECONDS = 10
ADB_RETRY_SECONDS = 60

# Discord app used for games Discord has never heard of. Its name shows as "Playing <app name>"
# with the real game name underneath. Empty disables it; config.json can set "fallback_app_id".
FALLBACK_APP_ID = ""

# Where BlueStacks keeps its log, config and ADB tool on each system.
if WINDOWS:
    _PROGRAM_DATA = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    BLUESTACKS_DATA_GLOBS = [os.path.join(_PROGRAM_DATA, "BlueStacks*")]
    BLUESTACKS_ADB_GLOBS = [os.path.join(os.environ.get(v, d), "BlueStacks*", "HD-Adb.exe")
                            for v, d in (("PROGRAMFILES", r"C:\Program Files"),
                                         ("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))]
    BLUESTACKS_PROCESS = "hd-player.exe"
else:
    BLUESTACKS_DATA_GLOBS = ["/Users/Shared/Library/Application Support/BlueStacks*"]
    BLUESTACKS_ADB_GLOBS = ["/Applications/BlueStacks*.app/Contents/MacOS/hd-adb"]
    BLUESTACKS_PROCESS = "/bluestacks.app/contents/macos/"

# BlueStacks logs every Android app switch, e.g.
# "...OnActivityDisplayed(1), com.ggv.roworldsea.aos, )" and "app_name : Ragnarok: The New World app_pkg : ..."
BS_ACTIVITY = re.compile(r"OnActivityDisplayed\(\d+\), ([\w.]+)")
BS_APP_NAME = re.compile(r"app_name : (.+?) app_pkg : ([\w.]+)")
BS_STOPPED = re.compile(r"Player state : Exiting")
BS_ADB_PORT = re.compile(r'bst\.instance\.[^.]+\.status\.adb_port="(\d+)"')
ADB_RESUMED = re.compile(r"(?:mResumedActivity|topResumedActivity|ResumedActivity)[:=].*? ([\w.]+)/")
# Home screens end the game; system pop-ups (permissions, Play Store, Google services) don't.
BS_HOME = re.compile(r"launcher|^com\.bluestacks\.")
BS_OVERLAY = re.compile(r"^(com\.android\.|com\.google\.android\.|android$)")

OP_HANDSHAKE, OP_FRAME, OP_CLOSE = 0, 1, 2

# Keep helper commands from flashing a console window on Windows.
_NO_WINDOW = {"creationflags": 0x08000000} if WINDOWS else {}


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    if LOG_FILE:
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
    if sys.stdout:
        print(line, flush=True)


def run(cmd, timeout=10):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **_NO_WINDOW).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


# ---------- Discord's game list ----------

def build_games(apps):
    names, packages = [], {}
    for app in apps:
        ref = [app["id"], app["name"]]
        for name in [app["name"]] + (app.get("aliases") or []):
            if normalize_name(name):
                names.append([normalize_name(name)] + ref)
        for sku in app.get("third_party_skus") or []:
            if sku.get("distributor") == "google_play" and sku.get("id"):
                packages.setdefault(sku["id"].lower(), ref)
    return {"names": names, "packages": packages}


def download_games():
    req = urllib.request.Request(DETECTABLE_URL, headers={"User-Agent": "bluestacks-discord-presence"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        games = build_games(json.load(resp))
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(games, f)
    os.replace(tmp, CACHE_FILE)
    return games


def load_games():
    """Fresh cache, else download, else stale cache, else the offline seed shipped with the install."""
    fresh = os.path.exists(CACHE_FILE) and time.time() - os.path.getmtime(CACHE_FILE) < CACHE_MAX_AGE
    if not fresh:
        try:
            games = download_games()
            log(f"downloaded Discord game list ({len(games['packages'])} Play Store IDs, {len(games['names'])} names)")
            return games
        except Exception as e:
            log(f"couldn't download game list: {e}")
    for path, opener in ((CACHE_FILE, open), (SEED_FILE, gzip.open)):
        try:
            with opener(path, "rt") as f:
                return json.load(f)
        except (OSError, ValueError):
            continue
    return {}


class Matcher:
    def __init__(self, games, fallback_app_id):
        self.packages = games.get("packages", {})
        self.by_name = {}
        for norm, app_id, label in games.get("names", []):
            self.by_name.setdefault(norm, (app_id, label))
        self.fallback_app_id = fallback_app_id

    def match(self, package, app_name):
        """Returns (app_id, label, details) or None."""
        hit = self.packages.get(package.lower())
        if not hit and app_name:
            hit = self.by_name.get(normalize_name(app_name))
        if hit:
            return hit[0], hit[1], None
        if self.fallback_app_id and app_name:
            return self.fallback_app_id, app_name, app_name
        return None


def load_fallback_app_id():
    try:
        with open(CONFIG_FILE) as f:
            return str(json.load(f).get("fallback_app_id") or FALLBACK_APP_ID)
    except (OSError, ValueError):
        return FALLBACK_APP_ID


# ---------- BlueStacks ----------

def bluestacks_dirs():
    found = []
    for pattern in BLUESTACKS_DATA_GLOBS:
        found += [d for d in glob.glob(pattern) if os.path.isdir(d)]
    return found


def bluestacks_log():
    """The Player.log written most recently, across every BlueStacks install."""
    logs = [p for d in bluestacks_dirs() for p in glob.glob(os.path.join(d, "Logs", "Player.log"))]
    return max(logs, key=os.path.getmtime) if logs else None


class BlueStacksWatcher:
    """Follows BlueStacks' log like `tail -f` to know which Android app is on screen,
    and falls back to asking over ADB when the log has nothing to say."""

    def __init__(self):
        self.path = None
        self.offset = 0
        self.inode = None
        self.package = None      # app currently in front, None at the home screen or when stopped
        self.names = {}          # package -> app name, as BlueStacks reports it
        self.log_has_switches = False
        self.adb_failed_at = 0

    def _read_new_lines(self):
        path = bluestacks_log()
        if not path:
            return []
        try:
            st = os.stat(path)
        except OSError:
            return []
        if path != self.path or st.st_ino != self.inode or st.st_size < self.offset:
            # New or rotated log: read it from the start.
            self.path, self.inode, self.offset, self.package = path, st.st_ino, 0, None
        if st.st_size == self.offset:
            return []
        with open(path, "rb") as f:
            f.seek(self.offset)
            data = f.read()
        # Only consume complete lines; a half-written last line is read next time.
        end = data.rfind(b"\n") + 1
        self.offset += end
        return data[:end].decode("utf-8", errors="ignore").splitlines()

    def _set_package(self, package):
        if BS_HOME.search(package):
            self.package = None
        elif not BS_OVERLAY.search(package):
            self.package = package

    def _from_log(self):
        for line in self._read_new_lines():
            m = BS_APP_NAME.search(line)
            if m and m.group(1).strip():
                self.names[m.group(2)] = m.group(1).strip()
            m = BS_ACTIVITY.search(line)
            if m:
                self.log_has_switches = True
                self._set_package(m.group(1))
            elif BS_STOPPED.search(line):
                self.package = None

    def _from_adb(self):
        """Ask Android which app is in front. Needs ADB turned on in BlueStacks settings."""
        if time.time() - self.adb_failed_at < ADB_RETRY_SECONDS:
            return
        adb = next((p for g in BLUESTACKS_ADB_GLOBS for p in glob.glob(g)), None)
        ports = []
        for d in bluestacks_dirs():
            try:
                with open(os.path.join(d, "bluestacks.conf"), errors="ignore") as f:
                    ports += BS_ADB_PORT.findall(f.read())
            except OSError:
                pass
        for port in dict.fromkeys(ports or ["5555"]):
            if not adb:
                break
            target = f"127.0.0.1:{port}"
            run([adb, "connect", target])
            out = run([adb, "-s", target, "shell", "dumpsys", "activity", "activities"])
            m = ADB_RESUMED.search(out)
            if m:
                self._set_package(m.group(1))
                return
        self.adb_failed_at = time.time()

    def current(self):
        """Return (package, app name) of the app in front, or None."""
        self._from_log()
        if not self.log_has_switches:
            self._from_adb()
        if not self.package:
            return None
        return self.package, self.names.get(self.package, "")


def bluestacks_running():
    if WINDOWS:
        out = run(["tasklist", "/FO", "CSV", "/NH"]).lower()
    else:
        out = run(["ps", "-axo", "command"]).lower()
    return BLUESTACKS_PROCESS in out


def running_game(matcher, watcher):
    """Return (app_id, label, details) for the game on screen in BlueStacks, or None."""
    if not bluestacks_running():
        watcher.package = None
        watcher.current()  # keep the log position current
        return None
    android = watcher.current()
    return matcher.match(*android) if android else None


# ---------- Discord IPC ----------

def temp_dir():
    # Discord's socket lives in the per-user temp dir; launchd agents don't always get $TMPDIR.
    if os.environ.get("TMPDIR"):
        return os.environ["TMPDIR"]
    out = run(["getconf", "DARWIN_USER_TEMP_DIR"])
    return out.strip() or "/tmp/"


class DiscordIPC:
    """Discord's local RPC: a Unix socket on macOS, a named pipe on Windows."""

    def __init__(self, client_id):
        self.client_id = client_id
        self.conn = None

    def connect(self):
        for i in range(10):
            if not self._open(i):
                continue
            try:
                self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
                _, data = self._recv()
                if data.get("evt") == "READY":
                    return True
                log(f"handshake rejected on discord-ipc-{i}: {data}")
            except (OSError, ValueError):
                pass
            self.close(quiet=True)
        return False

    def _open(self, i):
        if WINDOWS:
            try:
                self.conn = open(rf"\\?\pipe\discord-ipc-{i}", "r+b", buffering=0)
                return True
            except OSError:
                return False
        path = os.path.join(temp_dir(), f"discord-ipc-{i}")
        if not os.path.exists(path):
            return False
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect(path)
        except OSError:
            s.close()
            return False
        self.conn = s
        return True

    def _write(self, data):
        if WINDOWS:
            self.conn.write(data)
        else:
            self.conn.sendall(data)

    def _read(self, n):
        return self.conn.read(n) if WINDOWS else self.conn.recv(n)

    def _send(self, op, payload):
        body = json.dumps(payload).encode()
        self._write(struct.pack("<II", op, len(body)) + body)

    def _recv(self):
        op, length = struct.unpack("<II", self._recv_exact(8))
        return op, json.loads(self._recv_exact(length))

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self._read(n - len(buf))
            if not chunk:
                raise ConnectionError("Discord closed the connection")
            buf += chunk
        return buf

    def set_activity(self, start, details=None):
        activity = {"timestamps": {"start": start * 1000}}
        if details:
            activity["details"] = details
        self._send(OP_FRAME, {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": activity},
            "nonce": str(uuid.uuid4()),
        })
        _, data = self._recv()
        if data.get("evt") == "ERROR":
            raise ConnectionError(f"SET_ACTIVITY failed: {data.get('data')}")

    def alive(self):
        if not self.conn:
            return False
        if WINDOWS:
            # PeekNamedPipe fails once Discord has closed its end.
            import ctypes
            import msvcrt
            avail = ctypes.c_ulong(0)
            handle = msvcrt.get_osfhandle(self.conn.fileno())
            return bool(ctypes.windll.kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None))
        try:
            self.conn.setblocking(False)
            return self.conn.recv(1, socket.MSG_PEEK) != b""
        except BlockingIOError:
            return True
        except OSError:
            return False
        finally:
            if self.conn:
                self.conn.settimeout(5)

    def close(self, quiet=False):
        if self.conn:
            if not quiet:
                try:
                    self._send(OP_CLOSE, {})
                except (OSError, ValueError):
                    pass
            try:
                self.conn.close()
            except OSError:
                pass
            self.conn = None


# ---------- main loop ----------

def main():
    games = load_games()
    if not games:
        log("no game list available yet, will retry")
    matcher = Matcher(games, load_fallback_app_id())
    loaded_at = time.time()
    watcher = BlueStacksWatcher()
    active = None  # (app_id, label, DiscordIPC) for the game currently shown
    log("watching for Android games in BlueStacks")

    while True:
        if time.time() - loaded_at > CACHE_MAX_AGE or not games:
            games = load_games()
            matcher = Matcher(games, load_fallback_app_id())
            loaded_at = time.time()

        game = running_game(matcher, watcher)

        if active:
            app_id, label, ipc = active
            if not game or game[0] != app_id:
                log(f"stopped: {label}")
                ipc.close()
                active = None
            elif not ipc.alive():
                log(f"lost Discord connection for {label}, reconnecting")
                ipc.close(quiet=True)
                active = None

        if game and not active:
            app_id, label, details = game
            ipc = DiscordIPC(app_id)
            try:
                if ipc.connect():
                    ipc.set_activity(int(time.time()), details)
                    active = (app_id, label, ipc)
                    log(f"playing: {label}")
                else:
                    ipc.close(quiet=True)
            except (OSError, ConnectionError, ValueError) as e:
                log(f"{label}: {e}")
                ipc.close(quiet=True)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    # macOS restarts this through launchd; on Windows nothing does, so restart ourselves after a crash.
    while True:
        try:
            main()
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception:
            log("crashed, restarting in 30 seconds:\n" + traceback.format_exc())
            if not WINDOWS:
                raise
            time.sleep(30)

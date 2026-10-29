#!/bin/sh
# Rolls the two downloads people install from:
#   dist/BlueStacks-Discord-Presence-<version>-macOS.zip
#   dist/BlueStacks-Discord-Presence-<version>-Windows.zip
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-0.1-beta}"
NAME="BlueStacks-Discord-Presence"
SHARED="bluestacks_discord_presence.py games-seed.json.gz README.md CHANGELOG.md LICENSE"

build() {
    platform="$1"; shift
    stage="$ROOT/dist/$NAME"
    zip="$NAME-$VERSION-$platform.zip"
    rm -rf "$stage" "$ROOT/dist/$zip"
    mkdir -p "$stage"
    for f in $SHARED; do cp "$ROOT/$f" "$stage/"; done
    for f in "$@"; do cp "$ROOT/$f" "$stage/"; done
    [ -f "$ROOT/config.json" ] && cp "$ROOT/config.json" "$stage/"
    # ditto keeps the executable bits, so the macOS .command files stay double-clickable.
    (cd "$ROOT/dist" && ditto -c -k --norsrc --noextattr --keepParent "$NAME" "$zip")
    rm -rf "$stage"
    echo "Packaged dist/$zip"
}

chmod +x "$ROOT/install.sh" "$ROOT/uninstall.sh" "$ROOT/Install.command" "$ROOT/Uninstall.command"
build macOS install.sh uninstall.sh Install.command Uninstall.command
build Windows windows/Install.bat windows/Uninstall.bat

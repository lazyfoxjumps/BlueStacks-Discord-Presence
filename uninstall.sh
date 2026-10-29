#!/bin/sh
# Stops BlueStacks Discord Presence and removes everything install.sh created.
NAME="bluestacks-discord-presence"
LABEL="com.lazyfoxjumps.$NAME"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/Library/Application Support/$NAME" "$HOME/Library/Caches/$NAME"
rm -f "$HOME/Library/Logs/$NAME.log"

echo "BlueStacks Discord Presence is uninstalled."

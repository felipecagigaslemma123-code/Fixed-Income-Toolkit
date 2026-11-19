#!/bin/zsh

# macOS launchd cannot directly execute scripts stored under CloudStorage on
# this Mac. LaunchServices opens this bridge in Terminal, whose user session has
# access to the real OneDrive repository. The worker is detached immediately;
# run_treasury_bill_scheduler.py owns an OS-level lock, so a daily relaunch can
# never create a duplicate scheduler.

set -u

SCRIPT_DIR="${0:A:h}"
nohup /bin/zsh "$SCRIPT_DIR/morning_sync.sh" </dev/null >/dev/null 2>&1 &

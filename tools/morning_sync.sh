#!/bin/zsh

# Continuous daily sync, invoked at 09:30 by the macOS LaunchAgent
# com.fixedincome.morningsync. It starts the approved scheduler: A3 immediately
# and every 15 minutes; Treasury immediately and every 24 hours.
#
# Provider failures are isolated by the scheduler and do not stop the process.

set -u

# Resolve the repository root as the parent of this script's directory, so the
# LaunchAgent does not depend on the caller's working directory.
SCRIPT_DIR="${0:A:h}"
TOOLKIT_ROOT="${SCRIPT_DIR:h}"
cd "$TOOLKIT_ROOT" || exit 1

LOG_DIR="$TOOLKIT_ROOT/outputs/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/morning_sync.log"

PYTHON_CANDIDATES=(
  ".venv/bin/python"
  "python3.12"
  "python3.11"
  "python3.10"
  "python3.9"
  "python3"
)

{
  echo "----- morning_sync $(date '+%Y-%m-%d %H:%M:%S %z') -----"

  for candidate in "${PYTHON_CANDIDATES[@]}"; do
    if [[ "$candidate" == */* ]]; then
      resolved="$candidate"
      [[ -x "$resolved" ]] || continue
    else
      resolved="$(command -v "$candidate" 2>/dev/null)"
      [[ -n "$resolved" ]] || continue
    fi

    if "$resolved" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      echo "Using Python: $resolved"
      exec "$resolved" tools/run_treasury_bill_scheduler.py --environment PROD --allow-production
    fi
  done

  echo "No se encontró Python 3.9 o superior. Sync no ejecutado."
  exit 2
} >> "$LOG_FILE" 2>&1

#!/usr/bin/env bash
# Poll Jules sessions listed in watch.conf until each reaches a terminal state.
# watch.conf: line 1 = space separated session IDs, line 2 = poll interval (s)
cd "$(dirname "$0")" || exit 1
IDS=$(sed -n '1p' watch.conf)
INTERVAL=$(sed -n '2p' watch.conf)
[ -z "$INTERVAL" ] && INTERVAL=90
MAX=160

for i in $(seq 1 $MAX); do
  ALL_DONE=1
  for ID in $IDS; do
    LINE=$(jules remote list --session "$ID" 2>/dev/null | grep "$ID")
    echo "[$(date +%H:%M:%S)] $LINE"
    case "$LINE" in
      *Completed*|*Failed*|*"Awaiting User F"*) ;;
      *) ALL_DONE=0 ;;
    esac
  done
  if [ "$ALL_DONE" = "1" ]; then
    echo "=== ALL SESSIONS REACHED A TERMINAL STATE ==="
    exit 0
  fi
  sleep "$INTERVAL"
done
echo "=== TIMEOUT after $((MAX * INTERVAL))s ==="

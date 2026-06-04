#!/usr/bin/env bash
# Keep-warm poke: connect to the printer + status query (no paper) so its
# idle-sleep timer keeps resetting. Run frequently from cron, e.g. every 10
# min, or just through the night.
#
# Only logs STATE CHANGES (reachable <-> unreachable) so the log stays short
# and shows you exactly when the printer dozes off / comes back.
#
# Cron (NAS, root) — every 10 minutes:
#   */10 * * * * /home/guztaluz/gazeta/scripts/keep_awake.sh

URL="${GAZETA_URL:-http://localhost:8420}/printer/ping"
LOG="${GAZETA_KEEPAWAKE_LOG:-/home/guztaluz/gazeta/keepawake.log}"
STATE_FILE="/tmp/gazeta_printer_state"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

resp="$(curl -fsS --max-time 60 -X POST "$URL" 2>/dev/null)"
if echo "$resp" | grep -q '"awake": *true'; then
  state="awake"
else
  state="asleep"
fi

prev="$(cat "$STATE_FILE" 2>/dev/null || echo "unknown")"
if [ "$state" != "$prev" ]; then
  echo "$(ts) printer $prev -> $state ($resp)" >> "$LOG"
  echo "$state" > "$STATE_FILE"
fi

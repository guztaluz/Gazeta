#!/usr/bin/env bash
# Morning print, with patient retries + logging. Called by cron on the NAS.
#
# The printer auto-sleeps overnight. A BLE connect WAKES it, but the full
# wake+connect+print can take ~2 minutes. So each attempt must allow a long
# curl timeout, and gaps between attempts must be generous. (Earlier 20s gaps
# timed out before the printer finished waking -> 500s -> gave up.)
#
# Cron entry (NAS, root):
#   0 7 * * * /home/guztaluz/gazeta/scripts/cron_print.sh

URL="${GAZETA_URL:-http://localhost:8420}/print/summary"
# Fixed path (not $HOME) so it's the same whether run by your user or root cron.
LOG="${GAZETA_LOG:-/home/guztaluz/gazeta/cron.log}"
ATTEMPTS="${ATTEMPTS:-4}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-45}"
# Per-attempt curl ceiling: long enough for a cold wake+connect+print (~2 min)
# plus headroom. Without this, a slow wake looks like a failure.
CURL_MAX_TIME="${CURL_MAX_TIME:-180}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

for i in $(seq 1 "$ATTEMPTS"); do
  out="$(curl -fsS --max-time "$CURL_MAX_TIME" -X POST "$URL" 2>&1)"
  code=$?
  if [ $code -eq 0 ]; then
    echo "$(ts) OK (attempt $i): $out" >> "$LOG"
    exit 0
  fi
  echo "$(ts) FAIL (attempt $i, curl=$code): $out" >> "$LOG"
  [ "$i" -lt "$ATTEMPTS" ] && sleep "$SLEEP_BETWEEN"
done

echo "$(ts) GAVE UP after $ATTEMPTS attempts" >> "$LOG"
exit 1

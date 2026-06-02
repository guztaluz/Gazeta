#!/usr/bin/env bash
# Morning print, with retries + logging. Called by cron on the NAS.
#
# The printer may be asleep; the first BLE connect often wakes it but can time
# out, so we retry a few times. Logs to ~/gazeta-cron.log so failed mornings
# are visible.
#
# Cron entry (NAS):
#   0 7 * * * /home/guztaluz/gazeta/scripts/cron_print.sh

URL="${GAZETA_URL:-http://localhost:8420}/print/summary"
# Fixed path (not $HOME) so it's the same whether run by your user or root cron.
LOG="${GAZETA_LOG:-/home/guztaluz/gazeta/cron.log}"
ATTEMPTS=3
SLEEP_BETWEEN=20

ts() { date '+%Y-%m-%d %H:%M:%S'; }

for i in $(seq 1 "$ATTEMPTS"); do
  out="$(curl -fsS -X POST "$URL" 2>&1)"
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

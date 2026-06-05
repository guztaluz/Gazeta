#!/usr/bin/env bash
# Morning print. Wake the printer FIRST, confirm it's awake, then print once.
# Called by cron on the NAS.
#
# Why wake-first: the printer auto-sleeps (~10 min idle). If the print starts
# against a sleeping printer it may partially print then error, and a retry
# then prints the whole thing again (double print). Poking it awake first and
# only printing once it responds avoids both the failure and the double print.
#
# Cron entry (NAS, root):
#   0 7 * * * /home/guztaluz/gazeta/scripts/cron_print.sh

BASE="${GAZETA_URL:-http://localhost:8420}"
PING_URL="$BASE/printer/ping"
PRINT_URL="$BASE/print/summary"
LOG="${GAZETA_LOG:-/home/guztaluz/gazeta/cron.log}"

WAKE_TRIES="${WAKE_TRIES:-6}"      # up to ~3 min of waking attempts
WAKE_GAP="${WAKE_GAP:-25}"
PRINT_TRIES="${PRINT_TRIES:-2}"    # the print itself rarely needs a retry now
PRINT_GAP="${PRINT_GAP:-60}"
CURL_MAX_TIME="${CURL_MAX_TIME:-240}"  # full 4-block print can run a while

ts() { date '+%Y-%m-%d %H:%M:%S'; }

# 1) Wake the printer and wait until it actually responds awake.
awake=0
for i in $(seq 1 "$WAKE_TRIES"); do
  resp="$(curl -fsS --max-time 60 -X POST "$PING_URL" 2>/dev/null)"
  if echo "$resp" | grep -q '"awake": *true'; then
    awake=1
    echo "$(ts) printer awake (poke $i)" >> "$LOG"
    break
  fi
  sleep "$WAKE_GAP"
done
if [ "$awake" -ne 1 ]; then
  echo "$(ts) GAVE UP: printer never woke after $WAKE_TRIES pokes" >> "$LOG"
  exit 1
fi

# 2) Print once (retry only on hard failure, against a now-awake printer).
for i in $(seq 1 "$PRINT_TRIES"); do
  out="$(curl -fsS --max-time "$CURL_MAX_TIME" -X POST "$PRINT_URL" 2>&1)"
  code=$?
  if [ $code -eq 0 ]; then
    echo "$(ts) OK (print $i): $out" >> "$LOG"
    exit 0
  fi
  echo "$(ts) FAIL (print $i, curl=$code): $out" >> "$LOG"
  [ "$i" -lt "$PRINT_TRIES" ] && sleep "$PRINT_GAP"
done

echo "$(ts) GAVE UP after $PRINT_TRIES print attempts" >> "$LOG"
exit 1

#!/bin/sh
# Run every browser test on Chrome's engine and Safari's (WebKit). Usage: sh tests/run_all.sh
cd "$(dirname "$0")"
status=0
for engine in chromium webkit; do
  for t in test_*.py; do
    out=$(BROWSER=$engine python3 "$t" 2>&1); code=$?
    printf '%-9s %-20s %3s passed, %s failed\n' "$engine" "$t" "$(echo "$out" | grep -c '^PASS')" "$(echo "$out" | grep -c '^FAIL')"
    [ $code -ne 0 ] && { echo "$out" | grep -E '^FAIL|Error' | head -5; status=1; }
  done
done
exit $status

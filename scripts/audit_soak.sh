#!/usr/bin/env bash
# LBrightness Soak Audit & Promotion Readiness Verification Script
set -euo pipefail

HOURS="${1:-24}"
START="$(date -d "${HOURS} hours ago" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -v-${HOURS}H '+%Y-%m-%d %H:%M:%S')"
END="$(date '+%Y-%m-%d %H:%M:%S')"

echo "=================================================="
echo "      LBRIGHT 24-HOUR SOAK AUDIT PROTOCOL"
echo "=================================================="
echo "Audit Window: $START -> $END"
echo ""

FAILURES=0

# 1. Uptime, Memory & CPU Check
echo "--- [1/7] Service Lifecycle, Memory & CPU ---"
if systemctl --user is-active --quiet lbright.service; then
    systemctl --user status lbright.service --no-pager | grep -E "Active:|Memory:|CPU:" || true
    ps -o pid,etime,lstart,rss,pcpu,time,comm -C lbright || true
    
    RSS_KB=$(ps -o rss= -C lbright | tr -d ' ' || echo "0")
    if [ "$RSS_KB" -gt 5120 ]; then
        echo "❌ FAIL: RSS memory (${RSS_KB} KB) exceeds 5MB limit!"
        FAILURES=$((FAILURES + 1))
    else
        echo "✅ PASS: RSS memory (${RSS_KB} KB) is well below 5MB."
    fi
else
    echo "❌ FAIL: lbright.service is NOT active!"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# 2. Daemon Fatal Failure & Panic Audit
echo "--- [2/7] Daemon Fatal Failure & Panic Audit ---"
FATAL_ERRS=$(journalctl --user -u lbright.service --since "$START" --until "$END" --no-pager 2>/dev/null \
    | grep -Ei "panic|fatal|SIGSEGV|SIGABRT|backtrace|service failed|result=failed" || true)

FATAL_COUNT=$(echo -n "$FATAL_ERRS" | grep -c . || true)
if [ "$FATAL_COUNT" -gt 0 ]; then
    echo "❌ FAIL: Found $FATAL_COUNT daemon-level fatal errors or panics:"
    echo "$FATAL_ERRS"
    FAILURES=$((FAILURES + 1))
else
    echo "✅ PASS: Exactly 0 daemon-level fatal errors or panics."
fi
echo ""

# 3. Coredump Audit
echo "--- [3/7] Coredump Audit ---"
if command -v coredumpctl >/dev/null 2>&1; then
    COREDUMPS=$(coredumpctl --since "$START" list 2>/dev/null | grep -i lbright || true)
    CD_COUNT=$(echo -n "$COREDUMPS" | grep -c . || true)
    if [ "$CD_COUNT" -gt 0 ]; then
        echo "❌ FAIL: Found $CD_COUNT coredumps for lbright:"
        echo "$COREDUMPS"
        FAILURES=$((FAILURES + 1))
    else
        echo "✅ PASS: Exactly 0 coredumps found."
    fi
else
    echo "ℹ️  coredumpctl not installed, skipping system coredump list check."
fi
echo ""

# 4. DDC Timeout Pattern & Isolation
echo "--- [4/7] DDC Timeout Pattern & Rate Limiting ---"
TIMEOUT_LOGS=$(journalctl --user -u lbright.service --since "$START" --until "$END" --no-pager 2>/dev/null \
    | grep -i "timeout" || true)
TIMEOUT_COUNT=$(echo -n "$TIMEOUT_LOGS" | grep -c . || true)
echo "Logged DDC Timeout Events: $TIMEOUT_COUNT"
if [ "$TIMEOUT_COUNT" -gt 100 ]; then
    echo "⚠️  WARNING: High DDC timeout count ($TIMEOUT_COUNT). Reviewing last 10 entries:"
    echo "$TIMEOUT_LOGS" | tail -n 10
else
    echo "✅ PASS: DDC timeouts within normal rate-limited bounds."
fi
echo ""

# 5. Suspend / Resume & Rescan Recovery
echo "--- [5/7] Suspend / Resume & Rescan Evidence ---"
RESUME_LOGS=$(journalctl --user -u lbright.service --since "$START" --until "$END" --no-pager 2>/dev/null \
    | grep -Ei "suspend|resume|wake|rescan" || true)
RESUME_COUNT=$(echo -n "$RESUME_LOGS" | grep -c . || true)
echo "Resume / Rescan Events Logged: $RESUME_COUNT"
echo ""

# 6. Configuration & State File Integrity
echo "--- [6/7] Config & State Integrity ---"
CONFIG_FILE="$HOME/.config/lbrightness/config.ini"
if [ -s "$CONFIG_FILE" ]; then
    echo "✅ PASS: Configuration file exists and is non-empty ($(wc -l < "$CONFIG_FILE") lines)."
else
    echo "❌ FAIL: Configuration file missing or empty at $CONFIG_FILE!"
    FAILURES=$((FAILURES + 1))
fi

STALE_FILES=$(find "$HOME/.config/lbrightness" "$HOME/.local/state/lbrightness" -maxdepth 1 \( -name "*.tmp" -o -name "*.lock" \) 2>/dev/null || true)
STALE_COUNT=$(echo -n "$STALE_FILES" | grep -c . || true)
if [ "$STALE_COUNT" -gt 0 ]; then
    echo "⚠️  WARNING: Found $STALE_COUNT stale lock or tmp files:"
    echo "$STALE_FILES"
else
    echo "✅ PASS: No stale .tmp or .lock files."
fi
echo ""

# 7. Final CLI Responsiveness
echo "--- [7/7] CLI Responsiveness Check ---"
if lbright --version >/dev/null 2>&1 && lbright status >/dev/null 2>&1 && lbright pause status >/dev/null 2>&1; then
    echo "✅ PASS: CLI commands responded immediately without error."
else
    echo "❌ FAIL: CLI commands timed out or failed!"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "=================================================="
if [ "$FAILURES" -eq 0 ]; then
    echo "🎉 ALL GATES PASSED: Ready for Stable Promotion (v0.1.0)"
    echo "To promote to stable:"
    echo "  git tag -a v0.1.0 -m \"lbright 0.1.0 stable: direct sysfs + external DDC/CI support\""
    echo "  git push origin v0.1.0"
else
    echo "🛑 AUDIT FAILED ($FAILURES failures detected). Stable promotion blocked."
    echo "To roll back if needed:"
    echo "  systemctl --user disable --now lbright.service"
    echo "  systemctl --user enable --now auto-brightness.service"
fi
echo "=================================================="

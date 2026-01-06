#!/bin/bash
echo "========================================"
echo "   TradingAgents Test Suite Runner"
echo "========================================"

# Run pytest with verbose output to prevent "hanging" perception
# -v: verbose
# -s: show stdout (optional, but good for debugging)
python3 -m pytest tests/ -v

STATUS=$?

echo "========================================"
if [ $STATUS -eq 0 ]; then
    echo "✅ All Tests Passed!"
else
    echo "❌ Tests Failed."
fi
echo "========================================"
exit $STATUS

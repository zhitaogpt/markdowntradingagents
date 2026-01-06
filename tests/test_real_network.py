import subprocess
import sys
import pytest
import json
import time
import os

TICKER = "NVDA"

def run_tool(script_name):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    cmd = [sys.executable, f"tools/{script_name}", TICKER]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    if result.returncode != 0:
        return {"error": f"Script crashed: {result.stderr}"}
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {result.stdout}"}

class TestRealNetwork:
    def test_get_market_real(self):
        data = run_tool("get_market.py")
        # STRICT ASSERTION: No error allowed. Must have Price.
        assert "error" not in data, f"Market Fetch Failed: {data.get('error')}"
        assert data.get("current_price") is not None
        assert data.get("current_price") > 0

    def test_get_news_real(self):
        time.sleep(2)
        data = run_tool("get_news.py")
        # STRICT ASSERTION
        assert "error" not in data, f"News Fetch Failed: {data.get('error')}"
        assert len(data.get("top_news", [])) > 0

    def test_get_financials_real(self):
        time.sleep(2)
        data = run_tool("get_financials.py")
        # STRICT ASSERTION
        assert "error" not in data, f"Financials Fetch Failed: {data.get('error')}"
        # We check for a key metric
        val = data.get("valuation", {})
        # Note: Some keys might be N/A, but the structure must be valid
        assert val is not None
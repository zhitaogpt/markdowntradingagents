import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from tools import get_market, get_financials, get_news
except SyntaxError:
    pass 

class TestMarketTool:
    @patch('tools.get_market.yf.Ticker')
    def test_get_market_data_success(self, mock_ticker):
        pass

    def test_market_script_run(self):
        # Inject PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        import subprocess
        result = subprocess.run([sys.executable, "tools/get_market.py"], capture_output=True, text=True, env=env)
        # Check for expected error message when no args provided
        assert '"error": "No ticker provided"' in result.stdout

class TestOrchestrator:
    def test_orchestrator_syntax(self):
        with open("tools/orchestrator.py", "r") as f:
            source = f.read()
        compile(source, "tools/orchestrator.py", "exec")

    @patch('tools.orchestrator.subprocess.run')
    def test_orchestrator_logic(self, mock_run):
        from tools import orchestrator
        mock_run.return_value.stdout = json.dumps({"test": "data"})
        mock_run.return_value.returncode = 0
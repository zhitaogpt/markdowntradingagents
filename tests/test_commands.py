import os
import tomllib
import subprocess
import sys
import glob
import pytest
import time

COMMANDS_DIR = ".gemini/commands"
TEST_TICKER = "NVDA" 

def get_toml_files():
    files = glob.glob(os.path.join(COMMANDS_DIR, "**/*.toml"), recursive=True)
    return files

def run_with_retry(cmd_args, retries=2, delay=5):
    """Run command with retries."""
    last_result = None
    for attempt in range(retries):
        print(f"Executing: {" ".join(cmd_args)} (Attempt {attempt+1}/{retries})")
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        
        # We consider it a success ONLY if returncode is 0 AND no "Data Unavailable"
        if result.returncode == 0 and "Data Unavailable" not in result.stdout:
            return result
            
        last_result = result
        print(f"Attempt {attempt+1} failed/incomplete. Output snippet: {result.stdout[:100]}...")
        if attempt < retries - 1:
            time.sleep(delay)
            delay *= 2
            
    return last_result

@pytest.mark.parametrize("toml_file", get_toml_files())
def test_command_execution_real_network(toml_file):
    """
    STRICT REAL NETWORK TEST.
    Fails if data is unavailable.
    """
    time.sleep(1) 

    with open(toml_file, "rb") as f:
        data = tomllib.load(f)
    
    cmd_template = data.get("command")
    cmd = cmd_template.replace("{{args}}", TEST_TICKER)
    args = cmd.split()
    
    # Run with Retry Logic
    result = run_with_retry(args)
    
    stdout = result.stdout
    
    # 1. Critical Failure Check
    if result.returncode != 0:
        pytest.fail(f"Command crashed: {cmd}\nStderr: {result.stderr}")
        
    # 2. Strict Data Validation
    # If orchestrator prints "Data Unavailable", this test MUST FAIL now.
    if "Data Unavailable" in stdout:
        pytest.fail(f"Command ran but failed to fetch REAL data:\n{stdout}")

    assert "# Analysis Context" in stdout
    
    # 3. Content Check
    if "--mode tech" in cmd:
        assert "$" in stdout, "Real Price data missing (No $ symbol found)"
        # RSI might be None if Stooq fallback is used (Stooq snapshot has no history for RSI)
        # So we only assert Price for strict passing
             
    if "--mode fund" in cmd:
        assert "PE Ratio" in stdout
        assert "N/A" not in stdout.replace("Sent: N/A", ""), "Too many N/A values in fundamental data"

    if "--mode news" in cmd:
        assert "Recent Headlines" in stdout
import subprocess
import sys
import json
import argparse
import os
from concurrent.futures import ThreadPoolExecutor

def run_script(script_name, ticker):
    """Run a python script and return its JSON output."""
    try:
        env = os.environ.copy()
        root_dir = os.getcwd()
        env["PYTHONPATH"] = f"{root_dir}:{env.get('PYTHONPATH', '')}"

        result = subprocess.run(
            [sys.executable, f"tools/{script_name}", ticker],
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {"error": f"Failed to run {script_name}: {e.stderr}"}
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON output from {script_name}"}

def format_tech_report(data):
    if "error" in data:
        return f"STATUS: UNAVAILABLE ({data['error']})"
    ind = data.get("indicators", {})
    lines = [
        f"Price: ${data.get('current_price')} ({data.get('change_percent')}%) ",
        f"RSI: {ind.get('RSI_14')}",
        f"SMA50: {ind.get('SMA_50')} | SMA200: {ind.get('SMA_200')}",
        f"Bollinger: {ind.get('Bollinger_Position')}",
        f"Candles: {len(data.get('recent_candles', []))} periods"
    ]
    return "\n".join(lines)

def format_fund_report(data):
    if "error" in data:
        return f"STATUS: UNAVAILABLE ({data['error']})"
        
    val = data.get("valuation", {})
    fin = data.get("financials", {})
    
    lines = [
        f"PE_Trailing: {val.get('Trailing_PE')}",
        f"PE_Forward: {val.get('Forward_PE')}",
        f"Revenue_Growth: {fin.get('Revenue_Growth')}",
        f"Profit_Margin: {fin.get('Profit_Margins')}",
        f"Analyst_Target: {data.get('analyst_targets', {}).get('Target_Mean')}"
    ]
    return "\n".join(lines)

def format_news_report(data):
    if "error" in data:
        return f"STATUS: UNAVAILABLE ({data['error']})"
        
    news_items = data.get('top_news', [])
    lines = [f"Sentiment_Score: {data.get('overall_sentiment_score')}"]
    for n in news_items:
        title = n.get('title', 'No Title')
        lines.append(f"- {title}")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="TradingAgents Orchestrator")
    parser.add_argument("ticker", help="Stock Ticker Symbol")
    parser.add_argument("--mode", default="full", choices=["full", "tech", "fund", "news"], help="Data fetching mode")
    # Mock flag removed as per instruction
    args = parser.parse_args()

    # Parallel Fetching
    with ThreadPoolExecutor() as executor:
        futures = {}
        if args.mode in ["full", "tech"]:
            futures["tech"] = executor.submit(run_script, "get_market.py", args.ticker)
        if args.mode in ["full", "fund"]:
            futures["fund"] = executor.submit(run_script, "get_financials.py", args.ticker)
        if args.mode in ["full", "news"]:
            futures["news"] = executor.submit(run_script, "get_news.py", args.ticker)

        results = {k: v.result() for k, v in futures.items()}

    # Output XML-like structure for Strict Context Isolation
    print(f"<system_context ticker='{args.ticker}'>")
    
    if "tech" in results:
        print(f"  <data_source type='technical'>\n{format_tech_report(results['tech'])}\n  </data_source>")
        # Risk mostly uses tech data (volatility)
        print(f"  <data_source type='risk_metrics'>\n{format_tech_report(results['tech'])}\n  </data_source>")
        
    if "fund" in results:
        print(f"  <data_source type='fundamental'>\n{format_fund_report(results['fund'])}\n  </data_source>")
        
    if "news" in results:
        print(f"  <data_source type='sentiment'>\n{format_news_report(results['news'])}\n  </data_source>")
        print(f"  <data_source type='macro'>\n{format_news_report(results['news'])}\n  </data_source>")

    print("</system_context>")

if __name__ == "__main__":
    main()

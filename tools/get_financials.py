import yfinance as yf
import sys
import json
import time
import random
from tools.utils import get_session, exponential_backoff

def _fetch_yf_info(ticker_symbol):
    session = get_session()
    ticker = yf.Ticker(ticker_symbol, session=session)
    # ticker.info is the most prone to blocking
    info = ticker.info
    if not info or len(info) < 5:
        raise ValueError("YF info blocked or empty")
    return info

def get_financial_data(ticker_symbol):
    time.sleep(random.uniform(0.5, 2.0))
    try:
        info = exponential_backoff(lambda: _fetch_yf_info(ticker_symbol), retries=2)
        def gv(k): return info.get(k, "N/A")
        return {
            "symbol": ticker_symbol,
            "valuation": {"Trailing_PE": gv("trailingPE"), "Market_Cap": gv("marketCap")},
            "financials": {"Revenue_Growth": gv("revenueGrowth")},
            "source": "Yahoo Finance"
        }
    except Exception as e:
        # Finviz fallback
        try:
            import requests as req_std
            url = f"https://finviz.com/quote.ashx?t={ticker_symbol}"
            h = {"User-Agent": "Mozilla/5.0"}
            r = req_std.get(url, headers=h, timeout=10)
            p = r.text.split(">P/E<")[1].split("<b>")[1].split("</b>")[0]
            return {"symbol": ticker_symbol, "valuation": {"Trailing_PE": p}, "source": "Finviz (Fallback)"}
        except:
            return {"error": f"Financials failed: {e}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker"}))
    else:
        print(json.dumps(get_financial_data(sys.argv[1]), indent=2))

import yfinance as yf
import pandas as pd
import sys
import json
import time
import random
from tools.utils import get_session, exponential_backoff

def calculate_rsi(data, window=14):
    if len(data) < window: return None
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def _fetch_yf_history(ticker_symbol):
    session = get_session()
    ticker = yf.Ticker(ticker_symbol, session=session)
    hist = ticker.history(period="1mo")
    if hist.empty:
        raise ValueError("YF returned empty history")
    return hist

def get_market_data(ticker_symbol):
    # Initial stagger
    time.sleep(random.uniform(0.1, 1.5))
    
    try:
        hist = exponential_backoff(lambda: _fetch_yf_history(ticker_symbol), retries=2)
        
        hist['SMA_50'] = hist['Close'].rolling(window=min(len(hist), 50)).mean()
        hist['RSI'] = calculate_rsi(hist)
        latest = hist.iloc[-1]
        
        def safe_round(val):
            return round(float(val), 2) if not pd.isna(val) else None

        return {
            "symbol": ticker_symbol,
            "current_price": safe_round(latest['Close']),
            "indicators": {"RSI_14": safe_round(latest['RSI']), "SMA_50": safe_round(latest['SMA_50'])},
            "source": "Yahoo Finance"
        }
    except Exception as e:
        # Last resort fallback to Stooq (Minimal price)
        try:
            import requests as req_std
            import io
            url = f"https://stooq.com/q/l/?s={ticker_symbol}.US&f=sd2t2ohlc&h&e=csv"
            r = req_std.get(url, timeout=5)
            df = pd.read_csv(io.StringIO(r.text))
            return {"symbol": ticker_symbol, "current_price": float(df.iloc[0]['Close']), "source": "Stooq (Fallback)"}
        except:
            return {"error": f"Failed to get market data: {e}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker"}))
    else:
        print(json.dumps(get_market_data(sys.argv[1]), indent=2))

import os
import sys
import json
import time
import requests
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------
API_KEY = os.environ.get("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1"

def check_key():
    if not API_KEY:
        print("❌ Error: FINNHUB_API_KEY environment variable not set.", file=sys.stderr)
        print("   Usage: export FINNHUB_API_KEY='your_key' && python tools/get_data_finnhub.py <TICKER>", file=sys.stderr)
        sys.exit(1)

def fetch_json(endpoint, params={}):
    params['token'] = API_KEY
    url = f"{BASE_URL}{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠️ API Error [{endpoint}]: {e}", file=sys.stderr)
        return None

# -------------------------------------------------------------------------
# Technical Analysis (Using Pandas)
# -------------------------------------------------------------------------
def calculate_technicals(df):
    if df is None or len(df) < 1:
        return {}

    # Standardize column 't' to datetime
    if 't' in df.columns:
        # Check if it's numeric (Unix TS) or string
        if pd.api.types.is_numeric_dtype(df['t']):
            df['date'] = pd.to_datetime(df['t'], unit='s')
        else:
            df['date'] = pd.to_datetime(df['t'])
    
    df = df.sort_values('date')
    close = df['c']

    # 1. SMA
    df['SMA_50'] = close.rolling(window=50).mean()
    df['SMA_200'] = close.rolling(window=200).mean()

    # 2. RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # 3. Bollinger Bands (20, 2)
    df['BB_Mid'] = close.rolling(window=20).mean()
    df['BB_Std'] = close.rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)

    # 4. MACD (12, 26, 9)
    # EMA 12
    k_12 = 2 / (12 + 1)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    # EMA 26
    k_26 = 2 / (26 + 1)
    ema_26 = close.ewm(span=26, adjust=False).mean()
    
    df['MACD_Line'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']

    # Get latest values (last row)
    latest = df.iloc[-1]
    
    # Determine position relative to SMAs
    sma_50_status = "ABOVE" if latest['c'] > latest['SMA_50'] else "BELOW"
    if pd.isna(latest['SMA_50']): sma_50_status = "N/A"
    
    return {
        "RSI_14": round(latest['RSI_14'], 2) if not pd.isna(latest['RSI_14']) else None,
        "SMA_50": round(latest['SMA_50'], 2) if not pd.isna(latest['SMA_50']) else None,
        "SMA_200": round(latest['SMA_200'], 2) if not pd.isna(latest['SMA_200']) else None,
        "SMA_50_Status": sma_50_status,
        "Bollinger": {
            "Upper": round(latest['BB_Upper'], 2) if not pd.isna(latest['BB_Upper']) else None,
            "Lower": round(latest['BB_Lower'], 2) if not pd.isna(latest['BB_Lower']) else None
        },
        "MACD": {
            "Line": round(latest['MACD_Line'], 3) if not pd.isna(latest['MACD_Line']) else None,
            "Signal": round(latest['MACD_Signal'], 3) if not pd.isna(latest['MACD_Signal']) else None,
            "Hist": round(latest['MACD_Hist'], 3) if not pd.isna(latest['MACD_Hist']) else None
        }
    }

# -------------------------------------------------------------------------
# Main Logic
# -------------------------------------------------------------------------
def get_historical_candles_stooq(ticker):
    """Fallback: Fetch historical candles from Stooq CSV (No Key required)."""
    symbol = f"{ticker}.US"
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
    # Note: Stooq's /q/l/ is for latest quote. For historical we need /q/d/
    url_hist = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    
    try:
        r = requests.get(url_hist, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        # Stooq columns: Date,Open,High,Low,Close,Volume
        # Map to expected names
        df = df.rename(columns={"Date": "t", "Open": "o", "High": "h", "Low": "l", "Close": "c", "Volume": "v"})
        return df
    except Exception as e:
        print(f"⚠️ Stooq Fallback Error: {e}", file=sys.stderr)
        return None

def main():
    check_key()
    if len(sys.argv) < 2:
        print("Usage: python tools/get_data_finnhub.py <TICKER>")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    print(f"📡 Fetching data for {ticker} via Finnhub + Stooq...")

    # 1. Current Price (Finnhub Quote - Very Reliable)
    quote_raw = fetch_json("/quote", {"symbol": ticker})
    current_price = quote_raw.get('c', 0.0) if quote_raw else 0.0
    change_percent = quote_raw.get('dp', 0.0) if quote_raw else 0.0
    print(f"✅ Price Data: ${current_price} ({change_percent}%)")

    # 2. Historical Data (Stooq - for Indicators)
    df_hist = get_historical_candles_stooq(ticker)
    tech_indicators = calculate_technicals(df_hist) if df_hist is not None else {}
    if tech_indicators:
        print(f"✅ Technicals: RSI={tech_indicators.get('RSI_14')}, SMA50={tech_indicators.get('SMA_50')}")

    # 3. Basic Financials
    metrics_raw = fetch_json("/stock/metric", {"symbol": ticker, "metric": "all"})
    
    metrics = metrics_raw.get('metric', {}) if metrics_raw else {}
    print(f"✅ Fundamentals: PE={metrics.get('peTTM')}, Beta={metrics.get('beta')}")

    # 3. News
    # Get last 7 days news
    news_start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    news_end_date = datetime.now().strftime('%Y-%m-%d')
    
    news_raw = fetch_json("/company-news", {
        "symbol": ticker,
        "from": news_start_date,
        "to": news_end_date
    })
    
    news_items = []
    if news_raw and isinstance(news_raw, list):
        # Take top 10 relevant news
        # Simple keyword filter: Title should ideally contain ticker or company name parts
        # (This is a heuristic, can be relaxed if too strict)
        relevant_keywords = [ticker, "STOCK", "MARKET", "EARNINGS", "REVENUE", "PROFIT", "CEO"]
        
        count = 0
        for item in news_raw:
            if count >= 10: break
            
            headline = item.get('headline', '').upper()
            summary = item.get('summary', '').upper()
            
            # If explicit Ticker is mentioned in headline, it's high priority.
            # Otherwise, just include it (Finnhub usually filters by ticker already),
            # but we skip blank headlines.
            if not headline: continue
            
            news_items.append({
                "title": item.get('headline'),
                "source": item.get('source'),
                "published_at": datetime.fromtimestamp(item.get('datetime')).strftime('%Y-%m-%d %H:%M'),
                "summary": item.get('summary'),
                "url": item.get('url')
            })
            count += 1
    print(f"✅ News: Found {len(news_items)} recent articles.")

    # -------------------------------------------------------------------------
    # Persist to Files
    # -------------------------------------------------------------------------
    
    # Market JSON
    market_data = {
        "symbol": ticker,
        "current_price": current_price,
        "source": "Finnhub + Stooq",
        "indicators": tech_indicators,
        "raw_candles_last_5": df_hist['c'].tail(5).tolist() if df_hist is not None else []
    }
    
    # Financials JSON
    fund_data = {
        "valuation": {
            "PE_TTM": metrics.get('peTTM'),
            "PE_Forward": metrics.get('peInclExtraTTM'), # Finnhub metric naming varies, using best guess or 'peBasicExclExtraTTM'
            "PEG": metrics.get('pegTTM'),
            "Price_to_Book": metrics.get('pbAnnual'),
            "Price_to_Sales": metrics.get('psTTM')
        },
        "financials": {
            "52WeekHigh": metrics.get('52WeekHigh'),
            "52WeekLow": metrics.get('52WeekLow'),
            "MarketCap": metrics.get('marketCapitalization'),
            "Beta": metrics.get('beta')
        },
        "growth": {
            "EPS_Growth_5Y": metrics.get('epsGrowth5Y')
        }
    }
    
    # News JSON
    news_data = {
        "count": len(news_items),
        "top_news": news_items
    }

    # Ensure directory exists
    os.makedirs("agency/data", exist_ok=True)

    with open("agency/data/market.json", "w") as f:
        json.dump(market_data, f, indent=2)
    
    with open("agency/data/financials.json", "w") as f:
        json.dump(fund_data, f, indent=2)
        
    with open("agency/data/news.json", "w") as f:
        json.dump(news_data, f, indent=2)
        
    print("💾 All data saved to agency/data/")

if __name__ == "__main__":
    main()

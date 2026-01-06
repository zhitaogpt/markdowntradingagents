import json
import sys
import requests
import csv
import io
import re

def get_stooq_price(ticker):
    """Fetches Price and Volume from Stooq (No Key, CSV)."""
    # Stooq uses .US for US stocks
    symbol = f"{ticker}.US"
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        
        # Parse CSV
        f = io.StringIO(r.text)
        reader = csv.DictReader(f)
        row = next(reader, None)
        
        if row and row['Close'] != 'N/A':
            return {
                "price": float(row['Close']),
                "volume": float(row['Volume']),
                "date": row['Date']
            }
    except Exception as e:
        print(f"Error fetching Stooq: {e}", file=sys.stderr)
    return None

def get_finviz_data(ticker):
    """Fetches Fundamentals from Finviz (HTML Scraping)."""
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    data = {}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        html = r.text
        
        # Regex for key metrics in Finviz table
        # Format: <td ...>P/E</td><td ...><b>35.20</b></td>
        patterns = {
            "P/E": r">P/E</td>.*?<b>([\d\.]+)</b>",
            "Fwd P/E": r">Forward P/E</td>.*?<b>([\d\.]+)</b>",
            "PEG": r">PEG</td>.*?<b>([\d\.]+)</b>",
            "RSI": r">RSI \(14\)</td>.*?<b>([\d\.]+)</b>",
            "SMA50": r">SMA50</td>.*?<b>([-\d\.]+)%</b>",
            "SMA200": r">SMA200</td>.*?<b>([-\d\.]+)%</b>",
            "Price": r">Price</td>.*?<b>([\d\.]+)</b>" # Backup price
        }
        
        for key, pat in patterns.items():
            m = re.search(pat, html, re.DOTALL)
            if m:
                try:
                    data[key] = float(m.group(1))
                except:
                    data[key] = m.group(1)
                    
    except Exception as e:
        print(f"Error fetching Finviz: {e}", file=sys.stderr)
        
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python data_fetcher.py <TICKER>")
        sys.exit(1)
        
    ticker = sys.argv[1]
    print(f"Fetching data for {ticker}...")
    
    # 1. Get Price (Stooq preferred)
    market_data = get_stooq_price(ticker)
    finviz_data = get_finviz_data(ticker)
    
    # Merge
    final_price = market_data['price'] if market_data else (finviz_data.get('Price') or 0.0)
    
    # 2. Construct Market JSON
    market_json = {
        "symbol": ticker,
        "current_price": final_price,
        "source": "Stooq/Finviz",
        "indicators": {
            "RSI_14": finviz_data.get('RSI'),
            "SMA_50_Change_Percent": finviz_data.get('SMA50'),
            "SMA_200_Change_Percent": finviz_data.get('SMA200')
        }
    }
    
    # 3. Construct Financials JSON
    financials_json = {
        "valuation": {
            "Trailing_PE": finviz_data.get('P/E'),
            "Forward_PE": finviz_data.get('Fwd P/E'),
            "PEG_Ratio": finviz_data.get('PEG')
        },
        "financials": {
            "Note": "Data scraped from Finviz"
        }
    }
    
    # Write files
    with open("agency/data/market.json", "w") as f:
        json.dump(market_json, f, indent=2)
        
    with open("agency/data/financials.json", "w") as f:
        json.dump(financials_json, f, indent=2)
        
    print("✅ Data fetched and saved to agency/data/")

if __name__ == "__main__":
    main()

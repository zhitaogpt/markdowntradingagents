from duckduckgo_search import DDGS
from textblob import TextBlob
import sys
import json
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from tools.utils import exponential_backoff

def _fetch_ddg_news(query):
    with DDGS() as ddgs:
        results_gen = ddgs.text(query, max_results=5, region="wt-wt")
        items = list(results_gen)
        if not items:
            raise ValueError("DDGS returned no items")
        return items

def _fetch_yf_news(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    news = ticker.news
    if not news:
        raise ValueError("YF News returned no items")
    formatted = []
    for item in news[:5]:
        formatted.append({
            "title": item.get('title'),
            "body": item.get('summary', ''), 
            "href": item.get('link')
        })
    return formatted

def _fetch_google_rss(ticker_symbol):
    """Fallback: Google News RSS (Very robust)."""
    url = f"https://news.google.com/rss/search?q={ticker_symbol}+stock&hl=en-US&gl=US&ceid=US:en"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    
    root = ET.fromstring(resp.content)
    items = root.findall(".//item")[:5]
    
    formatted = []
    for item in items:
        formatted.append({
            "title": item.find("title").text,
            "body": "", # RSS doesn't have body usually
            "href": item.find("link").text
        })
    return formatted

def get_news_sentiment(ticker_symbol):
    news_items = []
    source_used = "DDG"
    
    try:
        # 1. DDG
        query = f"{ticker_symbol} stock news"
        news_items = exponential_backoff(lambda: _fetch_ddg_news(query), retries=1)
    except Exception as e1:
        try:
            # 2. YF
            news_items = exponential_backoff(lambda: _fetch_yf_news(ticker_symbol), retries=1)
            source_used = "YF"
        except Exception as e2:
            try:
                # 3. Google RSS
                news_items = exponential_backoff(lambda: _fetch_google_rss(ticker_symbol), retries=1)
                source_used = "GoogleRSS"
            except Exception as e3:
                return {"error": f"All sources failed. DDG:{e1} YF:{e2} RSS:{e3}"}

    try:
        sentiment_scores = []
        processed_news = []

        for item in news_items:
            title = item.get('title', '')
            text = title # Focus on title for sentiment
            
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            sentiment_scores.append(polarity)
            
            processed_news.append({
                "title": title,
                "source": item.get('href', ''),
                "sentiment": round(polarity, 2)
            })

        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        summary = {
            "symbol": ticker_symbol,
            "source": source_used,
            "overall_sentiment_score": round(avg_sentiment, 2),
            "sentiment_label": "Bullish" if avg_sentiment > 0.1 else ("Bearish" if avg_sentiment < -0.1 else "Neutral"),
            "top_news": processed_news
        }
        return summary

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ticker provided"}))
    else:
        print(json.dumps(get_news_sentiment(sys.argv[1]), indent=2))

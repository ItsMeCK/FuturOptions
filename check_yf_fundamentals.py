import yfinance as yf
import json

def check_fundamentals():
    ticker = "RELIANCE.NS"
    print(f"Fetching info for {ticker}...")
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Keys we are interested in
    keys = [
        "returnOnEquity", 
        "debtToEquity", 
        "trailingPE", 
        "priceToBook", 
        "freeCashflow", 
        "operatingCashflow",
        "ebitda",
        "revenueGrowth",
        "earningsGrowth"
    ]
    
    data = {k: info.get(k) for k in keys}
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    check_fundamentals()
